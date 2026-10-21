"""No GPU queries: fixtures and fake bindings exercise the fail-closed probe."""
import json
import sys
from types import SimpleNamespace
import uuid

import pytest
from robustbench.mgpu00.gpu_probe import (
    DeviceVerificationError, full_a100_checks, verify_full_a100, uuid_identity,
    same_full_uuid, probe_and_verify, collect_raw,
)

UID = '12345678-1234-5678-9abc-123456789abc'
OTHER = 'aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee'
GIB = 1024**3


def full_device():
    return {'node': 'n0003', 'slurmd_nodename': 'n0003', 'slurm_job_id': '42',
            'cuda_device_count': 1, 'cuda_visible_devices': '0',
            'slurm_job_description': 'AllocTRES=gres/gpu:a100=1 TresPerNode=gres/gpu:a100:1',
            'devices': [{'cuda_ordinal': 0, 'model': 'NVIDIA A100-SXM4-80GB',
                         'nvml_model': 'NVIDIA A100-SXM4-80GB', 'parent_model': 'NVIDIA A100-SXM4-80GB',
                         'mig_device': False, 'mig_mode_current': 0, 'mig_mode_pending': 0,
                         'cuda_memory_bytes': 80*GIB, 'nvml_memory_bytes': 80*GIB, 'parent_memory_bytes': 80*GIB,
                         'cuda_uuid': UID, 'nvml_uuid': 'GPU-'+UID, 'parent_uuid': 'GPU-'+UID,
                         'cuda_uuid_bytes': list(uuid.UUID(UID).bytes),
                         'cuda_pci_bus_id': '00000000:81:00.0', 'nvml_pci_bus_id': '0000:81:00.0', 'nvml_index': 3}]}


def failed_checks(record):
    return {c['check'] for c in full_a100_checks(record) if not c['passed']}


def test_genuine_full_device_and_numeric_remapping():
    record = full_device()
    assert verify_full_a100(record) == 'FULL_GPU_VERIFIED'
    record['cuda_visible_devices'] = '7'  # NOT nvml_index=3 or cuda_ordinal=0
    assert verify_full_a100(record) == 'FULL_GPU_VERIFIED'
    record['cuda_visible_devices'] = 'GPU-'+UID.upper()
    assert verify_full_a100(record) == 'FULL_GPU_VERIFIED'


@pytest.mark.parametrize('cuda_uuid', [UID, 'GPU-'+UID, 'gpu-'+UID.upper(), ('GPU-'+UID).encode()])
def test_equivalent_full_uuid_formats(cuda_uuid):
    assert same_full_uuid(cuda_uuid, 'GPU-'+UID)


@pytest.mark.parametrize('value', ['MIG-'+UID, 'MIG-GPU-'+UID+'/1/2'])
def test_mig_uuid_never_normalized_to_parent(value):
    assert uuid_identity(value)[0] == 'mig'
    assert not same_full_uuid(value, 'GPU-'+UID)


def test_known_mig_even_with_full_parent_inventory():
    record = full_device()
    record['slurm_job_description'] = 'AllocTRES=gres/gpu:a100_10g=1'
    d = record['devices'][0]
    d.update(mig_device=True, mig_mode_current=1, cuda_memory_bytes=int(9.5*GIB),
             nvml_memory_bytes=10*GIB, cuda_uuid='MIG-'+UID, nvml_uuid='MIG-'+UID,
             parent_uuid='GPU-'+OTHER)
    failures = failed_checks(record)
    assert {'slurm_full_a100_gres', 'cuda_full_memory', 'nvml_non_mig_handle', 'mig_mode_disabled',
            'cuda_nvml_uuid', 'parent_uuid'} <= failures
    with pytest.raises(DeviceVerificationError):
        verify_full_a100(record)


@pytest.mark.parametrize('field,value,check', [
    ('cuda_memory_bytes', None, 'cuda_full_memory'),
    ('cuda_uuid', None, 'cuda_nvml_uuid'),
    ('nvml_uuid', 'GPU-'+OTHER, 'cuda_nvml_uuid'),
    ('cuda_uuid_bytes', list(uuid.UUID(OTHER).bytes), 'cuda_uuid_bytes'),
    ('nvml_pci_bus_id', '0000:82:00.0', 'pci_mapping'),
    ('mig_device', None, 'nvml_non_mig_handle'),
    ('mig_mode_pending', 1, 'mig_mode_disabled'),
    ('parent_uuid', 'GPU-'+OTHER, 'parent_uuid'),
    ('model', 'NVIDIA L40', 'cuda_a100_model'),
])
def test_missing_or_contradictory_fields(field, value, check):
    record = full_device()
    record['devices'][0][field] = value
    assert check in failed_checks(record)


@pytest.mark.parametrize('selector', [None, '', '-1', '0,1', 'GPU-'+OTHER, 'MIG-'+UID, 'GPU-1234'])
def test_visible_selector_contradictions(selector):
    record = full_device()
    record['cuda_visible_devices'] = selector
    assert 'visible_device_selector' in failed_checks(record)


def test_nvidia_smi_contradictions_and_parse_failure():
    record = full_device()
    record['selected_nvidia_smi_command'] = {'returncode': 0}
    assert 'nvidia_smi_consistency' in failed_checks(record)
    record['selected_nvidia_smi'] = {'uuid': 'GPU-'+UID, 'pci_bus_id': '0000:81:00.0',
        'name': 'NVIDIA A100-SXM4-80GB', 'memory_mib': 80*1024, 'mig_mode': 'Disabled'}
    assert verify_full_a100(record) == 'FULL_GPU_VERIFIED'
    record['selected_nvidia_smi']['uuid'] = 'GPU-'+OTHER
    assert 'nvidia_smi_consistency' in failed_checks(record)


def test_failed_verification_persists_raw_before_raise(tmp_path):
    record = full_device()
    record['devices'][0]['mig_mode_current'] = 1
    with pytest.raises(DeviceVerificationError, match='mig_mode_disabled'):
        probe_and_verify(tmp_path, lambda journal: record)
    assert json.loads((tmp_path/'device_probe.raw.json').read_text()) == record
    report = json.loads((tmp_path/'device_verification.json').read_text())
    assert not report['passed']
    assert (tmp_path/'device_probe.events.jsonl').read_text().endswith('\n')
    with pytest.raises(FileExistsError):
        probe_and_verify(tmp_path, lambda journal: record)  # Never overwrite evidence.


def test_collection_crash_preserves_prior_journal(tmp_path):
    def crash(journal):
        journal.event('cuda_observation', uuid=UID, memory_bytes=80*GIB)
        raise RuntimeError('NVML unavailable')
    with pytest.raises(DeviceVerificationError):
        probe_and_verify(tmp_path, crash)
    assert UID in (tmp_path/'device_probe.events.jsonl').read_text()
    assert 'NVML unavailable' in (tmp_path/'device_probe.raw.json').read_text()
    assert not json.loads((tmp_path/'device_verification.json').read_text())['passed']


def test_collect_maps_by_uuid_not_cuda_index(tmp_path, monkeypatch):
    import robustbench.mgpu00.gpu_probe as probe
    monkeypatch.setenv('SLURM_JOB_ID', '42')
    monkeypatch.setenv('SLURMD_NODENAME', 'n0003')
    monkeypatch.setenv('CUDA_VISIBLE_DEVICES', '7')
    monkeypatch.setattr(probe.socket, 'gethostname', lambda: 'n0003')
    monkeypatch.setattr(probe, 'cgroup_evidence', lambda: {'fixture': True})
    monkeypatch.setattr(probe.importlib.metadata, 'version', lambda name: 'fixture')
    def cmd(argv):
        return {'argv': argv, 'returncode': 0 if 'scontrol' in argv[0] else 1,
                'stdout': 'TresPerNode=gres/gpu:a100:1', 'stderr': 'fixture'}
    monkeypatch.setattr(probe, 'command', cmd)
    class CUDAUUID:
        bytes = list(uuid.UUID(UID).bytes)
        def __str__(self):
            return UID
    prop = SimpleNamespace(name='NVIDIA A100-SXM4-80GB', uuid=CUDAUUID(), total_memory=80*GIB,
                           pci_domain_id=0, pci_bus_id=0x81, pci_device_id=0)
    monkeypatch.setitem(sys.modules, 'torch', SimpleNamespace(__version__='fixture',
        version=SimpleNamespace(cuda='13', git_version='fixture'), cuda=SimpleNamespace(
        device_count=lambda: 1, get_device_properties=lambda index: prop, nccl=SimpleNamespace(version=lambda: (2, 1, 0)))))
    lookups = []
    def handle(uid):
        lookups.append(uid)
        if uid != 'GPU-'+UID:
            raise ValueError('Explicit NVML GPU prefix required by fixture')
        return 'physical-handle-at-index-3'
    nv = SimpleNamespace(nvmlInit=lambda: None, nvmlShutdown=lambda: None,
        nvmlSystemGetDriverVersion=lambda: 'fixture', nvmlDeviceGetHandleByUUID=handle,
        nvmlDeviceGetUUID=lambda h: 'GPU-'+UID, nvmlDeviceGetName=lambda h: prop.name,
        nvmlDeviceGetIndex=lambda h: 3, nvmlDeviceGetPciInfo=lambda h: SimpleNamespace(busId=b'0000:81:00.0'),
        nvmlDeviceGetMemoryInfo=lambda h: SimpleNamespace(total=80*GIB),
        nvmlDeviceIsMigDeviceHandle=lambda h: False, nvmlDeviceGetMigMode=lambda h: (0, 0))
    monkeypatch.setitem(sys.modules, 'pynvml', nv)
    result = probe_and_verify(tmp_path, collect_raw)
    assert result['allocation_kind'] == 'FULL_GPU_VERIFIED'
    assert lookups == [UID, 'GPU-'+UID]
    assert result['devices'][0]['nvml_index'] == 3
    assert json.loads((tmp_path/'device_verification.json').read_text())['passed']


def test_no_gpu_import_or_query_without_allocation(tmp_path, monkeypatch):
    import robustbench.mgpu00.gpu_probe as probe
    monkeypatch.delenv('SLURM_JOB_ID', raising=False)
    monkeypatch.delenv('SLURMD_NODENAME', raising=False)
    monkeypatch.setattr(probe, 'cgroup_evidence', lambda: {'fixture': True})
    def forbidden(*args):
        pytest.fail('GPU command outside allocation')
    monkeypatch.setattr(probe, 'command', forbidden)
    with pytest.raises(DeviceVerificationError):
        probe_and_verify(tmp_path, collect_raw)
    raw = json.loads((tmp_path/'device_probe.raw.json').read_text())
    assert 'prohibited' in raw['collection_error']


def test_old_format_only_failures_explicit_on_new_evidence(tmp_path):
    probe_and_verify(tmp_path, lambda journal: full_device())
    report = json.loads((tmp_path/'device_verification.json').read_text())
    assert report['passed']
    legacy = report['legacy_predicates_on_new_evidence_only']
    assert not legacy['raw_cuda_uuid_equals_nvml_uuid']
    assert not legacy['raw_cuda_uuid_starts_GPU_prefix']
    assert legacy['mig_mode_current_zero']
