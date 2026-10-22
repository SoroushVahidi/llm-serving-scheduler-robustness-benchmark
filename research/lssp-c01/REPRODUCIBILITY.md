# Exact reproduction and launch records

## Authority and preserved inputs

Base M2:880a37e8e7c19d089be124291e288269966a9147. Protocol freeze8dd2c37; execution source **9aed0206de66886e9feb0b003b59f0b7dfea68c9**. `launch.json` pins every runtime source, contract, test and manifest file. Subsequent commits add evidence/reporting only; no scientific outcomes justify implementation changes.

Full-window local cache `/home/soroush/lssp-c01-cache/windows.json` (52,145,952 bytes). Exact hash in input_manifest.json and frozen_input_inspection.txt. Input-copy session/PID/exit in VALIDATION.md. Pilot payload `/home/soroush/lssp-c01-cache/pilot-inputs.json`, SHA256 `56b216fdfedf34ca8a959cb764c9896cf7f6351319259cba13dc8fb98df05f1c`. Do not replace the frozen windows with a current public-trace download. No data regeneration or historical rerun is needed.

Local checks: `bash research/lssp-c01/check_final.sh`, run in tmux as recorded. Local runtime Python3.12 environment with NumPy2.3.5 and pytest9.0.3; NumPy is needed only for unchanged historical input synthesis. Wulver execution uses Python3.12.13 standard library; pytest9.1.1 is used for engineering validation. No new environment or package installation.

## Remote deployment and engineering validation

Dedicated root:
`/project/ikoutis/sv96/github/llm-serving-scheduler-lssp-c01-3c8e2d6`

Its `code/` contains the C01 files pinned in launch.json; `inputs/pilot-inputs.json` is copied unchanged; `launch.json` is copied unchanged. Transfer used `rsync -a` from `/home/soroush/lssp-c01-cache/stage/` into this new root. Existing remote projects are not edited. Remote engineering script is preserved at `evidence/validate_remote.sh`; tmux `lssp-c01-remote-validation:cpu`, pane PID3042322. It tests synthetic fixtures only and verifies all code/input fingerprints; stdout/exit/PID copied into evidence/remote-validation.*.

Run identity (SHA256 of canonical launch.json):
`30f3af3717d536cb46d9f8cceb5c35535719a70ccb0fbfb1032ccee0176a0834`

Run ID: `c01-30f3af3717d536cb`.

Scientific output root:
`/project/ikoutis/sv96/github/llm-serving-scheduler-lssp-c01-3c8e2d6/runs/c01-30f3af3717d536cb`

Expected files: `checkpoint.json`, `launch.json`, `environment.json`, `cells/<cell-key-sha256-prefix>/events.jsonl.gz`, `cells/<prefix>/result.json`, incomplete `events.<attempt>.part.gz`, `failure-<pid>.json` on failure, `slurm.exit`, `started_utc.txt`, `finished_utc.txt`, and descriptive summaries/complete.json only after all144 cells validate. Never infer completion from a log file's existence. Each result records exact request hash, journal hash, identity and independent validation.

## One authorized submission

Submission is performed once after local+remote gates pass and queue/output duplicate checks. No array, GPU request, dependency, automatic retry or follow-up job. Exact sbatch command, job response, Slurm state and initial observation are in LAUNCH_REPORT.md and evidence/startup files. If that report does not record an accepted job, this document alone is not evidence of execution.

A manual resume after an infrastructure interruption requires establishing the cause and explicit author direction. Reuse the exact launch/input fingerprints and output root: valid completed cells are independently revalidated and skipped. Invalid cells stop the run; do not delete evidence to force a restart. Orphan final journals require investigation, not automatic replacement.

## Review after completion (not performed during startup monitoring)

Use Slurm accounting and slurm.exit, then independently revalidate every expected cell using `run.checked_cell` with its frozen condition/profile/identity before interpreting summaries. Completeness means144 valid cells with no unhandled failure, not144 filenames. Inspect unfinished fractions, conditional support, exact/tolerance ties and resource occupancy. The analyzer's full36 persistence and temporal-stability verdicts must remain NOT_EVALUABLE for this pilot. Author review and new execution authorization precede Job2.

## Preservation

All tracked changes are under `research/lssp-c01/`. The apparent modification to historical consolidated.json is the inherited Git LFS anomaly; its raw SHA256 still matches73adf7d97f06985ec8f8e1c2f794fd43178433eb198e1c00705e817f4bde9c26. It is never staged. Raw failure-log whitespace is retained deliberately. No frozen evidence, historical PR, manuscript or dataset publication was modified.
