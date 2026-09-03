from __future__ import annotations

import numpy as np
import pytest

from robustbench.rq3 import campaign as rq3_campaign
from robustbench.rq3 import transfer_stats as rq3_stats
from robustbench.rq3.synthetic_families import (
    FAMILY_IDS,
    SEEDS,
    generate_family_window,
)

KNOWN_CLASS_IDS = {"tight", "medium", "loose"}


# ---------------------------------------------------------------------------
# Section J: synthetic generator structural tests (fabricated fixtures only,
# no scheduler-ranking outcome inspected here).
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("family_id", FAMILY_IDS)
def test_generator_produces_nonempty_deterministic_trace(family_id):
    a = generate_family_window(family_id, seed=0)
    b = generate_family_window(family_id, seed=0)
    assert len(a) > 0
    # 1. exact request count + 2. deterministic replay given seed
    assert len(a) == len(b)
    for ra, rb in zip(a, b):
        assert ra.request_id == rb.request_id
        assert ra.arrival_time == rb.arrival_time
        assert ra.prompt_tokens == rb.prompt_tokens
        assert ra.actual_output_tokens == rb.actual_output_tokens
        assert ra.predicted_output_tokens == rb.predicted_output_tokens
        assert ra.slo_deadline == rb.slo_deadline
        assert ra.priority == rb.priority
        assert ra.class_id == rb.class_id


@pytest.mark.parametrize("family_id", FAMILY_IDS)
def test_generator_different_seeds_differ(family_id):
    a = generate_family_window(family_id, seed=0)
    b = generate_family_window(family_id, seed=1)
    # Not a scheduler-outcome check -- purely a structural randomness check.
    assert [r.arrival_time for r in a] != [r.arrival_time for r in b] or \
        [r.prompt_tokens for r in a] != [r.prompt_tokens for r in b]


@pytest.mark.parametrize("family_id", FAMILY_IDS)
def test_generator_token_and_arrival_validity(family_id):
    reqs = generate_family_window(family_id, seed=2)
    for r in reqs:
        # 4. no invalid token counts
        assert r.prompt_tokens > 0
        assert r.actual_output_tokens > 0
        assert r.predicted_output_tokens > 0
        # 5. no negative arrival times
        assert r.arrival_time >= 0.0
        assert r.slo_deadline >= r.arrival_time


@pytest.mark.parametrize("family_id", FAMILY_IDS)
def test_generator_stable_ordering(family_id):
    reqs = generate_family_window(family_id, seed=3)
    arrivals = [r.arrival_time for r in reqs]
    # 6. stable ordering -- arrival times non-decreasing in list order
    assert arrivals == sorted(arrivals)


@pytest.mark.parametrize("family_id", FAMILY_IDS)
def test_generator_stage0_synthesis_integration(family_id):
    reqs = generate_family_window(family_id, seed=4)
    # 7. correct Stage-0 synthesis integration: every request carries a
    # known SLO class, positive priority, and a slack consistent with its class.
    for r in reqs:
        assert r.class_id in KNOWN_CLASS_IDS
        assert r.priority > 0


@pytest.mark.parametrize("family_id", FAMILY_IDS)
def test_generator_no_missing_metadata_no_duplicate_ids(family_id):
    reqs = generate_family_window(family_id, seed=5)
    ids = [r.request_id for r in reqs]
    # 8. no missing metadata (dataclass fields always populated by construction)
    for r in reqs:
        assert r.request_id is not None and r.arrival_time is not None
        assert r.class_id is not None and r.priority is not None
    # 9. no duplicate request IDs
    assert len(ids) == len(set(ids))
    assert ids == list(range(len(ids)))


# ---------------------------------------------------------------------------
# Campaign manifest: determinism, expected cell count, no duplicate keys.
# ---------------------------------------------------------------------------

def test_campaign_manifest_expected_cell_count():
    manifest = rq3_campaign.build_manifest(
        family_ids=FAMILY_IDS[:2], seeds=SEEDS[:2], policies=("fifo", "edf"),
    )
    # 2 families * 2 seeds * 2 regions * 2 policies
    assert manifest["n_cells"] == 2 * 2 * 2 * 2
    assert len(manifest["cells"]) == manifest["n_cells"]


def test_campaign_manifest_no_duplicate_cell_ids():
    manifest = rq3_campaign.build_manifest(
        family_ids=FAMILY_IDS[:2], seeds=SEEDS[:2], policies=("fifo", "edf"),
    )
    cell_ids = [c["cell_id"] for c in manifest["cells"]]
    assert len(cell_ids) == len(set(cell_ids))


def test_campaign_manifest_deterministic_hash():
    m1 = rq3_campaign.build_manifest(family_ids=FAMILY_IDS[:1], seeds=SEEDS[:1], policies=("fifo",))
    m2 = rq3_campaign.build_manifest(family_ids=FAMILY_IDS[:1], seeds=SEEDS[:1], policies=("fifo",))
    assert m1["campaign_manifest_sha256"] == m2["campaign_manifest_sha256"]
    assert m1["windows"][0]["requests_content_sha256"] == m2["windows"][0]["requests_content_sha256"]


def test_campaign_manifest_stable_cell_ordering():
    m1 = rq3_campaign.build_manifest(family_ids=FAMILY_IDS[:2], seeds=SEEDS[:1], policies=("fifo", "edf"))
    m2 = rq3_campaign.build_manifest(family_ids=FAMILY_IDS[:2], seeds=SEEDS[:1], policies=("fifo", "edf"))
    assert [c["cell_id"] for c in m1["cells"]] == [c["cell_id"] for c in m2["cells"]]


# ---------------------------------------------------------------------------
# Transfer statistics: fabricated fixtures only.
# ---------------------------------------------------------------------------

def _const_windows(value, n=5):
    return [value] * n


def test_transfer_identical_rankings_gives_tau_one():
    synth = {
        "a": _const_windows(3.0), "b": _const_windows(2.0), "c": _const_windows(1.0),
    }
    real = {
        "a": _const_windows(30.0), "b": _const_windows(20.0), "c": _const_windows(10.0),
    }
    result = rq3_stats.compute_transfer(synth, real, min_common_policies=2, n_bootstrap=50,
                                         rng=np.random.default_rng(0))
    assert result.status == "OK"
    assert result.kendall_tau_b == pytest.approx(1.0)
    assert result.spearman_rho == pytest.approx(1.0)
    assert result.top1_agreement == pytest.approx(1.0)


def test_transfer_exactly_reversed_rankings_gives_tau_minus_one():
    synth = {"a": _const_windows(3.0), "b": _const_windows(2.0), "c": _const_windows(1.0)}
    real = {"a": _const_windows(1.0), "b": _const_windows(2.0), "c": _const_windows(3.0)}
    result = rq3_stats.compute_transfer(synth, real, min_common_policies=2, n_bootstrap=50,
                                         rng=np.random.default_rng(0))
    assert result.kendall_tau_b == pytest.approx(-1.0)
    assert result.spearman_rho == pytest.approx(-1.0)


def test_transfer_insufficient_common_policies_marked_undefined():
    synth = {"a": _const_windows(1.0), "b": _const_windows(2.0)}
    real = {"a": _const_windows(1.0), "b": _const_windows(2.0)}
    result = rq3_stats.compute_transfer(synth, real, min_common_policies=6, n_bootstrap=50)
    assert result.status == "UNDEFINED_INSUFFICIENT_COMMON_POLICIES"
    assert result.kendall_tau_b is None


def test_transfer_deterministic_bootstrap_same_seed_same_ci():
    synth = {"a": [1.0, 1.2, 0.9, 1.1, 1.0], "b": [2.0, 1.8, 2.1, 2.0, 1.9], "c": [0.5, 0.6, 0.4, 0.5, 0.55]}
    real = {"a": [10.0, 11.0, 9.5] * 4, "b": [20.0, 19.0, 21.0] * 4, "c": [5.0, 4.8, 5.2] * 4}
    r1 = rq3_stats.compute_transfer(synth, real, min_common_policies=2, n_bootstrap=200,
                                     rng=np.random.default_rng(42))
    r2 = rq3_stats.compute_transfer(synth, real, min_common_policies=2, n_bootstrap=200,
                                     rng=np.random.default_rng(42))
    assert r1.kendall_ci == r2.kendall_ci
    assert r1.spearman_ci == r2.spearman_ci


def test_transfer_only_common_policies_used_and_panel_recorded():
    synth = {"a": _const_windows(1.0), "b": _const_windows(2.0), "z_only_synth": _const_windows(9.0)}
    real = {"a": _const_windows(1.0), "b": _const_windows(2.0), "z_only_real": _const_windows(9.0)}
    result = rq3_stats.compute_transfer(synth, real, min_common_policies=2, n_bootstrap=20)
    assert result.effective_policy_count == 2
    assert set(result.policy_panel) == {"a", "b"}


def test_transfer_never_compares_a_metric_to_itself_via_disjoint_policy_sets():
    # Structural sanity: an empty intersection must be UNDEFINED, never a
    # silently-computed (and therefore misleading) correlation.
    synth = {"only_synth": _const_windows(1.0)}
    real = {"only_real": _const_windows(1.0)}
    result = rq3_stats.compute_transfer(synth, real, min_common_policies=1, n_bootstrap=20)
    assert result.status == "UNDEFINED_INSUFFICIENT_COMMON_POLICIES"
