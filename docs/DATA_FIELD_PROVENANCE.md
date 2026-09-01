# DATA_FIELD_PROVENANCE.md

Field-level provenance for the reused `ExternalWorkloadRecord` schema
(`src/robustbench/workloads/external/schema.py`). Every adapter must tag each
non-null field with one of: `SOURCE_OBSERVED`, `DETERMINISTIC_DERIVED`,
`SYNTHESIZED_IMPUTED`, `UNAVAILABLE` (see that file for the enforced
vocabulary and `ExternalWorkloadRecord.validate()`).

## Per-source field retention (Layer 1, as implemented by the reused adapters)

| Source | Retained (SOURCE_OBSERVED) | Always UNAVAILABLE in this adapter | Notes |
|---|---|---|---|
| BurstGPT | `arrival_time_s` (from `Timestamp`), `input_tokens`, `output_tokens`, `total_tokens`, `session_id`, `model_class` (from `Model`) | `tenant_id`, KV-reuse fields, SLO/priority | No tenant/user, KV-reuse, SLO, or failure-code field exists in BurstGPT's documented schema. |
| Azure 2023 / 2024 | `arrival_time_s` (from `TIMESTAMP`), `input_tokens` (from `ContextTokens`), `output_tokens` (from `GeneratedTokens`) | `session_id`, `tenant_id`, `model_class`, KV-reuse, SLO/priority, server-latency | Split (`code`/`conversation`) is passed in by the caller, never inferred from the file (no split column exists in the source schema). |
| Mooncake | `input_length`, `output_length`, `hash_ids` (16-token KV/prefix-block hashes — the only source in this set with genuine KV-reuse ground truth) | `tenant_id`, `model_class`, SLO/priority, server-latency | Timestamp field name is explicitly **unverified** in the primary-source audit; the adapter requires the caller to state the field name rather than guessing, and arrival timing stays `UNAVAILABLE` if the named field is absent. |
| Bailian/Qwen (loader exists upstream, not yet ported here) | `timestamp` (relative to trace start), `input_length`, `output_length`, `chat_id`/`parent_chat_id` (session), `type`, `turn`, `hash_ids` | Native SLO/priority | Upstream loader **discloses** `predicted_output_tokens`, `class_id`, `priority`, `slo_deadline` as synthesized — carry that disclosure forward verbatim if/when ported. |
| TraceLab | Not yet independently schema-inspected in this bootstrap (per-request timestamp/token field names require repository inspection at acquisition time) | Unknown pending inspection | Do not assume a field is source-native until the actual repository schema is inspected — see `docs/DATA_LICENSE_AUDIT.md`. |

## Fields this project synthesizes/overlays, and how they must be disclosed

None of the five primary sources natively carries `priority`, `slo_deadline`,
or a full `predicted_output_tokens` prediction usable by an *online* policy
(the online-visible `ObservableRequest` in `core/types.py` never exposes
`actual_output_tokens`, only `predicted_output_tokens`). Whenever this project
overlays such fields to make a source runnable through the simulator:

1. The overlay method must be documented in the relevant experiment config
   (not just in code comments).
2. `field_provenance` on the resulting record/row must read
   `SYNTHESIZED_IMPUTED`, never `SOURCE_OBSERVED`.
3. Any headline result that depends materially on a synthesized field (e.g.
   `edf`/`least_laxity_first` rankings, which require `slo_deadline`) must
   report a sensitivity check against at least one alternative synthesis rule
   (see `docs/STATISTICAL_ANALYSIS_PLAN.md`).
4. `WindowDescriptor.n_synthesized_fields` /
   `n_source_observed_fields` / `n_unavailable_fields`
   (`src/robustbench/descriptors/window_descriptors.py`) must be reported
   alongside any ranking result computed from that window, so a reader can
   see how much of the window's schema was invented versus observed.

## Known documentation-vs-artifact discrepancy

See `docs/OVERLAP_LEDGER.md` ("TraceLab OOD") and `docs/DATA_LICENSE_AUDIT.md`:
the LLM 2026 repo's workload-source manifest says TraceLab is not yet
acquired, but the HF seed dataset already contains a
`tracelab_scheduler_ood_policy_sweep` config. Until that config's own field
provenance is independently re-inspected, do not assume it satisfies this
project's provenance-disclosure bar.
