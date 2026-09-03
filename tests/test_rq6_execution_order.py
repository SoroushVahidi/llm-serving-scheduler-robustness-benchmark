from __future__ import annotations

import importlib.util
from pathlib import Path

SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "real_vllm" / "build_rq6_execution_order.py"
_spec = importlib.util.spec_from_file_location("build_rq6_execution_order", SCRIPT_PATH)
_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_module)

build_execution_order = _module.build_execution_order


def test_deterministic_same_seed_same_repetitions():
    a = build_execution_order(repetitions=10, seed=20260902)
    b = build_execution_order(repetitions=10, seed=20260902)
    assert a == b


def test_different_seed_changes_order_not_membership():
    a = build_execution_order(repetitions=4, seed=1)
    b = build_execution_order(repetitions=4, seed=2)
    a_ids = [r["run_id"] for r in a["order"]]
    b_ids = [r["run_id"] for r in b["order"]]
    assert a_ids != b_ids
    assert set(a_ids) == set(b_ids)


def test_every_run_unit_present_exactly_once():
    manifest = build_execution_order(repetitions=10, seed=20260902)
    ids = [r["run_id"] for r in manifest["order"]]
    assert len(ids) == len(set(ids))
    assert manifest["total_run_units"] == 3 * 2 * 10  # 3 sources * 2 policies * 10 reps


def test_policy_order_alternates_by_repetition_parity_within_pairs():
    manifest = build_execution_order(repetitions=6, seed=20260902)
    rows = manifest["order"]
    # every adjacent pair of rows must belong to the same (source, repetition)
    # and cover both policies exactly once
    for i in range(0, len(rows), 2):
        first, second = rows[i], rows[i + 1]
        assert first["source"] == second["source"]
        assert first["repetition"] == second["repetition"]
        assert {first["policy"], second["policy"]} == {"slai_faithful", "vllm_faithful"}


def test_no_policy_always_scheduled_first():
    manifest = build_execution_order(repetitions=10, seed=20260902)
    rows = manifest["order"]
    first_of_pair = [rows[i]["policy"] for i in range(0, len(rows), 2)]
    assert "slai_faithful" in first_of_pair
    assert "vllm_faithful" in first_of_pair
