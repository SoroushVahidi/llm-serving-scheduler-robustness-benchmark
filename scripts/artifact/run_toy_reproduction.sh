#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

export LSSP_ARTIFACT_REPRO_PREFREEZE_RESULT_BLIND=YES
export PYTHONPATH="${ROOT}/src${PYTHONPATH:+:${PYTHONPATH}}"

python scripts/artifact/toy_reproduction.py "$@"
