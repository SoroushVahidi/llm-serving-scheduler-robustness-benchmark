# Prepared MGPU02 full-A100 smoke — not submitted

This is one engineering smoke, one fresh native engine and one fresh checked-SLAI
engine, with one warmup plus 12 fixture requests per engine. It is not a ranking
measurement, repetition study, pilot, TP2 job or authorization to run.

## Configuration and limits

- Full `gpu:a100:1`, one node/task, account `ikoutis`, partition `gpu`, QoS
  `standard`, 16 CPUs, 32 GiB, no requeue or array, 35-minute wall-time limit.
- Same installed vLLM 0.27.1 environment and Qwen revision
  `7ae557604adf67be50417f59c2c2f167def9a775` used by MGPU01. Runtime checks seven
  source hashes and five model/tokenizer file hashes; no downloads.
- BF16, context 512, token budget 4096, max active 16, admitted prompt cap 256,
  fixture prompts/outputs 128/128, decode limit 2. Chunking ON, threshold zero,
  prefix cache/async OFF, eager, V2 runner, TP/PP/DP=1. Per-step checks forbid splits.
- API readiness is finite and at most 1200 seconds per server. Independent total
  process deadline 1950 seconds plus 45-second kill grace; Slurm ceiling 2100
  seconds. Two maximum readiness windows are not promised to fit. Slow startup
  fails the bounded job; no retry or automatic deadline extension follows.
- Durable Slurm stdout/stderr, bootstrap log, progress/device checkpoints, source
  identity through tested Git SHA, launch arguments/identity, server/startup logs,
  warmup, raw replay, validated per-policy results, summary or failure. Abrupt
  process/Slurm kill may prevent final summary: missing summary is NOT VERIFIED,
  never PASS. Preserve parent Slurm accounting alongside logs on later review.

## Prepared submission

Run only in a later authorized session. The final tested SHA and remote checkout
are recorded in PR #1 and the MGPU02 final report. Verify that the isolated remote
worktree's HEAD is that SHA. Do not substitute the old MGPU00 checkout or an
untested branch tip. `MGPU02_EXPECTED_SHA` is the tested commit, not a moving ref.

On Wulver, with `MGPU02_EXPECTED_SHA` set to that exact reviewed commit:

```sh
export MGPU02_REPO=/project/ikoutis/sv96/github/llm-serving-scheduler-lssp-mgpu02
export MGPU02_OUT_PARENT=/project/ikoutis/sv96/github/llm-serving-scheduler-lssp-mgpu02/artifacts/mgpu02/physical-smoke
export MGPU02_READINESS_TIMEOUT_S=1200
: "${MGPU02_EXPECTED_SHA:?Set the exact tested MGPU02 commit from PR 1}"
test "$(git -C "$MGPU02_REPO" rev-parse HEAD)" = "$MGPU02_EXPECTED_SHA"
mkdir -p "$MGPU02_OUT_PARENT"
/apps/slurm/current/bin/sbatch --export=ALL \
  --output="$MGPU02_OUT_PARENT/slurm-%j.out" \
  --error="$MGPU02_OUT_PARENT/slurm-%j.err" \
  "$MGPU02_REPO/scripts/mgpu02/smoke.sbatch"
```

This command has **not** been executed. The wrapper checks SHA and tracked-tree
cleanliness. New outputs go under a new MGPU02 path, never historical directories.
After an authorized launch, record job ID, command, log paths and initial health;
monitor only about two minutes using `squeue`/`sacct`, then return without waiting
for completion. Inspect results on a later user turn. Never infer completion from
successful submission or API readiness.

Maximum requested allocated GPU-hours: `1 * 35/60 = 0.583333`; no repeated job,
array or automatic retry. Cluster teardown/accounting overhead is not measured.
MGPU02 itself consumed **0 GPU-hours**.

## Acceptance criteria

All gates must PASS for a successful engineering smoke. A missing/unreached gate
is NOT VERIFIED. Any observed contradiction is FAIL and invalidates the smoke.
No subset of PASS gates is sufficient for physical ranking evidence.

| Gate | PASS requires | FAIL / NOT VERIFIED |
|---|---|---|
| Identity/configuration | Tested SHA, matching source/tokenizer hashes; effective contract passes on both schedulers; all full-A100 device checks pass | Mismatch/unsupported config/device is FAIL; not reached is NOT VERIFIED |
| Readiness | Expected served model on `/v1/models`, each server within its deadline | Exit/wrong model/timeout FAIL; not attempted NOT VERIFIED |
| Native warmup and fixture | Warmup completes; all 12 fixture requests complete exact input/output lengths, no errors/timeouts; transport timestamps and dispatch gates pass | Any observed failure FAIL; no serving evidence NOT VERIFIED |
| Checked-SLAI warmup and fixture | Same completion gates plus correct class transport/priority and at least one fixture hold event | No mechanism activation FAIL; engine not reached NOT VERIFIED |
| Scheduling decisions | All recorded inputs/plans independently audited; native FCFS and SLAI selections agree with reference; whole-prefill invariant holds; no preemption/mismatch | Any mismatch FAIL; incomplete decision record NOT VERIFIED |
| Actual progress | Every nonempty plan has exactly matching native runner completion/state evidence; per-request sampled and computed totals reconcile with client output counts | Divergence FAIL; missing completion NOT VERIFIED |
| Overall engineering result | Two validated policy files, common workload hash, final `summary.json` with success, Slurm COMPLETED/exit 0 | FAILED/CANCELLED job cannot PASS; missing final artifacts NOT VERIFIED |
| Scientific ranking / reproducibility / TP2 | **Not assessed by this smoke** | Always NOT VERIFIED; ranking and TP2 remain NO-GO |

The summary is necessary but not sufficient: later review must inspect accounting,
raw logs, per-round audits and identity. No two-round timing comparison should be
reported as a scheduler ranking or an estimate of speedup.
