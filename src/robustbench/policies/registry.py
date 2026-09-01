"""
Policy registry: map string names to policy instances.

Online-deployable baselines are in _REGISTRY / BASELINE_NAMES.
Non-deployable oracle policies are in ORACLE_POLICY_NAMES — never in BASELINE_NAMES
and never in SELECTOR_CANDIDATE_NAMES.
"""
from __future__ import annotations

from typing import Dict, List, Sequence

from .admission_control import AdmissionControlPolicy
from .adaptive_chunked_prefill import AdaptiveChunkedPrefillPolicy
from .aging_priority import AgingPriorityPolicy
from .base import BasePolicy
from .best_fit import BestFitPolicy
from .edf import EDFPolicy
from .estimated_service_time_first import EstimatedServiceTimeFirstPolicy
from .fifo import FIFOPolicy
from .first_fit import FirstFitPolicy
from .flow_control_stability import FlowControlStabilityPolicy
from .greedy_token_fill import GreedyTokenFillPolicy
from .kv_constrained_online import KVConstrainedOnlinePolicy
from .least_laxity_first import LeastLaxityFirstPolicy
from .least_loaded import LeastLoadedPolicy
from .multi_bin_batching import MultiBinBatchingPolicy
from .oracle import OracleShortestJobFirstPolicy, build_oracle
from .orca_style import OrcaStylePolicy
from .random_feasible import RandomFeasiblePolicy
from .sarathi_style import SarathiStylePolicy
from .scorpio_style_slo_guard import ScorpioStyleSloGuardPolicy
from .shortest_output_first import ShortestOutputFirstPolicy
from .shortest_prompt_first import ShortestPromptFirstPolicy
from .slai_style_phase_aware import SlaiStylePhaseAwarePolicy
from .slo_slack_score import SloSlackScorePolicy
from .sola_style_state_aware import SolaStyleStateAwarePolicy
from .splitfuse_style import SplitFuseStylePolicy
from .vllm_style_token_budget import VLLMStyleTokenBudgetPolicy
from .weighted_shortest_processing import WeightedShortestProcessingPolicy
from .weighted_fair_share import WeightedFairSharePolicy


_REGISTRY: Dict[str, type] = {
    # Phase 1 baselines
    "fifo":                    FIFOPolicy,
    "edf":                     EDFPolicy,
    "shortest_output_first":   ShortestOutputFirstPolicy,
    "shortest_prompt_first":   ShortestPromptFirstPolicy,
    "greedy_token_fill":       GreedyTokenFillPolicy,
    "least_loaded":            LeastLoadedPolicy,
    "multi_bin_batching":      MultiBinBatchingPolicy,
    "random_feasible":         RandomFeasiblePolicy,
    "first_fit":               FirstFitPolicy,
    "best_fit":                BestFitPolicy,
    # Phase 1.5 serving-style baselines
    "orca_style":              OrcaStylePolicy,
    "vllm_style_token_budget": VLLMStyleTokenBudgetPolicy,
    "sarathi_style":           SarathiStylePolicy,
    "splitfuse_style":         SplitFuseStylePolicy,
    "slo_slack_score":         SloSlackScorePolicy,
    "weighted_shortest_processing": WeightedShortestProcessingPolicy,
    # Phase 2A.3B: hardened deadline and service-time baselines
    "least_laxity_first":                LeastLaxityFirstPolicy,
    "estimated_service_time_first":      EstimatedServiceTimeFirstPolicy,
    # Phase 2B.5: explicit admission-control baseline
    "admission_control":                 AdmissionControlPolicy,
    # Phase 2B.10: SCORPIO-inspired SLO guard baseline
    "scorpio_style_slo_guard":           ScorpioStyleSloGuardPolicy,
}

BASELINE_NAMES: List[str] = list(_REGISTRY.keys())

# Policy Library v2 extension. These policies are deployable in the same
# monolithic simulator/action space as BASELINE_NAMES, but they are not added
# to BASELINE_NAMES because multiple Selector v2 reproducibility tests and
# docs intentionally pin that historical library at 20 policies.
_POLICY_LIBRARY_V2_REGISTRY: Dict[str, type] = {
    "sola_style_state_aware": SolaStyleStateAwarePolicy,
    "slai_style_phase_aware": SlaiStylePhaseAwarePolicy,
    "flow_control_stability": FlowControlStabilityPolicy,
    "kv_constrained_online": KVConstrainedOnlinePolicy,
    "adaptive_chunked_prefill": AdaptiveChunkedPrefillPolicy,
    "aging_priority": AgingPriorityPolicy,
    "weighted_fair_share": WeightedFairSharePolicy,
}

POLICY_LIBRARY_V2_NEW_NAMES: List[str] = list(_POLICY_LIBRARY_V2_REGISTRY.keys())
POLICY_LIBRARY_V2_NAMES: List[str] = list(BASELINE_NAMES) + list(POLICY_LIBRARY_V2_NEW_NAMES)

# Oracle policies — non-deployable, hindsight upper bounds only.
# MUST NOT appear in BASELINE_NAMES or SELECTOR_CANDIDATE_NAMES.
ORACLE_POLICY_NAMES: List[str] = ["oracle_srtf"]

# Selector candidates = all online-deployable baselines (no oracle).
SELECTOR_CANDIDATE_NAMES: List[str] = list(BASELINE_NAMES)

# Convenience subsets for experiment configs
PHASE1_BASELINES: List[str] = [
    "fifo", "edf", "shortest_output_first", "shortest_prompt_first",
    "greedy_token_fill", "least_loaded", "multi_bin_batching", "random_feasible",
    "first_fit", "best_fit",
]

SERVING_STYLE_BASELINES: List[str] = [
    "orca_style", "vllm_style_token_budget", "sarathi_style",
    "splitfuse_style", "slo_slack_score", "weighted_shortest_processing",
]

# Phase 2A.3B: deadline/laxity and service-time baselines
DEADLINE_LAXITY_BASELINES: List[str] = [
    "least_laxity_first",
    "estimated_service_time_first",
]


def make_policy(name: str, seed: int = 0, **kwargs) -> BasePolicy:
    """Instantiate a policy by name.

    Parameters
    ----------
    name : str
        Registry key (e.g. "fifo", "orca_style").
    seed : int
        Passed to stochastic policies (random_feasible).
    **kwargs
        Additional constructor arguments forwarded to the policy constructor.
    """
    if name not in _REGISTRY:
        raise KeyError(
            f"Unknown policy '{name}'. Available: {sorted(_REGISTRY.keys())}"
        )
    cls = _REGISTRY[name]
    if name == "random_feasible":
        return cls(seed=seed, **kwargs)
    return cls(**kwargs)


def make_policy_library_v2(name: str, seed: int = 0, **kwargs) -> BasePolicy:
    """Instantiate a historical or Policy Library v2 deployable policy."""
    if name in _REGISTRY:
        return make_policy(name, seed=seed, **kwargs)
    if name not in _POLICY_LIBRARY_V2_REGISTRY:
        raise KeyError(
            f"Unknown Policy Library v2 policy '{name}'. Available: {sorted(POLICY_LIBRARY_V2_NAMES)}"
        )
    return _POLICY_LIBRARY_V2_REGISTRY[name](**kwargs)


def all_baseline_policies(seed: int = 0) -> List[BasePolicy]:
    """Return one instance of every registered baseline policy."""
    return [make_policy(name, seed=seed) for name in BASELINE_NAMES]


def phase1_policies(seed: int = 0) -> List[BasePolicy]:
    """Return one instance of each Phase 1 baseline policy."""
    return [make_policy(name, seed=seed) for name in PHASE1_BASELINES]


def serving_style_policies(seed: int = 0) -> List[BasePolicy]:
    """Return one instance of each Phase 1.5 serving-style policy."""
    return [make_policy(name, seed=seed) for name in SERVING_STYLE_BASELINES]


def make_oracle_policy(name: str, requests: Sequence) -> OracleShortestJobFirstPolicy:
    """Build a non-deployable oracle policy from a list of Request objects.

    Raises ValueError if name is not in ORACLE_POLICY_NAMES, so callers
    cannot accidentally use this path for online baselines.

    Parameters
    ----------
    name : str
        Must be "oracle_srtf" (or another ORACLE_POLICY_NAMES entry in future).
    requests : sequence of Request
        The full trace — actual_output_tokens are extracted to build the oracle map.
    """
    if name not in ORACLE_POLICY_NAMES:
        raise ValueError(
            f"'{name}' is not an oracle policy. Oracle policies: {ORACLE_POLICY_NAMES}. "
            f"For online baselines use make_policy()."
        )
    if name == "oracle_srtf":
        return build_oracle(list(requests))
    raise ValueError(f"No oracle constructor defined for '{name}'.")
