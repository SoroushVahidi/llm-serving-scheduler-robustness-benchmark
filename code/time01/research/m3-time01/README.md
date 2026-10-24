# M3-TIME01 isolated experiment

Read PROTOCOL.md. No scientific outcomes were examined while selecting the model
or windows. The frozen_c01 files are unmodified C01 sources; timed_engine and
timed_validator contain the duration extension. support.verify_policy separately
checks unchanged policy intent. Analysis never modifies evidence.

Local/remote test command (from repository/code root):

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=research/m3-time01:research/m3-time01/frozen_c01 python -m pytest -q research/m3-time01
```

Preparation, after committing this directory:

```bash
python research/m3-time01/prepare.py C01_EVIDENCE NEW_PAYLOAD --remote-root REMOTE_ROOT
python research/m3-time01/regression.py NEW_PAYLOAD NEW_REGRESSION_REPORT.json
python research/m3-time01/campaign.py NEW_PAYLOAD --preflight
```

Preparation only selects existing inputs and copies hash-verified saved results.
Regression performs four fixed compatibility tests; it creates no scientific
variable-timing outcomes. Freeze a separate execution.json binding manifest SHA,
code SHA, passing validation reports, exact missing384 cells and environment.
Submission record supplies actual timestamp/job ID and hashes the execution.json.
A single SLURM submission uses experiment.sbatch with TIME01_ROOT; write logs into
REMOTE_ROOT/logs. Do not submit without checking live jobs and acquiring a durable
submission lock. No implicit restart or overwrite is supported. For interrupted
work, investigate compatibility and explicitly design missing-cell recovery later.

After completion, inspect sacct, slurm.exit, complete.json, all stderr and expected
384 cell identities. Then run the frozen analyzer in a persistent tmux session or
SLURM job if it may exceed3min (this is analysis of saved data, no simulations):

```bash
python code/research/m3-time01/analyze_results.py REMOTE_ROOT NEW_ANALYSIS_DIR
```

It revalidates every event, timing, policy intent, terminal, metric and telemetry,
then writes cells, paired differences, source means, rankings, policy comparisons,
strict10% reversal counts, duration/composition/urgency summaries and reliability.
Review censoring and denominators before interpreting conditional latency. Verify
selected timing rows by hand from P,D as an additional human check; all rows already
receive an independent code reconstruction. Compare fixed-mode regression output
to saved baseline SHA identities. Source-mean p95 is mean-window p95. Describe24
selected windows, never384 independent replicates. Keep adverse or null findings.
Only after review decide whether this one declared model supports persistence or
reveals sensitivity. It reduces the untested-composition limitation but cannot
establish hardware transfer, universal timing robustness or calibrated mixed-batch
performance. Do not update the manuscript, merge or publicly release without a
separate user request.
