> **Current revision:** see [major-revision/FINAL_REPORT.md](major-revision/FINAL_REPORT.md), [focused claims](major-revision/CLAIM_TO_EVIDENCE.md), and [remaining blockers](major-revision/REMAINING_BLOCKERS.md). Earlier reports below are historical.

> **Historical reference check.** The current 24-reference bibliography is documented in [PR20 reference updates](final-review/REFERENCES.md); consumed-source license/identity verification is superseded by [SOURCE_PROVENANCE.md](artifact-release/SOURCE_PROVENANCE.md).

# Reference and provenance checks

This records the original PR #19 rewrite. The [final review](final-review/REFEREE_REPORT.md), [reference audit](final-review/REFERENCES.md), and [final validation](final-review/VALIDATION.md) supersede it for the stacked correction.

Checked 2026-10-22. M3 has 20 bibliography entries and 20 cited keys, with no unresolved or unused key. Primary publication pages, original papers, official dataset documentation, and publisher-deposited DOI metadata were used. A successful metadata check is not described as full-paper access.

| Key(s) | Primary check and M3 disposition |
|---|---|
| `kwon2023vllm` | [Original paper](https://arxiv.org/abs/2309.06180) and publisher DOI metadata for [SOSP paper](https://doi.org/10.1145/3600006.3613165); title/authors/year and pages 611–626 checked. Claims concern PagedAttention, not this adaptation's fidelity. |
| `yu2022orca` | [OSDI 2022 record](https://www.usenix.org/conference/osdi22/presentation/yu), including BibTeX and pages 521–538. |
| `agrawal2024sarathi` | [OSDI 2024 record](https://www.usenix.org/conference/osdi24/presentation/agrawal), chunked prefill/stall-free scheduling and pages 117–134. |
| `zhong2024distserve` | [Final OSDI record](https://www.usenix.org/conference/osdi24/presentation/zhong-yinmin), pages 193–210. Final URL uses `zhong-yinmin`; the shorter guessed slug failed and is not retained. |
| `sun2024llumnix` | [Final OSDI record](https://www.usenix.org/conference/osdi24/presentation/sun-biao), pages 173–191; migration is context, not an evaluated action. |
| `slai2025` | [Original authors' paper](https://arxiv.org/abs/2508.01002v2) and [POMACS DOI](https://doi.org/10.1145/3771574) metadata: volume 9(3), article 59, 43 pages. RAD theory, SLAI, and the restricted adaptation are distinguished. |
| `burstgpt2025` | [KDD DOI](https://doi.org/10.1145/3711896.3737413), publisher metadata pages 5831–5841, and PR #16 version audit. The KDD 2025 publication and 2024 preprint are not mistaken for different works. Consumed-file identity is separate. |
| `azure2024trace` | [Official Azure 2024 documentation](https://github.com/Azure/AzurePublicDataset/blob/master/AzureLLMInferenceDataset2024.md), verified by PR #16; M3 pins the actual consumed file hash rather than treating a mutable page as the acquired artifact. |
| `bailianqwen2026` | [Pinned upstream README](https://github.com/alibaba-edu/qwen-bailian-usagetraces-anon/tree/5f7439c51ec248a0c585f7d90a41a6f57773b912) and the frozen local adapter. Dataset release terms still require the author to confirm the intended distribution. See the clarification below. |
| `papaioannou2024workload` | [EuroMLSys DOI](https://doi.org/10.1145/3642970.3655823) metadata and [authors' presentation](https://thaleia-dimitradoudali.github.io/docs/2024_EuroMLSys_Presentation_Konstantinos.pdf). Explicit close precedent, not a claim that workload sensitivity is new. Publisher full text was not available. |
| `zakay2014resampling` | [Extended journal DOI](https://doi.org/10.1002/cpe.3240), primary identity verified by PR #16. Retained in place of duplicating the 2013 conference version. Does not justify IID trace-window inference. |
| `servegen2026` | [NSDI 2026 publication](https://www.usenix.org/conference/nsdi26/presentation/xiang-servegen), title/authors/year and pages 1845–1859. Workload generation is contrasted with fixed-corpus comparison. |
| `vidur2024` | [MLSys proceedings](https://proceedings.mlsys.org/paper_files/paper/2024/hash/b74a8de47d2b3c928360e0a011f48351-Abstract-Conference.html) and its official BibTeX export: volume 6, pages 351–366. Profiling/predictive objective is explicit. |
| `llmservingsim2024` | [Original preprint v1](https://arxiv.org/abs/2408.05499v1), authors/title and HW/SW co-simulation scope. M3 cites this identified version, rather than retaining unverified final IISWC publication details. |
| `sargent2013` | [Journal DOI](https://doi.org/10.1057/jos.2012.20), publisher search record and DOI metadata: Journal of Simulation 7(1), 12–24. Full-text fetches were blocked; no claim of complete full-text review. The citation supports the verification/validation distinction, not CM-0.1 adequacy. |
| `benjamini1995` | [Original publisher record](https://rss.onlinelibrary.wiley.com/doi/10.1111/j.2517-6161.1995.tb02031.x), including independent-test-statistic guarantee and bibliographic metadata 57(1), 289–300. Added as the direct BH source. |
| `benjamini2001dependency` | [Original Annals DOI](https://doi.org/10.1214/aos/1013699998), identity and author-hosted paper checked in PR #16. Direct page extraction was limited in this turn. Valid marginal p-values remain a prerequisite. |
| `holm1979` | [Original journal identity](https://www.jstor.org/stable/4615733) plus [scan of the original six-page paper](https://sci2s.ugr.es/keel/pdf/specific/articulo/0052_001.pdf); 6(2), 65–70. Original title/author/year retained. |
| `hoeffding1963` | [Original DOI](https://doi.org/10.1080/01621459.1963.10500830), publisher-deposited metadata: JASA 58(301), 13–30. Full publisher fetch blocked; formula and attribution also agree with the original STAT01 protocol and the COLT primary paper. |
| `maurer2009` | [Original COLT paper](https://www.cs.mcgill.ca/~colt2009/papers/012.pdf) and [authors' preprint](https://arxiv.org/abs/0907.3740). Theorem 4 supplies the empirical Bernstein basis; two-tail and finite-family union accounting is explicit in the appendix. The nine-page proceedings paper is identified without inventing a publisher/location. |

Publisher-deposited metadata retrieved programmatically is recorded in `evidence/reference-metadata.json` and `reference-metadata-additional.json`. Known optional BibTeX advisories remain for Vidur's address and COLT's publisher/address; no title, author, year, identifier, or claimed publication status is missing. These are not unresolved citations.

## PR #16 corrections implemented

The retained literature has explicit contribution/assumption comparisons, including workload choice, predictive simulation, and original statistical procedures. Unneeded M2 catalogue entries are removed rather than carried forward uncited. This also removes the unused SCORPIO incomplete author list, Mooncake published/preprint mismatch, S3 unresolved DOI, KVCache proceedings-as-journal type, LLMServingSim2 unverified final metadata, and named-but-uncited future-policy digressions. These removed works are not cited for a retained claim. The foundational verification and statistical references requested by the audit are added.

## Bailian field-mapping clarification relative to the audit

PR #16 requested a “block-to-token transformation” disclosure. The frozen consumed loader does **not** multiply `input_length` or `output_length` by 16. `src/robustbench/workloads/external/adapters/bailian.py:95–96` casts those source fields directly to integer token counts. The same adapter documents `hash_ids` as 16-token KV/prefix blocks; `scripts/build_stage0_windows.py:162–164` instantiates this adapter. The pinned upstream README independently calls input/output lengths token lengths. M3 therefore states the implemented mapping and separates the hash-block unit. Inventing a ×16 length conversion merely to match an audit phrase would be incorrect. No loader, input, or frozen outcome was changed.

## Official venue checks

The [ToMPECS author-guidelines page](https://dl.acm.org/journal/tompecs/author-guidelines) and [general ACM submissions page](https://www.acm.org/publications/authors/submissions) returned HTTP 403 through the browsing tool. This does not establish a format or page limit. Journal-specific instructions remain unverified and appear conspicuously in the manuscript and blockers checklist.
