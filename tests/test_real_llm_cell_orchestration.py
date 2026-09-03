import pytest

from robustbench.real_llm.cell_orchestration import (
    CellKey,
    CompletedLedger,
    RunUnit,
    abba_order,
    deterministic_random_order,
    expand_cells_to_run_units,
    filter_pending,
    unique_output_namespace,
)


FIXTURE_CELLS = [
    CellKey("fifo", "fam_a", "PRE_KNEE"),
    CellKey("weighted_fair_share", "fam_a", "PRE_KNEE"),
    CellKey("fifo", "fam_b", "KNEE"),
]


def test_expand_cells_to_run_units_count():
    units = expand_cells_to_run_units(FIXTURE_CELLS, repetitions=3)
    assert len(units) == len(FIXTURE_CELLS) * 3


def test_expand_cells_rejects_zero_repetitions():
    with pytest.raises(ValueError):
        expand_cells_to_run_units(FIXTURE_CELLS, repetitions=0)


def test_expand_cells_rejects_duplicate_cell():
    dup = FIXTURE_CELLS + [CellKey("fifo", "fam_a", "PRE_KNEE")]
    with pytest.raises(ValueError, match="duplicate cell"):
        expand_cells_to_run_units(dup, repetitions=1)


def test_run_id_is_order_independent_and_unique():
    units = expand_cells_to_run_units(FIXTURE_CELLS, repetitions=2)
    ids = [u.run_id() for u in units]
    assert len(ids) == len(set(ids))
    # run_id depends only on (cell, repetition), not position in the list
    shuffled = list(reversed(units))
    assert {u.run_id() for u in units} == {u.run_id() for u in shuffled}


def test_deterministic_random_order_is_reproducible():
    units = expand_cells_to_run_units(FIXTURE_CELLS, repetitions=4)
    order_a = deterministic_random_order(units, seed=42)
    order_b = deterministic_random_order(units, seed=42)
    assert [u.run_id() for u in order_a] == [u.run_id() for u in order_b]


def test_deterministic_random_order_differs_across_seeds():
    units = expand_cells_to_run_units(FIXTURE_CELLS, repetitions=6)
    order_a = deterministic_random_order(units, seed=1)
    order_b = deterministic_random_order(units, seed=2)
    assert [u.run_id() for u in order_a] != [u.run_id() for u in order_b]


def test_deterministic_random_order_is_a_permutation():
    units = expand_cells_to_run_units(FIXTURE_CELLS, repetitions=3)
    order = deterministic_random_order(units, seed=7)
    assert {u.run_id() for u in order} == {u.run_id() for u in units}


def test_abba_order_alternates_pair_start_by_repetition():
    cells = [CellKey("fifo", "fam_a", "PRE_KNEE"), CellKey("edf", "fam_a", "PRE_KNEE")]
    units = expand_cells_to_run_units(cells, repetitions=2)
    order = abba_order(units)
    # Schedulers are sorted for reproducibility regardless of input order:
    # A="edf", B="fifo". rep 0 group: A then B; rep 1 group: B then A.
    seq = [(u.cell.scheduler, u.repetition) for u in order]
    assert seq == [("edf", 0), ("fifo", 0), ("fifo", 1), ("edf", 1)]


def test_completed_ledger_records_and_persists(tmp_path):
    path = tmp_path / "ledger.jsonl"
    ledger = CompletedLedger(path)
    assert not ledger.is_completed("run_a")
    ledger.record("run_a", "success")
    assert ledger.is_completed("run_a")

    # reload from disk
    ledger2 = CompletedLedger(path)
    assert ledger2.is_completed("run_a")


def test_completed_ledger_does_not_mark_failed_as_completed(tmp_path):
    ledger = CompletedLedger(tmp_path / "ledger.jsonl")
    ledger.record("run_x", "error")
    assert not ledger.is_completed("run_x")


def test_filter_pending_skips_only_successful(tmp_path):
    units = expand_cells_to_run_units(FIXTURE_CELLS, repetitions=1)
    ledger = CompletedLedger(tmp_path / "ledger.jsonl")
    ledger.record(units[0].run_id(), "success")
    ledger.record(units[1].run_id(), "error")

    pending = filter_pending(units, ledger)
    pending_ids = {u.run_id() for u in pending}
    assert units[0].run_id() not in pending_ids  # successful -> skipped
    assert units[1].run_id() in pending_ids  # errored -> retried
    assert units[2].run_id() in pending_ids  # never run -> included


def test_unique_output_namespace_no_collision_across_reps(tmp_path):
    cell = CellKey("fifo", "fam_a", "PRE_KNEE")
    ns0 = unique_output_namespace(tmp_path, RunUnit(cell, 0).run_id())
    ns1 = unique_output_namespace(tmp_path, RunUnit(cell, 1).run_id())
    assert ns0 != ns1
    assert ns0.exists() and ns1.exists()
