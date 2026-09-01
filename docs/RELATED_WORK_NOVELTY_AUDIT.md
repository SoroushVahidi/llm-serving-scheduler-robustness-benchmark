# RELATED_WORK_NOVELTY_AUDIT.md

Audited via live web search on 2026-08-31 (in addition to prior knowledge),
against public literature/artifacts through August 2026. Per the project
charter: **we do not claim "first"** anywhere below unless explicitly noted;
default wording is "we did not identify a prior work that ...".

Columns: does it provide (a) a workload, (b) a simulator, (c) evaluate one/few
new schedulers, (d) a many-policy × many-workload paired outcome matrix, (e)
explicit cross-source rank-stability study, (f) temporal/provider OOD splits,
(g) synthetic-to-real ranking transfer study, (h) benchmark sample-complexity
study.

| System / paper | (a) Workload | (b) Simulator | (c) 1-2 new schedulers | (d) Many×many matrix | (e) Cross-source rank stability | (f) Temporal/provider OOD | (g) Synthetic→real transfer | (h) Sample complexity |
|---|---|---|---|---|---|---|---|---|
| vLLM (continuous batching, PagedAttention) | No | No | Yes (the system itself) | No | No | No | No | No |
| Orca (iteration-level scheduling) | No | No | Yes | No | No | No | No | No |
| Sarathi-Serve (chunked prefill) | No | No | Yes | No | No | No | No | No |
| DistServe (disaggregated prefill/decode) | No | No | Yes | No | No | No | No | No |
| Llumnix (live migration / load rebalancing) | No | No | Yes | No | No | No | No | No |
| VTC (Virtual Token Counter, fair serving) | No | No | Yes | No | No | No | No | No |
| PARS / PARS-Serve (prompt-aware ranking scheduler, arXiv 2510.03243) | No (uses existing traces) | No | Yes (one predictor+scheduler) | No | No | No | No | No |
| vLLM-LTR (NeurIPS 2024, learning-to-rank scheduling, arXiv 2408.15792) | No | No | Yes | No | No | No | No | No |
| JITServe (SLO-aware, imprecise request info, arXiv 2504.20068) | Uses "diverse realistic workloads" (chat/deep-research/agentic) for its own evaluation | No | Yes | No (compares against a handful of baselines on its own workload mix, not a general cross-source matrix) | No | No | No | No |
| Vidur / Vidur-Bench (MLSys 2024, arXiv 2405.05465) | Configurable workload patterns | **Yes** — high-fidelity LLM inference simulator, closest infrastructure precedent to this project's simulator layer | No (a benchmark harness for *any* policy, not a new one) | Partial — "plug-and-play" support for many scheduling/batching/routing policies, but published Vidur results center on configuration search (parallelism, batch size), not a scheduler-ranking-stability study | No | No | No | No |
| LLMServingSim / LLMServingSim 2.0 (arXiv 2408.05499, 2511.07229) | Configurable | **Yes** — cycle-level HW/SW co-simulator; closer to hardware/heterogeneous-accelerator fidelity than this project needs | No | No | No | No | No | No |
| BurstGPT (workload trace, one of our five primary sources) | **Yes** | No | No | No | No | No | No | No |
| Azure LLM Inference Trace 2023 / 2024 (workload traces, two of our five primary sources) | **Yes** | No | No | No | No | No | No | No |
| DynamoLLM (Azure 2024 trace paper context) | Uses Azure 2024 trace | No | Autoscaling/power system, not a scheduler-ranking study | No | No | No | No | No |
| TraceLab (arXiv 2606.30560, coding-agent workload characterization) | **Yes** — a genuinely different domain (long-horizon agentic sessions, not chat-style serving) | No | No | No | No | Could serve as a provider/domain-OOD source for us, but the paper itself does not run one | No | No |
| ServeGen (NSDI 2026, arXiv 2505.09999) | **Yes** — a *generator*, not a fixed trace; characterizes/replicates production workload shifts (bursty arrivals, drifting length distributions over days/weeks) | No | No | Its production validation case is "avoids 50% under-provisioning vs. naive generation," not a scheduler-ranking study | No | Its whole premise is that workload distributions drift over time — directly relevant background for our RQ2, but not itself a ranking-stability benchmark | No | No |
| DynaSchedBench (ICML 2026, arXiv 2605.27566) | Synthetic job-shop-scheduling instances | Job-shop simulator | Evaluates **LLM agents as schedulers** for classical job-shop scheduling | N/A — different problem domain entirely (LLM-as-decision-maker for flexible job-shop scheduling, not scheduler-mechanism comparison for LLM-serving workloads) | No | No | No | No |
| HF dataset `SoroushVahidi/llm-serving-scheduler-baselines` (this project's own seed artifact) | Synthetic stress + one TraceLab-derived sweep | N/A (results only) | No — compares 12 baselines + Apt-Serve | **Partial** — `per_policy_results` + `tracelab_scheduler_ood_policy_sweep` configs exist, but as of this audit we did not verify a cross-source rank-stability analysis was published against it (see `docs/OVERLAP_LEDGER.md` "TraceLab OOD" row, `NEEDS_REVIEW`) | Unverified at bootstrap time | No | No | No |

## Assessment

- **Closest infrastructure precedents:** Vidur/Vidur-Bench and LLMServingSim
  2.0 are the most relevant prior simulators; both are oriented toward
  hardware/configuration-search fidelity, not toward a pre-registered,
  many-policy × many-workload-source ranking-**stability** study with
  cross-source/temporal/OOD splits and formal rank-reversal statistics.
- **We did not identify** a published benchmark that (a) evaluates a fixed
  scheduler panel across independently-sourced production/agentic workload
  families (BurstGPT, Azure 2023, Azure 2024, Bailian/Qwen, TraceLab) *and*
  (b) reports Kendall-tau/rank-reversal statistics across sources, load
  regimes, and metrics *and* (c) studies synthetic-to-real ranking transfer
  and ranking sample complexity as first-class questions. This combination
  (RQ1–RQ5) is this project's proposed contribution area, stated as an
  absence-of-evidence finding, not a priority claim.
- **ServeGen and TraceLab are the two most load-bearing pieces of context**
  for RQ2/RQ3: ServeGen's own premise (production workload distributions
  drift meaningfully over days/weeks) is direct external support for why
  cross-source/temporal ranking stability is a real concern worth
  benchmarking, not an assumption we invented.
- **Individual new-scheduler papers** (JITServe, PARS, vLLM-LTR, and the
  faithful baselines already in our panel) are evaluated against a handful of
  workloads chosen by their own authors; none of them is designed to answer
  "does *this specific comparison* generalize to an independently sourced
  workload," which is precisely this project's question.
