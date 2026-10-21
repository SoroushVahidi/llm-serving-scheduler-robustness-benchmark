"""Durable server diagnostics; independent of Torch, CUDA and vLLM imports."""
import json
import math
import os
from pathlib import Path
import signal
import subprocess
import threading
import time

from .slai import UnsupportedSemantics


def require_compatible_smoke(*, model, version, chunked_prefill):
    """No configuration is approved yet; never turn a warning into consent.

    This guard is deliberately specific to the reviewed MGPU00 experiment.
    A new supported-domain implementation and tests must replace it, rather
    than a CLI bypass or a silent flag change.
    """
    if model != 'Qwen/Qwen2.5-0.5B-Instruct' or version != '0.27.1':
        raise UnsupportedSemantics('Unreviewed model/version configuration')
    if not chunked_prefill:
        raise UnsupportedSemantics('vLLM 0.27.1 Qwen generation does not officially support disabling chunked prefill')
    raise UnsupportedSemantics('Chunked prefill requires an explicit checked-SLAI semantic extension; current adapter rejects it')


def validate_readiness_timeout(seconds):
    if not math.isfinite(seconds) or not 0 < seconds <= 1200:
        raise ValueError('Readiness deadline must be finite and within (0, 1200] seconds')
    return seconds


def checkpoint(path, value):
    """Replace only this run's progress checkpoint; preserve final evidence."""
    path = Path(path)
    temporary = path.with_suffix(path.suffix + '.tmp')
    with temporary.open('w') as stream:
        json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)
    fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


class ServerDiagnostics:
    """Own a process group and persist readiness, log milestones and exit status.

    Milestone timestamps measure log receipt, not unobservable internal phases.
    Server text is retained without timestamp prefixes; no log line establishes readiness.
    """
    MARKERS = {
        'api_process_initialized': 'non-default args:',
        'architecture_resolved': 'Resolved architecture:',
        'engine_initializing': 'Initializing a V1 LLM engine',
        'distributed_initializing': 'distributed_init_method=',
        'distributed_ranks_assigned': 'is assigned as DP rank',
        'model_loading_started': 'Loading model from scratch',
        'weights_loaded': 'Loading weights took',
        'model_loaded': 'Model loading took',
        'engine_initialized': 'init engine (',
        'api_application_started': 'Application startup complete',
    }

    def __init__(self, directory, prefix):
        self.base = Path(directory) / prefix
        self.events = Path(str(self.base) + '.startup.events.jsonl').open('x')
        self.lock = threading.Lock()
        self.process = None
        self.reader = None
        self.reader_error = None
        self.last = {'ready': False, 'attempts': 0, 'response': None, 'error': 'not attempted'}

    def event(self, stage, **fields):
        with self.lock:
            self.events.write(json.dumps(dict(stage=stage, time_ns=time.time_ns(),
                                             monotonic_s=time.monotonic(), **fields)) + '\n')
            self.events.flush()
            os.fsync(self.events.fileno())

    def save_readiness(self):
        checkpoint(str(self.base) + '.readiness.json', dict(self.last, time_ns=time.time_ns()))

    def start(self, command, environment):
        self.started = time.monotonic()
        self.event('process_launch_requested', command=command)
        self.save_readiness()
        self.log = Path(str(self.base) + '.server.log').open('x')
        try:
            self.process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                            env=environment, start_new_session=True, text=True,
                                            errors='replace', bufsize=1)
        except Exception as exc:
            self.event('process_launch_failed', error=repr(exc))
            self.last['terminal_error'] = repr(exc)
            self.save_readiness()
            self.log.close()
            raise
        self.event('process_started', pid=self.process.pid)
        self.reader = threading.Thread(target=self._drain, daemon=True)
        self.reader.start()

    def _drain(self):
        try:
            with self.log, self.process.stdout:
                for line in self.process.stdout:
                    self.log.write(line)
                    self.log.flush()
                    os.fsync(self.log.fileno())
                    for stage, marker in self.MARKERS.items():
                        if marker in line:
                            self.event(stage, source_line=line.rstrip(), timestamp_kind='log_receipt')
        except Exception as exc:
            self.reader_error = repr(exc)

    def wait_ready(self, client, model, timeout_s, interval_s=2.):
        timeout_s = validate_readiness_timeout(timeout_s)
        deadline = self.started + timeout_s
        self.event('readiness_wait_started', timeout_s=timeout_s)
        try:
            while time.monotonic() < deadline:
                if self.reader_error:
                    raise RuntimeError('Server log capture failed: ' + self.reader_error)
                code = self.process.poll()
                if code is not None:
                    raise RuntimeError(f'Server exited before readiness: {code}')
                self.last['attempts'] += 1
                self.last.update(response=None, error=None, ready=False)
                try:
                    response = client.get('/v1/models', timeout=min(3., max(.001, deadline-time.monotonic())))
                    self.last['response'] = {'status_code': response.status_code, 'body': response.text[:16384]}
                    if response.status_code == 200:
                        data = response.json()
                        self.last['ready'] = (isinstance(data, dict) and isinstance(data.get('data'), list)
                                              and any(isinstance(item, dict) and item.get('id') == model
                                                      for item in data['data']))
                        if not self.last['ready']:
                            self.last['error'] = 'Expected served model missing from readiness response'
                except Exception as exc:
                    self.last['error'] = f'{type(exc).__name__}: {exc}'
                self.save_readiness()
                if self.last['ready'] and time.monotonic() < deadline and self.process.poll() is None:
                    self.event('api_ready', elapsed_s=time.monotonic()-self.started)
                    return time.monotonic()-self.started
                time.sleep(min(interval_s, max(0., deadline-time.monotonic())))
            raise RuntimeError('Server readiness timeout')
        except Exception as exc:
            self.last.update(ready=False, terminal_error=f'{type(exc).__name__}: {exc}')
            self.save_readiness()
            self.event('readiness_failed', error=self.last['terminal_error'])
            raise

    def close(self):
        before = self.process.poll() if self.process else None
        error = None
        try:
            if self.process:
                # Always clean descendants, even if the API parent already exited.
                try:
                    os.killpg(self.process.pid, signal.SIGTERM)
                except ProcessLookupError:
                    pass
                try:
                    self.process.wait(timeout=30)
                except subprocess.TimeoutExpired:
                    pass
                try:
                    os.killpg(self.process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                self.process.wait(timeout=10)
            if self.reader:
                self.reader.join(timeout=5)
                if self.reader.is_alive() or self.reader_error:
                    raise RuntimeError('Incomplete server log capture: ' + str(self.reader_error))
        except Exception as exc:
            error = repr(exc)
        finally:
            status = dict(time_ns=time.time_ns(), returncode_before_cleanup=before,
                          returncode=self.process.poll() if self.process else None,
                          launched=self.process is not None, cleanup_error=error)
            checkpoint(str(self.base) + '.exit.json', status)
            self.event('process_cleanup_finished', exit_status=status)
            self.events.close()
        if error:
            raise RuntimeError(error)
