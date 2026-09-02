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

## Aggregate prelaunch go/no-go (Phase-12B)

| Requirement | Status |
|---|---|
| Telemetry semantic inconsistency resolved before campaign | YES (`docs/RANKING_PORTABILITY_PHASE12_TELEMETRY_SEMANTIC_AMENDMENT.md`) |
| Phase-12A smoke revalidated under corrected contract | YES (`PHASE12A_SMOKE_REVALIDATED_AFTER_TELEMETRY_AMENDMENT = YES`, 0/468 problems) |
| 5 immutable hashes exact | YES (independently recomputed above) |
| Full matrix exactly 18,720, no missing/duplicate/unexpected | YES |
| All 120 frozen windows used exactly as preregistered (40/source, verbatim) | YES |
| All 720 Phase-11 assignments consumed correctly (26 cells each) | YES |
| Exact 13-policy panel, no secondary-stratum leakage | YES |
| Repetition semantics correct (rep0/rep1 share identical seed/input) | YES (9,360/9,360 pairs) |
| Unique deterministic cell IDs | YES (18,720/18,720 unique) |
| Deterministic shard plan (64 shards, LPT-balanced, self-rebuild-verified) | YES (imbalance ratio 1.000) |
| Independent validator PASS | YES (`PHASE12_CAMPAIGN_MATRIX_INDEPENDENTLY_VALID = YES`) |
| Full test suite PASS | YES (236/236) |
| Dry-run PASS (both shard-runner and sbatch generation) | YES (0 problems on shards 0 and 63; `--execute` correctly raises `NotImplementedError`) |
| No scientific campaign cell executed | YES (confirmed: dry-run never calls `execute_cell`/`synthesize_requests_from_window`/constructs a `Simulator`) |

**PHASE12_CAMPAIGN_FREEZE_VALID = YES**

The 18,720-cell scientific campaign is **frozen and verified, but NOT
launched**. `PHASE12_CAMPAIGN_EXECUTION_STARTED = NO`.
`COMPARATIVE_PILOT_V2_RESULTS = NONE`.
