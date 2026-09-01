# EXPERIMENT_CAMPAIGN_PLAN.md

Estimated scope for the future campaign. **Stage 2 and beyond are not
launched in this bootstrap task.**

## Estimated scope (confirmatory sweep, Stage 2)

- Workload sources: 4 primary (BurstGPT, Azure 2023, Azure 2024, Bailian/Qwen)
  + 1 domain-OOD (TraceLab, pending license/schema re-verification) = 5.
- Windows per source: ~40 (targeting the sample-complexity study in
  `docs/STATISTICAL_ANALYSIS_PLAN.md` §F to need well under this).
- Load levels: 4 (LOW/PRE_KNEE/KNEE/OVERLOAD).
- Policies: 13 primary panel (`docs/POLICY_COMPARABILITY_AUDIT.md`) + 2
  secondary-stratum (`distserve_faithful`, `llumnix_faithful`, run separately).
- Seeds/repetitions: 5 per cell (matches the real-system validation plan's
  repetition count for later comparability).

**Estimated experiment cells:** 5 sources × 40 windows × 4 load levels × 13
policies × 5 seeds ≈ **520,000 simulated cells** for the primary panel alone
(secondary-stratum policies add a smaller separate sweep since they are not
pooled with the primary 13).

## Compute estimate

The reused simulator is a pure-Python deterministic iteration-level engine
(no GPU required for simulation itself; GPU is only needed for Stage 4 real
validation). A single cell on a small window (order-of-magnitude: a few
hundred to a few thousand requests) completes in well under a second based
on this bootstrap's smoke tests (4 tests including a full simulator run
completed in 1.5s total); budget conservatively at ~0.5–2 CPU-core-seconds
per cell to account for larger real-trace-derived windows. At 520,000 cells
this is roughly **70–290 CPU-core-hours** for the primary sweep — trivially
parallelizable (see below), not a GPU campaign.

## Storage

Each `PolicyOutcomeRow` is a small flat record (~30 float/int/string fields).
At 520,000 rows plus descriptor/provenance tables, expect low tens of MB in
Parquet — no special storage planning needed beyond `results/` /
`artifacts/` being gitignored (already configured).

## Parallelization / SLURM layout

- Fully embarrassingly parallel across (source, window, load_level, policy,
  seed) — one job array task per (source, load_level) shard is a reasonable
  granularity (20 shards for the primary sweep), each running all
  policies × windows × seeds within that shard sequentially.
- Checkpoints/resume: write `PolicyOutcomeRow`s incrementally per shard to a
  shard-local Parquet/JSONL file; a resumed job skips
  `(workload_window_id, load_level, policy_id, seed)` tuples already present
  in its shard's output file (idempotent by construction, matching the
  reused adapters' `derived_record_id` determinism discipline).
- Recommended: modest per-shard CPU allocation (2–4 cores), short walltime
  (well under an hour per shard given the per-cell estimate above), array
  job with `--array=0-19`.

## Stages

- **Stage 0 — small calibration pilot.** `docs/LOAD_CALIBRATION_PROTOCOL.md`'s
  pilot only. Also: port the Bailian/Qwen adapter to the `TraceAdapter`
  interface, and independently re-inspect the TraceLab schema/license
  (`docs/DATA_LICENSE_AUDIT.md`).
- **Stage 1 — workload discriminability pilot.** Confirm each source family,
  at a small number of windows, produces non-degenerate `WindowDescriptor`
  spread (not all windows identical) before committing to the full window
  count.
- **Stage 2 — frozen full simulation sweep.** The ~520K-cell sweep above,
  run only after `docs/SPLIT_PROTOCOL.md` manifests are frozen and hashed
  and `docs/GO_NO_GO_GATES.md` Gates A–D pass.
- **Stage 3 — statistical analysis.** `docs/STATISTICAL_ANALYSIS_PLAN.md`
  §A–G against the frozen Stage 2 output only.
- **Stage 4 — targeted real-vLLM validation.** `docs/REAL_SYSTEM_VALIDATION_PLAN.md`.
- **Stage 5 — sensitivity/robustness experiments.** E.g. re-run §D/§E with an
  alternative SLO-synthesis rule (per `docs/DATA_FIELD_PROVENANCE.md` item 3)
  to check that headline reversals are not artifacts of one synthesis choice.
- **Stage 6 — frozen dataset release and manuscript finalization.**
  `docs/DATASET_V2_SCHEMA.md`, paper skeleton in `paper/`.

**This bootstrap task completes Stage 0's pilot slice only** (calibration
pilot smoke-tested; Bailian porting and TraceLab re-verification are next-
session action items, not done here).
