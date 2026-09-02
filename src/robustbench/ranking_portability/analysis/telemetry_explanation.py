"""Offline, explanatory-only descriptor/reversal-association model
(docs/STATISTICAL_ANALYSIS_PLAN.md §G, docs/CLAIM_BOUNDARIES.md).

Relates frozen `WindowDescriptor` fields to whether a window is a
reversal site for a given policy pair, via ONE pre-specified logistic
regression over a FIXED feature set (burstiness_b, prompt_tokens_cv,
output_tokens_cv, long_context_fraction, concurrency_proxy) -- no model
search over descriptor subsets, no feature selection driven by which
features "work" after seeing results.

THIS IS NOT AN ONLINE SELECTOR. This module deliberately exposes no
`predict`, `route`, `select_scheduler`, or regret/reward-style function
-- only a fit-and-report association function -- so it cannot be wired
into a live scheduling decision by accident. Building any such thing
from this module's output is out of scope
(docs/CLAIM_BOUNDARIES.md: "if a descriptor is found to predict
reversals, the deliverable is a documented association, not a deployed
selector").
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Mapping, Sequence

import numpy as np
from scipy import optimize

# Fixed, pre-specified feature set (docs/STATISTICAL_ANALYSIS_PLAN.md §G).
# Never extended/pruned based on which features correlate with outcomes.
DESCRIPTOR_FEATURES = (
    "burstiness_b",
    "prompt_tokens_cv",
    "output_tokens_cv",
    "long_context_fraction",
    "concurrency_proxy",
)


@dataclass
class LogisticAssociationResult:
    features: List[str]
    coefficients: Dict[str, float]
    intercept: float
    n_observations: int
    n_reversal_sites: int
    n_excluded_missing_descriptor: int
    converged: bool


def _neg_log_likelihood(params: np.ndarray, X: np.ndarray, y: np.ndarray) -> float:
    intercept, *coefs = params
    z = intercept + X @ np.array(coefs)
    z = np.clip(z, -30, 30)
    p = 1.0 / (1.0 + np.exp(-z))
    eps = 1e-12
    return -np.sum(y * np.log(p + eps) + (1 - y) * np.log(1 - p + eps))


def fit_reversal_association(
    window_descriptors: Mapping[str, Mapping[str, float]],
    reversal_indicator: Mapping[str, bool],
    *,
    features: Sequence[str] = DESCRIPTOR_FEATURES,
) -> LogisticAssociationResult:
    """`window_descriptors`: {window_id: {feature_name: value, ...}}.
    `reversal_indicator`: {window_id: True/False} -- whether that window
    is a reversal site for the (pre-selected, caller-chosen) policy pair
    under analysis. Windows missing any required feature are excluded,
    never imputed."""
    common = sorted(set(window_descriptors.keys()) & set(reversal_indicator.keys()))
    rows, labels = [], []
    n_excluded = 0
    for w in common:
        desc = window_descriptors[w]
        vals = [desc.get(f) for f in features]
        if any(v is None or (isinstance(v, float) and v != v) for v in vals):
            n_excluded += 1
            continue
        rows.append(vals)
        labels.append(1.0 if reversal_indicator[w] else 0.0)

    n = len(rows)
    if n < len(features) + 2 or len(set(labels)) < 2:
        return LogisticAssociationResult(
            features=list(features), coefficients={f: float("nan") for f in features},
            intercept=float("nan"), n_observations=n,
            n_reversal_sites=int(sum(labels)), n_excluded_missing_descriptor=n_excluded,
            converged=False,
        )

    X = np.array(rows, dtype=float)
    mu, sigma = X.mean(axis=0), X.std(axis=0)
    sigma[sigma == 0] = 1.0
    Xn = (X - mu) / sigma
    y = np.array(labels, dtype=float)

    x0 = np.zeros(len(features) + 1)
    result = optimize.minimize(
        _neg_log_likelihood, x0, args=(Xn, y), method="BFGS",
        options={"maxiter": 500},
    )
    intercept, *coefs = result.x
    return LogisticAssociationResult(
        features=list(features),
        coefficients={f: float(c) for f, c in zip(features, coefs)},
        intercept=float(intercept),
        n_observations=n,
        n_reversal_sites=int(sum(labels)),
        n_excluded_missing_descriptor=n_excluded,
        converged=bool(result.success),
    )
