# EXPERIMENT_REUSE_AUDIT_20260902.md

Independent experiment-reuse audit for the frozen Phase-12B 18,720-cell LSSP
campaign (`campaign_freeze_sha256 = 81fa3d9b48a2241001e6820942d4542dcc5b5e30973ad9d2786e72972494f57a`,
`full_matrix_hash = 832d96d7ff4d5e8843c233a6a4708bbbbc578ef6b65307c37f5ac127c62c1ccf`,
branch `research/lssp-phase12-campaign-freeze-20260902` @ `2b9a21fb58798292c95980d35d05e53b3c6f14f6`).
Read-only investigation. **No Phase-12 scientific cell was executed, no Slurm
job was submitted, no frozen artifact was altered, and no ranking/
scheduler-performance analysis was performed by this audit.**

## Scope

Question: has any prior or parallel experiment already executed
scientifically equivalent cells/results to the frozen 18,720-cell campaign,
such that some or all results could legitimately substitute for fresh
execution? This is a compute/result-reuse question, distinct from
`docs/OVERLAP_LEDGER.md`'s novelty/claim-boundary audit (which asks whether a
*contribution* would duplicate another manuscript's headline claim, not
whether a *cell* has already been computed).

## Scientific-equivalence criteria (applied strictly)

A candidate prior result counts as `EXACT_REUSABLE_CELL` only if it matches
the frozen cell on **all** of: source family + exact provenance, exact
window/request set and content hash, synthesis transformation/version/seed,
load-calibration semantics and the specific `lambda_ref`/region assignment
used, absolute request-rate scaling, policy ID and implementation/version,
simulator implementation/version/config, metric semantics and SLO
construction, completion-conditioned NaN/undefined-metric convention,
repetition semantics, and output schema (including the telemetry fields
required by `docs/RANKING_PORTABILITY_ANALYSIS_PLAN.md` §E). Same source
name, same scheduler name, "similar" load, or same metric name alone is
**not** equivalence.

## Repositories / storage searched

- All 39 directories under `/home/soroush/repos/` (`grep -rl` for
  reuse/overlap terminology; targeted reads of the LSSP lineage repos).
- `/home/soroush/llm-serving-heuristic-evolution` (LLM 2026 source repo,
  branch `contextual-compositional-heuristics-20260731`-derived state,
  `HEAD=94f4621`), specifically `src/llmserveopt/policy_separation/
  public_replay_load_scaling_v1.py`/`v2.py`, `public_trace_replay_v1.py`,
  `docs/design/PUBLIC_REPLAY_LOAD_SCALING_V{1,2}.md`, and its Slurm
  logs/experiment output under `experiments/public_replay_load_scaling_v1/`.
- `/home/soroush/module-intervention-credit-v2-staging` (closest local
  checkout touching SIGMETRICS/module-intervention concepts available in
  this environment; not a git repo, greps for the three LSSP source names
  and the LSSP policy IDs returned nothing).
- `llm-serving-scheduler-project-state-audit` (`docs/OVERLAP_LEDGER.md`,
  `GO_NO_GO_GATES.md`, `RELATED_WORK_NOVELTY_AUDIT.md`, `EVIDENCE_INDEPENDENCE_PLAN.md`).
- HF dataset `SoroushVahidi/llm-serving-scheduler-baselines` — read directly
  via the Hugging Face Hub filesystem tool (README/dataset card, both config
  schemas), not from local docs alone.
- Wulver cluster (`ssh wulver`, live, reachable from this environment):
  searched `/project/ikoutis/sv96` and `/mmfs1/project/ikoutis/sv96` for
  `*phase12*`/`*campaign_result*` paths, inspected the discovered worktree's
  git state, its generated `.sbatch` file, its `campaign_results/` and
  `phase12_campaign_logs/` directories (file counts, `.out`/`.err` contents,
  per-shard cell counts, mtimes). **`squeue`/`sacct`/`module` were not on
  `PATH` in the non-interactive SSH shell used here**, so live queue state
  (RUNNING/PENDING) could not be directly confirmed — see the Wulver finding
  below and its stated limitation.
- Local filesystem: `.bash_history` (grep for `sbatch`/`phase12`), the
  phase12-freeze repo's own gitignored `artifacts/campaign_results/` (local
  checkout), `.gitignore`.

**Limitation:** this audit did not attempt to independently row-count or
re-derive the real BurstGPT/Azure/Bailian source corpora (none are acquired
locally, per `docs/DATA_LICENSE_AUDIT.md`), and did not open every file in
every one of the ~20 `llm-serving-module-intervention-benchmark-*`
timestamped checkpoint directories under `/home/soroush/repos/` individually
— `docs/PROVENANCE.md`'s explicit "not copied" list (everything under
`module_intervention_benchmark/gate1/*`, `benchmark_v2/*`,
`real_vllm_prefill_validation/*`, `release/*`, and all of `llmserveopt/
policy_separation/*`, `selector/*`, `composition/*`, `analysis/*`) was taken
as an authoritative, previously-verified boundary rather than re-walked
file-by-file in every checkpoint copy; a `grep` for the three LSSP source
names and LSSP policy IDs across the one available local
module-intervention checkout returned zero hits, consistent with that
boundary.

## Critical out-of-scope finding: the frozen campaign already has a live/near-complete execution on Wulver

Independent of any prior/parallel *other* experiment, this audit found that
the frozen campaign **itself** appears to already be executing (or to have
recently executed) on Wulver, discovered incidentally while searching
storage for reusable artifacts:

- Worktree `/project/ikoutis/sv96/github/llm-serving-scheduler-lssp-phase12-campaign-run`
  on Wulver, at git HEAD `2b9a21f` (same commit as the local freeze branch),
  contains a generated `artifacts/phase12_campaign.sbatch` embedding
  `campaign_manifest_freeze_sha256=81fa3d9b48a2241001e6820942d4542dcc5b5e30973ad9d2786e72972494f57a`
  (the exact frozen identity) and `--array=0-63`, `--execute`.
- `artifacts/campaign_results/81fa3d9b48a22410/` (the campaign-freeze-SHA
  namespace) contains all 64 `shard_NNN.json` checkpoint files.
- **17,882 / 18,720 cells (95.5%) present** across those 64 files as of the
  last check in this session (per-shard counts ranged 224–293, matching the
  frozen shard plan's expected ~292–293 cells/shard for most shards; several
  shards below that count, consistent with a run still in progress rather
  than one that failed).
- `phase12_campaign_logs/`: 48/64 `.out` files non-empty with clean
  `shard_id=N / computed_this_run=... / invalid_or_failed_after_run=0`
  summaries (sampled `shard_0.out`: `cell_count=293`,
  `computed_this_run=293`, `invalid_or_failed_after_run=0`); 16/64 empty
  (consistent with tasks still running or queued); **0 non-empty `.err`
  files found** in this pass.
- Result-file mtimes were actively advancing during this audit's own
  inspection window (e.g. `shard_055.json` written at `11:33:02`, during
  this session), confirming this is very recent/live activity, not stale
  leftover data from an earlier, unrelated run.
- This audit performed no scientific/ranking inspection of the result
  content — only structural facts (cell counts, presence/absence of error
  output, timestamps) were read, consistent with "structural canary check
  only," never scheduler-performance direction.

**This directly contradicts `docs/PROJECT_STATUS.md`'s and
`docs/RANKING_PORTABILITY_PHASE12_CAMPAIGN_PRELAUNCH_FREEZE.md`'s current
`PHASE12_CAMPAIGN_EXECUTION_STARTED = NO` / "READY, NOT STARTED" text**,
which is now stale as of this audit. It is not itself part of this audit's
assigned reuse question (it is the *same* frozen campaign's own execution,
not an external/parallel one) — flagged here because it materially affects
the launch-gate decision the parent conversation is managing, but this
audit was not authorized to interpret it further, retrieve a Slurm job ID,
or take any action on it (submitting, cancelling, or resuming anything on
Wulver is explicitly out of this audit's scope).

A small local, gitignored, uncommitted echo of the same in-progress checkpoint
exists at `artifacts/campaign_results/81fa3d9b48a22410/shard_000.json` in
*this* local repo checkout (228/293 cells, all `success=True`,
`scientific_status=PILOT_V2_SCIENTIFIC`, `repo_sha=51256ea1...`, but several
required provenance-hash fields — `calibration_manifest_sha256`,
`policy_registry_hash`, `simulator_config_hash`, `synthesis_version`,
`window_manifest_sha256` — are empty strings rather than populated hashes).
That empty-provenance-field detail is an engineering observation, not a
reuse-audit finding; it is left unresolved here per this audit's charter not
to touch Phase-12C engineering code.

## Exact reusable cells found

**0.** No prior or parallel experiment anywhere searched contains a cell
matching a frozen Phase-12 `(source, window, region, policy, repetition)`
tuple on every scientific-equivalence dimension in the criteria above.
Reasoning by candidate, below.

## Partial overlaps found

| Candidate | Overlapping dimensions | Non-matching dimensions (any one disqualifies exact reuse) | Classification |
|---|---|---|---|
| LLM 2026 `public_replay_load_scaling_v1/v2` | Source *families* only for 2 of 3 (BurstGPT; Azure — but 2023, not 2024) | Window set (60 fixed windows, `WINDOW_SIZE=200`, deterministic-but-different sampling rule vs. LSSP's own 40/source rule — cell-ID schemes are structurally different: `{canonical_scenario_id}::lambda{N}::{policy_id}` vs. `{source}::{window_id}::{load_region}::{policy_id}::rep{0,1}`); load design (`{1,2,4,8,16,32,64,128}` λ-multiplier grid vs. 6 named calibrated regions tied to Phase-11's own `lambda_ref`); policy panel (Pext = 6 P6 baselines + `official_vtc_joint_token_budget_remap` + `vllm_style_continuous_batching` — **0 of these 3 non-P6 policy IDs appear in LSSP's 13-policy panel**; P6/LSSP overlap is at most name-level for a handful of classical policies, not implementation-pinned identity per `docs/POLICY_COMPARABILITY_AUDIT.md`); Azure split (2023 vs. 2024 — `docs/EVIDENCE_INDEPENDENCE_PLAN.md` treats these as two distinct, non-interchangeable sources); simulator/repo lineage (different repo, `llm-serving-heuristic-evolution` vs. `robustbench` port, `docs/PROVENANCE.md` explicitly did **not** copy `policy_separation/*`); telemetry schema (LLM 2026 has none of LSSP's 7 mechanism-telemetry fields); scientific_status tagging; repetition semantics. Also explicitly `PROHIBITED_OVERLAP`/`PRIOR_RESULT_REFERENCE_ONLY` by standing project policy (`docs/OVERLAP_LEDGER.md`, `docs/CLAIM_BOUNDARIES.md`, Gate A) regardless of any technical match. | `PRIOR_RESULT_REFERENCE_ONLY` |
| Stage-0 (`research/stage0-zero-completion-undefined-metrics-20260901`, 1,080 real cells) | Same 3 source families (BurstGPT, Azure LLM 2024, Bailian/Qwen); its 10 windows/source are, by construction, a strict subset of LSSP's 40 windows/source (`docs/RANKING_PORTABILITY_PILOT_V2_PROTOCOL.md` §4); same deterministic synthesis rule (`stage0_synthesis_v1`, reused verbatim per §8 of the freeze doc); simulator is deterministic (no stochastic seed) | Policy panel: Stage-0 used a 6-policy subset (`docs/STAGE0_DISCRIMINABILITY_PROTOCOL.md`), not the 13-policy PRIMARY+robustness panel; load regions: Stage-0 used only `PRE_KNEE`/`KNEE`/`OVERLOAD` (3 regions, explicitly excluding `LOW`) against its **own** load-calibration run, not the frozen Phase-11 six-region calibration LSSP cells are keyed to (`region_assignment` hash `9fcb92f9...`) — Stage-0 predates and is not verified identical to that calibration artifact, so even a name-matching region label (e.g. `KNEE`) is not guaranteed to carry the same absolute request-rate scaling; **schema**: Stage-0's cell schema has none of the 7 `ALWAYS_DEFINED` mechanism-telemetry fields (`mean_queue_depth`, `batch_saturation_mean`, `mean_kv_occupancy`, etc.) that `docs/RANKING_PORTABILITY_ANALYSIS_PLAN.md` §E requires for every Pilot-V2 cell — a hard schema-validation blocker, not a policy choice; `scientific_status` tag differs (Stage-0 cells are not tagged `PILOT_V2_SCIENTIFIC`); and the preregistered protocol itself explicitly forbids the relabeling (`docs/RANKING_PORTABILITY_PILOT_V2_PROTOCOL.md` §0: "not... re-run Stage 0 until BurstGPT passes"; `docs/SCIENTIFIC_EVIDENCE_INVENTORY.md` classifies Stage-0 as `HISTORICAL_PILOT`, explicitly "not equivalent to the final benchmark"). Even the theoretically-closest overlap candidate found in this audit therefore fails on at least two independent, non-waivable grounds (schema completeness, protocol prohibition) before load-calibration identity is even considered. | `SEMANTIC_PARTIAL_OVERLAP` (closest candidate found; still not reusable) |
| Phase-11 FIFO calibration | Same windows/sources/regions | Single-policy (`fifo`) only; explicitly calibration provenance, not a comparative scheduler outcome (`docs/SCIENTIFIC_EVIDENCE_INVENTORY.md` boundary statement); cannot supply any of the other 12 policies' cells | `PRIOR_RESULT_REFERENCE_ONLY` (infrastructure/calibration input, not a substitutable result) |
| Phase-12A engineering smoke (468 cells) | Same repo/simulator/schema version, small subset of sources/windows/policies | Explicitly documented as engineering-only; `docs/PROJECT_STATUS.md` and the protocol give no permission to promote smoke cells to scientific evidence; smoke windows/policy subset chosen for coverage, not preregistered as part of the 18,720-cell design | `PRIOR_RESULT_REFERENCE_ONLY` |
| SIGMETRICS 2027 / module-intervention-benchmark | None found — no BurstGPT/Azure-2024/Bailian source usage or LSSP policy-ID matches in the one locally available checkout; `docs/PROVENANCE.md` independently confirms its scheduler-execution code paths (`gate1/*`, `benchmark_v2/*`, `real_vllm_prefill_validation/*`) were never copied into the LSSP repo | — | `PRIOR_RESULT_REFERENCE_ONLY` (different research question; no cell-level candidate exists) |
| HF `SoroushVahidi/llm-serving-scheduler-baselines` (`per_policy_results`, 36,975 rows) | Some policy-ID name overlap (`fifo`, `edf`, `admission_control`, etc.) | Workload grain: **41 synthetic parametric stress envelopes**, never BurstGPT/Azure-2024/Bailian raw-trace-derived windows (dataset card: "not raw production-trace replay"); no `window_id`/source-window identity to match against LSSP's frozen 120-window manifest at all; different metric-record grain (`regime_id`+`seed`, not `(source,window,region,policy,rep)`); dataset card explicitly warns against "mixing rows across configs as if they share the same workload grain or trace source" | `SEMANTIC_PARTIAL_OVERLAP` at the *policy-implementation* level only, `NO_EXISTING_RESULT` at the cell level |
| HF `tracelab_scheduler_ood_policy_sweep` (13,824 rows, 512 TraceLab-derived windows) | None at the source-family level — TraceLab is not one of LSSP's 3 sources; independence from this config is in fact a *precondition* LSSP's own `docs/EVIDENCE_INDEPENDENCE_PLAN.md` already imposed on itself | Entirely different source (TraceLab, not BurstGPT/Azure-2024/Bailian), different window construction (sqrt-compressed, synthetic-SLO-labeled, session-scoped), different policy library version (20+7 v2 entries vs. LSSP's pinned 13) | `NO_EXISTING_RESULT` for LSSP cells; `PRIOR_RESULT_REFERENCE_ONLY` for any future TraceLab-as-4th-source work |
| Real-vLLM runs (`real_llm/calibration_common.py` reuse only; no executed real-vLLM campaign found in this project) | Harness code only | No executed real-vLLM results exist yet for this project (`docs/GO_NO_GO_GATES.md` Gate F = "PASS (feasibility only)"); cannot substitute for any of the 18,720 *simulated* cells by design (RQ6 is a different, real-hardware question) | `REUSABLE_INFRASTRUCTURE` only |

## Prior-result-only artifacts

Everything in the "Partial overlaps" table above classified
`PRIOR_RESULT_REFERENCE_ONLY` belongs here as well: LLM 2026's
`public_replay_load_scaling_v1/v2` result and verdict, Stage-0's
`STAGE0_NO_GO` verdict, Phase-11's FIFO calibration, and Phase-12A's smoke
pass. All are citable as background/history; none may be restated as, or
substituted for, Phase-12 campaign evidence.

## Reusable inputs

- Frozen 120-window compact index (`ranking_portability_pilot_v2_windows_index.json`,
  hash `d78ec1087f...`) and full materialized windows manifest — already the
  canonical input to the frozen campaign itself, not "reuse" in the
  cross-project sense but confirmed intact/unchanged.
- Frozen Phase-11 six-region assignment (`9fcb92f9...`) and raw FIFO
  calibration (`201caaf0...`) — same status.
- Stage-0's synthesis rule (`stage0_synthesis_v1`) — already adopted
  verbatim by the frozen campaign design (not new reuse, pre-existing).

## Reusable infrastructure

Per `docs/PROVENANCE.md` (independently reconfirmed, not re-derived here):
simulator core (`simulator/*`), policy interface/registry
(`policies/base.py`, `registry.py`, and ~25 classical/faithful policy
implementations), evaluation harness, calibration utilities, workload
adapters (BurstGPT/Azure/Mooncake/LMSYS/Bailian), synthetic generators,
serialization/seeding utilities — all `REUSED_INFRASTRUCTURE`, carrying no
scientific claim of their own. **The current Phase-12C engineering
implementation at `2b9a21f` (real `--execute` path, idempotent
checkpoint/resume, `run_phase12_campaign_shard.py`) is explicitly
`REUSE_INFRASTRUCTURE_ONLY` and was not redone, modified, or re-reviewed by
this audit**, per the parent instruction.

## TraceLab verdict

- **LSSP core reuse: NO.** Not one of LSSP's 3 frozen sources; adapter
  doesn't exist in this repo.
- **Reusable external validation dataset: NOT YET** — independence from the
  HF release's 512-window sweep is explicitly unverifiable at the
  session-level from public artifacts (`docs/TRACELAB_PROVENANCE_RESOLUTION.md`,
  `docs/EVIDENCE_INDEPENDENCE_PLAN.md`).
- **Reusable secondary/OOD analysis:** plausible *future* 4th-source
  candidate, explicitly deferred, not part of this frozen campaign.
- **Infrastructure/input only:** the HF sweep's *existence* is useful context
  for a future OOD design, nothing more.
- **Incompatible with the frozen 18,720-cell matrix as-is:** yes (wrong
  sources, wrong schema, wrong policy-library version).
- **New execution required** for any TraceLab-based LSSP claim.

## Synthetic-data verdict

HF `per_policy_results` (41 synthetic stress envelopes) cannot substitute
for any frozen cell (wrong workload grain entirely — no real-trace window
identity exists in that config). It remains valid, independent
`REUSABLE_INFRASTRUCTURE`/background evidence for a *separate*,
already-out-of-scope synthetic-vs-real transfer question (RQ3), not for the
core 18,720-cell matrix. **New execution required** for every frozen cell.

## Real-vLLM verdict

1. Reusable execution infrastructure: `real_llm/calibration_common.py` (yes,
   confirmed importable, `docs/GO_NO_GO_GATES.md` Gate F).
2. Reusable raw workload manifests: N/A — no real-vLLM run has been executed
   against LSSP's specific windows.
3. Reusable calibration methodology: the general calibration approach is
   documented (`docs/REAL_SYSTEM_VALIDATION_PLAN.md`) but not yet executed.
4. Existing results directly answering LSSP RQ6: **none** — Gate F is
   feasibility-only, no cases run.
5. Results belonging only to prior manuscripts: none identified as
   overlapping (LLM 2026's own `real_llm/` results are `PROHIBITED_OVERLAP`
   to restate per `docs/CLAIM_BOUNDARIES.md`, and are for a different
   question — selector validation, not rank-reversal reproduction).

Estimate of avoidable future real-system work: **none at present** — RQ6
execution has not started; only its harness and design are reusable.

## 18,720-cell accounting

| Category | Count |
|---|---:|
| Frozen cells | 18,720 |
| `EXACT_REUSABLE_CELL` (any external/prior source) | 0 |
| `SEMANTIC_PARTIAL_OVERLAP` (Stage-0, closest candidate; not reusable — see table above) | up to 1,080 raw Stage-0 cells structurally intersect on (source, a 10/40-window subset, a 3/6-region subset, a ≤6/13-policy subset) but 0 of these pass every equivalence dimension |
| `PRIOR_RESULT_REFERENCE_ONLY` (not cell-level candidates at all: LLM 2026, Phase-11, Phase-12A, SIGMETRICS) | 0 (no cell-level tuple match attempted; categorically excluded by source/schema/design) |
| `NO_EXISTING_RESULT` (no prior artifact of any kind covers this tuple) | 18,720 |

By source (all three sources are symmetric in this accounting — no source
has any externally reusable cell):

| Source | Frozen cells | Exact reusable | Notes |
|---|---:|---:|---|
| `burstgpt` | 6,240 | 0 | LLM 2026 touched 20 different BurstGPT windows under a different sampling rule/cell schema; Stage-0 touched a window-ID-overlapping-by-construction subset but fails schema/protocol reuse tests. |
| `azure_llm_2024` | 6,240 | 0 | LLM 2026 used Azure **2023**, a distinct source per `docs/EVIDENCE_INDEPENDENCE_PLAN.md`; zero known prior consumption of Azure 2024 by anything. |
| `bailian_qwen` | 6,240 | 0 | Zero known prior consumption anywhere (`docs/EVIDENCE_INDEPENDENCE_PLAN.md`). |

By policy family: the 3 `FAITHFUL_EXTERNAL`/classical policy IDs that also
appear (by name) in LLM 2026's Pext panel or the HF `per_policy_results`
taxonomy (`fifo`, `edf`, `admission_control`-style entries) still carry 0
reusable cells, because in every case the workload/window/schema dimension
already disqualifies reuse before the policy-identity question matters.

**Would substituting any of these hypothetically-closest (Stage-0) cells
violate other constraints even if the schema gap were fixed?** Yes —
preregistration (`docs/RANKING_PORTABILITY_PILOT_V2_PROTOCOL.md` §0 explicitly
frames this pilot as intentionally *not* a Stage-0 rerun/relabeling),
evidence independence is not the issue here but deterministic-repetition
and campaign-uniformity are: Stage-0 has no `rep0`/`rep1` structure to draw
from for the 12,960 (18,720 − Stage-0's structural-max-overlap) cells with
no Stage-0 counterpart at all, so a partial substitution would produce a
matrix with heterogeneous provenance the freeze's own integrity checks
(`validate_phase12_campaign_freeze.py`) are explicitly designed to reject.

## DO_NOT_RERUN

Nothing — no cell in the frozen matrix has a legitimate substitute, so there
is nothing to mark "already computed, do not rerun" from *external* sources.
(This is distinct from the Phase-12C checkpoint/resume system's own
in-campaign idempotence, which already handles not re-running a cell the
*same* campaign has itself already validated — see the Wulver finding above
for the current state of that in-progress execution.)

## GENUINELY_NEW_EXECUTION_REQUIRED

All 18,720 frozen cells require genuine new execution under this campaign's
own frozen design; no externally-sourced substitution is scientifically or
procedurally valid for any of them.

## Final launch-gate decision

`PHASE12_CAMPAIGN_REUSE_AUDIT = FULL_NEW_EXECUTION_REQUIRED`

`PHASE12_CAMPAIGN_LAUNCH_GATE_REUSE_AUDIT = PASS`

This audit is complete enough to make the launch-reuse decision: no prior or
parallel experiment anywhere searched (local repos, the named LLM-2026 and
module-intervention lines, the HF baselines dataset, and Wulver storage)
contains a scientifically-equivalent substitute for any frozen Phase-12
cell. **This verdict authorizes only the reuse-audit gate itself** — it is
not, by itself, permission to submit or resume any Slurm job; see the
Wulver finding above, which indicates the frozen campaign may already be
executing outside this audit's knowledge or control and needs the parent
conversation's direct attention before any further launch action is
considered.
