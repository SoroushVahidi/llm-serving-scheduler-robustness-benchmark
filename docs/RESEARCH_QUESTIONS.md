# RESEARCH_QUESTIONS.md

Revised 2026-08-31 following Gate A resolution (`docs/OVERLAP_LEDGER.md`,
`docs/GO_NO_GO_GATES.md`). The original bootstrap freeze (2026-08-31, earlier
same day) is preserved in the changelog below for audit purposes.

**RQ1.** How stable are scheduler rankings across independent workload sources?

**RQ2.** How stable are scheduler rankings under temporal, provider, and
domain shifts?

**RQ3.** To what extent do rankings obtained on synthetic stress workloads
transfer to rankings on independent real-trace-derived workloads?

**RQ4.** Which source-native observable workload characteristics are
associated with cross-distribution scheduler rank reversals?

**RQ5.** How many independent workload windows are required before a
comparative scheduler ranking becomes statistically stable?

**RQ6.** Do representative simulated scheduler rankings and cross-workload
rank reversals reproduce on a real serving engine?

## Secondary robustness/sensitivity analysis (not a headline RQ)

**Load-level dependence** — how scheduler rankings from RQ1–RQ4 shift across
LOW/PRE_KNEE/KNEE/OVERLOAD (`docs/LOAD_CALIBRATION_PROTOCOL.md`) — is
deliberately **not** a headline research question. LLM 2026 already ran a
closely related load-scaling study (`public_replay_load_scaling_v1/v2`, the
same 60 canonical windows and an `{1,2,4,8,16,32,64,128}` load-factor grid);
promoting load-level dependence to a headline RQ here would risk exactly the
overlap `docs/OVERLAP_LEDGER.md` and `docs/CLAIM_BOUNDARIES.md` prohibit.
Load-level is instead treated as one axis of robustness/sensitivity checking
applied *to* RQ1–RQ4's findings (`docs/STATISTICAL_ANALYSIS_PLAN.md` §D), using
this project's own independently frozen calibration protocol and
independently established workload windows (`docs/EVIDENCE_INDEPENDENCE_PLAN.md`),
never LLM 2026's window set or load grid.

## Relationship to the overlap audit

RQ2 and RQ4 (temporal/provider/domain shift; source-native characteristics
associated with reversals) sit closest to prior work but are differently
scoped: a pre-registered, multi-source, multi-metric ranking-stability study
using independent windows, not a headroom/exploitability argument built on a
shared window set.

## Changelog

- 2026-08-31 (initial freeze): RQ1–RQ6 as specified in the bootstrap task,
  including load-dependent rank reversal folded into RQ2/RQ4.
- 2026-08-31 (Gate A resolution, same day): RQ2 reworded to "temporal,
  provider, and domain shifts" (was "temporal and provider/domain shifts" —
  wording only); RQ3 reworded "independent real-trace-derived workloads" (was
  "real-trace-derived workloads"); RQ4 reworded "source-native observable...
  cross-distribution scheduler rank reversals" (was "observable...rank
  reversals", to make explicit that only source-native, not synthesized,
  descriptors are used, and that reversals are cross-distribution, not
  cross-load); RQ5 reworded "independent workload windows"; RQ6 reworded
  "representative...cross-workload rank reversals" (was "important...rank
  reversals"). Load-level dependence demoted from an implicit part of
  RQ2/RQ4 to an explicit secondary analysis, per the Gate A resolution.
