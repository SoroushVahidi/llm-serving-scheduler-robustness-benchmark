# Correction and validation record

Reviewed baseline: PR #19 at `ed24b2e8224ea88aa289b60dea6142beeea5330d`. Branch: `audit/lssp-m3-final-readiness`, stacked directly on `manuscript/lssp-tompecs-m3-rewrite`. Task state: **COMPLETED_SUCCESS**. Submission verdict remains **NOT_READY** for the reasons in the [referee report](REFEREE_REPORT.md).

## Justified manuscript corrections

- Clarified that **a request** produces no output during its own prefill; other residents may decode in the same batch. Read against the frozen engine/policy implementation; no semantics or result changes.
- Clarified that throughput is a finite-window completion rate including drain, not a sustainable-arrival-rate or system-capacity estimate.
- Added directly relevant Etalon and LLMServingSim 2.0 comparisons; updated LLMServingSim 2024 to its published IISWC identity.
- Added the DynamoLLM and KVCache workload citations explicitly requested by the Azure and pinned Bailian/Qwen dataset documentation. Bibliography grows from 20 to **24** entries.
- Made the pending AI-disclosure question precise about research/analysis/figure use and current ACM policy. It remains an author-review question, not a fabricated declaration of author verification or a complete research history.
- Added ranked referee, contribution/evidence, literature, detailed overlap, requirements and author-decision reports. Marked earlier review inventories as superseded where applicable.

No figure, generated table, supplementary result CSV, protocol, frozen input, experimental implementation, or earlier manuscript was changed. The inherited manuscript `main.tex` and the performance/rankings/inference result sections are unchanged. No new performance/statistical numbers were inserted. PDF pagination and references were rebuilt after the source changes.

## Local checks and outcomes

Both existing ACM workflows completed successfully:

```bash
bash paper/tompecs-m3/scripts/build.sh manuscript
bash paper/tompecs-m3/scripts/build.sh acmsmall
python paper/tompecs-m3/scripts/validate.py
python paper/tompecs-m3/scripts/package.py
```

| Check | Outcome |
|---|---|
| ACM manuscript PDF | PASS, **21 pages**, including references and appendices |
| ACM `acmsmall` PDF | PASS, **22 pages**, including references and appendices |
| Final-pass LaTeX/BibTeX diagnostics | No errors, overfull boxes, undefined citations/references, duplicate labels, or rerun requests |
| Bibliography | All **24** keys cited; no undefined or uncited entries |
| Full saved C01 report oracle | PASS: **5,760** absolute rows; **15,840** rankings; **95,040** pairwise rows; **26,136** reversal groups |
| Narrative numerical anchors | **54** checks pass |
| STAT01 supplementary endpoint identity | All **7,200** family/method/endpoint rows match saved inputs, including availability and numerical endpoint fields |
| Frozen preservation | Exact byte comparison of all tracked files in M3 `evidence/inputs`, `supplement`, `figures`, `tables`, `template`, and `scripts` against PR #19; no changes outside M3 |
| Historical consolidated artifact | SHA-256 remains `73adf7d97f06985ec8f8e1c2f794fd43178433eb198e1c00705e817f4bde9c26` |
| Layout and displays | All **43 pages** visually checked in contact sheets; enlarged checks of results figures, calibration/scenario tables, bibliography and declarations. No observed clipping/overlap; PDF extraction finds no text outside page bounds |
| Visible decisions | Four AUTHOR REVIEW REQUIRED paragraphs present in each PDF; author/declaration/release gates remain unresolved |
| Whitespace/diff | `git diff --check` passes; build-console logs have trailing whitespace normalized only |
| Overlap diagnostic | 13 pinned source sets; current/headroom package identity and historical PEVA/SMPT similarity measured; semantic audit and unavailable-version limits reported separately |

Three unchanged optional BibTeX metadata advisories remain: missing Vidur address and missing Maurer/Pontil publisher/address. The draft also retains the known ACM reference-block suppression advisory. Build-console transcripts include expected undefined references from initial passes; **final-pass logs**, checked by the validator, have none. These are not journal-policy clearance or final production metadata.

Machine-readable evidence: [existing full validator output](../evidence/validation/validation.json), [additional preservation/PDF checks](final-checks.json), [source-overlap fingerprints and counts](overlap-evidence.json), and the regenerated [package manifest](../evidence/package-manifest.json). Logs are in `../evidence/validation/`.

All work ran locally and completed in short bounded commands. No detached worker or HPC job was necessary. No simulator campaign, synthetic-study generation, Slurm, GitHub Actions, merge, journal submission, external correspondence, artifact publication, or related-manuscript modification was performed. The commit and draft PR use `[skip ci]` to avoid push/PR workflows.

## Review limits

Rechecking saved metrics and package identity is not fresh raw-journal replication, independent model validation, a proof of every statistical implementation, or proof of current submission statuses. Full author responsibility, licenses, raw reviewer access, and journal-specific requirements remain explicit gates. This review does not turn the descriptive C01 results into population inference or the indexed official-source checks into a confirmed ToMPECS submission checklist.
