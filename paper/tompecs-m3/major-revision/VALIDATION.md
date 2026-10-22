# Current focused revision validation

Date: October 22, 2026. **All required checks PASS.** This supersedes earlier build/page/reference counts for the revised manuscript, not historical campaign evidence. Scientific assessment is separately justified in [REMAINING_BLOCKERS.md](REMAINING_BLOCKERS.md); compilation alone establishes no submission readiness.

## Current checks

- Both inherited ACM build workflows pass: **24 manuscript pages / 26 acmsmall pages**. No errors, overfull boxes, unresolved citations/references, duplicate labels or rerun requests. Three inherited optional BibTeX advisories (Vidur address; Maurer/Pontil publisher/address) and the intentionally suppressed ACM reference block remain recorded. No publisher/TAPS acceptance is claimed.
- All **25** bibliography keys are cited and resolve. The only new reference, Dai/Deng/Li/Peng arXiv v3 (May 18, 2026), was checked against the requested primary pages. All table/figure/appendix labels resolve: four figures, ten tables, Appendices A/B/C. Original appendix equations are preserved exactly.
- Independent full C01 saved-analysis oracle: **5,760** absolute rows, **15,840** rankings, **95,040** pairwise rows and **26,136** reversal groups. The unchanged **54** narrative checks and exact **7,200** STAT CSV endpoint rows pass. No original frozen check was removed or weakened.
- Worked example: standard-library direct terminal arithmetic versus an independently written NumPy/event reconstruction, with no shared analysis implementation or engine/policy imports. All **400** terminal states across **2,497** saved events match exactly; input/result/journal hashes, spans, arrivals, first-output/completion times, anchors, residency and KV ledgers pass. All new table/CSV values, percentages, completion counts, p95 bracket IDs and deterministic retrospective selection pass; floating arithmetic tolerance is `1e-12`, while hashes/identities/integer counts/terminal dictionaries are exact. [Machine report](example-verification.json).
- The first differing admission membership, requests13/14, and maximum delayed/improved requests26/196 are verified from events, not invented timelines. Throughput uses fixed 3,520 outputs over full drain; mean/p95 use all 200. The selected identity is frozen and reruns do not search for another.
- Chronology prose/caption moved intact to Appendix C; detailed STAT outcome/stopping prose moved intact to Appendix A. Larger scenario-table typography changes only its wrapper. All five pre-existing generated table files, three vector figures, supplements and **37** compressed inputs remain byte-identical. [Revision checks](revision-verification.json).
- Both rc1 archive digests remain exactly pinned, and frozen policies/engine match the full execution commit. Historical consolidated bytes still hash to `73adf7d97f06985ec8f8e1c2f794fd43178433eb198e1c00705e817f4bde9c26`; the known hydrated-LFS anomaly is not staged. M2, prior manuscripts and raw evidence are unchanged. [Preservation report](preservation.json).
- All newly created/modified tracked work is under `paper/tompecs-m3/`, aside from the unchanged pre-existing LFS status. `git diff --check` passes after removing one trailing blank line and using LF line endings for new CSVs and normalizing trailing whitespace in committed build-log copies (raw logs remain in the run directory). The earlier inspection typo for a result-file path was corrected to its directory's `result.json`; it did not modify evidence or mask a failed numeric check.

The example was additionally regenerated against rc1’s separate clean extraction. All five derived files were byte-identical and the independent event checker passed there, confirming the explicit artifact-root interface. See `portable-example-check.json`.

## Visual and claim review

Read the complete starting manuscript source (all sections, tables and bibliography) and all 22 compiled pages before substantive changes. Inspected full-page layout overviews for both revised formats and focused rendered pages covering related work, the model, worked-example tables, discussion/declarations and the enlarged scenario table. Final checks specifically inspected manuscript page11 and acmsmall page12 (example), and manuscript page22 / acmsmall page24 (scenario table); no clipping or overlap. A float barrier keeps the large absolute-performance figure from interrupting the worked example. This is a layout and affected-claim review, not a full accessibility certification.

[The focused claim audit](CLAIM_TO_EVIDENCE.md) identifies support, identity, reasoning, numeric checks and limits for every substantive revision. No existing C01/STAT result changed. The current source/validation package retains complete negative/null findings and distinguishes original/source/exact STAT identities, original/expanded families and precision/max-count stops.

## Reproduction and reporting boundary

Commands used, all on saved evidence:

```bash
python paper/tompecs-m3/scripts/render.py
python paper/tompecs-m3/major-revision/analyze_example.py /path/to/rc1-root --output paper/tompecs-m3/major-revision
bash paper/tompecs-m3/scripts/build.sh manuscript
bash paper/tompecs-m3/scripts/build.sh acmsmall
python paper/tompecs-m3/scripts/validate.py --artifact-root /path/to/rc1-root
python paper/tompecs-m3/major-revision/verify_revision.py
python paper/tompecs-m3/scripts/package.py
```

`verify_revision.py` uses this Git base for relocation/preservation checks; archive-only readers use `validate.py --standalone`. An explicit artifact root triggers fresh independent example reconstruction. Without it, validation clearly labels the narrower saved-report/support-hash check. The independent checker can also run separately with `--derived` and `--report`, leaving frozen files untouched. `package.py` runs after final documents and copies already-built PDFs, updating the complete packet manifest; no experiment is run. The versioned local companion has its own external manifest, avoiding self-referential hashes.

Full stdout/stderr, intermediate renders and checkpoints remain in `/home/soroush/lssp-m3-major-revision-20261022/`; current build logs are also in `evidence/validation/`. PR21's exhaustive raw inventory/clean-extraction checks remain dated historical evidence; this pass does not claim a fresh complete replay of 5,760 journals or 134,000 studies. No new simulation, Monte Carlo generation, Slurm job, Actions invocation, release, merge, submission or correspondence occurred.
