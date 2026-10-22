# LSSP-C01 — common-model scheduler comparability

New CPU investigation from M2 draft PR#10 (`880a37e8e7c19d089be124291e288269966a9147`). Historical data, code and M1/M2 evidence remain unchanged. No manuscript claims updated. The inherited Git LFS anomaly remains unresolved.

Start with [reuse/gap matrix](REUSE_AND_GAPS.md), [prospective protocol](PROTOCOL.md), [pre-launch corrections](CHANGES_BEFORE_LAUNCH.md) and [validation](VALIDATION.md). [input_manifest.json](input_manifest.json) pins the144-cell pilot (three original200-request windows × six original load settings × four new adaptations × two KV capacities).

The common model has a shared1ms batch cost,32,768-token budget/context,64-sequence ceiling, full-context KV reservation, and no preemption. Actual residency is four/eight requests for131,072/262,144 KV tokens. All policies see the same online fields; actual/future output length and synthetic output-derived deadline/prediction never enter the scheduling view. Policies are **project adaptations**, not original/native implementations. This conservative model is useful for conformance and finite-corpus scheduling comparison, but not a validated model of GPU performance.

The core new question is whether historical ranking differences persist after execution/resource/information harmonization. The first pilot establishes the measurement path. It cannot estimate survival of36 full-corpus reversals or temporal stability. Effects against history combine contract changes and adaptations; there is no isolated causal attribution. All results, including ties/no differences, must be reported.

## Reproduce engineering checks and inputs

From repository root, launch in tmux:

```bash
tmux new-session -d -s c01-local-checks -n cpu \
  'bash research/lssp-c01/check_final.sh > research/lssp-c01/evidence/recheck.txt 2>&1'
```

The script uses `/home/soroush/lssp-c01-cache/windows.json`, a byte-identical copy of the frozen Wulver full-window artifact (paths/hashes in REUSE_AND_GAPS). To use another path:

```bash
python3 research/lssp-c01/prepare.py \
  --windows /path/to/frozen/ranking_portability_pilot_v2_windows.json \
  --inputs /path/to/pilot-inputs.json \
  --manifest /path/to/reproduced-manifest.json
```

This does not run policies. Input payload SHA256 is pinned in input_manifest.json. Source records, source-file hashes, transformed arrivals/lengths, synthesis seeds, historical policy/engine identities, metric-only deadlines and matched historical values remain available in the payload/manifest. Raw source files are not republished.

## Execution and outputs

`pilot.sbatch` uses one CPU,4GiB, general/standard, account ikoutis, **02:00:00** walltime (within the nine-hour ceiling), no GPU and no job array. Python3.12.13 is explicitly selected from the existing Wulver environment; runtime code uses only the standard library. `run.py` verifies the launch file fingerprint and input hashes before simulation, acquires an exclusive run lock, validates every completed/resumed cell independently, and writes atomic checkpoints. `events.*.part.gz` preserves incomplete attempts; completed `events.jsonl.gz` and `result.json` are keyed by a stable cell hash. An orphan final journal or invalid checkpoint stops execution; no silent rerun.

After all144 cells validate, `analyze.py` emits absolute_metrics.csv, within-condition rankings/top sets, cross-source/region rank agreement, historical comparison labels with pilot-support warning, and KV-capacity sensitivity. It uses no inferential tests. A complete JSON report cannot substitute for author review of missingness, ties, truncation, temporal/source structure and model validity.

**Job2 requires complete pilot evidence, independent revalidation and separate authorization.** Do not scale from a healthy launch alone. No native measurements, GPU work, M3, merge or manuscript revision is authorized by this branch.
