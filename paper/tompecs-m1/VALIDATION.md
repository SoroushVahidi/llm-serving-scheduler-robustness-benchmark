# Validation and reproduction

Performed locally through Codex, CPU/document work only. No simulation campaign, model inference, GPU resources, Slurm/Wulver work, paid CI, Actions, submission or merge.

## Results

| Check | Result | Evidence |
|---|---|---|
| Layout-only ACM baseline | 34 manuscript / 35 acmsmall pages | PDFs, TeX and full compilation/BibTeX logs |
| Revised draft | **24 manuscript / 24 acmsmall pages**, including references/declarations | PDFs and `evidence/page-counts.json` |
| Focused inherited CPU suite | **32 passed, 0 failed, 0 skipped**, 0.75 s | `evidence/validation/cpu-tests.log.txt`; one expected scipy constant-input warning |
| Independent numerical checks | **8 passed, 0 failed** | `evidence/numerical-audit.{json,txt}` |
| Original table payload reproduction | **4/4 equal**, excluding generation time/checkout stamp | `evidence/table-regeneration.{json,txt}` |
| Document/preservation checks | **24 passed, 0 failed** | `evidence/document-validation.{json,txt}` |
| Frozen release validator | PASS, problems=[]; 18,720 rows, 9,360 deterministic pairs, 57 checksum entries/zero mismatches | `evidence/validation/dataset-validation.log.txt` |
| Original tracked files | **428 unchanged**, including 11 expanded LFS payloads validated by pinned size/SHA-256 | Document validation; no original dataset/manuscript/source edits |
| Baseline content | All 13 section bodies and abstract unchanged after disclosed whitespace/figure-path/Description normalization; bibliography unchanged | Document validation |
| Final LaTeX | Both revised modes: no undefined refs/citations, duplicate-label warnings or overfull boxes | Final native `.log` files copied as `.txt` |
| Bibliography | 40 entries examined, 25 cited in revision; 38 URLs retrieved, two blocked; some successful responses are only redirect pages | `evidence/bibliography-links.json`; retrieval is not full bibliographic correctness |
| Visual inspection | Manuscript pages 1,6,9,13,16,24 and both retained figures (pages 14,19) inspected through rendered images | No obvious clipping/illegibility found; not an exhaustive visual proof for all four PDFs |

Counts are separate: 32 pytest tests are not inflated by arithmetic/document assertions, table checks or repeated compiler passes. Full P2B 583-test suite was not rerun: this branch does not alter its code and is based on main, not the engineering stack. Scientific resampling/GLM models and native/GPU measurements were not rerun.

The 29-page budget leaves five pages for author additions. The baseline exceeds the 30-page ceiling by four manuscript pages (five in acmsmall); the revision has no excess. Section extents are approximate geometric allocations derived from visible heading coordinates; PDF page totals/start pages are exact. Original PDF bookmarks can have stale TeX destinations, so the inventory uses visible heading text rather than reporting negative bookmark-derived extents.

## Reproduction commands

From the isolated repository root, with existing Python/TeX dependencies:

```bash
export CUDA_VISIBLE_DEVICES='' HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
export PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONDONTWRITEBYTECODE=1
python -B -m pytest -q -p no:cacheprovider \
  tests/test_anwg_metric.py \
  tests/test_ranking_portability_analysis_stats.py \
  tests/test_ranking_portability_analysis_ranking.py \
  tests/test_ranking_portability_analysis_reversal.py \
  tests/test_ranking_portability_analysis_sample_complexity.py
(cd dataset/v1.1.0 && python -B scripts/validate_release.py)
python paper/tompecs-m1/scripts/audit.py
python paper/tompecs-m1/scripts/check_tables.py
python paper/tompecs-m1/scripts/validate_documents.py
bash paper/tompecs-m1/scripts/build.sh baseline manuscript
bash paper/tompecs-m1/scripts/build.sh baseline acmsmall
bash paper/tompecs-m1/scripts/build.sh revised manuscript
bash paper/tompecs-m1/scripts/build.sh revised acmsmall
python paper/tompecs-m1/scripts/inventory.py
```

Build scripts preserve acmart defaults, run pdflatex/BibTeX/required resolving passes, record actual start/end/pid/cwd, use fixed PDF date epoch, and write only this new directory's ignored `build/` tree. Committed review PDFs are copied from those outputs. The class is generated from vendored unchanged DTX/INS with `latex -interaction=nonstopmode acmart.ins` in `template/`; no installed TeX package is modified. The environment and class hashes are retained.

`audit.py` expects original cross-metric and SLO extension artifacts in sibling historical worktrees; set `LSSP_REPOS_ROOT` to their parent if different. Exact directories and SHA-256 are in `evidence/numerical-audit.json`. Missing files cause an error; the script does not invent results or silently use the copied point-record excerpt as independent raw evidence. These external originals are preserved, not re-published or regenerated. The canonical dataset is local and independently validated. Historical Git commits must be available for `inventory.py` and baseline checks. A fresh shallow clone without LFS payloads/historical commits is insufficient.

Optional bibliography URL recheck (network only, no credentials/API billing):

```bash
python paper/tompecs-m1/scripts/check_references.py
```

It uses bounded parallel HTTP requests to original primary URLs; status/title evidence must be interpreted manually. The Orca URL was corrected to its primary USENIX publication, and the Bailian source URL added from the pinned attribution ledger. No publication year, author list or DOI was inferred from HTTP 200.

## Persistent execution and diagnostics

Named TMUX session: **`lssp-tompecs-m1`**. Separate sequential completed build windows and a checks window retained logs under `/home/soroush/.local/state/lssp-tompecs-m1/`. Final `sealed` build completed with **exit 0**, as did both final document modes; `evidence/validation/tmux-final.txt` records the retained baseline pane; later short-lived windows exited normally and their separate PID, status and exit files are the completion evidence. Scripts, PID/exit files, full stdout, compiler file lists and checkpoints are mirrored in `evidence/validation/`. All workers completed promptly; none was left running or duplicated.

Initial diagnostics are retained, not counted as final test failures:

- Bibliography retrieval first failed because optional BeautifulSoup was absent. Replaced that dependency with stdlib title parsing; no package installation or evidence weakening.
- Initial preservation check compared expanded Parquet bytes to Git LFS pointer blobs and flagged 11 files. Final check validates the pinned SHA-256 and size; all pass. Raw initial report is retained.
- Initial revision was 20 manuscript pages. Expanded methods/tables and explicit corrections produced the final 24-page draft. Its earlier PDF/log is retained as development history, not a second scientific result.
- Standard acmart font-shape substitution and incomplete bibliography-field warnings remain. The required submission metadata and final complete references are not claimed ready. Old baseline errors remain deliberately visible.
- Git displays `dataset/v1.1.0/scientific/campaign/consolidated.json` as modified because of the inherited LFS-filter anomaly. Its raw bytes equal the original blob, SHA-256 `73adf7d97f06985ec8f8e1c2f794fd43178433eb198e1c00705e817f4bde9c26`; it is untouched and unstaged.

Final status concerns preparation only. No claim of submission readiness or physical scientific validation follows.
