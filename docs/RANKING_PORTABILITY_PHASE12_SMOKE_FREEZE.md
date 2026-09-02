# RANKING_PORTABILITY_PHASE12_SMOKE_FREEZE.md

Frozen **before** any smoke cell is executed. This is a Phase-12A
**engineering validation** freeze, not a scientific-content freeze: it
exercises the real Pilot-V2 execution path on a small, deterministic,
outcome-blind subset of the frozen 120-window matrix.

`SCIENTIFIC_STATUS = ENGINEERING_SMOKE_ONLY`

`SMOKE_RESULTS_MUST_NOT_BE_USED_AS_COMPARATIVE_PILOT_V2_EVIDENCE = YES`

No smoke result may be cited as a ranking-portability finding, a
scheduler-comparison result, or evidence toward RQ1–RQ6. The smoke answers
exactly one question: does the frozen Pilot-V2 execution/schema/telemetry
machinery run correctly end-to-end on real data, real policies, and the
real frozen Phase-11 load assignments?

## Authoritative parent state

- Authoritative pre-Phase-12 branch: `research/lssp-authoritative-pre-phase12-20260901`
- Authoritative parent SHA: `ec12af8ede08cf8b6ebb8f60fce85915fc2ef18d`
- Phase-12 engineering branch: `research/lssp-phase12-pilotv2-smoke-20260902`
- Worktree: `/home/soroush/repos/llm-serving-scheduler-lssp-phase12-smoke`

## Immutable scientific hashes (re-verified before this freeze; see §"Preflight hash gate" below)

| Artifact | SHA-256 |
|---|---|
| Phase-10 scientific window (content hash) | `0d1aa06ccbee352207327ea369ae75f12e91c0cda006c813a41b381effd29eef` |
| Phase-10 compact index | `d78ec1087fedae02174ca093a9860c70468be336ccb1d7e6de756c81ba331e53` |
| Phase-11 prelaunch freeze contract | `e2564ea9484190832de50f63173c4b73ae054d6ae7008bb4ff6648c8dc917f7b` |
| Phase-11 raw FIFO calibration | `201caaf04476ad8737ef6079fc0d6cb4e864601711d0b96c88750a717d8b2a6a` |
| Phase-11 region-assignment output | `9fcb92f9ea1206ce185194527ada35d0e3b91bf4904be7ae23ba9ea997c17574` |

## Smoke-selection rule (deterministic, outcome-blind)

No prior explicit Pilot-V2 smoke-selection contract existed in the
authoritative repository at freeze time (searched: no file matching
`*smoke*` under `docs/`/`scripts/` referenced a Pilot-V2 engineering
smoke). The following rule is therefore newly frozen here, before any cell
is executed:

- **Sources:** all 3 primary Pilot-V2 sources — `burstgpt`, `azure_llm_2024`, `bailian_qwen`.
- **Windows:** exactly 1 window per source, selected as the **first window
  for that source in canonical manifest ordering**
  (`artifacts/manifests/ranking_portability_pilot_v2_windows_index.json`'s
  `windows` list order), applied identically to every source. This rule
  never inspects window content, descriptors, or any scheduler outcome.
  It happens to select each source's `*_stage0_w00` window (a consequence
  of Stage-0-reused windows being placed first in the freeze's canonical
  order, not a separate choice).
- **Regions:** all 6 frozen operating regions — `LOW`, `PRE_KNEE`, `KNEE`, `POST_KNEE`, `OVERLOAD`, `HIGH_PRESSURE`.
- **Policies:** all 13 executed Pilot-V2 PRIMARY-panel policies (11 PRIMARY
  + 2 `STYLE_APPROXIMATION` robustness-only), in the order fixed by
  `robustbench.ranking_portability.phase12_smoke.SMOKE_POLICIES`.
  `distserve_faithful` and `llumnix_faithful` (secondary stratum) are
  explicitly excluded.
- **Repetitions:** `rep0` and `rep1` — both use the **identical** synthesis
  seed and identical scaled requests (the simulator is deterministic; reps
  verify bit-identical reproduction, not an independent stochastic draw).

## Selected window IDs

| Source | Window ID | Evidence class | Window content SHA-256 |
|---|---|---|---|
| `burstgpt` | `burstgpt_stage0_w00` | `STAGE0_WINDOW` | `73a99f07ae10bd332307cf3b9383d8c99c2a88adc35020f37c122a752400f54f` |
| `azure_llm_2024` | `azure_llm_2024_stage0_w00` | `STAGE0_WINDOW` | `4b428dca04a17119a165374edd3ff67026f60f203bfa523a9476c987a0a8d5aa` |
| `bailian_qwen` | `bailian_qwen_stage0_w00` | `STAGE0_WINDOW` | `47a85f452235531bed55a3ea3f41a5c5a226c374d2656e1e2f8cd451325d01fb` |

Each `content_sha256` above matches, byte-for-byte, both (a) this
repository's local compact index
(`artifacts/manifests/ranking_portability_pilot_v2_windows_index.json`)
and (b) the canonical, full-fidelity materialized manifest at
`/mmfs1/project/ikoutis/sv96/github/llm-serving-scheduler-ranking-portability-windows/artifacts/manifests/ranking_portability_pilot_v2_windows.json`
on Wulver (top-level `content_sha256` = `0d1aa06c...29eef`, i.e. the
Phase-10 scientific window hash itself) — independently re-verified before
this freeze. The 3 windows' full per-request records were extracted from
that canonical manifest (read-only; no re-derivation, no re-sampling) and
cached locally at `artifacts/smoke_input_windows_raw.json` for execution
in this environment (which does not otherwise have Wulver-mounted
filesystem access); this cache is a verified byte-identical subset of the
canonical artifact, not an independent reconstruction.

## Load assignment rule

No recalibration is performed. For every (source, window, region) cell,
this smoke consumes the frozen Phase-11 artifact
(`artifacts/manifests/ranking_portability_phase11_region_assignments.json`)'s
exact `lambda_ref` and `selected_load_factor` for that `(source,
window_id, region)` row, and computes the absolute compression factor as
`lambda_ref * selected_load_factor` — identical to
`build_phase11_calibration.py`'s own convention. The synthesis seed used
to build each window's base `Request` list is
`900000 + int(window_id.rsplit("w", 1)[1])`, identical to
`build_phase11_calibration.py`'s rule, so this smoke's synthesized
requests are byte-identical to what Phase-11 already calibrated against —
letting the smoke independently recompute `lambda_ref` from its own
synthesized requests and cross-check it against the frozen assignment
artifact's stored value as an integrity check (§ validation report).
No policy-under-study affects calibration; only the frozen `fifo`-derived
`lambda_ref` is ever used to scale load.

## Expected cell count

3 sources × 1 window/source × 6 regions × 13 policies × 2 reps =
**468 expected smoke cells**.

## Execution/schema/policy/simulator file hashes (frozen before execution)

| File | SHA-256 |
|---|---|
| `src/robustbench/ranking_portability/phase12_smoke.py` | `936b978f15d3d0b2322b6cc3a0d9ed6a9b049b98331120cb74bab281a88f2503` |
| `src/robustbench/ranking_portability/execute_cell.py` | `f43991b71a1588d1940f88de677351027a7ac13fc9144c4af90cd66fcf3d67a0` |
| `src/robustbench/ranking_portability/schema.py` | `dfb4b7815047852c5bf8d626daed1073380a844158ca54c76d030e47ae28e2b3` |
| `src/robustbench/ranking_portability/calibration.py` | `030ea1760ecc4797ab7a1bab48f8a7af3f59ddba54905d571ece6ef5cb1c8804` |
| `src/robustbench/workloads/external/benchmark_synthesis.py` | `8f429c8e640a1366c8251cafc14e0e6d802db910b137bb115bd92f26664c3e8b` |
| `src/robustbench/calibration/stage0_load_calibration.py` | `fe2c1d9f18c47d306bdf7ca991107befb89aaf722153ea1d6e934960a12de540` |
| `src/robustbench/policies/registry.py` | `662ed7d5308d0034a959186a27697d95af123b2e29702919d222579d522befd6` |
| `src/robustbench/simulator/simulator.py` | `a4fa693aa24c76e87bf0fc023ec88086f727dd926d89b586648c75c182ed1b5e` |
| `src/robustbench/simulator/telemetry.py` | `523755e263f52d67e8486e523a6a96bb725b9421e21b28ce5def7975a072ae3e` |

## Smoke freeze aggregate identity

`smoke_freeze_sha256 = 2a4a2f194fe3f1dec0d681f58f6b32f71e94d5e10af3d163ee00a5dd1718e1ce`

(SHA-256 over the sorted-key JSON of: parent branch SHA, all 5 immutable
scientific hashes, the frozen source/window/region/policy/repetition
lists, expected cell count, and the execution-file-hash table above.
Reproducible via
`robustbench.ranking_portability.phase12_smoke.compute_smoke_freeze_identity`.)

`PHASE12_SMOKE_PRELAUNCH_CONTRACT = SATISFIED`
