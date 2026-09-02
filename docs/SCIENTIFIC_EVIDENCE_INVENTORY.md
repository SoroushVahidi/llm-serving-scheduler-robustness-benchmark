# SCIENTIFIC_EVIDENCE_INVENTORY.md

Canonical scientific evidence inventory for the Phase-10/Phase-11 integrated state.

This file is the durable source of truth for what is established, what is methodology-only, and what remains pending.

## Inventory

| Component | Phase | Status | Branch/SHA | Input artifact | Output artifact | Scientific role | Manuscript role | Reusable? | Notes |
|---|---|---:|---|---|---|---|---|---|---|
| workload-source registration | 0 | DONE | `research/bootstrap-cross-workload-benchmark-20260831` @ `b7090b8` | source registry + provenance docs | registry + audit ledger | ESTABLISHED_EVIDENCE | not yet | Yes | source boundaries frozen |
| outcome-blind characterization | 1-3 | DONE | `research/workload-characterization-paper-result-20260901` @ `9435e87` | characterization raw data + descriptors | separability result | ESTABLISHED_EVIDENCE | historical | Yes | final result retained with caveats |
| leakage audit | 1 | DONE | `research/workload-characterization-paper-result-20260901` @ `9435e87` | overlap ledger + provenance | audit records | ESTABLISHED_EVIDENCE | historical | Yes | limitation explicitly recorded |
| final characterization result | 3 | DONE | `research/workload-characterization-paper-result-20260901` @ `9435e87` | characterization output | result document | ESTABLISHED_EVIDENCE | not yet | Yes | `SEPARABILITY_RESULT_CONFIRMED_WITH_CAVEATS` |
| Stage-0 window construction | 4 | DONE | `research/stage0-prerequisites-20260901` @ `23202e3` | load-calibration protocol | frozen Stage-0 windows | HISTORICAL_PILOT | historical | Yes | not a scheduler result |
| Stage-0 experiment | 5 | DONE | `research/stage0-orchestration-prelaunch-20260901` @ `de9f0a3` | stage-0 matrix | real pilot run | HISTORICAL_PILOT | historical | Yes | real 1,080-cell pilot executed |
| zero-completion repair | 5-6 | DONE | `research/stage0-zero-completion-undefined-metrics-20260901` @ `848bae3` | zero-completion metric amendment | repaired manifest | ESTABLISHED_EVIDENCE | historical | Yes | required for schema-valid repair |
| final Stage-0 NO_GO | 6 | DONE | `research/stage0-zero-completion-undefined-metrics-20260901` @ `848bae3` | Stage-0 pilot + diagnostic review | `STAGE0_NO_GO` decision | ESTABLISHED_EVIDENCE | historical | Yes | not a scheduler portability result |
| BurstGPT mechanism diagnostic | 7 | DONE | `research/stage0-burstgpt-diagnostic-20260901` @ `5508e81` | Stage-0 failure pattern | diagnostic record | ESTABLISHED_EVIDENCE | historical | Yes | root cause preserved |
| Pilot-V2 preregistration | 8 | DONE | `research/ranking-portability-pilot-v2-prereg-20260901` @ `edc4880` | protocol + policy panel + analysis plan | preregistration docs | METHODOLOGY_ONLY | not yet | Yes | no outcomes yet |
| policy panel freeze | 8 | DONE | `research/ranking-portability-pilot-v2-prereg-20260901` @ `edc4880` | policy registry | canonical policy set | METHODOLOGY_ONLY | not yet | Yes | no comparative results |
| metric-semantics freeze | 8-9 | DONE | `research/ranking-portability-telemetry-20260901` @ `d252b0b` | metric definitions + telemetry schema | telemetry implementation | METHODOLOGY_ONLY | not yet | Yes | required for calibration semantics |
| telemetry implementation | 9 | DONE | `research/ranking-portability-telemetry-20260901` @ `d252b0b` | raw telemetry schema | telemetry docs + code | METHODOLOGY_ONLY | not yet | Yes | not a benchmark result |
| Phase-10 120-window freeze | 10 | DONE | `research/lssp-integrated-phase10-20260901` @ `4a545b9` | window freeze manifest + compact index | `0d1aa06...` / `d78ec108...` | ESTABLISHED_EVIDENCE | historical | Yes | scientific freeze remains intact |
| Phase-11 FIFO calibration | 11 | DONE | `research/ranking-portability-phase11-calibration-run-20260901` @ `6e2c02f` | frozen 120-window manifest | raw FIFO manifest + region assignments | ESTABLISHED_EVIDENCE | not yet | Yes | calibration-only provenance |
| pending Phase-12 smoke | 12 | READY | `research/lssp-integrated-phase11-20260901` @ `6e2c02f` | Phase-11 calibration freeze | future smoke results | PENDING_RESULT | not yet | Yes | not started |
| pending 18,720-cell campaign | 12 | NOT_STARTED | `research/lssp-integrated-phase11-20260901` @ `6e2c02f` | smoke pass + freeze | future matrix results | PENDING_RESULT | not yet | Yes | not started |
| pending ranking analysis | 12 | NOT_STARTED | `research/lssp-integrated-phase11-20260901` @ `6e2c02f` | full campaign outcomes | ranking analysis | PENDING_RESULT | not yet | Yes | not started |
| pending sample-complexity analysis | 12 | NOT_STARTED | `research/lssp-integrated-phase11-20260901` @ `6e2c02f` | ranking outcome set | complexity analysis | PENDING_RESULT | not yet | Yes | not started |
| pending real-system validation | 12 | NOT_STARTED | `research/lssp-integrated-phase11-20260901` @ `6e2c02f` | benchmark results | validation report | PENDING_RESULT | not yet | Yes | not started |

## Classification notes

- ESTABLISHED_EVIDENCE: committed, frozen, not reinterpreted as a result beyond its intended purpose.
- METHODOLOGY_ONLY: protocol/implementation state that must be executed before any scientific claim is made.
- HISTORICAL_PILOT: earlier real experiment used to diagnose or constrain the study; preserved but not equivalent to the final benchmark.
- PENDING_RESULT: outcomes are not yet generated.

## Boundary statement

Phase 11 is calibration provenance, not a comparative scheduler result. It is included here as an established evidence artifact for protocol compliance and deterministic calibration, not as a ranking claim.
