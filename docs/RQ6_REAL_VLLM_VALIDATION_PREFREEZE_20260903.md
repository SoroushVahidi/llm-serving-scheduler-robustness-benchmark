# RQ6_REAL_VLLM_VALIDATION_PREFREEZE_20260903.md

`RQ6_REAL_VLLM_SCIENTIFIC_VALIDATION = NOT_STARTED`. This document is the
authoritative launch checklist for the RQ6 real-vLLM scientific-validation
campaign (stage 9 of `docs/RQ6_REAL_VLLM_SCIENTIFIC_PROTOCOL_20260902.md`).
Everything below was implemented and tested across two sessions; **no
scientific run was submitted**. `scripts/real_vllm/run_rq6_validation.sbatch`
exists but was never `sbatch`'d.

## 0. Session 2 addendum: protocol-ambiguity resolution pass (2026-09-03)

A follow-on session performed a strict resolution pass on the two blockers
this document originally recorded under §15. Summary of outcome (detail
inline in the relevant sections below, still numbered as originally
written):

- **Blocker 2 (simulator-selected reversal-winner direction): RESOLVED.**
  Recovered from an exact, hash-verified, already-committed manuscript
  artifact (`paper/generated/table_data/rq3_reversals.json` on
  `manuscript/lssp-jsc-reviewer-informed-polish-20260903`) whose own
  embedded `pairwise_reversals.json` hash and `analysis_code_git_sha` match
  the frozen case-selection manifest's recorded provenance exactly — not a
  rerun, not a reselection, not an inference from policy names. Result:
  `slai_faithful` wins `azure_llm_2024::HIGH_PRESSURE`
  (`diff_x=+0.5204`, CI excludes 0), `vllm_faithful` wins
  `burstgpt::HIGH_PRESSURE` (`diff_y=-0.3476`, CI excludes 0). See §3/§4.
- **Blocker 1 (replicates-per-cell): RESOLVED — AUTHOR DECISION (2026-09-03).**
  For RQ6, freeze 1 execution per (policy, source, window); the inferential
  resampling unit is the window (40 per source). This RQ6-specific decision
  supersedes the earlier generic ≥5-repetition guidance only for the final
  RQ6 protocol. Rationale: the experimental unit for RQ6 is the workload
  window; uncertainty is estimated by resampling across independent windows;
  repeated executions of an identical window primarily measure serving-engine
  jitter rather than additional workload-level uncertainty; RQ6 tests
  portability of signs/rankings/reversals across windows, not a separate
  stochastic-engine variance component. Decision frozen before any RQ6
  scientific result exists. See §4/"Protocol Reconciliation".
- **A real, unrelated bug was found and fixed**: `verify_manifest_chain`'s
  original exact-equality check (`repo HEAD == manifest's frozen_code_sha`)
  was self-defeating — committing the runner itself necessarily moved HEAD
  past the frozen scientific-protocol SHA, so the check would fail on every
  future invocation. Replaced with a `git merge-base --is-ancestor` check
  (the frozen SHA must be *in* HEAD's history, not equal to it). See §14.
- Manifest content updated (winner direction filled in, stable-control
  provenance cross-verified, replicates-per-cell frozen) →
  **validation-manifest sha256 = `172efb13b30efea440a18644ef852fa2d0b8cc6fee93ea730981b2ac868bd670`** (§6).
  511 tests pass, full 240-cell dry-run reswept clean.
- **No RQ6 scientific run was launched in either session.**

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
| Reversal | `azure_llm_2024::HIGH_PRESSURE` vs `burstgpt::HIGH_PRESSURE` | `slai_faithful` vs `vllm_faithful` | Largest operationalized effect size (`min(\|margin_x\|,\|margin_y\|) = 1.2816`) among 36 `SUPPORTED_PRACTICAL_REVERSAL` records for the primary metric, `bh_fdr_p_pair_iut=0.0`. | **Tied** with the `bailian_qwen`-vs-`burstgpt` record at identical effect size; tie-broken lexicographically on `condition_x` (disclosed in the manifest, not silently discarded). **Simulator direction (recovered, session 2)**: `slai_faithful` wins `azure_llm_2024::HIGH_PRESSURE` (`diff_x=+0.5204`, 95% CI `[0.4516,0.5878]`, excludes 0); `vllm_faithful` wins `burstgpt::HIGH_PRESSURE` (`diff_y=-0.3476`, CI `[-0.4323,-0.2604]`, excludes 0). Source: `paper/generated/table_data/rq3_reversals.json` @ `manuscript/lssp-jsc-reviewer-informed-polish-20260903` commit `e6766c95`, `supported_practical_reversals_primary_metric_sorted_by_effect_size[0]` — its embedded `pairwise_reversals.json` hash (`c90619e8...`) and `analysis_code_git_sha` (`eb574a8...`) match this case-selection manifest's own recorded provenance exactly. |
| Stable control | `azure_llm_2024::HIGH_PRESSURE` vs `bailian_qwen::HIGH_PRESSURE` | all Phase-12 policies (simulator-side ranking) | Highest simulator Kendall τ-b (`1.0`, CI `[0.904, 1.0]`) among 18 source-pair × region conditions, "largest tau" read as primary sort key. | Alternative "smallest CI first" interpretation disclosed in the manifest — would select a different *region* (`POST_KNEE`/`OVERLOAD`) but the same source pair. Re-verified byte-identical (session 2) against `paper/generated/table_data/rq1_rq2_portability.json`, same commit. |

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
| Seeds/replicates | 1 real execution per (policy, source, window) cell; uncertainty via window-level bootstrap over the 40-window population per condition | FROZEN FACT (RQ6-specific author decision, 2026-09-03) | Protocol reconciliation (§4): RQ6-specific design governs; supersedes earlier generic ≥5-repetition guidance for RQ6 only. |
| Run order/randomization | Not re-derived for stage 9; the old `rq6_execution_order_20260902.json` (source-level, 10 reps, no `window_id` dim) is explicitly `STALE_FOR_STAGE_9` per its own manifest and was **not reused** | IMPLEMENTATION DETAIL (deterministic array-index ordering by `(source, window_id, policy)` substitutes for it — no scientific run order was frozen, so a fixed deterministic enumeration was chosen conservatively rather than inventing a randomization scheme) | This session; `rq6_validation.enumerate_validation_cells`. |
| Warmup | 1 untimed warmup request per server start, discarded | FROZEN FACT (reused from calibration) | `configs/real_vllm/rq6_calibration_manifest_v2_20260903.json`. |
| Request horizon/count | 200 requests/cell (one frozen window) | FROZEN FACT | Same as calibration. |
| Timeout | 600s server-ready, 280s/request | IMPLEMENTATION DETAIL (reused calibration defaults; not scientific) | `run_rq6_calibration.py` defaults, carried forward. |
| Retry policy | 3 server-start retries on bind/readiness failure; no per-request retry (fail-closed to non-completion, matching calibration's `_slo_violation_rate_at` convention) | IMPLEMENTATION DETAIL | This session. |
| Failure/censoring | `run_status ∈ {COMPLETED, FAILED_CALIBRATION_DEPENDENCY, FAILED_SERVER_START, FAILED_DURING_REPLAY}`, always written, never silently dropped | FROZEN FACT (output contract, this session) | §8 below. |
| Telemetry | Full provenance block, §8 | FROZEN FACT (this session) | — |
| Statistics | Block bootstrap ≥2000 resamples/95% CI over windows; BH-FDR q=0.05 over the 4-test family | FROZEN FACT (reused verbatim from `docs/RQ6_REAL_VLLM_SCIENTIFIC_PROTOCOL_20260902.md`) | `robustbench.ranking_portability.analysis.stats.block_bootstrap_ci`/`benjamini_hochberg`, reused not reimplemented. |

### Protocol reconciliation (replicates per cell)

Early generic plan (2026-08-31): ≥5 repeated executions per `(scheduler, workload family, load region)` cell; repetition-level bootstrap (`docs/REAL_SYSTEM_VALIDATION_PLAN.md`, cross-referenced by `docs/EXPERIMENT_CAMPAIGN_PLAN.md`).

Final RQ6-specific design (frozen 2026-09-03): 1 execution per `(policy, source, window)` cell; 40 windows per source; window-level bootstrap for uncertainty, matching Phase-12’s inferential unit. This decision is RQ6-specific and supersedes the earlier generic guidance only for RQ6. It was frozen before any RQ6 real-system results exist, and was therefore not chosen based on observed outcomes.

**This is not resolvable by picking either number myself.** Applying
`docs/REAL_SYSTEM_VALIDATION_PLAN.md`'s rule literally would mean: (a) ≥5
real executions per `(policy, source, window)` cell → the task matrix grows
from 240 to ≥1,200 cells, and (b) the statistical design switches from
window-level to repetition-level bootstrap, which is a different, not
merely larger, analysis (and would need reconciling with — or replacing —
the window-bootstrap design the current, more specific RQ6 protocol
explicitly derived from Phase-12's own methodology). Silently picking 1
(ignoring a real, standing commitment) or silently picking 5 (importing a
generic pre-case-selection design as if it were RQ6-specific, when RQ6's
own later, more targeted analysis reasoned to something different) would
both be inventing a resolution the record does not actually contain. The
implementation currently runs `replicates_per_cell=1` (consistent with the
RQ6-specific trail), but `configs/real_vllm/rq6_validation_manifest_v1_
20260903.json`'s `replicates_per_cell_status` field records this full
conflict verbatim and is **not** marked frozen. **A human must explicitly
decide**: either amend `docs/REAL_SYSTEM_VALIDATION_PLAN.md` to record it
is superseded for RQ6 by the window-bootstrap design, or apply its
≥5-repetitions rule to RQ6 and rework the task matrix/statistics
accordingly. See §15.

### Simulator-selected winner direction — RESOLVED (session 2)

An earlier draft of `configs/real_vllm/rq6_validation_manifest_v1_20260903.json`
asserted specific per-condition winners (`slai_faithful` wins
`azure_llm_2024::HIGH_PRESSURE`, `vllm_faithful` wins
`burstgpt::HIGH_PRESSURE`) without source support — the case-selection
manifest records only an *unsigned* effect-size magnitude
(`operationalized_effect_size_min_abs_margin=1.2816`), not which policy
wins which condition; the signed value lives in the generated, gitignored
`pairwise_reversals_json` artifact (hash `c90619e8...`), not present in
this worktree. This was caught and corrected: the manifest recorded that the
labels were pending recovery from the authoritative artifact, with a full
explanation of what was required.

**Session 2 recovered it, rigorously**: `paper/generated/table_data/
rq3_reversals.json` on branch `manuscript/lssp-jsc-reviewer-informed-
polish-20260903` (commit `e6766c954feaf6bdc2ecfa24ee4e30385d1d335c`, an
already-committed, already-existing manuscript artifact — not regenerated,
not rerun) contains
`supported_practical_reversals_primary_metric_sorted_by_effect_size`, a
36-record list whose first (largest-effect-size) entry is:
`{policy_a: slai_faithful, policy_b: vllm_faithful, condition_x:
azure_llm_2024::HIGH_PRESSURE, condition_y: burstgpt::HIGH_PRESSURE,
diff_x: +0.5204, diff_y: -0.3476, operationalized_effect_size_min_abs_
margin: 1.281566820276498, bh_fdr_p_pair_iut: 0.0}`. This file's own
`source_artifact_hashes.pairwise_reversals.json` field
(`c90619e822925146ad4395deebbf0cc8ccd0fd66cc13a8aa84202fc39a5cfdde`) and
`analysis_code_git_sha` (`eb574a8ce5c34a80fddbcfd4417f6626fbdddfd1`) match
the case-selection manifest's own recorded provenance **exactly** — proving
this record came from the identical frozen `pairwise_reversals.json` the
case selection cites, run by the identical analysis code, not a different
or re-run analysis. The `operationalized_effect_size_min_abs_margin`
(`1.281566820276498`, matching the manifest's rounded `1.2816`) and
`bh_fdr_p_pair_iut` (`0.0`) match too. The exactly-tied alternative record
(`bailian_qwen::HIGH_PRESSURE` vs `burstgpt::HIGH_PRESSURE`, same
`1.281566820276498`) is present in the same list with the same sign
pattern, consistent with the case-selection manifest's disclosed tie —
further corroborating this is the correct, complete, untampered dataset.
The stable control's `kendall_tau=1.0`/CI were separately re-verified
byte-identical against `paper/generated/table_data/rq1_rq2_portability.json`,
same commit.

Per `_diff_and_margin`'s frozen sign convention (`diff = value(policy_a) -
value(policy_b)`, `policy_a=slai_faithful`): `diff_x>0` → `slai_faithful`
wins `azure_llm_2024::HIGH_PRESSURE`; `diff_y<0` → `vllm_faithful` wins
`burstgpt::HIGH_PRESSURE`. Both CIs exclude zero. **This happens to match
the earlier, unevidenced guess** — that coincidence is not evidence the
guess was sound; it was correctly flagged and replaced regardless, and is
now backed by an independent, hash-verified source. The manifest's
`case_selection.reversal_case.simulator_selected_winner_x`/`_y` fields (and
`simulator_diff_x`/`_y`, `simulator_ci_x`/`_y`) now record this recovered,
verified data; `rq6_validation_analysis.reversal_analysis()` still takes
these as required caller-supplied arguments (never hardcoded inside the
analysis module itself), and
`tests/test_rq6_validation_analysis.py::
test_reversal_analysis_wired_from_manifest_recovered_winners_agreement_case`
proves the wiring is mechanical (swapping the manifest's winner labels
flips the computed agreement), not a constant.

## 5. Files added/changed

| File | Purpose |
|---|---|
| `src/robustbench/real_llm/rq6_validation.py` | Task-matrix enumeration (240 cells), calibration-output lookup with hash/status verification, real-side ANWG metric. |
| `src/robustbench/real_llm/port_alloc.py` | OS-assigned free-port allocation (`bind((host,0))`), replacing calibration's buggy modulo scheme. |
| `src/robustbench/real_llm/rq6_validation_analysis.py` | Result-blind analysis: per-condition SLAI-minus-vLLM bootstrap effect, reversal/stable-control tests, BH-FDR — reuses `ranking_portability.analysis.stats`. |
| `configs/real_vllm/rq6_validation_manifest_v1_20260903.json` | The frozen, result-blind validation manifest (sha256 `8892ec9b299aced31f74785e9f7aa896b83641fe799863c70aacee119c0b1222`). |
| `scripts/real_vllm/run_rq6_validation.py` | Scientific runner: verifies hash chain, dry-run mode, dynamic port allocation with retry, atomic writes, overwrite refusal. |
| `scripts/real_vllm/run_rq6_validation.sbatch` | Slurm array launcher, 240 tasks, fail-closed on required env vars, no scientific parameter duplicated outside the frozen manifest. |
| `scripts/real_vllm/validate_rq6_validation_outputs.py` | Post-hoc output validator — identity/completeness/schema/provenance only, never judges the hypothesis. |
| `docs/RQ6_REAL_VLLM_VALIDATION_PREFREEZE_20260903.md` | This document. |
| `tests/test_rq6_validation.py`, `tests/test_port_alloc.py`, `tests/test_rq6_validation_analysis.py`, `tests/test_run_rq6_validation.py`, `tests/test_validate_rq6_validation_outputs.py` | Test coverage, §M. |

No existing file was modified; no calibration output, Phase-12 artifact, or
manuscript file was touched.

## 6. Validation manifest

- Path: `configs/real_vllm/rq6_validation_manifest_v1_20260903.json`
- sha256: `172efb13b30efea440a18644ef852fa2d0b8cc6fee93ea730981b2ac868bd670`
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
 - Replicate identity: no replicate dimension in the task key; `replicate_seed`
   in outputs is fixed to 0 (execution identifier only; not an inferential
   replicate).

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
  `agrees_with_simulator_selected_direction`. **Session 2**: the simulator
  winner labels this depends on are now recovered and hash-verified (§4);
  `agrees_with_simulator_selected_direction` is fully computable once a real
  per-window ANWG result exists for both conditions — nothing further
  blocks this specific quantity.
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

Commands and results (session 1 + session 2, this worktree):

```
PYTHONPATH=src python3 -m pytest tests/ -q
```
→ **511 passed**, 0 failed (full existing suite + 5 new files, 67 new
tests). No expensive/GPU/Slurm job was run.

New test files: `tests/test_rq6_validation.py` (24 tests: task matrix,
calibration lookup incl. all 3 terminal statuses, ANWG metric semantics),
`tests/test_port_alloc.py` (3 tests), `tests/test_rq6_validation_analysis.py`
(13 tests, incl. 2 new session-2 tests reading the recovered winner labels
directly from the manifest and proving the agreement wiring is mechanical),
`tests/test_run_rq6_validation.py` (19 tests: dry-run, manifest-chain
verification incl. stale-SHA and wrong-case-selection-hash rejection —
now via the corrected ancestor-based SHA check, §0 — atomic write,
overwrite refusal, sbatch fail-closed/no-modulo-port/array-range checks,
full mocked end-to-end), `tests/test_validate_rq6_validation_outputs.py`
(11 tests: missing/duplicate/schema/hash-mismatch/scheduler-mismatch
detection, engineering-file exclusion, and confirmation that ANWG
value/sign never affects `passed`).

**Session-2 regression note**: re-running the full suite at the session-1
commit (`4c846642d2...`) immediately surfaced 2 real failures
(`test_verify_manifest_chain_passes_on_real_manifest` and the end-to-end
CLI test) — both traced to the `frozen_code_sha` exact-equality bug (§0),
not to anything in the two named blockers. Fixed and reverified stable
across 4 repeated runs before proceeding.

## 14. Dry run

Full 240-index sweep executed via `scripts/real_vllm/run_rq6_validation.py
--dry-run` (real workload manifests, real validation manifest, no GPU, no
server started) — **re-run in session 2 after the manifest content and the
`verify_manifest_chain` fix**, with identical results to session 1:

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

**`verify_manifest_chain` bug found and fixed (session 2)**: the original
implementation compared `git rev-parse HEAD` for exact equality against the
manifest's `frozen_code_sha` (`773982a2...`). Since `frozen_code_sha` names
the commit the *scientific protocol* was frozen at, and the runner/manifest
implementing that protocol were necessarily committed *after* it (session 1's
own commit `4c846642d2...`), this check was guaranteed to fail forever once
the runner existed — confirmed: re-running the full suite at the session-1
commit immediately showed 2 failures from exactly this. Fixed by replacing
exact equality with `git merge-base --is-ancestor <frozen_sha> HEAD` (the
frozen commit must be present in HEAD's history, not equal to it) —
verified via `tests/test_run_rq6_validation.py::
test_verify_manifest_chain_passes_on_real_manifest` and the three
induced-failure tests (stale SHA now uses a genuinely-invalid all-zero SHA,
which correctly still fails the ancestor check).

## 15. Prefreeze status

```
READY_TO_LAUNCH_RQ6
```

Both original blockers are resolved: replicates-per-cell is frozen by author
decision; simulator-selected winner direction was recovered and
hash-verified from the authoritative committed artifact. Everything else —
code, tests, dry run, hash verification, port strategy, output contract,
scheduler mapping — is implemented, tested, and passing.

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
