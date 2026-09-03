# RQ6_REAL_VLLM_SCIENTIFIC_PROTOCOL_20260902.md

`RQ6_REAL_VLLM_SCIENTIFIC_VALIDATION = NOT_STARTED`. This document is a
prefreeze: it records what is genuinely frozen and validated as of
2026-09-02/03, and separates that clearly from what is still open. Nothing
in this document is scientific evidence. No `slai_faithful`-vs-`vllm_faithful`
comparative measurement has been run.

## What this validates

Whether the specific pairwise reversal selected in
`artifacts/manifests/phase12_rq6_case_selection_20260902.json` (frozen from
the simulated Phase-12 campaign, before any real-vLLM run) reproduces on
real vLLM hardware:

- **Reversal case**: `slai_faithful` vs `vllm_faithful`, metric
  `arrival_normalized_weighted_goodput`, comparing
  `azure_llm_2024::HIGH_PRESSURE` against `burstgpt::HIGH_PRESSURE`.
- **Stable control**: `azure_llm_2024::HIGH_PRESSURE` vs
  `bailian_qwen::HIGH_PRESSURE` (same metric), expected to remain a stable
  ordering (`kendall_tau = 1.0` in the simulator).

## Stage separation

| Stage | Status | Evidence |
|---|---|---|
| 1. Engineering validation (SLAI plugin on real vLLM) | **DONE** | Wulver job 1219334, `pass_gate: true` (`docs/REAL_VLLM_SLAI_FIDELITY.md`) |
| 2. Environment reproducibility | **DONE** | `requirements-real-vllm.txt` + `src/robustbench/real_llm/env_preflight.py`, commit `52ef9ff` |
| 3. Case selection | **DONE (verified, hash-corrected)** | see below |
| 4. Workload manifests (3 sources) | **DONE (2026-09-03)** | see "Workload manifests (built and validated)" below |
| 5. Calibration protocol (procedure) | **FROZEN** | `docs/RQ6_REAL_VLLM_CALIBRATION_PROTOCOL_20260902.md` |
| 6. Calibration execution | **NOT DONE** | SLO/weight metric pipeline now implemented (see below) but blocked on a still-undecided bisection request-population design question; see "Open items" |
| 7. Execution order | **FROZEN** | `artifacts/manifests/rq6_execution_order_20260902.json` |
| 8. Statistical analysis plan | **FROZEN (this document, §Statistics)** | |
| 9. Comparative scientific measurement | **NOT STARTED** | requires 4 and 6 complete first |

## Case selection (verified)

```
CASE_SELECTION_MANIFEST_PATH   = artifacts/manifests/phase12_rq6_case_selection_20260902.json
CASE_SELECTION_MANIFEST_SHA256 = f34e1c6a9f8d4c695720d14f7929741594ac8f7818a427db832933554e909e5a
CASE_SELECTION_SOURCE_CONSOLIDATED_INPUT_SHA256 = 73adf7d97f06985ec8f8e1c2f794fd43178433eb198e1c00705e817f4bde9c26
```

**Correction of a prior miscommunication**: an earlier instruction quoted
`73adf7d9...` as the case-selection manifest's own SHA256. That value is
actually the manifest's *internal* `source_provenance.consolidated_input_sha256`
field (the hash of the upstream consolidated analysis artifact the
selection was computed from, not the hash of this manifest file). The
manifest's own file hash is `f34e1c6a...`. Both hashes are recorded above,
explicitly labeled, so this cannot recur. A repository-wide search found
`73adf7d9...` used correctly elsewhere (as
`EXPECTED_CONSOLIDATED_ARTIFACT_SHA256` in
`scripts/ranking_portability/run_phase12_analysis.py` and
`docs/RANKING_PORTABILITY_PHASE12_ANALYSIS_PREFREEZE.md`) — no mislabeling
exists in the tracked repository itself; the confusion was introduced only
in conversational shorthand.

Case-selection content verified against the frozen reversal/control
described above — matches exactly, and was frozen
(`case_manifest_frozen_before_any_real_vllm_run: true`,
`real_vllm_run_launched_in_this_task: false`) before any real-vLLM run, as
required.

## Workload manifests (built and validated, 2026-09-03)

```
CACHE_PATH   = artifacts/pilot_v2_windows_full_cache.json (uncommitted, regenerable local artifact;
               located this session in the Phase-12 freeze worktree)
CACHE_SHA256_RAW = 97fbaf6a4b9b5f14cd19ce1c37193996c0758eebca73ab2adb1e944b404b3f4c
```

**Cache provenance -- corrected finding.** The cache's own top-level
`content_sha256` field is **stale/mislabeled**: it is byte-identical to
`0d1aa06ccbee352207327ea369ae75f12e91c0cda006c813a41b381effd29eef`, which
`docs/ARTIFACT_HASH_LEDGER.md` identifies as the unrelated legacy "Phase-10
full scientific hash" (an opaque git-freeze identifier, not a content hash
of this file), *not* a genuine recomputation of this manifest's own
content -- recomputing the same canonical-hash formula this codebase uses
elsewhere (`_canonical_content_sha256`, excluding `generated_at_utc`)
against the actual file yields a different value
(`6595e08c92df0d362b0f05383e385977ce6baab2da15ce15335bee72ee0fc634`), so
that top-level field must not be used for verification. The correct,
semantically-matched provenance check -- and the one
`build_rq6_workload_manifests.py` actually performs -- is the **per-window**
`content_sha256` (formula: `sha256(json.dumps(records, sort_keys=True,
separators=(",",":")))`), which is independently verified to match, for
all 120/120 windows, both `ranking_portability_pilot_v2_windows_index.json`
(the committed compact index, itself file-hash-gated against
`docs/ARTIFACT_HASH_LEDGER.md`'s pinned `d78ec108...`) and
`ranking_portability_phase12_campaign_freeze.json`'s own
`window_identities` map (itself file-hash-gated against this branch's
committed content, `44a81e98...`). Exactly 3 sources x 40 windows x 200
requests = 24,000 requests total, matching the frozen Phase-12 contract; no
divergence found.

**Stage-0 overlay.** `priority`/`class_id`/`predicted_output_tokens`/
`slo_deadline` are not stored in any artifact -- they exist only as the
deterministic, versioned synthesis function
`robustbench.workloads.external.benchmark_synthesis.synthesize_requests_from_window`
(`SYNTHESIS_VERSION = "stage0_synthesis_v1"`), applied with the exact
per-window `synthesis_seed` already recorded in
`ranking_portability_phase12_campaign_freeze.json`'s `cells` (one fixed
seed per window, e.g. `900000 + window index`, identical to the seed
convention already used by `build_phase11_calibration.py`) -- the same
seed the frozen Phase-12 campaign itself used, so regeneration reproduces
the exact frozen overlay values, not a new synthesis.

**40-window execution semantics -- implemented exactly as frozen above**
("Statistics" section): each window's requests are rebased to window-local
`t=0`, scaled by `_rebase_and_scale(requests, absolute_load_factor)` where
`absolute_load_factor` = that window's own `1.5 x lambda_ref` (from
`region_assignment_index`), then all 40 windows are concatenated in
`window_id`-sorted order with window `j+1`'s first arrival anchored exactly
at window `j`'s last (scaled) arrival -- verified programmatically (no
inter-window discontinuity) across all 120 windows in the generated
manifests.

**Timing transform (Section F formula, frozen here).** Each request's
`base_relative_arrival_s`/`base_slo_deadline_s` in the workload manifest is
the frozen HIGH_PRESSURE trace **shape** described above -- not a
real-engine rate. The calibration runner must apply, for its own
hardware-measured candidate scale `s`:
```
real_arrival_i      = base_relative_arrival_i / s
real_slo_deadline_i = real_arrival_i + (base_slo_deadline_i - base_relative_arrival_i) / s
```
(implemented and unit-tested in `robustbench.real_llm.rq6_slo_metrics.scale_request_timing`)
-- one formula, no policy-specific variants, never reusing the simulator's
absolute `lambda_ref` as a real-engine rate.

**Prompt reconstruction.** No adapter for any of the three sources ever
captured prompt/response text (confirmed by inspecting
`ExternalWorkloadRecord`'s schema and all three adapters). Audited
`real_llm/calibration_common.py`'s existing `build_length_targeted_prompt`
and found it **unsuitable** for this purpose: it only supports 3 discrete
token buckets (100/512/2048) and controls length via an approximate
word-count heuristic on the instruction text (its own docstring says so),
not an exact tokenizer-level match against an arbitrary frozen
`input_tokens` value. A new function,
`calibration_common.build_exact_length_prompt(tokenizer, target_tokens,
seed)`, was added: it reuses the same non-copyrighted `_SENTENCE_BANK` but
builds/truncates at the token-id level against the real target model's
tokenizer (`Qwen/Qwen2.5-0.5B-Instruct`, matching
`real_vllm_engineering_environment.json`'s already-validated smoke model).
Verified over all 24,000 generated requests (`input_tokens` ranging 6 to
29,067 across the frozen cache): **100% exact match**
(`actual_prompt_token_count == frozen_input_token_count` for every single
request; `prompt_exact_length_match_rate: 1.0` in every manifest). Per the
task's disclosure requirement: original prompt text was unavailable in the
trace-derived Phase-12 workload representation; real-vLLM validation
therefore uses deterministic tokenizer-length-matched executable prompts
while preserving frozen request timing and token-length descriptors. This
is a threat to external validity: real token content differs from the
source trace even though token counts match exactly. Prompt text itself is
not stored in the manifest (would bloat it substantially); each request
instead carries a `prompt_generation_seed` (derived deterministically from
the request's stable `derived_record_id`) plus the
`prompt_reconstruction_contract` block naming the exact function and
tokenizer, so the prompt is reproducible byte-for-byte without being
duplicated.

**Output-token execution contract.** `output_tokens_target` (=frozen
`actual_output_tokens`, ground truth) is what the calibration/execution
runner must send as vLLM's `max_tokens` with `ignore_eos=true`, so the real
server reproduces the frozen trace's decode-length footprint exactly
rather than stopping at a natural EOS -- `predicted_output_tokens` is
carried through separately as the `SYNTHESIZED_IMPUTED` length *estimate*
available to prediction-aware policies, never used as the execution cap
itself.

**Manifests:**

| Source | Path | `content_sha256` | Windows | Requests |
|---|---|---|---|---|
| azure_llm_2024 | `artifacts/manifests/rq6_real_vllm/rq6_workload_azure_llm_2024_20260903.json` | `689b7fa8df234bacb9e27c936bafafb79279b86bdb8f6996f6ebbecb79a1d887` | 40 | 8,000 |
| burstgpt | `artifacts/manifests/rq6_real_vllm/rq6_workload_burstgpt_20260903.json` | `8d1cf0726f316d37fe5dd8da53414ffa971760af27ce86c17f47686807f70371` | 40 | 8,000 |
| bailian_qwen | `artifacts/manifests/rq6_real_vllm/rq6_workload_bailian_qwen_20260903.json` | `e8d8a227f018e10ffa4c2a363554e8b9bea1d0afec1a3277ac7655b44d3fb9ad` | 40 | 8,000 |

Generator: `scripts/real_vllm/build_rq6_workload_manifests.py`. Validator:
`scripts/real_vllm/validate_rq6_workload_manifests.py`, output
`artifacts/validation/rq6_real_vllm_manifest_validation.json` (uncommitted,
regenerable -- reproduce by re-running the validator against the committed
manifests + inputs above); all three sources `passed: true`, zero problems,
as of this freeze. Tests: `tests/test_rq6_workload_manifests.py` (18 cases:
determinism, all-window inclusion, request-order/boundary/timing
semantics, exact prompt length, overlay preservation, duplicate/missing-
window/hash-mismatch/policy-leakage failure paths) and
`tests/test_rq6_slo_metrics.py` (9 cases for the SLO/weight pipeline
below).

## SLO/weight metric pipeline (implemented, 2026-09-03)

The prerequisite named in `docs/RQ6_REAL_VLLM_CALIBRATION_PROTOCOL_20260902.md`
("What is frozen now vs. what remains open") -- attaching a per-request
`slo_deadline`/`weight` and computing `t_done`-vs-`slo_deadline` client-side
-- is now implemented in `robustbench.real_llm.rq6_slo_metrics`:
`scale_request_timing` (the exact formula above) and
`real_slo_violation_rate` (`1 - weighted_met / weighted_completed`,
fail-closed to `1.0` on zero completions, mirroring
`_slo_violation_rate_at`). Both reuse the frozen manifest's `weight`
(=`priority`, uniformly `1.0` under `stage0_synthesis_v1`) and
`base_slo_deadline_s` fields unmodified -- no resynthesis. Unit-tested
against hand-computed weighted examples and directly against real
generated-manifest fields (`tests/test_rq6_slo_metrics.py`).

**This does not, by itself, make calibration executable.** A genuine,
still-open design question remains: the calibration protocol's bisection
searches 30 candidate factors; what request population should each
candidate's `slo_violation_rate_real` measurement replay against? Replaying
the full 8,000-request per-source manifest at all 30 iterations (per
source, x3 sources) is not obviously the intended scale, and no frozen
document resolves this -- deciding it now, under this task's time
pressure, would repeat exactly the kind of un-forced, outcome-blind-in-
name-only design shortcut this project has otherwise been careful to avoid
(cf. the forensic trace that led to the 40-window concatenation decision
above). This is recorded as the concrete next step, not invented here.

## Engineering recovery / environment

```
ENGINEERING_RECOVERY_BRANCH = engineering/lssp-rq6-wulver-recovery-20260902
ENGINEERING_RECOVERY_SHA    = 52ef9fff1dcb49ca729f91d24e1aed077c72a6b0
ENVIRONMENT_SPEC_PATH       = requirements-real-vllm.txt
ENVIRONMENT_SPEC_SHA256     = de46e1134fbd2aff7d2ad378dc4e516e18bd4795137d1c96a6e75729b421e3f0
```

## Calibration protocol

See `docs/RQ6_REAL_VLLM_CALIBRATION_PROTOCOL_20260902.md` and

```
CALIBRATION_MANIFEST_PATH   = configs/real_vllm/rq6_calibration_manifest_20260902.json
CALIBRATION_MANIFEST_SHA256 = 417dd8d3d07e770c4629beb59d3116b832516d3f59b7230b9a39b93eb7f65d2d
```

Procedure frozen; **not yet executable** — see that document's "What is
frozen now vs. what remains open" table.

## Execution order

```
EXECUTION_ORDER_PATH   = artifacts/manifests/rq6_execution_order_20260902.json
EXECUTION_ORDER_SHA256 = 885143cebc0dbd773c1f4b23291a906552886446d6aba6a19b9481c0236e9fd3
N_REPETITIONS           = 10
```

Generated by `scripts/real_vllm/build_rq6_execution_order.py`, which reuses
the existing tested orchestration primitives
(`robustbench.real_llm.cell_orchestration.expand_cells_to_run_units`,
`abba_order`) rather than new ordering logic: policy order alternates by
repetition parity within each (source, repetition) pair, and the resulting
pairs are shuffled with a fixed seed (`20260902`) so cell execution order
is not always the same either. 60 total run units (3 sources × 2 policies
× 10 repetitions). Deterministic: re-running the generator against the
same inputs reproduces a byte-identical file (checked in
`tests/test_rq6_execution_order.py`).

## Statistics (frozen before any comparative outcome)

Primary metric: `arrival_normalized_weighted_goodput` (ANWG), matching
`docs/STATISTICAL_ANALYSIS_PLAN.md` §E's naming and
`docs/REAL_SYSTEM_METRIC_MAPPING.md`'s real-engine mapping.

**Experimental unit — adapted from, not identical to, the simulator plan,
and corrected from an earlier draft of this document.** A forensic trace
of the frozen Phase-12 inputs (2026-09-03) found that
`<source>::HIGH_PRESSURE` in the case-selection manifest is **not** a
single window: `ranking_portability_phase12_campaign_freeze.json`'s
`region_assignment_index` scales all **40** frozen windows per source
(`{source}_stage0_w00..w09` + `{source}_pilot_v2_w10..w39`) independently
to `1.5×` each window's own FIFO `lambda_ref`, and `HIGH_PRESSURE` is the
label for that aggregate region, not one window's identity. An earlier
draft of this section incorrectly assumed a single frozen window; this is
the correction.

Running all 40 windows as 40 independent real-vLLM cells (×2 policies
×10 repetitions = 800 live server rounds per source, 2,400 total) is not
a defensible use of GPU time for a fidelity check whose stated purpose is
sign/direction agreement, not per-window precision (`docs/
REAL_SYSTEM_VALIDATION_PLAN.md`'s "Explicitly not required"). The
methodologically faithful resolution, decided here before any workload
manifest is built or any real measurement is taken (so it cannot be an
outcome-dependent choice): **one real-vLLM workload manifest per source
concatenates all 40 frozen windows' requests** (each window's arrival
times still independently rebased/scaled to 1.5× that window's own
`lambda_ref`, exactly mirroring `region_assignment_index`, then the 40
rebased sequences concatenated in `window_id`-sorted order into one fixed
arrival sequence for that source). No window is dropped or subsampled —
this uses the complete frozen `HIGH_PRESSURE` definition, not a new
selection. **One repetition = one live execution of that complete
40-window sequence** against one policy; 10 such repetitions per (policy,
source) is the experimental unit for bootstrap resampling. This requires
no change to the already-frozen execution order (§ above) or `N_REPETITIONS
= 10` — a "run unit" there already meant "one full run of the source's
fixed manifest," which now simply means the concatenated 40-window
manifest instead of a single window.

For each (policy, source) cell, the 10
repetition-level ANWG measurements are the population resampled with
replacement (bootstrap, ≥2,000 resamples, matching the simulator plan's
`≥2,000`-resample convention), producing a 95% CI on each cell's ANWG and
on the SLAI-minus-vLLM effect per condition.

For the reversal case (Azure `HIGH_PRESSURE` vs BurstGPT `HIGH_PRESSURE`):
- SLAI-minus-vLLM ANWG effect and its 95% bootstrap CI, per condition.
- Winner sign per condition (does the CI exclude zero, and in which
  direction).
- Whether the sign flips between the two conditions.
- Whether the real flip (if any) agrees with the simulator-selected
  reversal direction.

For the stable control (Azure `HIGH_PRESSURE` vs Bailian/Qwen
`HIGH_PRESSURE`):
- Same effect/CI computation per condition.
- Whether the same-sign (stable) ordering holds in both conditions,
  mirroring the simulator's `kendall_tau = 1.0` finding.

**Multiple-testing correction**: Benjamini-Hochberg FDR at q=0.05 across
the family of pairwise tests in this document (2 reversal-condition tests
+ 2 stable-control-condition tests = 4 tests), matching
`docs/STATISTICAL_ANALYSIS_PLAN.md`'s "Multiple-testing correction"
section and applied per-family, not globally.

**Do not change any of the above after observing outcomes.**

## Open items (must be resolved before stage 9 can run)

1. **Workload manifests** (stage 4) — **DONE (2026-09-03)**, see "Workload
   manifests (built and validated, 2026-09-03)" above for the full record.
   Summary of what was found and built:
   - No adapter for any of the three sources (`azure_llm.py`,
     `burstgpt.py`, `bailian.py`) ever captured prompt/response **text**
     — only timing and token counts. Real-vLLM prompts use **deterministic
     tokenizer-exact-length-matched synthetic text**
     (`calibration_common.build_exact_length_prompt`, a new function — the
     existing `build_length_targeted_prompt` was audited and found
     unsuitable: discrete-bucket-only, word-count-heuristic, not
     tokenizer-exact). Verified 100% exact match
     (`actual_prompt_token_count == frozen_input_token_count`) across all
     24,000 generated requests. Disclosed as a threat to external
     validity: real token *content* differs from the source trace even
     though token *counts* match exactly.
   - `priority`/`class_id`/`predicted_output_tokens`/`slo_deadline` are
     `SYNTHESIZED_IMPUTED` by `stage0_synthesis_v1`
     (`priority=1.0` constant, `class_id="stage0_uniform"` constant,
     `predicted_output_tokens` = log-normal noise at 20% relative error
     around the real `output_tokens`, `slo_deadline` = a linear proxy ×
     20.0). Carried through **unmodified** by re-invoking
     `synthesize_requests_from_window` with the exact frozen per-window
     `synthesis_seed` recorded in `campaign_freeze.json`'s `cells` — never
     resynthesized independently.
   - `azure_llm_2024::HIGH_PRESSURE` / `burstgpt::HIGH_PRESSURE` /
     `bailian_qwen::HIGH_PRESSURE` are each an aggregate over 40 frozen
     windows per source, not one window — resolved above ("Statistics"
     §Experimental unit): one manifest per source concatenates all 40
     windows' requests, each independently rebased/scaled to 1.5× its
     own window's `lambda_ref` (from `region_assignment_index` in
     `ranking_portability_phase12_campaign_freeze.json`), no
     subsampling.
   - Real per-request rows (real `prompt_tokens`/`actual_output_tokens`/
     `arrival_time_s`, still never prompt text) existed only as an
     **un-committed, regenerable local cache**
     (`pilot_v2_windows_full_cache.json`). **Correction of a prior
     miscommunication in this section**: that cache is *not* hash-verified
     against `phase10_window_hash` — forensic tracing found
     `phase10_window_hash` is an unrelated legacy Phase-10 git-freeze
     identifier (`docs/ARTIFACT_HASH_LEDGER.md`), and the cache's own
     top-level `content_sha256` field is a stale copy of that same
     unrelated value, not a genuine hash of this file's content. The
     correct, semantically-matched check — implemented in
     `build_rq6_workload_manifests.py` and passing 120/120 — is each
     window's own `content_sha256` against the committed compact index's
     and `campaign_freeze.json`'s `window_identities` map.
   - Stable request identity: use the adapter layer's
     `derived_record_id`/`source_record_id` (dropped by the simulator's
     own final `Request.request_id`, which resets to a local per-window
     loop index) as the real-vLLM manifest's `request_id`, since it is
     the only identity stable across regeneration.
2. **SLO-deadline/weight attachment** (blocks stage 6) — **metric pipeline
   implemented (2026-09-03)**: `robustbench.real_llm.rq6_slo_metrics`
   (`scale_request_timing`, `real_slo_violation_rate`) computes
   `slo_violation_rate_real` client-side from `t_done` vs. the manifest's
   frozen `base_slo_deadline_s`/`weight`, per
   `docs/RQ6_REAL_VLLM_CALIBRATION_PROTOCOL_20260902.md`'s definition;
   unit-tested including directly against generated-manifest fields
   (`tests/test_rq6_slo_metrics.py`). **Still blocking stage 6**: no
   frozen document specifies what request population each of the
   calibration bisection's 30 candidate-factor measurements should replay
   against (the full 8,000-request per-source manifest at every iteration
   is not obviously the intended scale, and would be extremely expensive
   across 3 sources). This is a genuine open design question, not decided
   here — deciding it under this task's time pressure would be exactly the
   kind of un-forced methodological shortcut this project has otherwise
   avoided. Concrete next step: decide and freeze this (before any real
   measurement, per this document's own standing rule), then wire
   `rq6_slo_metrics` into an actual bisection runner against a live vLLM
   server.
3. **`slai_faithful` real execution path status**: confirmed built and
   validated (`LSSPSlaiVLLMScheduler`, Wulver job 1219334) since the
   case-selection manifest's own `mechanism_mapping_status` was written
   (which had flagged it as `NOT YET BUILT`). This document supersedes
   that specific field of the case-selection manifest's status without
   modifying the manifest itself (the manifest stays immutable, per
   instruction; this is a documentation update recording that its stated
   blocker has since been resolved).
