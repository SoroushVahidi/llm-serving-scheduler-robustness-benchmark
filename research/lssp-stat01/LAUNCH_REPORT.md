# STAT01 launch record

**RUNNING_HEALTHY — accepted and queued at the single startup observation.** This status describes submission health, not verified runtime execution or completed scientific results. The campaign was launched; completed M2 arithmetic/sensitivities were reused without rerunning them. No equivalent known-truth calibration was located.

## Identity and submission

* Draft PR: https://github.com/SoroushVahidi/llm-serving-scheduler-robustness-benchmark/pull/12
* Branch: research/lssp-stat01-calibration; base M2 880a37e8e7c19d089be124291e288269966a9147.
* Execution code commit: 454168a005240341dc5a5ae88ac32c4b130f6bc5. The final PR commit additionally records this launch evidence.
* Prospective protocol commit: edbcfdfce5649a0c53502f9cc67da6b91e02c3d8.
* Canonical launch SHA-256: f97f91abe5da0bf5566edcf7f0877e4df226cbea4b4b3966c467a33a970b5700.
* Unique run ID: stat01-f97f91abe5da0bf5.
* Slurm job: **1438961**, submitted 2026-10-22T04:28:27Z (Slurm displays 00:28:27 local time).
* Requested allocation: general partition, standard QOS, ikoutis account, one node/task, 4 CPUs, 8 GiB, zero GPUs, maximum 09:00:00, automatic requeue disabled. No node was allocated at the snapshot.
* Wulver root: `/project/ikoutis/sv96/github/llm-serving-scheduler-lssp-stat01-454168a00524` (ROOT below).

See submit-once.sh for the exact sbatch command, duplicate guard, hash checks, lock and single startup snapshot. Submission ran in local TMUX `lssp-stat01-submit:startup`, pane PID 547045, shell PID 547046; wrapper exit 0. Exact local wrapper is launch-local.sh; evidence/submission-local.* records its PID/log/exit. The remote wrapper PID is evidence/submission-remote.pid. There was one submission and no relaunch.

## Persistent evidence paths

* Deployment manifest: `ROOT/launch.json`; identical tracked copy at research/lssp-stat01/launch.json.
* Frozen code/reference copies: `ROOT/code/` and `ROOT/reference/`.
* Slurm stdout: `ROOT/logs/stat01-f97f91abe5da0bf5-1438961.out`.
* Slurm stderr: `ROOT/logs/stat01-f97f91abe5da0bf5-1438961.err`.
* Raw outputs: `ROOT/runs/stat01-f97f91abe5da0bf5/batches/scenario-SS/rep-RRRRRR/{raw.npz,studies.json.gz,integrity.json}`.
* Checkpoint: `ROOT/runs/stat01-f97f91abe5da0bf5/checkpoint.json`.
* Scheduled statistical summaries: `ROOT/runs/stat01-f97f91abe5da0bf5/look-sSS-nNNNNN.json`.
* Runtime environment/PID/exit/completion: `ROOT/runs/stat01-f97f91abe5da0bf5/{environment-PID.json,wrapper.pid,slurm.exit,completion.json}`.
* Remote validation: `ROOT/logs/validation.{txt,pid,exit}`; tracked copies in evidence/wulver-validation.*.
* Submission and frozen startup observation: `ROOT/logs/{sbatch-response.txt,submitted_utc.txt,submitted-job-id.txt,submission-wrapper.pid,startup-health.txt}`; tracked relevant copies in evidence/.

Output paths are reserved, not claims that runtime artifacts already exist.

## Single startup observation

At 2026-10-22T04:28:37Z, **10 seconds** after submission, squeue/scontrol showed PENDING, Reason=None, eligible immediately, no dependency, no restart and the requested CPU/memory/time limits. Slurm accepted the job; no immediate rejection/allocation/input error was reported. Since the job was queued, runtime environment/input execution was not observable. Stdout, stderr, environment record and checkpoint did not yet exist; no failure artifact existed. Logging paths were registered with Slurm and checkpoint/resume functionality had passed engineering tests. Monitoring then stopped; no later state or outcome was queried.

## Scientific interpretation and next review

The new contribution is repeated-study calibration against explicit population truth, rather than further sensitivity arithmetic on selected historical observations. The protocol specifies 18 scenarios and eight methods, sign versus >10% practical alternatives, complete families, independent versus correlated windows, ties, missingness, finite resampling resolution and simultaneous Monte Carlo precision accounting.

Validation: 63 tests pass both locally and in the pinned Wulver environment. See VALIDATION.md for scope, independent checks and the retained pre-launch numerical correction. This is adequate to launch the specified synthetic investigation. It is not evidence that historical FDR/coverage is acceptable.

Execution health: submission accepted; runtime unobserved at return. Evidence validity: pending completed-batch validation and assumption-specific analysis. Publication readiness: not established; manuscript claims remain unchanged. Unknown real-workload dependence, selective missingness, provider sampling and native comparability are not repaired by synthetic calibration. Oracle covariance is a benchmark, not a deployable estimator. A finite scenario suite cannot establish universal validity.

No second job is authorized automatically. A later user-requested review should inspect completion, validate all output and assess precision gaps before recommending any additional computation. C01 was not queried or modified.
