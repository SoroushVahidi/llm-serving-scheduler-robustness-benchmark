# M3 author-review manuscript

**Current scientific verdict: READY_FOR_AUTHOR_AND_ADMINISTRATIVE_FINALIZATION.** Author review, access, disclosure and administrative blockers remain; submission is not authorized.

Title: *Scheduler Rankings and Performance Trade-offs in a Common-Model LLM-Serving Evaluation*.

This directory is a new manuscript, stacked on final evidence-review commit `6b2eedd7aa254986b85c1bb901587641cbeac8b0` (PR #17), which includes prewrite-audit commit `d22c7751af9c563d5a4d8a304c007f26112c4d12` (PR #16). It preserves M2 and all historical evidence. No new experiment is part of this package.

## Review entry points

- [Focused major-revision final report](major-revision/FINAL_REPORT.md), [claim audit](major-revision/CLAIM_TO_EVIDENCE.md), [current validation](major-revision/VALIDATION.md), and [remaining blockers](major-revision/REMAINING_BLOCKERS.md).
- [Saved-record example and independent verification](major-revision/EXAMPLE_PROVENANCE.md), [related-manuscript disclosure](major-revision/RELATED_MANUSCRIPTS.md), and [rc1/companion pairing](major-revision/COMPANION.md).

- [Historical PR21 artifact-readiness assessment](artifact-release/READINESS.md): **NOT_READY** for submission; verified source licenses/statuses, complete local candidate, author/venue gates.
- [Artifact inventory and access](artifact-release/INVENTORY.md), [portable candidate guide](artifact-release/CANDIDATE_README.md), and [PR21 verification](artifact-release/VERIFICATION.md).
- [Historical final scientific and submission-readiness review](final-review/REFEREE_REPORT.md): **NOT_READY**; includes claim/novelty assessment, overlap and literature audit, author decisions, and correction validation. Its pending status/license questions are superseded by the current artifact-readiness assessment.
- [ACM manuscript PDF](m3-manuscript.pdf) and [acmsmall PDF](m3-acmsmall.pdf).
- [LaTeX source](main.tex) and [bibliography](references.bib).
- [M2-to-M3 changes](M2_TO_M3_CHANGES.md).
- [Claim-to-evidence verification](CLAIM_TO_EVIDENCE.md).
- [Validation results](VALIDATION.md).
- [Remaining submission blockers](SUBMISSION_BLOCKERS.md).
- [Reference checks and provenance clarification](REFERENCE_CHECKS.md).

The two PDFs are review formats, not confirmation of current ToMPECS submission requirements. No journal-specific page limit is asserted.

## Regenerate displays and build locally

From the repository root, with Python 3, NumPy, Matplotlib, TeX Live (`pdflatex`, `bibtex`), and Poppler installed:

```bash
python paper/tompecs-m3/scripts/render.py
bash paper/tompecs-m3/scripts/build.sh manuscript
bash paper/tompecs-m3/scripts/build.sh acmsmall
python paper/tompecs-m3/scripts/validate.py
```

These commands only read saved experimental summaries, render manuscript assets, compile LaTeX, and check saved evidence. They never invoke the simulator, synthetic-study generator, Slurm, or GitHub Actions. Both build workflows use the byte-preserved ACM template from M2. The output PDFs are under `build/<mode>/`; the reviewed copies at this directory's top level are packaged after checks.

`evidence/inputs/*.json.gz` are deterministic gzip containers of **unchanged source bytes**, verified against `evidence/input-hashes.json`. Absolute source paths identify the review cache; regeneration does not require that cache because all display inputs are bundled. The full raw request/journal/study archives are not republished in this manuscript packet. Their persistent run locations, execution commits, and access limits are documented in the inherited PR #17 review and this manuscript's Appendix B. Reviewer access remains an author-review gate.

The supplementary CSVs retain all C01 cells and endpoints, source/capacity means, chronological aggregates, reversal groups, tie summaries, matched-window differences, all STAT01 stopping records, and all 7,200 final method/endpoint records (18 scenarios × [8 original + 17 expanded methods] × 16 endpoints). The complete ranked/pairwise reports are also included in the compressed saved inputs. STAT01 rows always carry the uncertainty-family label and endpoint availability count.

The four protocol/amendment Markdown files in `supplement/` are unchanged reference copies, not instructions to launch jobs. The copied `scripts/frozen_verify_analysis.py` is the independently implemented C01 report oracle; it imports no production analyzer or experiment runner.
