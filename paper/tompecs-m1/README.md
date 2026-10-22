# ToMPECS Phase M1 — author-review draft

> Historical manuscript version. The [current M3 PDF](../../LLM_Serving_Scheduler_Rankings_and_Performance_Tradeoffs.pdf) is the sole full-manuscript PDF on `main`; links below to older PDFs are pinned to their historical commit. Sources, figures and numerical validation records are retained.

**Preparation only. Not submission-ready. No journal submission, experiment, GPU allocation, CI run or merge.**

Repository: `SoroushVahidi/llm-serving-scheduler-robustness-benchmark` (private working repository).
Branch: `manuscript/lssp-tompecs-m1`, based on verified remote main
`e73a3b711b65f9c181ff9a2674007efca22f1b65`. It is independent of, and does not modify, draft PRs #3–#8.

Start with:

1. [Revised manuscript PDF](https://github.com/SoroushVahidi/llm-serving-scheduler-robustness-benchmark/blob/dda5fcf0f8f2a6f543e799f20767c9272022afc8/paper/tompecs-m1/revised-manuscript.pdf) and [LaTeX](revised/main.tex).
2. [Claim-to-evidence audit](CLAIM_AUDIT.md), particularly DISPUTED statements corrected in the draft.
3. [Source authority and submission lineage](AUTHORITY.md).
4. [Fidelity boundary](FIDELITY.md).
5. [Length inventory](LENGTH_INVENTORY.md) and [figure/table inventory](FIGURES_TABLES.md).
6. [Requirements and uncertainties](REQUIREMENTS.md).
7. [Validation/reproduction](VALIDATION.md) and [prioritized author revision plan](REVISION_PLAN.md).

The layout-only [baseline PDF](https://github.com/SoroushVahidi/llm-serving-scheduler-robustness-benchmark/blob/dda5fcf0f8f2a6f543e799f20767c9272022afc8/paper/tompecs-m1/baseline-manuscript.pdf) retains the SMPT scientific text, **including claims now known to be disputed**. Do not use it as the current scientific draft. Baseline and revised acmsmall PDFs are separate layout diagnostics; manuscript mode is the review target. All pages, including references and declarations, count in our conservative totals. The 29-page planning allocation is retained; unused space is available for author revisions rather than padded with unverified claims.

The numerical audit reads preserved outputs only. It verifies counts and point estimates; it does not generate new simulation outcomes, native inference, bootstrap results, or scientific experiments. The revised paper characterizes historical simulator ranking portability, not the prospective A100/L40/TP/DP research program. No new algorithmic novelty is claimed for standard rank statistics.

All additions are under this directory. Frozen datasets, manifests, original manuscript files, simulator code, existing PRs and MGPU06 authority remain unchanged. `evidence/` contains source identities, raw checks, discrepancies, commands, and the original-to-ACM preservation comparison. Public availability, overlap review, full bibliography review, scientific approval, cover letter and submission authorization remain separate gates.
