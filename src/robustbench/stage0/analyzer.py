"""Stage-0 frozen five-criterion GO/NO-GO analyzer (section C).

Encodes EXACTLY the five criteria in
docs/STAGE0_DISCRIMINABILITY_PROTOCOL.md's "GO criteria" section, applied
to a completed 1,080-cell (or any complete) matrix. Two genuine gaps in
the frozen protocol text are identified and resolved here with the
NARROWEST objective formalization possible -- documented, not silently
frozen (see `UNDERSPECIFIED_DEFINITIONS` and each criterion's docstring):

1. Criterion 3 ("universal overload/collapse... completion_fraction
   statistically indistinguishable from 0"): with only 2 DETERMINISTIC
   verification repetitions per cell (not independent statistical
   samples -- docs/STAGE0_DISCRIMINABILITY_PROTOCOL.md's own repetition
   rationale), no legitimate statistical test can be run. Resolved as
   `completion_fraction == 0.0` exactly (0 of `window_size` requests
   completed) -- the narrowest, most literal reading, consistent with the
   same discreteness argument used in
   docs/STAGE0_LOAD_CALIBRATION_AUDIT_20260901.md.
2. Criterion 4 ("range... exceeds 10% of the cell's minimum value"): the
   minimum value can legitimately be exactly 0 (e.g. `slo_violation_rate`
   of 0 for a well-performing policy at low load) making the ratio
   undefined. Resolved as: if `min == 0`, the cell qualifies iff
   `range > 0` (any separation from an exact-zero floor counts as
   qualifying variation; `range == 0` when `min == 0` means every policy
   scored identically at the floor, which does not qualify).

Never invents a threshold after inspecting a real Stage-0 outcome -- this
module was tested exclusively against synthetic/fixture matrices before
being pointed at anything Wulver-generated for real analysis.
"""
from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
from typing import Optional

from .cell import STAGE0_LOAD_REGIONS, STAGE0_POLICIES

TIE_TOLERANCE = 1e-6
CRITERION_1_THRESHOLD = 0.30
CRITERION_2_THRESHOLD = 0.50
CRITERION_4_RELATIVE_RANGE_THRESHOLD = 0.10
CRITERION_4_NON_TIED_FRACTION_THRESHOLD = 0.20
CRITERION_5_MIN_SHARE = 0.15
CRITERION_5_MAX_SHARE = 0.70

UNDERSPECIFIED_DEFINITIONS = [
    {
        "criterion": 3,
        "gap": "'completion_fraction statistically indistinguishable from 0' has no "
               "executable statistical-test definition, and only 2 deterministic "
               "verification repetitions exist per cell (not independent samples), "
               "so no real statistical test is possible.",
        "resolution": "completion_fraction == 0.0 exactly (narrowest literal reading).",
    },
    {
        "criterion": 4,
        "gap": "range/min is undefined when min == 0 (a legitimate value, e.g. "
               "slo_violation_rate=0 at low load).",
        "resolution": "if min == 0: qualifies iff range > 0 (any separation from an "
                       "exact-zero floor counts; identical zeros do not).",
    },
]


def _relative_range_qualifies(values: list[float]) -> bool:
    lo, hi = min(values), max(values)
    rng = hi - lo
    if lo == 0:
        return rng > 0
    return (rng / lo) > CRITERION_4_RELATIVE_RANGE_THRESHOLD


@dataclass
class CriterionResult:
    criterion: int
    name: str
    definition: str
    threshold: str
    numerator: float
    denominator: float
    observed_value: float
    passed: bool


def _group_key(r: dict) -> tuple:
    return (r["source_family"], r["window_id"], r["load_region"])


def _verify_repetition_consistency(cells: list[dict]) -> list[str]:
    """Data-integrity check: repetitions are deterministic verification
    reruns, so rep0 and rep1 of the same (source,window,load_region,policy)
    MUST agree. Returns a list of mismatch descriptions (empty = all
    consistent)."""
    by_combo: dict[tuple, dict[int, dict]] = {}
    for r in cells:
        key = (r["source_family"], r["window_id"], r["load_region"], r["policy_id"])
        by_combo.setdefault(key, {})[r["repetition"]] = r
    problems = []
    for key, reps in by_combo.items():
        if 0 in reps and 1 in reps and reps[0].get("success") and reps[1].get("success"):
            a = reps[0]["arrival_normalized_weighted_goodput"]
            b = reps[1]["arrival_normalized_weighted_goodput"]
            if a is None or b is None or abs(a - b) > 1e-9:
                problems.append(f"{key}: rep0 ANWG={a} != rep1 ANWG={b}")
    return problems


def analyze_stage0_matrix(cells: list[dict], *, primary_metric: str = "arrival_normalized_weighted_goodput") -> dict:
    """`cells` is a flat list of CellResult dicts (schema.py). Expects the
    matrix to already be validated complete (harness.py `validate`) --
    this function does not itself check for missing/duplicate cells, it
    only computes the 5 criteria over whatever it is given (so it can also
    run on deliberately incomplete synthetic matrices for adversarial
    testing, per section F)."""
    rep_problems = _verify_repetition_consistency(cells)

    successful = [c for c in cells if c.get("success")]
    by_group: dict[tuple, list[dict]] = {}
    for r in successful:
        by_group.setdefault(_group_key(r), []).append(r)

    # ---- Criterion 1: nontrivial pairwise policy differences ----
    # "not all equal within tolerance 1e-6" per (source,window,load_region) triple.
    n_groups_total = len(by_group)
    non_tied_groups: set[tuple] = set()
    for key, rows in by_group.items():
        # dedupe by policy (use rep0 if present, else whatever's there)
        by_policy: dict[str, float] = {}
        for r in sorted(rows, key=lambda x: x["repetition"]):
            if r["policy_id"] not in by_policy:
                by_policy[r["policy_id"]] = r[primary_metric]
        vals = [v for v in by_policy.values() if v is not None]
        if len(vals) >= 2 and (max(vals) - min(vals)) > TIE_TOLERANCE:
            non_tied_groups.add(key)
    c1_value = len(non_tied_groups) / n_groups_total if n_groups_total else 0.0
    c1 = CriterionResult(
        criterion=1, name="Nontrivial pairwise policy differences",
        definition=f"fraction of (source,window,load_region) cells where the {len(STAGE0_POLICIES)} "
                   f"policies' {primary_metric} are not all equal within tolerance {TIE_TOLERANCE}",
        threshold=f">= {CRITERION_1_THRESHOLD:.0%}",
        numerator=len(non_tied_groups), denominator=n_groups_total, observed_value=c1_value,
        passed=c1_value >= CRITERION_1_THRESHOLD,
    )

    # ---- Criterion 2: adequate fraction of non-tied (source,window) pairs ----
    sw_pairs: set[tuple] = {(k[0], k[1]) for k in by_group}
    non_tied_sw_pairs = {(k[0], k[1]) for k in non_tied_groups}
    c2_value = len(non_tied_sw_pairs) / len(sw_pairs) if sw_pairs else 0.0
    c2 = CriterionResult(
        criterion=2, name="Adequate fraction of non-tied windows",
        definition="fraction of (source,window) pairs with a non-tied result in >=1 of 3 load regions",
        threshold=f">= {CRITERION_2_THRESHOLD:.0%}",
        numerator=len(non_tied_sw_pairs), denominator=len(sw_pairs), observed_value=c2_value,
        passed=c2_value >= CRITERION_2_THRESHOLD,
    )

    # ---- Criterion 3: no universal collapse ----
    # See module docstring for the resolved "statistically indistinguishable from 0" gap.
    n_degenerate = 0
    for key, rows in by_group.items():
        by_policy_cf: dict[str, float] = {}
        for r in sorted(rows, key=lambda x: x["repetition"]):
            if r["policy_id"] not in by_policy_cf:
                by_policy_cf[r["policy_id"]] = r["completion_fraction"]
        vals = [v for v in by_policy_cf.values() if v is not None]
        if len(vals) < len(STAGE0_POLICIES):
            continue
        is_underload = all(v == 1.0 for v in vals)
        is_collapse = all(v == 0.0 for v in vals)
        if is_underload or is_collapse:
            n_degenerate += 1
    c3_value = n_degenerate / n_groups_total if n_groups_total else 0.0
    c3 = CriterionResult(
        criterion=3, name="No universal collapse",
        definition="NOT all (source,window,load_region) cells are trivial-underload "
                   "(completion_fraction==1.0 for all policies) or universal-collapse "
                   "(completion_fraction==0.0 for all policies, resolved definition -- see module docstring)",
        threshold="degenerate_fraction < 100%",
        numerator=n_degenerate, denominator=n_groups_total, observed_value=c3_value,
        passed=n_degenerate < n_groups_total if n_groups_total else False,
    )

    # ---- Criterion 4: meaningful metric variation among non-tied cells ----
    n_meaningful = 0
    for key in non_tied_groups:
        rows = by_group[key]
        by_policy_metrics: dict[str, dict] = {}
        for r in sorted(rows, key=lambda x: x["repetition"]):
            if r["policy_id"] not in by_policy_metrics:
                by_policy_metrics[r["policy_id"]] = r
        p95s = [r["p95_latency"] for r in by_policy_metrics.values() if r.get("p95_latency") is not None]
        svrs = [r["slo_violation_rate"] for r in by_policy_metrics.values() if r.get("slo_violation_rate") is not None]
        qualifies = (len(p95s) >= 2 and _relative_range_qualifies(p95s)) or \
                    (len(svrs) >= 2 and _relative_range_qualifies(svrs))
        if qualifies:
            n_meaningful += 1
    c4_value = n_meaningful / len(non_tied_groups) if non_tied_groups else 0.0
    c4 = CriterionResult(
        criterion=4, name="Meaningful metric variation",
        definition="fraction of non-tied cells where p95_latency OR slo_violation_rate's "
                   "range exceeds 10% of the cell's minimum value (resolved zero-denominator "
                   "rule -- see module docstring)",
        threshold=f">= {CRITERION_4_NON_TIED_FRACTION_THRESHOLD:.0%}",
        numerator=n_meaningful, denominator=len(non_tied_groups), observed_value=c4_value,
        passed=c4_value >= CRITERION_4_NON_TIED_FRACTION_THRESHOLD,
    )

    # ---- Criterion 5: no single source dominates ----
    from collections import Counter
    source_counts = Counter(k[0] for k in non_tied_groups)
    total_non_tied = len(non_tied_groups)
    per_source_shares = {s: (source_counts.get(s, 0) / total_non_tied if total_non_tied else 0.0)
                          for s in {k[0] for k in by_group}}
    c5_passed = total_non_tied > 0 and all(
        CRITERION_5_MIN_SHARE <= share <= CRITERION_5_MAX_SHARE for share in per_source_shares.values()
    )
    c5 = CriterionResult(
        criterion=5, name="No single source dominates",
        definition="each source contributes between 15% and 70% of all non-tied "
                   "(source,window,load_region) cells",
        threshold=f"{CRITERION_5_MIN_SHARE:.0%} <= share <= {CRITERION_5_MAX_SHARE:.0%} for every source",
        numerator=min(per_source_shares.values()) if per_source_shares else 0.0,
        denominator=max(per_source_shares.values()) if per_source_shares else 0.0,
        observed_value=0.0,  # multi-valued; see per_source_shares
        passed=c5_passed,
    )

    criteria = [c1, c2, c3, c4, c5]
    all_pass = all(c.passed for c in criteria)
    n_failed_cells = len(cells) - len(successful)

    return {
        "underspecified_definitions_resolved": UNDERSPECIFIED_DEFINITIONS,
        "repetition_consistency_problems": rep_problems,
        "n_cells_total": len(cells),
        "n_cells_successful": len(successful),
        "n_cells_failed": n_failed_cells,
        "n_groups_total": n_groups_total,
        "criteria": [
            {"criterion": c.criterion, "name": c.name, "definition": c.definition,
             "threshold": c.threshold, "numerator": c.numerator, "denominator": c.denominator,
             "observed_value": c.observed_value, "passed": c.passed}
            for c in criteria
        ],
        "criterion_5_per_source_shares": per_source_shares,
        "verdict": "STAGE0_GO" if (all_pass and n_failed_cells == 0 and not rep_problems) else "STAGE0_NO_GO",
        "verdict_blocked_by_incomplete_matrix": n_failed_cells > 0 or bool(rep_problems),
    }
