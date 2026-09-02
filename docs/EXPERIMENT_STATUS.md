# EXPERIMENT_STATUS.md

Permanent experiment status table for the integrated scientific state.

Status categories: `DONE`, `READY`, `NOT_STARTED`, `RUNNING`, `BLOCKED`, `HISTORICAL`, `SUPERSEDED`.

| Experiment | Phase | Status | Expected cells | Actual cells | Branch | Result | Next dependency |
|---|---|---|---:|---:|---|---|---|
| Stage-0 pilot | 0-6 | HISTORICAL | 1080 | 1080 final repaired matrix | `research/stage0-zero-completion-undefined-metrics-20260901` | `STAGE0_NO_GO` | Phase-10 window freeze |
| Phase-10 window freeze | 10 | DONE | 120 windows | 120 windows | `research/lssp-integrated-phase10-20260901` | frozen identity preserved | Phase-11 FIFO calibration |
| Phase-11 FIFO calibration | 11 | DONE | 720 cells | 720 cells | `research/ranking-portability-phase11-calibration-run-20260901` | `PHASE11_CALIBRATION_VALID` | Phase-12 smoke |
| Phase-12 smoke | 12 | READY | engineering smoke | 0 | `research/lssp-integrated-phase11-20260901` | not started | prelaunch freeze + campaign |
| Pilot-V2 main campaign | 12 | NOT_STARTED | 18,720 scheduler cells | 0 | `research/lssp-integrated-phase11-20260901` | none | ranking analysis |
| ranking analysis | 12 | NOT_STARTED | full ranking matrix | 0 | `research/lssp-integrated-phase11-20260901` | none | real-system validation |
| sample-complexity analysis | 12 | NOT_STARTED | analysis set | 0 | `research/lssp-integrated-phase11-20260901` | none | further benchmark release |
| real-system validation | 12 | NOT_STARTED | external validation set | 0 | `research/lssp-integrated-phase11-20260901` | none | manuscript release |

## Notes

- Historical `stage0_pilot` job `1213964` is recorded as historical Stage-0 work and must not be confused with the later Pilot-V2 smoke or full campaign.
- The Phase-11 run is a deterministic calibration matrix; it is not a comparative scheduler panel and it is not a result-generating campaign.
