# MGPU05 local validation record

**225 passed, 0 failed, 0 skipped**, 14 existing Torch deprecation warnings; 11.27 seconds. This comprises the unchanged **151-test MGPU02 validation set** plus **74 new MGPU05 tests**. Full stdout and JUnit test identities are in `pytest.log` and `pytest.xml`.

Executed directly through Codex:

```bash
CUDA_VISIBLE_DEVICES='' PYTHONDONTWRITEBYTECODE=1 /home/soroush/modal-venv/bin/python -m pytest \
  tests/mgpu00 tests/mgpu02 tests/test_anwg_metric.py tests/mgpu05 -q \
  --junitxml=artifacts/mgpu05/local-validation/pytest.xml
```

Coverage: hand-specified ID/token/text/timestamp/SLO histories; corrupt response/engine IDs, classes, tokens, counts, text, finish/DONE and clocks; BPE non-unique re-encoding; coalesced observations; single-token undefined TPOT; partial prefixes; timeout/cancellation/errors/EOF/saturation/admin censoring; actual loopback HTTP/SSE fragmentation and transport tracing; hash chain/seal tampering; fixed pairing/budget/whole-prefill proof; actual vLLM CPU scheduler/KV objects and synthetic completions; unchanged partial/KV rejection; actual completion-request schema; fail-closed policy choice; startup and cleanup failure sealing. Original MGPU02 differential/distributed/metadata tests are included unchanged.

No GPU, model forward pass, server model load, Slurm submission or Actions was used. Local tests do not validate physical timing, target-environment inference, numerical reproducibility or instrumentation overhead. No errors are hidden as physical successes.

`assets.json` records CPU-only model/tokenizer/source verification in the **local test environment**. `api-upstream.json` records exact matches to the authoritative vLLM v0.27.1 API/identity sources. `wulver-readonly.json` records only read-only package metadata, file hashes and Rust tokenization on the existing Wulver environment; no Torch/CUDA import or repository modification. Model/tokenizer/config/API hashes and fixture encoding agree across these checks. Wulver versions differ from local versions; the launcher pins Wulver's actual versions in `scripts/mgpu05/environment.json`. The full new suite was not run in that target environment.

Shell syntax, Python AST parsing, CLI help/import (without GPU/framework imports for the offline validator), staged whitespace and unchanged historical/protocol-source checks are recorded in `checks.txt`. A future physical run must separately establish content transport and timing integrity. Original MGPU03 evidence remains untouched.
