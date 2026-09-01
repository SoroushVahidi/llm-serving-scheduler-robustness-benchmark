# STAGE0_PRELAUNCH_READINESS_20260901.md

Final readiness assessment for the frozen 1,080-cell Stage-0
discriminability pilot (`docs/STAGE0_DISCRIMINABILITY_PROTOCOL.md`).
**The pilot itself is NOT launched by this document or this session** --
this only records that every prerequisite is now satisfied and freezes
`artifacts/manifests/stage0_prelaunch_freeze.json`.

## Prerequisite checklist

| Prerequisite | Status | Evidence |
|---|---|---|
| Azure 2024 / Bailian-Qwen / BurstGPT real data available, checksummed | ✅ | `docs/DATA_ACQUISITION_STATUS.md`; checksums re-verified and frozen in `stage0_prelaunch_freeze.json` |
| Independent BurstGPT windows frozen | ✅ | `stage0_windows.json`, `burstgpt_independent_sampling.py` disclosure |
| 30-window manifest frozen | ✅ | `stage0_windows.json` sha256 `0984ca4e...`, 30 windows (3 sources x 10) |
| Load calibration frozen | ✅ (with documented caveat) | `stage0_load_calibration.json` sha256 `e82736e7...`, 25/30 plausible under the corrected checker; see verdict below |
| Six policies operational | ✅ | All 6 resolve via `make_policy_any` (`tests/test_policy_registry_stage0.py`) -- 2 (`vllm_faithful`, `sarathi_faithful`) required a real registration-gap fix, documented below |
| Stage-0 orchestration harness | ✅ | `robustbench.stage0.{cell,schema,runner,analyzer}` + `scripts/stage0/stage0_harness.py` (plan/run/status/validate), 37 new tests |
| Complete tests passing | ✅ | 119/119 (local and Wulver) |
| Prelaunch hashes frozen | ✅ | `artifacts/manifests/stage0_prelaunch_freeze.json`, sha256 `a13af1f5...` |

## A. Calibration audit verdict

**`CALIBRATION_VALID_CHECKER_OVERSENSITIVE`** -- full detail in
`docs/STAGE0_LOAD_CALIBRATION_AUDIT_20260901.md`. No load-region
multiplier, threshold, or frozen window/lambda_ref was ever touched. The
sanity checker's PRE_KNEE flag was a genuine design defect (asked a
question the data's granularity could only ever answer one way); fixed as
an informational-only reclassification, regression-tested, justified
entirely from the reference-calibration mechanism's own numbers before any
Stage-0-study policy was run. Remaining 5/30 `OVERLOAD`-little-pressure
flags are real, minority-case, documented signal -- not a blocker, carried
forward as a caveat for interpretation of those specific windows
(`azure_llm_2024_stage0_w05/06/07`, `bailian_qwen_stage0_w05/07`).

## B. Harness implementation

`robustbench.stage0` package + `scripts/stage0/stage0_harness.py`. Real
bug found and fixed while building it: `vllm_faithful`/`sarathi_faithful`
(mature, extensively-used-elsewhere faithful reimplementations) were never
added to any policy registry dict; `kv_constrained_online` lived in a
registry the runner wasn't checking. Fixed additively in
`src/robustbench/policies/registry.py` (`make_policy_any`) without
changing any existing registry's behavior (regression-tested). Verified
end-to-end against REAL frozen Stage-0 data via a 16-cell smoke run
(`results/stage0_smoke_only/`, every row labeled
`scientific_status=SMOKE_ONLY_DO_NOT_ANALYZE`; `analyzer.py` independently
verified to refuse this data).

## C. Five-criterion analyzer

`robustbench.stage0.analyzer`. Two genuine gaps in the frozen protocol
text identified and resolved with the narrowest objective formalization
(full detail in the module docstring and `docs/STAGE0_DISCRIMINABILITY_PROTOCOL.md`
cross-reference): (1) "statistically indistinguishable from 0" ->
`completion_fraction == 0.0` exactly, since only 2 deterministic
verification reps exist (no real statistical test possible); (2)
range/min undefined when min==0 -> qualifies iff range>0. Verified against
10 adversarial synthetic matrices (pass-all, each criterion failing
individually, missing/duplicate/failed cells, repetition inconsistency) --
all produced the expected verdict.

## D. Not yet done, deliberately

- The real 1,080-cell pilot has **not** been run. This session explicitly
  stops short of that per its own instructions.
- `scripts/slurm/stage0_array.sbatch`'s default `--array=0-11` (12 shards)
  is a placeholder sized from the tiny smoke fixture's timing, not the
  real 200-request windows' timing -- re-derive shard count from an actual
  per-cell timing sample on a real window before submitting.
- The 5/30 `OVERLOAD`-little-pressure calibration caveat should be kept in
  mind when interpreting those 5 windows' contribution to criteria 1/2/5,
  though it does not block launch.

## Launch readiness

**`SAFE_TO_LAUNCH_STAGE0 = YES`**

Every mechanical and scientific prerequisite this session could verify is
satisfied: real data, frozen windows, a scientifically valid (audited)
load calibration, all 6 policies operational, a tested end-to-end harness
verified against real data, and a tested 5-criterion analyzer. The
prelaunch freeze (`stage0_prelaunch_freeze.json`) is written and hashed.
No scientific parameter was adjusted after seeing any outcome.
