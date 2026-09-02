# RANKING_PORTABILITY_PHASE12_TELEMETRY_SEMANTIC_AMENDMENT.md

Telemetry-semantics/schema-only amendment, resolved during Phase-12B
(campaign-freeze preparation), **before any scientific Pilot-V2 campaign
cell is executed**. This corrects a documentation/validator inconsistency
first exposed by the Phase-12A engineering smoke
(`docs/RANKING_PORTABILITY_PHASE12_SMOKE_FREEZE.md`,
`docs/RANKING_PORTABILITY_PHASE12_SMOKE_DEFECTS.md`).

## Discovered

During the Phase-12A engineering smoke (468 cells, 2026-09-02), before any
scientific Pilot-V2 campaign cell existed. The smoke's first run found
100/468 cells failing telemetry schema validation with
`kv_occupancy_max out of [0,1]: <1.003–1.013>`.

## Exact old semantic wording

- `docs/RANKING_PORTABILITY_TELEMETRY_IMPLEMENTATION.md`'s implementation
  map: `kv_occupancy_mean` / `kv_occupancy_max` — Unit: `fraction [0,1]`.
- `docs/RANKING_PORTABILITY_ANALYSIS_PLAN.md` § E: `mean_kv_occupancy` —
  "Mean KV-block occupancy fraction."
- `src/robustbench/simulator/telemetry.py::validate_telemetry`: validated
  by the same `_check_fraction` helper used for `batch_saturation_*` /
  `prefill_decode_contention_fraction` / `token_budget_saturation_fraction`
  — hard rejection outside `[0.0, 1.0 + 1e-9]`.
- (Phase-12A's own interim fix, now superseded by this amendment: a
  `_check_kv_occupancy` helper with an arbitrary `[0, 2.0]` ceiling.)

## Exact corrected semantic wording

`kv_occupancy_mean` / `kv_occupancy_max` are **normalized KV demand
relative to configured nominal KV capacity** — `kv_used / max_kv_tokens`,
per step, exactly as before — but this ratio is **not hard-bounded at
1.0**. It is:

- finite;
- non-negative;
- `kv_occupancy_max >= kv_occupancy_mean` (per-cell internal
  self-consistency, unchanged from before);
- **no upper numeric ceiling is imposed.** A value above 1.0 is valid and
  means realized KV demand exceeded the configured nominal capacity for
  that policy on that (window, region) combination.

Field names (`kv_occupancy_mean`, `kv_occupancy_max`) are unchanged for
schema/compatibility continuity; every place that names or documents them
must now state that values above 1.0 are valid normalized-demand readings,
not an invalid fraction.

## Reason

`kv_occupancy` is computed identically for every policy
(`compute_telemetry_summary`), but `max_kv_tokens` is enforced as a hard
admission constraint only by KV-aware policies (`kv_constrained_online`,
the `*_faithful` block-manager policies, `vllm_style_token_budget` —
confirmed by grepping the panel's policy implementations for
`max_kv_tokens` references). Several PRIMARY-panel policies (`fifo`,
`edf`, `least_laxity_first`, `estimated_service_time_first`,
`weighted_fair_share`, `admission_control`, `slai_faithful`) admit purely
on concurrency count (`max_active_sequences`) and never reference
`max_kv_tokens` at all, so aggregate KV demand from their active requests
can legitimately exceed the configured capacity whenever the token
footprint of concurrently active requests is large enough — a real,
policy-dependent property of the panel's admission-control diversity, not
an instrumentation defect. Critically, **no simulator or configuration
invariant caps how far demand can exceed nominal capacity** for a policy
that never checks it: a different window, load region, or request-size
mix could in principle push the overshoot further than the ~1.3% observed
across the smoke's three windows. An arbitrary finite ceiling (Phase-12A's
interim `2.0x`) would therefore have been just as semantically wrong as
the original `1.0` bound — merely wrong at a different threshold — so no
numeric ceiling is retained; only the genuine structural invariants
(finite, non-negative, max ≥ mean) are enforced.

## Scope discipline

- **No simulator behavior changed.** `compute_telemetry_summary`'s
  computation of `kv_occupancy_mean`/`kv_occupancy_max` is byte-identical
  to before this amendment (`kv_used / max_kv_tokens`, unchanged formula,
  unchanged aggregation).
- **No policy scheduling/admission behavior changed.** No policy file was
  modified. Which policies do or do not enforce `max_kv_tokens` is
  unchanged, unexamined-for-modification, and not itself judged good or
  bad by this amendment.
- **No metric changed.** `docs/RANKING_PORTABILITY_METRIC_DEFINITIONS.md`'s
  contract (ANWG, completion fraction, SLO-violation rate, latency,
  throughput, TTFT) is untouched — telemetry is a separate, non-metric
  schema block.
- **No frozen Phase-10/11 artifact changed.** The five immutable scientific
  hashes are unaffected (§ below) and were never referenced by this fix.
- **No scheduler outcome was used to select or tune the correction.** The
  fix was derived from the *shape* of the schema-validation failure (which
  field, and the general admission-control-diversity explanation) and from
  reading the panel policies' own source code for `max_kv_tokens`
  references — not from comparing any policy's performance, ranking, or
  metric value against another's.
- **Applies identically to every policy/source/window/region.** The
  corrected validator has no per-policy, per-source, per-window, or
  per-region special case; every cell, present or future, is validated by
  the same rule.
- **Phase-12A smoke raw values are unchanged.** The committed
  `artifacts/manifests/ranking_portability_phase12_smoke_raw.json` (468
  cells, from the post-defect-fix re-run) is not modified by this
  amendment — its `success=True`/telemetry values are re-validated
  in-place under the corrected rule (§ next document), not regenerated.
- **The scientific campaign has still not started.** Zero Pilot-V2
  scientific cells (0/18,720) exist at the time of this amendment.

## Immutable scientific hashes (unaffected; re-verified at amendment time)

| Artifact | SHA-256 |
|---|---|
| Phase-10 scientific window | `0d1aa06ccbee352207327ea369ae75f12e91c0cda006c813a41b381effd29eef` |
| Phase-10 compact index | `d78ec1087fedae02174ca093a9860c70468be336ccb1d7e6de756c81ba331e53` |
| Phase-11 prelaunch freeze | `e2564ea9484190832de50f63173c4b73ae054d6ae7008bb4ff6648c8dc917f7b` |
| Phase-11 raw FIFO calibration | `201caaf04476ad8737ef6079fc0d6cb4e864601711d0b96c88750a717d8b2a6a` |
| Phase-11 region assignments | `9fcb92f9ea1206ce185194527ada35d0e3b91bf4904be7ae23ba9ea997c17574` |

## Affected files

| File | Change | SHA-256 after amendment |
|---|---|---|
| `src/robustbench/simulator/telemetry.py` | `_check_kv_occupancy`: removed the arbitrary `2.0x` ceiling; now checks finite + non-negative only (max≥mean check unchanged, applies to this field as before) | `3f27807956d876b12ba76fa603f38c959ad47aad8165372e77b64a9b733785e8` |
| `docs/RANKING_PORTABILITY_TELEMETRY_IMPLEMENTATION.md` | `kv_occupancy_mean`/`kv_occupancy_max` row: unit corrected from `fraction [0,1]` to `normalized demand, [0, ∞)` | `ff5ee69e106ae0952ca6453d6cd34e472e9132347e2c984fbb6668d1add12874` |
| `docs/RANKING_PORTABILITY_ANALYSIS_PLAN.md` | `mean_kv_occupancy` row: description corrected to note it is not hard-bounded at 1.0 | `0a97bbfddb8ec1202200592d6a2172575649f53d6f579c1ad0e551ee567c5d7f` |
| `tests/test_ranking_portability_telemetry.py` | Replaced the now-incorrect "5.0 is wildly out of range" test with `test_validator_accepts_large_kv_occupancy_no_arbitrary_ceiling` (a large finite value is valid) and `test_validator_still_rejects_kv_occupancy_max_below_mean` (internal consistency still enforced); the small-overshoot and negative/non-finite regression tests from Phase-12A are retained unchanged | `fdea14804853c60fc3f7517938928e6db05711c71ad3f4e1e076213c88fa6322` |

`docs/RANKING_PORTABILITY_PHASE12_SMOKE_DEFECTS.md` (the Phase-12A defect
record) is **not rewritten** — it remains the accurate historical record
of what Phase-12A found and its own interim fix. This document is the
amendment on top of it, not a replacement.

## Amendment identity

`amendment_sha256 = da85c2d52e7018ecee26994c4ff38b7c3a08deb58b65ee3a3ab20f9c56736061`

(SHA-256 over the sorted-key JSON of: parent Phase-12A smoke branch SHA
`38188eca740c3bfeafa0463c80aaaff34b725e5a`, the 4 affected files' SHA-256
above, and the exact old/corrected semantic wording strings.)

`TELEMETRY_SEMANTIC_AMENDMENT_RESOLVED_BEFORE_CAMPAIGN = YES`
