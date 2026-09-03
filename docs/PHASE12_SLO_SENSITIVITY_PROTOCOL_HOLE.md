# PHASE12_SLO_SENSITIVITY_PROTOCOL_HOLE.md

Recorded result-blindly (no Phase-12 comparative output of any kind was
read to produce this document; the currently running admitted Phase-12
statistical analysis was left untouched).

## Finding

`SLO_DEFINITION_SENSITIVITY` (`analysis/contract.py`,
`analysis/robustness.py`) was planned as a robustness/sensitivity check
requiring **new simulator execution** — the alternative SLO-synthesis
rule changes request labels at synthesis time, which the frozen
Phase-12 campaign's existing cell columns cannot reconstruct after the
fact. It is correctly flagged `NEW_EXECUTION_REQUIRED_FOR_THIS_SENSITIVITY
= YES` and correctly *not* implemented as a row filter or metric
recomputation.

However, an exhaustive search across three independent checkouts of this
repository (the local `research/lssp-phase12-analysis-prefreeze-*`
worktree, the Wulver `research/lssp-phase12-campaign-freeze-*` checkout
that ran the admitted campaign, and the Wulver
`llm-serving-scheduler-lssp-phase12-provenance-repair` checkout), full
tracked-file search, and full git history (`git log --all -p -S`) found
**no alternative SLO-synthesis rule was ever actually frozen**. Every
document that references "the alternative SLO-synthesis rule"
(`docs/DATA_FIELD_PROVENANCE.md` item 3, `docs/EXPERIMENT_CAMPAIGN_PLAN.md`
Stage 5, `docs/RANKING_PORTABILITY_ANALYSIS_PLAN.md`,
`analysis/robustness.py`) cross-references the others as the place it is
defined — a closed loop that never terminates in an actual formula,
multiplier, or distribution. The only SLO-synthesis rule that exists
anywhere in the repository, at any commit, is `stage0_synthesis_v1`
(`src/robustbench/workloads/external/benchmark_synthesis.py`,
`SLO_MULTIPLIER = 20.0`) — the **primary** rule already used to produce
the admitted 18,720-cell campaign, not an alternative.

## Consequences

- No alternative rule was invented after Phase-12 execution.
- No SLO-sensitivity campaign has been launched.
- `SLO_DEFINITION_SENSITIVITY` must **not** be described as preregistered
  evidence in the manuscript or claim boundaries.
- Any future SLO-sensitivity check must be explicitly labeled a
  **post-campaign robustness extension**, with its own freeze/manifest
  process, unless a genuinely prior external protocol specifying the
  alternative rule is located (none was found as of this document).
- No replacement rule was selected in this task, and none should be
  selected without an explicit decision from the project owner made
  before either party inspects real Phase-12 comparative output for the
  affected pairs — see `docs/CLAIM_BOUNDARIES.md` for why post-hoc
  threshold selection is disallowed.

## Status

`PHASE12_SLO_SENSITIVITY_STATUS = NEEDS_RESULT_BLIND_PROTOCOL_RESOLUTION`
(unchanged from the prior determination in this task sequence; recorded
here as the durable, in-repository record of the finding).
