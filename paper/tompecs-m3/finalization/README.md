# M3 finalization checkpoint — publication blocked

Status: **BLOCKED**. Numerical core: **PASS**. Full scientific and administrative submission readiness: **NOT CERTIFIED**.

This checkpoint independently rechecks the major revision at `dda5fcf0f8f2a6f543e799f20767c9272022afc8` (PR #22). The starting main commit is `1ed5d332e006fdd0bc3a59a403c9044a36ef6d29`. That main commit contains the same manuscript bytes under `LLM_Serving_Scheduler_Rankings_and_Performance_Tradeoffs.pdf`. This checkpoint does not replace that PDF or create a research-artifact release.

## Freshly executed verification

The checkers read saved records; no simulator, study generator, GPU workload or new scientific campaign was run. C01 and STAT01 inputs came from the separate rc1 clean extraction. Reports here are new executions, not copied PASS conclusions from the previous worker.

| Check | Result | New evidence |
|---|---|---|
| Complete C01 saved terminal records and metric recomputation | 5,760 cells; 1,152,000 completed request executions; no unfinished requests | `c01-independent.json` |
| Chunked/decode equivalence | 1,440 exact terminal-record matches | `c01-independent.json` |
| C01 independently implemented analysis oracle | 15,840 rankings; 95,040 pairwise rows; 26,136 reversal groups | `manuscript-validation.json` |
| Previously identified narrative checks | 53 scientific checks plus the separate historical dataset SHA-256 check, covering the original 54 | `manuscript-validation.json`, `preservation.json` |
| STAT01 batch inventory and independent decimal reconstruction | 5,360 batches; 134,000 saved studies; all 7,200 endpoint summaries; maximum mean discrepancy below 1e-15 | `stat-independent.json` |
| Historical versus corrected procedures | 200 saved studies re-refereed; 200 frozen-source BH checks; original floating-point boundary discrepancy reproduced | `stat-procedures.json` |
| Worked BurstGPT example | 400 terminal states; 2,497 journal events; selection, derived tables and CSVs verified | `example-verification.json` |
| Abstract/conclusion effects and aggregation distinctions | All six source/capacity groups independently recomputed; 0/2,376 strict source-mean reversals; window/metric reversals retained | `abstract-independent.json` |
| Journal ordering versus terminal equality | Direct saved-journal counterexample: identical span membership, different span ordering, equal terminal records | `journal-order-check.json` |
| Fresh baseline PDF builds | 24 manuscript / 26 acmsmall pages; byte-identical to the authoritative PDFs after reference convergence | See hashes below |

The first clean acmsmall build exposed a reproducibility defect: three LaTeX passes were insufficient for reference convergence. `scripts/build.sh` now performs up to five passes, stops when references converge, and fails explicitly if they do not. A new build from an empty acmsmall build directory and the unchanged strict validator both pass. The separate abstract checker initially conflated the `source` and `source_mean` report axes; that checker error was corrected to the manuscript's stated source-mean estimand. No experimental data, scientific result or manuscript claim was changed.

Baseline PDF identities:

- Manuscript: 728,978 bytes; 24 pages; SHA-256 `a5e8d45d63bd404944a55c6efcb202b3fd52e06589ed7b64c90921eab0b6a39f`.
- Acmsmall: 728,933 bytes; 26 pages; SHA-256 `d41dbfa68eb4a18df9bff28d318992c21f3b2b6917b8d837379ca62514760fcb`.

These are baseline verification builds, not a finalized submission package. The old declaration placeholders and historical editorial-status prose have not been represented as resolved publication text.

## Scientific assessment

The numerical checks support the bounded CM-0.1 case study. Four policy labels yield three observed behaviors, with an inactive SLO urgency gate and active prompt-length admission ordering. Source code fixes batches at 1 ms; at most eight resident requests contribute at most 512 tokens each, below the 32,768-token budget. This explains why feasible chunked work is not budget-competitive and why the 495 ms urgency threshold does not bind for continuously scheduled decodes. Terminal equivalence must not be described as byte-identical journals.

The abstract's 11.3–34.0% mean-latency reductions, 1.65–4.01% throughput losses, and 3.72%/18.97% BurstGPT mean-window-p95 increases reproduce. Throughput is finite drained output divided by elapsed simulated time; it is not hardware throughput or a long-run stability claim. The example remains outcome-selected and noncausal. STAT01 remains a separate historical-inference diagnostic. No new general scheduling principle, physical validity or population guarantee is established.

[Dai et al., arXiv:2504.07347v3](https://arxiv.org/html/2504.07347v3), dated May 18, 2026, was freshly checked against its primary abstract and full text. Its token-load-dependent batch-time model and request-count-constrained stability analysis support the distinction in M3; no theorem transfers to CM-0.1. All 25 local citation keys resolve, but a fresh primary-source audit of all other references has not been completed in this checkpoint.

## Publication gate and unresolved work

The author has confirmed authorship, affiliation/contact, funding, conflicts, computing acknowledgment, AI disclosure, release authorization, MIT for original code, CC BY 4.0 for eligible original research data/results, and exclusion of original third-party raw traces. Those decisions are settled and are not awaiting reapproval.

Current official ToMPECS requirements remain unverified. The [author-guidelines endpoint](https://dl.acm.org/journal/tompecs/author-guidelines) returns HTTP 403; the legacy journal site and alternate ACM author/policy endpoints also did not supply usable current journal instructions. Initial-review format, anonymity, supplement rules, prepublication repository/artifact conditions, cover-letter requirements and declaration placement cannot be inferred from the template or from those failures. An official clarification route is the current journal editorial office; ACM's [official announcement](https://prod-www.acm.bloomreach.cloud/media-center/acm-updates) identifies Zhi-Li Zhang's editor-in-chief term beginning September 1, 2026. No message was sent.

Submission-confirmation correspondence for the two author-identified related papers establishes their identities, but does not establish exact uploaded-file hashes. Closest available local source versions were pinned and compared. A fresh full-source 12-word-shingle check finds zero shared shingles with either paper; this is a lexical diagnostic, not a semantic duplication verdict. A confidential comparison matrix and disclosure draft are retained outside the public repository. Exact submitted-version comparison and exact shared trace-row/experiment reuse remain unresolved. No author-specific editorial correspondence, submission IDs or private manuscript sources are added here.

The local rc1 candidate and companion remain unchanged. Their existence does not certify a sanitized final release. Final file-level redistribution checks, derived-input license scoping, credential/sensitivity checks, scoped release assembly and clean-environment artifact reproduction remain incomplete. Original third-party raw traces must stay excluded, and third-party-derived input fields must retain upstream terms rather than being relabeled indiscriminately as original CC BY data.

The policy gate is closed. No new Hugging Face dataset, Zenodo deposit/publication/DOI, GitHub research-artifact release or final manuscript integration was attempted. Existing portability release URLs/DOIs are not M3 release identifiers. Credentials are present locally, but their presence is not proof of publication access; no account obstacle is asserted without testing it.

## Reproduce these checks

Use an existing rc1 clean extraction as `CANDIDATE`; these commands verify saved evidence, not full experiment replication. The JSON output paths should be outside the frozen artifact.

```bash
python paper/tompecs-m3/artifact-release/verification/check_c01.py "$CANDIDATE" /tmp/m3-c01.json
python paper/tompecs-m3/artifact-release/verification/check_stat_inventory.py "$CANDIDATE" /tmp/m3-stat.json
python paper/tompecs-m3/artifact-release/verification/check_stat_samples.py "$CANDIDATE" /tmp/m3-stat-samples.json
bash paper/tompecs-m3/scripts/build.sh manuscript
bash paper/tompecs-m3/scripts/build.sh acmsmall
python paper/tompecs-m3/scripts/validate.py --standalone --artifact-root "$CANDIDATE"
python paper/tompecs-m3/finalization/check_abstract_claims.py --report /tmp/m3-abstract.json
```

The manuscript validator writes a new validation report within the checkout. Historical validation records were restored after saving the fresh results in this directory. The original worker checkout and its LFS-hydrated dataset were preserved. Full final-PDF page-by-page visual review and published-link verification remain pending because no final manuscript or artifact release was prepared.
