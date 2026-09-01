"""Source-separability classifier (section 6E of
docs/WORKLOAD_DISTRIBUTION_CHARACTERIZATION_PROTOCOL.md).

Purpose: measure whether workload sources are distinguishable from
source-native workload descriptors alone -- explicitly NOT a scheduler
selector (see docs/CLAIM_BOUNDARIES.md, which forbids exactly that
deliverable for a related but distinct analysis). This module never touches
a scheduler outcome, policy, or SLO field; its only inputs are the common
numeric workload-descriptor matrix and the source label.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.inspection import permutation_importance
from sklearn.metrics import balanced_accuracy_score, confusion_matrix, f1_score
from sklearn.model_selection import StratifiedKFold, cross_val_predict

SEPARABILITY_MODEL_VERSION = "source_separability_random_forest_v1"


@dataclass
class SeparabilityResult:
    balanced_accuracy: float
    macro_f1: float
    confusion_matrix: np.ndarray
    class_labels: list[str]
    feature_importances: dict[str, float]  # permutation importance, mean over held-out folds
    n_folds: int
    n_windows: int


def _fit_predict_permutation_importance(
    X: np.ndarray, y: np.ndarray, feature_names: list[str], *, n_folds: int, seed: int
) -> dict[str, float]:
    """Mean permutation importance (balanced-accuracy drop) computed on the
    held-out fold of each cross-validation split, then averaged across
    folds -- avoids the optimistic bias of computing importance on
    training data."""
    skf = StratifiedKFold(n_splits=n_folds, shuffle=True, random_state=seed)
    importances = np.zeros((n_folds, X.shape[1]))
    for i, (train_idx, test_idx) in enumerate(skf.split(X, y)):
        clf = RandomForestClassifier(
            n_estimators=300, max_depth=None, random_state=seed, class_weight="balanced_subsample"
        )
        clf.fit(X[train_idx], y[train_idx])
        result = permutation_importance(
            clf, X[test_idx], y[test_idx],
            scoring="balanced_accuracy", n_repeats=20, random_state=seed,
        )
        importances[i] = result.importances_mean
    mean_importance = importances.mean(axis=0)
    return {name: float(v) for name, v in zip(feature_names, mean_importance)}


def evaluate_source_separability(
    X: np.ndarray,
    y: list[str],
    feature_names: list[str],
    *,
    n_folds: int = 5,
    seed: int = 20260901,
) -> SeparabilityResult:
    """Nested-free but properly held-out evaluation: StratifiedKFold
    cross-validation for balanced accuracy / macro-F1 / confusion matrix
    (via cross_val_predict, so every prediction is made by a model that
    never saw that row during training), plus fold-held-out permutation
    importance (see `_fit_predict_permutation_importance`)."""
    y_arr = np.asarray(y)
    labels = sorted(set(y_arr.tolist()))
    n_classes = len(labels)
    effective_folds = min(n_folds, min(np.sum(y_arr == lbl) for lbl in labels))
    if effective_folds < 2:
        raise ValueError(
            f"at least 2 windows per class needed for cross-validated separability; "
            f"got class counts {[(lbl, int(np.sum(y_arr == lbl))) for lbl in labels]}"
        )
    clf = RandomForestClassifier(
        n_estimators=300, max_depth=None, random_state=seed, class_weight="balanced_subsample"
    )
    skf = StratifiedKFold(n_splits=effective_folds, shuffle=True, random_state=seed)
    y_pred = cross_val_predict(clf, X, y_arr, cv=skf)

    bal_acc = float(balanced_accuracy_score(y_arr, y_pred))
    macro_f1 = float(f1_score(y_arr, y_pred, average="macro"))
    cm = confusion_matrix(y_arr, y_pred, labels=labels)

    importances = _fit_predict_permutation_importance(
        X, y_arr, feature_names, n_folds=effective_folds, seed=seed
    )

    return SeparabilityResult(
        balanced_accuracy=bal_acc,
        macro_f1=macro_f1,
        confusion_matrix=cm,
        class_labels=labels,
        feature_importances=importances,
        n_folds=effective_folds,
        n_windows=int(X.shape[0]),
    )
