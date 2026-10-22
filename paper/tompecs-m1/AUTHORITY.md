# Source authority and historical submissions

Audit date: 2026-10-22 UTC (2026-10-21 America/Toronto). No email was sent or journal contacted. The author states that JSC, Performance Evaluation and SMPT rejected the manuscript and that no active review was found in their email records. This is **author-provided status**, not an independent email audit in M1. Submission packages prove prepared versions, not the exact upload accepted by each portal.

## Authority hierarchy

1. Frozen numerical evidence and execution manifests take precedence over prose. The v1.1.0 package on main contains 18,720 outcomes, six canonical analyses and immutable source/manifests. Its validator and hashes pass locally.
2. Latest complete venue-specific source located: SMPT at `cc25fcd14f6fe28ab30d9e46635a72c0d6285d00`, `paper/main.tex`, `paper/sections/`, `paper/references.bib`, `paper/generated/figures/`. This is the editorial starting point, **not a declaration that every claim is true**.
3. MGPU00 and PRs #4–#8 qualify scientific interpretation. Their sources/results are not merged or retrospectively substituted into historical numerical outputs.
4. Current main (`e73a3b7…`) contains newer dataset packaging but older Springer-style `paper/main.tex`/sections, alongside SMPT public PDFs/ZIP. A newer branch timestamp is therefore not sufficient to select a manuscript source.
5. Old `MANUSCRIPT_*` ledgers include pre-results placeholders. They preserve design history but are not authoritative inventories of completed findings.

## Versions recovered

| Venue/version | Recoverable source identity | Character of differences |
|---|---|---|
| Journal of Supercomputing | `b1f9a12`, `paper/jsc_submission_package/`; earlier JSC source ZIP preserved on historical branches | Springer format; broader exposition and earlier artifact statements |
| Performance Evaluation | `0975472`, `paper/peva_submission_package/` | Elsevier format, concision and performance-evaluation framing; same principal result numbers |
| Simulation Modelling Practice and Theory | `cc25fcd`, `paper/smpt_submission_package/` and `paper/sections/` | Explicit simulation-comparison framing; added execution-model/V&V material and model assumptions; preserves later metric/SLO extensions |
| SMPT blind | `cc25fcd`, `paper/smpt_blind_submission_package/` | Author/artifact-identification redaction, not new experiments |
| Main source versus latest package | `e73a3b7:paper/` versus `cc25fcd` SMPT | Main source is not the latest complete SMPT prose; PDF synchronization and dataset releases did not make these source trees identical |

Full revisions, per-file SHA-256, sizes and preserved PDF page counts are in `evidence/submission-versions.json`; all differing common TeX files are recorded in `evidence/submission-source-differences.diff`. Submission cover letters/ZIPs are left where they were; no originals are removed, re-uploaded or renamed.

## Layout-only baseline versus scientific revision

Baseline: convert front matter to acmart; select ACM bibliography style; retain body section text and scientific abstract verbatim modulo whitespace, figure path changes and added accessibility descriptions. Remove inherited global `sloppy`, `emergencystretch` and `arraystretch` overrides so ACM defaults govern layout. Original bibliography bytes and figure PDFs are preserved. No template dimensions/font sizes/spacing are adjusted to fit a cap. These are disclosed layout changes, not result corrections.

Revision: follow the agreed 11-section outline; consolidate repeated motivation, two redundant result tables/plots, long related-work catalogues and unverified descriptor claims. Correct data-backed prose contradictions explicitly (CLAIM_AUDIT). Reframe historical policy labels and physical results, retain all six RQs, and distinguish post-campaign extensions. The baseline and historical sources preserve all omitted prose and numerical material for author review. No result file is corrected to match the manuscript.

The manuscript is scientifically authoritative only at the level of audited claims with stated scope. Missing physical fidelity, inferential validity and provenance cannot be repaired by editorial authority.
