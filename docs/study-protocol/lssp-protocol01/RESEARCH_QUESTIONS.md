# Research questions and contributions

**DRAFT.** Central question: when do LLM-serving scheduler rankings transfer across GPU architectures and parallelism configurations, and which measured system mechanisms explain their stability or reversal?

The experimental object is a **specified scheduling mechanism running in a pinned engine**, not a product name. A deployment includes accelerator, memory, topology, host, engine configuration and routing. Unless topology and host are controlled, an A100/L40 contrast estimates deployment transfer, not an isolated causal effect of GPU architecture.

## C1 / RQ1 — Validated mechanisms on physical systems

Can four distinct, independently specified scheduling mechanisms execute their intended decisions on real hardware throughout the declared workload domain?

Necessary evidence: specification before adapter implementation; an independent decision oracle; differential state-transition tests; metadata receipt; native scheduled-token and runner-progress records; completion/error accounting; per-rank or per-replica reconciliation where applicable. Include concurrent arrivals, multiple SLO classes, long prefill, decode-heavy work, overload, partial-prefill boundaries and KV pressure.

Primary measurements: decision/state mismatches, unsupported transitions, missing events, token conservation, admission and completion consistency. Analysis: conformance by semantic case and deployment, with deterministic counterexamples and randomized state-machine trials; zero observed violations is a gate, not a probabilistic correctness proof. Acceptance requires all mandatory cases to pass and at least one independently constructed distinguishing case for every policy pair. Unexercised paths remain NOT VERIFIED.

Contribution: a reproducible semantic evidence chain that makes a physical comparison interpretable. It does not invent SLAI, VTC, chunked prefill, or continuous batching; unit tests do not establish production reliability or physical equivalence.

## C2 / RQ2 — Controlled ranking portability

Do policy-pair advantages remain practically equivalent, concordant, reverse, or remain unresolved when moving between six fixed deployments?

Necessary experiments: paired windows and SLO assignments across all deployments/policies; two pressure regions; both common offered rates and reference-calibrated relative pressure; independent repetitions and allocation/day blocks. Primary measurements: request SLO goodput, paired normalized-goodput differences, deployment interactions, transfer regret. Analysis: simultaneous uncertainty, practical margins and descriptive Kendall tau-b, specified in [statistics](METRICS_AND_STATISTICS.md).

Acceptance is a complete, uncertainty-qualified transfer map meeting the frozen precision target, including stable and inconclusive cells. At least one reversal is **not** required. No claim of universally best policy, architecture-only causation, or independent-provider generality follows from this design.

## C3 / RQ3 — Mechanistic explanation

Do queueing, prefill/decode interference, collective communication, replica imbalance and KV constraints account for measured changes in policy advantage?

Necessary experiments: synchronized event instrumentation on all valid runs; outcome-blind selection of detailed profiles; controlled, paired interventions on a small predefined set of bottlenecks. Primary measurements: queue delay, scheduled prefill/decode tokens, decode gaps, phase duration, collective critical-path time, replica offered/served work and KV allocation/recompute events. Analysis: predeclared interaction models with window/block effects, out-of-sample predictive increment, followed by intervention contrasts.

Acceptance: clearly separate association from intervention-supported explanation. If no reversal occurs, test explanations of stability and effect-size changes. An explanation claim requires its predicted intermediate measurement and performance contrast to change together under the controlled intervention; unexplained variation is reported. GPU utilization alone, a post-hoc regression or a single attractive trace does not establish causality.

## C4 / RQ4 — Transfer or recalibrate

Can a small, observable set of workload and reference-deployment measurements identify when reusing a source ranking incurs acceptably small target regret?

Necessary experiments: lock a simple abstaining rule on development windows; evaluate it on untouched temporal blocks, with identical held-out windows across deployments; include always-transfer, always-recalibrate and pressure-only baselines. Primary measurements: false-safe transfer rate, regret, abstention/coverage and net calibration GPU-hours saved. Analysis: grouped held-out inference with uncertainty on all four, including probe/training costs.

Acceptance: a rule is practically useful only if its held-out error/regret limits and positive net savings are supported at the approved uncertainty level. Otherwise publish that portability cannot be certified cheaply. The target oracle is a retrospective evaluation comparator; the rule cannot access target policy rankings at decision time. No online scheduling-policy invention, universal transfer guarantee, or prediction for unseen GPU families is claimed.

## Expected evidence, not expected winners

| Question | Deliverable if successful | Legitimate negative result |
|---|---|---|
| RQ1 | Mechanism specifications, oracle fixtures and physical conformance ledger | Fewer than four mechanisms pass; main study is NO-GO |
| RQ2 | Transfer graph with stable/reversed/tied/unresolved labels and effect intervals | Rankings stable throughout the tested domain, or precision insufficient |
| RQ3 | Measured pathways and isolated intervention effects | Correlations do not survive controls or interventions |
| RQ4 | Locked rule, held-out risk/coverage and cost accounting | Recalibration remains necessary; error bound too wide |
