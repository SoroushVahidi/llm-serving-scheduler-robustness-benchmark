# REJECTED_OR_NONCITABLE_REFERENCES.md

This document records references considered but rejected because they were non-primary, ambiguous, or unsupported by the project’s evidence standard.

| reference | reason rejected | action |
|---|---|---|
| generic search snippets | not primary-source verified | rejected |
| Google Scholar preview summaries | not authoritative metadata | rejected |
| blog or press coverage | not a primary-source authority | rejected |
| unsupported dataset-card summaries | version ambiguity and no direct source record | rejected |
| `P-PAS` | title/author now resolved (`P-PAS: Prefill-Pressure Adaptive Scheduling for Long-Context LLM Serving`, arXiv:2608.15171) but single-author, very recent (2026-08), not peer-reviewed | moved to `PRIMARY_SOURCE_CITATION_LEDGER.md`'s VERIFIED_RELATED_WORK_ONLY table; not in `verified_related_work.bib` |
| `XPerf` | no primary source located across two independent targeted searches | rejected; re-attempt only if a reviewer or reader supplies an exact citation |
| non-official recommendations from model cards or third-party summaries | insufficient provenance | rejected |
| websites without a formal paper or DOI record | cannot be used as canonical metadata | rejected |
| literature claims that overstate novelty without direct benchmark evidence | violates manuscript safety rules | rejected |

## Corrected in Query 3 (no longer rejected)

- `VTC` — **RESOLVED, no longer rejected.** Exact primary source: `Fairness in Serving Large Language Models` (Sheng, Cao, Li, Zhu, Li, Zhuo, Gonzalez, Stoica; USENIX OSDI 2024; arXiv:2401.00588), which introduces the Virtual Token Counter (VTC) algorithm. Now `PRIMARY_SOURCE_VERIFIED` as `sheng2024vtc`.
- `S^3` — **RESOLVED, no longer rejected.** Exact primary source: `S^3: Increasing GPU Utilization during Generative Inference for Higher Throughput` (Jin, Wu, Brooks, Wei; NeurIPS 2023; arXiv:2306.06000). It is a distinct paper from `Efficient LLM Scheduling by Learning to Rank` (NeurIPS 2024) and must never be substituted for it. Now `PRIMARY_SOURCE_VERIFIED` as `jin2023s3`. See `METADATA_CORRECTIONS.md` for the full resolution record.

## Rule

A rejected reference must have a reason, and that reason must be associated with the candidate list or metadata correction log. This prevents silent citation drift in future manuscript drafting.
