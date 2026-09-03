# LSSP Authoritative Project State — 2026-09-03

Handoff snapshot for a fresh coding agent / new chat. Originally produced by
read-only audit (Query 1 of 3 in a planned 3-query cleanup sequence);
updated after Query 2 (controlled organization/recovery/hygiene) and Query 3
(final scientific integration/manuscript reconciliation). Every claim is
tagged `[VERIFIED_FACT]`, `[INFERENCE]`, or `[PENDING]`. No scientific
conclusions are drawn beyond what the manuscript itself now states — this
is state reconciliation only.

**This file remains the canonical detailed current-state document.** A
compact companion, `docs/LSSP_NEW_CHAT_HANDOFF_20260903.md`, was added in
Query 3 specifically for bootstrapping a fresh chat quickly — read that
one first, and come back here only for the full detail/audit trail.

## Query 3 re-verification pass (2026-09-03, later same day, ~16:10 EDT)

A second Query-3-scoped pass re-checked every claim below against live
state rather than assuming the prior pass's record was still accurate.
Findings: **no drift** — all branch SHAs, remote pushes, manuscript
integration, and declarations text matched exactly what §0 already
recorded. Two things worth noting for the next session:

- **RQ6 task 108** is still `RUNNING` on node n0001, now at **2:29:35**
  elapsed of the 4:00:00 limit (up from ~2:22 at the end of the first
  Query-3 pass) — still healthy, still an outlier vs. the other 118
  tasks' 2–30 min typical runtimes, still not actionable. Task 19 retry
  remains the single carried-over item; see §9/§15 and the handoff doc §10
  for the exact resume command. Not blocked on in this pass either, per
  instruction not to wait indefinitely.
- **New out-of-band human edit found**: the *historical* (non-canonical)
  `manuscript/lssp-jsc-polish-20260902` branch has a commit on `origin`
  not present in its local worktree checkout — `21790cc`, "Add funding,
  acknowledgements, and generative-AI disclosures", authored directly by
  the user (`sv96@njit.edu`, 2026-09-03 13:25:38 -0400), i.e. pushed
  outside of any agent session. Diffed against the canonical manuscript's
  `declarations.tex` (`9f2c1ef`): **not byte-identical** — `21790cc` still
  contains the unresolved `[AUTHOR TO CONFIRM before submission.]`
  bracket on Competing Interests and uses slightly different paragraph
  wrapping/heading text ("Generative AI use." vs. canonical's "Generative
  AI statement."), whereas the canonical branch already resolved Competing
  Interests to a plain declaration. Per instructions, this was **left
  untouched** (not merged, not discarded, remote not force-pushed) — flagged
  here only. `SAFE_TO_DISCARD_REDUNDANT_DIFF` does **not** apply to this
  branch/commit; it is human-authored content on a non-canonical branch
  and should be triaged by the user, not silently reconciled by an agent.
- Manuscript rebuild reverified independently (`tectonic main.tex`): clean,
  zero errors, same pre-existing underfull-hbox warnings as before. The
  resulting `main.pdf` rebuild diff (binary, PDF producer metadata only)
  was reverted with `git checkout -- paper/main.pdf` to avoid an
  unnecessary commit — no content changed.
- Out-of-scope dirty worktrees (`lssp-dataset-release-prefreeze`, base
  `robustness-benchmark` checkout, `robustness-stage0-repair`) reconfirmed
  unchanged and untouched.

No commits were needed on any research/manuscript branch this pass — all
Query-3 deliverables were already complete and pushed. This addendum and a
small refresh to the handoff doc's task-108 watch numbers are the only
edits made in this pass, committed on the docs branch.

## Query 3 changes (2026-09-03, final integration pass)

- **Manuscript integration committed**: `manuscript/lssp-jsc-reviewer-informed-polish-20260903`
  @ `9f2c1efb99998f79bb8928a35ceecb785458167e` (pushed, remote-verified).
  Added a new "Cross-Metric Ranking Portability" results subsection
  (headline: 990 conditions, median Kendall τ_b=0.419, 20% negative-τ
  conditions, median top-1 agreement=0; 54,450 pairwise comparisons, 3,207
  (5.9%) FDR-supported disagreements). Corrected the SLO-sensitivity
  results/limitations/methodology text from "remains unavailable" to the
  completed full-scale finding (108 reversal checks: 88 persist, 6
  direction-change, 10 become unsupported, 4 disappear; 13/30
  ranking-robustness conditions show top-1 disagreement). Added a new
  "Synthetic-to-Real Ranking Transfer (Pilot, Not Headline Evidence)"
  subsection, explicit that the transfer statistic is undefined in 21/24
  pilot conditions by design and no transfer conclusion is drawn. Updated
  `real_system.tex` to clarify the 120-task Slurm array is a real-hardware
  **calibration prerequisite** (118/120 done), not the RQ6 validation
  result itself — the "Result Placeholder" is correctly left pending.
  Manuscript rebuilds cleanly (tectonic; zero undefined references, only
  pre-existing underfull-hbox warnings).
- **RQ3 decision**: `DEFER_TO_FUTURE_WORK` for the full 440-cell extension.
  Rationale: RQ3 is preregistered SECONDARY, never a headline result
  contract item; its own pilot-gate documentation stamps the pilot
  `RQ3_PIPELINE_PILOT_NOT_HEADLINE_SCIENTIFIC_EVIDENCE`; the manuscript
  never currently claims full RQ3 evidence (only poses the question); and
  launching a new 440-cell campaign would be starting a new experiment,
  out of scope for a reconciliation/handoff query. Integrated the pilot
  only with explicit "pilot, not headline evidence" labeling.
- **RQ6 task 19 retry**: still deferred. Task 108 remained `RUNNING` for
  Query 3's entire duration too (last checked ~2h22m of 4h limit — an
  outlier relative to the other 118 tasks' 2–30 min typical runtimes,
  worth watching but not yet actionable). **This is the one substantive
  action item carried into the next session** — see
  `docs/LSSP_NEW_CHAT_HANDOFF_20260903.md` §10 for the exact resume
  command.
- **Cross-metric and SLO verified read-only** (no rerun): cross-metric
  990/990 status OK, 54,450 disagreement records, log clean, input hash
  matches; SLO 19,800/19,800 raw cells, 30 ranking-robustness + 108
  reversal-persistence records read and classified exactly (no records
  inferred).
- **Hygiene**: redundant declarations.tex diff in the old
  `lssp-manuscript-jsc` worktree is **not byte-identical** to the
  canonical branch (the canonical branch has since also resolved
  Competing Interests, which the old diff never touched) — left
  untouched, not discarded. The three out-of-scope dirty worktrees flagged
  in Query 2 (`lssp-dataset-release-prefreeze`, base `robustness-benchmark`
  checkout, `robustness-stage0-repair`) remain untouched and unchanged.

## 0. Query 2 changes (2026-09-03, after this document's initial version)

- **RQ3 preserved**: the entire pilot implementation (protocol doc, config,
  `src/robustbench/rq3/`, scripts, tests, and the two committed manifests)
  is now committed at `research/lssp-rq3-synthetic-to-real-prefreeze-20260903`
  @ `4b9dfe0585062f7d6788502e48d56d3c50579acb` (pushed, remote-verified).
  34/34 RQ3 tests pass. Raw per-cell pilot outputs remain outside git per
  existing `artifacts/*` policy (location/hashes recorded in the protocol
  doc and in the pilot's own `rq3_status.json`). The prior loss risk is
  resolved.
- **SLO full-scale analysis executed**: fixed a call-site argument bug in
  `scripts/analysis/analyze_slo_sensitivity.py` (`reversal_persistence()`
  was calling the sealed `classify_pairwise_reversal()` with mismatched
  arguments — never triggered by the sparse pilot data, only by the full
  19,800-row set). Fix is call-site-only; nothing under
  `src/robustbench/ranking_portability/analysis/` was touched, and no
  statistical test/definition/threshold/campaign parameter changed.
  Committed at `research/lssp-slo-sensitivity-extension-20260903` @
  `7cddca5cd3949acdb35ac2fc62fdda2935c07603` (pushed, remote-verified).
  Full-scale result: 19,800 input rows, 30 ranking-robustness records, 108
  reversal-persistence records (88 persisting, 4 disappearing). Raw output
  stays local per policy; this commit is the provenance record.
- **Manuscript reconciled**: `manuscript/lssp-jsc-reviewer-informed-polish-20260903`
  is now the canonical forward manuscript branch (per explicit Query-2
  instruction — the older `manuscript/lssp-jsc-polish-20260902` is retained,
  untouched, as a historical alias/base, not deleted). The previously
  uncommitted Funding/Acknowledgements/Generative-AI-disclosure text is
  now committed there, and the Competing-Interests placeholder is resolved
  to a plain "no competing interests" declaration. Committed at
  `6ac78d311218d4211537e0d6fef402678d4de58b` (pushed, remote-verified);
  manuscript rebuilds cleanly via `tectonic` (only pre-existing
  underfull-hbox warnings, no errors). The duplicate uncommitted diff still
  sitting in `lssp-manuscript-jsc` (the older worktree) is now redundant —
  its content is safely preserved on the canonical branch — but was left
  untouched rather than discarded without explicit instruction.
- **`lssp-authoritative` worktree registration removed** (branch and all
  history fully retained, both locally and on remote — only the local
  worktree checkout directory was removed via `git worktree remove`, since
  it was clean and fully represented in git). Docs in that branch remain
  historical/pre-Phase-12 as noted below.
- **RQ6 task 19 retry deferred**: task 108 remained `RUNNING` (healthy, node
  n0001) for this query's entire duration (~2h05m of a 4h limit when last
  checked) — retrying task 19 on the same node while 108 is active was
  judged unnecessary contention risk, so per Query-1's own recommendation
  ("retry once task 108 finishes") the retry was deferred rather than
  forced. This is the one carried-over action for the next checkpoint
  (Query 3 or a dedicated follow-up) — see updated §9/§15.
- **Hygiene note**: three additional dirty worktrees were found during the
  Query-2 audit that are **outside this query's authorized scope**
  (`lssp-dataset-release-prefreeze`, the base `robustness-benchmark`
  checkout on `research/bootstrap-cross-workload-benchmark-20260831`, and
  `robustness-stage0-repair`) — each has untracked/modified files belonging
  to separate in-flight research threads not named in Query 1 or Query 2's
  brief. None were touched. Flagged for awareness only.

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
| MANUSCRIPT | `manuscript/lssp-jsc-reviewer-informed-polish-20260903` (canonical, resolved Query 2 — see §11) | `6ac78d3` | `lssp-jsc-reviewer-polish` |
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
state — treat as historical, not current.

> **RESOLVED IN QUERY 2**: the local worktree *registration* was removed
> (`git worktree remove`) since it was clean and fully represented in git.
> The branch `research/lssp-authoritative-pre-phase12-20260901` @ `ec12af8`
> and all its history are fully retained, locally and on the remote — only
> the checkout directory is gone. No filesystem rename was performed
> (worktree removal was judged sufficient to remove the naming hazard
> without doing both). If a fresh checkout of this branch is needed later,
> re-add it with `git worktree add`.

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

> **RESOLVED IN QUERY 2**: all of the above is now committed at
> `4b9dfe0585062f7d6788502e48d56d3c50579acb` (pushed, remote-verified),
> after running the 34-test suite (all passing) and a secret/size scan.
> FULL_EXTENSION remains NOT STARTED — that has not changed and was not
> attempted in Query 2. See §0.
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

`RQ6_TASK108_STATE` = RUNNING, healthy, node n0001, throughout Query 2
(last checked 2:06:19 elapsed / 4:00:00 limit). Untouched throughout.

`[VERIFIED_FACT]` **Location risk**: RQ6's actual execution artifacts
(sbatch logs, per-task JSON outputs, and one modified file
`scripts/ranking_portability/build_phase11_calibration.py`) live only in a
Wulver-side git worktree at
`/mmfs1/project/ikoutis/sv96/github/llm-serving-scheduler-lssp-rq6-calibration-20260903`
(HEAD `773982a`, same commit as the local `lssp-rq6-scientific-prefreeze`
worktree) — this location is **not mirrored** in the local
`/home/soroush/repos/` worktree set. **Inspected in Query 2**: the diff on
`build_phase11_calibration.py` is a file-permission-mode change only
(`100755` → `100644`), zero content difference — harmless, unrelated to
the task-19 port-collision bug, left as-is.

`[PENDING → still pending]` **RQ6 task 19 retry was deferred in Query 2.**
Task 108 remained `RUNNING` on node n0001 for this query's entire duration;
retrying task 19 (SAFE_ENGINEERING_RETRY per the root-cause analysis above)
was deliberately not forced alongside it, per Query 1's own recommendation
to wait for 108 to finish first and avoid adding scheduling contention on
the same node. **This is the single carried-over action item** — no launcher
change is needed (task 119 already completed and released port 8119); the
next session should check `squeue -j 1220661_108`, and once it is no longer
running, resubmit array index 19 alone with the existing, unmodified
`scripts/real_vllm/run_rq6_calibration.sbatch` (e.g.
`sbatch --array=19 scripts/real_vllm/run_rq6_calibration.sbatch`), then
verify `ExitCode 0:0` and that its output JSON validates like the other 118
completed tasks before treating all 120 RQ6 tasks as valid.

## 10. SLO state

See §4/§6. Raw generation: **COMPLETE** (19,800/19,800, 0 failures).

> **RESOLVED IN QUERY 2**: full-scale statistical analysis now run (fixed a
> call-site bug first — see §0). Branch `research/lssp-slo-sensitivity-extension-20260903`
> now at `7cddca5cd3949acdb35ac2fc62fdda2935c07603` (pushed,
> remote-verified). Result: 19,800 input rows, 30 ranking-robustness
> records, 108 reversal-persistence records (88 persisting, 4
> disappearing). Raw output stays local per `artifacts/*` policy.

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

> **RESOLVED IN QUERY 2**: `manuscript/lssp-jsc-reviewer-informed-polish-20260903`
> is designated canonical/forward (explicit Query-2 instruction). The older
> `manuscript/lssp-jsc-polish-20260902` is retained, untouched, as a
> historical alias/base — not deleted. See §0.

`[VERIFIED_FACT]` **Uncommitted declarations update, wrong worktree**: the
funding / acknowledgements / generative-AI-disclosure text described in the
task brief exists **only as an uncommitted `git diff`** in
`lssp-manuscript-jsc` (`paper/sections/declarations.tex`, +18/-3 lines) —
it is not committed to either manuscript branch, and it is **absent** from
the `lssp-jsc-reviewer-polish` worktree's committed content (which still
shows the placeholder "no funds... `[AUTHOR TO CONFIRM]`" and no
Acknowledgements/Generative-AI-statement paragraphs at all). If
`lssp-manuscript-jsc` were reset or the worktree removed, this text would be
lost. **RESOLVED IN QUERY 2** — see §0: this text is now committed to the
canonical branch at `6ac78d3`, and the Competing Interests placeholder is
resolved. The below reflects state as observed in Query 1 (kept for the
audit trail).

- `FUNDING` = now committed on canonical branch — CloudRift AI Builder
  Grant, Cohere Labs Catalyst Grant Program, AMD AI Developer Program /
  Fireworks AI credits.
- `ACKNOWLEDGEMENTS` = now committed on canonical branch — Professor
  Ioannis Koutis.
- `GENERATIVE_AI_USE` = now committed on canonical branch — ChatGPT, Codex,
  Claude, Gemini, Cursor, Perplexity AI.
- `COMPETING_INTERESTS_PLACEHOLDER_REMAINS` = **NO (resolved in Query 2)**
  — now reads "The author declares no competing interests." on the
  canonical branch. (Still present, unresolved, on the older
  `lssp-manuscript-jsc` worktree/branch, which was intentionally left
  untouched.)

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

Items 1, 2, 3, 5, and 6 below were completed in Query 2 (see §0). The one
carried-over item is:

1. **Retry RQ6 task 19 only**, once task 108 finishes — `squeue -j
   1220661_108`, and when it's no longer running,
   `sbatch --array=19 scripts/real_vllm/run_rq6_calibration.sbatch` (unmodified
   launcher; task 119 already released port 8119, so no launcher change is
   needed). Verify `ExitCode 0:0` and schema-valid output before treating
   all 120 RQ6 tasks as valid for downstream use.

Completed in Query 2 (kept here for the audit trail):
2. ~~Commit the untracked RQ3 pilot work~~ → `4b9dfe0` (pushed).
3. ~~Commit or discard the uncommitted `declarations.tex` edit~~ → committed
   on canonical branch at `6ac78d3` (pushed); Competing Interests resolved.
4. ~~Inspect the uncommitted diff in the Wulver-side RQ6 worktree~~ →
   confirmed permission-mode-only, harmless, left as-is.
5. ~~Run the full-scale SLO-sensitivity analysis~~ → `7cddca5` (pushed);
   108 reversal-persistence records (88 persisting, 4 disappearing).
6. ~~Decide manuscript-branch consolidation and resolve the misleadingly-named
   `lssp-authoritative` worktree~~ → reviewer-informed-polish branch
   designated canonical; stale worktree registration removed (branch/history
   retained).

Remaining scientific/manuscript integration work for Query 3 (not started,
not scientific redesign — see §13):
- Integrate cross-metric, RQ3 (pilot), SLO-sensitivity (now full-scale), and
  RQ6 (once task 19 is recovered) results into the manuscript body — all
  four are currently `NOT_INTEGRATED` / `PENDING_RESULT` / stale-text (§11).
- Decide/launch (or explicitly defer, with rationale) the RQ3 full
  (440-cell) extension referenced in the RQ3 protocol doc §7 — pilot-only
  today.
- Update `results.tex`'s SLO-sensitivity paragraph, which still says the
  result "remains unavailable" — now false at the raw-data and analysis
  level.
