> **Current revision:** see [major-revision/FINAL_REPORT.md](major-revision/FINAL_REPORT.md), [focused claims](major-revision/CLAIM_TO_EVIDENCE.md), and [remaining blockers](major-revision/REMAINING_BLOCKERS.md). Earlier reports below are historical.

> **Superseded checklist/report.** See [current artifact-readiness assessment](artifact-release/READINESS.md) and [current validation](artifact-release/VERIFICATION.md). This earlier record is retained as history.

# M3 validation

This records the original PR #19 rewrite. The [final review](final-review/REFEREE_REPORT.md), [reference audit](final-review/REFERENCES.md), and [final validation](final-review/VALIDATION.md) supersede it for the stacked correction.

**State: COMPLETED_SUCCESS.** The manuscript and author-review packet are complete; the separate submission checklist remains open.

## Scientific and numerical checks

- Verified all 37 bundled saved-input files against uncompressed and compressed SHA-256 fingerprints, including the PR #17 anchors for C01 absolute metrics/completion and STAT01 completion/checkpoint.
- Ran the copied independent C01 report oracle over **5,760 absolute rows, 15,840 ranking rows, 95,040 matched-difference rows, and 26,136 reversal groups**, including exact represented-value 10% boundaries and all source/chronological aggregates. PASS. This reads saved outputs and does not execute a scheduler.
- Checked **54 narrative anchors**, including complete execution, ranges, reuse, equivalence, source-factor ranges, source/metric top-set counts, chronological differences, and selected STAT01 values/availability.
- Regenerated all numerical tables and three data figures from saved inputs; the fourth figure is the execution-contract diagram defined in LaTeX. Verified mean-latency/throughput sign contrasts and unfavorable BurstGPT tails across all six source/capacity aggregates.
- Compared every numerical field of the **7,200 STAT01 endpoint CSV records** to its corresponding saved method/scenario/family report. Original and expanded families remain separate, with endpoint availability counts.
- Reviewed RQ/contribution/result alignment and removed stale M2 scientific claims. The claim-to-evidence report identifies preserved historical counts and the limits of each evidence stratum.

Machine-readable results: `evidence/numerical-checks.json` and `evidence/validation/validation.json`. Complete prior event/study validation is attributed to the completed allocations and PR #17. This task did **not** rerun all raw event journals or regenerate synthetic studies.

## Builds, references, and layout

Both local ACM workflows complete successfully using M2's unchanged template and the normal pdflatex/BibTeX/three-pass workflow. Final PDFs are packaged at this directory's top level; page counts and hashes are in `evidence/package-manifest.json`.

- No LaTeX error, overfull box, unresolved citation/reference, duplicate label, or pending cross-reference rerun warning.
- **20 cited bibliography entries**, all resolved; no uncited bibliography entries.
- Four figures have accessibility descriptions; units, directions, capacity notation, source labels, sample units, and p95 aggregation are explicit.
- The normal acmart advisory about suppressing the ACM reference-format block remains, as in the existing author-review workflow. Optional bibliography advisories concern the unprovided address for Vidur and publisher/address for COLT; missing values were not invented. Final submission metadata and format remain author-review items.
- Visual inspection covers every page in both formats via rendered contact sheets, with full-size checks of figure/table pages. Corrections address long identifier overflow, figure placement, clipped plot labels, and appendices. Sparse float pages are used for the twelve-panel absolute-performance figure rather than shrinking its labels further.

## Preservation and execution boundary

The branch is stacked directly on `6b2eedd7aa254986b85c1bb901587641cbeac8b0`. Only `paper/tompecs-m3/` is added. No M2, protocol, simulator, frozen-input, or experimental-result file is edited. Protocols and the independent report oracle within M3 are labeled reference copies, with file hashes in the package manifest.

The inherited working tree reports `dataset/v1.1.0/scientific/campaign/consolidated.json` as modified because of its pre-existing hydrated-LFS state. Its SHA-256 remains **73adf7d97f06985ec8f8e1c2f794fd43178433eb198e1c00705e817f4bde9c26**, matching the preservation record. It is excluded from the commit.

No new experiment, Slurm submission, GitHub Actions run, merge, journal submission, or external correspondence was performed. The commit and draft PR use `[skip ci]` so the repository's push/pull-request workflows are skipped. Author declarations, release permissions/access, related-manuscript status, and official venue requirements remain open as listed in `SUBMISSION_BLOCKERS.md`.
