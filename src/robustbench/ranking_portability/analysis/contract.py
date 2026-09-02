"""Frozen numeric/structural parameters for the Phase-12 post-campaign
analysis pipeline. Every value here is copied verbatim from a canonical
doc, never chosen by this module -- each constant's comment cites its
source so a future re-read of the docs can re-verify it did not drift.

This module contains NO logic and touches no data. It exists so every
analysis component imports the same frozen numbers instead of each
re-typing (and risking re-typo-ing) them.
"""
from __future__ import annotations

# --- Ranking analysis (docs/RANKING_PORTABILITY_ANALYSIS_PLAN.md §A) ---
# "top-k overlap (k in {1, 3} ... tightened from the existing plan's {3, 5})"
TOP_K_VALUES = (1, 3)
# "block-bootstrap CIs (>=2,000 resamples of windows within a source)"
BOOTSTRAP_RESAMPLES = 2000
BOOTSTRAP_CI_LEVEL = 0.95

# --- Pairwise reversal (docs/RANKING_PORTABILITY_ANALYSIS_PLAN.md §A) ---
# "the winning margin exceeds 10% of the losing policy's value on that
# metric (mirrors the already-frozen Criterion-4 relative-range rule,
# src/robustbench/stage0/analyzer.py::_relative_range_qualifies)"
REVERSAL_PRACTICAL_MARGIN_FRACTION = 0.10
# "the block-bootstrap CI on the sign of the difference excludes zero at
# the 95% level"
REVERSAL_CI_LEVEL = 0.95

# --- Sample complexity (docs/RANKING_PORTABILITY_ANALYSIS_PLAN.md §C,
# overriding docs/STATISTICAL_ANALYSIS_PLAN.md §F's illustrative
# "n in {5,10,20,40,...,full}" with the Phase-12-specific fixed ladder) ---
SAMPLE_COMPLEXITY_N_VALUES = (5, 10, 20, 30, 40)
SAMPLE_COMPLEXITY_DRAWS_PER_N = 500
# docs/STATISTICAL_ANALYSIS_PLAN.md §F: "the n at which this probability
# first exceeds a pre-registered threshold (0.9)"
SAMPLE_COMPLEXITY_RECOVERY_THRESHOLD = 0.9

# --- Multiple testing (docs/STATISTICAL_ANALYSIS_PLAN.md, "Multiple-
# testing correction") ---
# "Benjamini-Hochberg FDR control at q=0.05, applied per family"
FDR_Q = 0.05

# --- Metric contract (docs/RANKING_PORTABILITY_METRIC_DEFINITIONS.md).
# This is the canonical, later, Phase-12-specific metric list and is
# authoritative over docs/STATISTICAL_ANALYSIS_PLAN.md §E's older,
# pre-schema-freeze illustrative list (which additionally names "TPOT"
# and "p99 tail latency" -- neither field exists in
# RankingPortabilityCellResult / schema.py, so there is nothing to
# analyze for them; this is treated as the later, actually-implemented
# schema superseding an earlier aspirational list by omission, not as an
# unresolved conflict requiring a STOP). ---
ALWAYS_DEFINED_METRICS = (
    "arrival_normalized_weighted_goodput",
    "completion_fraction",
    "weighted_completion_fraction",
)
CONDITIONAL_ON_COMPLETION_METRICS = (
    "slo_violation_rate",
    "weighted_goodput",
    "mean_latency",
    "p95_latency",
    "request_throughput",
    "token_throughput",
)
CONDITIONAL_ON_OTHER_PRECONDITION_METRICS = ("mean_ttft", "p95_ttft")
ALL_RANKING_METRICS = (
    ALWAYS_DEFINED_METRICS
    + CONDITIONAL_ON_COMPLETION_METRICS
    + CONDITIONAL_ON_OTHER_PRECONDITION_METRICS
)
PRIMARY_METRIC = "arrival_normalized_weighted_goodput"

# --- Policy panel (docs/RANKING_PORTABILITY_POLICY_PANEL.md) ---
PRIMARY_POLICIES = (
    "fifo",
    "edf",
    "least_laxity_first",
    "estimated_service_time_first",
    "weighted_fair_share",
    "kv_constrained_online",
    "vllm_faithful",
    "vllm_chunked_prefill_faithful",
    "sarathi_faithful",
    "slai_faithful",
    "admission_control",
)
STYLE_APPROXIMATION_POLICIES = (
    "vllm_style_token_budget",
    "scorpio_style_slo_guard",
)
ALL_CAMPAIGN_POLICIES = PRIMARY_POLICIES + STYLE_APPROXIMATION_POLICIES

# Mechanism-family tags, copied from the "(letter)" concept codes in
# docs/RANKING_PORTABILITY_POLICY_PANEL.md's panel table. "slai_faithful"
# is documented as "(H)-adjacent", a distinct family from admission_control's
# "(H)" -- kept as its own key rather than merged, per that doc's own
# distinction.
POLICY_FAMILY = {
    "fifo": "A_ARRIVAL_ORDER",
    "edf": "B_DEADLINE_AWARE",
    "least_laxity_first": "C_SLACK_URGENCY",
    "estimated_service_time_first": "D_SERVICE_LENGTH",
    "weighted_fair_share": "I_FAIRNESS",
    "kv_constrained_online": "G_KV_MEMORY_PRESSURE",
    "vllm_faithful": "E_TOKEN_BUDGET_BATCHING",
    "vllm_chunked_prefill_faithful": "F_CHUNKED_PREFILL",
    "sarathi_faithful": "F_CHUNKED_PREFILL",
    "slai_faithful": "H_ADJACENT_SLO_AWARE",
    "admission_control": "H_ADMISSION_SLO_GUARD",
    "vllm_style_token_budget": "E_TOKEN_BUDGET_BATCHING",
    "scorpio_style_slo_guard": "H_ADMISSION_SLO_GUARD",
}

# --- Load regions (src/robustbench/ranking_portability/calibration.py
# REGION_SEQUENCE, 6-region Phase-12 grid) ---
SIX_REGION_GRID = ("LOW", "PRE_KNEE", "KNEE", "POST_KNEE", "OVERLOAD", "HIGH_PRESSURE")
# docs/RANKING_PORTABILITY_ANALYSIS_PLAN.md §F, "Load-calibration
# sensitivity ... original 4-region grid, LOW/PRE_KNEE/KNEE/OVERLOAD, as a
# subset of the 6-region grid"
FOUR_REGION_SUBSET = ("LOW", "PRE_KNEE", "KNEE", "OVERLOAD")

# --- Sources (src/robustbench/ranking_portability/phase12_campaign.py
# CAMPAIGN_SOURCES) ---
CAMPAIGN_SOURCES = ("burstgpt", "azure_llm_2024", "bailian_qwen")
WINDOWS_PER_SOURCE = 40
REPETITIONS = (0, 1)

EXPECTED_CAMPAIGN_CELL_COUNT = (
    len(CAMPAIGN_SOURCES) * WINDOWS_PER_SOURCE * len(SIX_REGION_GRID)
    * len(ALL_CAMPAIGN_POLICIES) * len(REPETITIONS)
)
assert EXPECTED_CAMPAIGN_CELL_COUNT == 18720, EXPECTED_CAMPAIGN_CELL_COUNT

# --- Temporal design (docs/RANKING_PORTABILITY_ANALYSIS_PLAN.md §D) ---
BURSTGPT_TEMPORAL_SPLIT_PRIMARY = "TERCILE"  # EARLY / MIDDLE / LATE
BURSTGPT_TEMPORAL_SPLIT_SENSITIVITY = "BISECT"
BAILIAN_TEMPORAL_LABEL = "RELATIVE_CHRONOLOGY_ONLY"
AZURE_CALENDAR_TEMPORAL_SOURCE = "azure_llm_2024"

# --- Robustness plan (docs/RANKING_PORTABILITY_ANALYSIS_PLAN.md §F) ---
ROBUSTNESS_COMPONENTS = (
    "PRIMARY_ONLY",
    "LEAVE_ONE_SOURCE_OUT",
    "WINDOW_SIZE_SENSITIVITY",  # = sample-complexity ladder, §C
    "METRIC_DEFINITION_SENSITIVITY",
    "LOAD_CALIBRATION_SENSITIVITY",
    "TEMPORAL_SPLIT_SENSITIVITY",
    "LEAVE_ONE_POLICY_FAMILY_OUT",
    "SLO_DEFINITION_SENSITIVITY",
)
# docs/RANKING_PORTABILITY_ANALYSIS_PLAN.md §F: "Seed sensitivity: not
# applicable -- this simulator is deterministic given identical inputs."
SEED_SENSITIVITY_APPLICABLE = False

ANALYSIS_CONTRACT_VERSION = "phase12_analysis_prefreeze_v1"
