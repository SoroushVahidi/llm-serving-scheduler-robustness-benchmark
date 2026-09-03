"""RQ3 synthetic-to-real transfer analysis (POST_PHASE12_RESULT_INDEPENDENT_ANALYSIS_EXTENSION).

Everything under this package answers RQ3 (docs/RESEARCH_QUESTIONS.md):
"To what extent do rankings obtained on synthetic stress workloads transfer
to rankings on independent real-trace-derived workloads?" -- a SECONDARY,
targeted analysis (docs/RQ3_SYNTHETIC_TO_REAL_PROTOCOL_20260903.md), not a
recreation of the original, much larger, never-executed RQ3 roadmap.

This was not part of the sealed Phase-12 analysis pipeline
(`research/lssp-phase12-analysis-prefreeze-20260902`); it is a new,
independent extension built on top of that sealed code without modifying
it. It reuses, unchanged: `robustbench.workloads.synthetic` (generator),
`robustbench.calibration.stage0_load_calibration` (FIFO load calibration),
`robustbench.ranking_portability.execute_cell` (cell execution), and
`robustbench.ranking_portability.analysis.stats` (ranking comparison
primitives) -- see the protocol doc for why each is safe to reuse as-is.
"""
