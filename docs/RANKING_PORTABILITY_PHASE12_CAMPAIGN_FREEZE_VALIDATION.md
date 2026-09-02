# RANKING_PORTABILITY_PHASE12_CAMPAIGN_FREEZE_VALIDATION.md

Independent Phase-12B campaign-matrix validation report. No ranking
analysis, no scheduler-performance inspection, no cell executed.

## Immutable hashes (independently recomputed)
- phase10_compact_index: expected=`d78ec1087fedae02174ca093a9860c70468be336ccb1d7e6de756c81ba331e53` observed=`d78ec1087fedae02174ca093a9860c70468be336ccb1d7e6de756c81ba331e53` match=True
- phase11_region_assignment: expected=`9fcb92f9ea1206ce185194527ada35d0e3b91bf4904be7ae23ba9ea997c17574` observed=`9fcb92f9ea1206ce185194527ada35d0e3b91bf4904be7ae23ba9ea997c17574` match=True
- phase11_raw_fifo: expected=`201caaf04476ad8737ef6079fc0d6cb4e864601711d0b96c88750a717d8b2a6a` observed=`201caaf04476ad8737ef6079fc0d6cb4e864601711d0b96c88750a717d8b2a6a` match=True
- phase10_window: expected=`0d1aa06ccbee352207327ea369ae75f12e91c0cda006c813a41b381effd29eef` observed=`0d1aa06ccbee352207327ea369ae75f12e91c0cda006c813a41b381effd29eef` match=True
- phase11_prelaunch: expected=`e2564ea9484190832de50f63173c4b73ae054d6ae7008bb4ff6648c8dc917f7b` observed=`e2564ea9484190832de50f63173c4b73ae054d6ae7008bb4ff6648c8dc917f7b` match=True

## Matrix
- expected cells: 18720
- manifest cells: 18720
- unique (source,window,region,policy,rep) tuples: 18720
- missing vs. independently-reconstructed expectation: 0
- unexpected vs. independently-reconstructed expectation: 0

## Load assignments
- expected assignment keys: 720
- consumed keys: 720
- mismatches: 0

## Info
- windows per source (independently loaded): [40, 40, 40]
- all 18720 cells carry scientific_status='PILOT_V2_SCIENTIFIC'
- all 720 region_assignment_index entries agree exactly with the frozen Phase-11 artifact
- all 9360 (source,window,region,policy) pairs have identical rep0/rep1 seed/input
- all 13 campaign policies instantiate successfully via make_policy_any
- CELL_SCHEMA_VERSION=ranking_portability_cell_result_v1
- TELEMETRY_SCHEMA_VERSION=ranking_portability_telemetry_v1
- shard plan: union of 64 shards covers exactly the 18,720-cell matrix, no duplicates

## Problems: none

PHASE12_CAMPAIGN_MATRIX_INDEPENDENTLY_VALID = YES
