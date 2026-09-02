# Phase-11 calibration plan (design only)

This document is intentionally a protocol handoff for the upcoming real calibration task. It defines the frozen pre-execution contract and the implementation shape, but it must not be used to execute real Pilot-V2 calibration in this task.

## 1. Scope and safety

- Calibration must use the frozen 120-window Pilot-V2 manifest only.
- Calibration references only the FIFO policy and one documented simulator configuration.
- No `EDF`, `LLF`, `ESTF`, weighted-fair, KV-aware, Sarathi, SLO-aware, or style-approximation policy may be referenced in the calibration logic.
- No comparative scheduler outcome may influence region selection.

## 2. Calibration unit

The calibration unit is one window at a time.

For each `(source, window_id)`, the system computes a single FIFO-based reference pressure and derives six region assignments for that window. The region definitions are not recomputed per source or per policy.

## 3. FIFO reference semantics

The reference pressure is defined with a single FIFO policy and one shared simulator configuration, identical across all sources and windows. The calibration process never compares the FIFO reference to any other scheduler outcome.

- reference policy: `fifo`
- reference semantics: identical rule for all sources/windows
- integration rule: calibration may inspect only FIFO pressure series for the window under a candidate load multiplier
- outcome dependence: forbidden

## 4. Candidate load-factor search

The candidate grid is fixed before real execution and must remain unchanged.

| Region | Multiplier of λ_ref |
|---|---|
| `LOW` | 0.5× |
| `PRE_KNEE` | 0.8× |
| `KNEE` | 1.0× |
| `POST_KNEE` | 1.1× |
| `OVERLOAD` | 1.2× |
| `HIGH_PRESSURE` | 1.5× |

The calibration search uses FIFO-only pressure observations from those candidate factors and chooses the region assignment by deterministic nearest-target logic.

## 5. Region mapping rules

For each window:
- compute the single FIFO reference pressure at `λ_ref` (the `KNEE` anchor);
- assign `LOW`/`PRE_KNEE`/`KNEE`/`POST_KNEE`/`OVERLOAD`/`HIGH_PRESSURE` using the exact multiplier table above;
- region membership is a deterministic function of the candidate load factor and the FIFO-only pressure series;
- no region should depend on which scheduler differentiates best.

## 6. Deterministic tie-breaking and fallback

- if two candidate factors are equally close to a target, prefer the earlier factor in the canonical region order (`LOW`, `PRE_KNEE`, `KNEE`, `POST_KNEE`, `OVERLOAD`, `HIGH_PRESSURE`);
- if a target region is flat or unreachable, assign the nearest valid candidate without consulting non-FIFO policies;
- if the minimum or maximum candidate is still outside the intended target range, the record is marked as `interpolated` or `edge_reached` rather than silently changing the protocol.

## 7. Edge cases to predeclare

- region target not exactly reachable: nearest valid candidate with explicit status
- flat FIFO response across adjacent candidate loads: deterministic midpoint/nearest rule
- already-high pressure at baseline: treat as valid high-pressure region assignment, not a protocol violation
- zero completion: record `zero_completion` and keep region assignment deterministic
- insufficient overload: leave as the nearest candidate, do not reinterpret the protocol
- numerical ties: earlier factor wins
- simulator failure: emit a schema-valid failure status and stop before claiming a full calibration record

## 8. Validation criteria

A calibration record is valid only if:
- it references the exact six-region order;
- it contains only FIFO pressure measurements and the frozen protocol hashes;
- it contains no non-FIFO policy field;
- it hashes against the frozen 120-window identity and the declared protocol version.

## 9. Source symmetry and provenance

- all sources use the same six-region definitions
- all windows use the same region definitions
- all records carry the same `window_freeze_hash`, `calibration_protocol_hash`, and simulator config hash
- no source is allowed to drift to a different calibration rule

## 10. Expected compute

This design is intentionally lightweight and synthetic-only. Real execution would produce 120 × 6 = 720 region assignments for the 120 windows, each with a fixed schema and a hash-locked protocol envelope, but no real 720-row run is executed in this task.
