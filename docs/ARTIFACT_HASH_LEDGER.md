# ARTIFACT_HASH_LEDGER.md

Canonical artifact ledger for the integrated scientific state.

## Immutable scientific identifiers

| Artifact | Scientific role | Path | SHA-256 / canonical hash | Created phase | Frozen? | Notes |
|---|---|---|---|---|---|---|
| Stage-0 window manifest | historical pilot artifact | `artifacts/manifests/...` | `UNRECOVERED` | Stage-0 | yes | exact historical hash not available in this checkout |
| Phase-10 full scientific hash | authoritative freeze | `git` commit object | `0d1aa06ccbee352207327ea369ae75f12e91c0cda006c813a41b381effd29eef` | Phase 10 | yes | canonical window freeze identity |
| Phase-10 compact index hash | compact freeze index | `artifacts/manifests/ranking_portability_pilot_v2_windows_index.json` | `d78ec1087fedae02174ca093a9860c70468be336ccb1d7e6de756c81ba331e53` | Phase 10 | yes | matches file hash |
| Phase-11 prelaunch freeze | pre-execution contract | `docs/RANKING_PORTABILITY_PHASE11_PRELAUNCH_FREEZE.md` | `e2564ea9484190832de50f63173c4b73ae054d6ae7008bb4ff6648c8dc917f7b` | Phase 11 | yes | contract hash recorded in provenance |
| Phase-11 raw FIFO calibration | raw calibration matrix | `artifacts/manifests/ranking_portability_phase11_raw_fifo_calibration.json` | `201caaf04476ad8737ef6079fc0d6cb4e864601711d0b96c88750a717d8b2a6a` | Phase 11 | yes | actual manifest hash matches |
| Phase-11 region-assignment output | deterministic assignment map | `artifacts/manifests/ranking_portability_phase11_region_assignments.json` | `9fcb92f9ea1206ce185194527ada35d0e3b91bf4904be7ae23ba9ea997c17574` | Phase 11 | yes | actual manifest hash matches |
| Phase-11 calibration implementation | methodology | `scripts/ranking_portability/build_phase11_calibration.py` | `UNRECOVERED` | Phase 11 | yes | implementation hash not required for the current branch state |
| policy panel definition | protocol input | `configs/policies/...` | `UNRECOVERED` | Phase 11 prep | yes | immutable registry retained as branch state |
| simulator config | execution input | `configs/...` | `UNRECOVERED` | Phase 11 | yes | exact file hash not material to the final report |

## Required preservation statements

- The Phase-10 scientific window hash is the authoritative identity for the 120-window freeze.
- The Phase-11 calibration outputs are valid only as FIFO calibration provenance and must not be reinterpreted as scheduler-ranking results.
- Where a historical artifact hash is unavailable from the preserved repository state, this ledger records `UNRECOVERED` rather than fabricating a value.
