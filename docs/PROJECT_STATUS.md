# LLM-Serving Scheduler Portability Benchmark — Project Status

Last verified: 2026-09-02 (Phase-12D provenance-repair preparation)
Canonical mutable status for the integrated scientific state through Phase 11,
the corrected canonical literature, manuscript foundation, Phase-12A smoke,
Phase-12B campaign freeze, completed Phase-12C execution, and Phase-12D
provenance-repair / completed-validation gate.

PROJECT_STATUS.md is the canonical single source of truth for project-state changes.

## 1. Executive summary

The frozen Phase-12 Pilot-V2 campaign has now been **executed completely**.
Slurm array job `1215964` ran all 64 frozen shards and completed with exit
code `0:0` for every array task. Structural inspection found all 18,720
expected scientific rows, 0 missing/duplicate/unexpected rows, 0 failed rows,
0 schema-invalid rows under the execution validator, 0 telemetry-validation
failures, and 0/9,360 rep0/rep1 scientific-input mismatches. No comparative
scheduler ranking/statistical analysis has been performed.

A Phase-12C engineering omission left five result-provenance fields empty in
all 18,720 raw rows. The scientific outcomes themselves are complete; the
raw namespace is preserved. Phase-12D defines an outcome-independent,
deterministic metadata-enrichment contract and a stricter analysis-admission
validator. The repository-side Phase-12D tooling is prepared on the dedicated
repair branch; the actual enrichment + completed-campaign validator must still
be run against the Wulver raw namespace before statistical analysis begins.

- Phase 10: DONE
- Phase 11: DONE
- Phase-12A (Pilot-V2 engineering smoke, 468 cells): DONE, `PHASE12_PILOT_V2_SMOKE_VALID = YES`
- Phase-12B (18,720-cell campaign matrix freeze): DONE, `PHASE12_CAMPAIGN_FREEZE_VALID = YES`
- Phase-12C (18,720-cell scientific execution): **DONE**
- Phase-12D (provenance repair + completed validation): **TOOLING READY, WULVER VALIDATION PENDING**
- 18,720-cell scientific campaign status: **COMPLETE_PENDING_VALIDATION**
- ranking analysis: NOT STARTED
- sample-complexity analysis: NOT STARTED
- real-system validation: NOT STARTED
- comparative Pilot-V2 scheduler results: NONE
- literature consolidation (Query 2): DONE
- targeted literature integrity gate (Query 3): DONE, `LITERATURE_INTEGRITY_GATE = PASS`
- manuscript foundation (Query 3): DONE — see §7 below

`PHASE12_CAMPAIGN_EXECUTION_STARTED = YES`

`PHASE12_CAMPAIGN_EXECUTION_STATUS = COMPLETE_PENDING_VALIDATION`

`COMPARATIVE_PILOT_V2_RESULTS = NONE`

The authoritative current scientific branch through Phase 11 remains:
`research/lssp-integrated-phase11-20260901` @ `30995d6dc5c9d3bb5db3aecdb975ddb70a92e86a`.

The corrected canonical literature branch remains:
`research/lssp-literature-canonical-20260901` @ `7e5230f4aa1ea408a7d9580594135ca471dc3e42`.

The final authoritative pre-Phase-12 branch remains:
`research/lssp-authoritative-pre-phase12-20260901` @ `ec12af8ede08cf8b6ebb8f60fce85915fc2ef18d`.

The Phase-12A engineering-smoke branch remains:
`research/lssp-phase12-pilotv2-smoke-20260902` @ `38188eca740c3bfeafa0463c80aaaff34b725e5a`.

The frozen Phase-12B campaign identity is:

- `campaign_freeze_sha256 = 81fa3d9b48a2241001e6820942d4542dcc5b5e30973ad9d2786e72972494f57a`
- `full_matrix_hash = 832d96d7ff4d5e8843c233a6a4708bbbbc578ef6b65307c37f5ac127c62c1ccf`
- Phase-12C execution SHA = `2b9a21fb58798292c95980d35d05e53b3c6f14f6`
- Slurm array = `1215964`

The branch a new chat should read to continue the **current Phase-12D gate** is:

`research/lssp-phase12-provenance-repair-20260902`

Read:

- `docs/RANKING_PORTABILITY_PHASE12_PROVENANCE_AMENDMENT.md`
- `docs/RANKING_PORTABILITY_PHASE12D_RUNBOOK.md`
- `src/robustbench/ranking_portability/phase12_provenance.py`
- `scripts/ranking_portability/enrich_phase12_campaign_provenance.py`
- `scripts/ranking_portability/validate_phase12_completed_campaign.py`

Do not begin ranking analysis until Phase-12D emits both
`PHASE12_COMPLETED_CAMPAIGN_VALID = YES` and
`PHASE12_ANALYSIS_INPUT_ADMITTED = YES`.

## 2. Phase map

| Phase | Objective | Status | Evidence |
|---|---|---|---|
| 0 | Bootstrap / provenance + overlap audit | DONE | repository bootstrap and audit docs |
| 1 | Evidence/source independence | DONE | provenance + exclusions records |
| 2 | Workload characterization | DONE | `SEPARABILITY_RESULT_CONFIRMED_WITH_CAVEATS` |
| 3 | Characterization paper-facing cleanup | DONE | leakage-resistant grouped evaluation |
| 4 | Stage-0 pilot preparation | DONE | calibration setup and protocol |
| 5 | Stage-0 execution | DONE | real 1,080-cell pilot executed |
| 6 | Stage-0 repair | DONE | `STAGE0_NO_GO` final decision |
| 7 | BurstGPT diagnostic | DONE | root cause documented |
| 8 | Pilot-V2 preregistration | DONE | protocol + policy panel + analysis plan |
| 9 | Telemetry implementation | DONE | telemetry schema and implementation |
| 10 | Pilot-V2 120-window freeze | DONE | canonical Phase-10 window hash preserved |
| 11 | Six-region FIFO calibration | DONE | raw FIFO calibration + assignments retained |
| 12A | Pilot-V2 engineering smoke (468 cells) | DONE | `PHASE12_PILOT_V2_SMOKE_VALID = YES` |
| 12B | 18,720-cell campaign matrix freeze | DONE | `PHASE12_CAMPAIGN_FREEZE_VALID = YES` |
| 12C | Frozen 18,720-cell campaign execution | DONE | Slurm `1215964`, 64/64 tasks completed `0:0`; 18,720/18,720 structurally present |
| 12D | Provenance enrichment + completed-matrix admission | IN PROGRESS | outcome-independent repair/validator prepared; Wulver payload run pending |
| 12E | Ranking portability statistical analysis | BLOCKED ON 12D | not started |

## 3. Current execution state

- frozen windows = YES
- six-region FIFO calibration = DONE
- Pilot-V2 engineering smoke (Phase-12A, 468 cells) = DONE, VALID
- telemetry semantic amendment (Phase-12B) = RESOLVED (`docs/RANKING_PORTABILITY_PHASE12_TELEMETRY_SEMANTIC_AMENDMENT.md`)
- 18,720-cell campaign matrix freeze (Phase-12B) = DONE, VALID
- campaign execution (Phase-12C) = DONE
- Slurm array `1215964`: 64/64 tasks COMPLETED, exit `0:0`
- raw structural matrix: 18,720/18,720 cells; 0 missing; 0 duplicate; 0 unexpected; 0 failed
- raw execution-schema failures observed: 0
- raw telemetry-validation failures observed: 0
- rep0/rep1 scientific-input mismatches observed: 0/9,360
- provenance omission: five result-level provenance fields empty in every raw row
- Phase-12D repair contract = PREPARED, outcome-independent
- Phase-12D Wulver enrichment + final analysis-admission validation = PENDING
- ranking analysis = NOT STARTED
- sample-complexity analysis = NOT STARTED
- real-system validation = NOT STARTED
- comparative Pilot-V2 scheduler results = NONE

The raw campaign files must not be overwritten. Phase-12D writes derivative
metadata-enriched shards to a separate namespace and proves all non-provenance
row content is identical.

## 4. Canonical scientific freeze

- Phase-10 scientific window hash: `0d1aa06ccbee352207327ea369ae75f12e91c0cda006c813a41b381effd29eef`
- Phase-10 compact index hash: `d78ec1087fedae02174ca093a9860c70468be336ccb1d7e6de756c81ba331e53`
- Phase-11 prelaunch freeze hash: `e2564ea9484190832de50f63173c4b73ae054d6ae7008bb4ff6648c8dc917f7b`
- Phase-11 raw FIFO calibration hash: `201caaf04476ad8737ef6079fc0d6cb4e864601711d0b96c88750a717d8b2a6a`
- Phase-11 region assignment hash: `9fcb92f9ea1206ce185194527ada35d0e3b91bf4904be7ae23ba9ea997c17574`
- canonical compact window manifest: `artifacts/manifests/ranking_portability_pilot_v2_windows_index.json`
- Phase-12 campaign freeze SHA: `81fa3d9b48a2241001e6820942d4542dcc5b5e30973ad9d2786e72972494f57a`
- Phase-12 full matrix hash: `832d96d7ff4d5e8843c233a6a4708bbbbc578ef6b65307c37f5ac127c62c1ccf`

Phase-12D provenance clarification:

- `window_manifest_sha256` = Phase-10 full materialized scientific-window content identity
- `calibration_manifest_sha256` = Phase-11 region-assignment artifact identity (the load-defining manifest consumed by Phase-12 cells)
- raw FIFO calibration identity remains separately recorded as upstream source provenance
- `policy_registry_hash` is derived from the Phase-12B frozen `execution_file_hashes` entry for `src/robustbench/policies/registry.py`
- `synthesis_version = stage0_synthesis_v1`
- `simulator_config_hash` is a value-level hash under `phase12_simulator_config_v1`, distinct from source-file implementation hashes

See `docs/RANKING_PORTABILITY_PHASE12_PROVENANCE_AMENDMENT.md`.

## 5. Scientific findings

Established scientific findings remain unchanged:

- Final workload-characterization result: `SEPARABILITY_RESULT_CONFIRMED_WITH_CAVEATS`.
- Stage-0 final verdict: `STAGE0_NO_GO`.
- Phase 11 is FIFO-only calibration provenance, not a comparative scheduler result.

The Phase-12 scientific campaign has generated raw scheduler outcomes, but
**no comparative Pilot-V2 scientific finding has yet been computed or
inspected in the Phase-12D workflow**. Ranking/stability/reversal directions
remain pending until the admitted analysis artifact is deliberately analyzed.

## 6. Caveats and provenance boundaries

The Phase-10 audit recorded the historical LLM-2026 overlap relationship as
`UNRESOLVED` where exact reconstruction was not possible from the available
public checkout. This remains a provenance limitation, not proof and not a
causal claim about benchmark validity.

The zero-completion counts retained in the Phase-11 calibration documentation
are descriptive only and must not be reinterpreted as comparative scheduler
performance.

Phase-12D raw-shard integrity limitation: no per-shard cryptographic ledger
was recorded at the earlier completed-campaign inspection. Phase-12D therefore
creates the first cryptographic raw-shard ledger immediately before repair and
proves immutability from that point onward. Pre-ledger evidence consists of
Slurm accounting plus the earlier structural 64-shard/18,720-row inspection.
This limitation must remain disclosed rather than being retrospectively
papered over.

## 7. Manuscript status

Manuscript sections, tracked in `docs/MANUSCRIPT_CONTENT_MAP.md` and
`paper/sections/*.tex`:

| Section | Status |
|---|---|
| Introduction | `DRAFT_V1` (manuscript-quality prose, outcome-neutral) |
| Related Work | `DRAFT_V1` (all 6 subsections, corrected literature) |
| Study Design | `DRAFT_V1` |
| Workload Corpus / Characterization | `DRAFT_V1` (established numbers included) |
| Scheduler Methodology (panel/fidelity/calibration/metrics/telemetry/robustness) | `DRAFT_V1` |
| Results (ranking portability) | `CONTRACT_ONLY` |
| Sample Complexity | `CONTRACT_ONLY` |
| Real-System Validation | `CONTRACT_ONLY` |
| Discussion | `STRUCTURED_V1` (both outcome branches written; numeric content pending) |
| Threats to Validity | `DRAFT_V1` |
| Reproducibility / Artifact | `DRAFT_V1` |
| Conclusion | `STRUCTURED_V1` |

The manuscript foundation remains outcome-neutral with comparative result
content pending.

## 8. Branch / lineage summary

- `main` remains untouched.
- `research/lssp-integrated-phase11-20260901` remains frozen scientific state through Phase 11.
- `research/lssp-integrated-phase10-20260901` remains the prior Phase-10 integration branch.
- `research/lssp-literature-canonical-20260901` remains the canonical literature branch.
- `research/lssp-authoritative-pre-phase12-20260901` remains the final pre-Phase-12 authoritative branch.
- `research/lssp-phase12-pilotv2-smoke-20260902` remains the completed Phase-12A smoke branch.
- `research/lssp-phase12-campaign-freeze-20260902` preserves the Phase-12B freeze and Phase-12C engineering lineage.
- `research/lssp-phase12-provenance-repair-20260902` is the current continuation branch for Phase-12D metadata enrichment and completed-result admission.

Parallel result-blind analysis/dataset/artifact preparation branches remain
separate and must not be merged opportunistically into the raw execution
history.

## 9. Immediate next action

**Next task:** run the Phase-12D provenance-enrichment pipeline and independent
completed-campaign validator against the already-completed Wulver raw result
namespace, following `docs/RANKING_PORTABILITY_PHASE12D_RUNBOOK.md`.

The target raw namespace is:

`/project/ikoutis/sv96/github/llm-serving-scheduler-lssp-phase12-campaign-run/artifacts/campaign_results/81fa3d9b48a22410`

Do not rerun a scheduler cell. Do not overwrite raw shards. Do not perform
ranking analysis.

If and only if Phase-12D returns:

`PHASE12_COMPLETED_CAMPAIGN_VALID = YES`

and

`PHASE12_ANALYSIS_INPUT_ADMITTED = YES`

then update this status to `PHASE12_CAMPAIGN_EXECUTION_STATUS = COMPLETE_VALIDATED`
and proceed to the separately prefrozen statistical-analysis pipeline.

Until then:

`PHASE12_CAMPAIGN_EXECUTION_STATUS = COMPLETE_PENDING_VALIDATION`

`COMPARATIVE_PILOT_V2_RESULTS = NONE`
