# REAL_SYSTEM_VALIDATION_PLAN.md

**Not run in this bootstrap task.** Designs a future validation campaign only.

## Primary question

Does relative scheduler ordering — especially the specific rank reversals
identified in the simulated Stage 2/3 analysis (`docs/EXPERIMENT_CAMPAIGN_PLAN.md`)
— reproduce on real vLLM/native serving? **Not** whether simulated absolute
latency equals hardware latency (see `docs/CLAIM_BOUNDARIES.md`).

## Design

- **~4 representative schedulers/mechanisms**: one from each stratum in
  `docs/POLICY_COMPARABILITY_AUDIT.md` that has a real or faithfully
  reimplementable execution path — e.g. `fifo`, `vllm_faithful` (or the
  chunked-prefill successor), `sarathi_faithful`, `weighted_fair_share`.
  `apt_serve_faithful` is excluded (scaffolding-only, not validated).
- **3–4 workload families**: at minimum one synthetic stress family and two
  independent real-trace-derived families (e.g. BurstGPT-derived, Azure-2024-
  derived), chosen specifically to include at least one predicted rank
  reversal from the simulated analysis.
- **2 load regions**: `PRE_KNEE` and `KNEE`/`OVERLOAD` from
  `docs/LOAD_CALIBRATION_PROTOCOL.md`, recalibrated against the real engine's
  own saturation point (the simulator's λ_ref is not assumed to transfer).
- **≥5 repetitions** per (scheduler, workload family, load region) cell.
- **Fixed workload manifests**, generated once and reused verbatim across
  schedulers and repetitions (no re-sampling per cell).
- **Warmups** discarded before measurement (exact warmup duration to be set
  during pilot, not tuned per scheduler).
- **Randomized or ABBA ordering** of scheduler/cell execution to avoid
  confounding with time-of-day GPU-sharing effects.

## Primary statistics

- **Sign agreement**: does the simulated pairwise winner match the real
  pairwise winner, per pair per cell.
- **Kendall tau** between the simulated ranking and the real-engine ranking,
  per cell.
- **Pairwise effect confidence intervals** (bootstrap over repetitions).
- **Rank-reversal agreement**: for pairs where simulation predicted a
  load-dependent reversal, does the real engine show the same reversal at
  the corresponding (recalibrated) load region.

## Reused infrastructure

`src/robustbench/real_llm/calibration_common.py` (generic real-vLLM
measurement helper, reused per `docs/PROVENANCE.md`) — reused for measurement
plumbing only. This project's own validation results are new; LLM 2026's
existing real-vLLM validation findings are `PRIOR_RESULT_REFERENCE_ONLY`
(citable, never restated as this project's evidence — see
`docs/OVERLAP_LEDGER.md`).

## Explicitly not required

Exact match between simulated and hardware absolute latency/throughput
values. A scheduler ranking that agrees in direction but differs in
magnitude counts as a successful validation for this project's purposes.
