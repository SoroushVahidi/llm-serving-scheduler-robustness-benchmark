# DATA_LICENSE_AUDIT.md

Status as independently re-derived during this bootstrap (2026-08-31), cross-
checked against the reused adapter docstrings (`docs/PROVENANCE.md`) rather
than assumed from memory. **None of these datasets have been downloaded or
acquired as part of this task** (per task charter, no massive acquisition
pass here) — this records license/status findings only.

| Source | License (as documented in reused adapter) | Redistribution status | Acquired in this task? | Notes |
|---|---|---|---|---|
| BurstGPT | CC-BY-4.0 | Permits redistribution with attribution | No | Adapter (`burstgpt.py`) validated only against a small synthetic fixture, not the real ~10M-row release — re-validate against a real sample before any confirmatory use. |
| Azure LLM Inference Trace 2023 | CC-BY (AzurePublicDataset) | Permits redistribution with attribution | No | Adapter handles `code` and `conversation` splits only; no function-calling subset exists in the audited release. |
| Azure LLM Inference Trace 2024 | CC-BY (AzurePublicDataset) | Permits redistribution with attribution | No | Same adapter class as 2023, `dataset_year="2024"`. Treat 2023 and 2024 as two distinct sources for temporal/provider-OOD splits, never merged into one "Azure" source. |
| Bailian/Qwen anonymized traces | Apache-2.0 (repository `LICENSE`; README states Apache-2.0 for the dataset release) | Permits redistribution | No | **Ported 2026-08-31**: `src/robustbench/workloads/external/adapters/bailian.py`, a new `TraceAdapter` implementation (not a copy of the source repo's `augment_trace`-coupled loader — see `docs/PROVENANCE.md`), smoke-tested against a synthetic fixture (`tests/test_bailian_adapter.py`). Confirmed zero prior consumption by LLM 2026 or the HF baselines release (`docs/EVIDENCE_INDEPENDENCE_PLAN.md`). Real trace still not acquired. |
| TraceLab | Code: Apache-2.0. Public trace dataset: CC BY 4.0 per repository README/NOTICE (per the LLM 2026 repo's source manifest) | Likely permits redistribution, **re-verify at acquisition time** | No | **See `docs/OVERLAP_LEDGER.md` "TraceLab OOD" row — a real discrepancy exists**: the LLM 2026 repo's workload-source manifest marks TraceLab `acquired=False`, but the HF seed dataset (`llm-serving-scheduler-baselines`) already ships a `tracelab_scheduler_ood_policy_sweep` config. Before using TraceLab data in this project, independently re-inspect that HF config's actual provenance/license statement rather than trusting either source's documentation. |
| ServeGen | Not yet independently verified; GitHub repo (`alibaba/ServeGen`) states the authors "plan to open-source" it — verify the actual license file before any acquisition/use | Unknown pending verification | No | It is a *generator*, not a fixed trace release — treat differently from the other four sources (see `configs/workloads/source_registry.yaml`). |
| Mooncake (FAST'25 release) | Repository carries Apache-2.0 via `LICENSE-APACHE`, but **no trace-specific data-license statement has been identified** (per the reused adapter's own docstring) | **`INTERNAL_ONLY`** — do not redistribute raw Mooncake rows or raw `hash_ids` | No | Per task charter rule #13: excluded from any distributable output (including any future Dataset v2 release) unless redistribution license is independently verified. Adapter kept in this repo for schema-parity/internal experimentation only. |

## Primary vs. secondary source status for this project

Primary (five sources named in the project charter): **BurstGPT, Azure 2023,
Azure 2024, Bailian/Qwen, TraceLab.**

Strongly investigate: **ServeGen** (as a generator, likely a synthetic-family
complement rather than a sixth "real" source — see
`docs/RELATED_WORK_NOVELTY_AUDIT.md`).

Internal-only, excluded from distributable outputs: **Mooncake**, pending
independent license verification.

## Outstanding license-audit action items

1. Re-verify the TraceLab dataset license directly from the
   `uw-syfi/TraceLab` repository's LICENSE/NOTICE files (not from a secondary
   summary) before any acquisition.
2. Re-verify ServeGen's actual license file once the `alibaba/ServeGen`
   repository publishes one (audited 2026-08-31: repo exists, described as
   "plan to open-source", framework code present per NSDI'26 paper page).
3. Independently confirm whether Mooncake's `FAST25-release/traces/`
   directory carries a data-specific license distinct from the repository's
   Apache-2.0 code license, before considering any change to `INTERNAL_ONLY`
   status.
