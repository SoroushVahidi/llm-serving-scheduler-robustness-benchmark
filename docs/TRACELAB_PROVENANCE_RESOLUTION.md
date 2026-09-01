# TRACELAB_PROVENANCE_RESOLUTION.md

Resolves the discrepancy flagged in the bootstrap
(`docs/OVERLAP_LEDGER.md`/`docs/DATA_LICENSE_AUDIT.md`, "TraceLab OOD"): the
LLM 2026 repo's workload-source manifest marked TraceLab `acquired=False`,
while the HF dataset `SoroushVahidi/llm-serving-scheduler-baselines` already
ships a `tracelab_scheduler_ood_policy_sweep` config. This document records
what was actually found by directly re-reading the HF dataset card (not the
code-level manifest), per the mandate to not assume documentation is current.

## What the HF dataset card actually says (verbatim facts, 2026-08-31)

- **Config:** `tracelab_scheduler_ood_policy_sweep`, 13,824 rows = 512 derived
  TraceLab workload windows × 27 scheduler policies.
- **Source:** TraceLab / SyFI Lab, University of Washington —
  `https://github.com/uw-syfi/TraceLab` and `https://tracelab.cs.washington.edu`.
  Trace data license: **CC BY 4.0**. Code license: Apache-2.0.
- **How used:** "Used only to construct derived workload windows and
  Soroush-generated scheduler simulation metrics." **Raw source data is NOT
  redistributed** — the public config removes "TraceLab session identifiers,
  raw row spans, source-file row ancestry, and request-level content."
- **Window construction (as disclosed):** session-scoped windows, "at most
  ~128 requests per window," with **sqrt-compressed prompt-token inputs**
  and **synthetic neutral SLO labels added for simulator compatibility** —
  the card explicitly states "these are not natural TraceLab deadlines."
  This matches the row-level evidence pulled directly from the dataset
  (`missing_field_treatment_id = "tracelab_v2_policy_sweep_neutral_slo_prompt_compression_v1"`,
  `observed_kv_reuse = false` with `derived_prefix_reuse_proxy = true` —
  i.e., KV reuse is honestly disclosed as a derived proxy, not a native
  observation).
- **Coverage:** 512 windows = 320 `TRAIN_DEVELOPMENT` + 64 temporal-OOD + 64
  provider/model-OOD + 64 `reserved_final_ood_source` (a held-out slice
  within the existing release itself). Provider/model split: 390
  Claude-family, 122 Codex-family derived windows.
- **Reported result:** "The generating sweep reported **near-saturated**
  policy separation on this 512-window set (oracle goodput ≈ 1.0, zero
  marginal gain for newer policy-library entries)." The card explicitly
  instructs: treat this config as an OOD coverage/diagnostic benchmark, "not
  as proof of production scheduler ranking."
- **Provenance gap, disclosed by the maintainer on the card itself:** "The
  exact source commit recorded in this release's build metadata... does not
  currently resolve in that repository's git history (checked against every
  local clone, all branches, reflogs, and dangling objects, and
  independently against the public GitHub API) — a documentation gap the
  maintainer intends to close, not evidence that the underlying simulation
  results are unreliable or fabricated." This independently confirms the
  exact reproducibility weakness this project's own
  `docs/REPRODUCIBILITY_CONTRACT.md` was written to avoid repeating.

## What could NOT be independently confirmed in this repo

- The generation script that built the 512-window sweep (session selection,
  sampling seed, exact windowing rule beyond "session-scoped, ≤128
  requests") was **not found** in the local clone of `llm-serving-heuristic-evolution`
  at the audited SHA (`94f4621b`) — searched `scripts/`, `experiments/`,
  `datasets/`, `dataset_staging/`; only the higher-level source-manifest
  entry (`selector/dataset_v2/workload_sources.py`, marking TraceLab
  `acquired=False`) exists there. The sweep was very likely generated in an
  ephemeral/discarded working session not preserved in this repo's git
  history (consistent with several `/tmp/codex-discarded/...` and similarly
  named scratch directories observed elsewhere on this machine during this
  project's initial audit).
- **Consequently, this project cannot verify, session-by-session, which of
  the ~4,300 real TraceLab sessions the 512 public windows were drawn
  from.** The public release deliberately strips that identifying
  information (see above), and the generating code/manifest is not
  recoverable from any repo this project has read access to.
- Whether a newer TraceLab release exists beyond the one behind arXiv
  2606.30560 was checked via live web search (2026-08-31): arXiv lists
  versions v1 and v2 of the paper (same title, "TraceLab: Characterizing
  Coding Agent Workloads for LLM Serving"), and the GitHub repo
  (`uw-syfi/TraceLab`) is presented as the live home of "the dataset, trace
  collection pipeline, and analysis code." No evidence of a distinct,
  larger follow-up *dataset* release (as opposed to a paper revision) was
  found. Re-check the live repository directly before acquisition, since
  a rolling collection could plausibly grow the corpus over time.

## Resolution / recommended mitigation

1. **Do not assume the existing 512-window HF sweep is sufficient evidence
   for this project.** Per its own card: near-saturated separation, sqrt-
   compressed and SLO-synthesized fields, and explicitly scoped as
   diagnostic, not a production-ranking claim.
2. **Do not reuse the existing 512 windows as this project's TraceLab
   evidence** — re-derive an independent window set directly from the raw
   TraceLab corpus (`uw-syfi/TraceLab`) using this project's own
   `TraceAdapter`/`ExternalWorkloadRecord` ingestion layer (not yet
   implemented for TraceLab — Stage 0 work, `docs/EXPERIMENT_CAMPAIGN_PLAN.md`),
   with an explicitly documented, different sampling seed/protocol than any
   prior release. Since exact prior-session overlap cannot be verified
   (see above), this project must **disclose** possible residual overlap as
   a limitation rather than claim guaranteed independence.
3. **Before implementing the adapter**, independently re-inspect the live
   `uw-syfi/TraceLab` repository's actual field schema (per-request
   timestamp field name, tool-call structure) — do not assume the HF card's
   summary ("input tokens, output tokens, session/step structure") is a
   complete or literal field list.
4. **Re-verify the CC BY 4.0 trace license directly from the repository's
   own LICENSE/NOTICE files** before acquisition (the HF card's license
   statement is a secondary source, consistent with but not a substitute
   for the primary one).
5. Given the existing sweep's own "near-saturated" finding, this project's
   Stage 0/1 discriminability pilot (`docs/STAGE0_DISCRIMINABILITY_PROTOCOL.md`)
   should treat TraceLab as a source that may need a different load
   calibration than chat-style sources to produce differentiation at all —
   this is itself a piece of relevant prior evidence, cited, not repeated.
