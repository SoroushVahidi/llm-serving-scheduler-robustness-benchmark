# STAGE0_LOAD_CALIBRATION_AUDIT_20260901.md

First-principles audit of why `run_stage0_load_calibration.py` flagged
**all 30/30** frozen Stage-0 windows `plausible: false`
(`docs/STAGE0_LOAD_CALIBRATION_STATUS.md`, prior session). Does not use any
scheduler-under-study outcome — the six policies under Stage-0 study have
never been run; only the frozen `fifo` reference-calibration mechanism and
the 30 frozen windows themselves are inspected.

## A1. Exact calibration semantics (as implemented, unchanged)

Source: `src/robustbench/calibration/stage0_load_calibration.py`
(`calibrate_window`), matching `docs/LOAD_CALIBRATION_PROTOCOL.md`:

1. **Reference mechanism**: policy-independent capacity search using a
   single frozen reference policy, `fifo` (`REFERENCE_POLICY`), against one
   documented `GPUConfig` (`STAGE0_REFERENCE_GPU_CONFIG`), identical for
   every window/source.
2. **Target quantity**: `lambda_ref` — the inter-arrival *compression
   factor* at which `fifo`'s `slo_violation_rate` first crosses
   `SLO_VIOLATION_THRESHOLD = 0.005` (0.5%).
3. **Search**: log-scale bisection over compression factor
   `10^[-2, 4]` (0.01x–10,000x), 30 iterations — converges to a
   compression factor, not a violation-rate value; the final
   `slo_violation_rate` at that factor is whatever it happens to be at
   convergence, not forced to equal exactly 0.005.
4. **Region definitions** (fixed multiplier table, applied identically to
   every window — never source- or outcome-adjusted):
   `PRE_KNEE = 0.8·lambda_ref`, `KNEE = 1.0·lambda_ref`,
   `OVERLOAD = 1.2·lambda_ref`.
5. **Sanity checks** (as found, before this audit's fix), each appending a
   string to `notes`; `plausible = len(notes) == 0`:
   - `PRE_KNEE`: `completion_fraction >= 0.999 AND slo_violation_rate < 1e-6`
     → "trivially underloaded"
   - `OVERLOAD`: `slo_violation_rate < SLO_VIOLATION_THRESHOLD * 2` (< 1%)
     → "little more pressure than the calibration threshold itself"
   - `OVERLOAD`: `NaN completion_fraction` OR `(0 completed AND 0 dropped)`
     → "possible simulator malfunction"
   - `lambda_ref` pinned to a bisection search bound (0.01x or 10,000x)
     → "not a genuine interior crossing"

## A2. Diagnostic table (all 30 windows)

Full per-window values pulled directly from
`artifacts/manifests/stage0_load_calibration.json` (Wulver-only,
sha256 `2d31036ddff428c2c95a1d53be1ebd4128031b40f4bfaeabd131757565afd50e`):

| Metric | Value across all 30 windows |
|---|---|
| `pre_knee_slo_violation_rate` | **exactly `0.0` for 30/30 windows** |
| `pre_knee_completion_fraction` | **exactly `1.0` for 30/30 windows** |
| `knee_slo_violation_rate` | exactly `0.0` (11/30) or exactly `0.005` (19/30) — no other value ever occurs |
| `overload_slo_violation_rate` | ranges `0.0`–`0.175`; 5/30 windows ≤ `0.005` |
| `lambda_ref` pinned to search bound | 0/30 |
| `OVERLOAD` NaN/no-completions-no-drops | 0/30 |

(Full per-window CSV: `artifacts/diagnostics/stage0_load_calibration_audit.csv`.)

## A3. Systematic-defect audit (checklist from the task)

Went through every listed failure mode against the actual code
(`stage0_load_calibration.py`) and the numbers above:

- Percentage vs. fraction, 0.5 vs 0.005 confusion: **no** — `0.005` is used
  consistently as a fraction (0.5%) throughout; `run_policy`'s
  `slo_violation_rate` is itself a fraction in [0,1] (confirmed via
  `core/metrics.py`).
- `>=`/`>` inversion, checking KNEE against PRE_KNEE's threshold, stale
  variable reuse, wrong metric column/denominator, incorrect repetition
  averaging: **no** — each region's check reads its own freshly-computed
  `m_pre`/`m_knee`/`m_over` object; there is only one repetition inside
  calibration (calibration is not repeated 2x — that's the *Stage-0 study*
  cells' repetition semantics, not calibration's).
- Absolute vs. relative change, NaN-fallback-mapped-to-implausible, units
  mismatch, rounding before comparison, synthetic-fixture thresholds
  applied to real data, one fixed tolerance for all regions: **no** for
  all — thresholds are read directly from `SLO_VIOLATION_THRESHOLD` (no
  separate fixture-only constant exists), no rounding occurs before any
  comparison, and the "one fixed tolerance for all regions" concern is
  addressed directly below (A4) — the three regions correctly use
  different absolute cut-offs already.

**No implementation bug** (no `>=`/`>` swap, no wrong variable, no wrong
column) — the code executes exactly as written and as documented. The
defect, where one exists, is in the *choice of PRE_KNEE's threshold value*
relative to the data's achievable resolution (A4), not in the code's logic.

## A4. Scientific validity of the three regions

- **PRE_KNEE**: by definition (`0.8·lambda_ref`, strictly below the 0.5%
  violation-crossing point) is *supposed* to look lightly loaded. With
  **200 requests/window** (the frozen Stage-0 window size), `slo_violation_rate`
  can only take values that are multiples of `1/200 = 0.005` — it is a
  discrete quantity, not a continuum. `SLO_VIOLATION_THRESHOLD` (0.005) is
  set to exactly **one violation's worth** of that granularity. Given any
  reasonably monotonic response curve, sitting at 80% of the load where the
  *first* violation appears will, for the overwhelming majority of windows,
  show **zero** violations (0/200) — i.e. `slo_violation_rate == 0.0`
  *exactly*, not "close to zero". **This is the mathematically expected,
  correct outcome of a properly functioning PRE_KNEE region, not a symptom
  of a broken one.** The check's own inner threshold (`< 1e-6`) is roughly
  5,000x finer than the data's actual resolution (`0.005`), so it is
  structurally certain to fire whenever PRE_KNEE is calibrated correctly —
  it cannot distinguish a good calibration from a bad one, because it asks
  a question the data can only ever answer one way.
- **KNEE**: lands at exactly `0.0` or exactly `0.005` violation rate for
  every one of the 30 windows — i.e. within one discrete step of the
  target 0.5% threshold in all 30 cases. This is exactly what a correctly
  converging bisection search against a threshold sitting at one
  violation's worth of granularity should produce. **KNEE performs its
  intended role correctly and precisely in all 30 windows.**
- **OVERLOAD**: shows meaningfully elevated violation rates (up to 17.5%)
  in 25/30 windows — real, substantial differentiation from KNEE. In the
  remaining 5/30, `OVERLOAD` sits at or barely above `KNEE`
  (`azure_llm_2024_stage0_w05/06/07`, `bailian_qwen_stage0_w05/07`) — this
  is a genuine, minority-case observation (not a granularity artifact in
  the same unconditional sense as PRE_KNEE) worth carrying forward as a
  documented caveat, not silently dismissed.
- **Ordering** `PRE_KNEE < KNEE < OVERLOAD` (in compression-factor space,
  which is the load axis) holds by construction (fixed multiplier table
  `0.8 < 1.0 < 1.2`) in all 30/30 windows — verified directly from
  `load_regions` in the manifest, no exceptions.

## A5. Reference-calibration-only sensitivity check

Using only the frozen `fifo` reference mechanism (no policy-under-study
involved), evaluated `slo_violation_rate` at compression factors
`{0.6, 0.7, 0.8, 0.9, 1.0, 1.1, 1.2, 1.4}·lambda_ref` for a representative
sample of windows (2 per source). Response is monotonic non-decreasing in
every sampled window with no inversion or discontinuity, and the discrete
step structure (jumps of `1/200`) is consistent with A4's granularity
argument — i.e. the selected PRE_KNEE/KNEE/OVERLOAD points sit on a stable,
monotonic curve, not on noise. (Script:
`scripts/diagnostics/stage0_calibration_sensitivity_smoke.py`; this is
reference-calibration-only, never touches a Stage-0-study policy, and is
explicitly not scheduler evidence.)

## A6. Calibration verdict: `CALIBRATION_VALID_CHECKER_OVERSENSITIVE`

- **Checker bug?** No code-logic bug (A3) — but the PRE_KNEE sanity
  check's *threshold* is a design defect: it checks for a condition
  (near-zero PRE_KNEE violations) that is the intended, correct behavior
  of a properly calibrated PRE_KNEE region given the window size, so it is
  incapable of ever passing on real, correctly-calibrated data. This is a
  genuine implementation defect in the checker (not in the calibration
  itself), fixed below.
- **Scientific calibration valid?** **YES**, with one documented caveat:
  KNEE and PRE_KNEE are correctly calibrated in all 30/30 windows; OVERLOAD
  is meaningfully differentiated from KNEE in 25/30 windows and only
  marginally so in 5/30 (documented, not hidden).
- **Load factors changed?** **No** — `LOAD_REGION_MULTIPLIERS`
  (0.8/1.0/1.2), `SLO_VIOLATION_THRESHOLD` (0.005), `REFERENCE_POLICY`
  (`fifo`), and every frozen window's `lambda_ref`/`load_regions` are
  **unchanged**. Only the PRE_KNEE *sanity-check* threshold changed (code
  fix below), justified entirely from A4's granularity argument, computed
  before any Stage-0-study policy has ever been run — no scheduler outcome
  informed this correction.

## Fix applied

`stage0_load_calibration.py`: the PRE_KNEE "trivially underloaded" check
is demoted from a `plausible`-gating condition to an **informational-only**
note (still recorded verbatim in `sanity.notes` for every window it fires
on — nothing is hidden), with the reasoning above added as a code comment.
The three other checks (OVERLOAD little-pressure, OVERLOAD
malfunction-shaped, `lambda_ref` pinned-to-bound) are unchanged and remain
`plausible`-gating. See `tests/test_stage0_load_calibration.py`'s new
cases for the exact before/after behavior, proven with synthetic
(non-real-data) fixtures.

After the fix, re-running calibration against the same frozen 30 windows
(same `lambda_ref`/`load_regions` — verified byte-identical except the
`sanity` block) yields: **25/30 windows now `plausible: true`**; the
remaining 5 are exactly the `OVERLOAD`-little-pressure cases from A4,
correctly still flagged (genuine signal, not an artifact).
