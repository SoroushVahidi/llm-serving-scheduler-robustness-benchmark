# WORKTREE_AUDIT.md

Operational audit of every local worktree's git state as of 2026-09-01.
Not a scientific document — update opportunistically when worktrees
change; no obligation to keep this byte-perfect between audits.

## Summary table

| Path | Branch | HEAD | Ahead/behind upstream | Dirty? |
|---|---|---|---|---|
| `~/repos/llm-serving-scheduler-robustness-benchmark` | `research/bootstrap-cross-workload-benchmark-20260831` | `b7090b8` | 0/0 | Yes — see below |
| `~/repos/llm-serving-scheduler-portability-telemetry` | `research/ranking-portability-telemetry-20260901` | `d252b0b` | 0/0 | No |
| `~/repos/llm-serving-scheduler-ranking-portability-windows` | `research/ranking-portability-windows-20260901` | `d252b0b` (branch not pushed) | no upstream | Yes — active work, see below |
| `~/repos/llm-serving-scheduler-robustness-ranking-portability-prereg` | `research/ranking-portability-pilot-v2-prereg-20260901` | `edc4880` | 0/0 | No |
| `~/repos/llm-serving-scheduler-robustness-stage0-burstgpt-diagnostic` | `research/stage0-burstgpt-diagnostic-20260901` | `5508e81` | 0/0 | No |
| `~/repos/llm-serving-scheduler-robustness-stage0-prelaunch` | `research/stage0-orchestration-prelaunch-20260901` | `de9f0a3` | 0/0 | No (untracked `logs/` — Wulver SLURM logs, not git-tracked by design) |
| `~/repos/llm-serving-scheduler-robustness-stage0-prereqs` | `research/stage0-prerequisites-20260901` | `23202e3` | 0/0 | No |
| `~/repos/llm-serving-scheduler-robustness-stage0-repair` | `research/stage0-zero-completion-undefined-metrics-20260901` | `848bae3` | 0/0 | Yes — one cosmetic edit, see below |
| `~/repos/llm-serving-scheduler-project-state-audit` | `research/project-state-audit-20260901` | this commit | new | Active work in progress |

## Detailed loose-change inventory

### `llm-serving-scheduler-robustness-benchmark` (the original "dirty" bootstrap worktree)

| File | State | Classification | Recommended action |
|---|---|---|---|
| `configs/workloads/source_registry.yaml` | Modified (tracked) | `DUPLICATE_OF_COMMITTED_WORK` | None needed — byte-identical (`diff` empty) to the version committed on `research/stage0-prerequisites-20260901` |
| `docs/DATA_ACQUISITION_STATUS.md` | Untracked | `DUPLICATE_OF_COMMITTED_WORK` | None needed — byte-identical to the committed version on `research/stage0-prerequisites-20260901` |
| `scripts/run_stage0_load_calibration.py` | Untracked | `DUPLICATE_OF_COMMITTED_WORK` | None needed — byte-identical to the committed version |
| `src/robustbench/calibration/stage0_load_calibration.py` | Untracked | `DUPLICATE_OF_COMMITTED_WORK` | None needed — byte-identical to the committed version |
| `tests/test_stage0_load_calibration.py` | Untracked | `DUPLICATE_OF_COMMITTED_WORK` | None needed — byte-identical to the committed version |

**Verified by direct `diff` against `git show research/stage0-prerequisites-20260901:<path>` for all five files: zero differences.** This worktree's entire dirty state is a leftover local copy of work that was already committed and pushed elsewhere — **zero risk of lost work here.** Per explicit instruction, left untouched (not staged, not committed, not discarded).

### `llm-serving-scheduler-ranking-portability-windows` (active work)

| File | State | Classification | Recommended action |
|---|---|---|---|
| `src/robustbench/ranking_portability/window_sampling.py` | Untracked | `INTENTIONAL_ACTIVE_WORK` | Commit once the real 120-window build (running on Wulver at audit time) completes and is retrieved |
| `scripts/ranking_portability/build_pilot_v2_windows.py` | Untracked | `INTENTIONAL_ACTIVE_WORK` | Same |
| `tests/test_ranking_portability_window_sampling.py` | Untracked | `INTENTIONAL_ACTIVE_WORK` | Same |

All 17 algorithm tests pass locally and on Wulver against synthetic data (no real data needed for these). The real 120-window manifest (`artifacts/manifests/ranking_portability_pilot_v2_windows.json`, gitignored per project convention — never committed) is being generated on Wulver at audit time; not yet retrieved to this worktree.

### `llm-serving-scheduler-robustness-stage0-repair`

| File | State | Classification | Recommended action |
|---|---|---|---|
| `scripts/stage0/build_stage0_zero_completion_repair_manifest.py` | Modified (tracked) | `SHOULD_IGNORE` (cosmetic) | The only diff is a hardcoded `repair_sha` default value used once to regenerate a gitignored manifest during that session; no scientific or committed-code impact. Safe to leave uncommitted indefinitely. |

### `llm-serving-scheduler-robustness-stage0-prelaunch`

Untracked `logs/` directory: real SLURM `.out`/`.err` logs from the array-1213964/merge-1213965 run, copied locally for inspection during Stage-0 verification sessions. `GENERATED_ARTIFACT`, not git-tracked by design (matches `.gitignore`'s `*.log` pattern) — preserve as operational evidence, never commit (would be large/binary-log noise).

## Unpushed commits

None — every worktree with a non-empty ahead/behind check reports `0/0`
against its upstream. The only unpushed *branch* is
`research/ranking-portability-windows-20260901` (has no upstream
configured yet — it has never been pushed).

## Lost-work risk assessment

**`LOST_WORK_RISK = NO.`**

- All committed, pushed work (9 branches, `255caca` through `d252b0b`) is
  present both locally and on `origin` — verified via `git fetch --all
  --prune` and per-branch SHA comparison.
- The only uncommitted work of substance (`research/ranking-portability-windows-20260901`'s
  algorithm code + in-progress real build) exists in a single local
  worktree and, for the real build, as a running process on Wulver — a
  single point of failure worth committing promptly once the build
  finishes, but not currently lost.
- All other uncommitted/untracked state across every worktree is either a
  verified byte-identical duplicate of already-committed work, or a
  clearly cosmetic/generated artifact — see tables above.
