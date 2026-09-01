# STAGE0_LOAD_CALIBRATION_STATUS.md

Records the first-ever execution of `scripts/run_stage0_load_calibration.py`
against the real, frozen `artifacts/manifests/stage0_windows.json` (30
windows, SLURM job `1209813`, completed 2026-09-01T04:47:03Z). This
calibration code existed only as uncommitted, never-executed work before
this session; it is committed on `research/stage0-prerequisites-20260901`
alongside this doc.

## Run

- Executed on Wulver in worktree
  `llm-serving-scheduler-robustness-stage0-prereqs`
  (branch `research/stage0-prerequisites-20260901`, commit `3b7caa6`).
- Input: `artifacts/manifests/stage0_windows.json`, sha256
  `0984ca4ee5c2d3f273b1de8c8906f1b0d864e60b18f0aeea6988219f6c1577c2`
  (byte-identical copy of the original, untouched tree's file — verified).
- Output: `artifacts/manifests/stage0_load_calibration.json`
  (Wulver-only, gitignored per this repo's convention for generated
  manifests — not committed, same as `stage0_windows.json` itself), sha256
  `2d31036ddff428c2c95a1d53be1ebd4128031b40f4bfaeabd131757565afd50e`.
- 30/30 windows calibrated without a script error.

## Finding requiring review before this calibration is trusted for launch

**All 30/30 windows are flagged `plausible: false`** by the module's own
built-in sanity check, always for the same reason: `"PRE_KNEE looks
trivially underloaded (completion_fraction~=1.0, slo_violation_rate~=0)."`
(5 of 30 additionally flag `"OVERLOAD shows little more pressure than the
calibration threshold itself."`)

Manual inspection of the underlying numbers suggests this is very likely
the sanity heuristic being **structurally over-sensitive by construction**,
not a sign that the calibration itself is broken:

- `lambda_ref` is defined as the compression factor at which `fifo`'s
  `slo_violation_rate` crosses the fixed 0.5% threshold. `PRE_KNEE = 0.8 *
  lambda_ref` will, for almost any smooth response curve, sit meaningfully
  below that crossing — so `slo_violation_rate ~= 0` at `PRE_KNEE` is close
  to the *expected*, by-design outcome, not evidence of a data problem.
  The "trivially underloaded" note appears to fire on essentially every
  window regardless of whether the underlying calibration is sound.
- Sampled `KNEE`/`OVERLOAD` values look scientifically sensible: `KNEE`
  lands almost exactly at the target ~0.5% `slo_violation_rate` (e.g.
  `burstgpt_stage0_w00`: 0.5%, `w01`: 0.0%, `w02`: 0.5%), and `OVERLOAD`
  shows a meaningfully elevated violation rate (1.5%-12.5% in the sampled
  windows) — i.e. the three regions ARE differentiated in the expected
  direction.
- `completion_fraction` stays at `1.0` even at `OVERLOAD` in the sampled
  windows (SLO violations rise, but no requests are dropped outright under
  the reference `STAGE0_REFERENCE_GPU_CONFIG` at these compression
  factors) — plausible given `fifo` has no admission control, but worth a
  second look before relying on `OVERLOAD` to trigger GO criterion 3
  ("no universal collapse").

**This is flagged for human/scientific review, not resolved by this
session.** No calibration parameter, threshold, or sanity-check rule was
changed to make the result look better — per
`docs/STAGE0_DISCRIMINABILITY_PROTOCOL.md`'s own instruction, a degenerate-
looking calibration result gets reported, not silently corrected. Two
honest paths forward: (a) the sanity-check heuristic in
`stage0_load_calibration.py` is miscalibrated (too strict) and should be
loosened/re-derived, with the underlying `lambda_ref`/region values kept
as-is; or (b) the near-zero `PRE_KNEE` violation rate is scientifically
real and acceptable (PRE_KNEE is *supposed* to be lightly loaded) and the
sanity check should simply not gate launch on it. Either way, this decision
belongs to a human review before Stage-0 is treated as launch-ready on this
axis specifically.

## What this does and does not resolve

Resolves: the "load calibration frozen" prerequisite now has a first real
execution against the actual frozen windows (previously: code existed,
never run). Does NOT resolve: the missing Stage-0 orchestration harness
(the actual 1,080-cell sweep script) remains unwritten and is the
dominant blocker to launch — see `docs/OVERNIGHT_STAGE0_HANDOFF` (not yet
created; Stage-0 has never been launched).
