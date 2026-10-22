# LSSP-C01 launch report — RUNNING_HEALTHY

State observed **2026-10-22T03:50:00Z**. One startup observation; monitoring interval **10 seconds** after submission. No subsequent completion polling or scientific result analysis was performed. This is execution health, not proof of a completed/valid scientific experiment.

| Item | Recorded value |
|---|---|
| Draft PR | https://github.com/SoroushVahidi/llm-serving-scheduler-robustness-benchmark/pull/11 |
| Branch / base | `research/lssp-c01-common-model` / M2 `880a37e8e7c19d089be124291e288269966a9147` |
| Executed source commit | `9aed0206de66886e9feb0b003b59f0b7dfea68c9` (later commits add evidence/reporting only) |
| Slurm job | **1438638**, RUNNING on n0009 at startup observation |
| Submitted | 2026-10-22T03:49:50Z (cluster displays2026-10-21T23:49:50 local) |
| Resources | general / standard / ikoutis; one node, one task, one CPU,4GiB, zero GPUs |
| Maximum walltime | **02:00:00**; below authorized09:00:00 ceiling |
| Execution process | PID899713 on n0009 |
| Submission wrapper | local tmux `lssp-c01-submit:startup`, pane PID541491; shell PID in evidence/launch-wrapper.pid, wrapper exit0 |
| Run identity | `30f3af3717d536cb46d9f8cceb5c35535719a70ccb0fbfb1032ccee0176a0834` |
| Scientific status | Prospective144-cell CPU conformance pilot; incomplete at observation |

## Exact Wulver paths

Deployment root:
`/project/ikoutis/sv96/github/llm-serving-scheduler-lssp-c01-3c8e2d6`

The directory suffix reflects the initial staging commit; **launch.json pins the final9aed020 execution code**, verified remotely after the control-label correction.

* stdout: `/project/ikoutis/sv96/github/llm-serving-scheduler-lssp-c01-3c8e2d6/logs/c01-30f3af3717d536cb-1438638.out`
* stderr: `/project/ikoutis/sv96/github/llm-serving-scheduler-lssp-c01-3c8e2d6/logs/c01-30f3af3717d536cb-1438638.err`
* checkpoint: `/project/ikoutis/sv96/github/llm-serving-scheduler-lssp-c01-3c8e2d6/runs/c01-30f3af3717d536cb/checkpoint.json`
* raw/output root: `/project/ikoutis/sv96/github/llm-serving-scheduler-lssp-c01-3c8e2d6/runs/c01-30f3af3717d536cb/`
* inputs: `/project/ikoutis/sv96/github/llm-serving-scheduler-lssp-c01-3c8e2d6/inputs/pilot-inputs.json`
* frozen launch: `/project/ikoutis/sv96/github/llm-serving-scheduler-lssp-c01-3c8e2d6/launch.json`
* staged validation log: `/project/ikoutis/sv96/github/llm-serving-scheduler-lssp-c01-3c8e2d6/validation.txt`
* submission record: `/project/ikoutis/sv96/github/llm-serving-scheduler-lssp-c01-3c8e2d6/submission.json`

`cells/<cell-key-hash>/events.jsonl.gz` and result.json preserve validated per-cell raw journals and terminal/request metrics. Incomplete attempts retain `.part.gz`; final exit and completion markers are only expected after actual termination. No completion claim is made here.

## Startup evidence

Slurm accepted the job and reported RUNNING, Reason=None, one allocated CPU,4G and no GPU TRES. The pinned Python process wrote STARTED and multiple CELL_VALIDATED events; the atomic checkpoint listed newly validated cells. stdout and stderr existed; the captured stderr was empty. Thus allocation, import/dependency, input identity and early event-validation paths were observably working. The captured log/checkpoint prefixes are intentionally bounded; they are not a complete result archive. Full runtime logs remain at the paths above.

`evidence/startup-scontrol.txt`, `startup-squeue.txt`, `startup-observation.txt`, `startup-monitoring-seconds.txt` and `submission.json` preserve the observation. `submit_once.sh` contains the exact command, queue/output duplicate guards and a persistent one-shot submission lock. No job array or second submission. The Slurm snapshot reports the site's default Requeue=1; the launcher/runner themselves do not retry failed submissions or invalid cells. No requeue had occurred (Restarts=0).

## Reuse, contribution and verdicts

Reused: exact historical120-window corpus, original synthesis seeds/load factors and all historical outcomes/labels. Prior policy-separation/shared-state and native-bridge experiments were inspected, found non-equivalent, and not rerun. Matrix and identities in REUSE_AND_GAPS.md.

New: four explicitly named adaptations under the same executor, token budget, KV rules, observable information and metrics; paired KV-capacity sensitivity. Stable controls are58 historical STABLE_NO_SIGN_CHANGE records, with14 microscopic changes and36 historically supported records separately retained. The pilot selects one200-request window/source and all six historical factors; it does not estimate full-corpus reversal survival.

Contract: CM-0.1, fixed1ms batches,32,768 token budget/context,64-sequence ceiling, conservative full-context reservation (four/eight residents), no preemption, no output oracle. Policies: whole_fcfs_c01, chunked_fcfs_c01, decode_first_c01, slo_gated_c01. See PROTOCOL.md for complete definitions and exclusions.

Validation:63 local tests passed;42 staged Wulver tests passed; independent referee, corruption rejection, deterministic replay/resume and exact input/source checks passed. No frozen-workload outcome used to tune the implementation.

**Execution health:** healthy at the bounded observation. **Evidence validity:** pending complete144-cell validation and result review. **Scientific readiness:** GO only for this pilot; NOT established for full original/native-policy or historical reversal claims. **Publication readiness:** NOT established. **Job2:** must not proceed until pilot completion/revalidation, scientific review and separate authorization. No manuscript, M3, GPU campaign, historical PR, merge or dataset publication was performed.
