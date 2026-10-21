# Bounded A100 engineering-repeatability protocol

**DRAFT — author approval required before any submission.** This is a measurement/fidelity pilot, not a powered policy-ranking study. It proposes an explicit amendment to Stage 1's `2 policies ×3 fixtures ×4 repetitions` in PR #2: the user's MGPU05 design is `2 policies ×2 windows ×2 regions ×3 repetitions = 24 policy executions`. The original draft protocol files and frozen fields are unchanged. Approval of this document must be recorded before execution; MGPU03 is not retrospectively preregistered here.

## Purpose, selection and exact inputs

Establish that independently audited response IDs, token counts/content transport, timing observations and completion accounting remain consistent across repeated fresh-server executions. Describe variability and measurement precision under fixed bounded synthetic loads. Neither different outputs nor scheduler order variation across repetitions is automatically a failure: decisions must agree with the independent oracle for the actually observed clock/state, not reproduce an earlier wall-clock schedule.

Frozen candidate: `scripts/mgpu05/design.json`, verified against `design.py`, seed **20261021**. No field is selected from observed policy performance. Twelve blocks are shuffled, each containing the same two policies; six have native first and six SLAI first. This balances order overall, not perfectly within every cell (three repetitions is odd). Report position and cell jointly.

| Factor | Exact engineering choice |
|---|---|
| Policies | native FCFS; MGPU02 checked SLAI, decode limit 2, unchanged SLAI core |
| Balanced window | 12 requests, 128 input /128 output tokens each; cyclic loose/tight/medium classes |
| Boundary window | 16 requests; repeat `(prompt,output)` = `(1,256),(256,128),(64,256),(128,64)` four times; cyclic classes |
| Spread region | Request i arrives at i×0.2 seconds |
| Burst region | Four concurrent requests at each floor(i/4)×0.2 seconds |
| Offered interval | Last scheduled arrival +0.2 seconds: balanced spread 2.4 s/burst 0.6 s; boundary spread 3.2 s/burst 0.8 s |
| Tokenizer/input | Qwen pinned revision; repeat `[63122,16614,12507]` to exact length, no truncation of real data |
| Sampling/output | Temperature 0, seed 0, n=1, ignore EOS, exact max output; raw token/text evidence |
| Contract | B4096/N16/P256, context512, BF16/eager, synchronous V2 runner, chunking enabled, threshold0; prefix/speculation/transfers/parallelism off |

“Spread” and “burst” are predeclared arrival shapes, **not independently calibrated equal-relative-pressure levels**. They intentionally probe different offered rates/concurrency without fitting a saturation point. Observed occupancy and queueing determine what they actually exercised. If no useful contention or variability range is present, report it and stop for a prospective design amendment; do not tune until a preferred ordering appears. A full N=16 active boundary is a target, not guaranteed by merely offering 16 requests. Report observed max-active, max-budget, held decisions and prefill/decode coexistence from raw events.

The sufficient budget proof is `R+(16−R)×256≤4096`, R=0…16. Held decodes occupy slots. This does not guarantee KV allocation; all KV admission deviations/preemption and partial-progress cases still fail explicitly. The boundary window cannot certify >256-token prompts. All 40 Azure and all 40 Bailian historical windows have median source-reported prompts above the limit; these synthetic windows are not realistic trace coverage.

## Independence, pairing and startup amortization

One allocation runs **one predetermined two-policy block** in the manifest's order. Each policy has a new OS process group, new engine, independent empty writable compiler/cache directories, fresh KV state, identical one-request 128-input/4-output warmup, then exactly one scored cohort. Warmup is captured/audited but excluded from scored metrics; server startup/readiness is recorded separately. No repeated measured cohorts share a live engine: SLAI's cumulative batch estimator and identity registries would otherwise carry state. This is why simply executing 24 cohorts through two long-lived servers is not justified.

Twelve paired allocations safely amortize Slurm queue/placement and read-only asset verification/device probing without conflating engine state. Model weights may remain in OS/GPFS cache after the first server. Do not claim cold-start equivalence, drop OS caches or silently warm only one policy. Counterbalance policy order, record readiness/load durations separately, and investigate position effects descriptively. Eager/prefix-off settings and per-policy writable caches match the intended comparison; machine-wide filesystem/driver caches remain uncontrolled nuisance factors. No performance causality claim follows from faster startup.

Use the same reviewed environment, weights/config/tokenizer hashes, GPU SKU/capacity, CPU/memory request, driver/CUDA/NCCL/topology controls and numerical configuration across blocks. Record raw identity at each allocation; changed hardware/software is a new stratum, not silently pooled. Fixed payload IDs/hash and seeds pair the offered streams; execution directories distinguish identical request IDs. Admission is server controlled; 32 client connections exceed the largest 16-request fixture, with saturation explicitly rejected. Pre-serialize and verify inputs before timing.

## Gates and stop rules

1. **Before allocation:** author approves design amendment, candidate commit, environment pins and budget. CPU preflight verifies clean exact checkout, sources, weights, tokenizer and plan. No automatic job retry/array. An author-owned execution ledger prevents duplicate block submissions; scripts do not claim global exactly-once scheduling.
2. **First pair (two executions within the 24 ceiling):** authorize block 0 only. Stop afterward for independent review of raw seals, response binding, decoding, sampling counts, physical clock causality, metric labels and logs. A local test pass is not this gate. If either mechanism fails, the runner stops that block without launching the other mechanism after the failed round, and no further block is eligible.
3. **Remaining 11 blocks:** only after the first-pair review and renewed authorization. Every run requires independent whole-prefill decision and runner agreement, full A100 identity/readiness, exact metadata, 100% fixture completions and ID/token/text reconciliation, no partial/KV/fallback behavior, complete seals and successful cleanup. Dispatch lag p95≤10 ms and maximum≤20 ms; transport-start lag≤20 ms; failures are retained, never silently rerun.
4. **Repeatability assessment:** all 24 pass the correctness/fidelity gates. At least two repeats/cell must provide usable endpoint timing; report individually timed token coverage and SLO uncertainty bounds. Coalesced chunks are not made into tokens to satisfy coverage. Failure to obtain usable timing is an engineering NO-GO for that metric, not a policy loss.

Infrastructure interruption, deadline miss, response failure, unsupported behavior and harness defect are separate ledger categories. No statistical outlier exclusion. Preserve every attempted run and offered request. Never replace a failed cell with an unrecorded successful retry. A correctness/fidelity failure stops the pilot. Unexpected environment, startup timeout, unusable clocks or systematic dispatch lag also stops for correction. If a pair is incomplete, retain it but do not treat it as an intact paired contrast.

The 24 count is a hard initial ceiling, not a target that must be filled after a failure. Extensions, retries and altered fixtures require a prospective amendment and new authorization; they do not get hidden inside the old budget. High variability or wide intervals is an allowed outcome, not justification to keep collecting automatically.

## Precision and variability analysis

Report per-execution validity, failures/censoring, observation coverage, output digest/ID equality, client lag, scheduler queueing, TTFT/E2E, endpoint TPOT, eligible observed ITLs, callback gaps, finite-cohort throughput, SLO lower/upper bounds, occupancy and startup separately. No requirement that policy outputs be byte-identical. Any numeric/text mismatch is investigated in terms of identities and independently decoded IDs before classifying correctness.

The experimental unit is a fresh-server policy execution. For each window×region cell, retain the three paired replicate differences/ratios and raw values. Pair by block, not by whichever executions happen to be closest. Show median, min/max, mean and sample SD; CV only for positive, non-negligible means. Across the three paired differences, a descriptive t interval is `mean(d) ± t(.975,2)×s(d)/sqrt(3)`; explicitly state the normality sensitivity and severe imprecision. Avoid treating hundreds of token observations as independent replicate samples or using a bootstrap over tokens to create artificially narrow CIs.

Provisional engineering variability flag: between-run CV>10% in per-execution median TTFT or E2E, or a visible position/environment shift, requires diagnosis before main-study calibration. This is not a significance test or a claim that CV≤10% proves reproducibility. A paired relative timing interval wider than ±10% is reported as insufficient precision; no forced winner. Inspect within-cell variation before pooling cells. Do not perform ranking reversals, Kendall correlations or multiple policy winner tests on this pilot. Report stable, variable or inconclusive measurements without assuming reversals exist.

## Resource bound and prepared commands

Each future allocation: account ikoutis, partition gpu, QoS standard, one full A100, 16 CPUs, 32 GiB, **50 minutes**, no requeue. Readiness≤1200 s per policy; warmup≤60 s; each request≤120 s; arrivals≤3 s plus drain; cleanup≤45 s. Whole launcher gets TERM at 2940 s, KILL 45 s later, below Slurm's 3000 s. Asset checks and offline audit share that bound; if they exceed the available margin, fail rather than extend it. A parent timeout/hard kill may prevent sealing; raw diagnostics survive and acceptance stays NOT VERIFIED.

Hard GPU ceiling: `12 allocations ×1 GPU ×50/60 h = 10 GPU-hours`; first pair≤0.833333 GPU-hours. Count actual elapsed parent allocation once from sacct, never add batch/extern steps. No GPU-hours were consumed by MGPU05 preparation. Planning estimate after first pair: paired readiness + warmup + last-arrival/drain + cleanup/validation + observed margin; project across remaining blocks and retain the hard ceiling. Do not infer inference cost from the historical 1010-second MGPU03 allocation.

Prepared paths below are new MGPU05 locations; create/provision the reviewed checkout separately, preserving the MGPU02 checkout. No command here was submitted. After approval, set:

```bash
export MGPU05_REPO=/project/ikoutis/sv96/github/llm-serving-scheduler-lssp-mgpu05
export MGPU05_OUT_PARENT="$MGPU05_REPO/artifacts/mgpu05/physical-repeatability"
export MGPU05_EXPECTED_SHA=<author-reviewed-MGPU05-commit>
export MGPU05_BLOCK=0
export MGPU05_VENV=/project/ikoutis/sv96/github/llm-serving-scheduler-lssp-real-vllm-prep/.venv-lssp-vllm-0.27.1
export MGPU05_MODEL=/home/sv96/.cache/huggingface/hub/models--Qwen--Qwen2.5-0.5B-Instruct/snapshots/7ae557604adf67be50417f59c2c2f167def9a775
export PYTHONPATH="$MGPU05_REPO/src" PYTHONDONTWRITEBYTECODE=1
"$MGPU05_VENV/bin/python" "$MGPU05_REPO/scripts/mgpu05/repeatability.py" \
  --check-only --expected-sha "$MGPU05_EXPECTED_SHA" --block "$MGPU05_BLOCK" --model-path "$MGPU05_MODEL"
mkdir -p "$MGPU05_OUT_PARENT"
# Only after authorization; ONE pair, not a loop or array:
sbatch --export=ALL --output="$MGPU05_OUT_PARENT/slurm-%j.out" \
  --error="$MGPU05_OUT_PARENT/slurm-%j.err" "$MGPU05_REPO/scripts/mgpu05/repeatability.sbatch"
```

For an existing execution, read-only offline validation (no CUDA/framework imports, no writes):

```bash
PYTHONPATH="$MGPU05_REPO/src" "$MGPU05_VENV/bin/python" \
  "$MGPU05_REPO/scripts/mgpu05/validate.py" \
  "$MGPU05_OUT_PARENT/job-<id>/native_fcfs"
# Repeat for slai_mgpu00_checked. Missing seal is not acceptance.
```

After any future submission, monitor only the authorized initial health interval, then return; this preparation grants no execution permission. Do not automatically proceed from engineering success to calibration, a 144-run pilot or the full ranking-transfer matrix.
