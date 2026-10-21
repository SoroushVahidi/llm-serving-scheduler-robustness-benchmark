"""Durable device diagnostics; CUDA/NVML collection only inside a Slurm job."""
import csv
import importlib.metadata
import json
import os
from pathlib import Path
import re
import socket
import subprocess
import time
import uuid

GIB = 1024**3


def uuid_identity(value):
    """Normalize UUID formatting without converting MIG identity into a GPU."""
    if isinstance(value, (list, tuple)):
        return 'unspecified', str(uuid.UUID(bytes=bytes(value)))
    if isinstance(value, bytes):
        value = value.decode('ascii')
    if not isinstance(value, str):
        raise ValueError('UUID must be text or 16 explicit UUID bytes')
    kind = 'unspecified'
    value = value.strip()
    if value.upper().startswith('MIG-GPU-'):
        match = re.fullmatch(r'MIG-GPU-([0-9a-fA-F-]{36})/(\d+)/(\d+)', value, re.I)
        if not match:
            raise ValueError('Malformed legacy MIG UUID')
        return 'mig', f'{uuid.UUID(match[1])}/{int(match[2])}/{int(match[3])}'
    for prefix, label in [('GPU-', 'gpu'), ('MIG-', 'mig')]:
        if value.upper().startswith(prefix):
            kind, value = label, value[len(prefix):]
            break
    # No abbreviated UUIDs or guessed matches.
    if not re.fullmatch(r'[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}', value):
        raise ValueError('Expected complete canonical UUID')
    return kind, str(uuid.UUID(value))


def same_full_uuid(cuda_uuid, nvml_uuid):
    ck, cv = uuid_identity(cuda_uuid)
    nk, nv = uuid_identity(nvml_uuid)
    return ck in {'unspecified', 'gpu'} and nk == 'gpu' and cv == nv


def pci_identity(value):
    m = re.fullmatch(r'([0-9a-fA-F]{4,8}):([0-9a-fA-F]{2}):([0-9a-fA-F]{2})\.([0-7])', value or '')
    if not m:
        raise ValueError('Missing/malformed PCI address')
    return tuple(int(x, 16) for x in m.groups())


def full_a100_checks(record):
    """Independent named checks. Missing/contradictory values fail closed."""
    checks = []
    def check(name, reason, predicate):
        try:
            passed = bool(predicate())
            detail = 'verified' if passed else reason
        except Exception as exc:
            passed, detail = False, f'{reason}: {type(exc).__name__}: {exc}'
        checks.append({'check': name, 'passed': passed, 'reason': detail})
    devices = record.get('devices') or []
    d = devices[0] if len(devices) == 1 else {}
    check('slurm_compute_context', 'Missing allocated compute-node context',
          lambda: bool(record['slurm_job_id']) and record['node'] == record['slurmd_nodename'] and not record['node'].startswith('login'))
    check('cuda_device_count', 'Must observe exactly one CUDA device and one property record',
          lambda: record['cuda_device_count'] == 1 and len(devices) == 1 and d['cuda_ordinal'] == 0)
    check('slurm_full_a100_gres', 'Missing full a100 GRES count 1 or contradictory typed GRES',
          lambda: slurm_full_a100(record['slurm_job_description']))
    check('cuda_a100_model', 'CUDA model is not A100', lambda: re.search(r'\bA100\b', d['model']))
    check('nvml_a100_model', 'Mapped NVML/parent model is not A100',
          lambda: re.search(r'\bA100\b', d['nvml_model']) and re.search(r'\bA100\b', d['parent_model']))
    check('cuda_full_memory', 'CUDA-visible capacity is below 75 GiB or absent', lambda: d['cuda_memory_bytes'] >= 75*GIB)
    check('nvml_full_memory', 'NVML physical capacity is below 75 GiB or inconsistent with CUDA (>2 GiB)',
          lambda: d['parent_memory_bytes'] >= 75*GIB and d['nvml_memory_bytes'] >= 75*GIB and
          abs(d['cuda_memory_bytes']-d['nvml_memory_bytes']) <= 2*GIB)
    check('nvml_non_mig_handle', 'NVML handle is MIG or its type is unknown', lambda: d['mig_device'] is False)
    check('mig_mode_disabled', 'Current or pending MIG mode is enabled/unknown',
          lambda: d['mig_mode_current'] == 0 and d['mig_mode_pending'] == 0)
    check('cuda_nvml_uuid', 'CUDA UUID does not match a full physical NVML UUID',
          lambda: same_full_uuid(d['cuda_uuid'], d['nvml_uuid']))
    check('cuda_uuid_bytes', 'CUDA UUID bytes contradict its string representation',
          lambda: d.get('cuda_uuid_bytes') is None or uuid_identity(d['cuda_uuid_bytes'])[1] == uuid_identity(d['cuda_uuid'])[1])
    check('parent_uuid', 'Mapped device and physical parent UUID differ',
          lambda: uuid_identity(d['nvml_uuid']) == uuid_identity(d['parent_uuid']) and uuid_identity(d['parent_uuid'])[0] == 'gpu')
    check('pci_mapping', 'CUDA and mapped NVML PCI addresses differ or are missing',
          lambda: pci_identity(d['cuda_pci_bus_id']) == pci_identity(d['nvml_pci_bus_id']))
    check('visible_device_selector', 'CUDA_VISIBLE_DEVICES is missing, multiple, malformed, MIG, or contradicts the observed UUID',
          lambda: visible_selector_matches(record.get('cuda_visible_devices'), d.get('cuda_uuid')))
    # nvidia-smi is supplementary to CUDA+NVML. If it supplies a selected row,
    # contradictions fail; command errors remain explicit diagnostics, not proof.
    smi = record.get('selected_nvidia_smi')
    check('nvidia_smi_consistency', 'Selected nvidia-smi row contradicts CUDA/NVML identity',
          lambda: (smi is None and record.get('selected_nvidia_smi_command', {}).get('returncode') != 0) or (smi is not None and same_full_uuid(d['cuda_uuid'], smi['uuid']) and
          pci_identity(smi['pci_bus_id']) == pci_identity(d['cuda_pci_bus_id']) and
          re.search(r'\bA100\b', smi['name']) and smi['mig_mode'].lower() == 'disabled' and
          abs(smi['memory_mib']*1024**2-d['cuda_memory_bytes']) <= 2*GIB))
    return checks


def legacy_identity_checks(record):
    """Evaluate the old compound predicate on NEW evidence, never old inference."""
    d = (record.get('devices') or [{}])[0]
    predicates = {
        'cuda_device_count_is_one': lambda: record['cuda_device_count'] == 1,
        'model_contains_A100': lambda: 'A100' in d['model'],
        'not_mig_device': lambda: not d['mig_device'],
        'mig_mode_current_zero': lambda: d['mig_mode_current'] == 0,
        'cuda_memory_at_least_75_GiB': lambda: d['cuda_memory_bytes'] >= 75*GIB,
        'raw_cuda_uuid_equals_nvml_uuid': lambda: d['cuda_uuid'] == d['nvml_uuid'],
        'raw_cuda_uuid_starts_GPU_prefix': lambda: d['cuda_uuid'].startswith('GPU-'),
        'literal_slurm_gres_match': lambda: 'gres/gpu:a100:1' in record['slurm_job_description'],
    }
    result = {}
    for name, predicate in predicates.items():
        try:
            result[name] = bool(predicate())
        except Exception as exc:
            result[name] = {'unavailable': f'{type(exc).__name__}: {exc}'}
    return result


def slurm_full_a100(description):
    typed = re.findall(r'gres/gpu:([a-zA-Z0-9_]+)[:=](\d+)', description)
    return bool(typed) and all(kind == 'a100' and int(n) == 1 for kind, n in typed)


def visible_selector_matches(selector, cuda_uuid):
    if not isinstance(selector, str) or ',' in selector or not selector.strip():
        return False
    selector = selector.strip()
    if selector.isdigit():
        # An ordinal is context, NOT a physical NVML index. UUID+PCI map it.
        return True
    return same_full_uuid(cuda_uuid, selector)


class DeviceVerificationError(ValueError):
    def __init__(self, checks):
        self.checks = checks
        super().__init__('Full A100 verification failed: ' + '; '.join(
            f"{c['check']}: {c['reason']}" for c in checks if not c['passed']))


def verify_full_a100(record):
    checks = full_a100_checks(record)
    if not all(c['passed'] for c in checks):
        raise DeviceVerificationError(checks)
    return 'FULL_GPU_VERIFIED'


class Journal:
    def __init__(self, directory):
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.stream = (self.directory/'device_probe.events.jsonl').open('x')

    def event(self, stage, **fields):
        self.stream.write(json.dumps({'stage': stage, 'time_ns': time.time_ns(), **fields}, sort_keys=True) + '\n')
        self.stream.flush()
        os.fsync(self.stream.fileno())

    def attempt(self, name, operation):
        self.event('query_started', query=name)
        try:
            value = operation()
        except Exception as exc:
            self.event('query_failed', query=name, error=f'{type(exc).__name__}: {exc}')
            return None
        self.event('query_result', query=name, value=value)
        return value


def persist_json(path, value):
    with Path(path).open('x') as stream:
        json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())


def probe_and_verify(directory, collector):
    """Persist raw evidence and check report BEFORE any identity exception."""
    journal = Journal(directory)
    record = {}
    try:
        journal.event('probe_started')
        try:
            record = collector(journal)
        except Exception as exc:
            record = {'collection_error': f'{type(exc).__name__}: {exc}'}
            journal.event('collection_failed', **record)
        persist_json(journal.directory/'device_probe.raw.json', record)
        checks = full_a100_checks(record)
        report = {'passed': all(c['passed'] for c in checks), 'checks': checks,
                  'legacy_predicates_on_new_evidence_only': legacy_identity_checks(record)}
        persist_json(journal.directory/'device_verification.json', report)
        journal.event('verification_complete', **report)
        if not report['passed']:
            raise DeviceVerificationError(checks)
        return dict(record, allocation_kind='FULL_GPU_VERIFIED')
    finally:
        journal.stream.close()


def command(arguments):
    p = subprocess.run(arguments, text=True, capture_output=True, timeout=20)
    return {'argv': arguments, 'returncode': p.returncode, 'stdout': p.stdout, 'stderr': p.stderr}


def string(value):
    return value.decode() if isinstance(value, bytes) else str(value)


def cgroup_evidence():
    result = {}
    for file in ['/proc/self/cgroup', '/proc/self/mountinfo']:
        try:
            text = Path(file).read_text()
            result[file] = '\n'.join(line for line in text.splitlines() if 'cgroup' in line) if file.endswith('mountinfo') else text
        except OSError as exc:
            result[file] = {'error': str(exc)}
    mounts = result.get('/proc/self/mountinfo', '')
    memberships = result.get('/proc/self/cgroup', '')
    if isinstance(mounts, str) and isinstance(memberships, str):
        for entry in memberships.splitlines():
            _, controllers, member = entry.split(':', 2)
            if 'devices' not in controllers.split(','):
                continue
            for line in mounts.splitlines():
                fields = line.split()
                if ' - cgroup ' not in line or 'devices' not in fields[-1].split(','):
                    continue
                root, mount = fields[3], fields[4]
                if member != root and not member.startswith(root.rstrip('/')+'/'):
                    continue
                path = Path(mount)/member.removeprefix(root).lstrip('/')/'devices.list'
                try:
                    result[str(path)] = path.read_text()
                except OSError as exc:
                    result[str(path)] = {'error': str(exc)}
    result['cgroup_v2_note'] = 'Device BPF policy is not inferred from filesystem visibility; no privileged BPF query attempted.'
    result['device_nodes'] = []
    for path in sorted(Path('/dev').glob('nvidia*')):
        try:
            st = path.stat()
            result['device_nodes'].append({'path': str(path), 'mode': oct(st.st_mode), 'major': os.major(st.st_rdev), 'minor': os.minor(st.st_rdev)})
        except OSError as exc:
            result['device_nodes'].append({'path': str(path), 'error': str(exc)})
    return result


def collect_raw(journal):
    result = {'node': socket.gethostname(), 'slurmd_nodename': os.environ.get('SLURMD_NODENAME'),
              'slurm_job_id': os.environ.get('SLURM_JOB_ID'), 'cuda_visible_devices': os.environ.get('CUDA_VISIBLE_DEVICES'),
              'environment': {k: os.environ.get(k) for k in ['CUDA_VISIBLE_DEVICES', 'CUDA_DEVICE_ORDER', 'NVIDIA_VISIBLE_DEVICES',
                  'SLURM_JOB_ID', 'SLURM_STEP_ID', 'SLURM_JOB_GPUS', 'SLURM_STEP_GPUS', 'SLURM_GPUS_ON_NODE', 'SLURMD_NODENAME']},
              'devices': [], 'software': {}}
    journal.event('context', value=result)
    result['cgroups'] = journal.attempt('cgroups', cgroup_evidence)
    if not result['slurm_job_id'] or not result['slurmd_nodename'] or result['node'].startswith('login'):
        result['collection_error'] = 'GPU queries prohibited outside allocated Slurm compute context'
        return result
    slurm = journal.attempt('scontrol_job', lambda: command(['/apps/slurm/current/bin/scontrol', 'show', 'job', '-d', '-o', result['slurm_job_id']]))
    result['scontrol'] = slurm
    result['slurm_job_description'] = slurm['stdout'] if slurm and slurm['returncode'] == 0 else None
    result['nvidia_smi_L'] = journal.attempt('nvidia_smi_L', lambda: command(['nvidia-smi', '-L']))
    result['nvidia_smi_inventory'] = journal.attempt('nvidia_smi_inventory', lambda: command(['nvidia-smi', '--query-gpu=index,uuid,name,memory.total,pci.bus_id,mig.mode.current,mig.mode.pending', '--format=csv']))
    journal.event('torch_import_started')
    import torch
    import pynvml as nv
    result['software'] = {'cuda': torch.version.cuda, 'torch': torch.__version__, 'torch_git': torch.version.git_version,
                          **{k: importlib.metadata.version(k) for k in ['vllm', 'transformers', 'nvidia-ml-py', 'httpx']}}
    journal.event('software', value=result['software'])
    result['cuda_device_count'] = journal.attempt('cuda_device_count', torch.cuda.device_count)
    # Persist CUDA properties before any NVML lookup/matching operation.
    for index in range(result['cuda_device_count'] or 0):
        def properties():
            p = torch.cuda.get_device_properties(index)
            return {'cuda_ordinal': index, 'model': p.name, 'cuda_uuid': string(p.uuid),
                    'cuda_uuid_type': type(p.uuid).__name__, 'cuda_uuid_repr': repr(p.uuid),
                    'cuda_uuid_bytes': list(p.uuid.bytes) if hasattr(p.uuid, 'bytes') else None,
                    'cuda_memory_bytes': p.total_memory, 'torch_properties_repr': repr(p),
                    'cuda_pci_bus_id': f'{p.pci_domain_id:08x}:{p.pci_bus_id:02x}:{p.pci_device_id:02x}.0'}
        d = journal.attempt(f'cuda_properties_{index}', properties)
        result['devices'].append(d or {'cuda_ordinal': index})
    journal.event('nvml_init_started')
    nv.nvmlInit()
    try:
        result['software']['driver'] = journal.attempt('nvml_driver', lambda: string(nv.nvmlSystemGetDriverVersion()))
        result['software']['nccl'] = journal.attempt('nccl_version', lambda: list(torch.cuda.nccl.version()))
        for d in result['devices']:
            # Try the original spelling and then only full canonical alternatives.
            # No lookup by CUDA index, no partial UUID matching, no PCI-only fallback.
            candidates = [d.get('cuda_uuid')]
            try:
                kind, value = uuid_identity(d.get('cuda_uuid'))
                if kind == 'unspecified':
                    candidates.extend(['GPU-'+value, 'MIG-'+value])
            except ValueError:
                pass
            handle = None
            for candidate in candidates:
                journal.event('nvml_uuid_lookup_started', uuid=candidate)
                try:
                    handle = nv.nvmlDeviceGetHandleByUUID(candidate)
                    journal.event('nvml_uuid_lookup_success', uuid=candidate)
                    d['nvml_lookup_uuid'] = candidate
                    break
                except Exception as exc:
                    journal.event('nvml_uuid_lookup_failed', uuid=candidate, error=f'{type(exc).__name__}: {exc}')
            if handle is None:
                continue
            def field(name, operation):
                d[name] = journal.attempt(f"device_{d['cuda_ordinal']}_{name}", operation)
            field('nvml_uuid', lambda: string(nv.nvmlDeviceGetUUID(handle)))
            field('nvml_model', lambda: string(nv.nvmlDeviceGetName(handle)))
            field('nvml_index', lambda: nv.nvmlDeviceGetIndex(handle))
            field('nvml_pci_bus_id', lambda: string(nv.nvmlDeviceGetPciInfo(handle).busId))
            field('nvml_memory_bytes', lambda: nv.nvmlDeviceGetMemoryInfo(handle).total)
            field('mig_device', lambda: bool(nv.nvmlDeviceIsMigDeviceHandle(handle)))
            if d['mig_device'] is None:
                continue
            parent = nv.nvmlDeviceGetDeviceHandleFromMigDeviceHandle(handle) if d['mig_device'] else handle
            field('parent_uuid', lambda: string(nv.nvmlDeviceGetUUID(parent)))
            field('parent_model', lambda: string(nv.nvmlDeviceGetName(parent)))
            field('parent_memory_bytes', lambda: nv.nvmlDeviceGetMemoryInfo(parent).total)
            mode = journal.attempt('parent_mig_mode', lambda: list(nv.nvmlDeviceGetMigMode(parent)))
            d['mig_mode_current'], d['mig_mode_pending'] = mode if mode else (None, None)
            if d['mig_device']:
                field('mig_gpu_instance_id', lambda: nv.nvmlDeviceGetGpuInstanceId(handle))
                field('mig_compute_instance_id', lambda: nv.nvmlDeviceGetComputeInstanceId(handle))
            if d.get('parent_uuid'):
                smi = journal.attempt('selected_nvidia_smi', lambda: command(['nvidia-smi', '-i', d['parent_uuid'],
                    '--query-gpu=name,uuid,memory.total,pci.bus_id,mig.mode.current', '--format=csv,noheader,nounits']))
                result['selected_nvidia_smi_command'] = smi
                if smi and smi['returncode'] == 0:
                    def parse_smi():
                        rows = list(csv.reader(smi['stdout'].splitlines()))
                        if len(rows) != 1 or len(rows[0]) != 5:
                            raise ValueError('Expected exactly one selected GPU row')
                        name, uid, mem, pci, mode = [v.strip() for v in rows[0]]
                        return {'name': name, 'uuid': uid, 'memory_mib': float(mem), 'pci_bus_id': pci, 'mig_mode': mode}
                    result['selected_nvidia_smi'] = journal.attempt('selected_nvidia_smi_parsed', parse_smi)
    finally:
        nv.nvmlShutdown()
    return result
