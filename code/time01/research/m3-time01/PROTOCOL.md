# M3-TIME01 prospective sensitivity protocol — 2026-10-23

Question: do the CM-0.1 policy rankings and latency/throughput trade-offs persist
when actual batch duration depends on executed prefill/decode composition?
Freeze this protocol, implementation, input selection and parameters before any
scientific variable-timing outcomes. No adaptive tuning or further campaigns.

## Contract and model

Use byte-identical C01 policies.py, Config and online View, vendored in frozen_c01
from C01-FULL (pilot engine execution commit9aed0206; full launcher2d8342e6).
The original engine/referee/tests are retained unchanged as regression oracles.
Admission, reservation, work spans, token budget32768, max_sequences64,
context32768, block16, last-arrival+50-second administrative horizon, information
and all metric definitions remain unchanged. Capacities131072/262144 reserve4/8
contexts. No policy RNG. Original workload synthesis seeds remain unchanged.
Only batch duration and the timing consequences change. No arrival/deadline
rescaling or load recalibration. LOW/HIGH_PRESSURE remain inherited labels,
not claims of equal measured pressure under the new model.

Shared model composition-v1 (seconds):
  T(P,D) = 0.0005 + (0.0005/512)*P + (0.0005/8)*D.
P = sum of actually executed prefill-span lengths; D = executed decode tokens
(one per selected decode request). Count executed work, not eligible/offered work,
full request lengths, latent output or policy labels. No mixed interaction term.
This is an explicit normalized model-sensitivity scenario, NOT a GPU calibration.
0.5ms overhead plus 0.5ms per512 prefill tokens plus0.5ms per8 decode tokens
anchors a512-token pure-prefill or8-token pure-decode batch at the old1ms cost.
Parameters are engineering reference choices, not fitted to outcomes.
The function is order-invariant and shared by every policy. It is positive and
finite for the entire contract domain P+D<=32768 and at most8 executing requests.
It extends linearly without clipping over that domain, including whole prompts
larger than512. There is no claim of measured support at any mixed-batch input.
Reject malformed work/nonfinite durations. Default fixed mode retains exactly
T=Config.dt, original journal schema and terminal records.

Reviewed physical evidence: heuristic-evolution results/gpu_calibration,
Qwen2.5-0.5B;80 training/36 validation points, prompt32..2048, output16..256,
batch1/2/4/8 (validation1/3/6). Single-request prefill fit only, decode fit uses
full prompt+output context, R2=.258; no mixed/chunked-batch measurements.
Prefill batch>1 lookup behavior differs greatly from fitted batch1 rows. Environment
snapshot postdates fit. Source hashes are preserved in the private audit.
These coefficients do not defensibly calibrate CM-0.1's mixed batch domain.
They inform the qualitative separate prefill/decode dependence only. Historical
calibrated replay did not consume decode predictions in its simulation clock;
native Sarathi/vLLM and module interventions used different contracts.
No physical performance/ranking prediction or mixed-interaction calibration claim.

At batch start, select using the existing policy and currently eligible arrivals.
Compute T from its legal work and advance the real event clock to t+T; acknowledge
all spans at that time. Arrivals inside the batch become eligible only at the next
batch. Completion, first-output, urgency anchors and metrics use those times.
A batch that cannot finish by the unchanged horizon is not executed; record its
planned spans/duration. Do not admit or partially execute it. Independent checks
reconstruct timings, state, metrics, urgency and policy intent including this stop.

## Deterministic workload selection and reuse

Use frozen C01 full-inputs.json SHA256
a77bf5420ca8a55c3765919dbf42e774794f471da6ff404d0ad19a53c43a8c8c.
For each original source's40 LOW windows, recursively halve sorted windows by
(1)mean prompt length, (2)mean output length within each half, (3)fraction of
requests sharing an arrival timestamp within each resulting quarter. Break every
tie by window ID. Eight bins of5 windows result. Select the median window ID
within each bin. Selection uses inputs only, never scheduler outcomes. Save all
120 descriptors, bin membership and24 selected windows. Retain exact LOW and
HIGH_PRESSURE request lists, seeds and factors for these24 windows.
24*2conditions*2capacities*4policies =384 new variable-timing cells.
Reuse all384 matched validated fixed C01 result records, matching request hash,
condition, policy source, configuration, seed/factor and saved identities. Validate
hashes against the saved complete C01 index. Do not rerun fixed baselines as a
campaign. Four selected LOW BurstGPT capacity4 records (one per policy) may be
replayed solely as an explicitly logged regression test of fixed-mode identity.
Other fixed checks use existing synthetic contract fixtures.

## Analysis frozen before outcomes

Preserve every cell including unfinished or missing metrics. Export original
metrics including mean/p95 latency, token/request throughput, completed population,
TTFT/TPOT, goodput, work and observation interval. Report paired new-minus-fixed
and relative changes at identical cell identity. Source means give each selected
window equal weight, separately by condition/capacity/policy. Means of window p95
are not pooled p95. Include aggregate mean differences, all policy pairwise
contrasts, exact ranks/top sets, rank changes across timing modes, and strict
practical reversals across timing modes at window and source-mean levels.
Primary practical margin is the original strict >10% of the loser at BOTH
endpoints with opposite oriented signs; exact binary-float rational arithmetic,
zero losers/missing values unestimable, ties eligible. Export numerator, eligible,
total and unestimable counts. Rank all11 original endpoints; preserve exact ties.
No new threshold is primary; no p-values, confidence intervals or independent
replicate claims.384 deterministic cells are paired conditions on24 correlated
selected windows, not384 independent replicates.

Record per-batch P,D,duration, ready/critical/selected-critical/omitted decode counts
and maximum anchor age (threshold.495s unchanged). Report duration min/mean/p50/
p95/max, pure/mixed batch counts, total selected work, urgency activation, waiting
to first admission, completion/censoring and validation status. Independently
reconstruct every event's duration and metrics; preserve journals for review.
A separate policy replay verifies original plan outputs against reconstructed
online state. Completion requires exact384-cell coverage, hash/source/manifest
consistency and all journal validations. Analysis follows later on user request;
submission/initial health are not a completion or scientific-success verdict.

## Execution and stop

Wulver SLURM, one task/CPU,4GiB, general/standard, account ikoutis,2h walltime,
no GPU or array. Single durable project directory, private permissions. Freeze
Git SHA plus per-source/input/manifest hashes; verify identical environment code
before submission and at runtime. Refuse output overwrite and concurrent runs.
Persistent submission lock; recheck queue immediately before one submission.
No automatic retries. Logs/results/manifests stay in project storage. Stop new
cells at90min, leaving time for graceful exit; partial results remain preserved.
Monitor at most approximately120s after submission, then stop interaction.
No manuscript, handoff, old evidence or PR edits; no merge/push/public data release.
