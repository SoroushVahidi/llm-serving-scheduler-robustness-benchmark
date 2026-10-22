# ToMPECS Phase M2 — independent adjudication and author review

> Historical manuscript version. The [current M3 PDF](../../LLM_Serving_Scheduler_Rankings_and_Performance_Tradeoffs.pdf) is the sole full-manuscript PDF on `main`; links below to older PDFs are pinned to their historical commit. Sources, figures and numerical validation records are retained.

**COMPLETED_WITH_ISSUES. Scientific readiness: NO-GO for publication-level comparative/native claims. Submission readiness: NOT READY.** A conditional historical simulator case study is defensible for author review; unresolved scientific limitations are not repaired by formatting.

Stack: `manuscript/lssp-tompecs-m2` directly on PR #9's verified `366752a76f86dec30190f3e7767124f684378de4` (`manuscript/lssp-tompecs-m1`). All M1 and earlier files are preserved.

Start with:

1. [Revised manuscript PDF](https://github.com/SoroushVahidi/llm-serving-scheduler-robustness-benchmark/blob/dda5fcf0f8f2a6f543e799f20767c9272022afc8/paper/tompecs-m2/revised-manuscript.pdf), [source](revised/main.tex), and [acmsmall diagnostic PDF](https://github.com/SoroushVahidi/llm-serving-scheduler-robustness-benchmark/blob/dda5fcf0f8f2a6f543e799f20767c9272022afc8/paper/tompecs-m2/revised-acmsmall.pdf).
2. [Independent statistical audit](M2_STATISTICAL_AUDIT.md).
3. [Research-question mapping](M2_RQ_ALIGNMENT.md).
4. [Skeptical referee report and M3 recommendation](M2_REFEREE_REPORT.md).
5. [Every quantitative/inferential claim change](M2_CLAIM_CHANGES.md), with [complete source diff](evidence/m1-to-m2-manuscript.diff).
6. [Reproduction/validation](VALIDATION.md), [section/page allocations](LENGTH_INVENTORY.md), and [numerical evidence summary](evidence/statistical-audit.json).

The manuscript is 27 pages in ACM manuscript mode and 28 in acmsmall, including all references/declarations. Typography is unchanged. It now asks four explicitly retrospective manuscript questions and maps every original RQ to its answered, partial or unresolved status.

All checked intervals and Friedman records reproduce. Inference is weaker than the old terminology: bootstrap tail fractions, screened BH families and window dependence do not establish calibrated 95% confidence or 5% FDR. We retain historical counts and withdraw those guarantees. Set-valued top-policy intersection is 57.8%, distinct from the unchanged 31.9% ID agreement. Matched-support sensitivities preserve the broad descriptive pattern while exposing different estimands. Full-family multiplicity bookkeeping and grouped-window resampling each leave 30 of 36 primary cases under their own rules; neither is a calibrated replacement discovery count.

**Unresolved blockers:** policy-dependent service/resource abstractions; no faithful native or synthetic transfer result; unestablished sampling/null calibration; limited source/provider coverage; publication-overlap and source-release checks; incomplete reference metadata/declarations; current journal requirements not independently accessible. The referee recommendation is not to submit this package as a validated serving-policy comparison.

**M3 recommendation:** author chooses the scientific scope first. A bounded historical-methodology paper needs contribution/overlap/venue review; a serving-policy paper needs a separately authorized common-model validation and new-evidence plan. M3 was not launched.

No Actions, paid CI, GPU inference, new serving/simulation campaign, Slurm/Wulver submission, merge, journal submission, editor contact or dataset publication. The inherited LFS anomaly remains unchanged and unstaged. Draft-PR publication is the authorized review deliverable only.
