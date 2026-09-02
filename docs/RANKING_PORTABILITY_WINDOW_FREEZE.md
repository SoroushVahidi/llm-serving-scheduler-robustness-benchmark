# Ranking Portability Pilot-V2 Window Freeze

Date frozen: 2026-09-01

This document records the authoritative freeze state for the Pilot-V2 workload window set used by the LSSP benchmark.

## 1. Source and artifact identity

Physical artifact (already materialized on Wulver):

- `/mmfs1/project/ikoutis/sv96/github/llm-serving-scheduler-ranking-portability-windows/artifacts/manifests/ranking_portability_pilot_v2_windows.json`
- physical SHA-256: `97fbaf6a4b9b5f14cd19ce1c37193996c0758eebca73ab2adb1e944b404b3f4c`
- compact index: `artifacts/manifests/ranking_portability_pilot_v2_windows_index.json`
- compact index SHA-256: `d78ec1087fedae02174ca093a9860c70468be336ccb1d7e6de756c81ba331e53`

Scientific canonical content hash (manifest excluding `generated_at_utc` and `content_sha256`):

- `0d1aa06ccbee352207327ea369ae75f12e91c0cda006c813a41b381effd29eef`

This is the frozen `content_sha256` value recorded in the materialized manifest.

## 2. Scope and counts

Exactly 120 windows are frozen:

- `azure_llm_2024`: 40 total = 10 Stage-0 reused + 30 Pilot-V2 new
- `bailian_qwen`: 40 total = 10 Stage-0 reused + 30 Pilot-V2 new
- `burstgpt`: 40 total = 10 Stage-0 reused + 30 Pilot-V2 new

Total: 120 windows

The Stage-0 subset is preserved verbatim as `STAGE0_WINDOW`. The additional 30 per source are `PILOT_V2_NEW_WINDOW` and are drawn using the pinned-extension deterministic sampler.

## 3. Deterministic sampling and provenance

The build used the pinned-extension selection algorithm defined in:

- `src/robustbench/ranking_portability/window_sampling.py`
- `scripts/ranking_portability/build_pilot_v2_windows.py`

Deterministic rule:

- Stage-0 windows are pinned as locked ranges.
- New windows are drawn from the remaining valid-row space using the same valid-row convention and the fixed extension seed offset `1_000_000`.
- Stage-0 ranges remain strict subsets of the larger Pilot-V2 window set.
- The algorithm is outcome-blind, source-symmetric, and does not use scheduler metrics or policy identities.

## 4. Anti-targeting result

`BURSTGPT_OUTCOME_TARGETING = NO`

The manifest records the explicit independence disclosure and the new sampler uses only valid-row index ranges, fixed seeds, and deterministic free-space selection. No Stage-0 tie/non-tie outcome, outcome variance, pressure proxy, policy identity, or scheduler metric is used in the selection rule.

## 5. Structural validation summary

The completed artifact was checked for:

- unique canonical window IDs: pass
- exact per-source counts: pass
- Stage-0 reused vs new counts: pass
- request_count = 200 for all windows: pass
- unique content hashes per window: pass
- duplicate record IDs within a window: none
- prohibited overlap between windows: none
- chronology ordering: valid
- evidence classes valid: pass
- source file checksums fixed: pass
- chronology strata valid: EARLY/MIDDLE/LATE assignment present and consistent
- absence of scheduler/policy/load-calibration outcome fields: pass

Invalid windows: 0.

## 6. Temporal strata

Temporal strata are assigned by deterministic relative chronology, not by post hoc balancing:

- `EARLY`: 60 windows
- `MIDDLE`: 30 windows
- `LATE`: 30 windows

The Stage-0 windows are all assigned to `EARLY`, and the newly selected Pilot-V2 windows are assigned as the fixed relative chronology split documented by the protocol.

## 7. Reproducibility and source independence

The manifest contains `source_sampling_reports` for each source and the per-source deterministic algorithm records. This permits independent verification of the selection geometry and canonical scientific hash without re-running the expensive Wulver build.

The selection is reproducible under the same source files, seeds, and protocol. The compact index is designed for Git-safe freeze tracking without carrying the full 52 MB materialized payload.

## 8. Phase-10 gate status

All required gate checks for this freeze are satisfied:

- actual artifact = 120 windows: PASS
- exactly 40 per source: PASS
- source checksums fixed: PASS
- Stage-0 reuse matches protocol: PASS
- LLM-2026 exclusions satisfied: PASS (documented as source-independent and different-window construction)
- chronology valid: PASS
- no malformed windows: PASS
- no prohibited overlap: PASS
- `BURSTGPT_OUTCOME_TARGETING = NO`: PASS
- `REPRODUCIBLE_SELECTION = YES`: PASS
- canonical freeze/index hash fixed: PASS
- relevant Phase-10 tests passed: PASS
- no Pilot-V2 scheduler outcomes exist: PASS
- Phase-11 calibration not started: PASS

These 120 window identities were frozen before any Pilot-V2 six-region load calibration and before any Pilot-V2 scheduler outcome was generated.
