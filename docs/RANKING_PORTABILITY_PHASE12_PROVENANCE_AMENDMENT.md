# Phase-12D provenance amendment — completed Pilot-V2 campaign

Status: **pre-analysis metadata clarification and repair contract**.

The frozen 18,720-cell Phase-12 scientific campaign completed before this
amendment was written.  The Phase-12C execution path produced complete
scientific rows but left five provenance fields at their dataclass defaults
(empty strings):

- `window_manifest_sha256`
- `calibration_manifest_sha256`
- `policy_registry_hash`
- `simulator_config_hash`
- `synthesis_version`

The omission is mechanical: `RankingPortabilityCellResult.from_run()` does not
accept or populate these provenance fields, and Phase-12C calls
`execute_cell()` without a provenance argument block.  The execution schema
therefore accepted scientifically complete rows with empty metadata.  This
amendment does **not** change the execution schema retroactively and does not
invalidate the raw campaign.  It defines a stricter analysis-admission layer
and a deterministic derivative representation with the missing metadata
filled from identities fixed independently of scheduler outcomes.

No ranking, winner, reversal, pairwise comparison, or result direction is
consulted by the repair.

## 1. Raw-result immutability

The 64 Phase-12C shard files are immutable scientific inputs.  Before repair,
Phase-12D records a SHA-256 and row count for every raw shard.  Enrichment
writes only to a separate `campaign_results_enriched/<campaign-prefix>/`
namespace.  The repair validator recomputes the raw shard hashes after
writing and requires them to remain unchanged.

Every original/repaired row is compared recursively after masking the
approved provenance fields.  Any difference in a metric, telemetry scalar,
cell identity, load factor, seed, success/error state, or scientific status is
a hard failure.

Required invariant:

`NON_PROVENANCE_ROW_DIFFERENCES = 0`

## 2. `window_manifest_sha256`

Canonical meaning: identity of the **full materialized Phase-10 scientific
120-window manifest content**, not the compact-index file hash and not an
individual window hash.

Canonical value:

`0d1aa06ccbee352207327ea369ae75f12e91c0cda006c813a41b381effd29eef`

Rationale: Phase-12C verifies the same `content_sha256` before synthesizing
requests, and the Phase-12B freeze carries this Phase-10 scientific-window
identity separately from the compact-index file identity.

## 3. `calibration_manifest_sha256` clarification

The generic field name predates Pilot-V2 and is ambiguous in isolation
because Phase 11 preserves two scientifically distinct artifacts:

- raw FIFO calibration output:
  `201caaf04476ad8737ef6079fc0d6cb4e864601711d0b96c88750a717d8b2a6a`
- final six-region assignment artifact:
  `9fcb92f9ea1206ce185194527ada35d0e3b91bf4904be7ae23ba9ea997c17574`

Historical Stage-0 semantics resolve the ambiguity: Stage-0's harness stores
`calibration_manifest_sha256` as the SHA-256 of the calibration manifest
**consumed to define the cell's frozen load**.  Phase-12 cells do not consume
the raw FIFO calibration table directly during execution; they consume the
Phase-11 region-assignment artifact's `(source, window, region)` mapping and
its `absolute_load_factor`.

Therefore Phase-12D defines:

`calibration_manifest_sha256 = phase11_region_assignments_sha256`

Canonical value:

`9fcb92f9ea1206ce185194527ada35d0e3b91bf4904be7ae23ba9ea997c17574`

To avoid losing the upstream distinction, every enriched row additionally
records both explicit fields:

- `phase11_raw_fifo_calibration_sha256 = 201caaf04476ad8737ef6079fc0d6cb4e864601711d0b96c88750a717d8b2a6a`
- `phase11_region_assignments_sha256 = 9fcb92f9ea1206ce185194527ada35d0e3b91bf4904be7ae23ba9ea997c17574`

This is a semantic clarification made after execution but before comparative
analysis and without consulting any scheduler outcome.

## 4. `policy_registry_hash`

Canonical meaning: SHA-256 of the exact policy-registry implementation pinned
by the Phase-12B campaign manifest.

The repair does **not** trust a separately typed value.  It reads:

`campaign_manifest["execution_file_hashes"]["src/robustbench/policies/registry.py"]`

and requires that value for every enriched row.  This binds repaired rows to
the exact registry identity frozen before campaign execution.

## 5. `simulator_config_hash` clarification

No historical code path in the repository unambiguously generated the
`simulator_config_hash` field.  In particular, Phase-11's phrase
"simulator implementation/config hash" refers to an implementation-file
identity; it is not a canonical serialized runtime-configuration generator.
The Stage-0 schema contains the field but its Stage-0 runner never populated
it.

Phase-12D therefore freezes a precise value-level configuration identity,
distinct from the simulator source-file hashes already present in the
Phase-12B campaign manifest.

Contract version:

`phase12_simulator_config_v1`

Canonical payload is sorted compact JSON over:

1. `contract_version = phase12_simulator_config_v1`
2. `gpu_configs = [asdict(STAGE0_REFERENCE_GPU_CONFIG)]`
3. `service_model = asdict(ServiceModel())`
4. `SimulatorConfig` runtime values constructed by `execute_cell`:
   - `max_steps = null`
   - `drain_steps = 50000`
   - `warn_on_invalid_action = true`

The SHA-256 is recomputed from the actual imported dataclasses by
`robustbench.ranking_portability.phase12_provenance.phase12_simulator_config_hash()`.
At the frozen Phase-12C code state this deterministic contract evaluates to:

`a7a8920a43d4c1ba90da249f64d60e9929355e66f150aa1afd60f3599f98717b`

This value identifies configuration values only.  Simulator implementation,
service-model implementation, and other execution source files remain
separately pinned by `execution_file_hashes` in the Phase-12B campaign
manifest.

## 6. `synthesis_version`

Canonical value:

`stage0_synthesis_v1`

Source of truth:
`robustbench.workloads.external.benchmark_synthesis.SYNTHESIS_VERSION`.
The Phase-12B freeze explicitly reuses the Phase-11/Phase-12A synthesis rule,
and Phase-12C calls that same synthesis function with the frozen per-window
seed.

## 7. Admission-layer distinction

Phase-12D deliberately distinguishes three concepts:

1. **Execution-row validity** — historical/raw Phase-12C rows may remain valid
   under `validate_cell_result()` even when provenance defaults are empty.
2. **Analysis-admission validity** — a `PILOT_V2_SCIENTIFIC` row must have
   complete, exact Phase-12D provenance matching independently reconstructed
   expectations before statistical analysis may read it.
3. **Dataset-release validity** — downstream release tooling may impose
   additional packaging/licensing requirements, but must start from an
   analysis-admitted artifact rather than the raw incomplete-provenance rows.

This avoids rewriting history while preventing metadata-incomplete execution
rows from silently entering analysis or release.

## 8. Repair scope

Approved row changes are restricted to:

- the five originally empty provenance fields; and
- the two explicit Phase-11 provenance fields added by this amendment.

No scientific value is recomputed.  In particular the repair never changes:
ANWG, completion metrics, SLO/goodput/latency/TTFT/throughput values,
telemetry, cell identity, source/window/region/policy/repetition, load factor,
synthesis seed, success/error state, repository SHA, or scientific status.

The raw namespace is never overwritten.

`PHASE12_PROVENANCE_REPAIR_OUTCOME_INDEPENDENT = YES`

`PHASE12_RAW_SCIENTIFIC_RESULTS_UNMODIFIED = YES`

`COMPARATIVE_PILOT_V2_RESULTS = NONE` until the separately frozen analysis
pipeline is deliberately run against an admitted completed-campaign artifact.
