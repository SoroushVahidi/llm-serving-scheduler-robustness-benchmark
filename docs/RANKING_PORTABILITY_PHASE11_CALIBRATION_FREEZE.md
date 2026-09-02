# Phase-11 calibration freeze

Date: 2026-09-02

## Scientific state

- Phase-10 window freeze hash: `0d1aa06ccbee352207327ea369ae75f12e91c0cda006c813a41b381effd29eef`
- Phase-11 prelaunch freeze hash: `e2564ea9484190832de50f63173c4b73ae054d6ae7008bb4ff6648c8dc917f7b`
- execution branch: `research/ranking-portability-phase11-calibration-run-20260901`
- execution branch SHA: `f67c65f2f0b6cef661701e75c14f0a7e6868da4d`
- window manifest path: `artifacts/manifests/ranking_portability_pilot_v2_windows.json`
- compact index hash: `d78ec1087fedae02174ca093a9860c70468be336ccb1d7e6de756c81ba331e53`

## Calibration contract

- `lambda_ref`: the inter-arrival compression factor at which the frozen FIFO `slo_violation_rate` crosses the fixed 0.5% threshold (`0.005`).
- FIFO pressure statistic used: `slo_violation_rate` from the single reference policy `fifo`.
- region grid: `LOW=0.5x`, `PRE_KNEE=0.8x`, `KNEE=1.0x`, `POST_KNEE=1.1x`, `OVERLOAD=1.2x`, `HIGH_PRESSURE=1.5x`.
- candidate grid is fixed before execution and applied directly to each region; it is not searched after seeing data.
- deterministic tie rule: earlier canonical factor wins.
- no non-FIFO scheduler outcome is evaluated or recorded.

## Execution summary

- expected FIFO cells: `720`
- actual FIFO cells: `720`
- successful cells: `720`
- failed cells: `0`
- missing cells: `0`
- duplicate cells: `0`
- raw calibration path: `artifacts/manifests/ranking_portability_phase11_raw_fifo_calibration.json`
- raw calibration SHA-256: `201caaf04476ad8737ef6079fc0d6cb4e864601711d0b96c88750a717d8b2a6a`
- region assignment path: `artifacts/manifests/ranking_portability_phase11_region_assignments.json`
- region assignment SHA-256: `9fcb92f9ea1206ce185194527ada35d0e3b91bf4904be7ae23ba9ea997c17574`
- valid region assignments: `720`

## Validity gate

All frozen validity checks are satisfied:

- six-region order matches the preregistered definition
- only FIFO policy is executed
- no comparative Pilot-V2 scheduler panel is run
- no missing or duplicate cells
- no simulator packet failures
- the canonical window hash matches the frozen manifest
- phase-11 tests pass

`PHASE11_CALIBRATION_VALID = YES`

## Determinism

The calibration output is deterministic under repeated execution of the same FIFO-only matrix over the same frozen manifest.

`CALIBRATION_DETERMINISTIC = YES`

## Phase-11 status

Phase 11 = DONE

Pilot-V2 smoke = NOT STARTED
18,720 campaign = NOT STARTED
ranking analysis = NOT STARTED
comparative Pilot-V2 results = NONE
