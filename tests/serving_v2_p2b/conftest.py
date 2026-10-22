"""Configuration-only native CPU scheduler. No weights or runner instantiation."""
from pathlib import Path
import importlib.util
import pytest

# Reuse the reviewed, local config fixture without changing MGPU02 files.
path = Path(__file__).parents[1]/'mgpu02'/'conftest.py'
spec = importlib.util.spec_from_file_location('p2a_config_fixture',path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


@pytest.fixture
def native_factory(tmp_path,monkeypatch):
    factory = module.scheduler_factory.__wrapped__(tmp_path,monkeypatch)
    def make(**kwargs):
        fixture = factory(slai=False,checked=False,**kwargs)
        from vllm.v1.core.sched.scheduler import Scheduler
        from vllm.v1.structured_output import StructuredOutputManager
        return Scheduler(vllm_config=fixture.vllm_config,
                         kv_cache_config=fixture.kv_cache_config,
                         structured_output_manager=StructuredOutputManager(fixture.vllm_config),
                         block_size=16)
    return make
