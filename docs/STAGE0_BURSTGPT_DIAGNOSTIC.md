# STAGE0_BURSTGPT_DIAGNOSTIC.md

Read-only, post-hoc diagnostic explaining Criterion 5's failure in the
completed, final `STAGE0_NO_GO` result
(`research/stage0-zero-completion-undefined-metrics-20260901`, HEAD
`848bae3`). **This does not change the Stage-0 verdict, any GO/NO-GO
threshold, the tie epsilon, any result cell, or any calibration value.**
Raw artifacts: `results/stage0_burstgpt_diagnostic/*.csv`,
`diagnostic_summary.json` (script:
`scripts/stage0/run_burstgpt_diagnostic.py`, deterministic, read-only
against the frozen matrix).

## Provenance

Read from branch `research/stage0-zero-completion-undefined-metrics-20260901`
at `848bae3`, against the completed matrix at
`results/stage0_v1/` on Wulver (1080/1080 valid cells). Re-verified
identical to the frozen values already recorded in
`stage0_zero_completion_repair.json`: window manifest sha256
`0984ca4e...`, calibration manifest sha256 `e82736e7...`, analyzer sha256
`d299c67b...`, policy registry sha256 `3646a2a5...`. No frozen artifact was
touched.

## A. Source differentiation (Section 2/17.A)

| Source | Non-tied conditions / 30 | % | Windows non-tied in ≥1 region / 10 |
|---|---|---|---|
| azure_llm_2024 | 30/30 | **100%** | 10/10 |
| bailian_qwen | 30/30 | **100%** | 10/10 |
| burstgpt | 10/30 | **33.3%** | 6/10 |

This is a starker contrast than Criterion 5's share numbers alone suggest:
Azure and Bailian are non-tied in *literally every* (window, load-region)
condition; BurstGPT is non-tied in only a third of its own. Criterion 5's
14.3%/42.9%/42.9% shares (computed against the pooled 70 non-tied cells)
are a downstream consequence of this per-source rate, not an independent
observation. (`source_differentiation.csv`)

## B. BurstGPT by load region (Section 3/17.B)

From `burstgpt_window_region_matrix.csv`, tied (T) / non-tied (NT) per
window:

| Window | PRE_KNEE | KNEE | OVERLOAD |
|---|---|---|---|
| w00 | T | NT | NT |
| w01 | T | T | NT |
| w02 | T | T | NT |
| w03 | T | NT | NT |
| w04 | T | T | T |
| w05 | T | NT | NT |
| w06 | T | T | T |
| w07 | T | T | T |
| w08 | T | NT | NT |
| w09 | T | T | T |

- **PRE_KNEE: 10/10 tied** — universal, but this is *not* BurstGPT-specific: Azure and Bailian are non-tied at PRE_KNEE in all 20/20 of their own conditions (see `all_conditions.csv`) despite PRE_KNEE being "trivially underloaded" (100% completion) for every source. So PRE_KNEE tying is a BurstGPT-only phenomenon, not a general property of the load region.
- **KNEE: tied in 6/10, non-tied in 4/10** (w00, w03, w05, w08).
- **OVERLOAD: tied in 4/10, non-tied in 6/10** (w00, w01, w02, w03, w05, w08) — OVERLOAD differentiates somewhat more than KNEE, but neither approaches Azure/Bailian's 10/10.
- **4 windows are tied at all 3 regions** (w04, w06, w07, w09) — completely flat across the entire load sweep, not just at low load.

## C. Tie magnitude (Section 4/17.C)

**Genuinely near-exact, not threshold-adjacent.** From
`policy_pair_similarity.csv`: on BurstGPT, `{fifo, edf,
kv_constrained_online, vllm_faithful, vllm_style_token_budget}` are
pairwise **exactly identical ANWG (max_abs_diff = 0.0) in 30/30
conditions** for every pair among them. From `metric_dependence.csv`,
12/20 (60%) of BurstGPT's tied conditions are `TIED_ACROSS_METRICS` —
identical not just in ANWG but in completion_fraction, slo_violation_rate,
p95_latency, mean_ttft, and both throughput fields simultaneously (e.g.
`burstgpt_stage0_w06/w07/w09`: every recorded metric is bit-identical
across all 6 policies at all 3 regions). The remaining 8/20 show a small
latency/TTFT difference under an identical ANWG/SLO outcome
(`ANWG_TIED_OTHER_METRIC_DIFFERS`) — real but too small, given the 20x SLO
multiplier, to flip any request's deadline outcome. Contrast: Azure/Bailian
tied conditions don't exist to compare against (0/30 each), and their
*non-tied* conditions show `anwg_range_mean` of 0.98/0.89 respectively
(near-maximal) vs. BurstGPT's non-tied `anwg_range_mean` of 0.12 — even
BurstGPT's differentiating conditions differentiate much less dramatically.

## D. Calibration (Section 5/17.D)

**No.** The 5 documented "OVERLOAD little-pressure" windows
(`docs/STAGE0_LOAD_CALIBRATION_AUDIT_20260901.md` A4) are
`azure_llm_2024_stage0_w05/w06/w07` and `bailian_qwen_stage0_w05/w07` —
**zero are BurstGPT**. From `calibration_comparison.csv`, BurstGPT's
`overload_slo_violation_rate` ranges 0.01–0.175 (comparable to, and in
several windows *exceeding*, Azure's 0.0–0.045 and Bailian's 0.005–0.065)
— including the fully-tied windows w06 (0.04), w09 (0.175, the single
highest overload violation rate of any window in the whole matrix) and w07
(0.01). BurstGPT receives real, sometimes the *most extreme*, calibrated
overload pressure in the entire pilot, and its policies still produce
bit-identical outcomes. **BurstGPT's low differentiation is not explained
by weak calibration pressure; it persists even under comparable or
higher pressure than the two differentiating sources.**

## E. Workload explanation (Section 6/17.E)

From `descriptor_comparison.csv`, the largest, most consistent contrast:

| | Azure-2024 | Bailian/Qwen | BurstGPT |
|---|---|---|---|
| prompt_tokens_mean | 1440–1773 | 695–1192 | **212–562** |
| prompt_tokens_cv | 0.84–1.02 | 0.82–2.21 | **0.03–0.62** (mostly <0.3) |
| output_tokens_mean | 93–137 | 70–146 | **7–142** (mostly ≈7) |
| output_tokens_cv | 1.31–1.66 | 1.15–5.62 | **0.00–5.83** (5 of 10 windows ≈0.00–0.09) |

BurstGPT prompts are roughly 3–7x shorter than Azure/Bailian's *and* far
more uniform in length (low CV). Output length is the sharpest contrast:
5 of BurstGPT's 10 windows (`w00,w01,w03,w05,w08` — exactly the windows
that *do* show some KNEE/OVERLOAD differentiation, notably) have
output-token distributions that are nearly **constant** (mean≈7,
p90≈7, CV≈0.01–0.09), while the 4 fully-tied windows (w04, w06, w07, w09)
have somewhat larger but still modest and low-variance output
(mean 20–142). Azure/Bailian output lengths are an order of magnitude
larger with much higher variance (CV 1.1–5.6). (Semantic caveat honored:
this compares BurstGPT's per-request prompt tokens against Azure/Bailian's
own per-request fields as extracted in this project's adapters — no
cumulative-context reinterpretation is implied.)

**Answer:** yes — BurstGPT's Stage-0 windows are structurally short-prompt,
short-and-near-constant-output workloads, which is exactly the opposite of
the profile (long, heterogeneous prompts and outputs) that would stress
token-budget accounting, KV-cache growth, and decode-time scheduling order.

## F. Policy-mechanism explanation (Section 7/8/17.F)

From `policy_pair_similarity.csv`: on BurstGPT, **`fifo`, `edf`,
`kv_constrained_online`, `vllm_faithful`, and `vllm_style_token_budget` are
pairwise 100%-identical to every other member of that group, in all 30/30
conditions.** Only `sarathi_faithful` (chunked-prefill scheduling) ever
diverges from the rest, and only in 10/30 (33%) conditions. This is a
**global collapse of 5 of the 6 policies into one behaviorally
indistinguishable cluster**, not "several policies happen to agree" or
"one mechanism dominates" — it is the near-total panel, with a single
partial exception.

Contrast with Azure/Bailian: there, `edf`/`kv_constrained_online`/
`vllm_style_token_budget` already cluster together (a pre-existing,
source-independent equivalence — the three simplest baselines behave alike
whenever there's no long-tail contention to expose their differences), but
`fifo` only joins that cluster in ~47–50% of conditions, and
`vllm_faithful`/`sarathi_faithful` never join it (0% identical) — they are
the mechanisms doing the differentiating work. **On BurstGPT specifically,
`vllm_faithful` additionally collapses into the classical cluster**
(100% identical to fifo/edf/kv/vllm_style there, vs. 0% on Azure/Bailian) —
the one FAITHFUL_EXTERNAL policy expected to behave distinctively stops
doing so.

No raw per-step telemetry (queue depth, batch saturation, KV occupancy
over time, preemption counts) was persisted for any Stage-0 cell — the
frozen `CellResult` schema stores only the 10 aggregate metrics in
`docs/STAGE0_METRIC_DEFINITIONS.md`'s conditional-metric table. This
diagnostic therefore cannot directly inspect mechanism activation
(admission-control firing, KV pressure) at the simulator-internal level;
Section E's workload descriptors (`kv_pressure_proxy`,
`concurrency_proxy`) are the closest available proxy and support the same
conclusion indirectly: BurstGPT's `concurrency_proxy` (11–94) and
`kv_pressure_proxy` (219–704) are both far below Azure's (2312–7870 /
1539–1880) and Bailian's (1999–3384 / 799–1338), consistent with
KV-block/token-budget mechanisms rarely being exercised.

## G. Metric dependence (Section 9/17.G)

12/20 (60%) tied BurstGPT conditions: `TIED_ACROSS_METRICS` (genuine
equivalence, every recorded metric identical). 8/20 (40%):
`ANWG_TIED_OTHER_METRIC_DIFFERS` (small p95_latency/TTFT differences exist
but don't cross an SLO deadline given the 20x multiplier). **Diagnostic
conclusion only, not used to revise Stage 0**: the collapse is
predominantly genuine scheduler equivalence, with a secondary,
smaller contribution from ANWG's SLO-binary insensitivity to sub-deadline
latency differences.

## H. Uncertainty (Section 10/17.H)

From `diagnostic_summary.json` (Wilson 95% CIs):

| Source | Non-tied/30 | 95% CI (condition-level) | Windows non-tied ≥1 region /10 | 95% CI (window-level) |
|---|---|---|---|---|
| azure_llm_2024 | 30/30 | [0.886, 1.0] | 10/10 | [0.722, 1.0] |
| bailian_qwen | 30/30 | [0.886, 1.0] | 10/10 | [0.722, 1.0] |
| burstgpt | 10/30 | [0.192, 0.512] | 6/10 | [0.313, 0.832] |

BurstGPT's condition-level interval doesn't overlap Azure/Bailian's at
all (upper bound 0.512 vs. their lower bound 0.886) — the difference is
not attributable to 10-window sampling noise at any plausible confidence
level, though the window-level CI (n=10 clusters) is wide, reflecting the
genuinely small window count. **Sample-size uncertainty affects the
precision of BurstGPT's rate estimate, but not the qualitative conclusion
that it differs sharply from the other two sources.**

## I. Root-cause classification (Section 12/17.I)

**Primary: `POLICY_PANEL_MECHANISM_MISMATCH`.** Evidence: (1) 5/6 policies
are pairwise bit-identical on 100% of BurstGPT conditions — not a
statistical near-tie but exact equivalence; (2) this holds even at
calibrated OVERLOAD pressure equal to or exceeding Azure/Bailian's; (3)
BurstGPT's workload descriptors show short, low-variance prompts and
near-constant, tiny output lengths — structurally the opposite of what
token-budget/KV-aware/prefill-chunking mechanisms need to diverge from
FIFO; (4) the one policy with a genuinely different mechanism on short
sequences (`sarathi_faithful`'s prefill chunking) is also the only one
that ever differentiates on BurstGPT.

**Explicitly ruled out or minor:**
- `LOAD_CALIBRATION_LIMITATION` — ruled out (Section D): pressure is
  present and comparable/higher than the differentiating sources; none of
  the 4 fully-tied windows are among the documented weak-calibration
  cases.
- `SAMPLE_SIZE_UNCERTAINTY` — minor only: CIs don't overlap Azure/Bailian
  (Section H); the qualitative finding is not a small-sample artifact,
  though the exact rate (33.3%) has real ±~15-20pp uncertainty.
- `PRIMARY_METRIC_INSENSITIVITY` — minor contributor only, to 8/20 (40%)
  of tied conditions (Section G), not the dominant driver (the other
  12/20 are identical across *every* metric, not just ANWG).
- `GENUINE_SOURCE_SPECIFIC_STABILITY` — true as a *description* of the
  outcome (scheduler choice genuinely doesn't matter much for this
  workload), but `POLICY_PANEL_MECHANISM_MISMATCH` is the more specific,
  mechanistic *explanation* of why that stability exists on BurstGPT and
  not the other two sources.

This is not chosen because it is the easiest story for the paper — it
would in fact require redesign work (Section K), whereas
`GENUINE_SOURCE_SPECIFIC_STABILITY` alone would let the current pilot
stand unchanged.

## J. Stage-0 status

**`STAGE0_NO_GO`** — unchanged, final, not reopened by this diagnostic.

## K. Redesign recommendation (Section 13/17.K)

**Not** "select BurstGPT windows/policies until Criterion 5 passes." The
diagnostic shows the mechanism-mismatch is a property of *this policy
panel's interaction with typical BurstGPT-style short-request traffic*,
which more or denser BurstGPT windows alone would not fix (Section D shows
higher pressure doesn't help; the ties are exact, not marginal).

Proposed second, new, pre-registered pilot (does not reuse Stage 0's GO
verdict; Stage 0's 1,080 cells stand as historical pilot evidence,
untouched):

- **(B) Denser, policy-independent operating-region grid for ALL three
  sources**, not just BurstGPT — e.g. 5–6 load regions instead of 3, same
  deterministic `lambda_ref`-relative multiplier rule applied identically
  to every source. This directly tests whether BurstGPT's collapse is a
  genuine plateau (more resolution finds nothing new) or a resolution
  artifact of only sampling 3 points, applied symmetrically so no source
  is treated differently by construction.
- **(A) More windows for all sources symmetrically** (e.g. 20/source
  instead of 10) — tightens the Wilson intervals in Section H for every
  source equally, not just BurstGPT's.
- **(E) Treat source-specific discriminability itself as a reportable
  result**, independent of whether a future redesign changes BurstGPT's
  number: Section F's finding (a specific, named policy-panel mechanism
  collapse tied to prompt/output-length homogeneity) is a legitimate,
  publishable finding about *when* this policy panel matters, not only an
  obstacle to clear before a confirmatory campaign.

Any new BurstGPT windows, if drawn, must use the same deterministic
sampling rule already used for the original 10 (no outcome-informed
reselection) — consistent with the non-negotiable design principles in
the parent task.

## L. Manuscript implication (Section 14/17.L)

**Safe, quantitatively supported statement:** *"The preregistered Stage-0
pilot found broad scheduler differentiation overall (Criteria 1–4 pass,
77.8%/86.7%/100% margins), but differentiation was strongly
source-dependent: Azure-2024 and Bailian/Qwen showed non-tied outcomes in
100% of their (window, load-region) conditions, versus 33.3% for BurstGPT,
traced to a near-total collapse of five of six scheduling policies into
identical behavior on BurstGPT's short-prompt, near-constant-output
traffic."* This is directly supported by Sections A, C, F above.

**Not supported, must not be written:** "Stage 0 demonstrated cross-source
rank instability" (rank-portability analysis was never run — out of
Stage-0's scope by design, Section J of the prior report) — and not
"BurstGPT is a low-quality/unsuitable source" (it received real,
comparable-or-higher calibrated pressure; the issue is policy-panel fit,
not data quality).

**Placement:** main methodology/pilot subsection, as the pilot's headline
result (`STAGE0_NO_GO`, Criterion 5's specific failure) plus this
diagnostic's mechanism finding as a short explanatory paragraph;
full per-condition tables belong in an appendix (the CSVs in
`results/stage0_burstgpt_diagnostic/`).

**Placeholder pending the new preregistered experiment:** any claim about
whether denser load resolution or more BurstGPT windows *would* produce
Criterion-5-passing differentiation — Section K's redesign has not been
run and must not be asserted as an outcome.
