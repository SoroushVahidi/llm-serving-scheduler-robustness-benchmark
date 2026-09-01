# LOAD_CALIBRATION_PROTOCOL.md

Goal: choose load levels **before** seeing which scheduler wins, so load
regions cannot be cherry-picked post hoc to manufacture a ranking-instability
finding.

## Reference-policy rule

Calibration is **policy-independent for capacity estimation, then uses
exactly one frozen reference policy** (`fifo`, chosen because it is the
simplest mechanism with no priority/deadline synthesis dependency — see
`docs/DATA_FIELD_PROVENANCE.md`) to translate raw offered load into observed
saturation behavior. No policy under actual study in RQ1–RQ6 is used for
calibration.

## Procedure

1. For each workload window, compute the maximum sustainable throughput of a
   single `GPUConfig` under `fifo` by binary-searching the inter-arrival
   compression factor λ at which `slo_violation_rate` (using the window's own
   synthesized-or-native SLOs, `docs/DATA_FIELD_PROVENANCE.md`) crosses a
   fixed threshold (0.5%, chosen before any policy-under-study is run).
   This uses the reused calibration infrastructure in
   `src/robustbench/calibration/` (`curve_fitting.py`, `simulator_adapter.py`).
2. Call that λ the window's **reference capacity** λ_ref.
3. Define four operating regions as multiples of λ_ref:
   - `LOW` ≈ 0.5× λ_ref
   - `PRE_KNEE` ≈ 0.8× λ_ref
   - `KNEE` ≈ 1.0× λ_ref
   - `OVERLOAD` ≈ 1.2× λ_ref
4. These multipliers are **preliminary** and may be adjusted per source
   family if `fifo`'s own saturation curve is not well-approximated by them
   (e.g. a source with unusually heavy-tailed output lengths may need a
   different `OVERLOAD` multiplier to reach comparable saturation) — but any
   such adjustment must be made and frozen **before** running any
   policy-under-study, and the adjustment rule itself must be documented
   here, not chosen per-result.
5. Freeze the final per-source-family multiplier table in this file before
   the Stage 2 confirmatory sweep (`docs/EXPERIMENT_CAMPAIGN_PLAN.md`).

## Pilot (this bootstrap only)

A **small pilot only** — calibrate `fifo`'s λ_ref on one synthetic trace
(`make_medium_trace`) and one BurstGPT-fixture-derived window, to confirm the
binary-search procedure terminates and produces a monotonic saturation curve.
Do not run the full multi-source calibration sweep in this bootstrap task.

## What this protocol explicitly avoids

- Never choosing load multipliers after observing a non-`fifo` policy's
  results.
- Never re-calibrating per-policy (that would silently normalize away real
  scheduler differences at exactly the load levels this benchmark exists to
  study).
- Never treating KV-pressure or concurrency proxies
  (`src/robustbench/descriptors/window_descriptors.py`) as real backend
  measurements when calibrating — they are documented proxies only.
