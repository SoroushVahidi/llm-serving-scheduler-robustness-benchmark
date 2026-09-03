# RQ6_REAL_VLLM_CALIBRATION_PROTOCOL_20260902.md

`REAL_VLLM_SCIENTIFIC_VALIDATION = NOT_STARTED`. This document freezes the
real-engine load-calibration *procedure* only. It does not report, and must
not be edited after, any real calibration measurement.

**2026-09-03 update: see `configs/real_vllm/rq6_calibration_manifest_v2_20260903.json`.**
The machine-readable manifest originally referenced from this document
(`rq6_calibration_manifest_20260902.json`) is superseded (left in place,
unmodified, as an immutable record) by a v2 manifest that resolves the
calibration-population question left open here and implements the
SLO/weight prerequisite in "What is frozen now vs. what remains open"
below: calibration runs per frozen window (`CALIBRATION_UNIT =
ONE_FROZEN_WINDOW`, 120 independent calibrations = 3 sources x 40
windows/source), never per concatenated source trace -- see
`docs/RQ6_REAL_VLLM_SCIENTIFIC_PROTOCOL_20260902.md`'s "Calibration
population" section for the forensic evidence and reasoning. The procedure
described in this document (region grid, knee-detection criterion,
bisection shape, failure handling, warmup) is otherwise **unchanged** —
only the population it's applied *to* was previously unspecified.

## Why this is not a new methodology

`docs/LOAD_CALIBRATION_PROTOCOL.md` and
`src/robustbench/ranking_portability/calibration.py` already froze a
six-region, single-reference-policy calibration procedure for the simulator
(Phase-11, 720 cells). RQ6's own case-selection manifest
(`artifacts/manifests/phase12_rq6_case_selection_20260902.json`) uses the
`HIGH_PRESSURE` label from that exact six-region grid. This document
reuses that procedure's *definition* for the real engine — never its
numeric `lambda_ref` result (per the explicit instruction not to reuse the
simulator's `lambda_ref` directly, and because the whole point of a
hardware validation is that the real engine's own saturation point is not
assumed to match the simulator's).

## Reference policy

```
REFERENCE_POLICY = vllm_faithful
```

Mirrors the simulator's choice of `fifo` as calibration reference
(`docs/LOAD_CALIBRATION_PROTOCOL.md`: "the simplest mechanism with no
priority/deadline synthesis dependency"). `vllm_faithful` is vLLM's native
FCFS scheduling (`--scheduling-policy fcfs`, no custom `--scheduler-cls`),
already built and validated end-to-end in
`scripts/real_vllm/wulver_engineering_gate.py` (job 1219334,
`pass_gate: true`). `slai_faithful` (the policy under actual RQ6 study) is
never used for calibration, exactly as `docs/LOAD_CALIBRATION_PROTOCOL.md`
requires for its simulator analogue ("No policy under actual study in
RQ1–RQ6 is used for calibration").

## Six-region grid (reused verbatim)

```
REGION_FACTORS = {
  "LOW": 0.5, "PRE_KNEE": 0.8, "KNEE": 1.0,
  "POST_KNEE": 1.1, "OVERLOAD": 1.2, "HIGH_PRESSURE": 1.5,
}
```

Identical names and multipliers to `REGION_FACTORS` in
`src/robustbench/ranking_portability/calibration.py`. Only the *unit* they
multiply changes: the simulator multiplies its own `lambda_ref`; this
protocol multiplies the real engine's own, independently measured
`lambda_ref_real`.

## Knee-detection criterion (reused definition, real-engine measurement)

The simulator's `compute_lambda_ref` binary-searches the FIFO inter-arrival
compression factor at which `slo_violation_rate` crosses a fixed 0.5%
threshold (`PHASE11_SLO_VIOLATION_THRESHOLD = 0.005`), over
`PHASE11_BISECTION_ITERATIONS = 30` iterations, search bounds
`10**-2.0 .. 10**4.0` in factor space. This protocol reuses that same
criterion and search shape against real measurements:

```
lambda_ref_real = argmin_factor { factor : slo_violation_rate_real(factor) >= 0.005 }
```

found by bisecting in `log10(factor)` space over the same bounds
(`[-2.0, 4.0]`) for the same `30` iterations, with the same tie behavior
(if the lower bound already exceeds 0.5% violation, return the lower
bound; if the upper bound is still under 0.5%, return the upper bound).

`slo_violation_rate_real(factor)` is computed exactly as
`docs/REAL_SYSTEM_METRIC_MAPPING.md` defines SLO/goodput for the real
engine: `1 - (weighted count of requests with t_done <= slo_deadline) /
(weighted count of completed requests)`, using the **same**
`slo_deadline`/`weight` values the frozen Phase-12 window already
overlays onto each request (`SYNTHESIZED_IMPUTED` per
`docs/DATA_FIELD_PROVENANCE.md`) — carried through unmodified into the
real-vLLM workload manifest, never resynthesized independently for the
real run. **This is currently a named, open prerequisite, not yet
implemented**: `docs/REAL_SYSTEM_METRIC_MAPPING.md` explicitly marks ANWG
as `UNAVAILABLE` from the real collection layer today, because
`calibration_common`/`vllm_openai_client` do not yet attach a per-request
`slo_deadline`/`weight` or compute `t_done`-vs-`slo_deadline` client-side.
Implementing that attachment (reusing the exact frozen per-source overlay
values, not a new synthesis) is a prerequisite for running this
calibration for real, and is tracked as the concrete next engineering
step (see the workload-manifest contract's open item).

## What is frozen now vs. what remains open

**2026-09-03: all rows below are now frozen and implemented** (see the v2
manifest note above) — this table is kept for its historical record of
what was still open as of 2026-09-02.

| Frozen now | Was not yet frozen as of 2026-09-02 — resolved 2026-09-03 |
|---|---|
| Reference policy (`vllm_faithful`) | Exact per-source `slo_deadline`/`weight` overlay values carried through — implemented in `robustbench.real_llm.rq6_slo_metrics`, sourced unmodified from each workload manifest's `base_slo_deadline_s`/`weight` fields |
| Region grid + multipliers (reused from Phase-11) | `real_lambda_ref` per **window** (not per source — see "Calibration population" in the scientific protocol doc), a measurement produced by `rq6_calibration.bisect_lambda_ref_real` against a live vLLM server |
| Bisection search shape (bounds, iteration count, threshold) | — |
| Rule: one reference policy for all three sources, no per-source or per-policy retuning | — |
| Timeout/failure handling: identical to the simulator's fail-closed posture — a candidate factor that cannot be measured (server crash, timeout) is treated as `slo_violation_rate = 1.0` for that factor, mirroring `_slo_violation_rate_at`'s `num_completed == 0 -> return 1.0` fallback | — |
| Warmup: one untimed warmup request per server start before any measured candidate factor, discarded from all statistics (matches the existing engineering-gate pattern in `wulver_engineering_gate.py::_calibration`) | — |

## Explicitly forbidden (mirrors `docs/LOAD_CALIBRATION_PROTOCOL.md`)

- Never choosing/adjusting region multipliers after observing `slai_faithful`'s results.
- Never calibrating `slai_faithful` and `vllm_faithful` separately.
- Never treating a proxy (e.g. GPU KV-cache percentage) as the SLO criterion — only the request-level `t_done` vs. `slo_deadline` comparison above counts.
