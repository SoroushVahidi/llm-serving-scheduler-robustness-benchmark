"""Append-only synthetic-fixture evidence. No model or GPU imports."""
import hashlib
import json
import os
from pathlib import Path
import socket
import time


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                                     allow_nan=False).encode()).hexdigest()


def clock_domain():
    return {'host': socket.gethostname(),
            'boot_id': Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
            'time_namespace': os.readlink('/proc/self/ns/time'),
            'clock': 'CLOCK_MONOTONIC'}


class Journal:
    """Flush each event; fsync terminal events. Truncated journals are not PASS.

    Hash chaining detects alteration relative to the final seal, not malicious
    rewriting of both log and seal. Capture is explicitly synthetic-only.
    """
    def __init__(self, path, *, synthetic, clock=time.monotonic):
        if synthetic is not True:
            raise ValueError('Full payload capture is restricted to synthetic fixtures')
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        self.stream = os.fdopen(fd, 'w')
        self.clock, self.sequence, self.previous = clock, 0, '0' * 64

    def event(self, kind, *, request_id=None, **data):
        row = dict(seq=self.sequence, kind=kind, time_s=self.clock(),
                   request_id=request_id, data=data, previous=self.previous)
        row['sha256'] = digest(row)
        self.stream.write(json.dumps(row, sort_keys=True, allow_nan=False) + '\n')
        self.stream.flush()
        if kind in ('terminal', 'run_end'):
            os.fsync(self.stream.fileno())
        self.previous = row['sha256']
        self.sequence += 1
        return row

    def close(self):
        self.stream.flush()
        os.fsync(self.stream.fileno())
        self.stream.close()


def read_journal(path):
    rows, previous = [], '0' * 64
    for line in Path(path).read_text().splitlines():
        row = json.loads(line)
        claimed = row.pop('sha256')
        if row['seq'] != len(rows) or row['previous'] != previous or digest(row) != claimed:
            raise ValueError('Journal sequence/hash chain mismatch')
        row['sha256'] = claimed
        previous = claimed
        rows.append(row)
    return rows


def seal(directory):
    """Seal every final file in this new execution directory, excluding seal itself."""
    directory = Path(directory)
    files = {}
    for p in sorted(directory.rglob('*')):
        if p.is_file() and p.name != 'seal.json':
            files[str(p.relative_to(directory))] = hashlib.sha256(p.read_bytes()).hexdigest()
    target = directory / 'seal.json'
    with target.open('x') as stream:
        json.dump({'files': files, 'scope': 'post-cleanup evidence; not a signature'}, stream, indent=2)
        stream.flush()
        os.fsync(stream.fileno())
    return files


def verify_seal(directory):
    directory = Path(directory)
    expected = json.loads((directory / 'seal.json').read_text())['files']
    actual = {str(p.relative_to(directory)): hashlib.sha256(p.read_bytes()).hexdigest()
              for p in directory.rglob('*') if p.is_file() and p.name != 'seal.json'}
    if actual != expected or not actual:
        raise ValueError('Evidence seal mismatch or empty evidence')
    return actual
