# RANKING_PORTABILITY_PHASE12_CAMPAIGN_PRELAUNCH_FREEZE.md

Frozen **before** any Pilot-V2 scientific campaign cell is executed. This
is the Phase-12B campaign-matrix freeze: it fixes the complete 18,720-cell
identity/provenance matrix and its shard plan. It does not execute
anything.

`EXPECTED_PHASE12_CAMPAIGN_CELLS = 18720`

`PHASE12_CAMPAIGN_EXECUTION_STARTED = NO`

`COMPARATIVE_PILOT_V2_RESULTS = NONE`

## 1. Parent smoke SHA

`38188eca740c3bfeafa0463c80aaaff34b725e5a`
(`research/lssp-phase12-pilotv2-smoke-20260902`, `PHASE12_PILOT_V2_SMOKE_VALID = YES`)

## 2. Telemetry-amendment identity

`amendment_sha256 = da85c2d52e7018ecee26994c4ff38b7c3a08deb58b65ee3a3ab20f9c56736061`
(`docs/RANKING_PORTABILITY_PHASE12_TELEMETRY_SEMANTIC_AMENDMENT.md`,
`TELEMETRY_SEMANTIC_AMENDMENT_RESOLVED_BEFORE_CAMPAIGN = YES`,
`PHASE12A_SMOKE_REVALIDATED_AFTER_TELEMETRY_AMENDMENT = YES`)

## 3. Five immutable scientific hashes (re-verified before this freeze)

| Artifact | SHA-256 |
|---|---|
| Phase-10 scientific window | `0d1aa06ccbee352207327ea369ae75f12e91c0cda006c813a41b381effd29eef` |
| Phase-10 compact index | `d78ec1087fedae02174ca093a9860c70468be336ccb1d7e6de756c81ba331e53` |
| Phase-11 prelaunch freeze | `e2564ea9484190832de50f63173c4b73ae054d6ae7008bb4ff6648c8dc917f7b` |
| Phase-11 raw FIFO calibration | `201caaf04476ad8737ef6079fc0d6cb4e864601711d0b96c88750a717d8b2a6a` |
| Phase-11 region assignments | `9fcb92f9ea1206ce185194527ada35d0e3b91bf4904be7ae23ba9ea997c17574` |

## 4. Exact 120-window list and per-window identities

40 windows/source × 3 sources, loaded verbatim (no resampling, no
replacement, no content-dependent filtering) from the frozen compact index
in its own canonical order
(`artifacts/manifests/ranking_portability_pilot_v2_windows_index.json`).
Every window's `content_sha256` is embedded in the campaign manifest's
`window_identities` map (120 entries) for independent reconstruction. Full
per-window ID lists are in the machine-readable manifest (§15); not
reproduced inline here for length.

## 5. Exact 6-region order

`LOW`, `PRE_KNEE`, `KNEE`, `POST_KNEE`, `OVERLOAD`, `HIGH_PRESSURE` — same
frozen order as Phase-11 (`docs/RANKING_PORTABILITY_PHASE11_CALIBRATION_FREEZE.md`).

## 6. Exact 13-policy order and fidelity classification

Identical panel and order to the Phase-12A smoke
(`robustbench.ranking_portability.phase12_campaign.CAMPAIGN_POLICIES ==
robustbench.ranking_portability.phase12_smoke.SMOKE_POLICIES`):

| # | Policy | Fidelity class |
|---|---|---|
| 1 | `fifo` | `REPOSITORY_NATIVE_CLASSICAL` |
| 2 | `edf` | `REPOSITORY_NATIVE_CLASSICAL` |
| 3 | `least_laxity_first` | `REPOSITORY_NATIVE_CLASSICAL` |
| 4 | `estimated_service_time_first` | `REPOSITORY_NATIVE_CLASSICAL` |
| 5 | `weighted_fair_share` | `REPOSITORY_NATIVE_CLASSICAL` |
| 6 | `kv_constrained_online` | `SIMULATOR_PROXY` |
| 7 | `vllm_faithful` | `FAITHFUL_EXTERNAL` |
| 8 | `vllm_chunked_prefill_faithful` | `FAITHFUL_EXTERNAL` |
| 9 | `sarathi_faithful` | `FAITHFUL_EXTERNAL` |
| 10 | `slai_faithful` | `FAITHFUL_EXTERNAL` |
| 11 | `admission_control` | `REPOSITORY_NATIVE_CLASSICAL` |
| 12 | `vllm_style_token_budget` | `STYLE_APPROXIMATION` (robustness-only) |
| 13 | `scorpio_style_slo_guard` | `STYLE_APPROXIMATION` (robustness-only) |

`distserve_faithful`, `llumnix_faithful` (secondary stratum) and
`apt_serve_faithful` (scaffolding-only) are excluded, as in Phase-12A.

## 7. Exact repetition rule

`rep0`, `rep1`. Both use the **identical** synthesis seed and identical
scaled `Request` list for a given (source, window, region, policy) — the
simulator is deterministic; reps verify bit-identical reproduction, not an
independent stochastic draw. Independently verified: all 9,360
(source,window,region,policy) pairs have identical rep0/rep1
seed/region-assignment-key in the generated manifest
(`docs/RANKING_PORTABILITY_PHASE12_CAMPAIGN_FREEZE_VALIDATION.md`).

## 8. Exact synthesis seed/version rule

Unchanged from Phase-11/Phase-12A: `seed = 900000 +
int(window_id.rsplit("w", 1)[1])`
(`robustbench.ranking_portability.phase12_smoke.synthesis_seed_for_window`,
reused verbatim, not reinvented). Synthesis implementation:
`stage0_synthesis_v1`
(`src/robustbench/workloads/external/benchmark_synthesis.py`).

## 9. Exact 720 Phase-11 assignment mapping identity

120 windows × 6 regions = 720 unique `(source, window_id, region)` keys.
All 720 consumed exactly once each; 0 missing, 0 duplicate, 0 unexpected
(independently verified, §J below). Each maps to exactly `13 × 2 = 26`
campaign cells; `720 × 26 = 18,720`.

## 10. Exact 18,720 cell IDs

Format: `{source}::{window_id}::{load_region}::{policy_id}::rep{0|1}`.
Full list is in the machine-readable manifest's `cells` array (§15); not
reproduced inline here for length. Every cell carries
`scientific_status = "PILOT_V2_SCIENTIFIC"`.

## 11. Exact shard membership

64 shards, cost-aware LPT-balanced (`docs/` §H below has the full
rationale); full membership in
`artifacts/manifests/ranking_portability_phase12_shard_plan.json`.

## 12. Expected cell count

`3 sources × 40 windows/source × 6 regions × 13 policies × 2 reps =
18,720`.

## 13. Execution/schema/telemetry/policy/simulator file hashes

| File | SHA-256 |
|---|---|
| `src/robustbench/ranking_portability/phase12_campaign.py` | see manifest `execution_file_hashes` |
| `src/robustbench/ranking_portability/phase12_smoke.py` | see manifest `execution_file_hashes` |
| `src/robustbench/ranking_portability/execute_cell.py` | see manifest `execution_file_hashes` |
| `src/robustbench/ranking_portability/schema.py` | see manifest `execution_file_hashes` |
| `src/robustbench/ranking_portability/calibration.py` | see manifest `execution_file_hashes` |
| `src/robustbench/workloads/external/benchmark_synthesis.py` | see manifest `execution_file_hashes` |
| `src/robustbench/calibration/stage0_load_calibration.py` | see manifest `execution_file_hashes` |
| `src/robustbench/policies/registry.py` | see manifest `execution_file_hashes` |
| `src/robustbench/simulator/simulator.py` | see manifest `execution_file_hashes` |
| `src/robustbench/simulator/telemetry.py` (post-amendment) | see manifest `execution_file_hashes` |

(Full values in
`artifacts/manifests/ranking_portability_phase12_campaign_freeze.json`'s
`execution_file_hashes` — not duplicated here to avoid a second,
independently-driftable copy.)

## 14. Environment/runtime contract

Python venv:
`/home/soroush/repos/llm-serving-scheduler-robustness-benchmark/.venv`
(same interpreter used for Phase-10/11/12A). Simulator is fully
deterministic given identical inputs (no stochastic seed consumed) —
reconfirmed by Phase-12A's exact rep0/rep1 match on all 234 pairs and this
freeze's exact rep-input-identity check on all 9,360 pairs. Slurm:
`module load slurm/wulver` (verified available on Wulver login node,
§K below). Raw source data: read-only at
`/project/ikoutis/sv96/llmserveopt-data/datasets/{burstgpt_v2,azure_llm_2024,bailian_qwen}/raw/`
(Wulver); the canonical 120-window materialized manifest (with full
records) at
`/mmfs1/project/ikoutis/sv96/github/llm-serving-scheduler-ranking-portability-windows/artifacts/manifests/ranking_portability_pilot_v2_windows.json`
(52,145,952 bytes, confirmed readable, §K).

## 15. Machine-readable manifest

`artifacts/manifests/ranking_portability_phase12_campaign_freeze.json` —
`window_identities` (120), `region_assignment_index` (720),
`cells` (18,720), `execution_file_hashes`, `full_matrix_hash`,
`campaign_freeze_sha256`.

## 16. Full-matrix / aggregate identity

- `full_matrix_hash = 832d96d7ff4d5e8843c233a6a4708bbbbc578ef6b65307c37f5ac127c62c1ccf`
  (SHA-256 over the sorted-key JSON of `window_identities` +
  `region_assignment_index` + `cells`.)
- `campaign_freeze_sha256 = 81fa3d9b48a2241001e6820942d4542dcc5b5e30973ad9d2786e72972494f57a`
  (SHA-256 over the sorted-key JSON of: parent smoke branch SHA, telemetry
  amendment SHA, all 5 immutable hashes, frozen source/window/region/
  policy/repetition lists, expected cell count, execution-file-hash table,
  and `full_matrix_hash`. Reproducible via
  `robustbench.ranking_portability.phase12_campaign.compute_campaign_freeze_identity`.)

`PHASE12_CAMPAIGN_PRELAUNCH_CONTRACT = SATISFIED`
