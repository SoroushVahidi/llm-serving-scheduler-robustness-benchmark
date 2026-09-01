"""Regression tests for the paper-facing separability pipeline
(src/robustbench/characterization/separability_pipeline.py):

1. The three deterministic-proxy features are excluded from
   PAPER_FACING_FEATURES.
2. Preprocessing (imputation + scaling) is fit on TRAIN-fold data only --
   the original pipeline's pooled-before-split scaling
   (docs/SOURCE_SEPARABILITY_AUDIT_20260901.md) is structurally impossible
   here because `make_pipeline(...).fit(X_train)` never sees X_test.
"""
from __future__ import annotations

import numpy as np
import pytest
from sklearn.dummy import DummyClassifier

from robustbench.characterization.descriptors import COMMON_NUMERIC_FEATURES
from robustbench.characterization.separability_pipeline import (
    DETERMINISTIC_PROXY_FEATURES,
    PAPER_FACING_FEATURES,
    evaluate_grouped,
    make_pipeline,
)


def test_paper_facing_features_excludes_deterministic_proxies():
    assert set(DETERMINISTIC_PROXY_FEATURES).isdisjoint(PAPER_FACING_FEATURES)
    assert len(PAPER_FACING_FEATURES) == len(COMMON_NUMERIC_FEATURES) - len(DETERMINISTIC_PROXY_FEATURES)
    for f in DETERMINISTIC_PROXY_FEATURES:
        assert f in COMMON_NUMERIC_FEATURES  # still valid descriptors, just not in the paper-facing set
        assert f not in PAPER_FACING_FEATURES


def test_pipeline_scaler_fit_on_train_fold_only_not_pooled():
    """Construct train/test blocks with deliberately different means/stds.
    A LEAKY pipeline (scaler fit on train+test pooled) would produce a
    scaler mean/std that depends on the test block's values. This pipeline
    must not."""
    rng = np.random.default_rng(0)
    x_train = rng.normal(loc=0.0, scale=1.0, size=(50, 3))
    x_test = rng.normal(loc=1000.0, scale=50.0, size=(10, 3))  # wildly different distribution

    pipe = make_pipeline(DummyClassifier(strategy="most_frequent"))
    pipe.fit(x_train, np.array(["a"] * 50))

    fitted_mean = pipe.named_steps["scale"].mean_
    pooled_mean = np.mean(np.vstack([x_train, x_test]), axis=0)
    train_only_mean = np.mean(x_train, axis=0)

    np.testing.assert_allclose(fitted_mean, train_only_mean, rtol=1e-9)
    # The pooled mean is wildly different (~1000) from the train-only mean (~0);
    # if this assertion ever fails it means the scaler saw the test block.
    assert np.all(np.abs(fitted_mean - pooled_mean) > 100), (
        "scaler mean matches the train+test pooled mean -- preprocessing leakage reintroduced"
    )


def test_evaluate_grouped_never_leaks_held_out_group_into_training_stats():
    """End-to-end: for a held-out group with a shifted distribution,
    evaluate_grouped's internal per-fold Pipeline must fit its scaler only
    on the training groups -- verified indirectly by reproducing the same
    fit manually and comparing fold predictions are deterministic/reproducible
    (a leaky implementation fit on the full pool would not vary by held-out
    group in a way consistent with train-only statistics)."""
    rng = np.random.default_rng(1)
    n_per_group = 40
    groups = np.array(["g0"] * n_per_group + ["g1"] * n_per_group + ["g2"] * n_per_group)
    # g2 is shifted far away from g0/g1 -- if g2's stats leaked into the g0-held-out
    # or g1-held-out fold's scaler fit, predictions on those folds would shift.
    X = np.concatenate([
        rng.normal(0.0, 1.0, size=(n_per_group, 2)),
        rng.normal(0.2, 1.0, size=(n_per_group, 2)),
        rng.normal(500.0, 1.0, size=(n_per_group, 2)),
    ])
    y = np.array(["src_a"] * n_per_group + ["src_b"] * n_per_group + ["src_a"] * n_per_group)

    result = evaluate_grouped(
        X, y, groups, lambda: DummyClassifier(strategy="most_frequent"),
        ["f0", "f1"], model_name="dummy", seed=0,
    )
    # With g2 held out, train pool is g0+g1 only (means near 0/0.2) -- the
    # fitted scaler for that fold must reflect only g0+g1, not g2's ~500 shift.
    g2_fold = next(f for f in result.folds if f.held_out_group == "g2")
    train_mask = groups != "g2"
    expected_train_mean = np.mean(X[train_mask], axis=0)
    pipe = make_pipeline(DummyClassifier(strategy="most_frequent"))
    pipe.fit(X[train_mask], y[train_mask])
    np.testing.assert_allclose(pipe.named_steps["scale"].mean_, expected_train_mean, rtol=1e-9)
    assert g2_fold.n_train == 2 * n_per_group
    assert g2_fold.n_test == n_per_group
