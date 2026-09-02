"""Consolidator fixture cases 12-17 (deterministic repetitions,
mismatched repetitions, missing cell, duplicate cell, wrong campaign
hash, wrong load assignment) plus schema/telemetry-invalid-row
rejection and cross-shard duplicate detection. All fabricated, tiny
(2 windows x 1 region x 2 policies x 2 reps = 8-cell) fixtures."""
from __future__ import annotations

import pytest

from robustbench.ranking_portability.analysis.consolidation import consolidate
from ranking_portability_analysis_fixtures import make_cell_row, make_tiny_manifest

FREEZE_SHA = "a" * 64


def _full_valid_shard(manifest):
    """One shard containing every cell in the tiny manifest, all valid."""
    rows = {}
    for c in manifest["cells"]:
        rows[c["cell_id"]] = make_cell_row(
            source_family=c["source_family"], window_id=c["window_id"],
            load_region=c["load_region"], policy_id=c["policy_id"],
            repetition=c["repetition"], synthesis_seed=c["synthesis_seed"],
            load_factor=1.0,
        )
    return rows


def test_case12_deterministic_repetitions_pass():
    manifest = make_tiny_manifest(campaign_freeze_sha256=FREEZE_SHA)
    rows = _full_valid_shard(manifest)
    report = consolidate(
        manifest=manifest, shard_outputs={0: (FREEZE_SHA[:16], rows)},
        expected_campaign_freeze_sha256=FREEZE_SHA,
    )
    assert report.is_complete_and_valid is True
    assert report.rep_mismatch_pairs == []
    assert report.n_consolidated_valid == len(manifest["cells"])


def test_case13_mismatched_repetitions_detected():
    manifest = make_tiny_manifest(campaign_freeze_sha256=FREEZE_SHA)
    rows = _full_valid_shard(manifest)
    # Corrupt one rep1 row's synthesis_seed so it no longer matches rep0's.
    for cid, row in rows.items():
        if row["repetition"] == 1 and row["policy_id"] == "fifo" and row["window_id"] == "w0":
            row["synthesis_seed"] = 999999
    report = consolidate(
        manifest=manifest, shard_outputs={0: (FREEZE_SHA[:16], rows)},
        expected_campaign_freeze_sha256=FREEZE_SHA,
    )
    # A corrupted synthesis_seed no longer matches the manifest's frozen
    # cell definition, so the row itself is invalid (identity mismatch);
    # is_complete_and_valid must be False either way.
    assert report.is_complete_and_valid is False
    assert report.n_invalid >= 1


def test_case13b_rep_input_mismatch_when_row_identity_otherwise_valid():
    manifest = make_tiny_manifest(campaign_freeze_sha256=FREEZE_SHA)
    # Give rep0 and rep1 of the SAME manifest cell definition genuinely
    # different synthesis seeds in the manifest itself would violate the
    # freeze contract, so instead we simulate the rep-mismatch check
    # directly at the consolidation layer by constructing two manifest
    # cells that share (source,window,region,policy) but were frozen
    # with different seeds (a hypothetical corrupted freeze) -- the
    # consolidator's rep-identity check must still catch it.
    manifest["cells"][1]["synthesis_seed"] = manifest["cells"][0]["synthesis_seed"] + 1
    rows = {}
    for c in manifest["cells"]:
        rows[c["cell_id"]] = make_cell_row(
            source_family=c["source_family"], window_id=c["window_id"],
            load_region=c["load_region"], policy_id=c["policy_id"],
            repetition=c["repetition"], synthesis_seed=c["synthesis_seed"], load_factor=1.0,
        )
    report = consolidate(
        manifest=manifest, shard_outputs={0: (FREEZE_SHA[:16], rows)},
        expected_campaign_freeze_sha256=FREEZE_SHA,
    )
    assert report.is_complete_and_valid is False


def test_case14_missing_cell_detected():
    manifest = make_tiny_manifest(campaign_freeze_sha256=FREEZE_SHA)
    rows = _full_valid_shard(manifest)
    missing_cid = manifest["cells"][0]["cell_id"]
    del rows[missing_cid]
    report = consolidate(
        manifest=manifest, shard_outputs={0: (FREEZE_SHA[:16], rows)},
        expected_campaign_freeze_sha256=FREEZE_SHA,
    )
    assert report.is_complete_and_valid is False
    assert missing_cid in report.missing_cell_ids
    assert report.n_missing == 1


def test_case15_duplicate_cell_across_shards_detected():
    manifest = make_tiny_manifest(campaign_freeze_sha256=FREEZE_SHA)
    rows = _full_valid_shard(manifest)
    one_cid = manifest["cells"][0]["cell_id"]
    shard0 = dict(rows)
    shard1 = {one_cid: rows[one_cid]}  # same cell reappears in a second shard
    report = consolidate(
        manifest=manifest,
        shard_outputs={0: (FREEZE_SHA[:16], shard0), 1: (FREEZE_SHA[:16], shard1)},
        expected_campaign_freeze_sha256=FREEZE_SHA,
    )
    assert report.is_complete_and_valid is False
    assert report.n_duplicate_cross_shard == 1
    assert one_cid in report.duplicate_cell_ids
    # And the cell never appears twice in the final consolidation dict.
    assert list(report.consolidated_rows.keys()).count(one_cid) <= 1


def test_case16_wrong_campaign_hash_rejected():
    manifest = make_tiny_manifest(campaign_freeze_sha256=FREEZE_SHA)
    rows = _full_valid_shard(manifest)
    with pytest.raises(ValueError, match="STOPPING"):
        consolidate(
            manifest=manifest, shard_outputs={0: (FREEZE_SHA[:16], rows)},
            expected_campaign_freeze_sha256="b" * 64,
        )


def test_case17_wrong_load_assignment_rejected():
    manifest = make_tiny_manifest(campaign_freeze_sha256=FREEZE_SHA)
    rows = _full_valid_shard(manifest)
    # Corrupt one row's load_factor so it no longer matches the frozen
    # Phase-11 assignment's absolute_load_factor (1.0 in the fixture).
    some_cid = manifest["cells"][0]["cell_id"]
    rows[some_cid]["load_factor"] = 42.0
    report = consolidate(
        manifest=manifest, shard_outputs={0: (FREEZE_SHA[:16], rows)},
        expected_campaign_freeze_sha256=FREEZE_SHA,
    )
    assert report.is_complete_and_valid is False
    assert some_cid in report.invalid_cell_ids


def test_unknown_cell_id_rejected():
    manifest = make_tiny_manifest(campaign_freeze_sha256=FREEZE_SHA)
    rows = _full_valid_shard(manifest)
    bogus = make_cell_row(source_family="burstgpt", window_id="w999", load_region="KNEE", policy_id="fifo")
    rows[bogus["cell_id"]] = bogus
    report = consolidate(
        manifest=manifest, shard_outputs={0: (FREEZE_SHA[:16], rows)},
        expected_campaign_freeze_sha256=FREEZE_SHA,
    )
    assert bogus["cell_id"] in report.unknown_cell_ids
    assert report.is_complete_and_valid is False


def test_wrong_provenance_shard_rejected_wholesale():
    manifest = make_tiny_manifest(campaign_freeze_sha256=FREEZE_SHA)
    rows = _full_valid_shard(manifest)
    report = consolidate(
        manifest=manifest,
        # Claimed directory prefix does not match the expected freeze prefix.
        shard_outputs={0: ("wrongprefix1234", rows)},
        expected_campaign_freeze_sha256=FREEZE_SHA,
    )
    assert report.n_wrong_provenance_shards == 1
    assert report.n_consolidated_valid == 0
    assert report.is_complete_and_valid is False


def test_failed_cell_not_counted_as_complete():
    manifest = make_tiny_manifest(campaign_freeze_sha256=FREEZE_SHA)
    rows = _full_valid_shard(manifest)
    failed_cid = manifest["cells"][0]["cell_id"]
    failed_c = manifest["cells"][0]
    rows[failed_cid] = make_cell_row(
        source_family=failed_c["source_family"], window_id=failed_c["window_id"],
        load_region=failed_c["load_region"], policy_id=failed_c["policy_id"],
        repetition=failed_c["repetition"], synthesis_seed=failed_c["synthesis_seed"],
        success=False,
    )
    report = consolidate(
        manifest=manifest, shard_outputs={0: (FREEZE_SHA[:16], rows)},
        expected_campaign_freeze_sha256=FREEZE_SHA,
    )
    assert failed_cid in report.failed_cell_ids
    assert report.is_complete_and_valid is False


def test_schema_invalid_row_rejected_never_silently_accepted():
    manifest = make_tiny_manifest(campaign_freeze_sha256=FREEZE_SHA)
    rows = _full_valid_shard(manifest)
    some_cid = manifest["cells"][0]["cell_id"]
    rows[some_cid]["telemetry"] = {}  # success=True but telemetry missing -- schema-invalid
    report = consolidate(
        manifest=manifest, shard_outputs={0: (FREEZE_SHA[:16], rows)},
        expected_campaign_freeze_sha256=FREEZE_SHA,
    )
    assert some_cid in report.invalid_cell_ids
    assert some_cid not in report.consolidated_rows


def test_idempotent_consolidation_is_deterministic_across_runs():
    manifest = make_tiny_manifest(campaign_freeze_sha256=FREEZE_SHA)
    rows = _full_valid_shard(manifest)
    r1 = consolidate(manifest=manifest, shard_outputs={0: (FREEZE_SHA[:16], rows)},
                      expected_campaign_freeze_sha256=FREEZE_SHA)
    r2 = consolidate(manifest=manifest, shard_outputs={0: (FREEZE_SHA[:16], dict(rows))},
                      expected_campaign_freeze_sha256=FREEZE_SHA)
    assert r1.consolidated_rows == r2.consolidated_rows
    assert r1.is_complete_and_valid == r2.is_complete_and_valid is True
