# Bounded M3 token-budget sensitivity

State: **COMPLETED_SUCCESS**. All 72 specified cells completed and were validated. No job remains running. Scientific outcome: the primary divergence hypothesis was rejected for this finite design; measurable secondary changes are modest. This is a completed negative/mixed sensitivity result, not a failed study or a claim of physical GPU performance.

## Scientific question, design and provenance

The exact primary hypothesis was: lowering only the work-token budget from 32,768 to 2,048 and 1,024 at eight resident slots makes chunked-FCFS and decode-first execute different per-request spans or batch memberships in at least one selected condition. The predicted mechanism was earlier resident prefills exhausting the budget before later ready decodes. Mere permutation of the span list does not count. Reject the hypothesis if every matched normalized journal and terminal state remains equal at both perturbed budgets.

The [prospective protocol](PROTOCOL.md) and initial runner were committed at `5630bfd` **before** any new simulation outcome. The branch starts at the actual PR #23 head, `4c08660eeb528a5a459800bbc79771f4b8e4dbfc`. The exact frozen engine/policy/referee execution commit is `2d8342e699f35044044ac518c0b75a3c4a1c768c`; no engine or policy was edited. The full frozen input file is SHA-256 `a77bf5420ca8a55c3765919dbf42e774794f471da6ff404d0ad19a53c43a8c8c`. All 720 condition request hashes were checked before execution.

The C01 engine is the separate `research/lssp-c01/engine.py`, not the historical `src/robustbench/simulator/simulator.py`. The latter's policy-dependent semantics must not be substituted into this study. The exact engine, policy, referee, input, protocol and runner hashes, condition seeds/factors, baseline result identities, and all new result/journal hashes are in [provenance.json](provenance.json).

Only budget changes within a matched comparison:

| Parameter | Baseline | Moderate | Restrictive |
|---|---:|---:|---:|
| Work tokens per batch | 32,768 | 2,048 | 1,024 |
| Batch duration | 1 ms | 1 ms | 1 ms |
| KV capacity / per-request context reservation | 262,144 / 32,768 | same | same |
| Resident slots / configured sequence limit | 8 / 64 | same | same |
| Allocation block / drain after final arrival | 16 tokens / 50 s | same | same |
| Chunk cap / urgency gate | 512 tokens / 0.495 s | same | same |

The four original adaptations are whole-FCFS, chunked-FCFS, decode-first and SLO-gated. All inputs retain their 200 requests, original outputs, priorities, deadlines, arrivals and synthesis seeds. No workload is resampled or truncated. The original LOW and HIGH_PRESSURE conditions supply two joint arrival/deadline settings; they are not new calibrated saturation points.

Selection is input-only: the first three lexicographically ordered BurstGPT windows with 512 < maximum prompt <= 1,024 are `burstgpt_pilot_v2_w16`, `burstgpt_pilot_v2_w23`, `burstgpt_pilot_v2_w28`; prompt maxima are 1,005, 790, 648. Their frozen synthesis seeds and per-setting load factors remain in the manifest and cell CSV. This is three unique windows (600 requests), six transformed conditions, three budgets and four policies: **72 cells / 14,400 completed request executions**, not 14,400 independent observations.

Budget choice follows the existing 512-token cap: 2,048 permits four maximum chunks and 1,024 permits two, below the eight-slot bound of 4,096; both still admit every selected whole prompt. The 12-cell pilot covers w16/HIGH_PRESSURE, all budgets and policies. It took 0.974 s; continuation took 5.330 s, including verified reuse of those 12 cells and 60 new executions. New raw evidence occupies about 6.4 MiB at `/home/soroush/artifacts/lssp-m3-budget-sensitivity-20261022`. Run identity: `f19883ccf2c41fdb8337ac1371bce78a6f8e7d29279d361255e5f7603aa5b5d5`. There is no Slurm/tmux job because execution was seconds, below the user's persistent-job threshold.

A first continuation attempt stopped before executing another cell because a JSON-saved list did not equal an in-memory tuple. Commit `d6407cd` fixes only resume metadata normalization, explicitly pins the compatible previous runner, and records the actual corrected runner hash. All scientific identities and pilot records remained unchanged. See [EXECUTION_NOTE.md](EXECUTION_NOTE.md). The partial analysis correctly refused the then-incomplete matrix. No failed scientific cell was dropped, replaced or silently retried.

## Model inspection and feasibility limit

* **Original mathematical equivalence:** each resident/newly admitted chunked request contributes at most 512 work tokens, and total selected requests cannot exceed the 4/8 reservation slots. The work bound is at most 4,096, far below 32,768. Chunked-FCFS and decode-first therefore execute the same spans from equal states, with shared batch-end timestamps and completion releases. Induction establishes equal state transitions; the original 1,440 matched conditions verify the consequence.
* **Original gate inactivity:** nonbinding work serves each ready decode every batch; prefill completion and each decode set the anchor to the batch end. At the next planning boundary anchor age is zero. Under these assumptions the 495 ms gate is structurally inactive, while prompt-length waiting admission remains active.
* **Admission/residency:** full-context reservation starts with first selected work; waiting requests reserve nothing. Completions release only after the batch, so no within-batch replacement. No preemption, eviction, migration or output-length prediction. Whole-FCFS admits feasible whole prompts in order and defers all decodes in any prefill-admission batch. Other policies permit inter-request prefill/decode sharing; no request emits output during its own prefill.
* **Previously consequential domain restriction:** every full prompt must be <= budget for **all** policies, including chunked policies. Maximum prompt in the frozen corpus is 29,067; preserving every input therefore requires budget >=29,067, which cannot bind the <=4,096 chunked-work bound. No intact Azure or Bailian window fits even 4,096 (minimum window maxima 6,180 and 5,773). Thus a full-corpus, budget-only test of the chunked equivalence mechanism is infeasible without an additional assumption/input change. This study honestly restricts to a feasible BurstGPT stratum.
* **New equivalence is observational:** the original sufficient bound no longer applies at the perturbed budgets. The new matches establish equivalence only on the selected runs; no stronger universal reachable-state theorem is claimed. Gate inactivity in those runs is measured, not inferred from the old zero-age proof.

## Results and negative findings

[All absolute metrics](cells.csv), [paired endpoint differences](effects.csv), [equivalence results](equivalence.csv), [ranking comparisons](rank-comparisons.csv), and [summary](summary.json) retain denominators and zero differences.

| Budget | Chunked/decode terminal and normalized-journal equality | Distinct terminal behaviors | Exactly full-budget batches, all labels |
|---:|---:|---:|---:|
| 32,768 | 6/6 | 3 in 6/6 conditions | 0/25,983 |
| 2,048 | 6/6 | 3 in 6/6 conditions | 3/25,986 |
| 1,024 | 6/6 | 3 in 6/6 conditions | 36/25,984 |

**H1 is rejected on all 12 perturbed matches.** Zero request terminal states differ between chunked-FCFS and decode-first (0/2,400 perturbed paired request states; 0/3,600 including baseline). Raw span order differs in 4/6 conditions at each budget, while normalized per-batch spans, membership, timestamps and terminal states agree exactly. Both policies serve every ready resident decode; binding changes prefill/admission progress without separating their executions on these inputs. No fourth effective terminal behavior emerges.

At 1,024, SLO-gated omits **42/35,976 ready-decode opportunities**, compared with zero at the other budgets. The maximum SLO anchor age is **2 ms**, below **495 ms**; urgent opportunities remain zero. Mean TPOT rises by at most **5.8655 microseconds**. This is a real service deferral, larger than floating-point noise but small in aggregate. Exactly-full counts include duplicate labels and are not independent trials; they do not count whole-prompt packing that leaves an unusable remainder. Saturation is rare in this selected operating region.

Ranges below are absolute changes from each policy's matched 32,768 baseline over six fixed conditions, not confidence intervals:

| Budget | Policy | Mean latency change (ms) | p95 latency change (ms) | Token throughput change (model tokens/s) |
|---:|---|---:|---:|---:|
| 2,048 | Whole-FCFS | [0, +0.565] | [0, +1.000] | [-10.931, 0] |
| 2,048 | Chunked-FCFS / decode-first | [0, +0.135] | [0, 0] | [0, 0] |
| 2,048 | SLO-gated | [0, +0.015] | [0, 0] | [0, 0] |
| 1,024 | Whole-FCFS | [-2.245, +2.560] | [-7.000, +4.000] | [-18.604, +18.332] |
| 1,024 | Chunked-FCFS / decode-first | [0, +0.520] | [0, +1.897] | [0, 0] |
| 1,024 | SLO-gated | [0, +0.365] | [0, +2.000] | [-4.503, 0] |

Whole-FCFS mean latency changes range from -1.558% to +1.216% at 1,024; throughput changes range from -0.353% to +0.3939%. Its whole-prompt packing changes which prefill batches exclude decoding, so effects need not be monotone in budget. SLO throughput falls by at most 0.0869%. Whole-FCFS ANWG changes by -0.005 to +0.010, SLO by -0.005 to zero, and the equivalent pair by zero. These correspond to one fewer through two more deadlines met among 200 arrivals, with uniform priorities.

There are **0/576 strict-10% practical reversals** across baseline/perturbation policy preferences: six conditions x two perturbations x six pairs x eight endpoints. All are eligible. Fourteen pairwise order classifications change after numerical-tie tolerance: ten TPOT and four ANWG comparisons, including duplicated chunked/decode comparisons. **5/96 numerical-tolerance top sets change**, all TPOT at budget 1,024 as SLO leaves a former tie. These are small differences, not substantive new ranking reversals. The prespecified one-millisecond/one-percent-throughput/one-request-ANWG screening rule and its endpoint flags are retained in the protocol/CSV; it is separate from the strict-10% reversal rule.

The original 5,760-cell results, 1,440 matched equalities, 0/2,376 original and **0/864 reduced source-mean reversals** remain unchanged. The sensitivity does **not** independently retest cross-source means. It supports persistence of the tested equivalence with modest secondary effects; it cannot establish robustness to long prompts, used-KV pressure, changing batch duration or arbitrary budgets. No bootstrap or population CI is justified by three input-selected, temporally related windows; paired full ranges expose heterogeneity without pretending deterministic repeats are independent samples.

## Manuscript changes

* New Section **5.6**, “A prospective token-budget sensitivity,” distinguishes the perturbed contract, records the hypothesis/design, reports rejection and secondary mechanisms, and states the full-corpus feasibility limit.
* New **Table 7** reports paired absolute latency/throughput ranges. Earlier tables and figures retain their original bytes and values; subsequent displayed table numbers shift through LaTeX cross-references.
* Abstract and structural contribution add a scoped statement that the 72-cell sensitivity preserves equivalence. Discussion/conclusion describe the modest result and restricted input domain. Related-work wording now distinguishes original nonbinding work from this sensitivity. Appendix B records the separate execution identity and metadata correction; README links this report.
* No bibliography additions or changed citation identities. No claims of GPU prediction, general equivalence at binding budgets, population inference or new scheduler optimality.

## Verification and visual review

* Existing repository regression suite: **378 passed**, 4 pre-existing numerical warnings, 41.40 s. Frozen C01 contract tests: **42 passed**, including corruption and deterministic replay tests.
* Every new cell passed the unchanged independent journal referee. All **24 baseline cells exactly match archived metrics and complete terminal records**. Independent terminal arithmetic covers all 72 cells, with maximum observed metric discrepancy **0**.
* A second implementation imports neither analyzer, engine, policy nor referee: verifies 72 saved results, 18 normalized event pairs, 384 endpoint effects, all 576 practical comparisons, 96 top-set comparisons, telemetry denominators, input-domain census and six displayed table rows. See [independent-verification.json](independent-verification.json).
* All seven derived output files regenerate byte-identically from raw local evidence. No simulation rerun was needed.
* Existing complete C01 oracle: **5,760 cells, 15,840 rankings, 95,040 pairwise records, 26,136 reversal groups**. All **54/54 scientific/preservation checks** pass; all **7,200 STAT01 endpoint rows** match. The original 8,208 reduced reversal groups reproduce; the 400-state/2,497-event worked example is freshly reconstructed. No claim is made to rerun all original raw campaign journals or synthetic studies.
* **63 frozen tracked assets** remain byte-identical. Protected hydrated datasets remain unchanged and uncommitted, including the original PR23 worktree. The scientific audit's `experiments_executed: 0` describes that saved-evidence checker, not this separate 72-cell experiment.
* Both revised PDFs are **26 pages**, with zero overflow, unresolved references/citations, or bibliography errors. All 28 citation keys resolve. Three inherited optional BibTeX metadata advisories remain. Rendered all-page contact sheets and inspected modified pages **1–3, 13–14, 18–19, 25** at readable resolution in both formats. Table 7, its units, signs, caption and numbering are legible; no clipping or text collisions found. Final PDF fingerprints are in [delivery-verification.json](delivery-verification.json).

## Reproduction and delivery

See [COMMANDS.md](COMMANDS.md) for exact commands and local logs. Derived manuscript evidence is committed; raw workload payloads and new journals remain local. No dataset/release artifact was published, manuscript submitted, editor contacted, or branch merged into main. Existing worktrees were preserved. The draft PR is stacked on `manuscript/lssp-m3-focused-editorial-20261022`; the delivery response records its URL and exact pushed SHA.

## Publication-readiness verdict

**Scientifically stronger and honestly bounded, but not an unconditional ToMPECS submission recommendation.** The study tests and rejects a plausible mechanism hypothesis rather than manufacturing a positive ranking result. It adds an executable feasibility boundary and distinguishes new decode stalls from an urgency gate that still does not activate. Those are useful explanatory improvements, but the modest effects, rare saturation, short-prompt selection, single-source support, restrictive fixed timing/residency model and unresolved older cross-project BurstGPT overlap remain substantive limitations. The full-journal novelty concern is reduced only modestly, not resolved. Complete artifact distribution and venue-specific readiness also remain separate pending work. Further experimental expansion is outside this bounded task.
