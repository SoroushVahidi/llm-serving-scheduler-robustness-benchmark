# RESEARCH_QUESTIONS.md

Frozen at bootstrap time (2026-08-31). Wording adjustments require a note in
this file's changelog, not silent edits.

**RQ1.** How stable are scheduler rankings across independent LLM workload sources?

**RQ2.** How stable are scheduler rankings under temporal and provider/domain shifts?

**RQ3.** To what extent do rankings obtained on synthetic stress workloads transfer
to rankings on real-trace-derived workloads?

**RQ4.** Which observable workload characteristics are associated with scheduler
rank reversals?

**RQ5.** How many workload windows are required before a scheduler ranking
becomes statistically stable?

**RQ6.** Do important relative scheduler rankings and rank reversals observed
in simulation reproduce on a real serving engine?

## Relationship to the overlap audit

RQ2 and RQ4 sit closest to prior work (`docs/OVERLAP_LEDGER.md`, "load-dependent
rank reversal"). Their scope here is deliberately narrower and differently
framed than the existing LLM 2026 evidence: a pre-registered, multi-source,
multi-metric ranking-stability study, not a headroom/exploitability argument.

## Changelog

- 2026-08-31: Initial freeze, unmodified from the task specification.
