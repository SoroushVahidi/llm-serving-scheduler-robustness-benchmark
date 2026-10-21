# Metrics and statistical analysis

**DRAFT.** Numerical thresholds and split sizes need approval; no physical outcome is being analyzed in this protocol.

## Primary metric and cohort

Use **request SLO goodput**, G=Σᵢ successᵢ/T, in requests/second. T is the fixed duration of the scored arrival interval [0,T), chosen before replay; it is not each policy's completion time. Each offered request belongs to the cohort once. A success requires a valid complete response with the declared output-token work, TTFT within its class limit, **every observable inter-token gap** within its TBT limit, and completion within its E2E deadline. This strict gap criterion aligns with SLAI's TBT objective and prevents average TPOT from hiding long stalls; it is a proposed service contract, not an observed production SLO. Author approval of this choice and its length sensitivity is required.

Define λ=N_offered/T and Y=G/λ=N_success/N_offered. G is the primary ranking metric within a deployment/window/rate. Y gives the same within-cell ordering and a common scale for cross-pressure pair contrasts and the δ=0.05 practical margin. Report G and Y together; do not interpret normalized goodput as absolute capacity. Use request weights of one, equal class mix by design, and class-specific results; historical weighted ANWG is a secondary comparability analysis only.

Drain until the latest finite E2E deadline in the cohort (plus bounded log-flush grace), so every success is classifiable. A completion after T counts if before that request's deadline. The common denominator remains T. The metric is finite-cohort offered-load goodput, not a claim of steady-state throughput. Queue trajectory and prelude/window-length sensitivity must support any steady-state wording. Wall limits must permit the frozen drain; otherwise mark the execution administratively incomplete, never count only its early successful requests as a comparable complete run.

## Clock and event definitions

For every request record scheduled arrival a, actual client send s, router receipt r, engine admission/admission refusal, first scheduled prefill, each scheduled/executed token range, client first-token receipt f, every stream-event/token identity, final token l and terminal completion c. Define client TTFT=f−a, E2E=c−a, send lag=s−a, and decode gaps from consecutive token receipts. Report server-observed equivalents separately. Dispatch delay is not omitted by replacing a with s.

Use a monotonic clock within each process and record wall-clock mapping/offset uncertainty. Cross-host queue/communication attribution requires synchronized clocks or same-clock bracketed spans. Never subtract unrelated monotonic epochs. Stream events can contain multiple tokens; do not invent distinct token timestamps from one coalesced event. Validate token-level observability/server emission and transport buffering before using the all-gap primary contract. If that cannot be measured, revise and approve the primary contract before outcomes; do not silently replace it with mean TPOT. For one-token output, the gap condition is vacuously satisfied and TPOT is undefined, with count reported.

## Secondary measurements

| Domain | Measures and interpretation |
|---|---|
| User latency | TTFT, E2E, per-request mean TPOT, gap distributions and p95/p99; label successful-only conditional statistics and show failure fraction |
| Completion/service | Completion fraction, refusal/error/timeout rates, generated output tokens/s, request goodput/GPU, per-class SLO attainment |
| Queueing | Client send lag, router wait, engine wait, active/waiting trajectories, backlog at end, prelude/window boundary sensitivity |
| Prefill/decode | Tokens scheduled and actually progressed by phase; partial-prefill state; decode holds and gaps; batch-duration distribution |
| Communication | Collective type/bytes and critical-path duration on synchronized ranks; distinguish overlap from elapsed time |
| Routing | Per-replica offered tokens, admissions, queue delay and completed work; imbalance and routing decisions |
| KV | Allocated/free blocks, peak occupancy, failed allocations, victims, swap/recompute, shared-prefix behavior (off in primary) |
| Cost/startup | Allocated GPU-hours, initialization/readiness/compile time separately from warmed inference; energy only if independently instrumented |

Tail metrics require adequate observed samples and uncertainty. Report undefined quantiles/TPOT as NA, not zero. Always show all-offered success so survivor-only latency cannot reward dropping hard requests. No weighted composite is substituted for the primary metric after viewing results.

## Pairing and hierarchy

Average repetition effects within each window **after pairing identical request inputs**. The independent scientific units are nonoverlapping temporal blocks/windows, not requests, tokens, policy cells or repetitions. Cluster adjacent windows sharing a temporal/session block; preserve all policy/deployment/pressure versions when resampling. Sources are three fixed strata, with related provenance; do not estimate a population of independent providers from three labels. Report per-source inference first and an equal-source-weight pooled summary second.

Fit a prespecified paired-effect model with policy×deployment×pressure terms and fixed source strata, plus window and allocation/day effects as supported by replication. Node effects are conditional when only one node is available. Estimate contrasts directly from paired window effects as the primary analysis; use the model as adjustment/sensitivity, not to replace missing paired cells with unexplained predictions. If allocation/day clusters cross temporal blocks, use a crossed-cluster resampling/model sensitivity; simple request bootstraps are prohibited. Report effective cluster counts and nonexchangeable timing confounds.

## Uncertainty, multiplicity and ranking labels

Primary relative-pressure family: 4 policies give 6 unordered pairs; 7 transfer edges ×3 sources ×2 regions give **252 interaction contrasts**. Joint endpoint advantages comprise 6 pairs ×6 deployments ×3 sources ×2 regions = **216 contrasts**. Freeze these **468** contrast definitions as one family for simultaneous 95% inference, so reversal and stability labels are not selected from uncorrected endpoints. If factors change before freeze, regenerate the family explicitly.

Recommended procedure: a paired, hierarchical, studentized max-|t| bootstrap over independent temporal blocks, preserving the entire contrast vector and within-block repetition/day pairing; 10,000 resamples with a frozen seed. Validate type-I error and coverage using synthetic null, heteroskedastic, tied and cluster-correlated outcomes before the main analysis. Small effective cluster counts or zero-variance contrasts can invalidate this approximation: report deterministic/degenerate cells directly, use a prespecified conservative simultaneous interval sensitivity, and label unsupported inference inconclusive. This is not a finite-sample guarantee. A statistician should approve the final estimator and cluster design at freeze.

The equal-arrival-rate view is a separate, labeled secondary family with the same correction rule. C3 intervention tests use Holm family-wise control across the frozen mediator/performance contrasts. Exploratory feature screening may use BH FDR but cannot establish confirmatory mechanisms. C4 risk/coverage/cost acceptance uses simultaneous bounds across its frozen criteria (allocate α across them). Do not pool a favorable unadjusted secondary result into the primary conclusion.

For each policy pair and transfer edge:

- **Practical reversal:** both endpoint intervals exclude ±δ in opposite directions.
- **Concordant preference:** both endpoint intervals exceed δ in the same direction; this does not require equal advantage.
- **Equivalent advantage:** the interaction interval lies entirely within [−δ,δ]. Separately report whether either endpoint has a supported preference.
- **Practical tie:** an endpoint advantage interval lies entirely within [−δ,δ].
- **Inconclusive:** remaining cases, including insufficient precision. Failure to reject zero is not equivalence.

A complete portable ordering requires all relevant pair relations to be resolved consistently; otherwise publish a partial order. Compute descriptive Kendall tau-b on prespecified mean-G rankings at each rate view, with exact ties and paired-window bootstrap uncertainty. With four policies there are only six pairs; tau has low resolution. If either ranking is all tied, tau-b is undefined. Practical pairwise indifference is not automatically a transitive tie group: report the partial-order graph rather than arbitrarily merging near ties. Add top-policy regret/selection uncertainty; never use tau alone to certify transfer.

## Failures, exclusion and censoring

Policy refusals, genuine overload, server-side request errors, policy-triggered crashes and request timeouts count as unsuccessful offered requests. If a policy crashes under a valid input, all remaining scheduled requests in that finite cohort are failures and availability loss is reported; retain the crashed run. A checked-adapter semantic mismatch instead invalidates the contract: stop the affected comparison, retain the record as a fidelity failure, and do not manufacture a ranking from invalid semantics.

Infrastructure loss unrelated to treatment (e.g. node failure) yields a labeled administrative incomplete block, not a zero-performance policy result. Keep all evidence; any replacement requires explicit stage authorization, uses the same cell/seed, and is reported beside the original. No automatic retries are authorized. Use paired complete blocks for the primary valid-system estimand, report missingness by policy/deployment, and provide pessimistic/optimistic outcome bounds for missing blocks. Treatment-dependent missingness cannot be cured by complete-case filtering.

For latency, deadlines/timeouts are right-censoring or terminal failures, not fabricated completion times. Report empirical deadline-attainment curves with unresolved mass and, where justified, restricted-mean/censoring analysis with its assumptions. Do not assume independent censoring for overload-related failures. Primary success is zero once its deadline is missed even if later completion is observed. Frozen invalid-input exclusions must be outcome-blind and quantified; rejection of an otherwise eligible request is an outcome, not an exclusion.

## Held-out portability rule

Start with a small, interpretable rule: transfer only where reference-calibrated pressure shift, workload length/burstiness and a small communication/KV probe vector lie inside training support and a learned conservative regret bound is below δ; otherwise abstain and recalibrate. Freeze feature definitions and at most three predictor groups before fitting. Compare to always-transfer, always-recalibrate and a pressure-only rule. No target candidate-policy latency/goodput may be a predictor. Target native-reference probes are permitted, with their cost disclosed.

All window versions remain in one chronological split; tune only with grouped inner validation on development data. Lock coefficients, thresholds and hashes before opening the held-out target outcomes. Held-out windows must differ from historical, calibration and development windows. Evaluate source-selected policy regret against the target best policy using repetition splits/cross-fitting to reduce optimistic target-winner selection, with uncertainty for both. Also evaluate full-order transfer separately. A leave-one-target-deployment-out stress analysis is useful, but six configurations from two architectures cannot establish generalization to unseen GPU families.

False-safe means the rule says transfer but target regret exceeds δ. Report its conditional risk among accepted transfers, acceptance coverage, regret distribution and net measured GPU-hours saved. Independent decision clusters, not all overlapping edges/windows, determine uncertainty. With zero errors, even a simple unadjusted independent-binomial 95% upper bound below 5% requires at least 59 accepted independent decisions; simultaneous and clustered inference may require more. Eight windows/source is therefore not automatically enough for C4. If precision cannot support the risk claim, label the rule exploratory and retain C1–C3 as the main contribution.
