# STAGE0_LAUNCH_HANDOFF_20260901.md

The real, frozen 1,080-cell Stage-0 discriminability pilot
(`docs/STAGE0_DISCRIMINABILITY_PROTOCOL.md`) is launched on Wulver.
Health-checked for ~3 minutes and left running unattended per instructions.

## Provenance

- Launch branch: `research/stage0-orchestration-prelaunch-20260901`
- Launch SHA: `17de339f4a0f5f352c5d847e29d33b789f171fa6`
- `main` SHA (unchanged): `6a8277993e4ef19b10e3fa53baf476d0d0d490f0`
- `stage0_prelaunch_freeze.json` sha256: `a13af1f5a27593d39bec4a1a0e9be99c54a75b7c33daefa07c4af27d2f6f5ae8`
- `stage0_launch_20260901.json` (Wulver-only, gitignored, same convention as every other generated manifest): repo_sha, plan hash, cost-estimates hash, expected matrix size
- Protocol hash: `6fd7f6b5c6f0f9289a5a373cf0b9f00c819049ae3a4b4a86bfe8578cf5bd26f5`
- Window manifest hash: `0984ca4ee5c2d3f273b1de8c8906f1b0d864e60b18f0aeea6988219f6c1577c2`
- Calibration manifest hash: `e82736e7b401aa8563711dcb2c87e22a456c503f6634d08fed8610ba054a3e8b`
- Policy registry code hash: `3646a2a5bcae9f9422b452a875ae22a7f964278b3af02f7c21f078ada49a2a71`
- Analyzer code hash: `d299c67b7f7049eb8327a647c558ee0e88dd7b87adb49eb6f483b1bb24621b42`
- Stage-0 plan hash (the actual submitted 1,080-cell plan): `c23c24ba0a03f856f598397397323902ad5fd77da367cbe3fc2e6540e8c43b81`

All frozen hashes were independently re-verified against current files on
Wulver immediately before submission -- exact match, no drift.

## Timing evidence (operational only, not scientific)

- `results/stage0_timing_only/` -- 54 real cells (3 windows x 3 regions x 6
  policies x 1 rep), every row labeled
  `scientific_status=TIMING_ONLY_DO_NOT_ANALYZE`.
- `vllm_faithful` median 18.19s/cell (max 20.01s) -- ~100x every other
  policy (fifo/edf/kv_constrained_online/vllm_style_token_budget: ~0.1-0.2s
  median; sarathi_faithful: ~0.21s median).
- `artifacts/manifests/stage0_policy_cost_estimates.json` (conservative,
  max-observed per policy) feeds `shard_cells()`'s greedy LPT balancer.
  Verified against the actual submitted 1,080-cell plan: 6 shards, each
  **exactly** 180 cells / ~712.5s (~11.9 min) estimated, perfectly balanced
  (ratio 1.00) -- vs. 31x-175x imbalance under naive stride slicing at
  every candidate shard count tested (4, 6, 8, 9, 12) on the real plan.

## SLURM

- Array job: **1213964** (`--array=0-5`, 6 shards, `--cpus-per-task=2`,
  `--mem=4G`, `--time=01:00:00` -- ~5x safety margin over the 11.9 min
  estimate).
- Merge job: **1213965**, `--dependency=afterany:1213964` (afterany, not
  afterok, so failed cells stay visible), `--time=00:30:00`. Runs
  `stage0_harness.py validate` then the frozen 5-criterion analyzer. Does
  **not** auto-launch anything further regardless of verdict.
- Submitted from `STAGE0_WORKTREE_DIR=/project/ikoutis/sv96/github/llm-serving-scheduler-robustness-stage0-prelaunch`
  (the harness does not exist in the original benchmark repo checkout).
- Logs: `logs/stage0_pilot/array_1213964_{0..5}.{out,err}`,
  `logs/stage0_pilot/merge_1213965.{out,err}` (under the worktree above).
- Scientific result directory: `results/stage0_v1/` (`cells/` subdir, one
  JSON per cell, `scientific_status=null` for every real cell -- distinct
  from `results/stage0_smoke_only/` and `results/stage0_timing_only/`,
  never mixed).

## Three-minute health check result

Submitted 2026-09-01 ~19:36:5x UTC. Polled at +4s, +32s, +44s, +51s:

- All 6 array tasks reached `RUNNING` within 4 seconds of submission (no
  PENDING/config-failure reason).
- 0 lines in every `.err` log at every poll.
- 28 cells written successfully (`success: true`) by the last poll, all
  schema-valid, correct source/window/policy/hash provenance, all
  `scientific_status: null` (correctly unlabeled as real evidence).
- Cells observed so far are all `azure_llm_2024` (expected: the cost-aware
  greedy balancer processes each shard's `vllm_faithful` cells first --
  same estimated cost, tie-broken alphabetically by `cell_id`, and
  "azure_llm_2024" sorts before "bailian_qwen"/"burstgpt" -- other sources
  will appear as each shard works through its `vllm_faithful` cells).
- No missing-path loops, no policy-factory errors, no schema failures, no
  NaN/Inf, no permission errors.

**Verdict: `STAGE0_LAUNCHED_HEALTHY`.**

## Commands for later inspection

```bash
ssh wulver
cd /project/ikoutis/sv96/github/llm-serving-scheduler-robustness-stage0-prelaunch

# 1. Completion
squeue -u $USER
sacct -j 1213964,1213965 --format=JobID,JobName,State,Elapsed,ExitCode,MaxRSS

# 2. Progress / status
SRC=/project/ikoutis/sv96/github/llm-serving-scheduler-robustness-benchmark
PYTHONPATH=src $SRC/.venv312/bin/python3 scripts/stage0/stage0_harness.py status --output-dir results/stage0_v1

# 3. Exact-matrix validation (also run automatically by the merge job)
PYTHONPATH=src $SRC/.venv312/bin/python3 scripts/stage0/stage0_harness.py validate --output-dir results/stage0_v1

# 4. Five-criterion GO/NO-GO result (written by the merge job)
cat results/stage0_v1/stage0_analysis_report.json | python3 -m json.tool

# 5. Logs if anything looks wrong
tail -50 logs/stage0_pilot/array_1213964_*.err
tail -50 logs/stage0_pilot/merge_1213965.err
```

Do NOT launch Stage 1, Stage 2, the ~520,000-cell confirmatory campaign, or
real-vLLM validation automatically after this completes -- even if the
verdict is `STAGE0_GO`. Validate the exact matrix and apply the five
frozen criteria first; the joint paper decision is a separate, deliberate
next step.
