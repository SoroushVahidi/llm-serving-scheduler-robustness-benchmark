#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

export LSSP_ARTIFACT_REPRO_PREFREEZE_RESULT_BLIND=YES
export PYTHONPATH="${ROOT}/src${PYTHONPATH:+:${PYTHONPATH}}"

usage() {
  cat <<'USAGE'
Usage: ./scripts/artifact/verify_artifact.sh [mode]

Validation-only modes:
  --quick                  environment sanity, immutable hashes, schema tests, toy fixture
  --full-tests             full pytest suite
  --validate-freeze        frozen Phase-12 manifest/matrix/shard validation only
  --validate-results PATH  validate an explicitly supplied completed artifact; no default path
  --analysis-fixture       run fabricated analysis fixture only

This script never submits Slurm, never passes --execute, never starts real-vLLM,
and never reads a live campaign-results directory by default.
USAGE
}

require_arg() {
  if [[ $# -lt 1 ]]; then
    echo "ERROR: missing argument" >&2
    usage >&2
    exit 2
  fi
}

mode="${1:---quick}"
case "$mode" in
  --quick)
    python - <<'PY'
import importlib, platform
for name in ["numpy", "pandas", "yaml", "scipy", "robustbench"]:
    importlib.import_module(name)
print(f"python={platform.python_version()}")
print("ENVIRONMENT_SANITY_CHECK = PASS")
PY
    python scripts/artifact/write_provenance_snapshot.py
    python scripts/artifact/verify_immutable_artifacts.py
    python -m pytest -q \
      tests/test_ranking_portability_schema.py \
      tests/test_ranking_portability_phase12_campaign.py \
      tests/test_ranking_portability_phase12_campaign_dry_run.py \
      tests/test_artifact_repro.py
    python scripts/artifact/toy_reproduction.py
    echo "ARTIFACT_QUICK_VERIFY_PASS = YES"
    ;;
  --full-tests)
    python -m pytest
    ;;
  --validate-freeze)
    mkdir -p artifacts/generated
    python scripts/artifact/verify_immutable_artifacts.py
    python scripts/ranking_portability/validate_phase12_campaign_freeze.py \
      --report artifacts/generated/ranking_portability_phase12_campaign_freeze_validation.md
    echo "ARTIFACT_FREEZE_VALIDATION_PASS = YES"
    ;;
  --validate-results)
    shift
    require_arg "$@"
    python scripts/artifact/validate_supplied_results.py "$1"
    ;;
  --analysis-fixture)
    python scripts/artifact/toy_reproduction.py
    ;;
  -h|--help)
    usage
    ;;
  *)
    echo "ERROR: unknown mode: $mode" >&2
    usage >&2
    exit 2
    ;;
esac
