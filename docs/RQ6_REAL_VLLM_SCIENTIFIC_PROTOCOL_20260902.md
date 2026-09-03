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
| 5. Calibration protocol (procedure) | **FROZEN, EXECUTABLE (2026-09-03)** | `configs/real_vllm/rq6_calibration_manifest_v2_20260903.json` |
| 6. Calibration execution | **READY TO LAUNCH as of this commit** | runner built, unit-tested, and validated end-to-end against a real local vLLM server (ENGINEERING_ONLY); 120 independent window calibrations to run as a Slurm array against this exact pushed commit, output namespace `artifacts/real_vllm/calibration/rq6/<v2 manifest sha256>/<source>/<window_id>.json`; job IDs are operational/runtime information, recorded in the task report at launch time, not in this frozen document |
| 7. Execution order | **FROZEN, needs a follow-on revision before stage 9** | `artifacts/manifests/rq6_execution_order_20260902.json` was built under the now-corrected concatenation assumption (no `window_id` dimension); tracked as an open item, does not block calibration |
| 8. Statistical analysis plan | **FROZEN (this document, §Statistics)** | |
| 9. Comparative scientific measurement | **NOT STARTED** | requires all 120 window calibrations (stage 6) to complete and validate first |

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

**Execution unit -- corrected 2026-09-03, forensically verified against
Phase-12's own execution code.** A prior draft of this document (see git
history) assumed all 40 windows per source should be concatenated into one
continuous 8,000-request trace, reasoning from GPU-budget concerns alone
without checking how Phase-12 itself executed a window. That assumption
was **wrong** and has been corrected. Direct inspection of
`src/robustbench/ranking_portability/execute_cell.py` shows every
`(source, window, load_region, policy, repetition)` cell constructs a
**fresh `Simulator` instance** and calls **`policy.reset()`** before
running exactly that window's 200 requests (`cell_id` itself embeds a
single `window_id`, e.g. `"burstgpt::burstgpt_stage0_w00::LOW::fifo::rep0"`)
-- there is no cross-window state or arrival-time coupling anywhere in the
frozen Phase-12 campaign. Confirmed independently at the analysis layer:
`src/robustbench/ranking_portability/analysis/ranking_analysis.py`'s own
module docstring states results are "resampled over WINDOWS (never
requests, never (policy,window) rows treated as independent)" [sic --
meaning: windows, not raw rows, are the independent resampling block], and
`per_window_policy_values` builds a `{window_id: {policy_id: value}}` map
that the bootstrap literally resamples over (`rng.choice(windows_x, ...)`).
Each window also has its own, independently-measured `lambda_ref`: all 120
`HIGH_PRESSURE` region-assignment entries have **120 distinct** `lambda_ref`
values, each satisfying `absolute_load_factor == 1.5 x lambda_ref` exactly.

The real-vLLM workload manifests are corrected to match: **each of the 40
windows per source is an independent episode** -- rebased to its own
window-local `t=0`, scaled by `_rebase_and_scale(requests,
absolute_load_factor)` at its own `1.5 x lambda_ref`, with **no**
cross-window arrival offset. All 40 windows are still retained per source
(no window dropped or subsampled) as 40 separate entries in the manifest;
they are simply no longer concatenated. Verified programmatically: every
window's first request has `base_relative_arrival_s == 0.0`, and
reordering/removing windows in the input cache does not change any other
window's generated request timing (`tests/test_rq6_workload_manifests.py::
test_windows_are_independent_episodes_not_concatenated`).

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
| azure_llm_2024 | `artifacts/manifests/rq6_real_vllm/rq6_workload_azure_llm_2024_20260903.json` | `dc51e154798d31ee780ad9f7e1a0655c0f25787b0e881fbf9ec1807f47f72ffc` | 40 | 8,000 |
| burstgpt | `artifacts/manifests/rq6_real_vllm/rq6_workload_burstgpt_20260903.json` | `45aac8de3f9329af07b9e457f3e603900e34c03974fab2fbd919fa391e81d4e2` | 40 | 8,000 |
| bailian_qwen | `artifacts/manifests/rq6_real_vllm/rq6_workload_bailian_qwen_20260903.json` | `4cd96da756d2362083944f9b2a1315e2efdcd7b2b4995c3be338914f1d4b8614` | 40 | 8,000 |

(Hashes above supersede an earlier 2026-09-03 freeze of the same three
paths that concatenated windows; regenerated after the execution-unit
correction above. 8,000 requests/source is still 40 windows x 200
requests -- only the per-window independence, not the counts, changed.)

Generator: `scripts/real_vllm/build_rq6_workload_manifests.py`. Validator:
`scripts/real_vllm/validate_rq6_workload_manifests.py`, output
`artifacts/validation/rq6_real_vllm_manifest_validation.json` (uncommitted,
regenerable -- reproduce by re-running the validator against the committed
manifests + inputs above); all three sources `passed: true`, zero problems,
as of this freeze. Tests: `tests/test_rq6_workload_manifests.py` (18 cases:
determinism, all-window inclusion, request-order/independence/timing
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

**Calibration population -- resolved 2026-09-03 (see "Calibration
population" under "Statistics" below).** An earlier draft of this section
left open what request population each bisection candidate should replay
against, noting that the full 8,000-request per-source manifest was not
obviously the right scale. That question is now moot: per the corrected
execution-unit finding (see "Execution unit -- corrected 2026-09-03"
above), the calibration unit is one frozen window (200 requests), not any
per-source population — `CALIBRATION_UNIT = ONE_FROZEN_WINDOW`, 120
independent calibrations. The live bisection runner
(`robustbench.real_llm.rq6_calibration.bisect_lambda_ref_real`) is built,
unit-tested (`tests/test_rq6_calibration.py`, 14 cases), and validated
end-to-end against a real local vLLM server
(ENGINEERING_ONLY_NOT_SCIENTIFIC_EVIDENCE, 2026-09-03: 32-candidate
bisection, reset barrier passed 32/32 candidates, converged cleanly).

## Episode reset (frozen 2026-09-03)

```
SERVER_RESTART_PER_WINDOW      = NO
MODEL_RELOAD_PER_WINDOW        = NO
LOGICAL_ENGINE_EPISODE_RESET   = YES
```

The model stays loaded across all 120 window calibrations a given Slurm
array task's server process handles per source shard; only the *serving
state* is reset between episodes (windows) and between bisection
candidates within a window. This is not a special server-side reset
operation: the runner's replay design (`rq6_calibration.replay_window_once`)
only returns once every one of a candidate's dispatched requests has
already received an HTTP response, so vLLM's running/waiting queues are
empty by construction before the next candidate or window begins; this is
verified as a defense-in-depth check via vLLM's own `/metrics`
(`vllm:num_requests_running`, `vllm:num_requests_waiting`) before every
single candidate measurement (`rq6_calibration.check_reset_barrier`).
Prefix caching is passed `--no-enable-prefix-caching` explicitly at server
start, so no KV-block reuse can leak across requests or windows regardless
of prompt content overlap. No held/admission-control state exists during
calibration (`vllm_faithful` is vLLM's native FCFS, no custom
`--scheduler-cls`). Full contract:
`configs/real_vllm/rq6_calibration_manifest_v2_20260903.json`'s
`episode_reset_contract`.

## Engineering recovery / environment

```
ENGINEERING_RECOVERY_BRANCH = engineering/lssp-rq6-wulver-recovery-20260902
ENGINEERING_RECOVERY_SHA    = 52ef9fff1dcb49ca729f91d24e1aed077c72a6b0
ENVIRONMENT_SPEC_PATH       = requirements-real-vllm.txt
ENVIRONMENT_SPEC_SHA256     = de46e1134fbd2aff7d2ad378dc4e516e18bd4795137d1c96a6e75729b421e3f0
```

## Calibration protocol

See `docs/RQ6_REAL_VLLM_CALIBRATION_PROTOCOL_20260902.md` (v1, historical
record) and its 2026-09-03 update note, plus:

```
CALIBRATION_MANIFEST_V2_PATH   = configs/real_vllm/rq6_calibration_manifest_v2_20260903.json
CALIBRATION_MANIFEST_V2_SHA256 = 839f1ea99982cbfd198aa12c801a5e2e90ee47699b2b75e7b1c67da3878a8d00
CALIBRATION_MANIFEST_V1_PATH   = configs/real_vllm/rq6_calibration_manifest_20260902.json (superseded, left unmodified)
CALIBRATION_MANIFEST_V1_SHA256 = 417dd8d3d07e770c4629beb59d3116b832516d3f59b7230b9a39b93eb7f65d2d
```

Procedure frozen; **executable as of 2026-09-03** — per-window calibration
population resolved (see "Calibration population" below), SLO/weight
metric pipeline implemented (`robustbench.real_llm.rq6_slo_metrics`), and
the live bisection runner (`robustbench.real_llm.rq6_calibration`,
`scripts/real_vllm/run_rq6_calibration.py`) built, unit-tested, and
validated end-to-end against a real local vLLM server
(ENGINEERING_ONLY_NOT_SCIENTIFIC_EVIDENCE).

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
twice-corrected from earlier drafts of this document.** A forensic trace
of the frozen Phase-12 inputs (2026-09-03) found that
`<source>::HIGH_PRESSURE` in the case-selection manifest is **not** a
single window: `ranking_portability_phase12_campaign_freeze.json`'s
`region_assignment_index` scales all **40** frozen windows per source
(`{source}_stage0_w00..w09` + `{source}_pilot_v2_w10..w39`) independently
to `1.5×` each window's own FIFO `lambda_ref`, and `HIGH_PRESSURE` is the
label for that aggregate region, not one window's identity.

**Second correction (2026-09-03, same day, before any measurement was
taken):** the first correction above then wrongly concluded that the 40
windows should be *concatenated* into one continuous per-source trace,
reasoning only from GPU-budget concerns. That was never checked against
how Phase-12 itself executed a window, and was wrong. Direct inspection of
`execute_cell.py` and `ranking_portability/analysis/ranking_analysis.py`
(see "Execution unit" above) establishes that Phase-12 treats each of the
40 windows per source as an **independent** unit — fresh simulator state
per window, and bootstrap resampling performed **over windows**, not over
repetitions of one long trace. The real-vLLM design is corrected to match:
**the window (200 requests), not the concatenated 8,000-request source
trace, is both the calibration unit (see "Calibration population" below)
and the eventual scientific-comparison sampling unit.** No window is
dropped or subsampled — this still uses the complete frozen
`HIGH_PRESSURE` definition (all 40 windows per source), just executed and
aggregated the way Phase-12 itself did.

**Calibration population (frozen 2026-09-03, before any real calibration
measurement):**
```
CALIBRATION_UNIT           = ONE_FROZEN_WINDOW
REQUESTS_PER_CALIBRATION_UNIT = 200
N_CALIBRATION_UNITS        = 120   (= 3 sources x 40 windows/source)
REFERENCE_POLICY           = vllm_faithful   (unchanged)
```
Each of the 120 (source, window) pairs is calibrated independently: the
already-frozen bisection rule (unchanged, see "Calibration protocol"
below) runs against exactly that window's 200 requests, producing
`real_lambda_ref(source, window)`, from which
`real_HIGH_PRESSURE(source, window) = 1.5 x real_lambda_ref(source,
window)` — exactly parallel to how the simulator's own
`region_assignment_index` was built. **Not** used: the full 8,000-request
per-source concatenation as one calibration unit; a subset of windows;
separate SLAI calibration; averaging `lambda_ref` across windows before
defining `HIGH_PRESSURE`.

**Open follow-on item (does not block calibration, must be resolved
before stage 9):** the already-frozen `rq6_execution_order_20260902.json`
enumerates `(policy, source, repetition)` triples with no `window_id`
dimension — built under the now-corrected concatenation assumption ("one
run unit = one full run of the source's manifest"). Its exact
per-window replicate structure for the eventual SLAI-vs-vLLM comparison
(stage 9) is not re-derived here, since that stage is explicitly out of
this correction's scope (calibration only) — tracked as an open item, not
silently left presented as still-valid.

For each (policy, source, window) unit, the eventual stage-9
repetition-level ANWG measurements are the population resampled with
replacement (bootstrap, ≥2,000 resamples, matching the simulator plan's
`≥2,000`-resample convention, and matching Phase-12's own window-level
block-bootstrap), producing a 95% CI on each cell's ANWG and
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
   (`tests/test_rq6_slo_metrics.py`). **Calibration population — resolved
   (2026-09-03)**: see "Calibration population" under "Statistics" above —
   `CALIBRATION_UNIT = ONE_FROZEN_WINDOW`, 120 independent per-window
   calibrations, never the concatenated per-source trace. Remaining
   concrete next step: implement and validate the episode-reset barrier
   between window calibrations (see "Episode reset" below), then run the
   live bisection runner (`src/robustbench/real_llm/rq6_calibration.py`,
   `scripts/real_vllm/run_rq6_calibration.py`) on Wulver.
3. **`slai_faithful` real execution path status**: confirmed built and
   validated (`LSSPSlaiVLLMScheduler`, Wulver job 1219334) since the
   case-selection manifest's own `mechanism_mapping_status` was written
   (which had flagged it as `NOT YET BUILT`). This document supersedes
   that specific field of the case-selection manifest's status without
   modifying the manifest itself (the manifest stays immutable, per
   instruction; this is a documentation update recording that its stated
   blocker has since been resolved).
