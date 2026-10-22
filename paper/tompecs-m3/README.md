# M3 author-review manuscript

**State: complete manuscript draft, pending author review and submission blockers.** This is a rewrite, not an experimental campaign. The common-model evaluation is central; historical evidence motivates it; STAT01 is a separately scoped diagnostic.

- Source: `main.tex`, `sections/`, `references.bib`.
- Review PDF: [pdf/m3-manuscript.pdf](pdf/m3-manuscript.pdf).
- Compact layout: [pdf/m3-acmsmall.pdf](pdf/m3-acmsmall.pdf).
- [M2_TO_M3_CHANGES.md](M2_TO_M3_CHANGES.md).
- [CLAIM_EVIDENCE_VERIFICATION.md](CLAIM_EVIDENCE_VERIFICATION.md).
- [CITATION_VERIFICATION.md](CITATION_VERIFICATION.md).
- [SUBMISSION_BLOCKERS.md](SUBMISSION_BLOCKERS.md).
- [VALIDATION.md](VALIDATION.md).

## Authority and preservation

Branch `manuscript/lssp-tompecs-m3` is stacked on final-results review PR #17, commit `6b2eedd7aa254986b85c1bb901587641cbeac8b0`, which includes prewrite audit PR #16, `d22c7751af9c563d5a4d8a304c007f26112c4d12`, and the M2 source. Execution evidence retains its separate campaign identities: C01-FULL `2d8342e699f35044044ac518c0b75a3c4a1c768c` (PR #15, job 1440402), pilot `9aed0206de66886e9feb0b003b59f0b7dfea68c9`, and STAT01 recovery `1ac4c8dd1421aabad05e6ce243cb911a6ed6c8e1` (PR #14, job 1440206).

Only this new directory changes. Experimental branches, M2, historical outputs and frozen protocols remain intact. Copies in `evidence/data/` are gzip envelopes around exact saved bytes, with both compressed and uncompressed SHA-256 values in `evidence/source-manifest.json`. These are presentation inputs, not replacement campaign outputs. The full raw arrays/journals remain in the locations listed in the claim-evidence report. Current external reviewer access is unresolved.

## Local reproduction (no scheduling or experiment execution)

From repository root:

```bash
python paper/tompecs-m3/scripts/render_results.py
bash paper/tompecs-m3/scripts/build.sh manuscript
bash paper/tompecs-m3/scripts/build.sh acmsmall
python paper/tompecs-m3/scripts/validate.py
```

Dependencies: Python 3.12, NumPy, Matplotlib, PyMuPDF; pdfLaTeX/BibTeX and pdfinfo. The build deliberately uses the unchanged ACM template in `paper/tompecs-m2/template/` (acmart 2.20) and its bibliography style. Source/PDF clocks are fixed; vector plot dates are omitted. This reuses existing manuscript/acmsmall workflows without asserting a current ToMPECS format requirement or page limit. Do not use GitHub Actions.

`render_results.py` verifies saved hashes, renders four vector figures, exports every cell metric and both calibration families, and records numerical claims. It imports no engine, policy, bootstrap or synthetic generator. `validate.py` independently checks presentation numbers, full endpoint CSV equality, references, PDFs and preservation. No external source access is needed for these steps.

The supplementary CSVs are machine-readable, not an additional inferential analysis. Plot points aggregate complete windows; no C01 error bars or significance stars are used. `stat-all-endpoints.csv` has **7,200 rows**, explicitly keyed by original versus expanded family, method, scenario and endpoint, with available count, mean, bounds and MCSE. The original-family scenario screen and stop table remains separate from the expanded-family main-text diagnostic.
