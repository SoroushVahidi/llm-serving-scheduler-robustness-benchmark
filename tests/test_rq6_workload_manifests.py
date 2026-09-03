from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]


def _load_module(name: str, rel_path: str):
    path = REPO_ROOT / rel_path
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


build_mod = _load_module("build_rq6_workload_manifests", "scripts/real_vllm/build_rq6_workload_manifests.py")
validate_mod = _load_module("validate_rq6_workload_manifests", "scripts/real_vllm/validate_rq6_workload_manifests.py")


# ---------------------------------------------------------------------------
# Fabricated fixtures -- never the real 24,000-row frozen data, per the
# task's "use fabricated data for error-path tests" instruction. Structural
# tests that call build_source_manifest() directly use FAKE_N_WINDOWS x
# FAKE_WINDOW_SIZE fake records (matching the real shape, since that
# function hard-asserts it); the STOPPING/error-path tests further down use
# smaller ad hoc fixtures against load_and_verify_inputs() directly.
# ---------------------------------------------------------------------------

# build_source_manifest hard-asserts the real WINDOW_SIZE (200) and
# N_WINDOWS_PER_SOURCE (40) as a production safety feature (never silently
# accepting a truncated/malformed frozen window) -- so fabricated fixtures
# for tests that exercise build_source_manifest directly must match that
# shape exactly, not a smaller stand-in size.
FAKE_WINDOW_SIZE = build_mod.WINDOW_SIZE
FAKE_N_WINDOWS = build_mod.N_WINDOWS_PER_SOURCE


def _fake_record(i: int, window_id: str, arrival: float, input_tokens: int = 10, output_tokens: int = 5) -> dict:
    return {
        "source_dataset": "fake",
        "source_version": "v0",
        "source_record_id": f"{window_id}:{i}",
        "derived_record_id": hashlib.sha256(f"{window_id}:{i}".encode()).hexdigest()[:32],
        "source_license": "CC0",
        "source_url": "https://example.invalid",
        "conversion_version": "fake_adapter_v1",
        "arrival_time_s": arrival,
        "interarrival_time_s": None,
        "session_relative_time_s": None,
        "timestamp_provenance_kind": "real",
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": None,
        "context_growth_tokens": None,
        "sequence_position": None,
        "session_id": None,
        "tenant_id": None,
        "synthetic_tenant_assigned": False,
        "model_class": None,
        "prefix_reuse_info": None,
        "kv_block_hash": None,
        "reuse_group_id": None,
        "reuse_confidence_source": None,
        "task_category": None,
        "interaction_category": None,
        "model_family": None,
        "extra": None,
        "field_provenance": None,
    }


def _fake_window(source: str, idx: int) -> dict:
    wid = f"{source}_fake_w{idx:02d}"
    records = [_fake_record(i, wid, arrival=float(i) * 0.01, input_tokens=10 + i) for i in range(FAKE_WINDOW_SIZE)]
    content_sha256 = hashlib.sha256(json.dumps(records, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return {
        "window_id": wid,
        "source_family": source,
        "source_file": "fake.csv",
        "source_file_sha256": "0" * 64,
        "sampling_algorithm": "fake",
        "sampling_seed": idx,
        "offset_valid_rows": 0,
        "start_index_in_valid_rows": 0,
        "request_count": FAKE_WINDOW_SIZE,
        "arrival_time_s_min": records[0]["arrival_time_s"],
        "arrival_time_s_max": records[-1]["arrival_time_s"],
        "descriptor": {},
        "records": records,
        "evidence_class": "FAKE_WINDOW",
        "chronology_stratum": "fake",
        "content_sha256": content_sha256,
    }


def _fake_cache(source: str, n_windows: int = 2) -> dict:
    windows = [_fake_window(source, i) for i in range(n_windows)]
    return {"manifest_kind": "fake", "windows": windows}


def _fake_campaign_freeze(source: str, windows: list) -> dict:
    window_identities = {w["window_id"]: w["content_sha256"] for w in windows}
    cells = [
        {"cell_id": f"{w['window_id']}::HIGH_PRESSURE::fifo::rep0",
         "window_id": w["window_id"], "synthesis_seed": 900000 + i,
         "source_family": source, "load_region": "HIGH_PRESSURE"}
        for i, w in enumerate(windows)
    ]
    region_assignment_index = {
        f"{source}::{w['window_id']}::HIGH_PRESSURE": {
            "absolute_load_factor": 1.5,
            "lambda_ref": 1.0,
            "selected_load_factor": 1.5,
        }
        for w in windows
    }
    return {
        "window_identities": window_identities,
        "cells": cells,
        "region_assignment_index": region_assignment_index,
    }


class _FakeTokenizer:
    """Whitespace tokenizer: deterministic, dependency-free, exact by
    construction (no BPE merge ambiguity) -- used for fast unit tests of
    the generator's structural logic. Exact-length-match-vs-a-real-model
    tokenizer is separately verified in test_build_exact_length_prompt_*
    below using the real project tokenizer."""

    def encode(self, text: str, add_special_tokens: bool = False):
        return text.split()

    def decode(self, ids):
        return " ".join(ids)


@pytest.fixture(scope="module")
def real_tokenizer():
    transformers = pytest.importorskip("transformers")
    return transformers.AutoTokenizer.from_pretrained("Qwen/Qwen2.5-0.5B-Instruct")


# ---------------------------------------------------------------------------
# 1/2. Deterministic generation + repeat generation == identical content hash
# ---------------------------------------------------------------------------

def test_build_source_manifest_deterministic():
    source = "fake_source"
    cache = _fake_cache(source, n_windows=FAKE_N_WINDOWS)
    campaign_freeze = _fake_campaign_freeze(source, cache["windows"])
    tok = _FakeTokenizer()

    m1 = build_mod.build_source_manifest(
        source, cache=cache, campaign_freeze=campaign_freeze, tokenizer=tok,
        tokenizer_name="fake", generation_code_sha="fixed", verify_prompts=True,
    )
    m2 = build_mod.build_source_manifest(
        source, cache=cache, campaign_freeze=campaign_freeze, tokenizer=tok,
        tokenizer_name="fake", generation_code_sha="fixed", verify_prompts=True,
    )
    assert m1["content_sha256"] == m2["content_sha256"]


# ---------------------------------------------------------------------------
# 3. All-window inclusion (no dropping/subsampling)
# ---------------------------------------------------------------------------

def test_all_windows_included_none_dropped():
    source = "fake_source"
    cache = _fake_cache(source, n_windows=FAKE_N_WINDOWS)
    campaign_freeze = _fake_campaign_freeze(source, cache["windows"])
    m = build_mod.build_source_manifest(
        source, cache=cache, campaign_freeze=campaign_freeze, tokenizer=_FakeTokenizer(),
        tokenizer_name="fake", generation_code_sha="fixed", verify_prompts=False,
    )
    assert m["window_count"] == FAKE_N_WINDOWS
    assert {w["window_id"] for w in m["windows"]} == {w["window_id"] for w in cache["windows"]}
    assert m["request_count"] == FAKE_N_WINDOWS * FAKE_WINDOW_SIZE


# ---------------------------------------------------------------------------
# 4. Request-order preservation (arrival-sorted within each window)
# ---------------------------------------------------------------------------

def test_request_order_matches_arrival_order():
    source = "fake_source"
    cache = _fake_cache(source, n_windows=FAKE_N_WINDOWS)
    # Shuffle record order in the fake window; synthesis re-sorts by arrival.
    cache["windows"][0]["records"] = list(reversed(cache["windows"][0]["records"]))
    campaign_freeze = _fake_campaign_freeze(source, cache["windows"])
    m = build_mod.build_source_manifest(
        source, cache=cache, campaign_freeze=campaign_freeze, tokenizer=_FakeTokenizer(),
        tokenizer_name="fake", generation_code_sha="fixed", verify_prompts=False,
    )
    reqs = m["windows"][0]["requests"]
    arrivals = [r["base_relative_arrival_s"] for r in reqs]
    assert arrivals == sorted(arrivals)
    assert [r["request_index"] for r in reqs] == list(range(FAKE_WINDOW_SIZE))


# ---------------------------------------------------------------------------
# 5. Window boundary / concatenation semantics: window j+1 starts exactly at
#    window j's last (scaled) arrival -- no artificial gap or overlap.
# ---------------------------------------------------------------------------

def test_window_boundary_continuity():
    source = "fake_source"
    cache = _fake_cache(source, n_windows=FAKE_N_WINDOWS)
    campaign_freeze = _fake_campaign_freeze(source, cache["windows"])
    m = build_mod.build_source_manifest(
        source, cache=cache, campaign_freeze=campaign_freeze, tokenizer=_FakeTokenizer(),
        tokenizer_name="fake", generation_code_sha="fixed", verify_prompts=False,
    )
    for prev_w, next_w in zip(m["windows"], m["windows"][1:]):
        assert next_w["requests"][0]["base_relative_arrival_s"] == pytest.approx(
            prev_w["requests"][-1]["base_relative_arrival_s"]
        )
    all_arrivals = [r["base_relative_arrival_s"] for w in m["windows"] for r in w["requests"]]
    assert all(a <= b + 1e-12 for a, b in zip(all_arrivals, all_arrivals[1:]))


# ---------------------------------------------------------------------------
# 6. Timing normalization: absolute_load_factor scaling is applied (window
#    with factor 3.0 compresses inter-arrival gaps by 3x vs factor 1.0).
# ---------------------------------------------------------------------------

def test_timing_normalization_scales_by_absolute_load_factor():
    source = "fake_source"
    cache = _fake_cache(source, n_windows=FAKE_N_WINDOWS)
    campaign_freeze = _fake_campaign_freeze(source, cache["windows"])
    wid = cache["windows"][0]["window_id"]
    key = f"{source}::{wid}::HIGH_PRESSURE"

    campaign_freeze["region_assignment_index"][key]["absolute_load_factor"] = 1.0
    m_unscaled = build_mod.build_source_manifest(
        source, cache=cache, campaign_freeze=copy.deepcopy(campaign_freeze), tokenizer=_FakeTokenizer(),
        tokenizer_name="fake", generation_code_sha="fixed", verify_prompts=False,
    )
    campaign_freeze["region_assignment_index"][key]["absolute_load_factor"] = 4.0
    m_scaled = build_mod.build_source_manifest(
        source, cache=cache, campaign_freeze=campaign_freeze, tokenizer=_FakeTokenizer(),
        tokenizer_name="fake", generation_code_sha="fixed", verify_prompts=False,
    )
    last_unscaled = m_unscaled["windows"][0]["requests"][-1]["base_relative_arrival_s"]
    last_scaled = m_scaled["windows"][0]["requests"][-1]["base_relative_arrival_s"]
    assert last_scaled == pytest.approx(last_unscaled / 4.0)


# ---------------------------------------------------------------------------
# 7. Exact prompt-token length (real tokenizer)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("target,seed", [(1, 0), (7, 3), (100, 900000), (2048, 42)])
def test_build_exact_length_prompt_exact_match(real_tokenizer, target, seed):
    from robustbench.real_llm.calibration_common import build_exact_length_prompt, verify_exact_length_prompt
    text = build_exact_length_prompt(real_tokenizer, target, seed)
    assert verify_exact_length_prompt(real_tokenizer, text, target)


def test_build_exact_length_prompt_deterministic(real_tokenizer):
    from robustbench.real_llm.calibration_common import build_exact_length_prompt
    a = build_exact_length_prompt(real_tokenizer, 250, 12345)
    b = build_exact_length_prompt(real_tokenizer, 250, 12345)
    assert a == b


# ---------------------------------------------------------------------------
# 8. Output-token mapping: output_tokens_target == frozen actual_output_tokens
#    (ground truth), predicted_output_tokens carried separately.
# ---------------------------------------------------------------------------

def test_output_token_mapping_and_overlay_preservation():
    source = "fake_source"
    cache = _fake_cache(source, n_windows=FAKE_N_WINDOWS)
    campaign_freeze = _fake_campaign_freeze(source, cache["windows"])
    m = build_mod.build_source_manifest(
        source, cache=cache, campaign_freeze=campaign_freeze, tokenizer=_FakeTokenizer(),
        tokenizer_name="fake", generation_code_sha="fixed", verify_prompts=False,
    )
    fake_output_tokens = {r["output_tokens"] for r in cache["windows"][0]["records"]}
    manifest_targets = {r["output_tokens_target"] for r in m["windows"][0]["requests"]}
    assert manifest_targets == fake_output_tokens
    for r in m["windows"][0]["requests"]:
        assert r["priority"] == 1.0
        assert r["weight"] == 1.0
        assert r["class_id"] == "stage0_uniform"
        assert isinstance(r["predicted_output_tokens"], int)


# ---------------------------------------------------------------------------
# 9. Stage-0 overlay is the frozen synthesis contract, not a new one
# ---------------------------------------------------------------------------

def test_uses_frozen_synthesis_version():
    source = "fake_source"
    cache = _fake_cache(source, n_windows=FAKE_N_WINDOWS)
    campaign_freeze = _fake_campaign_freeze(source, cache["windows"])
    m = build_mod.build_source_manifest(
        source, cache=cache, campaign_freeze=campaign_freeze, tokenizer=_FakeTokenizer(),
        tokenizer_name="fake", generation_code_sha="fixed", verify_prompts=False,
    )
    assert m["synthesis_version"] == "stage0_synthesis_v1"


# ---------------------------------------------------------------------------
# 10. Duplicate window ID detection (STOPPING)
# ---------------------------------------------------------------------------

def test_duplicate_window_id_detected(tmp_path):
    source = "fake_source"
    windows = [_fake_window(source, 0), _fake_window(source, 0)]  # same idx -> same window_id
    cache = {"manifest_kind": "fake", "windows": windows}
    compact_index = {"windows": [
        {"window_id": w["window_id"], "content_sha256": w["content_sha256"]} for w in windows
    ]}
    campaign_freeze = _fake_campaign_freeze(source, windows)

    paths = _write_fake_input_files(tmp_path, cache, compact_index, campaign_freeze)
    with _patched_expected_hashes(paths):
        with pytest.raises(build_mod.HashMismatchError, match="duplicate window_id"):
            build_mod.load_and_verify_inputs(
                cache_path=paths["cache"], compact_index_path=paths["compact_index"],
                campaign_freeze_path=paths["campaign_freeze"], case_selection_path=paths["case_selection"],
                calibration_manifest_path=paths["calibration_manifest"],
            )


# ---------------------------------------------------------------------------
# 11. Missing-window failure (window in campaign but absent from cache)
# ---------------------------------------------------------------------------

def test_missing_window_detected(tmp_path):
    source = "fake_source"
    windows = [_fake_window(source, 0), _fake_window(source, 1)]
    cache = {"manifest_kind": "fake", "windows": windows[:1]}  # drop window 1 from the cache
    compact_index = {"windows": [
        {"window_id": w["window_id"], "content_sha256": w["content_sha256"]} for w in windows
    ]}
    campaign_freeze = _fake_campaign_freeze(source, windows)  # campaign still expects both

    paths = _write_fake_input_files(tmp_path, cache, compact_index, campaign_freeze)
    with _patched_expected_hashes(paths):
        with pytest.raises(build_mod.HashMismatchError, match="window ID set mismatch"):
            build_mod.load_and_verify_inputs(
                cache_path=paths["cache"], compact_index_path=paths["compact_index"],
                campaign_freeze_path=paths["campaign_freeze"], case_selection_path=paths["case_selection"],
                calibration_manifest_path=paths["calibration_manifest"],
            )


# ---------------------------------------------------------------------------
# 12. Wrong-cache-hash / cross-artifact hash mismatch failure
# ---------------------------------------------------------------------------

def test_wrong_content_hash_detected(tmp_path):
    source = "fake_source"
    windows = [_fake_window(source, 0)]
    cache = {"manifest_kind": "fake", "windows": windows}
    compact_index = {"windows": [
        {"window_id": windows[0]["window_id"], "content_sha256": "f" * 64}  # deliberately wrong
    ]}
    campaign_freeze = _fake_campaign_freeze(source, windows)

    paths = _write_fake_input_files(tmp_path, cache, compact_index, campaign_freeze)
    with _patched_expected_hashes(paths):
        with pytest.raises(build_mod.HashMismatchError, match="compact index content_sha256 mismatch"):
            build_mod.load_and_verify_inputs(
                cache_path=paths["cache"], compact_index_path=paths["compact_index"],
                campaign_freeze_path=paths["campaign_freeze"], case_selection_path=paths["case_selection"],
                calibration_manifest_path=paths["calibration_manifest"],
            )


def test_frozen_file_hash_mismatch_stops_before_reading_cache(tmp_path):
    """A tampered/unexpected campaign_freeze.json (or any of the four
    hash-gated files) must STOP before the (expensive, 52MB) cache is even
    read -- not silently proceed."""
    source = "fake_source"
    windows = [_fake_window(source, 0)]
    cache = {"manifest_kind": "fake", "windows": windows}
    compact_index = {"windows": [
        {"window_id": windows[0]["window_id"], "content_sha256": windows[0]["content_sha256"]}
    ]}
    campaign_freeze = _fake_campaign_freeze(source, windows)
    paths = _write_fake_input_files(tmp_path, cache, compact_index, campaign_freeze)

    # Patch every EXPECTED_* EXCEPT campaign freeze, so only that one is wrong.
    orig = {
        "EXPECTED_COMPACT_INDEX_SHA256": build_mod.EXPECTED_COMPACT_INDEX_SHA256,
        "EXPECTED_CAMPAIGN_FREEZE_SHA256": build_mod.EXPECTED_CAMPAIGN_FREEZE_SHA256,
        "EXPECTED_CASE_SELECTION_SHA256": build_mod.EXPECTED_CASE_SELECTION_SHA256,
        "EXPECTED_CALIBRATION_MANIFEST_SHA256": build_mod.EXPECTED_CALIBRATION_MANIFEST_SHA256,
    }
    try:
        build_mod.EXPECTED_COMPACT_INDEX_SHA256 = build_mod._sha256_file(paths["compact_index"])
        build_mod.EXPECTED_CASE_SELECTION_SHA256 = build_mod._sha256_file(paths["case_selection"])
        build_mod.EXPECTED_CALIBRATION_MANIFEST_SHA256 = build_mod._sha256_file(paths["calibration_manifest"])
        build_mod.EXPECTED_CAMPAIGN_FREEZE_SHA256 = "0" * 64  # deliberately wrong
        with pytest.raises(build_mod.HashMismatchError, match="campaign freeze hash mismatch"):
            build_mod.load_and_verify_inputs(
                cache_path=paths["cache"], compact_index_path=paths["compact_index"],
                campaign_freeze_path=paths["campaign_freeze"], case_selection_path=paths["case_selection"],
                calibration_manifest_path=paths["calibration_manifest"],
            )
    finally:
        for k, v in orig.items():
            setattr(build_mod, k, v)


# ---------------------------------------------------------------------------
# 13. Policy-field leakage detection (validator)
# ---------------------------------------------------------------------------

def test_validator_detects_policy_field_leakage():
    source = "fake_source"
    cache = _fake_cache(source, n_windows=FAKE_N_WINDOWS)
    campaign_freeze = _fake_campaign_freeze(source, cache["windows"])
    m = build_mod.build_source_manifest(
        source, cache=cache, campaign_freeze=campaign_freeze, tokenizer=_FakeTokenizer(),
        tokenizer_name="fake", generation_code_sha="fixed", verify_prompts=False,
    )
    m["windows"][0]["requests"][0]["policy_id"] = "vllm_faithful"  # inject leakage
    result = validate_mod.validate_source_manifest(source, m, cache=cache, campaign_freeze=campaign_freeze)
    assert result["passed"] is False
    assert any("policy field leakage" in p for p in result["problems"])


# ---------------------------------------------------------------------------
# 14. Provenance/hash mismatch failure (validator)
# ---------------------------------------------------------------------------

def test_validator_detects_provenance_hash_mismatch():
    source = "fake_source"
    cache = _fake_cache(source, n_windows=FAKE_N_WINDOWS)
    campaign_freeze = _fake_campaign_freeze(source, cache["windows"])
    m = build_mod.build_source_manifest(
        source, cache=cache, campaign_freeze=campaign_freeze, tokenizer=_FakeTokenizer(),
        tokenizer_name="fake", generation_code_sha="fixed", verify_prompts=False,
    )
    m["windows"][0]["content_sha256"] = "deadbeef" * 8
    result = validate_mod.validate_source_manifest(source, m, cache=cache, campaign_freeze=campaign_freeze)
    assert result["passed"] is False
    assert any("content_sha256 mismatch vs cache" in p for p in result["problems"])


# ---------------------------------------------------------------------------
# helpers for the STOPPING-path tests
# ---------------------------------------------------------------------------

def _write_fake_input_files(tmp_path, cache, compact_index, campaign_freeze):
    paths = {
        "cache": tmp_path / "cache.json",
        "compact_index": tmp_path / "compact_index.json",
        "campaign_freeze": tmp_path / "campaign_freeze.json",
        "case_selection": tmp_path / "case_selection.json",
        "calibration_manifest": tmp_path / "calibration_manifest.json",
    }
    paths["cache"].write_text(json.dumps(cache))
    paths["compact_index"].write_text(json.dumps(compact_index))
    paths["campaign_freeze"].write_text(json.dumps(campaign_freeze))
    paths["case_selection"].write_text(json.dumps({"fake": True}))
    paths["calibration_manifest"].write_text(json.dumps({"fake": True}))
    return paths


class _patched_expected_hashes:
    """Context manager: point EXPECTED_*_SHA256 at the fabricated fixture
    files' real hashes, so load_and_verify_inputs's outer file-hash gate
    passes and the inner (cache/window-level) checks under test actually
    run."""

    def __init__(self, paths):
        self.paths = paths
        self.orig = {}

    def __enter__(self):
        self.orig = {
            "EXPECTED_COMPACT_INDEX_SHA256": build_mod.EXPECTED_COMPACT_INDEX_SHA256,
            "EXPECTED_CAMPAIGN_FREEZE_SHA256": build_mod.EXPECTED_CAMPAIGN_FREEZE_SHA256,
            "EXPECTED_CASE_SELECTION_SHA256": build_mod.EXPECTED_CASE_SELECTION_SHA256,
            "EXPECTED_CALIBRATION_MANIFEST_SHA256": build_mod.EXPECTED_CALIBRATION_MANIFEST_SHA256,
        }
        build_mod.EXPECTED_COMPACT_INDEX_SHA256 = build_mod._sha256_file(self.paths["compact_index"])
        build_mod.EXPECTED_CAMPAIGN_FREEZE_SHA256 = build_mod._sha256_file(self.paths["campaign_freeze"])
        build_mod.EXPECTED_CASE_SELECTION_SHA256 = build_mod._sha256_file(self.paths["case_selection"])
        build_mod.EXPECTED_CALIBRATION_MANIFEST_SHA256 = build_mod._sha256_file(self.paths["calibration_manifest"])
        return self

    def __exit__(self, *exc):
        for k, v in self.orig.items():
            setattr(build_mod, k, v)
