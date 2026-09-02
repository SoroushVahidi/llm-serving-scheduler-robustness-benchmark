# SEARCH_COVERAGE_LOG.md

This log records the broad literature search and the candidate coverage used for the LSSP primary-source consolidation.

## Search date / cutoff

- search date: 2026-09-01
- search cutoff: 2026-09-01
- search scope: public literature and official project pages; no private or hidden sources

## Databases / sources used

- arXiv
- USENIX proceedings pages
- MLSys proceedings pages
- ACM Digital Library
- Microsoft Research project pages
- official project GitHub repositories
- official benchmark and dataset releases

## Venue families

- USENIX OSDI / NSDI
- MLSys
- NeurIPS
- ACM Meas. Anal. Comput. Syst.
- arXiv preprints for 2025–2026 systems

## Query families

- `LLM serving scheduler` + system names
- `LLM serving workload trace` + `BurstGPT` + `Azure trace` + `TraceLab`
- `LLM serving benchmark simulator` + `Vidur` + `LLMServingSim`
- `scheduler ranking portability` + `rank stability` + `rank reversal` + `cross-workload scheduler comparisons`
- `LLM inference scheduling` + system names such as `FastServe`, `JITServe`, `Libra`, `SLAI`, `SCORPIO`, `PARS`, `S^3`, `P-PAS`, `LMetric`

## Candidate coverage

- total candidate works reviewed: 35+ (broad pass, 2026-09-01) plus 12 targeted items resolved in the Query-3 integrity gate (2026-09-01/02)
- primary-source verified and cited (`verified_related_work.bib`): 30 BibTeX entries (28 distinct works; `azure2024trace`/`stojkovic2025dynamollm` and `stojkovic2024dynamollmpre`/`stojkovic2025dynamollm` are paired dataset+paper / preprint+final-venue entries for the same work)
- verified metadata, related-work-only (flagged low-weight; `A Year in LLM Serving` is in the bib with an explicit caveat note, `P-PAS` is not in the bib): 2 (`P-PAS`, `A Year in LLM Serving`)
- rejected / non-citable: `XPerf` (not locatable) plus the general categories in `REJECTED_OR_NONCITABLE_REFERENCES.md`
- corrected in the Query-3 gate: BurstGPT (arXiv-only → KDD 2025), S^3 (restored as distinct from `Efficient LLM Scheduling by Learning to Rank`), Azure trace publications (bare dataset manuals → Splitwise/DynamoLLM as primary papers), VTC (restored from rejected), Azure/BurstGPT provider-independence language (softened to "distinct workload sources")

## Query-3 targeted integrity gate (2026-09-01/02)

- trigger: explicit user-directed targeted verification of apparent inconsistencies in this log's Query-2 output (not a broad re-search)
- scope: BurstGPT final-venue resolution, S^3 vs. "Efficient LLM Scheduling by Learning to Rank" distinctness, Azure/BurstGPT provider relationship, and coverage-completeness dispositions for a named 30-work checklist (Orca, vLLM/PagedAttention, Sarathi-Serve, DistServe, Llumnix, Splitwise, Mooncake, VTC, S^3, Efficient LLM Scheduling by Learning to Rank, FastServe, JITServe, Libra, LMetric, PARS, SLAI/RAD, P-PAS, SCORPIO, ProServe, Apt-Serve, BurstGPT, Azure trace publications, DynamoLLM, KVCache in the Wild, ServeGen, TraceLab, A Year in LLM Serving, Vidur, LLMServingSim, LLMServingSim 2.0, XPerf)
- result: `LITERATURE_INTEGRITY_GATE = PASS` — every named item has an explicit disposition (see `PRIMARY_SOURCE_CITATION_LEDGER.md` and `METADATA_CORRECTIONS.md`); the only unresolved item is `XPerf`, for which no primary source could be located after two independent targeted searches.

## Final search decision

Broad search is complete for this consolidation pass, and the Query-3 targeted gate above resolved the specific inconsistencies flagged for follow-up. Future broad search should be triggered only by the conditions defined in `README.md`.
