from __future__ import annotations

import numpy as np

from robustbench.characterization.separability import evaluate_source_separability


def test_high_accuracy_for_well_separated_synthetic_sources():
    rng = np.random.default_rng(0)
    n_per_class = 40
    X_a = rng.normal(loc=0.0, scale=0.5, size=(n_per_class, 4))
    X_b = rng.normal(loc=10.0, scale=0.5, size=(n_per_class, 4))
    X_c = rng.normal(loc=-10.0, scale=0.5, size=(n_per_class, 4))
    X = np.vstack([X_a, X_b, X_c])
    y = ["a"] * n_per_class + ["b"] * n_per_class + ["c"] * n_per_class
    result = evaluate_source_separability(
        X, y, feature_names=["f0", "f1", "f2", "f3"], n_folds=5, seed=0
    )
    assert result.balanced_accuracy > 0.9
    assert result.macro_f1 > 0.9
    assert result.confusion_matrix.shape == (3, 3)
    assert set(result.class_labels) == {"a", "b", "c"}
    assert result.n_windows == 3 * n_per_class


def test_low_accuracy_for_indistinguishable_synthetic_sources():
    rng = np.random.default_rng(0)
    n_per_class = 40
    X_a = rng.normal(loc=0.0, scale=1.0, size=(n_per_class, 4))
    X_b = rng.normal(loc=0.0, scale=1.0, size=(n_per_class, 4))
    X = np.vstack([X_a, X_b])
    y = ["a"] * n_per_class + ["b"] * n_per_class
    result = evaluate_source_separability(
        X, y, feature_names=["f0", "f1", "f2", "f3"], n_folds=5, seed=0
    )
    # Same distribution -> near-chance balanced accuracy (~0.5 for 2 classes).
    assert result.balanced_accuracy < 0.75


def test_feature_importances_returned_for_every_feature():
    rng = np.random.default_rng(0)
    n_per_class = 30
    X_a = rng.normal(loc=0.0, size=(n_per_class, 3))
    X_b = rng.normal(loc=5.0, size=(n_per_class, 3))
    X = np.vstack([X_a, X_b])
    y = ["a"] * n_per_class + ["b"] * n_per_class
    result = evaluate_source_separability(X, y, feature_names=["f0", "f1", "f2"], n_folds=3, seed=1)
    assert set(result.feature_importances.keys()) == {"f0", "f1", "f2"}
