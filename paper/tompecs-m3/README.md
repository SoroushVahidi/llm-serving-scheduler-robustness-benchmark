# M3 author-review manuscript

**Current revision: scientific and editorial review (2026-10-23), stacked on PR #28.**
The current [29-page review PDF](m3-manuscript.pdf) integrates the fixed-policy,
empty-initial-state BOUND01 theorem and four verified related-work additions.
See [revision report](scientific-editorial-revision/REPORT.txt),
[proof review](scientific-editorial-revision/PROOF_REVIEW.txt),
[validation](scientific-editorial-revision/validation.json), and
[reference/journal checks](scientific-editorial-revision/REFERENCES_AND_REQUIREMENTS.txt).
TIME01 and ABL01 numerical findings are not integrated; their completion and
independent scientific review are separate gates. No new experiments were run.

The permanent [project handoff](PROJECT_HANDOFF.md) remains an unchanged paused
snapshot for PR #28 at `03efa8eabcf5304a514dfd002b70b05c042cde36`.
Its verified 26-page PDF (SHA-256 `43af9fb9e3b77e4dac7f602e0a768d1e00554699bcc44287d33328e5e23da592`)
and private reviewer package remain preserved. This branch supersedes that PDF
for editorial review only; it does not silently update the private package or
claim submission readiness. No merge, journal submission or data release occurs.

The entries below describe earlier revisions and historical validation records.

**Preceding revision: scientific contribution and novelty positioning (2026-10-23).** The three research questions now connect effective scheduling behavior, the mathematical explanation of inactivity, and comparison-level performance trade-offs. See the [revision report](novelty-positioning/REPORT.md), [contribution-to-evidence matrix](novelty-positioning/CONTRIBUTIONS.md), and [primary-literature comparison](novelty-positioning/PRIOR_WORK.md). This manuscript-only revision starts at actual PR #25 head `d73192df32fd14ec025eb8b9dab72da401eb65ae`; it adds no experiments.

**Preceding revision: structural urgency investigation (2026-10-23).** See the [urgency report](urgency-analysis/REPORT.md), [pre-experiment structural findings](urgency-analysis/STRUCTURAL_FINDINGS.md), and [decision not to run an invalid deadline-only experiment](urgency-analysis/EXPERIMENT_DECISION.md). The fixed gate agrees with its specification. A finite-work certificate rules out activation in the examined regimes; completion deadlines are metric-only. No new scientific experiments were run. This branch starts at actual PR #24 head `8a32ecf6e5e5dcca114594b320ac7c5210d8c543`.

**Preceding revision: prospective budget sensitivity (2026-10-22).** See the [sensitivity report](budget-sensitivity/REPORT.md), [prospective protocol](budget-sensitivity/PROTOCOL.md), and [numerical results](budget-sensitivity/summary.json). This branch is stacked on the actual PR #23 head `4c08660eeb528a5a459800bbc79771f4b8e4dbfc`. The 72-cell study preserves chunked/decode equivalence in its selected BurstGPT stratum; effects on other behaviors are modest.

**Preceding revision: focused scientific contribution and editorial revision (2026-10-22).** The evidence supports a tighter, contract-specific case study; full-journal novelty remains a substantive review risk. See the [focused revision report](editorial-revision/REVISION_REPORT.md), [changed-claim audit](editorial-revision/CLAIM_TO_EVIDENCE.md), and [reference comparison](editorial-revision/CLAIM_TO_REFERENCE.md). The author declarations are confirmed. Complete artifact publication and current venue-specific submission checks remain pending, outside this task.

Title: *Scheduler Equivalence and Performance Trade-offs under a Common LLM-Serving Contract*.

The historical focused editorial revision is based exactly on PR #22 commit `dda5fcf0f8f2a6f543e799f20767c9272022afc8` and targets `manuscript/lssp-m3-major-revision`. It selectively incorporates the build-convergence fix and abstract checker from descendant finalization commit `1598518c144bba04ff239794f232fbaa53830356`. It does not import that branch wholesale or update main.

The historical manuscript stack starts from final evidence-review commit `6b2eedd7aa254986b85c1bb901587641cbeac8b0` (PR #17), which includes prewrite-audit commit `d22c7751af9c563d5a4d8a304c007f26112c4d12` (PR #16). It preserves M2 and all historical evidence. Those historical revisions generated no new experiments; the separate sensitivity adds 72 cells.

## Review entry points

- [Historical editorial revision and section word counts](editorial-revision/REVISION_REPORT.md), [post hoc reduced comparisons](editorial-revision/reduced-comparisons.json), and [clean-build verification](editorial-revision/clean-validation.json).
- Earlier status/approval lists below are historical records; they do not reopen the author decisions confirmed on 2026-10-22.

- [Focused major-revision final report](major-revision/FINAL_REPORT.md), [claim audit](major-revision/CLAIM_TO_EVIDENCE.md), [historical major-revision validation](major-revision/VALIDATION.md), and [historical blocker list](major-revision/REMAINING_BLOCKERS.md).
- [Saved-record example and independent verification](major-revision/EXAMPLE_PROVENANCE.md), [related-manuscript disclosure](major-revision/RELATED_MANUSCRIPTS.md), and [rc1/companion pairing](major-revision/COMPANION.md).

- [Historical PR21 artifact-readiness assessment](artifact-release/READINESS.md): **NOT_READY** for submission; verified source licenses/statuses, complete local candidate, author/venue gates.
- [Artifact inventory and access](artifact-release/INVENTORY.md), [portable candidate guide](artifact-release/CANDIDATE_README.md), and [PR21 verification](artifact-release/VERIFICATION.md).
- [Historical final scientific and submission-readiness review](final-review/REFEREE_REPORT.md): **NOT_READY**; includes claim/novelty assessment, overlap and literature audit, author decisions, and correction validation. Its pending status/license questions are superseded by the current artifact-readiness assessment.
- [Final review manuscript PDF](m3-manuscript.pdf).
- [LaTeX source](main.tex) and [bibliography](references.bib).
- [M2-to-M3 changes](M2_TO_M3_CHANGES.md).
- [Claim-to-evidence verification](CLAIM_TO_EVIDENCE.md).
- [Validation results](VALIDATION.md).
- [Historical submission checklist](SUBMISSION_BLOCKERS.md).
- [Reference checks and provenance clarification](REFERENCE_CHECKS.md).

The final review PDF uses an ACM layout with the supported `nonacm` option to suppress untrue submission/publication boilerplate. It is a review copy, not confirmation of current ToMPECS submission requirements. The current revision checks all pages against the user-specified 30-page cap; journal-specific rules remain independently unverified.

## Regenerate displays and build locally

From the repository root, with Python 3, NumPy, Matplotlib, TeX Live (`pdflatex`, `bibtex`), and Poppler installed:

```bash
python paper/tompecs-m3/scripts/render.py
python paper/tompecs-m3/editorial-revision/reduced_comparisons.py
bash paper/tompecs-m3/scripts/build.sh manuscript
bash paper/tompecs-m3/scripts/build.sh acmsmall
python paper/tompecs-m3/scripts/validate.py --standalone --report /tmp/m3-validation.json
```

These commands only read saved experimental summaries, render manuscript assets, compile LaTeX, and check saved evidence. They never invoke the simulator, synthetic-study generator, Slurm, or GitHub Actions. Both build workflows use the byte-preserved ACM template from M2. The output PDFs are under `build/<mode>/`; only the reviewed manuscript-mode PDF is tracked at this directory's top level after checks.

`evidence/inputs/*.json.gz` are deterministic gzip containers of **unchanged source bytes**, verified against `evidence/input-hashes.json`. Absolute source paths identify the review cache; regeneration does not require that cache because all display inputs are bundled. The full raw request/journal/study archives are not republished in this manuscript packet. Their persistent run locations, execution commits, and access limits are documented in the inherited PR #17 review and this manuscript's Appendix B. The current compact reviewer package and separately preserved full evidence archive are prepared for confidential delivery only. Neither is uploaded or hosted. Current instructions prohibit public artifact release and supersede earlier release-planning permissions. Cover letters, current related-submission disclosures, and private reviewer-access instructions remain outside the repository.

The supplementary CSVs retain all C01 cells and endpoints, source/capacity means, chronological aggregates, reversal groups, tie summaries, matched-window differences, all STAT01 stopping records, and all 7,200 final method/endpoint records (18 scenarios × [8 original + 17 expanded methods] × 16 endpoints). The complete ranked/pairwise reports are also included in the compressed saved inputs. STAT01 rows always carry the uncertainty-family label and endpoint availability count.

The four protocol/amendment Markdown files in `supplement/` are unchanged reference copies, not instructions to launch jobs. The copied `scripts/frozen_verify_analysis.py` is the independently implemented C01 report oracle; it imports no production analyzer or experiment runner.
