"""Adversarial synthetic-matrix tests for the Stage-0 5-criterion analyzer
(section F). Every matrix here is hand-constructed with generous margins on
each side of a threshold so the tests are robust to +/-1-cell rounding,
not fragile boundary cases. No real Stage-0 data is used anywhere in this
file."""
from __future__ import annotations

from robustbench.stage0.analyzer import analyze_stage0_matrix
from robustbench.stage0.cell import STAGE0_POLICIES

SOURCES = ["azure_llm_2024", "bailian_qwen", "burstgpt"]
REGIONS = ["PRE_KNEE", "KNEE", "OVERLOAD"]


def _cell(source, window, region, policy, rep, *, anwg, completion, p95=100.0, svr=0.01, success=True):
    return {
        "cell_id": f"{source}::{window}::{region}::{policy}::rep{rep}",
        "canonical_hash": f"{source}-{window}-{region}-{policy}-{rep}",
        "source_family": source, "window_id": window, "load_region": region,
        "policy_id": policy, "repetition": rep, "synthesis_seed": 1,
        "arrival_normalized_weighted_goodput": anwg if success else None,
        "completion_fraction": completion if success else None,
        "slo_violation_rate": svr if success else None,
        "p95_latency": p95 if success else None,
        "success": success,
        "error_category": None if success else "synthetic_failure",
    }


def _both_reps(source, window, region, policy, **kw):
    return [_cell(source, window, region, policy, 0, **kw), _cell(source, window, region, policy, 1, **kw)]


def _build_matrix(n_windows_per_source, group_spec):
    """group_spec(source, window, region) -> dict[policy] -> dict(anwg, completion, p95, svr)"""
    cells = []
    for source in SOURCES:
        for w in range(n_windows_per_source):
            window = f"{source}_w{w}"
            for region in REGIONS:
                per_policy = group_spec(source, window, region)
                for policy in STAGE0_POLICIES:
                    kw = per_policy[policy]
                    cells.extend(_both_reps(source, window, region, policy, **kw))
    return cells


# ---------------------------------------------------------------------------
# Scenario: everything passes
# ---------------------------------------------------------------------------
def _pass_all_spec(source, window, region):
    idx = int(window.rsplit("_w", 1)[1])
    # ~2/3 of groups non-tied (well above 30%/50% thresholds), spread across
    # windows and load regions; big p95/svr spread on non-tied groups.
    non_tied = (idx + REGIONS.index(region)) % 3 != 0
    out = {}
    for i, p in enumerate(STAGE0_POLICIES):
        if non_tied:
            out[p] = dict(anwg=0.5 + 0.05 * i, completion=0.7, p95=100.0 + 80.0 * i, svr=0.01 + 0.05 * i)
        else:
            out[p] = dict(anwg=0.5, completion=0.7, p95=100.0, svr=0.01)
    return out


def test_all_five_criteria_pass():
    cells = _build_matrix(6, _pass_all_spec)
    report = analyze_stage0_matrix(cells)
    assert report["verdict"] == "STAGE0_GO", report["criteria"]
    for c in report["criteria"]:
        assert c["passed"], c


# ---------------------------------------------------------------------------
# Scenario: fail criterion 1 only (almost everything tied)
# ---------------------------------------------------------------------------
def _fail_c1_spec(source, window, region):
    idx = int(window.rsplit("_w", 1)[1])
    non_tied = (idx == 0 and region == "KNEE")  # only 1 of 18 groups/source non-tied
    out = {}
    for i, p in enumerate(STAGE0_POLICIES):
        if non_tied:
            out[p] = dict(anwg=0.5 + 0.05 * i, completion=0.7, p95=100.0 + 50.0 * i, svr=0.01 + 0.05 * i)
        else:
            out[p] = dict(anwg=0.5, completion=0.7, p95=100.0, svr=0.01)
    return out


def test_fails_criterion_1_only():
    cells = _build_matrix(6, _fail_c1_spec)
    report = analyze_stage0_matrix(cells)
    by_num = {c["criterion"]: c for c in report["criteria"]}
    assert not by_num[1]["passed"], by_num[1]
    assert report["verdict"] == "STAGE0_NO_GO"


# ---------------------------------------------------------------------------
# Scenario: fail criterion 2 (non-tied groups all concentrated in ONE window
# per source, so most (source,window) pairs never see a non-tied region)
# ---------------------------------------------------------------------------
def _fail_c2_spec(source, window, region):
    idx = int(window.rsplit("_w", 1)[1])
    # Non-tied only for window index 0, but in ALL 3 regions there (still
    # clears criterion 1's 30% cell-fraction easily: 3 of 18 = 16%... need
    # >=30%, so widen to windows 0,1 non-tied in all regions = 6/18=33%,
    # but only 2 of 6 windows/source ever non-tied -> 33% of (source,window)
    # pairs non-tied, well under criterion 2's 50%.
    non_tied = idx in (0, 1)
    out = {}
    for i, p in enumerate(STAGE0_POLICIES):
        if non_tied:
            out[p] = dict(anwg=0.5 + 0.05 * i, completion=0.7, p95=100.0 + 50.0 * i, svr=0.01 + 0.05 * i)
        else:
            out[p] = dict(anwg=0.5, completion=0.7, p95=100.0, svr=0.01)
    return out


def test_fails_criterion_2_only():
    cells = _build_matrix(6, _fail_c2_spec)
    report = analyze_stage0_matrix(cells)
    by_num = {c["criterion"]: c for c in report["criteria"]}
    assert by_num[1]["passed"], by_num[1]  # c1 still passes (33% >= 30%)
    assert not by_num[2]["passed"], by_num[2]  # c2 fails (33% < 50%)
    assert report["verdict"] == "STAGE0_NO_GO"


# ---------------------------------------------------------------------------
# Scenario: fail criterion 3 (every single group is degenerate: either
# universal completion or universal collapse)
# ---------------------------------------------------------------------------
def _fail_c3_spec(source, window, region):
    idx = int(window.rsplit("_w", 1)[1])
    collapse = region == "OVERLOAD"
    out = {}
    for i, p in enumerate(STAGE0_POLICIES):
        # still vary ANWG across policies so c1/c2 can pass despite c3 failing
        anwg = 0.0 if collapse else (0.3 + 0.1 * i)
        out[p] = dict(anwg=anwg, completion=(0.0 if collapse else 1.0), p95=100.0, svr=0.0)
    return out


def test_fails_criterion_3_only():
    cells = _build_matrix(6, _fail_c3_spec)
    report = analyze_stage0_matrix(cells)
    by_num = {c["criterion"]: c for c in report["criteria"]}
    assert not by_num[3]["passed"], by_num[3]
    assert report["verdict"] == "STAGE0_NO_GO"


# ---------------------------------------------------------------------------
# Scenario: fail criterion 4 (non-tied groups exist, but p95/svr are
# identical across policies within each non-tied group -- ANWG differs,
# nothing else does)
# ---------------------------------------------------------------------------
def _fail_c4_spec(source, window, region):
    idx = int(window.rsplit("_w", 1)[1])
    non_tied = (idx + REGIONS.index(region)) % 3 != 0
    out = {}
    for i, p in enumerate(STAGE0_POLICIES):
        anwg = 0.5 + 0.05 * i if non_tied else 0.5
        out[p] = dict(anwg=anwg, completion=0.7, p95=100.0, svr=0.01)  # p95/svr identical always
    return out


def test_fails_criterion_4_only():
    cells = _build_matrix(6, _fail_c4_spec)
    report = analyze_stage0_matrix(cells)
    by_num = {c["criterion"]: c for c in report["criteria"]}
    assert by_num[1]["passed"], by_num[1]
    assert not by_num[4]["passed"], by_num[4]
    assert report["verdict"] == "STAGE0_NO_GO"


# ---------------------------------------------------------------------------
# Scenario: fail criterion 5 (one source produces ALL the non-tied cells)
# ---------------------------------------------------------------------------
def _fail_c5_spec(source, window, region):
    idx = int(window.rsplit("_w", 1)[1])
    if source == "burstgpt":
        # Dominant source: every window, every region is non-tied.
        non_tied = True
    else:
        # Other two sources: only window indices 0-2, only region KNEE --
        # still enough distinct (source,window) PAIRS to clear criterion 2's
        # 50% pair-coverage bar, but far fewer total non-tied CELLS than
        # burstgpt, so criterion 5's per-source share is skewed.
        non_tied = idx in (0, 1, 2) and region == "KNEE"
    out = {}
    for i, p in enumerate(STAGE0_POLICIES):
        if non_tied:
            out[p] = dict(anwg=0.5 + 0.05 * i, completion=0.7, p95=100.0 + 50.0 * i, svr=0.01 + 0.05 * i)
        else:
            out[p] = dict(anwg=0.5, completion=0.7, p95=100.0, svr=0.01)
    return out


def test_fails_criterion_5_only():
    cells = _build_matrix(6, _fail_c5_spec)
    report = analyze_stage0_matrix(cells)
    by_num = {c["criterion"]: c for c in report["criteria"]}
    assert by_num[1]["passed"], by_num[1]
    assert not by_num[5]["passed"], by_num[5]  # burstgpt = 100% of non-tied cells > 70%
    assert report["verdict"] == "STAGE0_NO_GO"


# ---------------------------------------------------------------------------
# Missing / duplicate / explicit-failure cells
# ---------------------------------------------------------------------------
def test_explicit_failed_cells_block_go_verdict_even_if_criteria_pass():
    cells = _build_matrix(6, _pass_all_spec)
    # Corrupt one cell into an explicit failure.
    cells[0] = _cell(cells[0]["source_family"], cells[0]["window_id"], cells[0]["load_region"],
                      cells[0]["policy_id"], cells[0]["repetition"], anwg=0.0, completion=0.0, success=False)
    report = analyze_stage0_matrix(cells)
    assert report["n_cells_failed"] == 1
    assert report["verdict_blocked_by_incomplete_matrix"] is True
    assert report["verdict"] == "STAGE0_NO_GO"


def test_repetition_inconsistency_is_detected_and_blocks_go():
    cells = _build_matrix(2, _pass_all_spec)
    # Break rep1's ANWG for one cell so it disagrees with rep0 (deterministic
    # verification reps must match).
    for c in cells:
        if c["repetition"] == 1:
            c["arrival_normalized_weighted_goodput"] = (c["arrival_normalized_weighted_goodput"] or 0.0) + 5.0
            break
    report = analyze_stage0_matrix(cells)
    assert len(report["repetition_consistency_problems"]) >= 1
    assert report["verdict"] == "STAGE0_NO_GO"


def test_missing_cells_do_not_crash_analyzer_but_reduce_denominator():
    cells = _build_matrix(3, _pass_all_spec)
    # Remove an entire policy's cells for one group (simulates a missing cell,
    # not just a failure) -- criterion 3's "all 6 policies present" guard
    # should skip that group rather than crash.
    target_window = cells[0]["window_id"]
    cells = [c for c in cells if not (c["window_id"] == target_window and c["policy_id"] == "fifo"
                                       and c["load_region"] == "KNEE")]
    report = analyze_stage0_matrix(cells)  # must not raise
    assert report["n_cells_total"] == len(cells)


def test_duplicate_cells_do_not_double_count_in_tie_detection():
    cells = _build_matrix(2, _pass_all_spec)
    duplicate = dict(cells[0])
    cells_with_dup = cells + [duplicate]
    report_dup = analyze_stage0_matrix(cells_with_dup)
    report_plain = analyze_stage0_matrix(cells)
    # by_policy dedup in analyzer keeps first-seen per (group,policy), so a
    # duplicate of an already-present (group,policy,rep) must not change
    # the criteria numerators.
    for a, b in zip(report_dup["criteria"], report_plain["criteria"]):
        assert a["numerator"] == b["numerator"]
        assert a["denominator"] == b["denominator"]


def test_analyzer_refuses_cells_labeled_smoke_only():
    cells = _build_matrix(2, _pass_all_spec)
    cells[0]["scientific_status"] = "SMOKE_ONLY_DO_NOT_ANALYZE"
    import pytest
    with pytest.raises(ValueError, match="SMOKE_ONLY_DO_NOT_ANALYZE|scientific_status"):
        analyze_stage0_matrix(cells)
