# M3 urgency-mechanism investigation

State: **COMPLETED_SUCCESS**. Supported interpretation: **C**, strengthened by a structural inactivity certificate. No new scientific pilot/campaign was run; no policy, engine, workload or deadline was modified. Existing frozen records and engineering boundary tests distinguish a functioning branch from a reachable mechanism.

## 1. Exact explanation

An arrived, unfinished request is critical precisely when it is resident, fully prefilled, has a defined anchor, and the actual comparison `now - anchor >= 0.495` succeeds. The anchor is the **end of final prefill or the last executed decode**. Each successful decode resets it; an omitted decode does not. A waiting request and a resident still in prefill are ineligible, regardless of how long they have waited. Large TTFT or completion latency therefore does not imply token-gap urgency.

In the original contract, selectable work is at most 512K <=4,096 tokens for K<=8, against a 32,768-token budget. Every ready decode executes. Its anchor equals the next planning clock, giving zero age and a structurally inactive positive threshold. No idle jump occurs while such a request remains unfinished.

In the binding-budget sensitivity, finite available prefill work supplies a stronger explanation than the observed 2ms maximum. Let P denote total prompt work, B the integer work budget, K the residency bound, and delta the fixed batch duration. Before a putative **first** critical decision, each batch omitting the candidate resident decode must exhaust B: otherwise the residual-decode loop would serve it. At most K-1 other decodes consume one token each, so that batch consumes at least B-(K-1) prefill tokens. Without recomputation, m consecutive omissions satisfy:

`m [B-(K-1)] <= P`, hence `age <= delta floor(P/[B-(K-1)])`.

If this bound is strictly less than 495ms, first activation is impossible. For the existing 200-request windows, the common-domain rule prompt<=B gives P<=200B. With B>=1,024, K<=8 and delta=1ms, the resulting bound is at most **201ms**. The three selected windows have the tighter certificates below. These are mathematical sufficient certificates under the stated contract, not estimates or confidence bounds. Failure of a certificate would not prove activation. The assertion is not about every configuration or arbitrary policy accepted by the engine.

The calculation uses integer token accounting and rational milliseconds. Independent checks also verify that observed floating-point batch durations times the conservative bound remain strictly below 0.495s. Rounding at exactly 495ms is immaterial to the large certificate separation.

## 2. Specification and implementation agree

The frozen C01 `policies.py` exactly implements the protocol's fixed 495ms age rule and priority order: critical decodes, resident prefills, waiting prefills sorted by prompt length, residual decodes. Engine anchors are updated only on acknowledged final prefill and executed decode. No reset-on-deferral or missing-comparison defect was found.

The 495ms literal is explained in the C01 protocol as a uniform 500ms token-gap allowance minus a 5ms margin. **It is not a configurable C01 operating parameter.** Neither Config nor View contains an SLO/TBT, deadline, threshold or estimated-service field. Actual/remaining output length is hidden; it only affects engine completion and future reservation release. Prompt length affects eligibility, demand and admission. Residency controls competition, not the threshold.

Synthetic completion deadlines are finite-valued metric inputs, used for ANWG. They do not enter the scheduling view. Changing them alone leaves every event and terminal time unchanged, although ANWG and its rankings can change as the evaluation criterion changes. This would not demonstrate urgency control. The historical `slai_faithful` class has configurable TBT classes/offsets and a different clock convention; it is a distinct implementation and cannot silently replace C01. Agreement here means agreement with the declared C01 adaptation, not reproduction or validation of full native SLAI.

Three supplied-state engineering checks verify the exact threshold: the adjacent representable value below 0.495 remains noncritical, equality is critical, and the adjacent value above is critical. In a deliberately aged online state the critical decode receives priority, displacing one prefill token. This is a branch test, **not evidence of a reachable active operating region** on the frozen inputs.

## 3. Recorded decision about experiments

[STRUCTURAL_FINDINGS.md](STRUCTURAL_FINDINGS.md) was committed at `c99dce3` before the [experiment decision](EXPERIMENT_DECISION.md). It records the implementation/specification inspection, proof, candidate numerical bounds and claim audit.

No baseline/moderate/strict SLO experiment is preregistered or performed because the requested isolated scheduler control is absent. Varying metric deadlines cannot exercise the mechanism. Replacing the fixed literal, importing historical constructor settings, assigning new request classes, changing timing or changing budgets would alter the authorized comparison. No alternative policy is invented. A hypothetical smaller positive threshold would also remain inactive under the original nonbinding contract; zero/negative thresholds are not introduced merely to trigger a branch.

Thus no new activation/performance trade-off is claimed. Whether a separately parameterized contract has a scientifically useful active region remains untested and would require a separate decision. Existing observations are not relabeled as a newly executed sensitivity.

## 4. Saved-evidence findings

The audit retains exactly the existing PR24 selection: BurstGPT `pilot_v2_w16`, `w23`, `w28`; LOW/HIGH_PRESSURE; eight resident slots; original budgets and unchanged seeds/configurations. Its 18 SLO-gated cells were already part of the 72-cell study. No new source sampling occurs.

| Budget | SLO cells | Batches | Ready-decode opportunities | Urgent opportunities | Omitted opportunities | Maximum anchor age |
|---:|---:|---:|---:|---:|---:|---:|
| 32,768 | 6 | 6,720 | 35,934 | 0 | 0 | 0ms |
| 2,048 | 6 | 6,720 | 35,934 | 0 | 0 | 0ms |
| 1,024 | 6 | 6,722 | 35,976 | 0 | 42 | 2ms |

Total: **0/107,844 urgent ready-decode opportunities**, and **0/20,162 batches** with an active gate. The 42 omissions at 1,024 comprise **10 before first output and 32 between outputs**; the maximum consecutive omission count is two. Admission and residual-prefill priority, not executed urgency, produced these deferrals.

| Window | Total prompt work P | Inactivity bound at B=2,048 | Inactivity bound at B=1,024 | Observed maximum age at B=1,024, both settings |
|---|---:|---:|---:|---:|
| w16 | 39,300 | 19ms | 38ms | 0ms |
| w23 | 52,250 | 25ms | 51ms | 2ms |
| w28 | 44,765 | 21ms | 44ms | 1ms |

The general finite-work formula also yields a loose 1ms bound for these windows at budget 32,768; the original nonbinding argument proves the tighter zero-age result. Certificates are deliberately distinguished from observed maxima.

Completed inter-output gaps meet the declared 500ms allowance in **34,734/34,734 gaps at each budget**. Their observed maximum is 1ms at 32,768/2,048 and 2ms at 1,024. The longest final-prefill-to-first-output gap at 1,024 is 3ms; this includes the next batch's execution and is not TTFT from arrival. These are model token-gap measurements, not the synthetic completion-deadline ANWG or production SLO compliance. The omitted opportunities and gaps are dependent repeated observations, not independent trials.

No new mean/tail latency, throughput or ANWG intervention effects are estimated. PR24's unchanged results still show three terminal behaviors, chunked/decode equality in all 12 perturbed comparisons, and 0/576 strict-10% preference reversals. The original common-contract source-mean results remain separate, including 0/864 reduced reversals. The certificate concerns urgency reachability; it is **not** a new general proof of chunked/decode equivalence at binding budgets.

## 5. Scientific interpretation and manuscript changes

The supported outcome is C for the examined assumptions, with no implementation/specification inconsistency (D). Outcomes A and B are not established by an unreachable supplied-state fixture. No change is falsely attributed to urgency: the baseline paper already credits admission ordering and whole-prefill/decode exclusion; the prior sensitivity already describes residual decode deferral. The new text removes the remaining ambiguity between a policy label, a token-gap gate, and completion deadlines.

* Added concise Section **3.4**, “What can activate the urgency gate?”, and **Equation (1)**: exact predicate, parameter/interface limitation, first-activation proof, and the 201ms finite-window certificate. Subsequent equation labels resolve automatically.
* Added the three tighter prompt-work certificates and the 107,844-opportunity reconstruction to existing Section 5.6. The existing table and all original numerical assets remain unchanged; no new table/figure duplicates the prior study.
* Abstract and structural contribution mention the certificate. Discussion/conclusion distinguish mathematical inactivity from observed scheduler equivalence and explain why changing metric deadlines does not test urgency.
* Appendix B and README identify the read-only audit, independent reconstruction and decision not to run a misleading experiment. No new citation or bibliography change.
* Both manuscript formats remain **26 pages**.

## 6. Verification

* **378 repository tests passed**, four inherited numerical warnings, 41.79s; **42 frozen C01 contract tests passed**. Regression fixtures are engineering execution, not new scientific campaign cells.
* Three exact-boundary policy checks passed with unchanged code; Config/View field sets and pinned policy identity were checked.
* Eighteen saved journals reconstructed; all 107,844 ready opportunities, 42 omissions, token-gap summaries and 18 certificate rows independently checked by a separate per-request event-interval implementation. This second checker imports neither the analyzer nor engine, policy or referee. Integer bracketing verifies each floor bound; a separate inequality verifies the general 201ms result. See [independent-check.json](independent-check.json).
* All three generated urgency outputs reproduce byte-identically from the frozen inputs/journals. Input, result, journal and code identities are recorded in [saved-evidence-audit.json](saved-evidence-audit.json).
* **All 54 original scientific/preservation checks passed**, including the full C01 oracle (5,760 cells, 15,840 rankings, 95,040 pairwise records, 26,136 reversal groups) and 7,200 STAT01 endpoint identities. The original reduced analysis and abstract checks pass; the worked example is freshly reconstructed. No claim is made to re-execute the original full campaigns.
* PR24's independent 72-cell/384-effect/576-comparison/96-top-set check passed. All **19 PR24 support files**, **72 raw results and 72 journals**, plus the earlier **63 frozen tracked assets**, retain their pinned bytes. Protected hydrated datasets remain unchanged and uncommitted. Historical validation reports are retained; fresh reports are copied here.
* Both 26-page PDFs compile with **zero overflow and zero unresolved references/citations**, with all 28 citation keys intact. The three inherited optional BibTeX metadata advisories remain. All-page contact sheets were examined; modified pages 1–2, 5–6, 14, 18–19 and 25 were inspected at readable resolution in both formats. The equation, units, cross-references and prior sensitivity table remain legible. PDF/internal-destination fingerprints are recorded in [delivery-verification.json](delivery-verification.json).

## 7. Delivery and reproducibility

Dedicated worktree: `/home/soroush/repos/llm-serving-scheduler-lssp-m3-urgency-mechanism`.
Branch: `research/lssp-m3-urgency-mechanism-20261023`, stacked on actual PR24 head `8a32ecf6e5e5dcca114594b320ac7c5210d8c543`.
Commands and logs: [COMMANDS.md](COMMANDS.md). The final delivery response supplies the pushed commit, draft PR and both PDF links. No persistent job remains. No merge, artifact publication, journal submission or editor contact occurred.

## 8. Contribution and publication-readiness verdict

The investigation **materially improves the explanation**: the prior finite observation of an inactive gate now has a sufficient analytic certificate even when work can bind, and a deadline-only experiment is correctly ruled out as a mechanism test. It does **not** demonstrate the benefit of active urgency or make the benchmark a broader evaluation of SLO-aware scheduling. The proof is short and contract-dependent; its explanatory value should not be inflated into a general scheduling theorem or a new performance result.

Full-ToMPECS novelty therefore remains a substantive concern. Restrictive timing, reservation and input-domain assumptions; finite selected and temporally related workloads; absent active-urgency evaluation; unresolved older cross-project BurstGPT overlap; pending complete artifact distribution and venue checks remain. This is an evidence-supported improvement, not an unconditional publication-readiness endorsement. Neither contract predicts physical GPU performance. Further experiments are outside this completed investigation.
