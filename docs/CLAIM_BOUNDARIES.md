# CLAIM_BOUNDARIES.md

This paper does **not** claim:

- Universal superiority of any scheduler across all sources/loads/metrics —
  the entire premise (RQ1/RQ2) is that such universal claims are suspect.
- A new online selector, router, or adaptive policy-switching mechanism.
  RQ4's workload-descriptor analysis is explanatory/offline only (see
  `docs/STATISTICAL_ANALYSIS_PLAN.md` §G); if a descriptor is found to predict
  reversals, the deliverable is a documented association, not a deployed
  selector. Building a selector from this analysis is explicitly out of
  scope and would collide with the LLM 2026 manuscript's selector line.
- A new exploitability, regret, or SBS/VBS-headroom method. Those concepts
  are LLM 2026's; this paper may only cite LLM 2026's published results as
  prior work (`PRIOR_RESULT_REFERENCE_ONLY` in `docs/OVERLAP_LEDGER.md`), never
  reproduce or extend them under a new name.
- A new module-attribution or module-intervention method (SIGMETRICS 2027's).
- Production equivalence of simulator latency/throughput values to a real
  serving engine's numbers. RQ6 asks only whether *relative ranking* and
  *rank-reversal direction* reproduce on real vLLM — not that simulated
  absolute latencies match hardware latencies (see
  `docs/REAL_SYSTEM_VALIDATION_PLAN.md`).
- Discovery priority ("first to study X") beyond what
  `docs/RELATED_WORK_NOVELTY_AUDIT.md` supports. Default wording is "we did
  not identify a prior benchmark that ..." rather than "we are the first to ...".
- That every scheduler in the panel is production-grade or officially
  endorsed by its origin system — see `docs/POLICY_COMPARABILITY_AUDIT.md` for
  per-policy validation status and comparability caveats (in particular,
  `apt_serve_faithful` is scaffolding-only, not a validated reimplementation,
  at bootstrap time).
