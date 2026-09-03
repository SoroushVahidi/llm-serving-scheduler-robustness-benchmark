# LSSP New-Chat Handoff — 2026-09-03

Compact handoff for starting a fresh chat on this project. For full detail,
audit trail, and per-item `[VERIFIED_FACT]`/`[INFERENCE]`/`[PENDING]` tags,
see `docs/LSSP_AUTHORITATIVE_STATE_20260903.md` (same branch, same repo) —
this document is deliberately shorter and summarizes only what a new
session needs to act correctly from the first message.

## 1. Project

- **Title/topic**: LLM-serving scheduler robustness and ranking-portability
  benchmark ("LSSP" = LLM Serving Scheduler Portability).
- **Scientific objective**: characterize how portable a scheduling-policy
  ranking is across workload sources, load regions, metrics, SLO
  definitions, and (partially) synthetic-vs-real workloads and
  simulator-vs-real hardware.
- **Target venue**: Journal of Supercomputing (JSC).
- **Repo**: `SoroushVahidi/llm-serving-scheduler-robustness-benchmark`
  (GitHub), checked out locally as ~30 git worktrees under
  `/home/soroush/repos/llm-serving-scheduler-*`.

## 2. Authoritative branches / SHAs

| Role | Branch | SHA |
|---|---|---|
| Phase-12 sealed base | `research/lssp-phase12-analysis-prefreeze-20260902` | `bd641d4902431b821cd7eb4ce9ad236955cec45d` |
| Cross-metric extension | `research/lssp-cross-metric-analysis-extension-20260903` | `b009e9dfc19b49775332777a17f233652bc2e599` |
| RQ3 (pilot preserved) | `research/lssp-rq3-synthetic-to-real-prefreeze-20260903` | `4b9dfe0585062f7d6788502e48d56d3c50579acb` |
| RQ6 | `research/lssp-rq6-real-vllm-scientific-prefreeze-20260902` | `773982a280be7a2e6dc812174f6c90c8ca0dc18b` |
| SLO-sensitivity | `research/lssp-slo-sensitivity-extension-20260903` | `7cddca5cd3949acdb35ac2fc62fdda2935c07603` |
| **Manuscript (canonical)** | `manuscript/lssp-jsc-reviewer-informed-polish-20260903` | `9f2c1efb99998f79bb8928a35ceecb785458167e` |
| Manuscript (historical alias, do not use) | `manuscript/lssp-jsc-polish-20260902` | `a37e7060e6d99a737d177c173e554ca4687eac95` (retained, not deleted) |
| Artifact/repro | `research/lssp-artifact-repro-prefreeze-20260902` | `8a624e4606ffa4b9f7d545b6cbe193c4191c7e82` |
| Release prep | `release/lssp-jsc-artifact-prep-20260902` | `f46bfb52041cdec00a6379c342b5f02bc945599a` |
| Docs/handoff (this doc) | `docs/lssp-authoritative-state-reconciliation-20260903` | see `git log` — this file is updated in place |

All branches above are pushed and remote-SHA-verified as of this handoff.

## 3. Completed science

- **Phase-12** (sealed, unchanged all session): six canonical result
  artifacts from the 18,720-cell consolidated matrix. Not touched.
- **Cross-metric extension**: COMPLETE. 990/990 correlation conditions
  status OK, 54,450 pairwise disagreement records. Integrated into the
  manuscript (`results.tex` §Cross-Metric Ranking Portability).
- **SLO-sensitivity**: COMPLETE (raw + full analysis). 19,800/19,800 raw
  cells, 30 ranking-robustness + 108 reversal-persistence records.
  Integrated into the manuscript.
- **RQ3**: PILOT COMPLETE only (176/176 cells, 24/24 analysis records).
  Full 440-cell extension explicitly **deferred to future work** (RQ3 is
  preregistered SECONDARY, not a headline RQ). Pilot integrated into the
  manuscript with explicit "not headline evidence" labeling.
- **RQ6**: calibration campaign 118/120 complete (1 running, 1 failed —
  see §5). The calibration is a *prerequisite*, not the RQ6 result itself;
  the actual ranking-agreement validation has not started (also blocked on
  a separate SLAI/RAD engineering prerequisite). Manuscript's Result
  Placeholder correctly left pending — do not fill it in until both
  prerequisites clear and the validation runs actually execute.

## 4. Key verified results (headline, manuscript-relevant only)

- **Cross-metric**: median Kendall τ_b = 0.419 across 990 conditions
  (range −0.506 to 1.000); 20% of conditions have negative τ_b; median
  top-1 policy agreement between metrics = 0. At the pairwise-comparison
  level (54,450 total), 3,207 (5.9%) are FDR-supported practical
  disagreements between metrics.
- **SLO-sensitivity**: median ranking-robustness Kendall τ_b = 0.872
  (range 0.533–1.000) across 30 conditions, but top-1 policy changes in
  13/30 (43%). Of 108 preregistered-reversal recheck conditions: 88 (81%)
  persist, 6 (6%) change direction, 10 (9%) become unsupported, 4 (4%)
  disappear.
- **RQ3 pilot**: 176/176 cells, 24/24 analysis records, but the transfer
  statistic (Kendall τ_b) is undefined in 21/24 (88%) conditions by design
  (only 2 synthesis seeds/family) — **no transfer conclusion drawn**.
- **RQ6**: no scientific result yet (see §3).

## 5. Pending items (exact, unresolved)

1. **RQ6 task 19 retry** — the only substantive open action. Task 108 was
   still `RUNNING` on node n0001 throughout Queries 2 and 3, and through a
   Query-3 re-verification pass later the same day (last checked **2:29:35
   elapsed of the 4:00:00 limit**, ~16:10 EDT 2026-09-03 — an outlier vs.
   the other 118 tasks' 2–30 min typical runtimes; watch it, don't assume
   it's stuck). Once it finishes:
   see §10 for the exact resume command. Root cause of task 19's failure
   (port collision with task 119, both computing `PORT=8100+idx%100=8119`)
   is fully diagnosed and requires no launcher change — task 119 already
   completed and released the port.
2. Once task 19 succeeds and task 108 is valid: verify all 120 outputs
   are schema-valid before treating RQ6 calibration as fully done — then
   the *actual* ranking-agreement validation runs (still blocked on the
   SLAI/RAD `--scheduler-cls` plugin, `real_system.tex` §Frozen Case
   Selection) can be scoped as a follow-up, not assumed automatic.
3. RQ3 full 440-cell extension — explicitly deferred, not scheduled.
4. Per-source `discriminability` (fraction of non-tied conditions) — an
   open item from the original Phase-12 result contract, never populated,
   noted in `results.tex` intro. Not touched this session.
5. `METRIC_DEFINITION_SENSITIVITY` robustness family — disclosed
   implementation gap (no comparison function was ever written), noted in
   `results.tex` §Robustness. Not touched this session.

## 6. Manuscript status

- **Canonical branch/SHA**: `manuscript/lssp-jsc-reviewer-informed-polish-20260903`
  @ `9f2c1efb99998f79bb8928a35ceecb785458167e`.
- **Build**: clean (`tectonic main.tex` from `paper/`), zero undefined
  references/citations, only pre-existing underfull-hbox warnings.
  `paper/main.pdf` is committed and current.
- **Integrated**: cross-metric (new subsection), SLO-sensitivity (results +
  limitations + methodology updated), RQ3 pilot (new subsection, labeled
  non-headline). RQ6 explicitly NOT integrated (correctly still pending).
- **Declarations**: Funding, Acknowledgements, Generative AI statement, and
  Competing Interests (resolved to a plain "no competing interests") are
  all present and correct on the canonical branch.
- **Remaining placeholders**: only the RQ6 `[PENDING RESULT: ...]` in
  `real_system.tex` — genuinely accurate, not stale, leave until RQ6
  validation actually runs.
- **Do not use** `manuscript/lssp-jsc-polish-20260902` — it is the
  pre-integration historical branch, retained but superseded.

## 7. Artifact / repro status

`research/lssp-artifact-repro-prefreeze-20260902` and
`release/lssp-jsc-artifact-prep-20260902` worktrees are clean; not deeply
re-audited this session (out of scope — see
`docs/LSSP_AUTHORITATIVE_STATE_20260903.md` §12 for the one prior note on
this).

## 8. Important provenance / hashes

- Phase-12 seal: `bd641d4` (preceded by `eb574a8`).
- Cross-metric contract hash: `33729102c2f8867cb521f8557cd51b42d8830811de8dea16cc7ab68d53b61fd9`;
  input hash `09db0f1d285f830e054dfd5f3876eff94caa08ea1ca982828d5e228d1b3350b9`.
- SLO campaign manifest hash: `424b332ff860870ae062db3360c18170476c19b462eb895dff69cd0d88b22c6d`;
  full results.json sha256 `b67d4721fecbf6e36e6cfae08c6dafb727d7b7e68867f771cb607b7320f3ea9b`.
- RQ3 pilot campaign manifest hash: `8591a009be8c5ef8af7c8654abe06737abbea07a6a49ed9ff39d97060fbce3b6`.
- RQ6 Slurm array: job `1220661`, 120 tasks (0–119), submitted from
  `/mmfs1/project/ikoutis/sv96/github/llm-serving-scheduler-lssp-rq6-calibration-20260903`
  on Wulver (HEAD `773982a`, not mirrored in local `/home/soroush/repos/`).

## 9. Known caveats

- **RQ3 pilot vs full extension**: the pilot is engineering validation
  only (its own contract stamps it
  `RQ3_PIPELINE_PILOT_NOT_HEADLINE_SCIENTIFIC_EVIDENCE`); do not cite its
  176/176 completion as evidence for or against RQ3 itself.
- **RQ6 calibration vs validation**: the 120-task Slurm array calibrates
  real-hardware load factors (λ_ref per window) — it is not the
  scheduling-ranking-agreement experiment. Even at 120/120, RQ6 has no
  result until the separate validation runs execute (further blocked on
  the SLAI/RAD plugin).
- **Simulator vs real-system scope**: this manuscript never claims
  absolute latency/throughput transfer between simulation and real
  hardware — only relative-ranking/reversal-direction agreement on a
  small, frozen case set. Preserve this framing in any future edits.
- **Deterministic reps vs statistical replication**: Phase-12's simulator
  runs are deterministic (rep0/rep1 verification, not stochastic
  repetition); the cross-metric and SLO-sensitivity extensions use genuine
  bootstrap resampling (2,000 resamples) for statistical inference — don't
  conflate the two when writing about either.
- **BurstGPT provenance**: `related_work.tex` carries a provider-
  independence note for BurstGPT relative to the other two sources — not
  touched this session, still valid as written.

## 10. Next actions (ordered, minimal, concrete)

1. Check RQ6 task 108:
   ```
   ssh wulver 'squeue -j 1220661_108 -o "%.18i %.10T %.12M %.12l %R"'
   ```
   Once it is no longer listed as `RUNNING`, retry task 19 with the
   **unmodified** existing launcher (no code change needed — task 119
   already released the colliding port):
   ```
   ssh wulver
   cd /mmfs1/project/ikoutis/sv96/github/llm-serving-scheduler-lssp-rq6-calibration-20260903
   sbatch --array=19 scripts/real_vllm/run_rq6_calibration.sbatch
   ```
   Then verify: `sacct -j 1220661_19 --format=JobID,State,ExitCode -X`
   should show `ExitCode 0:0`, and confirm the output JSON for window
   index 19 validates against the same schema as the other 118.
2. Once all 120 calibrations are valid, scope (don't assume) the actual
   RQ6 ranking-agreement validation runs — still gated on the SLAI/RAD
   `--scheduler-cls` plugin (`real_system.tex` §Frozen Case Selection).
3. Decide whether the RQ3 440-cell full extension is worth running before
   submission, or stays deferred to future work (current manuscript text
   already supports "deferred" without contradiction).
4. Do a full-manuscript read-through for submission readiness (this
   session focused edits on the 4 extension-integration points listed in
   §6; a cover-to-cover pass wasn't performed).
5. Consider a JSC-specific formatting/length pass once content is final.

## 11. Do not do

- Do not rerun Phase-12 or modify any of its six sealed canonical
  artifacts.
- Do not duplicate/rerun the cross-metric, SLO-sensitivity, or RQ3-pilot
  campaigns — they are complete and their outputs are frozen at the hashes
  in §8.
- Do not treat the `lssp-authoritative` worktree/branch
  (`research/lssp-authoritative-pre-phase12-20260901`, `ec12af8`) as
  current — it predates the Phase-12 seal. (Its local worktree checkout
  was removed for hygiene in Query 2; the branch and history are intact if
  ever needed.)
- Do not use `manuscript/lssp-jsc-polish-20260902` as the manuscript
  branch — use `manuscript/lssp-jsc-reviewer-informed-polish-20260903`.
- Do not expose secrets — none were found in any session-touched content,
  but keep scanning new commits.
- Do not promote the RQ3 pilot, or any single cross-metric/SLO condition,
  to a headline claim beyond what's stated in the manuscript's own new
  text (§4's numbers are the ceiling of what's currently claimable).

## 12. Resume commands

```bash
# Canonical worktree paths (all under /home/soroush/repos/)
llm-serving-scheduler-lssp-rq3-synthetic-to-real            # RQ3
llm-serving-scheduler-lssp-cross-metric-analysis-extension  # cross-metric
llm-serving-scheduler-lssp-slo-sensitivity-extension        # SLO
llm-serving-scheduler-lssp-jsc-reviewer-polish              # manuscript (canonical)
llm-serving-scheduler-lssp-rq6-scientific-prefreeze         # RQ6 (local mirror; real
                                                             # execution artifacts are
                                                             # on Wulver, see §8)
llm-serving-scheduler-docs-reconciliation                   # this doc + the detailed one

# Check out / verify any branch
git -C <worktree-path> branch --show-current
git -C <worktree-path> rev-parse HEAD
git -C <worktree-path> status --short

# RQ6 job status (read-only)
ssh wulver 'squeue -j 1220661 -o "%.18i %.10T %.12M %.12l %R"; sacct -j 1220661 --format=JobID,State,Elapsed,ExitCode -X'

# Rebuild the manuscript
cd /home/soroush/repos/llm-serving-scheduler-lssp-jsc-reviewer-polish/paper && tectonic main.tex
```
