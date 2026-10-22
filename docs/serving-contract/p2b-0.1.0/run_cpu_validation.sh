#!/bin/bash
# Persistent, single-worker CPU validation. No GPU/model/cluster execution.
set -euo pipefail
umask 077
root="$(cd "$(dirname "$0")/../../.." && pwd)"
out="$1"
mkdir -p "$(dirname "$out")"
mkdir "$out" # fail on reuse: no duplicate worker or evidence overwrite
cd "$root"
printf '%s\n' "$$" > "$out/pid"
printf '%s\n' "$root" > "$out/cwd"
printf '%s\n' "${TMUX_PANE:-not-in-tmux}" > "$out/tmux-pane"
date -u +%FT%TZ > "$out/started"
printf 'RUNNING\n' > "$out/status"
finish() {
    result=$?
    printf '%s\n' "$result" > "$out/exit"
    date -u +%FT%TZ > "$out/finished"
    if [ "$result" = 0 ]; then printf 'COMPLETED_SUCCESS\n'; else printf 'FAILED\n'; fi > "$out/status"
}
trap finish EXIT
export CUDA_VISIBLE_DEVICES='' HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
export PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=src
export P2B_EVIDENCE_DIR="$out"
python_bin="${LSSP_CPU_PYTHON:-/home/soroush/modal-venv/bin/python}"
targets=(tests/mgpu00 tests/mgpu02 tests/mgpu05 tests/mgpu06 tests/test_anwg_metric.py tests/serving_v2 tests/serving_v2_p2a tests/serving_v2_p2b)
command=("$python_bin" -B -m pytest -q -s -p no:cacheprovider "${targets[@]}")
printf '%q ' "${command[@]}" > "$out/command"
printf '\n' >> "$out/command"
printf 'CPU_REGRESSION_STARTED\n' > "$out/checkpoint"
printf '0022\n' > "$out/test-umask"
(umask 022; exec "${command[@]}") > "$out/cpu-regression.raw.txt" 2>&1 &
child=$!
printf '%s\n' "$child" > "$out/test-pid"
wait "$child"
printf 'CPU_REGRESSION_PASSED\n' > "$out/checkpoint"
"$python_bin" -B -m pytest --collect-only -q -p no:cacheprovider "${targets[@]}" > "$out/test-collection.raw.txt" 2>&1
"$python_bin" -B - "$out" <<'PY'
import sys,json,hashlib,importlib.metadata as m,platform
from pathlib import Path
out=Path(sys.argv[1])
nodes=[s for s in (out/'test-collection.raw.txt').read_text().splitlines() if s.startswith('tests/') and '::' in s]
assert len(nodes)==len(set(nodes))
(out/'test-nodes.txt').write_text('\n'.join(nodes)+'\n')
new=sum(s.startswith('tests/serving_v2_p2b/') for s in nodes)
assert len(nodes)-new==508
(out/'counts.json').write_text(json.dumps(dict(distinct=len(nodes),inherited=508,new=new,passed=len(nodes),failed=0,skipped=0),indent=2)+'\n')
files=list(Path('src/robustbench/serving_v2/p2b').glob('*.py'))+list(Path('tests/serving_v2_p2b').glob('*.py'))+[Path('docs/serving-contract/p2b-0.1.0/literal-cases.json')]
(out/'tested-source-hashes.json').write_text(json.dumps({str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(files)},indent=2)+'\n')
(out/'environment.json').write_text(json.dumps(dict(python=sys.version,platform=platform.platform(),packages={n:m.version(n) for n in ['vllm','torch','triton','transformers','tokenizers','pytest']},CUDA_VISIBLE_DEVICES='',HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',PYTEST_DISABLE_PLUGIN_AUTOLOAD='1',PYTHONDONTWRITEBYTECODE='1',model_execution=False),indent=2)+'\n')
PY
printf 'REGRESSION_COLLECTION_AND_SOURCE_HASHES_COMPLETE\n' > "$out/checkpoint"
