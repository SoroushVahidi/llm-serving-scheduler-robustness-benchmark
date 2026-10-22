# Persistent integrity audit

This is an audit of saved data, not a recovery experiment. No Slurm submission or
automatic recovery occurs. The scientific-definition decision in DIAGNOSIS.md is
still required regardless of the audit outcome.

Separate Wulver deployment:
`/project/ikoutis/sv96/github/llm-serving-scheduler-lssp-stat01-diagnosis-20261022/`

Session name: `stat01-integrity-20261022`.

Command inside the persistent tmux session:

```bash
STAT01_DIAG_ROOT=/project/ikoutis/sv96/github/llm-serving-scheduler-lssp-stat01-diagnosis-20261022 \
bash /project/ikoutis/sv96/github/llm-serving-scheduler-lssp-stat01-diagnosis-20261022/tools/run-audit.sh
```

It runs the pinned Python with BLAS threads one, two bounded audit threads,
niceness 10 and a two-hour timeout. Original files are read-only inputs.
Logs and results, relative to the separate deployment:

- `evidence/full-audit/console.log`
- `evidence/full-audit/progress.json`
- `evidence/full-audit/batches.jsonl`
- `evidence/full-audit/summary.json` (only after audit completion)
- `evidence/full-audit/audit.exit`
- `evidence/full-audit/wrapper.pid`

Local and pinned-Wulver tests: **70 passed**, including all 63 original focused
tests and seven diagnostic regression tests. See `evidence/tests-local.txt` and
`evidence/tests-pinned.txt`. No production/reference code was changed.

Status at the single startup inspection: **RUNNING_HEALTHY**.
Launched 2026-10-22 13:45:30 UTC. At 13:46:20.261824 UTC, the tmux session was
alive, audit PID was `808734`, progress was current, and **307/4,491 batches
(7,675 studies)** had passed with zero recorded failed batches. No exit/failure
record existed. See `evidence/audit-startup.json` for the captured snapshot,
tool hashes, source snapshot and log tail. Monitoring ended after this check,
within two minutes; final audit counts are not yet available in this report.

Audit implementation/evidence commit: `e27d4fc` (the commit preceding this
startup-record update). Initial startup must not be interpreted as completion
or approval of any scientific procedure. No recovery Slurm ID exists.
