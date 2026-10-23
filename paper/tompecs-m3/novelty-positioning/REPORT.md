# Focused scientific-contribution revision

State: **COMPLETED_SUCCESS**. Baseline: actual PR #25 head
`d73192df32fd14ec025eb8b9dab72da401eb65ae`.
Branch: `manuscript/lssp-m3-novelty-positioning-20261023`.

No experiments, simulator changes, workload changes, or new result tables were introduced. Authorship and declarations remain unchanged.

## Before and after

The baseline already contained the necessary scientific evidence, but its title emphasized rankings, its research questions separated performance/rankings/historical inference, and its discussion of Vidur did not adequately credit Vidur-Bench's shared workload/policy comparisons. The urgency certificate was present without being one of the organizing research questions.

The revised title is **Scheduler Equivalence and Performance Trade-offs under a Common LLM-Serving Contract**. The introduction now asks: which distinctions survive the contract, why are others inactive, and what preferences remain at different comparison levels? The contributions are effective behavior, a mechanistic/mathematical inactivity explanation, and the interpretation of residual trade-offs. Reproducibility and historical calibration support that argument rather than supplying additional scheduler novelty.

See [CONTRIBUTIONS.md](CONTRIBUTIONS.md) for each claim, artifact, denominator and boundary, and [PRIOR_WORK.md](PRIOR_WORK.md) for the primary-literature comparison and access/version qualifications.

## Exact manuscript changes

- **Title and abstract:** emphasize the contract-dependent behavioral result; place the finite-work certificate beside the equivalence; state both original and reduced source-mean denominators; distinguish observed binding-budget persistence from the original proof. Remove historical calibration from the abstract's contribution list.
- **Introduction:** replace the performance/rankings/historical RQs with effective behavior, mechanism inactivity, and residual trade-offs/rankings. Credit existing workload, metric, shared-simulation and fairness work before posing the narrower question.
- **Related work:** explicitly discuss Vidur-Bench within Vidur; tie distinctions from Etalon and the evaluation-methodology preprint to concrete M3 sections; acknowledge Bari et al.'s formal batching framework. Retain native scheduling, workload and inference provenance with less repeated framing. No bibliography entries added or removed.
- **Section 3:** name the conditional state-transition argument; distinguish the induction from terminal-record confirmation; give the finite-work certificate a named paragraph and spell out its sufficient inequality and interpretation. The proof assumptions, equation, gate threshold and numerical bounds are unchanged. Compress repeated model motivation.
- **Sections 5–7:** align headings and answer paragraphs with the new RQs. Expand `0/864` into its exact population and state its scope. Preserve all original within-window, window-pair, source-mean, cross-metric and separate budget-sensitivity results. Historical inference is explicitly supporting evidence.
- **Discussion, limitations and conclusion:** connect model constraints to executable mechanisms and the residual performance question; distinguish failure of a proof premise from empirical failure of equivalence; retain corpus, dependence, inference and physical-model limitations without repeatedly summarizing the whole paper.

The frozen figures/tables and their numbering are unchanged; the 28-entry bibliography, declarations, data, code, experiment configurations, mathematical equation and numerical support are preserved. Both final PDFs remain **26 pages**. On the same whitespace-delimited LaTeX-source measure, main-text sources plus abstract decrease from **7,284 to 7,149 tokens (1.9%)**; this is not a prose-only word count. [Exact accounting](source-word-counts.json).

## Validation

- All **54 original scientific/preservation checks** pass, including the independent full C01 report oracle and all 7,200 saved STAT01 endpoint rows.
- Repository tests: **378 passed**, four known numerical warnings on constant/nearly constant test inputs. Frozen C01 contract tests: **42 passed**.
- Independently rechecked existing abstract effects, reduced comparisons, the 72-cell budget sensitivity, and the finite-work certificate/event reconstruction: 18 SLO cells, 107,844 ready opportunities, zero urgent decisions.
- Existing preservation checker confirms 63 frozen tracked assets and the protected hydrated file. Baseline support records are restored after fresh verification reports are copied here. Only declared manuscript/support files and the two PDFs are committed.
- Both PDFs rebuild with **zero overfull boxes, unresolved references/citations, or duplicate labels**. The three existing optional bibliography-metadata advisories remain. Visual review covers the changed narrative, equation, tables, section transitions, references and final figure in both layouts.
- Detailed checks and PDF hashes: [verification.json](verification.json), [scientific-validation.json](scientific-validation.json), [abstract-check.json](abstract-check.json), [preservation.json](preservation.json). Reproduction commands: [COMMANDS.md](COMMANDS.md).

## Remaining weaknesses and verdict

There is a defensible independent contribution suitable for consideration as a tightly scoped performance-modeling/evaluation case study: conditional equivalence, a sufficient inactivity certificate, and a measured account of the comparisons that survive. The revision makes that contribution easier to assess; it does not add scientific evidence or transform it into a broad scheduling theory.

The restricted fixed-cost model suppresses mechanisms relevant to native serving. The inequalities are elementary, the budget study is confined to a small selected stratum with rare saturation, and the ranking observations are descriptive and dependent. A reviewer can reasonably question whether the explanatory reach is sufficient for a full journal article. Writing cannot establish transfer, hardware fidelity, representativeness, or greater novelty. Complete-artifact reviewer access remains a separate readiness issue; this revision does not certify submission readiness or current venue requirements.
