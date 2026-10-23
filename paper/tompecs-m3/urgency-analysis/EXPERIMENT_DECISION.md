# Phase 2 decision: no new SLO/deadline experiment

Phase 1 was recorded in commit `c99dce3` before this decision.

The authorized isolation is one relevant SLO/deadline operating parameter,
with fixed policies, budget, timing and workload. C01 has no such scheduler
parameter: its 495ms threshold is a literal in the frozen policy, while
completion deadlines are metric-only fields. Therefore:

1. A finite deadline-only sweep cannot activate urgency or change any
   execution event. It could change ANWG solely by moving the evaluation
   cutoff. That is not evidence about an urgency mechanism.
2. The original contract serves every ready decode. Even a hypothetical
   smaller positive token-gap threshold would remain inactive there.
3. PR24's binding-budget conditions have a finite-prompt-work inactivity
   certificate. Their unchanged 495ms gate cannot activate even if arrival
   timing were changed while retaining the same finite work/resources.
4. Replacing `.495`, borrowing the historical scheduler's `default_tbt`,
   assigning new classes, or silently importing a configurable descendant
   would change the frozen policy/interface. No such change is made under
   the instruction not to modify the policy to force activation.

Accordingly no moderate/strict runtime SLO settings are invented and no
new scientific pilot or campaign is launched. This is not an inconclusive
parameter search: the requested single-parameter activation comparison is
not represented by the current C01 interface. A future explicit decision
could authorize a parameterized-contract investigation, but no such work
is started here. The implementation is not corrected because it agrees
with its declared fixed-threshold specification.

Remaining authorized work is bounded saved-evidence verification: reconstruct
age/omission histories in the 18 existing SLO-gated journals (six conditions
at three previously executed budgets), independently check the analytic
certificate, check exact predicate boundary behavior with a supplied online
state as an engineering unit test, rerun existing regressions/scientific
checks, and make concise supported manuscript clarifications. Engineering
tests do not establish reachable scientific activation. Counterfactual
threshold counts on an old trajectory would not establish the performance
of a newly active policy, so none are presented as experimental results.

Supported outcome: C, strengthened by an analytic inactivity certificate
for the examined contracts. No evidence supports A, B or D for a new study.
The functional branch in a hand-supplied aged state is not outcome A/B.
