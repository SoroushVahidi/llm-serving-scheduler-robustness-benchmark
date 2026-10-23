# M3 project handoff

## Project overview

**PAUSED — submission candidate prepared. Status snapshot: 2026-10-23.**

*Scheduler Equivalence and Performance Trade-offs under a Common LLM-Serving Contract* studies which scheduler distinctions affect execution and performance under CM-0.1. The intended journal is ACM Transactions on Modeling and Performance Evaluation of Computing Systems (TOMPECS). The completed work connects conditional behavioral equivalence, mechanism inactivity, and bounded latency/throughput trade-offs. The manuscript, frozen evidence, source, and reproducibility procedures are preserved; focused revisions and final scientific/document checks are complete.

The manuscript has **not been submitted**. The project is paused by the author. No merge, journal submission, public reviewer-archive release, or further experiment is authorized. This handoff records a candidate, not certified journal compliance or acceptance.

## GitHub state

- [Repository](https://github.com/SoroushVahidi/llm-serving-scheduler-robustness-benchmark).
- [Draft PR #27](https://github.com/SoroushVahidi/llm-serving-scheduler-robustness-benchmark/pull/27): prerequisite ACM metadata, acknowledgment, and AI-disclosure corrections; head `manuscript/lssp-m3-acm-compliance-20261023`, verified commit `8bdf692f0432304002c64b23b7afef6ee3bc3617`. It remains open and unmerged, itself based on `manuscript/lssp-m3-novelty-positioning-20261023` at `dab2b4302ce72cf5bdd35d952208481e910101f7` (PR #26).
- [Draft PR #28](https://github.com/SoroushVahidi/llm-serving-scheduler-robustness-benchmark/pull/28): latest revised manuscript, focused submission preparation, and this permanent handoff; head `manuscript/m3-submission-preparation-20261023`. **PR #28 is currently stacked on PR #27**, targeting `manuscript/lssp-m3-acm-compliance-20261023`.
- Verified manuscript-preparation commit: `4624cc71add7c152544be1639a7e0573afb141d4`; Stage 1/2 candidate commit: `696556f8ec7e95299239c2038e6608984d315c20`. Stage 3 adds documentation only on top of that candidate; obtain its containing commit from this file's Git history or PR #28 head rather than treating the candidate SHA as the final branch head.
- Remote `main` at this snapshot is `d6c53851f7c27a0dc178bbdf208da29500186199`; its older PDF is not the revised candidate.

Both PRs remain drafts because the author has paused the project and has not authorized integration. If integration is later authorized, first inspect the earlier prerequisite stack and integrate its dependencies in order, including PR #27 before PR #28. After PR #27 merges, reassess where its changes landed, the new base and merge-base, and PR #28's complete diff. Retarget to current `main` only when the prerequisites are actually present there and the resulting comparison is correct. Do not blindly retarget, merge the stack, or replace only the PDF on main. No history rewrite is needed for the present state.

## Manuscript state

The authoritative review PDF is [m3-manuscript.pdf](m3-manuscript.pdf), repository path `paper/tompecs-m3/m3-manuscript.pdf`: **26 pages, 728,953 bytes**, SHA-256:

```text
43af9fb9e3b77e4dac7f602e0a768d1e00554699bcc44287d33328e5e23da592
```

Its version-controlled source is [main.tex](main.tex), [sections/](sections/), [references.bib](references.bib), and the bundled [template/](template/), figures, and tables. The [immutable Stage 2 PDF](https://github.com/SoroushVahidi/llm-serving-scheduler-robustness-benchmark/blob/696556f8ec7e95299239c2038e6608984d315c20/paper/tompecs-m3/m3-manuscript.pdf) identifies the same bytes. The superseded 26-page baseline has SHA-256 `cfbf6bce69feec09b6a1927c86e3a6b84b5e4561847466e9297844c7954d1eb2`. Its matching source was established and rebuilt before revision; do not regenerate the candidate from older main-branch source.

Only `m3-manuscript.pdf` is tracked as the final M3 manuscript in this revision. PDFs under `figures/` are scientific figures. The optional `acmsmall` output and temporary build products are ignored; historical PDFs remain in Git history and preserved evidence, not as competing current manuscripts.

### Build and verification

Use a disposable checkout or private package extraction when regenerating outputs. From its repository root, use Python 3 with the [recorded display dependencies](artifact-release/requirements-display.txt), TeX Live with `pdflatex`/`bibtex`, and Poppler. The recorded environment used Python 3.12.3 and TeX Live 2023/Debian; restoring an environment months later requires checking those dependencies. No live temporary environment is promised to persist.

```bash
python paper/tompecs-m3/scripts/render.py
python paper/tompecs-m3/editorial-revision/reduced_comparisons.py
bash paper/tompecs-m3/scripts/build.sh manuscript
bash paper/tompecs-m3/scripts/build.sh acmsmall
python paper/tompecs-m3/scripts/validate.py --standalone
sha256sum paper/tompecs-m3/m3-manuscript.pdf
sha256sum paper/tompecs-m3/build/manuscript/m3-manuscript.pdf
cmp paper/tompecs-m3/m3-manuscript.pdf paper/tompecs-m3/build/manuscript/m3-manuscript.pdf
```

The build script fixes its timestamp and converges references. The saved-evidence validator expects both layouts, writes its validation report, and checks the independent C01 oracle, narrative anchors, STAT01 rows, bibliography, and build diagnostics. `--standalone` deliberately omits historical-checkout preservation checks and uses saved worked-example support; it does not claim fresh full event replay. The private review package's tested `run_review_checks.py --output EXTERNAL_RESULTS` additionally orchestrates the budget, urgency, abstract, and fresh worked-example checks. Consult its reviewer guide for exact package-relative arguments. These workflows regenerate documents from saved evidence; do not run preserved campaign or SLURM launch scripts.

Stage 1 reproduced the candidate PDF byte-for-byte from an actual archive extraction. Stage 3 changes only this handoff and its README entry; the source, PDF, scientific evidence, and package stay unchanged. See the [focused changelog](submission-preparation/CHANGELOG.txt), [preparation validation record](submission-preparation/validation.json), and [README](README.md). Older reports are dated provenance, not current authorization to release or submit.

## Completed scientific work

| Evidence | Verified finding and scope | Committed entry point |
| --- | --- | --- |
| C01-FULL | 5,760 evaluation cells; 1,440 chunked-FCFS/decode-first terminal equivalences. Journal ordering can differ while selected work, state transitions, and terminal performance agree under the proved conditions. | [All cells](supplement/c01-all-cells.csv), [contract](sections/contract.tex), [claim audit](CLAIM_TO_EVIDENCE.md) |
| Budget sensitivity | 72 cells in the selected BurstGPT stratum; observed pairwise equivalence, not a proof for arbitrary binding budgets. | [Report](budget-sensitivity/REPORT.md), [summary](budget-sensitivity/summary.json) |
| Urgency | 0 critical/urgent opportunities among 107,844 ready-decode opportunities; 42 omissions retained. The current urgency gate was inactive; admission ordering remained active. | [Urgency report](urgency-analysis/REPORT.md), [certificate analysis](urgency-analysis/STRUCTURAL_FINDINGS.md) |
| Source-mean rankings | No strict-practical reversals at the declared 10% margin: 0/2,376 original comparisons and 0/864 reduced comparisons. Window-level and metric-dependent reversals remain. | [Ranking definitions/results](sections/rankings.tex), [reduced comparisons](editorial-revision/reduced-comparisons.json) |
| SLO-gated trade-offs | Aggregate mean-latency reductions of 11.3–34.0% against chunked-FCFS, with finite-window token-throughput losses of 1.65–4.01%. Unfavorable BurstGPT mean-window-p95 increases of 3.72% and 18.97% are retained. Benefit is not evidence of urgency activation. | [Performance](sections/performance.tex), [source/capacity means](supplement/c01-source-capacity-means.csv) |
| STAT01 | 134,000 known-truth studies across 18 scenarios; 7,200 final method/endpoint rows. Original-eight and expanded-17 uncertainty families, post-diagnosis distinctions, abstentions, and precision/power limitations are retained. | [Inference](sections/inference.tex), [protocol](supplement/STAT01_PROTOCOL.md), [amendment](supplement/STAT01_AMENDMENT.md), [endpoint rows](supplement/stat01-all-endpoints.csv) |

STAT01 exposes calibration failures of historical procedures in specified scenarios; it does not supply population-significance claims for C01's selected trace corpus. Reproducing historical arithmetic, checking execution conformance, and establishing statistical calibration are distinct tasks.

Completed reproduction checks include all nine private-package document/saved-evidence commands, 16 byte-identical regenerated displays, 53 narrative checks, 28 resolved bibliography entries, all-page visual review, embedded fonts, and 77 valid internal PDF links. Full-record validation previously confirmed terminal identities and inventories; detailed independent referees sampled 24 journals and 200 studies rather than exhaustively replaying all decisions. Three optional bibliography metadata advisories, some inaccessible external reference URLs, and an untagged review PDF remain documented. No new OS/container or hardware validation is claimed.

## Remaining scientific limitations

1. **The exact reachable-state equivalence boundary has not been fully characterized.** The original proof uses common timestamps and a bound of at most eight residents, each offering at most 512 work tokens: 4,096 is below the 32,768-token budget. The 72-cell smaller-budget agreement does not establish equivalence for all reachable states or arbitrary binding budgets. Different-contract legacy examples are not CM-0.1 counterexamples.
2. **Same-contract composition-dependent batch timing has not been evaluated.** The recorded October 23 workstation/Wulver audit found no completed such M3 experiment. Fixed-duration batches limit transfer of latency, tail, and throughput findings; closure did not repeat that remote audit.
3. **Historical physical-serving experiments do not directly validate M3 rankings.** Their execution contracts and comparison objects differ. No physical GPU ranking or production-rate prediction is established here.
4. **The current urgency rule was inactive throughout evaluated M3 states.** The finite-work certificate and saved checks support this null result. SLO-gated's observed benefit cannot be attributed to an activated urgency mechanism.
5. **Restricted assumptions limit generalization.** Fixed 1 ms batches, four/eight residents, conservative full-context reservations, restricted online information, finite correlated selected windows, synthetic deadlines, and the documented inference assumptions bound the conclusions. No universal scheduler ranking, general optimality theorem, or population-level reversal claim follows.

These are acknowledged research boundaries, separate from submission administration. They do not automatically require new experiments before submission if the manuscript keeps its bounded claims. The decision on journal fit and sufficiency remains with the author; this pause does not initiate another research campaign.

## Submission blockers

- Final author review of the revised candidate remains outstanding.
- Current TOMPECS formatting, anonymity, page limits, supplement rules, and portal requirements need confirmation. Prior official guideline access returned HTTP 403; ACM template conformance alone does not certify journal-specific compliance.
- Required overlap/related-submission disclosures must be checked against actual submitted versions where necessary. Inspected candidate versions do not certify exact uploaded-file identities. The detailed disclosure stays private.
- Confidential reviewer-supplement delivery has not been established. The verified compact archive and separately preserved full evidence candidate remain private, with no hosted reviewer URL or new DOI. Original provider raw traces are excluded and component license scopes retained.
- Author declarations and applicable personal, rights, ORCID, and portal attestations remain to be completed or confirmed. Existing approved identity, funding, conflict, and AI-role statements are preserved.
- No journal submission has occurred. No public reviewer-archive release is authorized. Merge, submission, and public release require separate explicit author authorization.

Private cover letter, portal answers, confidential disclosure, validation logs, package locations and preservation details are recorded outside this repository in the author's private Stage 3 handoff. This public document deliberately provides no private access route or confidential manuscript-status details.

## Resumption checklist

1. Read this handoff and the author's private Stage 3 closure record; treat dates as snapshots.
2. Inspect PR #27 and PR #28, current head/base SHAs, local changes, and earlier dependencies. Preserve independent user work and reassess any changed integration relationship.
3. Restore or verify the documented environment in an isolated checkout/extraction. Do not assume temporary environments or original workstation paths still exist.
4. Verify the authoritative PDF hash, corresponding source and package identity. Use the saved-evidence build checks if the environment or source changed; do not launch experiments.
5. Confirm current journal-specific requirements from official sources and resolve any needed exact-version disclosure checks privately.
6. Complete final author review, including bounded claims, journal fit, declarations, and attestations.
7. Prepare authorized confidential reviewer-supplement access through an accepted channel; verify hashes and attachment limits. Do not invent a public link or publish the archive.
8. Decide whether to submit the bounded manuscript as prepared. New experiments are not an automatic prerequisite; any expanded scope requires a separate decision.
9. Submit only after explicit author authorization. Repository integration is a separate authorized decision and follows the dependency order above.

## Important links

- [PR #27 prerequisite](https://github.com/SoroushVahidi/llm-serving-scheduler-robustness-benchmark/pull/27) and [PR #28 latest candidate and handoff](https://github.com/SoroushVahidi/llm-serving-scheduler-robustness-benchmark/pull/28).
- [Manuscript](m3-manuscript.pdf), [source](main.tex), [README/build entry point](README.md), and [build script](scripts/build.sh).
- [Current preparation validation](submission-preparation/validation.json), [focused manuscript changelog](submission-preparation/CHANGELOG.txt), and [saved-evidence validator](scripts/validate.py).
- [Frozen input fingerprints](evidence/input-hashes.json), [supplementary tables and protocols](supplement/), [full-candidate verification procedure](artifact-release/verify_candidate.py), and [recorded display dependencies](artifact-release/requirements-display.txt).

Start here when returning. Preserve the candidate and its evidence; no further development is scheduled by this handoff.
