# Phase 1: structural urgency investigation

Recorded before proposing or executing any new workload experiment.
Baseline: actual PR24 head `8a32ecf6e5e5dcca114594b320ac7c5210d8c543`.
Frozen execution: `2d8342e699f35044044ac518c0b75a3c4a1c768c`.
Examined: frozen `research/lssp-c01/{policies.py,engine.py,PROTOCOL.md}`,
the historical `src/robustbench/policies/slai_faithful.py` for the distinction
between implementations, and current M3 contract/design/performance/
sensitivity/discussion/related-work claims. No policy or engine is modified.

## Exact activation condition

At planning time t a request i is in the critical list if and only if:
(i) it is an arrived, unfinished resident in the engine's live view;
(ii) acknowledged prefill equals its positive prompt length;
(iii) its anchor a_i is not None; and (iv) the implemented subtraction
`t - a_i >= 0.495` is true. This is a per-request predicate; the gate is
active in a batch iff at least one request satisfies it. In reachable valid
states (iii) follows from (ii), since final prefill establishes the anchor.
Equality belongs to the critical side. Binary arithmetic, not rounded
printed ages, governs exact boundary comparisons.

The anchor is the end of the last executed decode, or the end of final
prefill before the first decode. It is NOT arrival, admission, current
batch start recomputed unconditionally, a request deadline, or a predicted
completion time. Omitted decodes retain their previous anchor. Since an
unfinished resident is eligible work, no idle jump occurs during its wait.
For ideal fixed dt, m consecutive omitted batches give age m*dt. At dt=1ms,
495 consecutive omissions are necessary for the 495ms gate; floating
roundoff can affect exact equality at that boundary, not the much smaller
bounds below.

Critical requests precede resident prefills, prompt-length-ordered waiting
prefills, and residual decodes. Activation does not by itself prove changed
membership or performance: if all work fits, changing span order changes no
batch-end state. For the examined B>=1024, K<=8 profiles, all critical
decodes would fit the leading budget (at most K one-token decodes).

## Inputs, deadlines, remaining work and residency

* The fixed 0.495s is the C01 protocol's declared 0.5s uniform TBT minus
  a 5ms margin. This lineage explanation is NOT a runtime parameterization:
  Config has budget, max_sequences, context, kv_capacity, block, dt, drain;
  neither Config nor View has TBT, threshold, deadline or service estimate.
* Synthetic completion deadlines and actual/remaining output lengths do
  not enter the policy. Deadlines are validated as finite and consumed by
  the ANWG metric. Any finite deadline-only change leaves all execution
  events unchanged; it can only change the deadline score.
* Prompt length and acknowledged prefill determine decode eligibility and
  prefill demand. Generated count determines the next span index, not
  estimated remaining service. Output length affects engine completion and
  reservation release, indirectly changing future competition.
* Waiting requests and resident prefills are not urgency candidates,
  however long they have waited. An active request reserves the entire
  context. No eviction, preemption or recomputation occurs. Admission and
  reservation release affect contention, not the threshold itself.
* Existing LOW/HIGH_PRESSURE labels jointly scale arrivals and metric
  deadlines. Varying those labels is not an isolated urgency/SLO change.

## Agreement and defect assessment

The implementation matches the explicit CM-0.1 specification: exact 495ms
predicate, acknowledged-progress anchors, declared priority classes, stable
order within resident lists, and prompt-length waiting admission. The
historical `slai_faithful` implementation has configurable class-to-TBT maps,
offsets and different clock conventions; C01 intentionally excludes these.
Neither that class nor full native SLAI is the evaluated C01 policy.
Treating historical constructor arguments as C01 controls would be an
implementation substitution, not a valid sensitivity.

No unconditional-anchor-reset or deadline-wiring defect was found. Existing
engineering tests include a manually supplied state with age 0.6s and check
critical decode priority. That establishes branch functionality, not
reachability on frozen workloads or scientific activation evidence.

## Original proof and finite-work extension to be independently checked

Original nonbinding case: total selectable chunked work is <=512K<=4096,
versus B=32768. Every ready decode runs, its anchor equals the next planning
clock, and age is always zero. This is a structural result, not a small
sample inference.

First-activation certificate for the binding cases: let P be all prompt
work in the finite workload, B the positive integer budget, K the residency
limit, B>K-1, and dt fixed. Suppose the first critical decision exists,
and i is a ready decode reaching it. In every consecutive omitted batch
since its anchor, no critical request yet existed. The residual loop would
execute i unless the budget had been exhausted: residency cannot exclude
an already resident request. At most K-1 other decodes execute, each using
one token. Thus each such batch consumes at least B-(K-1) prefill tokens.
No recomputation occurs, so for m omissions:

    m [B-(K-1)] <= P,
    age <= dt floor(P/[B-(K-1)]).

If this upper bound is strictly below 0.495s, first activation is impossible.
This is a sufficient certificate of inactivity, not a necessary condition
for activation; failure of the certificate would not prove reachability.
It allows arbitrary arrival/deadline arrangements with the same P and
resources. It applies only before the first activation and does not assert
an arbitrary-policy waiting-time bound.

The selected windows' P values are 39300, 52250, 44765. At B=1024, K=8 the
candidate bounds are 38, 51, 44ms; at B=2048 they are 19, 25, 21ms.
These are conservative bounds, not observed maxima. All are far below
495ms. More generally the unchanged input-domain rule prompt<=B gives
P<=NB. For N=200, B>=1024, K<=8, the ideal upper bound is at most 201ms,
also below 495ms. The tighter nonbinding proof covers original profiles.

## Claim audit and scope

The current manuscript already calls the gate inactive, attributes baseline
effects to admission ordering and whole-prefill/decode exclusion, and calls
PR24's stalls residual-decode deferrals. No measured effect was incorrectly
attributed to executed urgency decisions in the examined scientific text.
The label "SLO-gated" can nevertheless invite confusion between token-gap
urgency and synthetic completion deadlines; making the distinction explicit
and adding the finite-work certificate would strengthen interpretation.

This does not show the branch is unreachable for every Config/workload
accepted by the engine, nor validate native SLAI. It shows why the original
and existing budget sensitivity are poor tests of active urgency. A claim
about a new active operating region would require a separate supported
threshold interface or a different workload/resource/timing contract.
