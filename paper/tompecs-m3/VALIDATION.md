# M3 build and validation record

**Outcome: COMPLETED_SUCCESS for manuscript preparation.** Author-review draft ready; final submission blockers remain in `SUBMISSION_BLOCKERS.md`. This outcome does not assert native model validity, universal statistical calibration or journal acceptance.

## Local checks performed

1. `python paper/tompecs-m3/scripts/render_results.py` — PASS. Verified 27 frozen presentation-source hashes; exact 5,760-cell Cartesian coverage; 144-cell reuse; all requests complete; chunked/decode metric equality; rounded headline trade-offs; reversal numerator/denominator identities. Generated four vector PDF figures, seven TeX tables (three handwritten contract/provenance/method tables plus four data-generated tables), and complete CSV supplements. No engine or synthetic generator imported.
2. `bash paper/tompecs-m3/scripts/build.sh manuscript` — PASS, **20 pages**, including bibliography, declarations and appendices.
3. `bash paper/tompecs-m3/scripts/build.sh acmsmall` — PASS, **19 pages**, including the same material. These counts are not journal page limits.
4. `python paper/tompecs-m3/scripts/validate.py` — PASS, 17 grouped assertions with per-record checks. Independently recomputed key source/capacity means and relative differences; checked all 5,760 CSV rows against saved metrics and all 7,200 STAT01 endpoint rows against original/expanded means, bounds, available counts and MCSEs. Checked all 18 final scenarios, stop reasons, screen totals and both multiplicity budgets.
5. Document checks — 21 distinct bibliography entries, all cited; zero unresolved citation keys or cross-reference labels; four existing figures and four accessibility descriptions; explicit answers to RQ1/RQ2/RQ3; four conspicuous author-review declaration paragraphs. No overfull horizontal boxes or undefined citations/references in either final LaTeX log.
6. Visual inspection — reviewed all-page contact sheets for both layouts and enlarged key display pages, including the absolute-performance and calibration figures. Fixed a clipped axis label, moved figures beside their discussion, and kept complete tables readable. The manuscript layout has a supplementary figure-only page; no content is cropped. Vector fonts are embedded. This is a visual inspection, not accessibility certification.
7. Preservation — compared inherited tracked paths against PR17. Only the already present hydrated-LFS status remains for historical `consolidated.json`; its SHA-256 matches the reviewed historical bytes. No M2, protocol, experiment or historical result is staged in the M3 change.

## Scientific checks versus prior validation

This revision checks the presentation of saved evidence. It does not rerun the campaigns or duplicate their raw validation. The final-results review already checked every C01 result/input identity and all analysis outputs, plus24 sampled raw event journals; STAT01 had full inventory/moment checks plus200 sampled saved-study referee checks. Both allocations had already performed exhaustive independent conformance/batch checks before completion. Five copied review-result JSON files preserve those distinctions.

The publication package retains nulls and costs: zero source-mean practical reversals; exact chunked/decode equivalence; inactive urgency gate; lower throughput and worse BurstGPT tails; calibration concerns, low power, unavailable intervals and inconclusive scenarios. The arithmetic amendment is not presented as a statistical repair. No C01 confidence intervals, p-values or significance stars were introduced.

## Residual build messages, disclosed

- The inherited ACM draft convention `printacmref=false` emits an ACM reference-format warning in both layouts. Publication metadata and the final reference block must be completed in the actual submission/production configuration; no DOI, volume or issue has been certified for this unpublished manuscript.
- BibTeX emits one optional metadata warning: no address in the official Vidur proceedings entry. Title/authors/venue/year/volume/pages and URL are verified; no location was fabricated solely to silence the warning.
- The PDFs are not tagged-accessibility-certified. Figure descriptions are supplied in LaTeX for the final production process.

## Reproducibility evidence

- `evidence/manuscript-validation.json`: numerical checks, page counts and final PDF hashes.
- `evidence/numerical-claims.json`: machine-readable C01 totals, trade-off ranges and STAT01 stopping summary.
- `evidence/source-manifest.json`: exact source paths and compressed/uncompressed SHA-256 identities.
- `evidence/build-environment.json`: Python, NumPy, Matplotlib, PyMuPDF and unchanged ACM template identity.
- `evidence/build-manuscript.log.txt`, `build-acmsmall.log.txt`, `bibtex.log.txt`: final compiler records, with trailing whitespace normalized for Git.
- `evidence/citation-metadata.json`: retrieved publisher-deposited records and official BibTeX responses.

All commands completed locally in seconds. No Slurm connection, new submission, experiment, GitHub Actions dispatch, merge or external correspondence was used for this rewrite. Commit and PR titles include `[skip ci]` to avoid repository push/pull-request workflows.
