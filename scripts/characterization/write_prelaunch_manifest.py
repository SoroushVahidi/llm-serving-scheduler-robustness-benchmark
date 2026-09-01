#!/usr/bin/env python3
"""Freeze artifacts/manifests/workload_characterization_prelaunch.json
BEFORE the full characterization campaign runs (section 8 of
docs/WORKLOAD_DISTRIBUTION_CHARACTERIZATION_PROTOCOL.md). Captures the
frozen sampling/statistical protocol, source checksums (from
configs/workloads/source_registry.yaml), and environment info -- everything
needed to confirm, after the fact, that the full run used exactly the
protocol committed here (not one chosen after seeing preliminary results).

Does not touch any real data file and does not build any window -- it is
intentionally cheap to run repeatedly.
"""
from __future__ import annotations

import hashlib
import json
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from robustbench.characterization.descriptors import (  # noqa: E402
    COMMON_NUMERIC_FEATURES,
    DESCRIPTOR_SCHEMA_VERSION,
    LONG_PROMPT_THRESHOLDS,
)
from robustbench.characterization.separability import SEPARABILITY_MODEL_VERSION  # noqa: E402
from robustbench.workloads.external.stage0_window_selection import (  # noqa: E402
    SELECTION_ALGORITHM_VERSION,
)

sys.path.insert(0, str(REPO_ROOT / "scripts" / "characterization"))
from build_and_describe_windows import (  # noqa: E402
    BUILDER_VERSION,
    MIN_DEFENSIBLE_N_WINDOWS,
    OFFSET_VALID_ROWS,
    SEED,
    TARGET_N_WINDOWS,
    WINDOW_SIZES,
)
from merge_and_analyze import PRIMARY_WINDOW_SIZE, STATISTICAL_PROTOCOL_VERSION  # noqa: E402

SOURCES = ["burstgpt", "azure_llm_2024", "bailian_qwen", "tracelab"]


def _git_sha() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO_ROOT).decode().strip()


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


# Independently re-verified by this session directly against the on-disk
# files (`sha256sum`, 2026-09-01) -- see
# docs/OVERNIGHT_WORKLOAD_CHARACTERIZATION_HANDOFF_20260901.md. Hardcoded
# here (rather than read from configs/workloads/source_registry.yaml) so
# this manifest does not depend on a concurrent, separately-in-progress
# edit to that shared file's checksum fields for other sources -- these
# values are independently verified regardless of that file's commit
# status. Must match scripts/slurm/workload_characterization_build.sbatch's
# RAW_PATHS exactly.
SOURCE_CHECKSUMS = {
    "burstgpt": {
        "wulver_path": "/project/ikoutis/sv96/llmserveopt-data/datasets/burstgpt_v2/raw/BurstGPT_without_fails_2.csv",
        "checksum": "sha256:56193aa9b2bb26128ded43d2d29a960df6bf5af062bcfc9b005f3fcaa4e6e501",
    },
    "azure_llm_2024": {
        "wulver_path": "/project/ikoutis/sv96/llmserveopt-data/datasets/azure_llm_2024/raw/AzureLLMInferenceTrace_conv_2024.csv",
        "checksum": "sha256:a0cc9b969a9bbf0fd811802cbf4323edd3a209ace791e3799ad4f9207f213941",
    },
    "bailian_qwen": {
        "wulver_path": "/project/ikoutis/sv96/llmserveopt-data/datasets/bailian_qwen/raw/qwen_traceB_blksz_16.jsonl",
        "checksum": "sha256:68e3f98e2d601d60d0abf4b89bc8a3654372abab7b1cde6373a13d0054379d59",
    },
    "tracelab": {
        "wulver_path": "/project/ikoutis/sv96/llmserveopt-data/tracelab_staging_20260722T192050Z/raw/syfi_coding_trace.jsonl.gz",
        "checksum": "sha256:9d265eae69a31cae203848bea936f018148eed7ca8bf56050c5abe96da0b4e6b",
    },
}


def main() -> None:
    checksums = {s: {**SOURCE_CHECKSUMS[s], "acquired": True} for s in SOURCES}
    missing = [s for s in SOURCES if s not in checksums or checksums[s]["checksum"] is None]
    if missing:
        print(f"ERROR: missing checksum for: {missing}", file=sys.stderr)
        sys.exit(1)

    sampling_config = {
        "seed": SEED,
        "offset_valid_rows": OFFSET_VALID_ROWS,
        "target_n_windows": TARGET_N_WINDOWS,
        "min_defensible_n_windows": MIN_DEFENSIBLE_N_WINDOWS,
        "window_sizes": list(WINDOW_SIZES),
        "primary_window_size": PRIMARY_WINDOW_SIZE,
        "selection_algorithm_version": SELECTION_ALGORITHM_VERSION,
        "builder_version": BUILDER_VERSION,
        "sources": SOURCES,
    }
    feature_schema = {
        "descriptor_schema_version": DESCRIPTOR_SCHEMA_VERSION,
        "common_numeric_features": list(COMMON_NUMERIC_FEATURES),
        "long_prompt_thresholds": list(LONG_PROMPT_THRESHOLDS),
    }
    statistical_protocol = {
        "statistical_protocol_version": STATISTICAL_PROTOCOL_VERSION,
        "separability_model_version": SEPARABILITY_MODEL_VERSION,
        "univariate": ["bootstrap_mean_ci(n_boot=2000)", "cohens_d", "ks_2samp", "wasserstein_distance", "benjamini_hochberg_fdr"],
        "multivariate": ["centroid_euclidean_distance", "mahalanobis_centroid_distance(ridge)", "mmd_rbf_unbiased(median_heuristic)"],
        "cross_vs_within": ["mann_whitney_u", "rank_biserial_effect_size"],
        "separability": ["RandomForestClassifier(300 trees)", "StratifiedKFold(5)", "cross_val_predict", "permutation_importance(20 repeats, held-out folds)"],
    }

    manifest = {
        "manifest_kind": "workload_characterization_prelaunch",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "repo_sha": _git_sha(),
        "source_checksums": checksums,
        "window_sampling_protocol": sampling_config,
        "window_sampling_protocol_hash": _sha256_text(json.dumps(sampling_config, sort_keys=True)),
        "feature_schema": feature_schema,
        "feature_schema_hash": _sha256_text(json.dumps(feature_schema, sort_keys=True)),
        "statistical_protocol": statistical_protocol,
        "statistical_protocol_hash": _sha256_text(json.dumps(statistical_protocol, sort_keys=True)),
        "environment": {
            "python_version": platform.python_version(),
            "platform": platform.platform(),
        },
        "note": (
            "window_sampling_protocol_hash/feature_schema_hash/statistical_protocol_hash "
            "are hashes of the FROZEN CONFIGURATION (parameters/versions), computed before "
            "the full campaign ran against real data -- not a hash of the built windows "
            "themselves (those only exist after the SLURM job runs against the real files "
            "and are hashed separately as combined_window_manifest_sha256 in "
            "results/workload_distribution_characterization_v1/provenance.json)."
        ),
    }
    out_path = REPO_ROOT / "artifacts" / "manifests" / "workload_characterization_prelaunch.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(manifest, f, indent=2)
    print(f"Wrote {out_path}", file=sys.stderr)
    print(f"repo_sha={manifest['repo_sha']}")
    print(f"window_sampling_protocol_hash={manifest['window_sampling_protocol_hash']}")
    print(f"feature_schema_hash={manifest['feature_schema_hash']}")
    print(f"statistical_protocol_hash={manifest['statistical_protocol_hash']}")


if __name__ == "__main__":
    main()
