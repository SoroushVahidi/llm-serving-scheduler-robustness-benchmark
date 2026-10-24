# Prospective bounded token-budget sensitivity

Recorded before any new simulation outcome. Baseline manuscript/PR23 head:
`4c08660eeb528a5a459800bbc79771f4b8e4dbfc`. Frozen C01 execution:
`2d8342e699f35044044ac518c0b75a3c4a1c768c`. No engine or policy edits.

## Hypothesis and possible rejection

H1: lowering only the work-token budget from 32768 to 2048 and 1024,
with eight resident slots, causes chunked-FCFS and decode-first to select
different per-request token spans or batch memberships on at least one
selected intact condition. Span-list permutations alone do not count.
Mechanism predicted: earlier resident prefills exhaust work before later
resident decodes under chunked-FCFS; decode-first protects those decodes.
Reject H1 for this finite design if all matched normalized event sequences
and terminal states agree at both perturbed budgets. Losing the original
sufficient nonbinding bound does not imply this mechanism is reachable.

Secondary questions: do whole-FCFS or SLO-gated change admissions, decode
service gaps, latency/TTFT/TPOT, finite-window throughput or deadline
attainment? Does SLO urgency reach its unchanged 0.495 s threshold? Does
the number of distinct terminal behaviors increase? Are top sets or
strict-10% policy-pair preferences different from their matched baseline?
A substantive performance effect requires changed execution plus at least
1 ms absolute mean/p95 latency or TTFT change, or 1% relative throughput
change, or 0.005 absolute ANWG change (one of 200 requests). Smaller effects
are reported without treating floating-point rank changes as science.
The original strict >10% losing-value reversal definition is unchanged.

## Input-only selection and configuration

Original input file SHA256:
`a77bf5420ca8a55c3765919dbf42e774794f471da6ff404d0ad19a53c43a8c8c`.
All 720 original condition request hashes must verify. The engine rejects
prompt > budget for every policy. The minimum window maximum prompt is
6180 for Azure and 5773 for Bailian; neither can test binding chunked work
under the <=4096 eight-slot bound without changing inputs/domain. BurstGPT
has 17/40 windows <=512, 27/40 <=1024, 36/40 <=2048, 39/40 <=4096.

Choose lexicographically first three BurstGPT windows with
512 < maximum prompt <=1024: pilot_v2_w16 (1005), w23 (790), w28 (648).
This input-only stratum permits multi-batch individual prefills and every
policy's whole-prompt admission. It is a targeted feasibility stratum,
not representative sampling. Retain all 200 requests per window, unchanged
seeds, token counts, deadlines and arrival factors from the frozen inputs.
Keep LOW and HIGH_PRESSURE to cover the existing setting endpoints.
No source-mean cross-source inference is possible from this subset.

Budgets: original 32768; moderate 2048 (four 512-token chunks); restrictive
1024 (two chunks; still >= each selected prompt). Potential chunked work
at eight slots is 4096. Whether these budgets actually bind is measured,
not assumed. Hold context=32768, KV=262144, max_sequences=64, block=16,
dt=0.001 s, drain=50 s fixed. All four original adaptations, unmodified.
Only budget varies within every matched condition. 3 windows x 2 settings
x 3 budgets x 4 policies = 72 cells. No new random seeds or synthetic load.

## Pilot, execution and stopping

First run the first window at HIGH_PRESSURE for all 12 budget-policy cells.
Validate each journal with the unchanged independent C01 referee; require
baseline metrics and full terminal states to match the archived baseline.
Record input/config/code hashes, outcomes, runtime and binding/urgency
telemetry without influencing scheduling. Pilot cells are part of the 72,
reused only by verified identity. Stop on invalid input, invariant failure,
baseline disagreement, or no feasible comparison; no policy redesign,
request filtering, horizon extension or outcome-driven replacement.
If pilot runtime projects a study >3 minutes, use persistent background
execution and end the turn with startup status per the user's job rules.
Otherwise execute the remaining bounded cells. Raw inputs/journals remain
in a new local artifact directory; no dataset/release publication.

## Analysis and uncertainty

Primary unit is a frozen window, with paired budgets/policies and settings.
Compare exact terminal states and events normalized within each batch;
report raw-order differences separately. Recompute metrics independently
from terminal records and reconstruct mechanism telemetry from journals.
Report absolute differences, relative differences, full ranges, counts and
denominators. Use the inherited 1e-12 scale tolerance for numerical ties,
and exact rational evaluation for strict practical reversal boundaries.
No population CI or p-value: three selected, temporally related windows
and two deterministic settings do not support IID/population inference.
Original 5760 cells, 1440 matches and 0/864 reduced source-mean reversals
remain unchanged and separate. No physical GPU performance claim.
