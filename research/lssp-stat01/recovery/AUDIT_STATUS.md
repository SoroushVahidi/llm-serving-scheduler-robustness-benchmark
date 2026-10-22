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

Launch and initial health evidence will be recorded separately. Initial startup
must not be interpreted as completion or approval of any scientific procedure.
