"""Bootstrap smoke test for the reused external-workload ingestion layer.

Runs only against small synthetic, schema-equivalent fixtures in
configs/external_workloads/fixtures/ -- never real third-party trace data.
"""
from __future__ import annotations

from pathlib import Path

from robustbench.workloads.external import registry
from robustbench.workloads.external.adapters import azure_llm, burstgpt, mooncake  # noqa: F401
from robustbench.workloads.external.schema import PROVENANCE_UNAVAILABLE

REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURES = REPO_ROOT / "configs" / "external_workloads" / "fixtures"


def test_registry_has_expected_adapters():
    names = registry.registered_names()
    assert {"burstgpt", "azure_llm_2023", "mooncake"} <= set(names)


def test_burstgpt_adapter_parses_fixture_and_flags_provenance():
    adapter = burstgpt.BurstGPTAdapter()
    path = FIXTURES / "burstgpt_sample.csv"
    records = list(adapter.stream_records(path))
    assert len(records) > 0
    r0 = records[0]
    assert r0.field_provenance["arrival_time_s"] != PROVENANCE_UNAVAILABLE
    assert r0.field_provenance.get("tenant_id", PROVENANCE_UNAVAILABLE) == PROVENANCE_UNAVAILABLE
    assert r0.validate() == []


def test_azure_llm_adapter_distinguishes_2023_and_2024_versions():
    a2023 = azure_llm.AzureLLMAdapter(split_name="code", dataset_year="2023")
    a2024 = azure_llm.AzureLLMAdapter(split_name="code", dataset_year="2024")
    assert a2023.source_dataset == "azure_llm_2023"
    assert a2024.source_dataset == "azure_llm_2024"
    assert a2023.source_version != a2024.source_version


def test_deterministic_record_ids_across_reparse():
    adapter = burstgpt.BurstGPTAdapter()
    path = FIXTURES / "burstgpt_sample.csv"
    ids_a = [r.derived_record_id for r in adapter.stream_records(path)]
    ids_b = [r.derived_record_id for r in adapter.stream_records(path)]
    assert ids_a == ids_b
