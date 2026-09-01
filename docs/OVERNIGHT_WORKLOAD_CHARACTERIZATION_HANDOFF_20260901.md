# OVERNIGHT_WORKLOAD_CHARACTERIZATION_HANDOFF_20260901.md

Overnight handoff for the outcome-blind workload-distribution-characterization
experiment, launched 2026-09-01. See
`docs/WORKLOAD_DISTRIBUTION_CHARACTERIZATION_PROTOCOL.md` for the full frozen
protocol. This is a SECOND, independent experiment from the frozen Stage-0
scheduler-discriminability pipeline; it does not modify, run, or depend on
any Stage-0 code path.

## Repository / launch state

- Repo: `SoroushVahidi/llm-serving-scheduler-robustness-benchmark`
- Branch: `research/bootstrap-cross-workload-benchmark-20260831`
- Launch SHA (both local and Wulver checkouts, fast-forwarded, clean):
  `862e8f5f789cce329f84d535c54cfc4b747e8d7e`
- `main` SHA (unchanged throughout): `6a8277993e4ef19b10e3fa53baf476d0d0d490f0`
- Not merged to `main`.

**Note on a concurrent, separate, uncommitted edit found in the local
working tree at session start:** `configs/workloads/source_registry.yaml`
had an uncommitted edit (adding checksums/`acquired: true` for
burstgpt/azure_llm_2024/bailian_qwen) and four other uncommitted/untracked
files (`docs/DATA_ACQUISITION_STATUS.md`,
`scripts/run_stage0_load_calibration.py`,
`src/robustbench/calibration/stage0_load_calibration.py`,
`tests/test_stage0_load_calibration.py`) related to Stage-0 load
calibration -- this appears to be separate, legitimate in-progress work on
the same branch, not created by this session. **It was deliberately left
exactly as found: uncommitted, unpushed, untouched.** This session's commits
touch only the tracelab entry of `source_registry.yaml` (a cleanly separable
diff hunk) plus entirely new files. Verify with `git status` before doing
anything else tomorrow -- that other work is still sitting there waiting for
its own review/commit, this session did not resolve it.

## Sources / checksums (independently re-verified this session, 2026-09-01)

| Source | Wulver path | SHA-256 |
|---|---|---|
| BurstGPT | `/project/ikoutis/sv96/llmserveopt-data/datasets/burstgpt_v2/raw/BurstGPT_without_fails_2.csv` | `56193aa9b2bb26128ded43d2d29a960df6bf5af062bcfc9b005f3fcaa4e6e501` |
| Azure LLM 2024 (conv) | `/project/ikoutis/sv96/llmserveopt-data/datasets/azure_llm_2024/raw/AzureLLMInferenceTrace_conv_2024.csv` | `a0cc9b969a9bbf0fd811802cbf4323edd3a209ace791e3799ad4f9207f213941` |
| Bailian/Qwen | `/project/ikoutis/sv96/llmserveopt-data/datasets/bailian_qwen/raw/qwen_traceB_blksz_16.jsonl` | `68e3f98e2d601d60d0abf4b89bc8a3654372abab7b1cde6373a13d0054379d59` |
| TraceLab | `/project/ikoutis/sv96/llmserveopt-data/tracelab_staging_20260722T192050Z/raw/syfi_coding_trace.jsonl.gz` | `9d265eae69a31cae203848bea936f018148eed7ca8bf56050c5abe96da0b4e6b` |

TraceLab uses a NEW adapter (`src/robustbench/workloads/external/adapters/tracelab.py`)
re-derived directly from this raw release asset -- not the existing HF
`tracelab_scheduler_ood_policy_sweep` config (see
`docs/TRACELAB_PROVENANCE_RESOLUTION.md`).

Excluded this run: Azure 2023 (optional per charter), ServeGen (generator,
not a fixed trace), Mooncake (`INTERNAL_ONLY`).

## Prelaunch freeze

`artifacts/manifests/workload_characterization_prelaunch.json` (gitignored
per repo convention, regenerable via
`scripts/characterization/write_prelaunch_manifest.py` -- not committed,
same as Stage-0's own `stage0_windows.json`):

- `repo_sha`: `862e8f5f789cce329f84d535c54cfc4b747e8d7e`
- `window_sampling_protocol_hash`: `9041e6b5ea0ab6f309c1aa9013f1d66acde11d8551b9211f8e3726bdeda4f8c0`
- `feature_schema_hash`: `60f7b9e7d1e9c1eec6a77569f69b740fd9a545aea3e657a1969b72ea7911e4ad`
- `statistical_protocol_hash`: `d0ad6d2d5fea44b30ca8b346cb7589c6d91249a39c473ec8a3c32f376c0955f3`

## Tests / smoke checks (all before launch)

- Local suite: 68 passed (`.venv`).
- Wulver suite: 65 passed (`.venv312`; the 3-fewer are the other,
  intentionally-untouched Stage-0 load-calibration tests, whose source files
  aren't pushed since they're someone else's uncommitted work -- not a
  failure of anything this session added).
- Real-data smoke test (section 9's "do not proceed on fixtures alone"):
  ran the actual `BurstGPTAdapter`/`BailianAdapter` against the first 2,000
  real rows of each real file on Wulver, computed
  `WorkloadCharacterizationDescriptor` on 3 real 200-request windows per
  source -- zero `validate()` problems, all values in sane ranges
  (arrival rates, prompt/output means, Gini in [0,1], burstiness in [-1,1]).

## Overnight job

- **SLURM** (Wulver, `sv96`, account `ikoutis`, partition `general`, QOS `standard`).
- Build array job: **1212784** (`--array=0-3`, one task per source:
  0=burstgpt, 1=azure_llm_2024, 2=bailian_qwen, 3=tracelab),
  `--time=09:00:00`, `--cpus-per-task=2`, `--mem=8G`.
- Merge/analysis job: **1212785**, submitted with
  `--dependency=afterok:1212784`, `--time=01:00:00`, `--cpus-per-task=4`, `--mem=16G`.
  Does **not** auto-launch any further experiment.
- Logs: `logs/workload_characterization/build_1212784_{0..3}.{out,err}`,
  `logs/workload_characterization/merge_1212785.{out,err}`
  (all under `/project/ikoutis/sv96/github/llm-serving-scheduler-robustness-benchmark/`).
- Fragments (intermediate, per-source): `artifacts/manifests/characterization_fragments/`.
- Final results directory: `results/workload_distribution_characterization_v1/`.

## Three-minute health check result

Polled every 30s for ~3 minutes after submission (16:23:40 - 16:26:40 UTC).
All 4 array tasks started immediately (`n0107`), no errors in any `.err`
log at any poll. Two of four sources completed fully within the window:

- `bailian_qwen`: DONE at 16:24:17Z, all 3 window sizes at the full 100
  windows/size (300 descriptor rows total).
- `tracelab`: DONE at 16:25:07Z, same (300 descriptor rows).
- `burstgpt`: reached window_size=500 selection by the end of the health
  check (on track to finish shortly after).
- `azure_llm_2024`: still on the window_size=100 counting pass at the end
  of the health check (expected -- 27.3M rows, the largest file by far;
  a 2M-row throughput benchmark earlier in this session measured ~30K
  rows/sec on the login node, i.e. ~15 min for one full-file pass and up to
  6 passes total across the 3 window sizes -- comfortably within the 9h
  budget).

**Verdict: HEALTHY_AND_LEFT_RUNNING.**

## Tomorrow: how to check on it

```bash
ssh wulver
cd /project/ikoutis/sv96/github/llm-serving-scheduler-robustness-benchmark

# 1. Completion
squeue -u $USER                         # should be empty if both finished
sacct -j 1212784,1212785 --format=JobID,JobName,State,ExitCode,Elapsed

# 2. Integrity validation
cat results/workload_distribution_characterization_v1/integrity_report.json | python3 -m json.tool
cat results/workload_distribution_characterization_v1/provenance.json | python3 -m json.tool
# per-source fragment integrity (built even if the merge job hasn't run yet):
for f in artifacts/manifests/characterization_fragments/integrity_*.json; do echo "== $f =="; cat "$f"; done

# 3. Cross-source distance results
column -s, -t results/workload_distribution_characterization_v1/source_pair_distances_multivariate.csv | less -S
column -s, -t results/workload_distribution_characterization_v1/source_pair_distances.csv | less -S   # univariate, per feature per pair
cat results/workload_distribution_characterization_v1/cross_vs_within_summary.json | python3 -m json.tool
cat results/workload_distribution_characterization_v1/source_classifier_metrics.json | python3 -m json.tool

# 4. Temporal-drift results
column -s, -t results/workload_distribution_characterization_v1/temporal_drift_distances.csv | less -S

# 5. Window-size sensitivity (section 6F / RQ5)
column -s, -t results/workload_distribution_characterization_v1/window_size_sensitivity.csv | less -S

# 6. Whether the 4 sources are genuinely diverse enough for the new paper
#    -- read, in order:
#    a. cross_vs_within_summary.json's rank_biserial_effect_size and
#       mann_whitney_pvalue: is source identity's distance systematically
#       LARGER than ordinary within-source temporal drift? (RQ3)
#    b. source_classifier_metrics.json's balanced_accuracy/macro_f1: are
#       sources distinguishable from descriptors alone? (framing: workload
#       separability only, never a scheduler selector -- CLAIM_BOUNDARIES.md)
#    c. feature_importance.csv: which descriptors drive separability? (RQ4)
#    d. window_size_sensitivity.csv: do (a)/(b) hold at 100/200/500
#       requests/window, or only one granularity? (RQ5)
#    e. source_pair_distances.csv + source_pair_distances_multivariate.csv:
#       per-pair, per-feature effect sizes (RQ1) and which source pairs are
#       closest/furthest.
```

If either job failed: check the `.err` log named above first; this was not
observed during the health-check window but the array's 9h walltime and
Azure's long single-file passes mean a late failure (e.g. an unexpected
malformed row far into the file) cannot be ruled out. Re-running a single
failed array index is `sbatch --array=<index> scripts/slurm/workload_characterization_build.sbatch`
(then re-submit the merge job with the correct `--dependency`) -- do not
change the frozen sampling parameters (`SEED`/`OFFSET_VALID_ROWS`/window
sizes in `scripts/characterization/build_and_describe_windows.py`) when
retrying; only fix an actual bug.
