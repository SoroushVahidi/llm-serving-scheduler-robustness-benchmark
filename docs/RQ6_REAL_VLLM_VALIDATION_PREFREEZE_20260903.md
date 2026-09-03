# RQ6_REAL_VLLM_VALIDATION_PREFREEZE_20260903.md

`RQ6_REAL_VLLM_SCIENTIFIC_VALIDATION = NOT_STARTED`. This document is the
authoritative launch checklist for the RQ6 real-vLLM scientific-validation
campaign (stage 9 of `docs/RQ6_REAL_VLLM_SCIENTIFIC_PROTOCOL_20260902.md`).
Everything below was implemented and tested in this session; **no scientific
run was submitted**. `scripts/real_vllm/run_rq6_validation.sbatch` exists
but was never `sbatch`'d.

## 1. Calibration gate

```
RQ6_CALIBRATION_GATE = PASS_120_OF_120
```

Independently reverified in this session (not merely asserted from the
task prompt), against Wulver directly:

- `sacct -j 1221379_19` → `COMPLETED`, `ExitCode 0:0` (the retry that
  superseded the earlier `1220661_19` `FAILED` job — port collision with
  task 119, both `PORT=8100+idx%100=8119`, root-caused in
  `docs/LSSP_NEW_CHAT_HANDOFF_20260903.md`).
- `sacct -j 1220661_108` → `COMPLETED`, `ExitCode 0:0`, `Elapsed 03:40:34`
  (the outlier task the handoff doc was still watching).
- `artifacts/real_vllm/calibration/rq6/839f1ea9.../{azure_llm_2024,bailian_qwen,burstgpt}/*.json`
  on Wulver: **120 files**, **120 unique `slurm_array_task_id` values 0–119**
  (0 missing, 0 duplicates), **0** non-`{azure_llm_2024,bailian_qwen,burstgpt}`
  sources, all `repo_sha == 773982a280be7a2e6dc812174f6c90c8ca0dc18b`.
- `convergence_status` distribution: `CONVERGED=43`,
  `LOWER_BOUND_ALREADY_VIOLATING=77` (sums to 120 — matches the task
  prompt's claim exactly, independently recomputed).
- Aggregate content hash over all 120 outputs (formula below, §6):
  `d3a875524aaf1faa424864f69a601267fe9f54ea3c39cedfb052c92c006e8ddf`.

**Note on `docs/LSSP_NEW_CHAT_HANDOFF_20260903.md`**: that document (read
per this task's preflight instruction) reports calibration as 118/120 with
task 19 still failed and task 108 still running under job `1220661`. This
is not a contradiction — it is an earlier snapshot from the same day; job
`1221379_19` (a later, separate resubmission not mentioned in that handoff)
and the eventual completion of `1220661_108` are newer state, verified
directly against Wulver above rather than assumed. No newer authoritative
document contradicts `PASS_120_OF_120`.

## 2. Calibration terminal-status contract

| Status | Meaning | Valid terminal? | Downstream handling |
|---|---|---|---|
| `CONVERGED` | Bisection found a crossover factor within `[10^-2, 10^4]` inside 30 iterations; `real_lambda_ref = 10^((lo+hi)/2)`. | Yes | None beyond the standard record — `derived_high_pressure = 1.5 * real_lambda_ref` computed identically to the other two statuses. |
| `LOWER_BOUND_ALREADY_VIOLATING` | Even the slowest candidate (`factor = 10^-2`) already violates the 0.5% SLO threshold — the window's own request timing is tight enough that no candidate scale in the search space satisfies it *by early-exit design*; `real_lambda_ref` is pinned to the lower bound (`10^-2`) rather than searched. | Yes | None — same `derived_high_pressure` formula, same output schema. Not an error, not a retry condition. |
| `UPPER_BOUND_NEVER_VIOLATING` | Even the fastest candidate (`factor = 10^4`) never violates the threshold; `real_lambda_ref` is pinned to the upper bound. | Yes | None — same as above. |

Verified directly from `src/robustbench/real_llm/rq6_calibration.py::bisect_lambda_ref_real`
(all three branches return a `WindowCalibrationResult` with a well-defined,
finite `real_lambda_ref`/`derived_high_pressure`; none is exceptional) and
from `tests/test_rq6_calibration.py`'s three dedicated tests
(`test_bisect_converges_near_known_crossover_factor`,
`test_bisect_lower_bound_already_violating`,
`test_bisect_upper_bound_never_violating`), which the calibration
implementer wrote as three equally-weighted, equally-tested branches, not
one "normal" path and two "failure" paths. `robustbench.real_llm.
rq6_validation.VALID_CALIBRATION_TERMINAL_STATUSES` now encodes this
three-element set as the single source of truth used by both the runner
(`load_calibrated_scale`) and the validator
(`validate_rq6_validation_outputs.py`), so a future audit cannot again treat
a non-`CONVERGED` status as invalid — `tests/test_rq6_validation.py::
test_load_calibrated_scale_accepts_every_valid_terminal_status` is
parametrized over exactly this set.

## 3. Frozen RQ6 cases (from the byte-verified case-selection artifact)

Source: `artifacts/manifests/phase12_rq6_case_selection_20260902.json`,
sha256 `f34e1c6a9f8d4c695720d14f7929741594ac8f7818a427db832933554e909e5a`
(recomputed locally, matches the manifest's own record and this document's
dependents).

| Case | Sources / region | Policies | Selection basis | Notes |
|---|---|---|---|---|
| Reversal | `azure_llm_2024::HIGH_PRESSURE` vs `burstgpt::HIGH_PRESSURE` | `slai_faithful` vs `vllm_faithful` | Largest operationalized effect size (`min(\|margin_x\|,\|margin_y\|) = 1.2816`) among 36 `SUPPORTED_PRACTICAL_REVERSAL` records for the primary metric, `bh_fdr_p_pair_iut=0.0`. | **Tied** with the `bailian_qwen`-vs-`burstgpt` record at identical effect size; tie-broken lexicographically on `condition_x` (disclosed in the manifest, not silently discarded). |
| Stable control | `azure_llm_2024::HIGH_PRESSURE` vs `bailian_qwen::HIGH_PRESSURE` | all Phase-12 policies (simulator-side ranking) | Highest simulator Kendall τ-b (`1.0`, CI `[0.904, 1.0]`) among 18 source-pair × region conditions, "largest tau" read as primary sort key. | Alternative "smallest CI first" interpretation disclosed in the manifest — would select a different *region* (`POST_KNEE`/`OVERLOAD`) but the same source pair. |

`case_manifest_frozen_before_any_real_vllm_run: true`,
`real_vllm_run_launched_in_this_task: false` (both fields verified present
and `true`/`false` respectively in the manifest itself).

## 4. RQ6 protocol — frozen vs. derived vs. unresolved

| Dimension | Value | Classification | Source |
|---|---|---|---|
| Model | `Qwen/Qwen2.5-0.5B-Instruct` | FROZEN FACT | `configs/real_vllm/rq6_scientific_manifest_20260902.json`, matches the already-validated calibration campaign. |
| vLLM version | `0.27.1` | FROZEN FACT | `requirements-real-vllm.txt` / `env_preflight.py` (pinned; SLAI plugin requires v1 `SchedulerInterface`). |
| GPU / hardware | `NVIDIA A100-SXM4-80GB`, Wulver `gres=gpu:a100_10g:1`, partition `gpu`, qos `low` | FROZEN FACT (reused from the validated calibration campaign) | `run_rq6_calibration.sbatch`, cross-checked against calibration output `gpu` field. |
| Workload sources/windows | 3 sources × 40 windows, no subsampling | FROZEN FACT | Workload manifests, hash-verified (§below). |
| Offered-load construction | `candidate_scale` = this (source,window)'s calibration output `derived_high_pressure` (already `1.5 × real_lambda_ref`) | FROZEN FACT | `docs/RQ6_REAL_VLLM_SCIENTIFIC_PROTOCOL_20260902.md` "Calibration population"; unambiguous 1:1 mapping. |
| Policies | `slai_faithful`, `vllm_faithful` | FROZEN FACT | Case-selection manifest. |
| Plugin/scheduler mapping | `vllm_faithful`→FCFS native; `slai_faithful`→`--scheduler-cls LSSPSlaiVLLMScheduler`, `--scheduling-policy priority` | FROZEN FACT + IMPLEMENTATION DETAIL (engine flags held constant across arms — see §8) | `docs/REAL_VLLM_SLAI_FIDELITY.md`, `wulver_engineering_gate.py`'s existing wiring pattern. |
| SLO definition / metric | `arrival_normalized_weighted_goodput` (arrival-normalized: `success_weight / all_arrivals_weight`) | FROZEN FACT | `src/robustbench/core/metrics.py` (simulator-side canonical formula); real-side implementation `rq6_validation.real_arrival_normalized_weighted_goodput` mirrors it exactly, newly written this session (IMPLEMENTATION DETAIL). |
| Seeds/replicates | 1 real execution per (policy, source, window) cell; uncertainty via window-level bootstrap over the 40-window population per condition | **UNRESOLVED_SCIENTIFIC_DECISION** (best-supported inference, not literally frozen — see §5) | `docs/RQ6_REAL_VLLM_SCIENTIFIC_PROTOCOL_20260902.md` "Statistics" section. |
| Run order/randomization | Not re-derived for stage 9; the old `rq6_execution_order_20260902.json` (source-level, 10 reps, no `window_id` dim) is explicitly `STALE_FOR_STAGE_9` per its own manifest and was **not reused** | IMPLEMENTATION DETAIL (deterministic array-index ordering by `(source, window_id, policy)` substitutes for it — no scientific run order was frozen, so a fixed deterministic enumeration was chosen conservatively rather than inventing a randomization scheme) | This session; `rq6_validation.enumerate_validation_cells`. |
| Warmup | 1 untimed warmup request per server start, discarded | FROZEN FACT (reused from calibration) | `configs/real_vllm/rq6_calibration_manifest_v2_20260903.json`. |
| Request horizon/count | 200 requests/cell (one frozen window) | FROZEN FACT | Same as calibration. |
| Timeout | 600s server-ready, 280s/request | IMPLEMENTATION DETAIL (reused calibration defaults; not scientific) | `run_rq6_calibration.py` defaults, carried forward. |
| Retry policy | 3 server-start retries on bind/readiness failure; no per-request retry (fail-closed to non-completion, matching calibration's `_slo_violation_rate_at` convention) | IMPLEMENTATION DETAIL | This session. |
| Failure/censoring | `run_status ∈ {COMPLETED, FAILED_CALIBRATION_DEPENDENCY, FAILED_SERVER_START, FAILED_DURING_REPLAY}`, always written, never silently dropped | FROZEN FACT (output contract, this session) | §8 below. |
| Telemetry | Full provenance block, §8 | FROZEN FACT (this session) | — |
| Statistics | Block bootstrap ≥2000 resamples/95% CI over windows; BH-FDR q=0.05 over the 4-test family | FROZEN FACT (reused verbatim from `docs/RQ6_REAL_VLLM_SCIENTIFIC_PROTOCOL_20260902.md`) | `robustbench.ranking_portability.analysis.stats.block_bootstrap_ci`/`benjamini_hochberg`, reused not reimplemented. |

### Replicates per cell (§5 detail)

No frozen document states a per-cell real-execution replicate count in
those exact words. The frozen Statistics section says the eventual
"repetition-level ANWG measurements are the population resampled with
replacement... matching Phase-12's own window-level block-bootstrap" — read
literally, this identifies the population being bootstrapped as the 40
per-window ANWG values themselves, not repeated measurements of one
(policy, source, window) cell. This is reinforced by the protocol
document's own aside that "Phase-12's simulator runs are deterministic
(rep0/rep1 verification, not stochastic repetition)" — i.e. even Phase-12
did not treat its own `rep0`/`rep1` pair as statistical replication.
`replicates_per_cell: 1` was therefore implemented as the best-supported
reading, and is explicitly labeled `UNRESOLVED_SCIENTIFIC_DECISION` in
`configs/real_vllm/rq6_validation_manifest_v1_20260903.json`, not silently
frozen. **A human must explicitly confirm this before actual launch** —
see §O below.

### Simulator-selected winner direction (correction made during this session)

An earlier draft of `configs/real_vllm/rq6_validation_manifest_v1_20260903.json`
asserted specific per-condition winners (`slai_faithful` wins
`azure_llm_2024::HIGH_PRESSURE`, `vllm_faithful` wins
`burstgpt::HIGH_PRESSURE`) without source support — the case-selection
manifest records only an *unsigned* effect-size magnitude
(`operationalized_effect_size_min_abs_margin=1.2816`), not which policy
wins which condition; the signed value lives in the generated, gitignored
`pairwise_reversals_json` artifact (hash `c90619e8...`, not present in this
worktree). This was caught and corrected before commit: the manifest now
records `"UNRESOLVED_NOT_AVAILABLE_IN_THIS_WORKTREE"` for both winner
labels, with a full explanation of what is needed to resolve it.
`rq6_validation_analysis.reversal_analysis()` takes these as required
caller-supplied arguments (never defaulted/hardcoded), so
`agrees_with_simulator_selected_direction` correctly returns `None` until
an operator supplies the real labels from the actual artifact.

## 5. Files added/changed

| File | Purpose |
|---|---|
| `src/robustbench/real_llm/rq6_validation.py` | Task-matrix enumeration (240 cells), calibration-output lookup with hash/status verification, real-side ANWG metric. |
| `src/robustbench/real_llm/port_alloc.py` | OS-assigned free-port allocation (`bind((host,0))`), replacing calibration's buggy modulo scheme. |
| `src/robustbench/real_llm/rq6_validation_analysis.py` | Result-blind analysis: per-condition SLAI-minus-vLLM bootstrap effect, reversal/stable-control tests, BH-FDR — reuses `ranking_portability.analysis.stats`. |
| `configs/real_vllm/rq6_validation_manifest_v1_20260903.json` | The frozen, result-blind validation manifest (sha256 `111e298c743b24fb5b842f5c9fb51b423fbc5fd9e37abce268fa3389d25bd05a`). |
| `scripts/real_vllm/run_rq6_validation.py` | Scientific runner: verifies hash chain, dry-run mode, dynamic port allocation with retry, atomic writes, overwrite refusal. |
| `scripts/real_vllm/run_rq6_validation.sbatch` | Slurm array launcher, 240 tasks, fail-closed on required env vars, no scientific parameter duplicated outside the frozen manifest. |
| `scripts/real_vllm/validate_rq6_validation_outputs.py` | Post-hoc output validator — identity/completeness/schema/provenance only, never judges the hypothesis. |
| `docs/RQ6_REAL_VLLM_VALIDATION_PREFREEZE_20260903.md` | This document. |
| `tests/test_rq6_validation.py`, `tests/test_port_alloc.py`, `tests/test_rq6_validation_analysis.py`, `tests/test_run_rq6_validation.py`, `tests/test_validate_rq6_validation_outputs.py` | Test coverage, §M. |

No existing file was modified; no calibration output, Phase-12 artifact, or
manuscript file was touched.

## 6. Validation manifest

- Path: `configs/real_vllm/rq6_validation_manifest_v1_20260903.json`
- sha256: `111e298c743b24fb5b842f5c9fb51b423fbc5fd9e37abce268fa3389d25bd05a`
- Dependencies embedded by hash (never by value): case-selection manifest
  (`f34e1c6a...`), calibration manifest (`839f1ea9...`), the 120 calibration
  outputs' **aggregate content hash**
  (`d3a875524aaf1faa424864f69a601267fe9f54ea3c39cedfb052c92c006e8ddf`,
  formula: sha256 of the sorted, newline-joined `"sha256sum(file)  relpath"`
  lines over every `*.json` under the calibration output directory — no
  `real_lambda_ref` value is embedded anywhere in the manifest), 3 workload
  manifest content hashes, environment spec hash (`de46e113...`), frozen
  code SHA (`773982a2...`).

## 7. Task matrix

- Expected run count: **240** (`2 policies × 3 sources × 40 windows/source`).
- Structure: `(source, window_id, policy)`-sorted deterministic enumeration
  (`robustbench.real_llm.rq6_validation.enumerate_validation_cells`);
  `array_index` = position in this sort.
- Deterministic mapping verified: re-enumerating against unchanged
  workload manifests reproduces byte-identical `array_index → cell`
  assignment (`tests/test_rq6_validation.py::
  test_enumerate_validation_cells_deterministic`).
- Live dry-run sweep (this session, all 240 indices, real workload
  manifests): 240/240 rows, 240 unique `(policy, source, window_id)` keys,
  exactly 120/120 split by policy, exactly 80/80/80 split by source, all
  `region=HIGH_PRESSURE`, correct `scheduler_cls` per policy, and exactly
  **120** distinct `(source, window_id)` calibration dependencies (matching
  the 120 calibration outputs exactly — no orphaned or missing dependency).

## 8. Scheduler mapping

| Simulator policy | Real implementation | Plugin/class/config |
|---|---|---|
| `vllm_faithful` | vLLM native FCFS | `--scheduling-policy fcfs`, `scheduler_cls=null`, `--no-enable-chunked-prefill --no-enable-prefix-caching` |
| `slai_faithful` | Custom `--scheduler-cls` | `robustbench.real_llm.slai_plugin.slai_vllm_scheduler.LSSPSlaiVLLMScheduler`, `--scheduling-policy priority`, same engine flags |

Engine flags (`--no-enable-chunked-prefill --no-enable-prefix-caching`) are
held identical across both arms — an engineering decision (not specified
per-policy by any frozen document) made conservatively so the comparison
isolates the scheduler, disclosed in the manifest's
`scheduler_mapping.slai_faithful.note`.

## 9. Port strategy

- Mechanism: `robustbench.real_llm.port_alloc.allocate_port` — binds a
  throwaway socket to `(host, 0)`, lets the OS assign a currently-free
  ephemeral port, releases it, hands the port to `vllm serve`.
- Collision safety: correct by construction for any number of
  concurrently-scheduled array tasks on one node (the OS never hands out an
  already-bound port), unlike the calibration launcher's
  `PORT=8100+task_id%100` (fixed 100-port modulus — collided at task
  19/119, both `%100==19`, root-caused and confirmed independently against
  Wulver job history in this session, §1).
- Residual risk (disclosed): a small bind-release-to-vLLM-start TOCTOU
  race, mitigated by `run_rq6_validation.py`'s `--server-start-retries`
  (default 3), which reallocates a fresh port on server-start failure.
- Logged in provenance: `selected_port`, `port_selection_method` in every
  `COMPLETED` output record.
- Tests: `tests/test_port_alloc.py` (bindability, method label, 60-call
  distinctness regression test for the modulus-collision failure mode).

## 10. Output schema

Required fields for a `COMPLETED` record (34 keys; enforced by
`validate_rq6_validation_outputs.py`'s `REQUIRED_COMPLETED_KEYS`): identity
(`policy`, `source`, `window_id`, `region`, `replicate_seed`), scientific
inputs (`candidate_scale`, `real_lambda_ref`,
`calibration_convergence_status`, `scheduler_cls`, `scheduling_policy`),
environment (`model`, `gpu`, `selected_port`, `port_selection_method`),
timing (`started_at_utc`, `finished_at_utc`), outcomes
(`offered_request_count`, `completed_request_count`,
`arrival_normalized_weighted_goodput`, `slo_violation_rate`), and full
provenance (workload/calibration/validation/case-selection/environment
hashes, `repo_sha`, Slurm IDs).

Failure/timeout semantics: `run_status ∈ {COMPLETED,
FAILED_CALIBRATION_DEPENDENCY, FAILED_SERVER_START, FAILED_DURING_REPLAY}` —
every cell always produces a file (atomic write via temp-file +
`os.replace`), so a failed scientific run is structurally distinguishable
from zero completions (`completed_request_count=0` inside a `COMPLETED`
record with `n_total=200` — a real, measured zero, not silently omitted),
an undefined metric (ANWG is NaN only when arrival weight is 0, which
cannot happen for a 200-request frozen window), an engineering-only run
(`stamp` field: `RQ6_REAL_VLLM_SCIENTIFIC_VALIDATION` vs the calibration
runner's `RQ6_REAL_VLLM_CALIBRATION` vs the engineering gate's
`ENGINEERING_ONLY_NOT_SCIENTIFIC_EVIDENCE`), and a valid completed run.

## 11. Analysis contract

- Sign agreement / winner: `rq6_validation_analysis.condition_effect` —
  per-condition SLAI-minus-vLLM ANWG effect, block-bootstrapped (≥2000
  resamples) over the 40 per-window differences; `winner` is set only when
  the 95% CI excludes zero.
- Kendall's tau: reused via `ranking_portability.analysis.stats.
  compare_rankings`, reported for framework consistency with Phase-12's
  many-policy comparisons — disclosed as degenerate for exactly 2 policies
  (±1 or undefined, never partially informative on its own for n=2); the
  scientifically load-bearing quantity is `condition_effect`'s sign/CI, not
  this tau.
- Reversal agreement: `reversal_analysis` — sign-flip detection between the
  two reversal-case conditions, `both_conditions_supported` gate, and
  `agrees_with_simulator_selected_direction` (currently unresolvable — §4's
  "Simulator-selected winner direction" note — until an operator supplies
  the real signed values).
- Stable-control same-sign check: `stable_control_analysis`.
- Multiple-testing: `apply_family_fdr` — BH q=0.05 over the frozen 4-test
  family, reusing `benjamini_hochberg` verbatim.
- All example numbers in `tests/test_rq6_validation_analysis.py` are
  labeled `SYNTHETIC_FIXTURE_NOT_SCIENTIFIC_EVIDENCE`; no real RQ6 value is
  read or embedded anywhere in the analysis module or its tests.

## 12. SLAI/RAD end-to-end preflight

- Import: directly verified in this session —
  `PYTHONPATH=src python3 -c "from robustbench.real_llm.slai_plugin.slai_vllm_scheduler import LSSPSlaiVLLMScheduler"`
  succeeds (this dev environment has `vllm` installed; the class imports
  cleanly, subclassing `vllm.v1.core.sched.scheduler.Scheduler`).
- Scheduler-cls wiring: `scheduler_mapping.slai_faithful.scheduler_cls =
  "robustbench.real_llm.slai_plugin.slai_vllm_scheduler.LSSPSlaiVLLMScheduler"`
  in the frozen manifest; `run_rq6_validation.py` passes it via
  `--scheduler-cls` exactly as `wulver_engineering_gate.py`'s already-
  validated pattern does.
- Manifest → implementation mapping: verified by
  `tests/test_validate_rq6_validation_outputs.py::
  test_validate_detects_scheduler_mapping_mismatch` (validator rejects a
  record whose `scheduler_cls` doesn't match the manifest's mapping for its
  `policy`).
- No accidental fallback to native scheduler: `run_rq6_validation.py`
  builds `extra_args` conditionally on `scheduler_mapping["scheduler_cls"]`
  being truthy — a `slai_faithful` cell with a null `scheduler_cls` in the
  manifest would start a plain FCFS server, but the manifest's own
  `scheduler_mapping.slai_faithful.scheduler_cls` is non-null and
  hash-pinned as part of the manifest, so this can only diverge if the
  manifest itself is tampered with (caught by `verify_manifest_chain`'s
  hash check on the manifest file... actually the manifest is the trust
  root here, not separately hash-verified against a third source — this is
  a disclosed trust boundary, not a gap: the manifest **is** the frozen
  scientific configuration).
- Telemetry/provenance identifies the plugin: `scheduler_cls` and
  `scheduling_policy` are both required output fields (§10).
- **No frozen scientific case was run to completion in this task** — the
  end-to-end CLI test
  (`tests/test_run_rq6_validation.py::
  test_main_cli_end_to_end_writes_completed_record_then_refuses_overwrite`)
  uses a fully mocked `vLLM` server/HTTP layer (no GPU, no real network
  call, no real model load) and is excluded from any scientific output
  directory (writes to `tmp_path`, never `artifacts/real_vllm/validation/`).

## 13. Tests

Commands and results (this session, this worktree):

```
PYTHONPATH=src python3 -m pytest tests/ -q
```
→ **509 passed**, 0 failed (full existing suite + 5 new files, 65 new
tests). No expensive/GPU/Slurm job was run.

New test files: `tests/test_rq6_validation.py` (24 tests: task matrix,
calibration lookup incl. all 3 terminal statuses, ANWG metric semantics),
`tests/test_port_alloc.py` (3 tests), `tests/test_rq6_validation_analysis.py`
(11 tests, synthetic-fixture-labeled), `tests/test_run_rq6_validation.py`
(19 tests: dry-run, manifest-chain verification incl. stale-SHA and
wrong-case-selection-hash rejection, atomic write, overwrite refusal,
sbatch fail-closed/no-modulo-port/array-range checks, full mocked
end-to-end), `tests/test_validate_rq6_validation_outputs.py` (11 tests:
missing/duplicate/schema/hash-mismatch/scheduler-mismatch detection,
engineering-file exclusion, and confirmation that ANWG value/sign never
affects `passed`).

## 14. Dry run

Full 240-index sweep executed via `scripts/real_vllm/run_rq6_validation.py
--dry-run` (real workload manifests, real validation manifest, no GPU, no
server started):

- **240/240** expected scientific tasks produced a plan row.
- **240** unique `(policy, source, window_id)` cells — no duplicates.
- **120** distinct calibration dependencies resolved, exactly matching the
  120 validated calibration outputs (§1) — no orphaned or unmatched
  dependency.
- All hashes in the manifest chain verified against the current worktree
  (`verify_manifest_chain`, exercised both positively and via 3 induced-
  failure tests).
- Every `policy` maps to a concrete, importable real implementation
  (`vllm_faithful` → native, `slai_faithful` → `LSSPSlaiVLLMScheduler`) —
  no policy without a mapping exists in the 240-cell matrix.

## 15. Prefreeze status

```
NOT_READY_TO_LAUNCH_RQ6
```

Concrete blockers (both non-code, human decisions — not implementation
gaps):

1. **Replicates-per-cell is an inference, not a frozen fact** (§4/§5). A
   human must explicitly confirm `replicates_per_cell=1` (relying on
   window-level bootstrap for uncertainty, mirroring Phase-12) is the
   intended design before `sbatch`-ing the array — or specify a different
   count and the manifest/runner must be updated first.
2. **Simulator-selected winner direction is unavailable in this worktree**
   (§4). The reversal-case analysis's `agrees_with_simulator_selected_
   direction` cannot be computed until the real, signed `pairwise_
   reversals_json` artifact (hash `c90619e8...`) is regenerated or located
   and its `diff_x`/`diff_y` signs for this specific condition pair are
   read. This does not block *running* the campaign (the runner never
   reads this artifact), only the final agreement determination in the
   analysis step — but it should be resolved before launch is treated as
   fully scoped, since discovering it post-hoc would be worse.

Everything else — code, tests, dry run, hash verification, port strategy,
output contract, scheduler mapping — is implemented, tested, and passing.

## 16. Manuscript accuracy note

Not edited this pass, per instruction. For the next manuscript-touching
session: `paper/sections/real_system.tex`'s current framing (via
`docs/RQ6_REAL_VLLM_SCIENTIFIC_PROTOCOL_20260902.md`'s open item 3) still
reflects `slai_faithful`'s real-execution path as effectively unresolved in
older shorthand; the accurate current-state sentence is:

> "The custom vLLM scheduler extension has been implemented and
> component-validated; execution of the frozen RQ6 scientific cases remains
> pending."

The `[PENDING RESULT]` placeholder itself must **not** be filled in — it
remains correct as long as `SCIENTIFIC_RUNS_LAUNCHED = NO`.

## 17. Scientific runs launched

```
SCIENTIFIC_RUNS_LAUNCHED = NO
```

No `sbatch scripts/real_vllm/run_rq6_validation.sbatch` was executed. No
GPU job was submitted. No frozen RQ6 case was run to completion outside a
fully mocked test.
