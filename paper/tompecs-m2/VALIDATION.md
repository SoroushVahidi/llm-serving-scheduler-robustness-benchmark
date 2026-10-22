# M2 reproduction and validation

Execution was local, CPU-only, without GitHub Actions, paid CI, GPU work, Slurm/Wulver submissions, new serving/simulation measurements, merges or publication. All scientific writes are under `paper/tompecs-m2/`. The branch starts at verified PR #9 commit `366752a76f86dec30190f3e7767124f684378de4`.

## Completed checks

* Independent numerical reproduction: 198 source-rank intervals; 72 primary reversal intervals/tails; 6,890 cross-metric difference intervals/tails; six cross-metric rank intervals; 66 Friedman records; 990 cross-metric point/ID summaries; all match.
* Independent primary classification, point difference and margin reconstruction: 990/990.
* Focused inherited CPU tests: 32 passed, zero failures/skips; expected SciPy constant-input warning.
* Frozen dataset release validator: valid, `problems=[]`, hashes/schema/deterministic-pair checks pass. No simulation run.
* Full document/preservation validator: 14 passed, zero failures; all 571 inherited tracked files unchanged, including 11 hydrated LFS payloads verified by pinned size/hash.
* Clean ACM builds: **27 manuscript pages, 28 acmsmall pages**, all pages counted. No undefined references/citations, duplicate labels, overfull boxes or TeX errors. The inherited ACM 2.20 class is byte-identical and has no typography override. The acmsmall final page contains reference continuation; it is included in 28.
* Visual review: complete 27/28-page layout contact sheets; full-size manuscript pages 14 (new absolute-value table), 18 (tie interpretation) and 21 (recovery figure/SLO boundaries), plus final page 6 (undefined-draw disclosure). No visible clipping found. This is not a semantic proof from thumbnails. Figure source bytes are inherited unchanged.

Standard font-shape fallback warnings and the draft's disabled ACM citation-strip warning remain. Inherited incomplete bibliography-field warnings remain in `.blg.txt`; citations resolve, but full reference metadata/publication and accessibility checks remain an author gate. Current ToMPECS author-guidelines fetch still returns HTTP 403, so the publisher's exact current page/anonymity/supplement rules remain unverified. The conservative author-imposed 30-page ceiling is enforced.

## Commands

Requirements: Python 3.12 with NumPy 2.3.5, SciPy 1.17.1, PyMuPDF, pandas/pyarrow and the repository's existing pytest dependencies; TeX Live with pdflatex/BibTeX and the unchanged M1 template. No package upgrade was performed. Audit scripts are independent of the production analysis modules. `scripts/revise.py` records one-time editing construction and is **not** a regeneration step; build the committed final TeX directly.

The cross-metric audit requires the preserved sibling worktree:
`llm-serving-scheduler-lssp-cross-metric-analysis-extension/artifacts/analysis/cross_metric_extension/33729102c2f8867cb521f8557cd51b42d8830811de8dea16cc7ab68d53b61fd9/`.
Set `LSSP_REPOS_ROOT` to its parent if needed. Exact input hashes are in `evidence/statistical-audit.json`; a missing external source fails rather than falling back to derived M1 excerpts. SLO extension values remain inherited audited M1 findings; M2 does not rerun SLO simulations.

From the M2 repository root, run each job in a separate TMUX window. The wrapper records command, shell PID, start/end, log and exit code. Its completed run logs are committed under `evidence/validation/`.

```bash
# Session may already exist from this review; reuse it if so.
tmux new-session -d -s lssp-tompecs-m2-repro -n keeper
export LSSP_REPOS_ROOT=/home/soroush/repos
# Commands below are window payloads; use the absolute checkout path when launching from elsewhere.
tmux new-window -t lssp-tompecs-m2-repro -n audit \
  'bash paper/tompecs-m2/scripts/job.sh audit-repro python -u paper/tompecs-m2/scripts/audit.py'
tmux new-window -t lssp-tompecs-m2-repro -n additional \
  'bash paper/tompecs-m2/scripts/job.sh additional-repro python paper/tompecs-m2/scripts/additional_checks.py'
tmux new-window -t lssp-tompecs-m2-repro -n cpu \
  'bash paper/tompecs-m2/scripts/job.sh cpu-repro bash paper/tompecs-m2/scripts/checks.sh'
tmux new-window -t lssp-tompecs-m2-repro -n documents \
  'bash paper/tompecs-m2/scripts/job.sh documents-repro bash paper/tompecs-m2/scripts/build_validate.sh'
```

The wrapper sets `CUDA_VISIBLE_DEVICES=''`, offline model flags, disabled pytest plugin autoload/bytecode writing and single-thread BLAS/OpenMP. Inputs are opened read-only. Audit runs here took 5–8 seconds; complete clean document validation took 8–9 seconds. No task exceeded three minutes and none was left running. If a future environment makes a job long-running, follow the user's stop/record rule rather than repeatedly polling or waiting synchronously.

For a clean rebuild, archive each existing `paper/tompecs-m2/build/revised-*` directory to a uniquely named directory under the ignored M2 build tree before launching `build_validate.sh`. Do not modify M1. Builds use the existing M1 template/figures via relative symlinks, fixed `SOURCE_DATE_EPOCH=1792627200`, and resolving pdflatex/BibTeX passes. `validate.py` publishes the generated review PDFs and section allocations only under M2.

`SHA256SUMS` binds new package files; `evidence/input-source-hashes.json` binds the analysis code/protocol inputs, with raw-data hashes also in the statistical report. `evidence/m1-to-m2-manuscript.diff` records every manuscript change. Reproduction scripts write new evidence, so run in a disposable checkout when preserving the delivered evidence byte for byte.

## Persistent execution record

TMUX session: `lssp-tompecs-m2`, with an idle `keeper` window retained. Actual commands, PIDs and timestamps are in `evidence/validation/*.metadata`; matching `.exit` files are authoritative completion evidence. These are wrapper shell PIDs, not a claim to have recorded every short-lived child process ID. Build logs also record build-script PIDs.

| Window/job | Wrapper PID | Exit | State |
|---|---:|---:|---|
| audit | 531876 | 1 | FAILED |
| audit-final | 532029 | 1 | FAILED |
| audit-v3 | 532121 | 1 | FAILED |
| audit-verified | 532196 | 0 | COMPLETED_SUCCESS |
| cpu-checks | 532833 | 0 | COMPLETED_SUCCESS |
| build-first | 532842 | 0 | COMPLETED_SUCCESS |
| clean-build | 533123 | 0 | COMPLETED_SUCCESS |
| additional-checks | 533898 | 0 | COMPLETED_SUCCESS |
| package-check | 535080 | 0 | COMPLETED_SUCCESS |
| package-final | 535930 | 0 | COMPLETED_SUCCESS |
| clean-build-final | 535204 | 0 | COMPLETED_SUCCESS |

Each job has exactly one recorded state. Task disposition is separately `COMPLETED_WITH_ISSUES` because scientific blockers remain; successful compilation is not publication readiness.

## Preserved development diagnostics and anomaly

The first audit attempted a nonexistent `relative_order` field. It was corrected to the manifest's native valid-row position. The next two runs exposed NumPy scalar JSON serialization issues (output writer, then console summary). These were fixed without changing scientific methods. All failed logs and exit codes remain; final assertions and the separate primary checks pass. They are not counted as successful tests. A final manual assertion that all resampled tau values were defined failed; inspection found 3,287 discarded draws across 30 comparisons. The independent computation already matched the historical skip rule. The manuscript and audit now disclose this rather than assuming 2,000 usable draws. See `evidence/final-review-diagnostic.json`.

A requested shell cleanup command was automatically rejected before execution because `rm -f`-style commands were prohibited. A safer archive/rename of the generated M2 build directory enabled the clean build; no approval or historical deletion was needed.

The inherited `dataset/v1.1.0/scientific/campaign/consolidated.json` LFS-filter anomaly remains visible as a modified Git status entry. Its raw SHA-256 is unchanged:
`73adf7d97f06985ec8f8e1c2f794fd43178433eb198e1c00705e817f4bde9c26`.
It is not staged or repaired. The eleven normal Parquet LFS files were hydrated in the **new checkout** from existing local objects and validated against their pinned payload hashes; this is distinct from repairing the anomaly. No inherited scientific bytes were replaced.
