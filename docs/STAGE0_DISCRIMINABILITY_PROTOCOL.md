# STAGE0_DISCRIMINABILITY_PROTOCOL.md

**Design only — not launched in this task**, except a tiny parser/smoke
execution already covered by `tests/`. This answers: *do NEW independent
workload windows produce enough policy differentiation to justify the full
~520k-cell campaign (`docs/EXPERIMENT_CAMPAIGN_PLAN.md`, Stage 2)?*

## Design (frozen before any pilot cell is run)

- **3 independent workload sources** (`docs/EVIDENCE_INDEPENDENCE_PLAN.md`):
  - **Azure 2024** — fully independent (zero known prior consumption).
  - **Bailian/Qwen** — fully independent (zero known prior consumption; adapter
    now ported, `docs/PROVENANCE.md`).
  - **BurstGPT** — previously touched by LLM 2026 (20 windows out of a
    million-row corpus), but this pilot draws a **different, explicitly
    non-overlapping window sample** (a different offset/seed into the file
    than any locally-recoverable prior sampling), demonstrating the
    non-reuse methodology concretely rather than avoiding the source
    entirely.
  - TraceLab is deliberately excluded from this minimal Stage-0 pilot — its
    adapter does not exist yet and its independence cannot be fully verified
    (`docs/TRACELAB_PROVENANCE_RESOLUTION.md`); it belongs in the broader
    Stage 1 pilot, not this smallest-possible check.
- **8–12 windows/source** (target: 10), drawn by a documented, fixed sampling
  rule (e.g., every Nth 200-request block starting from a stated offset),
  frozen before any cell is run.
- **3 load regions**: `PRE_KNEE`, `KNEE`, `OVERLOAD`
  (`docs/LOAD_CALIBRATION_PROTOCOL.md`'s frozen, policy-independent, `fifo`-
  reference-calibrated protocol). **`LOW` is deliberately excluded from this
  minimal pilot** (low load rarely differentiates schedulers by construction,
  and the pilot's whole purpose is to check for differentiation efficiently).
  **The LLM 2026 `{1,2,4,8,16,32,64,128}` grid is not used** — load regions
  come only from this project's own calibration protocol, per
  `docs/CLAIM_BOUNDARIES.md`.
- **6 representative policies**, chosen to span the fidelity taxonomy
  (`docs/POLICY_COMPARABILITY_AUDIT.md`): `fifo`, `edf`
  (`REPOSITORY_NATIVE_CLASSICAL`), `kv_constrained_online`
  (`SIMULATOR_PROXY`), `vllm_faithful`, `sarathi_faithful`
  (`FAITHFUL_EXTERNAL`), `vllm_style_token_budget` (`STYLE_APPROXIMATION`).
- **2 repetitions per cell** — not for statistical power (none of these six
  policies has stochastic tie-breaking) but solely to verify deterministic
  rerun behavior on real-trace-derived windows, mirroring
  `tests/test_smoke_simulator.py::test_deterministic_rerun`.

**Total pilot size:** 3 sources × 10 windows × 3 load regions × 6 policies ×
2 repetitions = **1,080 cells** — small enough to run interactively, large
enough to answer the GO/NO-GO question below.

## Primary metric for the pilot

`arrival_normalized_weighted_goodput` (ANWG), for continuity with the
existing metric vocabulary (`docs/STATISTICAL_ANALYSIS_PLAN.md` §E lists it
first for cross-artifact comparability) — full metric-dependence analysis is
deferred to Stage 2/3, not needed to answer the discriminability question.

## GO criteria (defined before any outcome is observed)

The full Stage 2 campaign is justified only if **all** of the following hold
on the 1,080-cell pilot:

1. **Nontrivial pairwise policy differences.** In at least **30%** of
   (source, window, load-region) cells, the six policies' ANWG values are
   not all equal within a tolerance of 1e-6 (i.e., not a universal tie,
   mirroring the tie-detection convention already used in LLM 2026's own
   `public_trace_replay_v1_analysis`, cited as methodological precedent,
   not reused as data).
2. **Adequate fraction of non-tied windows.** At least **50%** of the 30
   (source, window) pairs (10 windows × 3 sources) show a non-tied result in
   at least one of the three load regions.
3. **No universal collapse.** Not all cells fall into either trivial
   underload (`completion_fraction == 1.0` for every policy, i.e.
   `PRE_KNEE` behaving like `LOW`) or universal overload/collapse
   (`completion_fraction` statistically indistinguishable from 0 for every
   policy at `OVERLOAD`) — mirroring the
   `PUBLIC_LOAD_SCALING_ONLY_COLLAPSE` failure mode LLM 2026 itself
   preregistered against (cited as a concept, not its data).
4. **Meaningful metric variation.** In at least **20%** of non-tied cells,
   the range of `p95_latency` or `slo_violation_rate` across the six
   policies exceeds **10%** of the cell's minimum value (guards against
   "different but negligibly so").
5. **No single source dominating all differentiation.** Each of the three
   sources contributes at least **15%** and at most **70%** of all
   non-tied (source, window, load-region) cells — guards against a
   conclusion that is really just "one degenerate source is discriminative,
   the other two are not."

If any criterion fails, the honest outcome is **NO-GO on Stage 2 as currently
scoped** — not a manufactured positive story (`docs/GO_NO_GO_GATES.md` Gate
D/E). A partial failure (e.g., criterion 5 fails because BurstGPT dominates)
is itself a useful, reportable finding about source-dependent
discriminability, not a reason to silently drop the failing source and
re-run until it passes.

## What this pilot does not do

Compute any cross-source ranking-stability statistic (Kendall tau, rank
reversal rate, etc.) — that is Stage 2/3's job, on the full sweep, not this
pilot. This pilot only answers "is there enough signal to be worth
measuring rigorously," using the smallest cell count that can honestly
answer that.
