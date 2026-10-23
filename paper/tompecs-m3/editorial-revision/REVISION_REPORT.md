# Focused M3 scientific and editorial revision

Task outcome: **COMPLETED_SUCCESS** for the requested revision and validation. This is not an unconditional ToMPECS submission-readiness verdict.

## Baseline and integration

- Exact scientific baseline: `dda5fcf0f8f2a6f543e799f20767c9272022afc8` (PR #22).
- Final scientific-content commit: Recorded after the scientific-content commit; see delivery record and draft PR head.
- Branch: `manuscript/lssp-m3-focused-editorial-20261022`.
- Draft PR target: `manuscript/lssp-m3-major-revision`, immediately above #22 (which targets #21's branch).
- Dedicated worktree: `/home/soroush/repos/llm-serving-scheduler-lssp-m3-focused-editorial-20261022`.
- Finalization commit `1598518c144bba04ff239794f232fbaa53830356` descends from the scientific baseline through main PDF-packaging commit `1ed5d332e006fdd0bc3a59a403c9044a36ef6d29`. Its scientific LaTeX, bibliography, figures, tables, and frozen inputs are unchanged from #22. This was checked rather than assumed.
- Selective compatible imports: build-convergence fix and independent abstract checker from `1598518…`. No wholesale merge, main update, artifact release, experiment, editorial submission, or additional worker.
- Remote main remains `1ed5d332e006fdd0bc3a59a403c9044a36ef6d29`. Earlier PRs/reports remain traceable and unmodified. A final delivery record identifies the report-only follow-up commit and pushed PR head.

## Scientific-readiness verdict

**Materially stronger, evidence-supported case study; full-ToMPECS novelty remains borderline.** The paper now makes one linked argument: derive which distinctions can affect execution, measure the surviving trade-offs, and check whether the ranking interpretation survives removal of duplicated comparisons. This is stronger than repeated warnings about metrics and model fidelity. The added post hoc analysis contributes an actual saved-evidence result.

It remains a detailed study under one deliberately restrictive contract. The equivalence argument is straightforward once its assumptions are explicit; large cell counts and extensive validation do not independently establish journal-level novelty. I would not give an unqualified full-journal readiness recommendation solely on the strength of this revision. The smallest meaningful additional evidence would be a targeted matched-input contract perturbation that makes token work binding, predicts where the equivalence argument ceases to apply, and checks the resulting execution/performance differences. An alternative would vary composition-dependent timing. Neither was run, proposed as already completed, or silently added to this task.

No material numerical defect was found. Remaining scientific limits are the fixed contract, selected/temporally related corpus, unresolved older cross-project BurstGPT overlap, dependent metric families, and STAT01's explicitly bounded inferential scope. Exact submitted-version overlap verification, complete artifact publication, and current venue-specific review requirements remain separate pending readiness work; already confirmed author decisions are not reopened.

## Changes and redundancy removed

| Section | Revision |
|---|---|
| Abstract | Leads with executable distinctions and their measured consequences; keeps every original headline magnitude; adds the reduced-view finding; replaces the long list of disclaimed contributions with one scope sentence. |
| Introduction | Removes duplicate headline-result summaries and a second contribution summary; states structural reduction, residual trade-offs, and ranking interpretation once; aligns three RQs with evidence. |
| Related Work | Adds the three targeted comparisons; distinguishes evaluation anti-patterns, output-length learning, and active SLO-aware control from this contract. Uses focused prose rather than an additional dense table. Removes confidential statuses, obsolete unrelated manuscript references, and local submission-upload speculation from scientific text. |
| Contract | Preserves the complete work/residency bound, induction, clock-anchor argument, restrictions, and conformance evidence. This is the single detailed home for the equivalence and inactive-gate explanations. |
| Design | Retains all provenance, transformations, estimands, and denominator definitions. Replaces obsolete release-approval wording with pending-distribution status. |
| Performance/example | Keeps original measurements, tables, and request timelines. Removes duplicated equivalence/RQ summaries and lengthy packaging logistics. Explicitly states independently verified 400 terminal states / 2,497 events. |
| Rankings | Consolidates duplicate-endpoint prose. Adds a labeled post hoc three-behavior/eight-endpoint view with unchanged strict-10% semantics and both original/reduced denominators. Preserves informative whole-FCFS TPOT. |
| STAT01 | Shortens repeated caveats and RQ response. Keeps historical/port/exact arithmetic identities and moves no statistical definitions out of the existing appendix. |
| Discussion/Conclusion | Separates structural argument, finite-corpus observation, illustrative example, and conditional transfer limits. Removes a second numerical headline recap and repeated GPU exclusions. Conclusion states the linked result without re-listing percentages. |
| Declarations/appendix | Uses confirmed affiliation, funding, conflicts, Wulver acknowledgment, and full approved AI statement. Keeps historical evidence reuse and uncertainty; removes author-review prompts, submission IDs/status histories, and internal version discussions. Complete public artifact distribution is honestly pending. |
| Layout/build | Imports convergence fix; uses supported `nonacm` option for review copies to suppress false submission/publication boilerplate; prevents split bibliography entries and removes a forced appendix break that left a near-empty page. The ACM template itself is unchanged. |

Approximate prose counts exclude figures/tables/captions, math, citations, labels, headings, input directives, and bibliography; they are reproducible with `word_counts.py`, not a journal word-limit calculation. Main-text total includes abstract, worked example, and conclusion, excluding declarations and appendix.

| Section | Before | After | Change |
|---|---:|---:|---:|
| abstract | 212 | 202 | -4.72% |
| introduction | 604 | 439 | -27.32% |
| related | 719 | 480 | -33.24% |
| contract | 909 | 909 | +0.00% |
| design | 907 | 904 | -0.33% |
| performance | 752 | 720 | -4.26% |
| example | 510 | 475 | -6.86% |
| rankings | 639 | 688 | +7.67% |
| inference | 490 | 436 | -11.02% |
| conclusion | 142 | 92 | -35.21% |
| discussion | 534 | 391 | -26.78% |
| declarations | 386 | 199 | -48.45% |
| appendix | 2,000 | 1,956 | -2.20% |

Main prose: **6,418 → 5,736 words (-10.63%)**. The rankings section grows because it contains a new analysis; the reduction is not achieved by removing qualifications or moving the main narrative into an appendix.

## References and novelty comparison

Added Agrawal et al. (arXiv:2507.09019v1) for evaluation anti-patterns; Fu et al. (NeurIPS 2024) for learned output-length ordering; Hong et al. (SOLA, MLSys 2025) for active state-aware SLO scheduling. Each supports a specific distinction. The complete [claim-to-reference matrix](CLAIM_TO_REFERENCE.md) rechecks existing workload, simulator, serving-system, Dai, verification/validation, and statistical sources. There are 28 cited entries and no undefined/unused bibliography keys.

The SOLA proceedings metadata disagrees with the published PDF on the order of two authors; the bibliography follows the PDF and records its 13-page length without inventing a DOI or page range. Agrawal's experimental HTML title differs from the abstract/DOI title; the bibliography uses the primary metadata title. Some publisher full texts remain access-limited; primary manuscripts, official proceedings/slides, and publisher-deposited metadata are distinguished rather than represented as universal full-text access.

## Effective comparison diversity

The complete original analysis remains 4 labels, 6 pairs, 11 endpoints, 15,840 rankings, 95,040 pairwise records, and 26,136 reversal groups. The post hoc view retains 3 distinct behaviors, 3 pairs, and 8 endpoints in 5 families: latency, TTFT, TPOT, throughput, and deadline attainment. Completion is uniformly tied; three throughput rankings coincide. Mean/p95 distinctions remain. Whole-FCFS has a strict-10% TPOT disadvantage in 341 mean and 1,027 p95 conditions, so discarding TPOT entirely would lose informative differences.

| Reduced axis | Reversals | Eligible | Total |
|---|---:|---:|---:|
| kv | 240 | 17,219 | 17,280 |
| load | 629 | 85,962 | 86,400 |
| metric | 4,492 | 120,288 | 120,960 |
| source | 61,880 | 1,374,720 | 1,382,400 |
| source_mean | 0 | 864 | 864 |
| window | 18,732 | 670,637 | 673,920 |

The view has 11,520 rankings, 34,560 matched pairs, and 8,208 reversal groups. Every retained archived group agrees with independently recalculated absolute-cell comparisons using exact rational arithmetic on represented floats. The full original oracle uses separate code and direct enumeration. Near-tie tolerance changes TPOT top-set diagnostics only; it never changes the strict practical-reversal rule. Source-mean stability and window/metric sensitivity survive the reduction. Neither original nor reduced counts are independent trials, and their rates are not interchangeable.

## Independently executed validation

- **PASS:** original complete C01 oracle: 5,760 cells, 15,840 rankings, 95,040 pairwise records, 26,136 reversal groups.
- **PASS:** 54/54 original narrative checks in the worktree, including the protected historical dataset hash; 53/53 in the clean standalone copy, where that checkout-only test is intentionally inapplicable.
- **PASS:** all 7,200 STAT01 endpoint CSV records exactly agree with saved endpoint fields. This is a regression check of saved results, not regeneration of 134,000 studies.
- **PASS:** independent abstract effect calculation, 1,152,000 completed executions, and 1,440 matched metric equalities. Prior exhaustive raw-terminal verification is retained, not falsely described as newly rerun in this focused task.
- **PASS:** fresh event reconstruction of the selected example: 400 terminal states, 2,497 events; selection, displayed tables, admissions, and p95 brackets checked.
- **PASS:** all 8,208 reduced reversal groups independently recomputed; TPOT diagnostics and duplicate-throughput/completion identities checked.
- **PASS:** clean figure/table regeneration with newly created Python venv and pinned NumPy 2.3.5, SciPy 1.17.1, Matplotlib 3.10.9. 57 compared generated/copied files byte-identical, including all original figures/tables and supplementary CSVs. TeX Live 2023/Debian and Poppler remain system dependencies; this is an isolated dependency/auxiliary-file build, not a newly provisioned operating system.
- **PASS:** 63 frozen tracked assets match the exact scientific baseline. Protected hydrated dataset files in both old and new worktrees retain SHA-256 `73adf7d97f06985ec8f8e1c2f794fd43178433eb198e1c00705e817f4bde9c26` and remain uncommitted.
- **PASS:** clean builds, citation/label/reference checks, all-page rendering and visual inspection, and PDF internal destination bounds. Zero overfull boxes, unresolved citations, unresolved references, or numerical failures. Three inherited optional BibTeX metadata advisories remain (Vidur address; Maurer publisher/address); no metadata is invented to silence them.
- **Link check:** all 29 distinct external annotations opened or classified; one mailto address was not contacted. Seventeen requests returned HTTP200, three IEEE links HTTP202, eight publisher links access errors. DOI identities were separately verified; these results do not certify every publisher full-text download. See `pdf-link-check.json`. No fictional M3 release/DOI link is present.

Commands and complete machine-readable results are in this directory and `../evidence/validation/validation.json`. All checks consume saved evidence; experiments executed: **0**. No background job remains.

## Final files

- [manuscript PDF](../m3-manuscript.pdf): 24 pages, 715,947 bytes, SHA-256 `feb277e11cfda0a335e82e9db299f5b985c78824eff15c9e84b908e1f6e11015`.
- [acmsmall PDF](../m3-acmsmall.pdf): 24 pages, 712,082 bytes, SHA-256 `ccb5c6c25f38204411def9f91ee7f02a8555b91ff6c7ca1624cdd096f48431ab`.
- [Manuscript source](../main.tex), [bibliography](../references.bib), and [section sources](../sections/).
- [Changed-claim/evidence matrix](CLAIM_TO_EVIDENCE.md), [reference matrix](CLAIM_TO_REFERENCE.md), [reduced results](reduced-comparisons.json), [clean validation](clean-validation.json), [PDF metadata](pdf-metadata.json), [preservation record](preservation.json), and [visual review](VISUAL_REVIEW.md).
- Existing confidential overlap and cover-letter records were preserved; none of their submission identifiers was copied into the revised article.

The PDFs are available on the dedicated revision branch only. The author-requested later main integration, complete artifact releases, and journal submission are not part of this task. The final response and delivery record supply exact pushed commits and the draft PR link.
