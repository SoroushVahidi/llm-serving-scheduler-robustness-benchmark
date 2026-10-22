# Citation and provenance verification for M3

Checked 2026-10-22. All **21 bibliography entries are cited**, with no duplicate or unresolved keys. Sixteen relevant M2 entries are retained and five foundational entries added. Uncited catalogues are removed rather than padded. The existing PR16 audit remains the complete 43-entry M2 audit; M3 does not overwrite it.

Publisher-deposited metadata and official USENIX/MLSys BibTeX responses are retained in `evidence/citation-metadata.json`. An initial parallel Crossref request hit a rate limit; subsequent bounded requests retrieved the consequential records successfully. Bibliographic identity verification is distinct from proving all results of a source. No full-paper review is claimed where only metadata/abstract/author material was accessible.

| Key | Primary record / verification | Use and correction |
|---|---|---|
| kwon2023vllm | [SOSP DOI](https://doi.org/10.1145/3600006.3613165); deposited author/title/year/pages611–626 | PagedAttention background; not local adaptation fidelity |
| yu2022orca | [Official OSDI22](https://www.usenix.org/conference/osdi22/presentation/yu), BibTeX/pages521–538 | Iteration-level scheduling; original system separated from CM |
| agrawal2024sarathi | [Official OSDI24](https://www.usenix.org/conference/osdi24/presentation/agrawal), pages117–134 | Chunked-prefill throughput/latency precedent; published author form used |
| zhong2024distserve | [Official OSDI24](https://www.usenix.org/conference/osdi24/presentation/zhong-yinmin), pages193–210 | Final publication link replaces preprint link; disaggregation excluded from CM |
| sun2024llumnix | [Official OSDI24](https://www.usenix.org/conference/osdi24/presentation/sun-biao), pages173–191 | Final publication link; migration excluded from CM |
| slai2025 | [POMACS DOI](https://doi.org/10.1145/3771574),9(3),article59,43pages; [author preprint v2](https://arxiv.org/abs/2508.01002v2) | RAD theory versus SLAI heuristic versus restricted adaptation; no transferred guarantee; publication/preprint pairing fixed |
| burstgpt2025 | [KDD25 DOI](https://doi.org/10.1145/3711896.3737413),pages5831–5841 | Dataset identity; consumed successful-request file separately pinned |
| azure2024trace | [Official source description](https://github.com/Azure/AzurePublicDataset/blob/master/AzureLLMInferenceDataset2024.md), verified in PR16 | 2024 conversation source, not Azure2023; consumed file hash pinned; final upstream-version/access check remains author item |
| bailianqwen2026 | [Pinned upstream README](https://raw.githubusercontent.com/alibaba-edu/qwen-bailian-usagetraces-anon/5f7439c51ec248a0c585f7d90a41a6f57773b912/README.md) | **Correction to audit suggestion:** `input_length`/`output_length` are token counts;16-token blocks refer to `hash_ids`. Actual frozen adapter maps lengths directly. License assertion removed from BibTeX note; release-specific permissions remain explicit |
| servegen2026 | [Official NSDI26](https://www.usenix.org/conference/nsdi26/presentation/xiang-servegen),pages1845–1859 | Characterization/generation scope distinguished from fixed-window comparison |
| vidur2024 | [Official MLSys24](https://proceedings.mlsys.org/paper_files/paper/2024/hash/b74a8de47d2b3c928360e0a011f48351-Abstract-Conference.html), official BibTeX volume6,pages351–366 | Profiling/predictive-model validation contrasted with fixed batch timing; no superiority claim. Official BibTeX has no address; none invented |
| llmservingsim2024 | [Primary preprint](https://arxiv.org/abs/2408.05499v1) and [IISWC DOI](https://doi.org/10.1109/IISWC63097.2024.00012),pages15–29 | Final conference/DOI verified; hardware/software simulation contrast |
| papaioannou2024workload | [EuroMLSys DOI](https://doi.org/10.1145/3642970.3655823),pages39–46; [authors' presentation](https://thaleia-dimitradoudali.github.io/docs/2024_EuroMLSys_Presentation_Konstantinos.pdf) | Direct precedent for workload-choice sensitivity; M3 makes no priority claim for discovering workload dependence |
| zakay2014resampling | [Journal DOI](https://doi.org/10.1002/cpe.3240),26(12):2079–2105 | Trace structure/resampling precedent, not a proof that these windows are IID; conference duplicate omitted |
| demsar2006comparisons | [Official JMLR](https://jmlr.org/papers/v7/demsar06a.html),7:1–30, verified in PR16 | Established multiple-algorithm comparison context; not an interaction test or new inference borrowed for C01 |
| benjamini2001dependency | [Annals DOI](https://doi.org/10.1214/aos/1013699998),29(4):1165–1188, metadata checked | BY threshold/dependence context; valid component p-values still required |
| sargent2013 | [Publisher record](https://www.tandfonline.com/doi/abs/10.1057/jos.2012.20),Journal of Simulation7(1):12–24; deposited metadata | Added verification/validation distinction. Volume year2013, not publisher site's later online-platform date2017 |
| benjamini1995 | [Publisher record](https://academic.oup.com/jrsssb/article/57/1/289/7035855),JRSSB57(1):289–300 | Added original BH attribution and inclusive step-up definition |
| holm1979 | [Original journal record](https://www.jstor.org/stable/4615733); [scan of original article](https://sci2s.ugr.es/keel/pdf/specific/articulo/0052_001.pdf),Scandinavian Journal of Statistics6(2):65–70 | Added sequential-rejection definition. JSTOR shell access limited; original article scan/title/page header checked; no DOI invented |
| hoeffding1963 | [Publisher record](https://www.tandfonline.com/doi/abs/10.1080/01621459.1963.10500830),JASA58(301):13–30, deposited metadata | Added bounded independent-sample inequality; not applied to dependent trace windows |
| maurer2009 | [Official COLT paper](https://www.cs.mcgill.ca/~colt2009/papers/012.pdf), [primary arXiv](https://arxiv.org/abs/0907.3740) | Added empirical-Bernstein basis; two-sided union accounting and finite looks stated. Cited as conference-presented primary paper without inventing publisher/address/pagination |

## Disposition of audit-flagged unused references

M3 drops Mooncake, S3, KVCache-in-the-Wild, SCORPIO, LLMServingSim2.0 and other unused catalogue entries. Thus their old mismatched version links, unresolved DOI, wrong entry type or incomplete author list are not propagated. This is not a claim that those works are unimportant or incorrect; none is needed to support the narrowed manuscript's specific claims. Corrected final URLs and metadata are used for every retained entry where the audit requested them.

## Official journal requirements

The [ToMPECS author-guidelines URL](https://dl.acm.org/journal/tompecs/author-guidelines) and [ACM submissions URL](https://www.acm.org/publications/authors/submissions) returned403 on this check. Current journal-specific format, anonymity and declaration instructions therefore remain **unverified**. Building two standard ACM layouts does not resolve that status. No page limit is stated or inferred.

## Source-attribution boundary

Raw trace hashes and adapter identities establish what was consumed; they do not establish common tokenizer semantics, independent providers or current redistribution permission. The pinned Bailian README supports direct token-length interpretation and describes its Apache2.0 licensing; M3 nevertheless leaves final exact-artifact redistribution clearance to the author. Historical registry keys containing “faithful” are not used as fidelity certifications.
