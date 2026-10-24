"""Distribution-shift distance/effect-size primitives (section 6 of
docs/WORKLOAD_DISTRIBUTION_CHARACTERIZATION_PROTOCOL.md).

Pure numeric functions operating on 1-D or 2-D numpy arrays of already-
extracted descriptor values -- no knowledge of ExternalWorkloadRecord,
sources, or windows lives here, so these are independently unit-testable
against synthetic distributions with known ground truth.

The window is the unit throughout: every array passed in here is expected
to already be one value (or one feature vector) per window, never per
individual request -- see docs/WORKLOAD_DISTRIBUTION_CHARACTERIZATION_PROTOCOL.md
"statistical rules".
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np
from scipy import stats as scipy_stats


# ---------------------------------------------------------------------------
# Univariate (section 6A)
# ---------------------------------------------------------------------------

def bootstrap_mean_ci(
    values: np.ndarray, *, n_boot: int = 2000, ci: float = 0.95, seed: int = 0
) -> tuple[Optional[float], Optional[float]]:
    """Percentile-bootstrap CI for the mean. None/None if fewer than 2 values."""
    v = np.asarray(values, dtype=float)
    v = v[~np.isnan(v)]
    if v.size < 2:
        return None, None
    rng = np.random.default_rng(seed)
    boot_means = np.empty(n_boot)
    n = v.size
    for i in range(n_boot):
        sample = v[rng.integers(0, n, size=n)]
        boot_means[i] = np.mean(sample)
    alpha = (1.0 - ci) / 2.0
    lo = float(np.percentile(boot_means, 100 * alpha))
    hi = float(np.percentile(boot_means, 100 * (1 - alpha)))
    return lo, hi


def cohens_d(a: np.ndarray, b: np.ndarray) -> Optional[float]:
    """Pooled-SD standardized mean difference (a - b). None if degenerate."""
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    a = a[~np.isnan(a)]
    b = b[~np.isnan(b)]
    if a.size < 2 or b.size < 2:
        return None
    n1, n2 = a.size, b.size
    s1, s2 = np.var(a, ddof=1), np.var(b, ddof=1)
    pooled_var = ((n1 - 1) * s1 + (n2 - 1) * s2) / (n1 + n2 - 2)
    pooled_sd = np.sqrt(pooled_var)
    if pooled_sd == 0:
        return None
    return float((np.mean(a) - np.mean(b)) / pooled_sd)


@dataclass
class UnivariatePairResult:
    ks_statistic: Optional[float]
    ks_pvalue: Optional[float]
    wasserstein: Optional[float]
    cohens_d: Optional[float]


def univariate_pair_distance(a: np.ndarray, b: np.ndarray) -> UnivariatePairResult:
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    a = a[~np.isnan(a)]
    b = b[~np.isnan(b)]
    if a.size < 2 or b.size < 2:
        return UnivariatePairResult(None, None, None, None)
    ks = scipy_stats.ks_2samp(a, b)
    wd = float(scipy_stats.wasserstein_distance(a, b))
    return UnivariatePairResult(
        ks_statistic=float(ks.statistic),
        ks_pvalue=float(ks.pvalue),
        wasserstein=wd,
        cohens_d=cohens_d(a, b),
    )


def benjamini_hochberg(pvalues: list[Optional[float]]) -> list[Optional[float]]:
    """BH FDR-adjusted p-values, preserving input order and None entries."""
    indexed = [(i, p) for i, p in enumerate(pvalues) if p is not None]
    if not indexed:
        return list(pvalues)
    idx = [i for i, _ in indexed]
    pvals = np.array([p for _, p in indexed], dtype=float)
    m = pvals.size
    order = np.argsort(pvals)
    ranked = pvals[order]
    adjusted = ranked * m / (np.arange(m) + 1)
    # Enforce monotonicity (standard BH step-up correction).
    adjusted = np.minimum.accumulate(adjusted[::-1])[::-1]
    adjusted = np.clip(adjusted, 0, 1)
    out_by_rank = np.empty(m)
    out_by_rank[order] = adjusted
    result: list[Optional[float]] = list(pvalues)
    for pos, i in enumerate(idx):
        result[i] = float(out_by_rank[pos])
    return result


# ---------------------------------------------------------------------------
# Multivariate (section 6B)
# ---------------------------------------------------------------------------

def standardize(X: np.ndarray, mean: np.ndarray, std: np.ndarray) -> np.ndarray:
    safe_std = np.where(std > 0, std, 1.0)
    return (X - mean) / safe_std


def fit_standardizer(X: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Column-wise mean/std over rows with no NaN handling -- caller must
    pass an already-imputed/complete-case matrix."""
    return np.nanmean(X, axis=0), np.nanstd(X, axis=0)


def centroid_euclidean_distance(X_a: np.ndarray, X_b: np.ndarray) -> Optional[float]:
    if X_a.shape[0] == 0 or X_b.shape[0] == 0:
        return None
    ca = np.nanmean(X_a, axis=0)
    cb = np.nanmean(X_b, axis=0)
    return float(np.linalg.norm(ca - cb))


def mahalanobis_centroid_distance(
    X_a: np.ndarray, X_b: np.ndarray, *, ridge: float = 1e-3
) -> Optional[float]:
    """Mahalanobis distance between two group centroids using a pooled,
    ridge-regularized covariance estimate (numerically stable even when a
    group has fewer rows than columns)."""
    if X_a.shape[0] < 2 or X_b.shape[0] < 2:
        return None
    ca = np.mean(X_a, axis=0)
    cb = np.mean(X_b, axis=0)
    cov_a = np.cov(X_a, rowvar=False)
    cov_b = np.cov(X_b, rowvar=False)
    pooled = (cov_a + cov_b) / 2.0
    p = pooled.shape[0]
    pooled_reg = pooled + ridge * np.eye(p) * np.trace(pooled) / p if np.trace(pooled) > 0 else pooled + ridge * np.eye(p)
    diff = ca - cb
    try:
        inv = np.linalg.pinv(pooled_reg)
    except np.linalg.LinAlgError:
        return None
    dist_sq = float(diff @ inv @ diff)
    return float(np.sqrt(max(dist_sq, 0.0)))


def _median_heuristic_gamma(X: np.ndarray) -> float:
    """RBF kernel gamma = 1 / (2 * median pairwise squared distance)."""
    n = X.shape[0]
    if n < 2:
        return 1.0
    # Subsample for cost control on large window counts (not needed at our
    # scale of ~100 windows/source, kept for robustness).
    sub = X if n <= 500 else X[np.random.default_rng(0).choice(n, 500, replace=False)]
    sq_dists = np.sum((sub[:, None, :] - sub[None, :, :]) ** 2, axis=-1)
    iu = np.triu_indices(sub.shape[0], k=1)
    med = np.median(sq_dists[iu])
    if med <= 0:
        return 1.0
    return float(1.0 / (2.0 * med))


def mmd_rbf_unbiased(X_a: np.ndarray, X_b: np.ndarray, gamma: Optional[float] = None) -> Optional[float]:
    """Unbiased MMD^2 estimate with an RBF kernel (Gretton et al. 2012,
    eq. 3). gamma defaults to the median-heuristic bandwidth computed over
    the pooled sample. Returns MMD^2 (can be slightly negative due to the
    unbiased estimator; not clipped, so a caller can see near-zero noise)."""
    m, n = X_a.shape[0], X_b.shape[0]
    if m < 2 or n < 2:
        return None
    if gamma is None:
        gamma = _median_heuristic_gamma(np.vstack([X_a, X_b]))

    def rbf(X, Y):
        sq = np.sum((X[:, None, :] - Y[None, :, :]) ** 2, axis=-1)
        return np.exp(-gamma * sq)

    Kaa = rbf(X_a, X_a)
    Kbb = rbf(X_b, X_b)
    Kab = rbf(X_a, X_b)
    sum_aa = (np.sum(Kaa) - np.trace(Kaa)) / (m * (m - 1))
    sum_bb = (np.sum(Kbb) - np.trace(Kbb)) / (n * (n - 1))
    sum_ab = np.sum(Kab) / (m * n)
    return float(sum_aa + sum_bb - 2 * sum_ab)


# ---------------------------------------------------------------------------
# Cross-source vs within-source comparison (section 6D)
# ---------------------------------------------------------------------------

def pairwise_row_distances(X_a: np.ndarray, X_b: np.ndarray) -> np.ndarray:
    """Flat array of Euclidean distances between every row of X_a and every
    row of X_b (window-level unit -- see module docstring)."""
    if X_a.shape[0] == 0 or X_b.shape[0] == 0:
        return np.array([])
    diffs = X_a[:, None, :] - X_b[None, :, :]
    return np.linalg.norm(diffs, axis=-1).ravel()


@dataclass
class MannWhitneyResult:
    statistic: Optional[float]
    pvalue: Optional[float]
    rank_biserial: Optional[float]  # common-language-adjacent effect size


def mann_whitney_with_effect_size(a: np.ndarray, b: np.ndarray) -> MannWhitneyResult:
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    if a.size < 1 or b.size < 1:
        return MannWhitneyResult(None, None, None)
    res = scipy_stats.mannwhitneyu(a, b, alternative="two-sided")
    n1, n2 = a.size, b.size
    # Rank-biserial correlation from the U statistic (Wendt 1972).
    r = 1.0 - (2.0 * res.statistic) / (n1 * n2)
    return MannWhitneyResult(statistic=float(res.statistic), pvalue=float(res.pvalue), rank_biserial=float(r))
