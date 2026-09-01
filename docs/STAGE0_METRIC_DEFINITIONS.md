# STAGE0_METRIC_DEFINITIONS.md

Authoritative definition of the Stage-0 primary metric, per
`docs/STAGE0_DISCRIMINABILITY_PROTOCOL.md` ("Primary metric for the
pilot"). Not copied from LLM 2026 — this is this project's own
`RunMetrics.arrival_normalized_weighted_goodput`
(`src/robustbench/core/metrics.py::compute_metrics`), which already
existed in this codebase; this doc documents and tests it, it does not
introduce a new implementation.

## Arrival-Normalized Weighted Goodput (ANWG)

```
ANWG = sum(weight_i * 1[completion_time_i <= slo_deadline_i]  for i in COMPLETED)
       -----------------------------------------------------------------------
       sum(weight_i  for i in ALL ARRIVALS)
```

- `weight_i = request.priority` if `priority > 0`, else `1.0` (unit weight
  fallback — a request with unset/zero priority is not excluded).
- The **denominator is over every arriving request** in the window —
  dropped, rejected, and unfinished requests contribute their weight to the
  denominator with **zero numerator credit**. This is what "arrival-
  normalized" means and is the key correction over the older
  `weighted_goodput` metric (below).
- Edge cases (see `tests/test_anwg_metric.py`):
  - `num_total == 0` (no arrivals at all): `ANWG = NaN` (undefined, not 0).
  - Nonzero arrivals, zero completions: `ANWG = 0.0` (a real, meaningful
    zero, distinct from the NaN case above).

## Explicitly distinguished from three other metrics already in `RunMetrics`

1. **`weighted_goodput`** (a.k.a. "priority-weighted SLO goodput" /
   "conditional weighted SLO attainment"): same numerator, but the
   denominator is `sum(weight_i for i in COMPLETED only)`. A policy that
   drops 90% of requests but perfectly meets SLO on the 10% it completes
   scores `weighted_goodput = 1.0` yet `ANWG` near `0.1` — ANWG is the
   metric that cannot be gamed by dropping hard requests.
2. **`completion_fraction`** / **`request_throughput`**: measure whether
   requests finish at all, not whether they finish on time. A policy that
   completes 100% of requests arbitrarily late has
   `completion_fraction = 1.0` but `ANWG` can be `0.0` if every completion
   misses its deadline (`test_anwg_throughput_and_completion_are_not_conflated_with_anwg`).
3. **`weighted_completion_fraction`**: the un-conditioned analogue of
   `completion_fraction` (weight of completed / weight of all arrivals) —
   ANWG additionally requires the completion to have met its SLO deadline,
   `weighted_completion_fraction` does not.

## Test coverage (`tests/test_anwg_metric.py`, unit-level against
`compute_metrics`, no simulator/frozen data involved)

Perfect completion (ANWG=1.0), zero completion (ANWG=0.0), mixed SLO
success/failure, priority-weighted requests, zero-priority fallback to
unit weight, the `num_total==0` NaN edge case, ANWG-vs-`weighted_goodput`
divergence under drops, and ANWG-vs-throughput/completion divergence under
late-but-complete responses — 8 tests, all passing.
