"""Leakage-safe, paper-facing source-separability evaluation.

Sibling of `separability.py` (which remains unchanged as the historical/
audit record of the original random-split result). This module:

1. Excludes the three deterministically redundant "pressure proxy"
   descriptors from the classifier's PRIMARY feature matrix
   (`docs/SOURCE_SEPARABILITY_AUDIT_20260901.md` section 5) -- they remain
   available in the underlying descriptor dataset for other uses.
2. Fits all preprocessing (median imputation, z-score standardization)
   INSIDE an `sklearn.pipeline.Pipeline`, refit fresh on each fold's TRAIN
   rows only -- structurally impossible to leak test-fold statistics into
   training, unlike the original pipeline's pooled-before-split scaling
   (see the audit doc's "preprocessing leakage" note).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Sequence

import numpy as np
from sklearn.impute import SimpleImputer
from sklearn.inspection import permutation_importance
from sklearn.metrics import balanced_accuracy_score, confusion_matrix, f1_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from .descriptors import COMMON_NUMERIC_FEATURES

#: Exact deterministic products of other COMMON_NUMERIC_FEATURES columns
#: (R^2 = 1.0 vs. the product of their components, see the audit doc) --
#: excluded from the paper-facing classifier's primary feature matrix.
DETERMINISTIC_PROXY_FEATURES = (
    "approx_token_arrival_rate_tps",
    "approx_concurrent_request_proxy",
    "approx_kv_demand_proxy_tokens",
)

#: The paper-facing primary classifier feature set: COMMON_NUMERIC_FEATURES
#: minus the three deterministic proxies. Order matches COMMON_NUMERIC_FEATURES.
PAPER_FACING_FEATURES = tuple(
    f for f in COMMON_NUMERIC_FEATURES if f not in DETERMINISTIC_PROXY_FEATURES
)


def make_pipeline(estimator) -> Pipeline:
    """Median imputation -> z-score standardization -> estimator, as one
    Pipeline object so `.fit(X_train)` / `.transform(X_test)` can never see
    test-fold statistics during preprocessing fit."""
    return Pipeline([
        ("impute", SimpleImputer(strategy="median")),
        ("scale", StandardScaler()),
        ("clf", estimator),
    ])


@dataclass
class FoldResult:
    held_out_group: str
    n_train: int
    n_test: int
    balanced_accuracy: float
    macro_f1: float
    y_true: list
    y_pred: list


@dataclass
class GroupedEvalResult:
    model_name: str
    folds: list  # list[FoldResult]
    balanced_accuracy_pooled: float
    macro_f1_pooled: float
    balanced_accuracy_mean: float
    balanced_accuracy_std: float
    macro_f1_mean: float
    macro_f1_std: float
    confusion_matrix: np.ndarray
    class_labels: list
    permutation_importance_mean: dict | None
    permutation_importance_std: dict | None
    permutation_importance_n_folds_positive: dict | None


def evaluate_grouped(
    X: np.ndarray,
    y: np.ndarray,
    groups: np.ndarray,
    model_factory: Callable[[], object],
    feature_names: Sequence[str],
    *,
    model_name: str,
    seed: int,
    compute_permutation_importance: bool = False,
    n_repeats: int = 30,
    scoring: str = "balanced_accuracy",
) -> GroupedEvalResult:
    """Leave-one-group-out grouped evaluation. Each fold's Pipeline is
    fit fresh on that fold's TRAIN rows only (structural leakage safety --
    see module docstring)."""
    unique_groups = sorted(set(groups.tolist()))
    folds: list[FoldResult] = []
    all_true, all_pred = [], []
    perm_importances = []

    for held_out in unique_groups:
        train_mask = groups != held_out
        test_mask = groups == held_out
        if train_mask.sum() == 0 or test_mask.sum() == 0:
            continue
        pipe = make_pipeline(model_factory())
        pipe.fit(X[train_mask], y[train_mask])
        pred = pipe.predict(X[test_mask])
        yte = y[test_mask]
        all_true.extend(yte.tolist())
        all_pred.extend(pred.tolist())
        folds.append(FoldResult(
            held_out_group=str(held_out),
            n_train=int(train_mask.sum()),
            n_test=int(test_mask.sum()),
            balanced_accuracy=float(balanced_accuracy_score(yte, pred)),
            macro_f1=float(f1_score(yte, pred, average="macro")),
            y_true=yte.tolist(),
            y_pred=pred.tolist(),
        ))
        if compute_permutation_importance:
            pr = permutation_importance(
                pipe, X[test_mask], yte, scoring=scoring, n_repeats=n_repeats, random_state=seed
            )
            perm_importances.append(pr.importances)  # shape (n_features, n_repeats)

    bal_accs = [f.balanced_accuracy for f in folds]
    f1s = [f.macro_f1 for f in folds]
    class_labels = sorted(set(y.tolist()))
    cm = confusion_matrix(all_true, all_pred, labels=class_labels) if all_true else None

    perm_mean = perm_std = perm_n_pos = None
    if compute_permutation_importance and perm_importances:
        # Concatenate per-fold repeat-level importances along the repeats axis,
        # then aggregate -- gives a proper cross-fold mean/std, not a mean-of-means.
        stacked = np.concatenate(perm_importances, axis=1)  # (n_features, n_folds*n_repeats)
        perm_mean = {name: float(v) for name, v in zip(feature_names, stacked.mean(axis=1))}
        perm_std = {name: float(v) for name, v in zip(feature_names, stacked.std(axis=1))}
        # "n folds with positive importance" -- per-fold mean-over-repeats > 0
        per_fold_means = np.stack([imp.mean(axis=1) for imp in perm_importances], axis=1)  # (n_features, n_folds)
        perm_n_pos = {
            name: int(np.sum(per_fold_means[i] > 0))
            for i, name in enumerate(feature_names)
        }

    return GroupedEvalResult(
        model_name=model_name,
        folds=folds,
        balanced_accuracy_pooled=float(balanced_accuracy_score(all_true, all_pred)) if all_true else float("nan"),
        macro_f1_pooled=float(f1_score(all_true, all_pred, average="macro")) if all_true else float("nan"),
        balanced_accuracy_mean=float(np.mean(bal_accs)) if bal_accs else float("nan"),
        balanced_accuracy_std=float(np.std(bal_accs)) if bal_accs else float("nan"),
        macro_f1_mean=float(np.mean(f1s)) if f1s else float("nan"),
        macro_f1_std=float(np.std(f1s)) if f1s else float("nan"),
        confusion_matrix=cm,
        class_labels=class_labels,
        permutation_importance_mean=perm_mean,
        permutation_importance_std=perm_std,
        permutation_importance_n_folds_positive=perm_n_pos,
    )
