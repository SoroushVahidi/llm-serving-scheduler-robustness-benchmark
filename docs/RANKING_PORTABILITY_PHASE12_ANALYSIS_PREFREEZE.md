# RANKING_PORTABILITY_PHASE12_ANALYSIS_PREFREEZE.md

Freeze of the Phase-12 post-campaign **analysis code**, executed after
Phase-12D admitted the completed campaign
(`PHASE12_CAMPAIGN_EXECUTION_STATUS = COMPLETE_VALIDATED`,
`PHASE12_ANALYSIS_INPUT_ADMITTED = YES`) but **before any real
comparative result was computed or inspected**.

Declarations (required by the analysis-prefreeze task):

- `PHASE12_ANALYSIS_CODE_FROZEN_BEFORE_RESULTS = YES`
- `COMPARATIVE_PILOT_V2_RESULTS_INSPECTED = NO`
- `PHASE12_ANALYSIS_PREFREEZE_RESULT_BLIND = YES`
- `PHASE12_ANALYSIS_PREFREEZE_STATUS = COMPLETE_READY_TO_RUN`

Every component below was developed and tested exclusively against
fabricated synthetic fixtures
(`tests/ranking_portability_analysis_fixtures.py`); no function in the
frozen package resolves a default path into the live campaign-results
tree, and `analysis/result_blindness.py::assert_not_live_campaign_path`
blocks any such path at the CLI layer unless a caller explicitly passes
`--allow-live` (reserved for a deliberate production run, never used by
these tests).

## A. Frozen statistical methods

All numeric parameters live in
`src/robustbench/ranking_portability/analysis/contract.py`
(`ANALYSIS_CONTRACT_VERSION = phase12_analysis_prefreeze_v1`) with
per-constant citations to their canonical source document:

| Method | Frozen choice | Source |
|---|---|---|
| Rank correlation | Kendall tau-b, Spearman rho | `docs/STATISTICAL_ANALYSIS_PLAN.md` §A |
| Top-k agreement | k ∈ {1, 3}, overlap fraction with `k_reduced` flagging | `docs/RANKING_PORTABILITY_ANALYSIS_PLAN.md` §A |
| Bootstrap unit | workload **window** (whole windows, with replacement, never requests, never per-policy rows) | `docs/STATISTICAL_ANALYSIS_PLAN.md` preamble |
| Bootstrap replicates | ≥ 2,000 (`BOOTSTRAP_RESAMPLES = 2000`) | §A |
| Bootstrap CI level | 0.95 | §A |
| Omnibus test | Friedman rank-sum (block = window, treatment = policy), per metric × load region, run BEFORE any pairwise decomposition; no alternative omnibus selectable | `RANKING_PORTABILITY_ANALYSIS_PLAN.md` §B |
| Multiple testing | Benjamini-Hochberg FDR, q = 0.05, per family, never global across sections. Applied to: (1) Friedman omnibus p-values within each metric family across load regions; (2) Kendall-tau p-values within each (metric, load-region) cross-source ranking-comparison family; (3) pairwise reversal tests within each (metric, load-region) family — per-pair p = max(p_x, p_y) (intersection-union: BOTH conditions must be supported) of the block-bootstrap sign-test p-values read off the SAME resamples that back the preregistered CI rule (`analysis/reversal_analysis.py::_bootstrap_diff_ci`). Family membership for reversals = exactly the tests that reached the pre-registered statistical-support stage (sign change + both margins pass); the multiplicity-corrected headline flag is `supported_after_fdr` | `STATISTICAL_ANALYSIS_PLAN.md` "Multiple-testing correction" |
| Sample-complexity ladder | n ∈ {5, 10, 20, 30, 40} (40 = full), ≥ 500 draws per n, without replacement | `RANKING_PORTABILITY_ANALYSIS_PLAN.md` §C |
| Recovery target | P(recover full-window ranking) ≥ 0.9; recovery = exact-order match AND top-k match, defined before any real output | `STATISTICAL_ANALYSIS_PLAN.md` §F |
| Reversal practical threshold | winning margin > 10% of the losing policy's value, required in BOTH conditions | `RANKING_PORTABILITY_ANALYSIS_PLAN.md` §A |
| Reversal confidence criterion | block-bootstrap CI on the sign of the mean per-window difference excludes zero at 95%, in BOTH conditions | §A |
| Deterministic seeds | every bootstrap/subsample uses an explicitly seeded `numpy.random.Generator`; seeds recorded in outputs (`base_seed` defaults: ranking/reversal 0, sample-complexity 12345+n, concentrated-vs-spread 999) | implementation contract |

## B. Frozen metric scopes (conflict resolution, §E of the task)

`docs/STATISTICAL_ANALYSIS_PLAN.md` §E's older illustrative list names
"TPOT" and "p99 tail latency"; neither field exists in the frozen
`RankingPortabilityCellResult` schema
(`src/robustbench/ranking_portability/schema.py`). The later,
Phase-12-specific `docs/RANKING_PORTABILITY_METRIC_DEFINITIONS.md` is
authoritative by supersession (implemented schema wins over an earlier
aspirational list); the actually-analyzable metric set is:

- `ALWAYS_DEFINED`: `arrival_normalized_weighted_goodput` (**primary
  metric**), `completion_fraction`, `weighted_completion_fraction`;
- `CONDITIONAL_ON_COMPLETION`: `slo_violation_rate`,
  `weighted_goodput`, `mean_latency`, `p95_latency`,
  `request_throughput`, `token_throughput`;
- `CONDITIONAL_ON_OTHER_PRECONDITION`: `mean_ttft`, `p95_ttft` (TTFT is
  a separate preconditioned metric — its precondition is checked
  independently of `completion_fraction`).

## C. Frozen NaN / undefined semantics

Never imputed, never converted to zero, never ranked with fabricated
values:

- an undefined conditional metric excludes that (policy, window)
  observation from that metric's aggregate only;
- a policy with no defined value in a condition is reported via
  `excluded_policies_no_defined_value` and contributes `None`, never
  `0.0`;
- a comparison with fewer than 2 commonly-defined policies reports
  `tau=None` / `rho=None` and flags `k_reduced`, rather than computing a
  fabricated correlation;
- Friedman excludes any policy not defined in EVERY block (complete
  block design) and reports the exclusions;
- BH FDR never rejects a NaN p-value and NaN p-values do not consume
  rank slots;
- the descriptor/telemetry explanatory model excludes windows missing
  any required feature, never imputes them.

## D. Frozen reversal contract

Five mutually exclusive classes
(`analysis/reversal_analysis.py::ReversalClass`), preserving the
preregistered "practical effect AND statistical support, both required"
logic; microscopic or unsupported sign changes are labeled separately
and never pooled into a headline reversal count:

1. `UNDEFINED_UNESTIMABLE` — undefined value, or zero-valued loser
   makes the margin unestimable;
2. `STABLE_NO_SIGN_CHANGE` — includes exact ties;
3. `MICROSCOPIC_SIGN_CHANGE` — sign changed but a margin ≤ 10%;
4. `UNSUPPORTED_SIGN_CHANGE_WIDE_CI` — margins pass but ≥ 1 condition's
   bootstrap CI on the sign straddles zero;
5. `SUPPORTED_PRACTICAL_REVERSAL` — sign change + both margins > 10% +
   both CIs exclude zero.

Criteria were fixed in the plan docs before any Phase-12 outcome
existed and are not adjustable at analysis time.

Multiplicity layer (frozen): the five-class raw classification above is
unchanged; ON TOP of it, Benjamini-Hochberg FDR (q = 0.05) is applied
per (metric, load-region) reversal family, per the plan's own example
family ("all pairwise reversal tests within one load level"). The
per-pair test p-value is the intersection-union combination
max(p_x, p_y) of the two conditions' block-bootstrap sign-test
p-values, computed from the same frozen resamples as the CI rule — no
new inferential procedure. Only pairs that reached the
statistical-support stage (classes 4–5) are reversal hypotheses and
thus family members; pairs in classes 1–3 carry no p-value and are
never rejected. The corrected supported-reversal flag is
`supported_after_fdr`.

## E. Frozen sample-complexity contract

`analysis/sample_complexity.py::run_sample_complexity`:
ladder n ∈ {5,10,20,30,40}; 500 draws per n without replacement;
explicit per-n seeds (`base_seed + n`); recovery defined as
exact-ranking match and top-{1,3} match against the full-window
reference; first n reaching P ≥ 0.9 reported per source/metric.
`compare_concentrated_vs_spread` implements the plan's two purely
descriptive budget comparisons — (i) n=40 concentrated in one source vs
(ii) n≈13 from each of the three sources — measured as Kendall tau
against the full 3×40 cross-source reference, with no framing of either
as "expected".

## F. Frozen temporal design

`analysis/temporal_analysis.py`:

- BurstGPT: native-timestamp EARLY/MIDDLE/LATE terciles (primary) and
  EARLY/LATE bisect (sensitivity split), computed over the 40 BurstGPT
  windows ONLY;
- Bailian/Qwen: relative-order bisect over the 40 Bailian windows ONLY,
  every downstream finding labeled
  `RELATIVE_CHRONOLOGY_ONLY`, never calendar-dated;
- Azure 2024: calendar-anchored split over the 40 Azure windows ONLY at
  the frozen boundary
  `contract.AZURE_2024_CALENDAR_BOUNDARY_EPOCH_SECONDS = 1715731200.0`
  (2024-05-15T00:00:00Z — the exact midpoint of the canonical
  2024-05-10..2024-05-19 collection window,
  `docs/EVIDENCE_INDEPENDENCE_PLAN.md`,
  `configs/workloads/source_registry.yaml`; on the frozen Phase-10
  window index it partitions the 40 Azure windows 17 BEFORE / 23
  AT_OR_AFTER — verified from provenance metadata, never outcomes). The
  launcher refuses any other boundary value (fail-closed);
- SOURCE ISOLATION is mandatory: no source's timestamps or order
  metadata may influence another source's split boundaries or group
  sizes (enforced by per-source maps in the launcher and covered by
  synthetic isolation tests);
- temporal comparisons reuse the cross-source tau/reversal toolkit
  unchanged (source held fixed).

## G. Frozen robustness plan

`analysis/robustness.py` — run alongside every RQ1/RQ2/RQ5 headline
finding, never used to select which finding to report:

- `PRIMARY_ONLY` (11 PRIMARY policies; the 2 STYLE_APPROXIMATION
  policies are the 13-policy robustness stratum, never silently mixed
  into a primary headline);
- `LEAVE_ONE_SOURCE_OUT`; `WINDOW_SIZE_SENSITIVITY` (= the §E ladder);
- `METRIC_DEFINITION_SENSITIVITY` (frozen per-policy exclusion rule vs
  same-family drop-the-whole-condition alternative);
- `LOAD_CALIBRATION_SENSITIVITY` (4-region subset of the 6-region
  grid); `TEMPORAL_SPLIT_SENSITIVITY` (bisect vs tercile);
- `LEAVE_ONE_POLICY_FAMILY_OUT` (one mechanism family removed at a
  time);
- `SLO_DEFINITION_SENSITIVITY` — the alternative SLO-synthesis rule
  changes request labels at synthesis time and **cannot be recomputed
  from the frozen campaign's columns**; explicitly flagged
  `NEW_EXECUTION_REQUIRED_FOR_THIS_SENSITIVITY = YES`, never disguised
  as a row filter;
- seed sensitivity: **not applicable** (deterministic simulator given
  identical inputs).

## H. Frozen explanatory (never predictive) model

`analysis/telemetry_explanation.py`: ONE pre-specified logistic
regression of reversal-indicator on the FIXED descriptor set
(`burstiness_b`, `prompt_tokens_cv`, `output_tokens_cv`,
`long_context_fraction`, `concurrency_proxy`); no feature search, no
model comparison after seeing results; no `predict`/`route`/`select`
function exists — explanatory association only
(`docs/CLAIM_BOUNDARIES.md`).

The window-level reversal-site indicator (constructed by the launcher's
`_window_reversal_sites`) applies the plan's own window-indexed
meaningful-reversal definition (`RANKING_PORTABILITY_ANALYSIS_PLAN.md`
§A indexes a reversal "at a given (source-pair, window, load-region,
metric)"; `STATISTICAL_ANALYSIS_PLAN.md` §G asks whether "a given
window is a reversal site for a given pair (A, B)"): a window w of
source X is a reversal site for pair (a, b) at a load region iff
(i) sign(a_w − b_w) is defined, nonzero, and opposite to the sign of
source Y's aggregate (a − b) difference at that region, AND (ii) the
frozen 10% practical margin gate holds in BOTH directions (window side
and other-source aggregate side). Undefined values, exact ties,
microscopic margins, and zero-loser (unestimable) margins are EXCLUDED,
never imputed — mirroring the frozen reversal contract. ALL unordered
PRIMARY policy pairs × source pairs × load regions are enumerated and
reported; no pair is selected based on results, and no real outcome was
consulted in defining the rule.

## I. Deterministic input/output pipeline

- **Consolidation** (`analysis/consolidation.py`,
  `scripts/ranking_portability/consolidate_phase12_campaign.py`):
  reads shard outputs from an explicit `--shard-output-dir` (no
  default), verifies every row's identity/seed/load-factor/schema/
  telemetry against the frozen manifest, rejects wrong-provenance
  shards wholesale, detects cross-shard duplicates, re-checks rep0/rep1
  input identity on the ACTUAL rows, and writes one canonical
  consolidated artifact only if complete-and-valid.
- **Independent matrix validation** (`analysis/matrix_validator.py`,
  `scripts/ranking_portability/validate_phase12_completed_campaign.py`):
  re-derives the 18,720-cell Cartesian product from the frozen contract
  module without trusting the consolidator; checks dimension counts,
  secondary-stratum leakage, Phase-11 assignment coverage, immutable
  hash preservation, and rep input identity.
- **Analysis-input admission** (`analysis/input_manifest.py`): refuses
  (raises) unless the independent validation report is CLEAN; the
  manifest records campaign freeze SHA, canonical
  `consolidated_result_sha256` (binds the exact scientific content),
  validation-report SHA, analysis git SHA, contract version, metric
  definitions version, and policy-panel identity SHA.
- **Output contract** (`analysis/output_writer.py`): every analysis
  artifact is stamped with campaign freeze SHA, consolidated result
  SHA, analysis code git SHA, and contract version. Canonical relative
  output namespace: `artifacts/analysis/phase12/*` (ranking
  correlations, top-k overlap, pairwise reversals, sample complexity,
  temporal robustness, telemetry explanation). Writers take explicit
  output paths; no default output location exists.

## J. Result-blindness guard

`analysis/result_blindness.py::assert_not_live_campaign_path` raises
`LiveCampaignPathBlocked` for any path resolving under
`artifacts/campaign_results` unless `allow_live=True` is passed
explicitly. Both CLI scripts call it on every user-supplied input path.
Regression tests cover: remote live path blocked, local
`artifacts/campaign_results` blocked, explicit tmp fixture path
allowed, explicit `allow_live` override.

## K. Synthetic fixture coverage

`tests/ranking_portability_analysis_fixtures.py` +
`tests/test_ranking_portability_analysis_*.py` (9 files, 93 tests)
cover: identical ranking (tau=1), completely reversed (tau=-1), partial
top-k change, exact ties, partial ties, undefined-policy exclusion,
bootstrap CI shrinkage, BH FDR (incl. NaN handling), Friedman
incomplete-policy exclusion, zero-completion rows, NaN conditional
metrics, TTFT-specific undefinedness, style-policy stratum exclusion,
clear supported reversal, microscopic sign flip, unsupported wide-CI
reversal, stable/tie ordering, undefined-unestimable reversal,
deterministic repetitions, mismatched repetitions, missing cells,
duplicate cells, unknown cell IDs, wrong campaign hash, wrong load
assignment, wrong-provenance shards, failed cells, schema-invalid rows,
idempotence, full-scale fabricated 18,720-cell matrix validation,
temporal split edge cases (odd counts, single window), sample-complexity
ladder determinism, concentrated-vs-spread, descriptor signal, null
descriptor signal, missing-descriptor exclusion, all robustness filters,
admission refusal on failed validation, output identity stamping, the
blindness guard itself, and every launcher fail-closed gate (admission
flags, corrupted admission campaign/full-matrix/consolidated hashes,
tampered consolidated artifact bytes, analysis-code git-SHA mismatch,
output-namespace violations, input/output overlap, live-path blocking)
plus a full-fabricated-matrix launcher happy path that verifies the six
canonical artifacts are written, identity-stamped, and that the admitted
input file's bytes are unchanged. The audit-seal pass additionally
covers: non-frozen Azure boundary refusal, the frozen boundary's exact
collection-window-midpoint identity and before/at-or-after semantics,
source-isolation of every temporal split (perturbing other sources'
timestamps/order metadata cannot change BurstGPT/Azure/Bailian groups;
40-window membership preserved), bootstrap sign-test p-value extremes,
reversal BH family membership + intersection-union p-value semantics,
telemetry reversal-site margin-gate/zero-loser/no-flip semantics,
Friedman 120-window pooled-block scope, and the per-source × metric
sample-complexity scope with trivially-exact n=40 recovery. **No real
campaign row is used anywhere.**

## L. Frozen code/test identities (SHA-256)

```
8fd0c6837ac32a2c5d775ff4b180d54e78b00508379c36829f6d25cce0d46b4c  analysis/consolidation.py
3d409050a9011b4378cc481dec51f4a27cdccae89ed58ed0717b81a946ebf0c2  analysis/contract.py
a4e0deff7871b39c5dd346318663ccf9bddb89584504f0b3d8d996f493e95f3b  analysis/input_manifest.py
78d74f3e847090c3823daada175b616503e49b8a2ab366bba977130bb3810c7a  analysis/matrix_validator.py
fb98372d4450e1006bbed5d850d4ea26b0a05e4eec743750bada3ee8d9ea0fd2  analysis/omnibus.py
f4f3cb6441ab1e7a3af460c7484e5a916fff5379d77945245aace49ac451ce4b  analysis/output_writer.py
449bce19f2d41143bb502e0cba87cb03f62645f4539c1c8b848a4349e357a243  analysis/ranking_analysis.py
8227cd9601ec2bd7b7d53534c68ad98c3e2d18bb1262d1abafee831e8475eead  analysis/result_blindness.py
cde759b146ba51c3f5cb8674842ced6fc9198612254b00acc739a6c2b4d10b5f  analysis/reversal_analysis.py
55f4898801f1049c02badfcb8f1f6bc92580d454577f9be40b25221ead1ddd69  analysis/robustness.py
36b53b1e6c63cfe6329e49ac7d8a08614623c51c6ad2f3ef3f5f7101ef390acf  analysis/sample_complexity.py
76ecae65f800bebe2ecfed80efb9757428763423e8380203c0b3460e8cf00168  analysis/stats.py
d5f534e6418d0fa93d72c192ed6de35925f87a10dfa697f8527b043464be5a98  analysis/telemetry_explanation.py
74b204c32c7358c659ab04ffec64c42a47d78cbafac39d826a48ca427d078aed  analysis/temporal_analysis.py
bc719ca4c262d199a53fabfbcb87f82190740e6c09854b8bfc1e5505c6f4ca93  scripts/.../consolidate_phase12_campaign.py
920cd5a355a4ebae42669afd0e483a287e8e43c23cccbf933e3bb7288b9efc11  scripts/.../validate_phase12_completed_campaign.py
2cb784563dafffda542364a003c15a4c2f98473ce8d2fbc71a01853fc6d831d9  scripts/.../run_phase12_analysis.py
da8825a7cd782364041ddbaaca9ba3c0ce719817212ba889d4598fcc3405c9bd  tests/ranking_portability_analysis_fixtures.py
30afb645a300355e2d2abee56a59afa59fbedacb8a2ff6a4f94429540ccd0c9a  tests/..._consolidation.py
bcd6db0bed50a14dc44bba3f9920b933a5a9fd1f803b488de07be9c170111b9f  tests/..._matrix_validator.py
a19adfd84877ba74a331877a705c037d61497b0a437cd232aa50847895dd6999  tests/..._prefreeze_gates.py
7c7b414f5fc7dafbb4fac07c82b4aa84401e362f719e6ddb3861f77d485eddb1  tests/..._ranking.py
882cadd2b25fe0c5e206ba5501f67c0f23d72dc67888e63632d4e21d1b2765b9  tests/..._reversal.py
98778682e9e1f6aab3b22ba89fc9b8d860a993461073c34c05a54b1e26421d5b  tests/..._sample_complexity.py
1014baaa3f71c3f267dc27ddb2841f609d9e76e0fcac406342fe0e55ef132446  tests/..._stats.py
a723f9538663b2bb2d1041b06120196722b75234aab05e6898fb4921e66248a2  tests/..._temporal.py
fb0d15b4bfb41997223ce13f8c442c568d40e2e64e57f613306dae4e509f9404  tests/..._launcher.py
```

(paths abbreviated: `analysis/` =
`src/robustbench/ranking_portability/analysis/`; `tests/..._x.py` =
`tests/test_ranking_portability_analysis_x.py`.)

Test status at freeze (post-audit seal): targeted analysis tests
**93 passed**; full repository suite **337 passed** (4 pre-existing
benign scipy precision-loss RuntimeWarnings in
`characterization/descriptors.py`, unrelated to the analysis package).

## M. Real-analysis launcher (prepared, NOT executed)

The exact launcher is
`scripts/ranking_portability/run_phase12_analysis.py`. It fails closed
(exit 2, nothing analyzed) unless ALL of the following hold:

1. the Phase-12D analysis-admission manifest declares
   `PHASE12_COMPLETED_CAMPAIGN_VALID = true` and
   `PHASE12_ANALYSIS_INPUT_ADMITTED = true`;
2. its `campaign_freeze_sha256` equals the pinned
   `81fa3d9b48a2241001e6820942d4542dcc5b5e30973ad9d2786e72972494f57a`
   and its `full_matrix_hash` equals the pinned
   `832d96d7ff4d5e8843c233a6a4708bbbbc578ef6b65307c37f5ac127c62c1ccf`;
3. the SHA-256 of the consolidated artifact's file bytes equals the
   pinned admission-bound
   `73adf7d97f06985ec8f8e1c2f794fd43178433eb198e1c00705e817f4bde9c26`;
4. `git rev-parse HEAD` equals the caller-pinned LITERAL
   `--expected-analysis-git-sha` (the sealed analysis-code commit; the
   verified SHA is stamped into every output artifact) — command
   substitution like `$(git rev-parse HEAD)` is NOT acceptable here,
   it must be the externally frozen literal;
5. the consolidated matrix passes INDEPENDENT re-validation
   (`matrix_validator.validate_completed_campaign`) before any metric
   is aggregated;
6. `--azure-boundary-epoch-seconds` equals the frozen canonical
   boundary `1715731200.0` (2024-05-15T00:00:00Z) exactly.

It writes only the six canonical artifacts into a fresh
`artifacts/analysis/phase12/` namespace (refuses any other location,
any pre-existing content, and any overlap with the admitted input,
which is opened read-only and never modified).

Exact command (run on Wulver in the subsequent real-analysis task --
NOT in this prefreeze/audit task). The sealed analysis-code commit is

**ff087e8c6bd3047229ddcdb4b5600b9ddf8e3c67**

("Seal Phase-12 analysis prefreeze: temporal source isolation, reversal
BH layer, frozen Azure boundary"). The production run must `git
checkout` that exact commit and pass its literal SHA — this
documentation-only follow-up record names it, but the analysis must
execute the sealed code commit exactly (its tree is identical to this
record's tree except for this section):

```
SEALED=ff087e8c6bd3047229ddcdb4b5600b9ddf8e3c67
git -C /project/ikoutis/sv96/github/llm-serving-scheduler-lssp-phase12-analysis checkout "$SEALED"
cd /project/ikoutis/sv96/github/llm-serving-scheduler-lssp-phase12-analysis
PYTHONPATH=src python scripts/ranking_portability/run_phase12_analysis.py \
  --admission-manifest /project/ikoutis/sv96/github/llm-serving-scheduler-lssp-phase12-provenance-repair/artifacts/manifests/ranking_portability_phase12_analysis_input.json \
  --consolidated-artifact /project/ikoutis/sv96/github/llm-serving-scheduler-lssp-phase12-provenance-repair/artifacts/campaign_results_enriched/81fa3d9b48a22410/consolidated.json \
  --campaign-manifest /project/ikoutis/sv96/github/llm-serving-scheduler-lssp-phase12-provenance-repair/artifacts/manifests/ranking_portability_phase12_campaign_freeze.json \
  --compact-window-index /project/ikoutis/sv96/github/llm-serving-scheduler-lssp-phase12-provenance-repair/artifacts/manifests/ranking_portability_pilot_v2_windows_index.json \
  --output-dir /project/ikoutis/sv96/github/llm-serving-scheduler-lssp-phase12-analysis/artifacts/analysis/phase12 \
  --expected-analysis-git-sha "$SEALED" \
  --azure-boundary-epoch-seconds 1715731200.0 \
  --allow-live
```

The admitted consolidated-artifact path above was resolved
result-blind: filename + filesystem metadata + SHA-256 identity check
only (`73adf7d97f06985ec8f8e1c2f794fd43178433eb198e1c00705e817f4bde9c26`,
37,252,923 bytes — byte-hash matches the admission manifest exactly; no
scientific row was deserialized).

This launcher was prepared but NOT executed in the prefreeze task:
`COMPARATIVE_PILOT_V2_RESULTS = NONE`,
`RANKING_ANALYSIS = READY_NOT_STARTED`.

## N. Out of scope (unchanged)

Selecting a "winning" scheduler, exploitability/regret, portfolio or
online-selector construction — see `docs/CLAIM_BOUNDARIES.md` and
`docs/OVERLAP_LEDGER.md`. The explanatory model must never be repackaged
as an online selector.
