# RANKING_PORTABILITY_PHASE12_SMOKE_VALIDATION.md

Phase-12A engineering-smoke validation report. Engineering validation ONLY --
no ranking analysis, no scheduler comparison, no direction of finding.

## Matrix integrity
- expected cells: 468
- actual cells: 468
- duplicate cell_ids: 0
- missing cells: 0
- unexpected cells: 0

## Execution integrity
- successful cells: 468/468
- unresolved failures: 0

## Frozen-input integrity
- phase10_compact_index: expected=`d78ec1087fedae02174ca093a9860c70468be336ccb1d7e6de756c81ba331e53` observed=`d78ec1087fedae02174ca093a9860c70468be336ccb1d7e6de756c81ba331e53` match=True
- phase11_raw_fifo: expected=`201caaf04476ad8737ef6079fc0d6cb4e864601711d0b96c88750a717d8b2a6a` observed=`201caaf04476ad8737ef6079fc0d6cb4e864601711d0b96c88750a717d8b2a6a` match=True
- phase11_region_assignment: expected=`9fcb92f9ea1206ce185194527ada35d0e3b91bf4904be7ae23ba9ea997c17574` observed=`9fcb92f9ea1206ce185194527ada35d0e3b91bf4904be7ae23ba9ea997c17574` match=True
- phase10_window: expected=`0d1aa06ccbee352207327ea369ae75f12e91c0cda006c813a41b381effd29eef` observed=`0d1aa06ccbee352207327ea369ae75f12e91c0cda006c813a41b381effd29eef` match=True
- phase11_prelaunch: expected=`e2564ea9484190832de50f63173c4b73ae054d6ae7008bb4ff6648c8dc917f7b` observed=`e2564ea9484190832de50f63173c4b73ae054d6ae7008bb4ff6648c8dc917f7b` match=True

## Load-assignment agreement
- mismatches vs. frozen Phase-11 region-assignment artifact: 0
- lambda_ref recomputation for `azure_llm_2024_stage0_w00`: matches=True (rel_diff=0.000e+00)
- lambda_ref recomputation for `bailian_qwen_stage0_w00`: matches=True (rel_diff=0.000e+00)
- lambda_ref recomputation for `burstgpt_stage0_w00`: matches=True (rel_diff=0.000e+00)

## Metric integrity (independent schema re-validation)
- cells failing independent schema re-validation: 0

## Telemetry integrity (independent re-validation)
- cells failing independent telemetry re-validation: 0

## Determinism (rep0 vs rep1)
- (source,window,region,policy) pairs compared: 234
- mismatches: 0

## Info
- successful cells: 468/468
- lambda_ref recomputation for azure_llm_2024_stage0_w00: MATCHES frozen Phase-11 value exactly
- lambda_ref recomputation for bailian_qwen_stage0_w00: MATCHES frozen Phase-11 value exactly
- lambda_ref recomputation for burstgpt_stage0_w00: MATCHES frozen Phase-11 value exactly
- determinism: rep0 == rep1 exactly for all 234 (source,window,region,policy) pairs

## Problems: none

## Scientific safety
- No ranking analysis performed.
- No comparative Pilot-V2 claim written.
- Every cell's `scientific_status` = `ENGINEERING_SMOKE`; this report is not comparative evidence.

PHASE12_PILOT_V2_SMOKE_VALID = YES
