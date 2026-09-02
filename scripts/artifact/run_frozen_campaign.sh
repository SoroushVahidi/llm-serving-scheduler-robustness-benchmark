#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

usage() {
  cat <<'USAGE'
Usage:
  ./scripts/artifact/run_frozen_campaign.sh --confirm-scientific-execution --dry-run-shard SHARD_ID
  ./scripts/artifact/run_frozen_campaign.sh --confirm-scientific-execution --execute-shard SHARD_ID

This is the explicit scientific-execution entrypoint. It is intentionally
separate from verify_artifact.sh. Execution also requires:
  LSSP_ALLOW_SCIENTIFIC_EXECUTION=YES

No Slurm submission is performed here. Slurm users should generate/review the
sbatch file with scripts/ranking_portability/generate_phase12_sbatch.py and
submit it manually under their site policy.
USAGE
}

if [[ "${1:-}" != "--confirm-scientific-execution" ]]; then
  usage >&2
  exit 2
fi
shift

if [[ "${LSSP_ALLOW_SCIENTIFIC_EXECUTION:-}" != "YES" ]]; then
  echo "ERROR: set LSSP_ALLOW_SCIENTIFIC_EXECUTION=YES for scientific execution." >&2
  exit 2
fi

export PYTHONPATH="${ROOT}/src${PYTHONPATH:+:${PYTHONPATH}}"

case "${1:-}" in
  --dry-run-shard)
    [[ -n "${2:-}" ]] || { usage >&2; exit 2; }
    python scripts/ranking_portability/run_phase12_campaign_shard.py --shard-id "$2" --dry-run
    ;;
  --execute-shard)
    [[ -n "${2:-}" ]] || { usage >&2; exit 2; }
    python scripts/ranking_portability/run_phase12_campaign_shard.py --shard-id "$2" --execute
    ;;
  -h|--help|"")
    usage
    ;;
  *)
    echo "ERROR: unknown execution mode: $1" >&2
    usage >&2
    exit 2
    ;;
esac
