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

- total candidate works reviewed: 35+
- primary-source verified: 19
- verified preprint / conference among them: 16
- unresolved / partial metadata: 5
- rejected / non-citable: 11+

## Final search decision

Broad search is complete for this consolidation pass. Future broad search should be triggered only by the conditions defined in `README.md`.
