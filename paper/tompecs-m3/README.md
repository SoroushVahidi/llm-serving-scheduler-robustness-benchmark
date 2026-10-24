# M3 author-review manuscript

**Final PDF: READY_FOR_AUTHOR_SUBMISSION_REVIEW.** Final author attestations and the journal portal requirements remain; no journal submission has been performed.

Title: *Scheduler Equivalence and Performance Trade-offs under a Common LLM-Serving Contract*.

The [final 29-page PDF](LLM_Serving_Scheduler_Equivalence_and_Performance_Tradeoffs.pdf) is byte-identical to the validated manuscript in [PR #31](https://github.com/SoroushVahidi/llm-serving-scheduler-robustness-benchmark/pull/31), source commit `8e9e23914c7b9298f1335005a1ef86851b5ef8cb`. Its SHA-256 is `7bd5183d8aa6b9acf56c464f560c3171b4995cda2586ecad6652aee6c46111a2`; [download provenance](download-manifest.json) records its identity and historical locations.

**Source/PDF distinction:** the LaTeX, figures, tables and scientific records on `main` remain at an earlier revision. Building this checkout does **not** reproduce the final PDF. The corresponding [final manuscript source](https://github.com/SoroushVahidi/llm-serving-scheduler-robustness-benchmark/tree/8e9e23914c7b9298f1335005a1ef86851b5ef8cb/paper/tompecs-m3) is pinned to PR #31. This publication updates only the PDF and its download documentation; it does not merge PRs #27–#31 or change scientific source or evidence.

The inherited source and review records below describe earlier M3 revisions, including final evidence-review commit `6b2eedd7aa254986b85c1bb901587641cbeac8b0` (PR #17) and prewrite-audit commit `d22c7751af9c563d5a4d8a304c007f26112c4d12` (PR #16). Their historical verdicts, filenames, page counts and checksums are preserved and do not describe the final PDF. No new experiment is part of this publication.

## Historical source and review entry points

- [Focused major-revision final report](major-revision/FINAL_REPORT.md), [claim audit](major-revision/CLAIM_TO_EVIDENCE.md), [historical validation](major-revision/VALIDATION.md), and [historical remaining blockers](major-revision/REMAINING_BLOCKERS.md).
- [Saved-record example and independent verification](major-revision/EXAMPLE_PROVENANCE.md), [related-manuscript disclosure](major-revision/RELATED_MANUSCRIPTS.md), and [rc1/companion pairing](major-revision/COMPANION.md).

- [Historical PR21 artifact-readiness assessment](artifact-release/READINESS.md): **NOT_READY** for submission; verified source licenses/statuses, complete local candidate, author/venue gates.
- [Artifact inventory and access](artifact-release/INVENTORY.md), [portable candidate guide](artifact-release/CANDIDATE_README.md), and [PR21 verification](artifact-release/VERIFICATION.md).
- [Historical final scientific and submission-readiness review](final-review/REFEREE_REPORT.md): **NOT_READY**; includes claim/novelty assessment, overlap and literature audit, author decisions, and correction validation. Its pending status/license questions are superseded by the current artifact-readiness assessment.
- [Current validated manuscript PDF — 29 pages](LLM_Serving_Scheduler_Equivalence_and_Performance_Tradeoffs.pdf) and [download provenance](download-manifest.json).
- [Earlier LaTeX source on main](main.tex) and [earlier bibliography](references.bib); use the pinned PR #31 source above for the final PDF.
- [M2-to-M3 changes](M2_TO_M3_CHANGES.md).
- [Claim-to-evidence verification](CLAIM_TO_EVIDENCE.md).
- [Validation results](VALIDATION.md).
- [Remaining submission blockers](SUBMISSION_BLOCKERS.md).
- [Reference checks and provenance clarification](REFERENCE_CHECKS.md).

Only the final principal PDF is tracked as the current M3 manuscript. Older full-manuscript PDFs remain available through commit-pinned historical locations in `download-manifest.json`; no alternate manuscript PDF is retained on `main`. Figure PDFs and validation records remain unchanged. The review format does not establish current TOMPECS submission requirements; no journal-specific page limit is asserted.

## Build the historical source retained on main

From the repository root, with Python 3, NumPy, Matplotlib, TeX Live (`pdflatex`, `bibtex`), and Poppler installed:

```bash
python paper/tompecs-m3/scripts/render.py
bash paper/tompecs-m3/scripts/build.sh manuscript
bash paper/tompecs-m3/scripts/build.sh acmsmall
python paper/tompecs-m3/scripts/validate.py
```

These commands only read saved experimental summaries, render manuscript assets, compile LaTeX, and check saved evidence. They never invoke the simulator, synthetic-study generator, Slurm, or GitHub Actions. Both build workflows use the byte-preserved ACM template from M2. The local output PDFs are under `build/<mode>/`. These outputs belong to the historical source revision, not the final PDF. The single current manuscript download is `LLM_Serving_Scheduler_Equivalence_and_Performance_Tradeoffs.pdf`. Historical package manifests and reports retain their original filenames and checksums; `download-manifest.json` identifies the final PDF and links to earlier provenance.

`evidence/inputs/*.json.gz` are deterministic gzip containers of **unchanged source bytes**, verified against `evidence/input-hashes.json`. Absolute source paths identify the review cache; regeneration does not require that cache because all display inputs are bundled. The full raw request/journal/study archives are not republished in this manuscript packet. Their persistent run locations, execution commits, and access limits are documented in the inherited PR #17 review and this manuscript's Appendix B. Reviewer access remains an author-review gate.

The supplementary CSVs retain all C01 cells and endpoints, source/capacity means, chronological aggregates, reversal groups, tie summaries, matched-window differences, all STAT01 stopping records, and all 7,200 final method/endpoint records (18 scenarios × [8 original + 17 expanded methods] × 16 endpoints). The complete ranked/pairwise reports are also included in the compressed saved inputs. STAT01 rows always carry the uncertainty-family label and endpoint availability count.

The four protocol/amendment Markdown files in `supplement/` are unchanged reference copies, not instructions to launch jobs. The copied `scripts/frozen_verify_analysis.py` is the independently implemented C01 report oracle; it imports no production analyzer or experiment runner.
