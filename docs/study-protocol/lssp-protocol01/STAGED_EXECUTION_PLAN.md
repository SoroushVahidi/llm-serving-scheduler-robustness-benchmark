# Staged execution plan

**DRAFT — all future GPU work requires separate authorization.** A stage's GO means its scientific prerequisites are met; it is not permission to submit. This protocol adds no submission scripts and launches no experiments. The historical 24/144 designs are not automatically authorized.

| Stage | Purpose and bounded scope | GO evidence | NO-GO / stop conditions | Current status |
|---|---|---|---|---|
| 0: MGPU03 | One approved MGPU02 smoke, already submitted historically | Independent physical review of all 11 smoke acceptance requirements: full identity, load/readiness, both valid inference paths, received class metadata, active mechanism, expected/observed decisions, supported boundaries, clocks, errors/timeouts and durable provenance | Any failed or unverified required acceptance item; completion/exit zero alone insufficient | Accounting COMPLETED; physical acceptance NOT VERIFIED in this review |
| 1: repeated A100 validation | **24 executions = 2 policies ×3 diagnostic fixtures ×4 independent repetitions**, one full A100 | Stage 0 PASS; all 24 satisfy conformance/accounting; repeated timing/provenance usable; replay jitter and instrumentation criteria met | Decision/state mismatch, partial/KV event outside bounded contract, missing responses/events, inability to reproduce metadata | NO-GO pending Stage 0 review and explicit authorization |
| 2: additional fidelity and distributed eligibility | Specify/implement four mechanisms; long-prefill/KV cases; validate A100 TP2/DP2 and L40 single/TP2/DP2 eligibility; separate calibration/variance pilot on approved small cells | F0–F9 for all policy/deployment combinations, distinguishability fixtures, declared coverage, main model fit, routing/collective correctness; usable nuisance-variance/runtime estimates | Fewer than four distinct faithful mechanisms; unsupported required domain, model/context infeasible, topology identities uncertain or physical checks absent | NO-GO; implementation and approval required |
| 3: main study | Frozen balanced paired factor set; pilot-selected W/R, two load views; locked held-out split; full provenance | All Stage 2 gates; author-approved immutable preregistration/hash; valid statistical precision plan; resource cap and stop rule approved; public-version overlap reconciled | Missing freeze fields, insufficient budget for required precision, hidden exclusions, semantic drift, broken input identities | NO-GO; manifest is intentionally non-executable |
| 4: focused extensions | Mechanism interventions, scale/second-model robustness and held-out transfer evaluation as specified below | Separate hypotheses/contrast/intervention/split freeze before their outcomes; all new contracts validated; bounded incremental budget approved | Post-hoc favorable subset presented as confirmatory, unsupported topology/model, overlapping held-out training data | NO-GO pending design freeze and authorization |

Stage 1 fixtures are engineering tests: (i) concurrent arrivals with all three classes, (ii) whole-prefill boundary/prefill–decode contention with prompts at 256, and (iii) decode-heavy work with held decodes and queued arrivals. Negative metadata/unsupported cases are additional gate checks, not successful serving runs in the 24. These are synthetic bounded fixtures, **not** three representative trace sources or a ranking campaign. Counterbalance native/SLAI order over four repetition blocks; no winner-dependent changes. The final fixture bytes and output limits must be approved before execution.

Stage 2 begins with CPU specification/oracle work before any GPU allocation. Freeze per-contract failure cases, then separately authorize only the minimal conformance and calibration cells needed. Do not infer TP2 support from vLLM documentation or DP2 support from two independently working TP1 processes. Main-size model and expanded semantics require new physical evidence even if Stage 1 passes.

## Minimum credible evidence set

For the requested C2 scope the irreducible factor set is all **6 deployments ×4 independently distinct policies ×3 sources ×2 pressure regions**. Within each cell, W independent temporal blocks/windows and R real repetitions must satisfy the precision/power procedure in [RESOURCE_BUDGET.md](RESOURCE_BUDGET.md). W=8 and R=3 yield the illustrative 3,456 count; this is neither a power result nor an automatic minimum. Prefer additional independent windows over redundant repetitions once within-window noise is small. No fixed low run count can be called adequate without a variance estimate.

The smallest engineering milestone is Stage 0 acceptance plus the 24 Stage 1 executions and Stage 2 conformance tests. It cannot establish C2–C4. A budget-limited single-A100 or two-policy screen may inform engineering but requires a narrower research question; it must not inherit the six-deployment claims. For the full proposed journal contribution, add a prespecified profile subset and at least one independently confirmed mechanism intervention, plus a held-out transfer-rule evaluation with sufficient decision clusters. If C4 precision is unaffordable, publish it as exploratory rather than certify unsafe transfer.

Equal-arrival-rate comparisons and mechanism interventions are planned parts of the evidence, not automatically included in 3,456. Development, calibration and detailed profiles also consume resources. Stage 4 can be planned before Stage 3 and executed afterward; exploratory observations may generate additional hypotheses only in a clearly labeled amendment tested on new data.

## Optional extensions and incremental value

| Extension | Additional scientific question | Admission gate / limitation |
|---|---|---|
| A100 TP4/DP4 | Does the two-GPU transfer boundary persist with larger collective/replica scale? | Validate ranks/route/topology and matched aggregate-budget controls; not a substitute for L40 evidence |
| Second dense model | Are mechanism/transfer effects specific to model shape and KV heads? | Outcome-independent model selection, immutable weights and independent fit/semantic gate; no selective “supportive” model |
| PP or dynamic parallelism | Do bubbles or adaptation change scheduler-transfer conclusions? | New scheduling/time model and references; distinct factor from fixed TP2/DP2 |
| Multi-node | Do network bandwidth/latency and failure boundaries change transfer? | Explicit network/placement controls and clock synchronization; separate budget and contract |
| Prefix-cache/real text | Does reuse/locality alter the ordering? | Authentic reuse mapping, verified source fields, caching-state control; cannot derive from arbitrary synthetic text |
| Focused routing/chunk/KV interventions | Can an observed association survive a controlled perturbation? | Freeze mediator, direction and magnitudes; negative controls; independent confirmation data |

Select detailed profiles by source×pressure×deployment strata before looking at rankings. A reversal-selected case study is allowed only as exploratory and needs new matched confirmation data for a causal claim. The absence of a reversal does not cancel mechanism or stability analysis.

## MGPU03 read-only status

One `sacct` query during protocol preparation returned job **1435222**, node **n0046**, state **COMPLETED**, exit **0:0**, elapsed **1010 s**, allocation **one A100, 16 CPUs, 32 GiB host memory**. Accounting start/end: 2026-10-21 15:40:04–15:56:54 in the Slurm display timezone (EDT in the prior submission record; 19:40:04–19:56:54 UTC). Submission was recorded at 19:38:02 UTC. Execution commit: `4332b08b17e5b789e20a4fe042a6b007f0d43dd6`.

Evidence: [accounting output](evidence/mgpu03_accounting.txt); [prior PR #1 submission record](https://github.com/SoroushVahidi/llm-serving-scheduler-robustness-benchmark/pull/1#issuecomment-6324936268). Persistent serving output directory:

`/project/ikoutis/sv96/github/llm-serving-scheduler-lssp-mgpu02/artifacts/mgpu02/physical-smoke/job-1435222`

Submission/preflight evidence directory:

`/project/ikoutis/sv96/github/llm-serving-scheduler-lssp-mgpu02/artifacts/mgpu03`

No MGPU03 serving summaries, scheduler verdicts or performance outcomes were used here. Slurm completion is not COMPLETED_SUCCESS for physical acceptance. Separate later read-only status command:

```bash
ssh -T wulver '/apps/slurm/current/bin/sacct -n -P -j 1435222 --format=JobID,State,ExitCode,ElapsedRaw,AllocTRES,NodeList,Start,End'
```
