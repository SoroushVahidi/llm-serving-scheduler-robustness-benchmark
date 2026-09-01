# EVIDENCE_INDEPENDENCE_PLAN.md

Goal: this project's confirmatory benchmark should preferentially use windows
that are **not** already consumed by LLM 2026's `public_replay_load_scaling_v1/v2`
(the 60-canonical-window study, `docs/OVERLAP_LEDGER.md`) or by the existing
HF `llm-serving-scheduler-baselines` release's `tracelab_scheduler_ood_policy_sweep`
config. **If old windows are retained at all, they are labeled
`PRIOR_REFERENCE` / `REPLICATION`, never `NEW_CONFIRMATORY`.**

None of the audits below required downloading real trace data (no source was
acquired in this task, per `docs/DATA_LICENSE_AUDIT.md`); figures for "total
available" are drawn from public dataset documentation, not from a local
count, and are flagged as such.

| Source | Total available (per public docs, **not independently row-counted**) | Windows consumed by LLM 2026 | Windows consumed by HF `llm-serving-scheduler-baselines` | Independently available unused | Temporal disjointness | Provider/domain disjointness | Source-native chronology |
|---|---|---|---|---|---|---|---|
| BurstGPT | On the order of millions of rows (HPMLL public release; exact current row count not independently verified in this audit — verify at acquisition time). | **20 windows** (`WINDOW_SIZE=200` → 4,000 requests), the `burstgpt` third of the 60 canonical windows. | **0** — the HF release's `per_policy_results` config uses synthetic stress envelopes only, not raw BurstGPT replay (per the dataset card's own Limitations section: "not raw production-trace replay"). | Effectively all of it (LLM 2026's 20 windows are a vanishingly small fraction of a million-row dataset). | Real relative/absolute timestamps present (`Timestamp` column) — chronological, non-overlapping windows can be drawn from a different time slice than LLM 2026's 20. | Single provider (HPMLL research release), not internally sub-dividable by provider. | Yes (native). |
| Azure 2023 conversation | Public release; exact row count not independently verified in this audit. | **20 windows** (Azure-2023-conversation third of the 60 canonical windows). | 0 (same reasoning as BurstGPT above). | Likely substantial, but this source is documented as smaller than BurstGPT — re-verify actual row count before assuming ample headroom for a large window count. | Real `TIMESTAMP` column. | Microsoft Azure, `conversation` split. | Yes (native). |
| Azure 2023 code | Public release; exact row count not independently verified. | **20 windows** (Azure-2023-code third of the 60 canonical windows). | 0. | Same caveat as conversation split. | Real `TIMESTAMP` column. | Microsoft Azure, `code` split. | Yes (native). |
| Azure 2024 | Public release, 2024-05-10 to 2024-05-19 collection window; row count not independently verified. | **0** — per `docs/current/llm2026_dataset_provenance_audit_20260824.md`, Azure 2024 is "not used in final manuscript results." | 0. | **All of it, as far as this audit can determine — the cleanest available source with zero known prior consumption.** | Real `TIMESTAMP` column; distinct calendar period from Azure 2023, making it this project's primary temporal-OOD source (`configs/splits/temporal_ood.yaml`). | Microsoft Azure, but a full year later than the 2023 release — a genuinely different production snapshot. | Yes (native). |
| Bailian/Qwen | Anonymized trace release; row count not independently verified in this audit. | **0** — not cited as used in LLM 2026's final manuscript results (per the same provenance audit doc). | 0 — not listed in the HF card's "Upstream Workload / Trace Sources" table at all. | All of it, as far as this audit can determine. | `timestamp` is relative-to-trace-start, not an absolute calendar date — sufficient for within-trace chronological windowing, insufficient by itself for calendar-date temporal-OOD splits against another source. | Alibaba Cloud (Bailian/Qwen production serving) — the same underlying platform as ServeGen's characterization data (see `docs/SERVEGEN_ADOPTION_AUDIT.md`); note this when claiming Bailian and ServeGen as two *independent* provider sources. | Relative only (native, but not absolute). |
| TraceLab | ~4,300 real coding-agent sessions, ~350K LLM steps, ~430K tool calls, per the source paper (arXiv 2606.30560). | **0** in the final LLM 2026 manuscript (same provenance audit doc: "not used in final manuscript results" — TraceLab appears only in LLM 2026's *future/OOD planning* docs, never executed against). | **512 derived windows** (320 `TRAIN_DEVELOPMENT`, 64 temporal-OOD, 64 provider/model-OOD, 64 `reserved_final_ood_source`), per the HF dataset card. | **Cannot be determined exactly** — the public HF release strips "TraceLab session identifiers, raw row spans, source-file row ancestry" (dataset card, "TraceLab OOD Policy Sweep Config" section), so this project cannot check session-by-session overlap against the 512 already-used windows. Given ~4,300 total sessions vs. 512 already-derived windows, substantial headroom is *plausible* but not verifiable at the individual-session level from public artifacts alone. See `docs/TRACELAB_PROVENANCE_RESOLUTION.md` for the full resolution and the recommended mitigation (re-derive from the full raw corpus with an explicitly different, documented sampling seed/protocol, and treat any accidental overlap as a limitation to disclose rather than something that can be guaranteed against). | Provider/model split already exists in the source data (390 Claude-family, 122 Codex-family derived windows, per the HF card) — a real domain-OOD axis if this project re-derives its own windows. | Unknown/unverified — TraceLab's own per-request timestamp field name requires direct repository schema inspection (`docs/DATA_LICENSE_AUDIT.md`), not yet performed. |
| ServeGen | Not a fixed corpus — a generator; "windows available" is not the right question. See `docs/SERVEGEN_ADOPTION_AUDIT.md`. | N/A | N/A | N/A | N/A | Characterizes Alibaba Cloud Model Studio (Bailian) production traffic — **not independent of the Bailian/Qwen provider identity**, see the Bailian row above. | N/A |

## Conclusions

1. **Azure 2024 is this project's cleanest, fully-independent source** — zero
   known consumption by either LLM 2026 or the HF baselines release, real
   chronology, and a distinct calendar period from Azure 2023 (useful for
   temporal-OOD by construction).
2. **Bailian/Qwen is the second-cleanest** — zero known consumption anywhere,
   now has a ported adapter (`docs/PROVENANCE.md`), but its chronology is
   relative-only and it shares an underlying platform with ServeGen.
3. **BurstGPT and Azure 2023 (both splits) are safe to reuse as sources**, but
   this project's own window selection must avoid the *specific* 60 windows
   LLM 2026 already used. Since the exact 60-window identity is fixed by a
   deterministic builder (`llmserveopt.policy_separation.public_trace_replay_v1.build_all_scenarios()`,
   not copied into this repo per `docs/PROVENANCE.md`), the practical
   mitigation is: this project constructs its own windows from a different,
   independently documented sampling procedure and window-count target
   (`docs/EXPERIMENT_CAMPAIGN_PLAN.md`'s ~40 windows/source, not 20), and
   records the construction rule so a reader can confirm non-identity by
   construction even without a public list of the old 60 window IDs.
4. **TraceLab's independence cannot be fully verified from public artifacts**
   — treat any TraceLab-derived finding in this project as provisional until
   `docs/TRACELAB_PROVENANCE_RESOLUTION.md`'s recommended mitigation is
   executed.
5. **ServeGen is not a fifth independent provider** — it characterizes the
   same underlying platform as Bailian/Qwen. Do not count it toward "4
   independent workload families" (Go/No-Go Gate B) as a distinct provider;
   it may still be adopted as a synthetic-family enhancement (see its own
   audit doc).
