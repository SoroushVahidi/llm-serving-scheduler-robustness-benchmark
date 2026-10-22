# Independent skeptical ToMPECS referee assessment

Recommendation for the present scientific package: **NO-GO for submission / not ready for acceptance**. The revised descriptive manuscript is suitable for author review. That is not a recommendation to submit it now. The fundamental concern is the interpretation of policy comparisons under different service/resource abstractions, compounded by uncalibrated inference and incomplete external validation.

## Summary of contribution

The work treats portability of a comparative conclusion as an evaluation output. It preserves a fixed corpus, enumerates source/region/metric comparisons, distinguishes full-order agreement from practical pair changes, and exposes the effects of eligibility and tie rules. Independent reproduction and explicit corrections make the evidence more trustworthy as a historical simulator case study. They do not independently validate the simulated mechanisms or establish a general law of serving behavior.

## 1. Novelty beyond standard statistics

**Assessment: limited to moderate; acceptance case remains weak.** Kendall/Spearman, bootstrap, Friedman and BH are standard. Workload sensitivity and resampling in scheduler evaluation are established; rank-based comparison across datasets is also established. Adding these tools to LLM serving is not itself a strong methodological advance.

A defensible contribution is the integrated, traceable comparison contract and its demonstrated failure modes: deterministic top choice versus set overlap, marginal means versus paired-support intervals, and pooled policy effects versus portability. This has educational and reproducibility value. A ToMPECS referee may nevertheless ask for a validated method that changes evaluation decisions, a generalizable empirical finding under a defensible model, or a stronger analytical insight. M2 does not pretend to supply such a result simply by improving prose.

**Correctable writing:** narrow novelty claims, explain exactly what each comparison object adds, relate to prior workload-resampling and rank-comparison studies, avoid priority claims and scheduler innovation language. Implemented.

**Requires new evidence or a different contribution:** validate any proposed evaluation decision rule or show comparative findings under a common, verified execution model. Merely expanding the literature review cannot provide that evidence.

## 2. Correctness and strength of inference

**Assessment: arithmetic reliable in audited scope; inferential guarantees unsupported.** The independent reproduction is unusually concrete: all 198 source-ranking intervals, 72 primary reversal intervals, 6,890 cross-metric difference intervals, six cross-metric rank intervals and 66 Friedman records match. However:

* The bootstrap assumes a sampling structure not established for stride-selected, temporally related production windows. Tied rank statistics are nonsmooth.
* Empirical bootstrap tails are called sign tests without a demonstrated calibrated null distribution. Same-data sign/margin screening precedes BH, and dependence assumptions are unverified.
* Practical point margins exceeding 10% do not establish population effects exceeding 10%.
* Conditional point differences and bootstrap differences use different supports.
* Friedman tests pooled policy effects, not cross-source rank reversals. Conditional omnibus records exclude vLLM entirely.
* Many apparently separate comparisons reuse the same data.

M2 appropriately withdraws calibrated significance/FDR claims rather than replacing them with a more flattering post-hoc result. Full-family arithmetic and grouped-window sensitivities each reduce the primary procedural count to 30; stronger bookkeeping gives other counts. None is a certified discovery count. The broad descriptive cross-metric pattern survives matching support; the meaning of top-policy disagreement changes markedly under sets.

**Correctable now:** label estimands and nominal intervals, remove guarantees, report all finite-corpus outcomes and post-hoc sensitivities. Implemented.

**Not repaired by writing or more bootstrap draws:** establish independent sampling, null calibration and a prospective multiplicity/direction contract for future inference. A defensible purely descriptive paper can forego significance, but then its scientific value must rest elsewhere.

## 3. Simulator and policy comparisons

**Assessment: major scientific blocker for intended scheduler interpretation.** Different policy paths can receive instantaneous versus budgeted prefill and different KV enforcement. Policy-local shadow state and oracle trace information can differ from native execution. Determinism and passing unit tests prove neither treatment comparability nor implementation equivalence. The experiment is a comparison of policy–model combinations, not an isolated manipulation of scheduling discipline.

Absolute outcomes make the issue visible: LOW mean ANWG ranges from .018 to 1.000 in Azure but .968 to 1.000 in BurstGPT. This is not, by itself, evidence against any named native serving system; it may reflect the representation and constraints applied to that implementation. No sensitivity on frozen outcome aggregates identifies the counterfactual ranking under a common service/resource model.

The legacy physical study cannot arbitrate this: MIG identity, missing class transport, synthetic clock, admission/replay and execution-plan discrepancies undermine the intended policy comparison. CPU ledger work and bounded engineering smoke cannot replace faithful serving evidence. These limitations are structural, not merely missing confidence intervals.

**NO-GO:** interpretation as native system superiority, faithful physical rank transfer, or causal scheduler-mechanism effects. Conditional descriptive interpretation remains possible and is what M2 permits.

**Acceptance evidence needed:** an explicit common execution/service contract, outcome-independent eligibility and information model, mechanism-level conformance evidence, and either validated trace-level simulation comparisons or a scientifically justified alternative scope that does not need native portability. Any corrected outcomes must be a new version, not substituted into this corpus. This report does not authorize experiments.

## 4. Relevance to modeling and performance evaluation

**Assessment: relevant topic, incomplete validation.** The questions concern comparative validity, workload representation, utility definitions and finite evaluation budgets, all appropriate performance-evaluation topics. The stronger presentation now connects implementation identity, observational support and reported ranking. The 27-page manuscript / 28-page acmsmall builds meet the conservative local ceiling without template modification.

The risk is that the paper reads as an audit of a flawed benchmark rather than a validated modeling contribution. ToMPECS relevance does not remove the need for a useful scientific result. A carefully delimited negative methodological case study might be viable, but that requires an explicit author decision and a stronger argument for transferable lessons; no acceptance can be assumed.

## 5. Evidence required for acceptance

Priorities, not an automatically launched campaign:

1. Decide the scientific object: an archival methodological case study versus a comparative serving study. The latter requires common-model comparability and new evidence; the former needs a precise contribution that remains valuable after giving up native ranking and significance claims.
2. Validate the execution and information contracts for whichever mechanisms the paper will interpret. Distinguish common resource constraints from policy decisions.
3. For inferential claims, define the sampling target, grouping/dependence assumptions, directional/practical hypotheses and complete multiplicity families prospectively. Demonstrate calibration appropriate to that design; alternatively keep results descriptive.
4. If native or synthetic transfer remains a promised result, obtain faithful evidence addressing original RQ3/RQ6 under separately authorized protocols. Historical runner counts cannot stand in for it.
5. Finish source eligibility/overlap/licensing, complete bibliography metadata and current artifact-accessibility review. These are necessary but do not replace scientific validation.

## 6. Remaining rejection risks

Even after correct formatting and honest qualifications: modest novelty; no validated portable selection rule; three-source/two-provider coverage; synthetic deadlines and trace token-semantic differences; only 200 requests/window; finite-reference recovery presented near “sample complexity”; policy abstraction confounds; incomplete native/synthetic transfer; post-campaign emphasis; and unknown overlap with related manuscripts. A referee may judge that removing overclaims leaves too little empirical insight for a full ToMPECS article.

The reported statistical corrections improve correctness, not automatically contribution strength. More pages, a prestigious format and perfect reproducibility are not solutions to comparability or external-validity defects.

## M3 recommendation (not launched)

Recommend an **author scientific-scope decision before M3**. If retaining the conditional historical case study, M3 should be a bounded contribution/overlap/bibliography and venue-readiness review with no new inference claims. If the author wants a defensible serving-policy comparison, M3 must first specify a separate common-model validation and evidence plan; any experiments require separate authorization. Do not proceed directly to submission polishing as though M2 removed these blockers.

Scientific readiness: **NO-GO for publication-level comparative/native claims; conditional descriptive author-review draft is defensible.**
Submission readiness: **NOT READY** (scientific scope/comparability plus publication-overlap, release, references, declarations and current venue requirements).
