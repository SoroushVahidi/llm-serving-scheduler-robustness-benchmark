# LSSP-STAT01 protocol1.0 — prospective statistical calibration

Freeze before scientific simulation. Synthetic scores only; no observed LLM-serving outcome enters the generator. One metric/load-region family per independently generated study, matching the historical within-family size. Not a calibration of provider sampling or native scheduler comparability.

## Population and truth

Three sources s=0,1,2;11 policies j=0,...,10; n=40 windows/source unless explicitly specified. A study draws a3×n×11 latent outcome array Y with population means μ_sj>0. Larger scores are better. Scores are continuous synthetic measurements, not bounded ANWG unless the scenario explicitly says bounded. Sources are independent in this design; policies and windows need not be. Each study is independent of every other study.

One family consists of all C(3,2)×C(11,2)=165 unordered source-pair/policy-pair hypotheses, fixed before observations. For h=(s,t,a,b):

* Sign reversal alternative A_sign: (μ_sa−μ_sb)(μ_ta−μ_tb)<0. Its null is the complement, including exact ties.
* Primary practical reversal alternative A_prac: [μ_sa>1.1μ_sb AND μ_tb>1.1μ_ta] OR [μ_sb>1.1μ_sa AND μ_ta>1.1μ_tb]. Its null is the complement. Equality at10% is null. Positive population means make this equivalent to the historical losing-value population margin, but the historical procedure does not actually test this null.

Both truth labels are independently enumerated from decimal/rational mean specifications. Primary false discoveries use A_prac; secondary sign-truth results distinguish failure of practical-effect inference from sign inference.

## Generator

Let C(ρ)=(1−ρ)I+ρ11'. Temporal covariance R is I (IID), block diagonal with independent5-window blocks having within-block correlation0.7, or AR(1) with R_ij=0.7^|i−j|. For each source draw independent standardized innovations Z_common and Z_policy, form U=sqrt(ρ)Z_common+sqrt(1−ρ)Z_policy, and Y_s=μ_s+σ_s L_R U. L_R is the fixed lower Cholesky factor. Thus E(Y)=μ and Cov(vecY_s)=σ_s² R⊗C for every innovation distribution. Default σ=.15, ρ=.5. Innovations are standard normal; heterogeneous-distribution scenarios use normal / Student-t5 scaled by sqrt(3/5) / (exp(N(0,1))−exp(.5))/sqrt(exp(2)−exp(1)). Bounded scenarios use Uniform(−sqrt3,sqrt3), IID windows,σ=.08; their configured means imply Y∈[0,1] analytically. No clipping, winsorizing or post-outcome generator changes.

Means: equal=.5 throughout; stable=.5+.01j at every source; near tie=.5+.0002j; reversal(δ): source0 policies0/1=.5±δ/2, source1 swapped, all other means=.5. Boundary: source0 policies0/1=.55/.5, source1=.5/.55, all others=.5.

Frozen scenarios (all n40 except final row):

| ID | Mean / distribution / temporal / missingness variation |
|---|---|
| iid_equal_null | Equal, Gaussian IID |
| iid_stable_null | Stable ordering, Gaussian IID |
| iid_near_tie_null | Near ties, Gaussian IID |
| exact_ties_null | Equal, Gaussian IID,ρ=1: policy outcomes identical |
| practical_boundary | Boundary means, Gaussian IID |
| small_sign_reversal | δ=.03, Gaussian IID: sign reversal but below practical threshold |
| medium_reversal | δ=.10, Gaussian IID |
| large_reversal | δ=.30, Gaussian IID |
| block_null | Equal, Gaussian independent5-window blocks |
| block_reversal | δ=.15, same block structure |
| ar_null | Equal, Gaussian AR(.7) |
| ar_reversal | δ=.15, Gaussian AR(.7) |
| unequal_variances | δ=.15, Gaussian IID,σ=(.08,.25,.15) |
| mixed_distributions | δ=.15, IID, same unequal σ, source innovations normal/t5/lognormal |
| mcar_reversal | δ=.15, Gaussian IID; each policy/window observed independently with probability.8 |
| selective_null | Equal, Gaussian IID; source0 policy0 missing when Y<μ, source1 policy1 missing when Y<μ; all others observed |
| bounded_reversal | δ=.30, uniform bounded IID construction |
| bounded_reversal_n400 | Same bounded construction, n400 |

Selective missingness changes observed-support targets while the primary truth remains the unconditional latent μ. No observed-data procedure is endorsed as identifying missing unconditional means without additional assumptions. Retain latent Y and observation masks in raw outputs; never replace unobserved outcomes in an analysis with their latent values. Oracle covariance uses known covariance parameters, **not latent outcomes**.

## Procedures (α=q=.05; historical B=2,000)

1. **historical_screened_BH:** separately observed policy means; same sign/tie excluded; opposite signs must each have |difference|/|loser|>.1, zero loser unestimable. For each eligible side, bootstrap matched observed per-window differences2,000 times; percentile95% interval and p=min(1,2min(P_boot(mean≤0),P_boot(mean≥0))). Combine max(p_s,p_t). BH only across screened records; discovery also requires both intervals exclude zero. Shared per-study stream in frozen source-pair/policy-pair order. New seed hierarchy, not historical seed0 or its preceding ranking draws. Synthetic-fixture equivalence to historical code required.
2. **historical_full_BH:** same actual screened p-values, untested=1; BH over165. Diagnostic: selection and uncalibrated components remain.
3. **historical_plus1_BY:** same screened stages, p_tail=min(1,(2000*p+2)/2001) before max; untested=1; BY over165 with H_165. Diagnostic, not assumed valid.
4. **iid_t_Holm:** matched paired contrast Z=Y_a−1.1Y_b and its reverse; one-sided Student t for mean>0. For each orientation take max of the two source components; undirected p=min(1,2min(p_orientation1,p_orientation2)). Holm over all165, no point screen. Finite-sample justification for Gaussian IID complete/MCAR paired samples; diagnostic under temporal dependence, nonnormality or selective missingness.
5. **cluster_t_Holm:** same construction on independent5-window cluster averages, retaining only completely observed clusters for each pair. Exact for Gaussian IID/independent-block complete or MCAR data; diagnostic for correlated clusters, nonnormality or selective missingness. Fewer than2 complete clusters means no test, p=1, CI absent.
6. **oracle_normal_Holm:** same IUT/orientation/complete-family construction with the known covariance of the observed matched sample mean: Var(meanZ)=σ_s²(c'C c)×sum(R_observed)/m². Normal upper-tail tests. Exact under Gaussian complete/MCAR generation including AR; diagnostic for nonnormal/selective missingness. An oracle benchmark, not a deployable procedure when covariance is unknown.
7. **group_bootstrap_BY:** resample whole nonoverlapping5-window groups jointly across policies, B=2,000; retain pair matching/masks. Component p=(1+#(bootstrap contrast mean−observed contrast mean≥observed contrast mean))/(B+1), centered at the null boundary. Same IUT/orientation combination; BY full165. Zero-observation resamples cause that component to abstain (p=1), never silently disappear. Diagnostic/asymptotic candidate even when groups are independent; no finite-sample guarantee asserted. For AR this block length is a deliberately imperfect approximation, not a tuned choice. Finite p-value resolution and power limits remain explicit.
8. **bounded_Hoeffding_Holm:** only bounded IID scenarios. For Z=Y_a−1.1Y_b∈[−1.1,1], p=exp(−2m max(meanZ,0)²/2.1²); same IUT/orientation and Holm. Distribution-free finite-sample justification for independent bounded observed samples, no selective missingness. Abstains outside its stated domain. Conservative power is a scientific finding, not a reason to change the bound.

Two orientations are multiplicity-corrected explicitly; taking a max alone does not test the union of possible directions. Holm needs valid marginal p-values but no comparison independence. BY similarly needs valid marginal p-values. Source/policy comparisons overlap and are not treated as165 independent observations.

## Coverage and ranking endpoints

Retain every method's165-element rejection vector and component diagnostics. Study-level R=#discoveries,V=#false discoveries; FDP=V/max(R,1), FDR=E(FDP), familywise false-positive probability=P(V>0), null rejection fraction=V/#nulls, power=(R−V)/#alternatives when alternatives exist. Report both practical and sign truth. Replicate indices, not individual hypotheses, are the independent Monte Carlo units.

Coverage: fixed predeclared source0/policy0−policy1 unconditional mean difference. Historical percentile interval is additionally computed unconditionally in a separate diagnostic stream (not inserted into its discovery procedure); also retain whether and how often actual screened intervals cover their targets, explicitly selection-conditional. Other methods produce ordinary95% difference intervals using their t/normal/Hoeffding/bootstrap construction, with missing/undefined intervals recorded. Marginal diagnostic coverage and interval availability are separate; no assumption that post-selection coverage equals95%. Missingness bias in separate versus matched means is recorded for the fixed contrast.

Ranking ties: preserve population maximizer sets and empirical exact-maximizer sets and lexicographic choice. For analytic methods additionally retain candidate-best sets, excluding a policy only when some competitor's one-sided zero-margin dominance test passes Bonferroni α/[3×11×10]. Under valid component assumptions these sets simultaneously contain all population maximizers with probability≥.95. Exact empirical ties are not confidence sets. Report set containment, size and deterministic-ID correctness separately; no selected tolerance tuned to the results.

## Monte Carlo design, precision and stopping

Master seed2026102201, NumPy PCG64/SeedSequence with explicit scenario index, replicate index and stream ID; separate streams for generator, missing mask, historical bootstrap, grouped bootstrap and unconditional coverage. Workers and resume order must not affect a replicate. Retain generated arrays/masks and per-study method results, not just aggregates.

Batches of25 independent studies. Prespecified analysis looks at500,1000,2000,4000,8000 completed studies **per scenario**; maximum8,000. Stop a scenario early only when simultaneous Monte Carlo uncertainty half-widths meet: practical FDR/FWER/null rejection fraction≤.025; ordinary95% coverage≤.03; power≤.08 where defined. Coverage precision is required for available unconditional diagnostic intervals, not the rare selected intervals. Never stop because results favor a method or achieve nominal calibration.

At each look use a two-sided empirical Bernstein bound for bounded study-level endpoints X∈[0,1]: b=sqrt(2s² log(4/δ)/N)+7log(4/δ)/[3(N−1)]. Allocate δ=.05/(18×8×16×5), covering up to16 reported bounded endpoints/method/scenario and all5 looks; use clipped [mean−b,mean+b]. No independence among endpoints is needed for this union bound. Conditional interval coverage uses only studies emitting an interval, with available counts and the same bound; the IID emitted-study distribution is explicit. This prespecified finite-look correction protects reported MC bounds after precision stopping. Report ordinary MCSE separately, not as the stopping guarantee.

Operational decision: empirical calibration concern if the simultaneous lower bound for practical FDR exceeds.05, or ordinary nominal95% interval coverage upper bound is below.95. Mark empirical compatibility-with-tolerance only if FDR upper≤.06 and coverage lower≥.94 on relevant assumption-valid scenarios; otherwise inconclusive. These tolerances are screening criteria, not mathematical guarantees or universal validation. Oracle benchmarks, abstention and diagnostic scenarios cannot establish a deployable procedure's validity by themselves.

One CPU Slurm job,4 CPUs,8GiB, general/standard account ikoutis, maximum09:00:00. At most4 worker processes, BLAS threads1. Stop starting batches at8h45m; finish in-flight batches/checkpoint, exit with an explicit time-budget status if incomplete. Per-scenario precision stopping, maximum-count stopping and time-budget truncation are distinct statuses. No automatic additional job. Unique immutable batch artifacts, hashes, exclusive run lock; resume only validated completed batches. No silent recalculation of corrupt output. Monitor startup≤120s then return control; no C01 inspection/interference.

## Primary references and interpretation boundary

[Benjamini–Yekutieli2001](https://doi.org/10.1214/aos/1013699998) supplies the dependence-aware multiplicity context; valid p-values remain necessary. [Hoeffding1963](https://doi.org/10.1080/01621459.1963.10500830) supports the bounded independent-sample tail bound. [Maurer–Pontil2009, Theorem4](https://www.cs.mcgill.ca/~colt2009/papers/012.pdf) supplies the empirical Bernstein bound; applying it to1−X and union-bounding the prespecified looks yields the stated two-sided MC accounting. The IUT/orientation argument and Gaussian contrast variances are explicitly derived above. Finite synthetic scenarios cannot prove universal validity or repair historical sampling/comparability assumptions.
