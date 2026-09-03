# LSSP Authoritative Project State — 2026-09-03

Handoff snapshot for a fresh coding agent / new chat. Produced by read-only
audit (Query 1 of 3 in a planned 3-query cleanup sequence). Every claim is
tagged `[VERIFIED_FACT]`, `[INFERENCE]`, or `[PENDING]`. No scientific
conclusions are drawn — this is state reconciliation only.

## 1. Project objective and frozen RQs

`[VERIFIED_FACT]` Paper: "Journal of Supercomputing" (JSC) submission on
LLM-serving scheduler robustness / ranking portability. Manuscript defines
RQ1–RQ6 (see `paper/sections/introduction.tex` / `study_design.tex` in the
manuscript branches). RQ3 (synthetic-to-real ranking transfer) is explicitly
SECONDARY, never a headline RQ. RQ6 covers real-vLLM validation of the
simulator.

`[VERIFIED_FACT]` Phase-12 result-blind analysis pipeline was sealed at
commit `eb574a8` and re-sealed at `bd641d4` on
`research/lssp-phase12-analysis-prefreeze-20260902`. All later research
branches (cross-metric, RQ3, SLO-sensitivity) are described in their own
protocol docs as **independent extensions built on top of that sealed code,
not modifications of it** (`scientific_status:
POST_PHASE12_RESULT_INDEPENDENT_ANALYSIS_EXTENSION` recorded in every
status/manifest JSON produced by these extensions).

## 2. Authoritative branch/worktree map

`[VERIFIED_FACT]` Single git repo (`llm-serving-scheduler-robustness-benchmark`,
remote `origin = github.com/SoroushVahidi/llm-serving-scheduler-robustness-benchmark`)
checked out as ~30 worktrees under `/home/soroush/repos/llm-serving-scheduler-*`.
Full `git worktree list --porcelain` was captured; only branches relevant to
the LSSP RQ3/RQ6/cross-metric/SLO/manuscript thread are listed below.

| Role | Branch | SHA | Worktree dir |
|---|---|---|---|
| SCIENTIFIC_BASE | `research/lssp-phase12-analysis-prefreeze-20260902` | `bd641d4` | `lssp-phase12-analysis-prefreeze` |
| PHASE12_RESULTS | `research/lssp-phase12-analysis-prefreeze-20260902` | `bd641d4` | same as above — this branch tip *is* the seal commit |
| CROSS_METRIC | `research/lssp-cross-metric-analysis-extension-20260903` | `b009e9d` | `lssp-cross-metric-analysis-extension` |
| RQ3 | `research/lssp-rq3-synthetic-to-real-prefreeze-20260903` | `bd641d4` (committed tip) | `lssp-rq3-synthetic-to-real` |
| RQ6 | `research/lssp-rq6-real-vllm-scientific-prefreeze-20260902` | `773982a` | `lssp-rq6-scientific-prefreeze` (mirrored on Wulver, see §9) |
| SLO | `research/lssp-slo-sensitivity-extension-20260903` | `67f5cad` | `lssp-slo-sensitivity-extension` |
| MANUSCRIPT | ambiguous — see §11 | `a37e706` (both candidates) | `lssp-manuscript-jsc`, `lssp-jsc-reviewer-polish` |
| ARTIFACT_REPRO | `research/lssp-artifact-repro-prefreeze-20260902` | `8a624e4` | `lssp-artifact-repro` |
| RELEASE_PREP | `release/lssp-jsc-artifact-prep-20260902` | `f46bfb5` | `lssp-release-prep` |
| (sibling) | `research/lssp-dataset-release-prefreeze-20260902` | `2b9a21f` | `lssp-dataset-release-prefreeze` |

`[INFERENCE]` PHASE12_RESULTS and SCIENTIFIC_BASE are the same branch/commit
because the seal commit itself constitutes "the results." Two other
Phase-12-named branches exist —
`research/lssp-phase12-reuse-audit-20260902` (`44e3a6e`, worktree
`lssp-phase12-freeze`) and `validation/lssp-phase12-structural-audit-20260902`
(`2aba8b6`, worktree `lssp-phase12-result-validation`) — these are read-only
**audit/validation checkpoints**, not alternative results branches; their
names (`-freeze`, `-result-validation`) are misleading relative to their
actual branch refs (`reuse-audit`, `structural-audit`). `[PENDING]` confirm
this reading in Query 2 before touching either.

`[VERIFIED_FACT]` **Naming trap**: the worktree literally named
`lssp-authoritative` (branch `research/lssp-authoritative-pre-phase12-20260901`,
tip `ec12af8`, last commit 2026-09-02 10:03, message "finalize LSSP
manuscript and repository foundation") **predates the Phase-12 seal** and is
now stale. Despite its name it is **not** the current authoritative branch
for anything. Its `docs/PROJECT_STATUS.md`, `docs/EXPERIMENT_STATUS.md`,
`docs/DATA_ACQUISITION_STATUS.md` almost certainly describe pre-Phase-12
state — treat as historical, not current. `[PENDING]` decide in Query 2
whether to rename/archive this worktree to remove the naming hazard.

## 3. Phase-12 campaign identifiers/hashes

`[VERIFIED_FACT]` Seal commit: `bd641d4902431b821cd7eb4ce9ad236955cec45d`
("Record post-repair Phase-12 analysis-code seal"), preceded by
`eb574a8` ("Seal Phase-12 result-blind analysis interface repair"). All three
post-Phase-12 extensions (cross-metric, RQ3, SLO) record `code_sha` values
descending from this lineage in their output manifests.

## 4. Completed experiments

- `[VERIFIED_FACT]` **RQ3 pilot**: 176/176 cells (manifest
  `8591a009…fce3b6`), 24/24 analysis records, 0 duplicates, 0 undefined
  (`rq3_status.json`). `is_pilot: true`. This is PILOT only — see §9 for why
  it must not be conflated with a full extension.
- `[VERIFIED_FACT]` **Cross-metric extension**: 990/990 correlation records
  status `OK`, 54,450 disagreement records generated, run log ends cleanly
  with a JSON summary listing all 4 output files
  (`cross_metric_correlations.json`, `cross_metric_topk.json`,
  `cross_metric_status.json`, `cross_metric_pairwise_disagreements.json`).
  Contract hash `33729102…1de8dea16cc7ab68d53b61fd9`, code_sha `b009e9d`.
- `[VERIFIED_FACT]` **SLO-sensitivity full campaign**: raw generation is
  **COMPLETE** — `artifacts/analysis/slo_sensitivity/full_run_20260903.log`
  ends with `DONE mode=full n_total=19800 n_success=19800 n_failed=0
  n_validation_failures=0`; `full/results.json` (37MB) independently
  verified to contain exactly 19,800 keys, all with `success: true`. This
  finished shortly before this audit ran (results.json mtime ≈ 2026-09-03
  15:12 EDT). **This corrects a stale assumption carried into this query as
  "RUNNING_HEALTHY" — it is done.** No local or Wulver tmux session named
  `lssp-slo-full` (or anything SLO-related) is currently running, consistent
  with completion, not with an active/dead-mid-run process.

## 5. Currently running experiments

- `[VERIFIED_FACT]` **RQ6 Slurm array 1220661, task 108**: `RUNNING` on
  node `n0001`, elapsed 1:47:49 of a 4:00:00 limit at check time. Untouched
  per instructions.

## 6. Failed/incomplete items

- `[VERIFIED_FACT]` **RQ6 task 19**: `FAILED`, elapsed 00:00:28, ExitCode
  `1:0`. Root cause fully identified (§9): a hardcoded port-derivation
  formula collides between task *i* and task *i+100*.
- `[PENDING]` **SLO-sensitivity full-scale analysis** (correlation /
  ranking-robustness / reversal-persistence statistics computed *over* the
  19,800-cell full results): only a **pilot-scale** analysis exists
  (`.../pilot/slo_sensitivity_status.json`: 36 input rows, 4
  ranking-robustness records, 108 reversal-persistence records, 0
  reversals persisting or disappearing). No analysis has yet been run over
  the full 19,800-cell `results.json`. The `full/` output directory
  currently contains only the raw per-cell `results.json` — no
  correlation/topk/status files analogous to the cross-metric extension's
  output shape.
- `[PENDING]` **RQ3 full extension**: does not exist yet — only the pilot
  manifest/analysis are present (§9).

## 7. Cross-metric result state

See §4. Additionally: `git status --short` in
`lssp-cross-metric-analysis-extension` is **clean** — everything is
committed at `b009e9d`. `[VERIFIED_FACT]`

## 8. RQ3 state

`[VERIFIED_FACT]` **PILOT_COMPLETE**: 176/176 cells, 24/24 analysis records,
0 failed/duplicate/undefined (§4).

`[VERIFIED_FACT]` **FULL_EXTENSION: NOT STARTED.** No full-scale manifest,
config, or analysis directory exists anywhere under
`lssp-rq3-synthetic-to-real`. Only pilot-scoped artifacts
(`artifacts/rq3/synthetic_to_real/<hash>/analysis_pilot/…`,
`analysis_manifest ...pilot_20260903.json`) exist.

`[VERIFIED_FACT]` **Critical hygiene risk**: `lssp-rq3-synthetic-to-real`
worktree is **dirty** — the entire RQ3 protocol doc
(`docs/RQ3_SYNTHETIC_TO_REAL_PROTOCOL_20260903.md`), config
(`configs/rq3/rq3_synthetic_to_real_20260903.json`), source
(`src/robustbench/rq3/`), scripts (`scripts/rq3/*.py`), and result manifests
(`artifacts/manifests/rq3/*.json`) are **all untracked**, not committed to
the `research/lssp-rq3-synthetic-to-real-prefreeze-20260903` branch (whose
committed tip is still just `bd641d4`, identical to the sealed base). If
this worktree were deleted or reset, **all RQ3 pilot work would be lost.**
This is the single highest-priority item for Query 2.

## 9. RQ6 state

`[VERIFIED_FACT]` Slurm array `1220661`, 120 tasks (indices 0–119), on
Wulver. Current counts from `sacct`:

| State | Count |
|---|---|
| COMPLETED | 118 |
| RUNNING | 1 (task 108) |
| FAILED | 1 (task 19) |
| PENDING | 0 |

Task 19: `Elapsed 00:00:28`, `ExitCode 1:0`.
Task 95 (previously flagged): `COMPLETED`, `Elapsed 00:30:55`, `ExitCode 0:0`.

**Task 19 root cause** `[VERIFIED_FACT]`, traced from
`slurm-1220661_19.err`/`.out` on Wulver
(`/mmfs1/project/ikoutis/sv96/github/llm-serving-scheduler-lssp-rq6-calibration-20260903/artifacts/real_vllm/calibration/rq6/slurm_logs/`):

- `scripts/real_vllm/run_rq6_calibration.sbatch` line 33:
  `PORT=$((8100 + SLURM_ARRAY_TASK_ID % 100))`. This collides for any pair
  `(i, i+100)` in range 0–119 — task 19 and task 119 both compute
  `PORT=8119`.
- `sacct` timestamps confirm both ran on node `n0001` with an overlapping
  window: task 119 ran 14:02:59–14:08:55; task 19 started 14:08:32 (23s
  before 119 released the port).
- Task 19's vLLM server could not bind port 8119 (already held by task
  119's still-running server); the client's first `/metrics` health check
  during `bisect_lambda_ref_real` → `check_reset_barrier` raised
  `httpx.ConnectError: [Errno 111] Connection refused`, crashing the task.
- Frozen scientific inputs (model, calibration protocol, manifest) are
  completely unaffected — this is a pure port-allocation bug in the sbatch
  launcher, not a data or protocol issue.

`RQ6_TASK19_ROOT_CAUSE` = port collision between array indices 19 and 119
(both map to port 8119 under `8100 + idx % 100`), triggered by
node-co-location + overlapping wall-clock windows.
`RQ6_TASK19_FAILURE_CLASS` = engineering / infrastructure (launcher bug),
not scientific.
`RQ6_TASK19_RETRY_SAFETY` = **SAFE_ENGINEERING_RETRY** — task 119 has
already completed and released its slot, so an isolated rerun of task 19
alone would not hit the same collision. (Note for Query 2/3: the underlying
`% 100` formula should ideally be widened to `% 120` or replaced with a
per-node port allocator before any future rerun of the full array, in case
two colliding indices are ever co-scheduled again.)

`RQ6_TASK108_STATE` = RUNNING, healthy, 1:47:49 elapsed / 4:00:00 limit,
node n0001. Untouched.

`[VERIFIED_FACT]` **Location risk**: RQ6's actual execution artifacts
(sbatch logs, per-task JSON outputs, and one **uncommitted** modified file
`scripts/ranking_portability/build_phase11_calibration.py`) live only in a
Wulver-side git worktree at
`/mmfs1/project/ikoutis/sv96/github/llm-serving-scheduler-lssp-rq6-calibration-20260903`
(HEAD `773982a`, same commit as the local `lssp-rq6-scientific-prefreeze`
worktree) — this location is **not mirrored** in the local
`/home/soroush/repos/` worktree set and was not discovered until this audit
searched Wulver's `/mmfs1/project/ikoutis/sv96/github/` tree. `[PENDING]`
inspect and either commit or discard that uncommitted diff in Query 2 —
do not assume it is unrelated to the task-19 fix without reading it first.

## 10. SLO state

See §4/§6. Raw generation: **COMPLETE** (19,800/19,800, 0 failures).
Full-scale statistical analysis (correlations/reversals over the full run,
analogous to the pilot's `slo_sensitivity_status.json`): **NOT YET RUN**
`[PENDING]`. Worktree clean, branch `67f5cad`.

## 11. Manuscript state

`[VERIFIED_FACT]` Two branches, **identical commit** `a37e706aa...`
("Reconcile robustness-contract discrepancy: LEAVE_ONE_POLICY_FAMILY_OUT
was materialized, add it"):
- `manuscript/lssp-jsc-polish-20260902` (worktree `lssp-manuscript-jsc`)
- `manuscript/lssp-jsc-reviewer-informed-polish-20260903` (worktree
  `lssp-jsc-reviewer-polish`)

`git merge-base --is-ancestor` confirms they are the same commit — the
2026-09-03-dated branch was cut from the 2026-09-02 branch's tip and has
**zero new commits**. Neither name is more "authoritative" by history alone;
the newer date suggests intended forward direction but carries no actual
content difference yet. **This must be resolved by a human/Query-2 decision,
not inferred.** `[PENDING]`

`[VERIFIED_FACT]` **Uncommitted declarations update, wrong worktree**: the
funding / acknowledgements / generative-AI-disclosure text described in the
task brief exists **only as an uncommitted `git diff`** in
`lssp-manuscript-jsc` (`paper/sections/declarations.tex`, +18/-3 lines) —
it is not committed to either manuscript branch, and it is **absent** from
the `lssp-jsc-reviewer-polish` worktree's committed content (which still
shows the placeholder "no funds... `[AUTHOR TO CONFIRM]`" and no
Acknowledgements/Generative-AI-statement paragraphs at all). If
`lssp-manuscript-jsc` were reset or the worktree removed, this text would be
lost.

- `FUNDING` = present (uncommitted diff only) — CloudRift AI Builder Grant,
  Cohere Labs Catalyst Grant Program, AMD AI Developer Program /
  Fireworks AI credits.
- `ACKNOWLEDGEMENTS` = present (uncommitted diff only) — Professor Ioannis
  Koutis.
- `GENERATIVE_AI_USE` = present (uncommitted diff only) — ChatGPT, Codex,
  Claude, Gemini, Cursor, Perplexity AI.
- `COMPETING_INTERESTS_PLACEHOLDER_REMAINS` = **YES** — the diff does not
  touch the Competing Interests paragraph; `[AUTHOR TO CONFIRM before
  submission.]` is still present in both worktrees.

**Result integration into manuscript body** (grepped `paper/sections/*.tex`
in `lssp-jsc-reviewer-polish`):

| Item | Status |
|---|---|
| CROSS_METRIC_IN_MANUSCRIPT | `NOT_INTEGRATED` — "cross-metric" appears once in `related_work.tex` as framing language for the paper's contribution, not as a reference to the actual 990/54,450-record extension result. |
| RQ3_IN_MANUSCRIPT | `NOT_INTEGRATED` — RQ3 appears only as the original research-question definition in `introduction.tex`/`study_design.tex`; no mention of "synthetic-to-real" pilot or extension results anywhere. |
| SLO_IN_MANUSCRIPT | `PENDING_RESULT`, and **stale**: `results.tex` §"SLO-Definition Sensitivity" currently states *"remains unavailable... no such result is reported or fabricated here"* — this is now factually contradicted by §4/§10 (the full 19,800-cell run has completed, and a pilot-scale analysis with actual numbers already exists). This text needs updating in a future query, but was **not edited here** per read-only-audit scope. |
| RQ6_IN_MANUSCRIPT | `PENDING_RESULT` — `real_system.tex` line 129 contains an explicit `"Placeholder: simulator-vs-real-vLLM ranking agreement..."` table caption awaiting the calibration campaign's real numbers. |

## 12. Artifact/repro state

`[VERIFIED_FACT]` `research/lssp-artifact-repro-prefreeze-20260902` (`8a624e4`)
and `release/lssp-jsc-artifact-prep-20260902` (`f46bfb5`) worktrees are both
clean (`git status --short` empty). `[PENDING]` Content-level review of
artifact/repro completeness was out of scope for this fast audit — not
inspected beyond confirming clean working trees.

## 13. Pending scientific integration work

1. Run full-scale statistical analysis over the completed 19,800-cell SLO
   results (currently only pilot-scale analysis exists).
2. Decide/launch (or explicitly defer) the RQ3 full extension — currently
   only a pilot exists.
3. Update `results.tex` SLO-sensitivity section once full-scale analysis
   exists — current text says the result "remains unavailable," which is
   now false at the raw-data level (analysis-level it is still true).
4. Integrate cross-metric extension findings, RQ3 pilot/extension findings,
   and RQ6 real-vLLM findings into manuscript body sections (currently a
   placeholder/absent for all three).
5. Resolve the manuscript branch ambiguity (§11) and commit the
   declarations.tex update to whichever branch is chosen authoritative.

## 14. Known caveats

- This audit is **fast and read-mostly**; it did not open every file in
  every one of the ~30 worktrees (out of scope: ranking-portability /
  stage0 / robustness-benchmark worktrees not directly in the
  RQ3/RQ6/cross-metric/SLO/manuscript thread — listed in §2 only as
  "sibling" branches, not characterized further).
- The 54,450-record cross-metric disagreement file and the 19,800-cell SLO
  results file were inspected only via aggregate/structural checks
  (key counts, a `success`/`status` field tally), never fully loaded/printed,
  per task instructions.
- RQ6's Wulver-side uncommitted diff (§9) was located but its contents were
  **not read** in this pass — flagged as a `[PENDING]` for Query 2.

## 15. Exact next actions in priority order

1. **Commit the untracked RQ3 pilot work** in `lssp-rq3-synthetic-to-real`
   (docs/configs/src/scripts/artifacts/manifests) before anything else
   touches that worktree — it is currently one `git clean`/reset away from
   being permanently lost.
2. **Commit or discard** the uncommitted `declarations.tex` edit in
   `lssp-manuscript-jsc`, after deciding which manuscript branch is
   authoritative (§11) — do not let it sit uncommitted through a Query-2
   cleanup pass.
3. **Inspect** the uncommitted diff in the Wulver-side RQ6 worktree
   (`build_phase11_calibration.py`) before deciding whether to commit,
   discard, or fold it into a task-19 retry.
4. **Retry RQ6 task 19 only**, once task 108 finishes (to avoid adding
   scheduling contention) — safe per §9's root-cause analysis. Do not
   touch task 108 before then.
5. Run the full-scale SLO-sensitivity analysis step now that raw generation
   is complete.
6. Decide manuscript-branch consolidation (§11) and rename/archive the
   misleadingly-named `lssp-authoritative` worktree/branch (§2) to remove
   the naming hazard for future sessions.
