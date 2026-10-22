# M3 pre-rewrite scientific and editorial audit

**Audit date:** 2026-10-22. **Disposition:** revision planning only; no manuscript rewrite or experimental work.

**Authoritative M2:** branch `manuscript/lssp-tompecs-m2`, commit `880a37e8e7c19d089be124291e288269966a9147`. Locations below refer to this version. `sections/foo.tex:Lx–Ly` means `paper/tompecs-m2/revised/sections/foo.tex`, inclusive lines; `main.tex` and `references.bib` mean the files in `revised/`. These locations are intended to remain stable even after M3 is created elsewhere.

**Audit scope and epistemic status.** The complete M2 main file, all eleven section files, and all 43 bibliography entries were read, together with the M2 referee report, statistical audit, claim changes, RQ alignment, validation record and relevant evidence tables. The frozen C01, C01-FULL and STAT01/recovery protocols and documented launch evidence were inspected. Earlier LSSP material and the abstracts/contributions of related local manuscripts were examined where needed for overlap. Citation contexts were checked individually; bibliographic verification used publisher-deposited Crossref records, official proceedings, author sources and arXiv. This is an independent audit of the supplied materials, not three external human referee reports, a fresh execution of every validator, or certification of every cited paper's proofs. Recorded validation success is distinguished from evidence independently inspected here. No live campaign results or Slurm state were queried.

## 1. Executive verdict

**Scientifically viable after a substantial, focused restructuring; not submission-ready in its present form.** M2 is markedly more accurate than the earlier manuscript. It corrects the reversal count interpretation, recognizes policy-dependent historical service models, separates deterministic verification from replication, and retracts unsupported calibration and native-transfer claims. Those corrections should survive M3. Its present weakness is that the proposed “methodology” is largely established statistics assembled around a historically confounded comparison. Extensive qualifications dominate the paper without supplying a sufficiently clear positive contribution.

**Preferred direction: C, an integrated paper with B as its empirical center.** Lead with an explicitly defined common-model performance-evaluation question, answer it using the independently validated full frozen corpus when available, and use the historical analysis as a compact motivating and interpretive case. Treat STAT01 as an assessment of inferential procedures under stated synthetic assumptions, not a certificate for historical findings. This recommendation does not presume ranking reversals, favorable calibration, or completed campaigns.

The existing and already-authorized work **should be sufficient to attempt a defensible, bounded submission**, provided full-campaign integrity and analysis checks pass and M3 reports whatever the results show. No additional campaign is recommended. Whether the final empirical findings are substantial enough for ToMPECS remains a judgment after result review. A synthetic fixed-cost model cannot establish production GPU ranking portability; retaining that ambition would require evidence outside the authorized scope. The practical resolution is to narrow the claim, not automatically commission that evidence.

| Referee perspective | Assessment | Acceptance-relevant change |
|---|---|---|
| Novelty and contribution | Workload dependence, metric-dependent rankings, paired comparison, ties and resampling are established. “A reproducible comparison methodology” alone is weak novelty. | Demonstrate what is learned about these four adaptations under an explicit execution contract across the complete finite corpus. Explain why existing serving evaluations and simulators do not already answer that particular question. |
| Methodological correctness | M2 is candid and many historical arithmetic results are reproduced, but historical comparisons mix scheduling and execution semantics. Validity of inference remains distinct from arithmetic fidelity. | Make comparison identities, target quantities, support, selection history and validation levels explicit; keep historical, common-model and calibration results in separate evidence strata. |
| Journal suitability | A principled modeling/performance study is a plausible fit. An audit diary with many counts and little system interpretation is less compelling. | Center the execution model, workload/resource conditions, absolute performance and trade-offs. Journal-specific submission compliance remains partly unverified because official pages blocked access; see §6. |

There are **6 P0 issues, 8 P1 issues and 3 P2 issues** below. P0 means submission blocker, not that every item requires new scientific computation.

## 2. Evidence inventory and campaign boundaries

| Evidence stratum | What is established by inspected records | What is not established |
|---|---|---|
| Historical LSSP | 120 windows, three sources, 13 executed policies, 11-policy primary panel, six regions, 9,360 configurations and 18,720 deterministic passes. M2 evidence reproduces saved analyses and corrects interpretation. | Independent stochastic replications; common service/resource semantics; calibrated historical p-values; native-engine ranking transfer. |
| C01 pilot, [PR #11](https://github.com/SoroushVahidi/llm-serving-scheduler-robustness-benchmark/pull/11) | Execution `9aed0206de66886e9feb0b003b59f0b7dfea68c9`, job 1438638; 144/144 completed and independently validated cells according to the supplied completion evidence and C01-FULL's recorded replay/reuse audit. | Representative full-corpus frequencies. Pilot selection followed historical findings; it is not an untouched confirmatory sample. This audit did not rerun its journals. |
| C01-FULL, [PR #15](https://github.com/SoroushVahidi/llm-serving-scheduler-robustness-benchmark/pull/15) | Frozen target 5,760 cells: 120 × 6 × 4 × 2; 144 compatible pilot cells, 5,616 new. Execution `2d8342e699f35044044ac518c0b75a3c4a1c768c`, launch freeze `22756cee28db386205ebfe03b0cf782d6c64d2e5`. Job 1440402 was last documented RUNNING_HEALTHY at 2026-10-22 15:38:48 UTC. | Present state, completion, final numerical findings or scientific validity. Startup is not a result. |
| STAT01 recovery, [PR #14](https://github.com/SoroushVahidi/llm-serving-scheduler-robustness-benchmark/pull/14) | Execution `1ac4c8dd1421aabad05e6ce243cb911a6ed6c8e1`; original 112,275 studies audited reusable, zero raw studies invalidated; 21,725 missing on the retained stopping plan, target 134,000. Job 1440206 was last documented RUNNING_HEALTHY in the 14:54:04–14:54:07 UTC startup snapshot on 2026-10-22. | Current completion or calibration success. Reuse eligibility is not completion of all added decisions/summaries. Precision stops and maximum-count stops must remain distinct. |

The full common-model protocol preserves CM-0.1: one abstract device, fixed 0.001-second batch cost, shared token budget 32,768, maximum 64 sequences, full 32,768-token reservation per resident, KV capacities 131,072 and 262,144, and horizon last arrival + 50 seconds. Consequently the two capacities permit four or eight fully reserved residents; a nominal 64-sequence cap is not the binding residency limit. Actual occupancy is separately block-accounted. All 200 requests in each window are retained. No eviction, migration, prefix cache, recomputation or native GPU timing is modeled. This is deliberate abstraction, not hardware validation.

The four CM policies are project-maintained adaptations with new identities: `whole_fcfs_c01`, `chunked_fcfs_c01`, `decode_first_c01` and `slo_gated_c01`. In particular, `slo_gated_c01` uses a fixed decode-urgency gate and prompt ordering under its restricted information view; it is not a reproduction of the complete SLAI policy or its theoretical guarantees. Metric-side synthetic deadlines and latent output lengths are not policy-visible information. A theorem about an original algorithm cannot be transferred merely through the adaptation's name.

### Claim–evidence matrix

| Major claim and manuscript location | Current evidence establishes | Legitimate statement after pending validation / limit |
|---|---|---|
| Reproducible corpus and comparisons — abstract; introduction:74–109 | Historical identities and deterministic outputs, with recorded numerical audit agreement. | A reproducible evidence chain after reviewer access and complete artifact checks; not independent physical replication or a new statistical method. |
| Source ranking portability — portability:5–37 | Historical ANWG source-pair Kendall correlations 0.551–1.000 under the old policy–model combinations. | Separate CM source-specific finite-corpus rankings if validated. No isolated provider/domain effect; BurstGPT and Azure are not independent provider interventions. |
| Practical reversals — portability:63–114 | 36/990 records meet the archived rule, spanning five pairs and all involving BurstGPT; classification reproduced in M2 evidence. | CM reversal frequencies under its separately frozen estimands. No historical-reversal persistence claim and no population-significance interpretation of 36. |
| Metric-dependent conclusions — metrics:10–66 | Historical median correlation 0.419, 202/990 negative correlations, 316/990 deterministic-ID agreement and 572/990 maximizing-set intersections; these answer different questions. | Full CM trade-offs and exact-tie/missingness frequencies, with absolute magnitudes. Metric disagreement is not automatically a performance defect or independent statistical evidence. |
| Missingness robustness — metrics:68–108 | Common-window sensitivity retains the reported broad historical pattern; matched support can change individual estimates. | Explicit missing/undefined categories and paired supports. No recovery of unobserved unconditional latency or removal of completion-survivorship bias. |
| Temporal stability and “sample complexity” — robustness:44–108 | Recovery relative to a fixed 40-window ranking and descriptive temporal partitions. | Descriptive CM block/window stability; no independent sample-size requirement or calibrated temporal generalization. |
| Error control / coverage — research_questions:94–149; robustness:157–231 | Historical numerical reproduction and sensitivity to family definitions, not calibrated error control. | STAT01's scenario-specific Monte Carlo estimates/bounds after full validation. No blanket FDR guarantee for historical trace data; post-diagnosis comparisons stay labeled. |
| Isolated scheduling comparison — model:74–104 | Not established by historical paths with policy-dependent work/resources. | Within-CM policy comparisons under equal engine/resource/information rules. Model adequacy remains scoped; no native-engine equivalence. |
| Native or production ranking transfer — limitations:21–48 | Legacy audits leave transfer unverified; related papers' probes concern different questions. | No upgrade from CPU common-model or synthetic calibration results. Remove from promised contributions. |
| Methodological novelty — introduction:21–37; related_work:47–98 | An auditable organization of established methods; no demonstrated new rank statistic or inference theorem. | A specific model-based performance-evaluation contribution, conditional on final insight and positioning; not novelty by collecting more analyses. |

Historical numbers in this matrix are attributed to the preserved M2 audits; this report checks their interpretation and consistency with the text rather than claiming a fresh full numerical reproduction.

## 3. P0 — critical issues before submission

### P0-1. The central comparison and contribution must match the evidence

**Location:** `main.tex:21–43`; `introduction.tex:21–37,74–109`; `model.tex:74–89,165–201`; `conclusion.tex:1–34`.

**Evidence/problem:** Historical instant-prefill and budgeted-prefill paths execute different work, and KV limits bind only selected historical policies. Repeating the simulations exactly verifies these policy–model combinations; it does not isolate scheduling. C01 deliberately supplies a new, shared contract and new policy identities. Its results therefore cannot be substituted into the old 11-policy tables or described as reproducing the original 36 reversals.

**Correction:** Define the paper's main object as ranking stability of four adaptations under CM-0.1. Keep historical implementation-specific results labeled and separately tabulated. State explicitly that model conformance, model adequacy for a question, and physical predictive accuracy are different properties. Require completed coverage and independent analysis validation before inserting C01-FULL findings. If incomplete, describe the exact observed subset and do not claim full-corpus frequencies.

**Resolution route:** clarification/restructuring plus validated ongoing results. No new experiment is required for the bounded common-model claim. Native or universal ranking claims would require new evidence and should be removed instead. **Closure:** every headline claim names its model, policy panel, corpus and metric, and has a corresponding validated evidence row.

### P0-2. Preserve inferential identities and avoid retrospective calibration claims

**Location:** `research_questions.tex:94–149`; `portability.tex:42–69`; `robustness.tex:157–231`; `main.tex:37–42`. Future STAT01 integration is particularly sensitive.

**Evidence/problem:** Saved percentile intervals and bootstrap tail fractions were reproduced, but this is not proof of coverage or p-value validity. Screening before BH changes the family. Thirty of 36 historical primary records have zero bootstrap tail fractions at B=2,000. Neither full-family BH nor BY repairs invalid marginal p-values. Source/policy contrasts overlap; pooled Friedman differences are not an interaction test. The recovery also distinguishes the frozen eight-procedure port from actual historical code: its audit found 31 studies with different historical-source BH decisions. Equality-boundary floating-point implementation fidelity is not ideal mathematical correctness.

**Correction:** Reserve “historical-rule reversal” for the 36 archived records; remove residual “supported” or significance language unless explicitly qualified as that rule. In STAT01, retain eight original identities and stopping rules; label one frozen-source legacy comparator and eight exact-definition comparators as nine post-diagnosis additions. Exact finite-bootstrap probabilities and rational BH/BY/Holm thresholds must not be conflated with legacy binary-floating decisions. Analytic p-values interpreted as exact dyadic values are still approximations to analytic tail probabilities. Report original and expanded uncertainty families separately: `.05/(18*8*16*5)` and `.05/(18*17*16*5)`. Expansion controls the stated finite endpoint family under its assumptions; it does not make the additions prespecified or erase their data-informed selection. Do not transfer synthetic calibration to the 120 historical trace windows or to descriptive C01 results.

**Resolution route:** clarification and existing audit evidence; validated ongoing results only for empirical calibration statements. **Closure:** method IDs, truth definitions, assumptions, endpoint availability, stopping reason and simultaneous-bound family accompany each calibration result; no historical FDR guarantee is inferred from agreement with code or selected scenarios.

### P0-3. Fix the estimand, analysis unit and operational-condition definitions

**Location:** `research_questions.tex:43–91,157–164`; `workloads.tex:89–128`; `metrics.tex:68–108`; `robustness.tex:44–108`.

**Evidence/problem:** Separate observed-support policy means and matched-window differences are different targets. Conditional latency among completions can favor a policy that leaves more requests unfinished. Exact ties are common. The six historical region multipliers are relative to window-specific FIFO calibration; they are not six common absolute loads and are not independently established CM-0.1 saturation regions. Disjoint windows need not be independent, and the 990 historical pair records are not 990 experimental replicates. Finite-reference recovery at n=40 is tautologically perfect and is not population sample complexity.

**Correction:** Define the primary analysis unit as a complete workload window, with load, KV, policy and metric as repeated conditions. Write `lambda(w,r) = c(r) * lambda_FIFO(w)` and report the actual frozen load distribution; call LOW/OVERLOAD etc. inherited region labels when used for CM-0.1. State averaging weights, paired support and conditional metric populations beside results. Retain completion fractions, unfinished counts, exact ties and missingness. Report mean-of-window-p95 separately from a pooled p95. Cross-source windows are not matched by ordinal. Treat chronological blocks descriptively; do not call an ordinary window bootstrap a temporal block bootstrap. Rename sample complexity to finite-corpus ranking recovery.

**Resolution route:** clarification and existing-data reanalysis/reporting; the frozen C01-FULL analysis already specifies most of these rules. No new synthetic studies. **Closure:** every table has a denominator, support rule and unit; no request-level or repeated-condition pseudoreplication, zero imputation of undefined metrics, or population-sampling inference.

### P0-4. Establish a reviewable, versioned evidence chain and trace provenance

**Location:** `main.tex:59–68`; `workloads.tex:33–36,113–128`; `model.tex:31–44,128–151`; `limitations.tex:81–96`.

**Evidence/problem:** The working repository is private; current HF/Zenodo version/access is explicitly unverified. Native physical request records are incomplete. Dataset licenses are asserted more strongly in the design section than the declarations establish. Historical registry keys containing “faithful” are not independent fidelity evidence. Mutable upstream dataset URLs do not identify the consumed bytes. Original source-engine citations do not document the modifications in a local adaptation.

**Correction:** Prepare a compact provenance table linking source release/revision/license, raw file hash, transformations/window IDs, execution commit, contract, adaptation ID and output hash. Provide reviewer access to immutable journals, analysis inputs and reports with pinned environment and verification commands. Preserve historical raw artifacts and identify unavailable records honestly. Cite original algorithms and the project adaptation separately. Resolve redistribution terms from the actual upstream release, rather than treating a paper citation or current repository license as sufficient evidence for every archived file. Archival publication can follow applicable review rules; reviewer access is the immediate requirement.

**Resolution route:** existing-artifact packaging, source/license verification and author confirmation, not new experiments. **Closure:** a reviewer can identify and retrieve the exact evidence supporting each table; access and rights statements are accurate. If particular data cannot be redistributed, document lawful retrieval and hashes or narrow the reproducibility claim.

### P0-5. Update publication overlap and confirm submission status

**Location:** `related_work.tex:47–98`; `workloads.tex:113–128`; `limitations.tex:89–96`; `docs/OVERLAP_LEDGER.md` and `docs/CLAIM_BOUNDARIES.md`.

**Evidence/problem:** The existing overlap ledger is stale relative to local related manuscripts. The module-intervention manuscript explicitly analyzes metric sensitivity, while the ledger says that axis is not examined there. The heuristic-evolution line now has a performance-evaluation manuscript centered on action opportunity and causal headroom, rather than only the old exploitability-gap framing. A different title or new execution model does not itself establish independent textual or experimental contributions. Existing internal records state earlier JSC/PEVA/SMPT versions were rejected, but this is an author declaration rather than independently verified current editorial status.

**Correction:** Update the overlap account during M3 preparation, identify shared code/data and reused historical results, and distinguish whole-policy ranking stability from module causal attribution and one-step headroom. Check exact window/file identities where independence from related papers is claimed. Have the author confirm all related papers' current published/accepted/under-review/withdrawn/rejected/preprint status and supply relevant disclosure in the cover letter. Do not import related papers' native-vLLM findings as validation of C01. See §8 for the precise inspected versions and differences.

**Resolution route:** clarification, existing provenance comparison and author confirmation. No new campaign. **Closure:** accurate status and overlap disclosure, no duplicate headline results, no unverified claim of independent source windows.

### P0-6. Close journal-specific compliance and author declarations

**Location:** `main.tex:1–18,59–78`; `VALIDATION.md`; `evidence/document-validation.json`.

**Evidence/problem:** Successful TeX builds and the recorded under-30-page check do not verify a current ToMPECS page limit. Official journal scope/author pages returned access errors in this audit. Funding, contributions, AI assistance, competing interests and release accessibility still contain author-review placeholders. The available official template supports `acmsmall` for TOMPECS but does not settle all submission settings.

**Correction:** Before submission, obtain the current journal instructions through an accessible official page or submission portal; record format, page/supplement limits, review anonymity, declarations, availability requirements and any applicable publication charges. Confirm declarations and rights information. Do not borrow SIGMETRICS/POMACS or TOMACS rules. Treat 27/28-page M2 builds as descriptive evidence only.

**Resolution route:** administrative verification and author confirmation. No scientific computation. **Closure:** a dated compliance checklist tied to current official instructions, with placeholders resolved. This is a submission gate, not a reason to delay the scientific rewrite plan.

## 4. P1 — important improvements

| ID | Exact location and supporting evidence | Recommended correction |
|---|---|---|
| P1-1 — sharpen novelty | `introduction.tex:21–37,74–109`; `related_work.tex:29–45,62–98`. Papaioannou–Doudali already study workload choice; Zakay–Feitelson study scheduler evaluation under workload resampling; Vidur and LLMServingSim already provide simulation infrastructure. | Replace novelty-by-combination language with a specific unresolved comparison and resulting systems insight. Contrast predictive simulators with a controlled abstraction and conformance referee. Do not claim the first workload-dependent ranking study or a new statistical method. |
| P1-2 — explain model adequacy, not just implementation correctness | `model.tex:45–104,165–201`; C01 `PROTOCOL.md`. Fixed-cost batches and worst-case full-context reservations intentionally reshape the trade-off. | Explain why this abstraction answers an internal comparison question and which real-system mechanisms it omits. Explain the effective four/eight resident limits and fixed timing. Discuss which qualitative conclusions are conditional on those choices; do not equate an event-referee PASS with physical validation. |
| P1-3 — lead with performance magnitude | `within.tex:30–104`; `portability.tex:5–37`; `metrics.tex:10–30`. Rank changes alone can reflect tiny differences or conditional completion. | Present absolute latency/TTFT/TPOT, throughput, completion and goodput with matched-window policy differences, then rank summaries. Distinguish descriptive reversals over windows, source-mean reversals, metric reversals and load/KV changes. Avoid claiming that one factor “drives” variation without a defined decomposition. |
| P1-4 — make ties, missingness and censoring visible | `research_questions.tex:64–91`; `metrics.tex:33–108`; `within.tex:16–22,89–104`. M2 finds 1,010/1,980 tied maximizing sets and 48 zero-completion primary configurations. | Use exact maximizing sets and missing counts in the main display; label deterministic-ID winners as a separate convention. Pair conditional latency with completion fraction and horizon accounting. Keep the original 31.9% ID agreement and 57.8% set intersection as different quantities, not a corrected version of one statistic. |
| P1-5 — remove the audit-diary structure | `introduction.tex:39–72`; `portability.tex:106–114`; `robustness.tex:157–231`; `limitations.tex:21–79`; `conclusion.tex`. Repeated corrections, caveats and arithmetic audits overwhelm findings. | Keep one comparison-scope table and a concise threats section. Move legacy GPU diagnosis, detailed interval replication and claim-history corrections to appendices/artifact. Retain necessary qualifications at claims; remove statements about what earlier wording got wrong from the research narrative. |
| P1-6 — distinguish design history from prospective analysis | `workloads.tex:41–58`; `metrics.tex:126–133`; `robustness.tex:109–155`; C01-FULL protocol. Older windows and outcomes existed before later freezes; policies were selected in light of historical findings. | Say exactly what was frozen before which outcomes. C01-FULL analyses were predeclared before new full-campaign outcomes, while the corpus and adaptations were informed by earlier work. Mark post-hoc SLO and descriptor analyses. Retain null/inconclusive cases and do not select only the most favorable source/metric panels. |
| P1-7 — correct and focus citations | `references.bib`; all contexts enumerated in §7; `model.tex:5–44`. Published/preprint version mismatches, one omitted author, an unverified DOI and unused entries weaken care and attribution. | Correct the identified records; attach citations to mechanism/lineage claims rather than a remote catalogue. Prioritize simulator validation, workload evaluation and the specific statistical definitions actually retained. Remove irrelevant unused entries rather than adding a long recent-work list. |
| P1-8 — close the RQ-to-result chain | `research_questions.tex:8–32`; `robustness.tex:44–155`; `conclusion.tex:1–34`. Provider/domain isolation, synthetic-to-real transfer and native reproduction are explicitly unanswered. | Use three answerable main RQs (§9). Merge chronological stability into the workload question. Move finite-reference recovery and descriptor associations to supplementary analysis. Remove unanswered old RQs from the promised contribution rather than repeatedly apologizing for them. |

## 5. P2 — optional polishing

| ID | Location | Recommendation |
|---|---|---|
| P2-1 | `portability.tex:137–169`, rank heatmap and full interval table; `robustness.tex` audit tables | Avoid displaying the same 18 correlations twice in the main paper. Keep the detailed nominal interval table in the archive/appendix. |
| P2-2 | `workloads.tex:13–17,63–85`; `limitations.tex:81–89` | Remove unused-source shopping lists and shorten the 400-window classifier digression. Keep engineering token-budget failures only where needed to explain why they do not validate this experiment. |
| P2-3 | `research_questions.tex:43`; captions throughout; `conclusion.tex` | Standardize model/adaptation/source/region terminology and metric direction. Replace “sample complexity” captions and generic calls for future campaigns. End with the actual bounded result, including a null result if that is what the data show. |

## 6. Journal requirements: verified facts versus recommendations

Checks were made on 2026-10-22. Retrieval failures are reported as such, not filled with secondary-site guesses.

| Item | Official source and verification | Consequence |
|---|---|---|
| Journal-specific scope and current author instructions | [ToMPECS aims and scope](https://dl.acm.org/journal/tompecs/aims-and-scope), [author guidelines](https://dl.acm.org/journal/tompecs/author-guidelines), and [journal site](https://tompecs.acm.org/) returned HTTP 403/access blocks. Exact current wording and journal-specific rules were **not verified**. | The fit judgment in §1 is an assessment, not a quotation or certification of current editorial policy. Author must complete this bounded check before submission. |
| ACM journal format | The indexed official [acmart manual, Table 1](https://portalparts.acm.org/hippo/latex_templates/acmart.pdf) explicitly lists TOMPECS under `acmsmall`; the direct PDF fetch was blocked. The same manual describes `manuscript` and `review` options. | Publication-style classification is verified from the official indexed text. It does not establish the journal's required review mode, anonymity or page ceiling. M2 already supports both manuscript and acmsmall builds. |
| Performance-evaluation expectations | Official [SIGMETRICS 2026 CFP](https://sigmetrics.org/sigmetrics2026/call_for_papers.html), overview and Measurement & Applied Modeling track, emphasizes motivated system questions, modeling/measurement, and validation by simulation and/or implementation. | Useful primary evidence of this research community's expectations. It is **not ToMPECS author policy**; its 20-page rule, double anonymity and submission process must not be applied to this journal. No verified source here requires every ToMPECS paper to invent a scheduler or perform GPU experiments. |
| Prior publication / simultaneous submission | Current [ACM policy URL](https://www.acm.org/publications/policies/simultaneous-submissions) also blocked access. | Do not certify compliance based on old policy copies or an assumed percentage of new content. Obtain current rules and author-confirmed related-submission status. |
| Artifact badges and availability | No ToMPECS-specific mandatory badge/release policy was verified. | Recommend immutable reviewer-accessible evidence for scientific reproducibility; do not describe a badge as mandatory or claim an independently reproduced badge. |
| Formatting/length evidence already present | M2 `document-validation.json`: 14 recorded checks passed, including references, labels, citations, unchanged class and PDF checks; `page-counts.json`: 27 manuscript pages, 28 acmsmall pages. | These are recorded build checks, not a fresh M3 build or journal-compliance certificate. Do not use the internal “under 30” condition as an ACM requirement. |

Recommended emphasis for this journal: define the queueing/execution abstraction, resource constraints and policy information before presenting rankings; report the performance consequences and their dependence on conditions. A simulated model can be scientifically useful without claiming hardware accuracy, provided the scope and evidence are explicit. This recommendation is methodological judgment, not a claimed ToMPECS rule.

## 7. Literature and citation audit

### 7.1 Coverage and verification method

There are **43 distinct bibliography entries; 28 are cited and 15 are uncited** in the complete current M2 text. No duplicate keys or unresolved citations were found in the context inventory, consistent with M2's recorded validation. Each cited use was checked for support at the level it claims: serving mechanism, dataset identity, simulation scope or statistical method. Metadata verification does not prove an original algorithm's local adaptation is faithful, nor validate all numerical claims in a cited paper. Published records take precedence over a mismatched preprint link. DOI metadata was checked through publisher-deposited Crossref records where available; a Crossref 404 alone is not proof that an identifier is fabricated.

The table covers every entry. “Matches” means no consequential mismatch found in the checked title/authors/year/source; unverified venue details are explicitly identified. BibTeX key years are internal labels and need not match publication years. Uncited entries are not inherently errors, but cannot support claims until actually cited.

| BibTeX key / current use | Primary verification and support assessment | M3 action |
|---|---|---|
| `kwon2023vllm` — introduction:12; related_work:6 | [SOSP 2023 DOI](https://doi.org/10.1145/3600006.3613165), title/authors/year match; PagedAttention memory-management background is supported. | Retain; distinguish original engine from local `vllm_*` keys and CM adaptations. |
| `yu2022orca` — introduction:12; related_work:6 | [OSDI 2022](https://www.usenix.org/conference/osdi22/presentation/yu) matches Orca and iteration-level scheduling background. | Retain as foundational continuous-batching lineage. |
| `agrawal2024sarathi` — introduction:13; related_work:7 | [OSDI 2024](https://www.usenix.org/conference/osdi24/presentation/agrawal) matches Sarathi-Serve, chunked prefill and throughput/latency motivation. | Retain; do not transfer original performance to CM timing. |
| `zhong2024distserve` — introduction:14; related_work:9 | [Primary preprint](https://arxiv.org/abs/2401.09670) supports prefill/decode disaggregation; checked title/authors match. | Cite final OSDI record when completing metadata; keep as background, not an evaluated local policy. |
| `sun2024llumnix` — related_work:10 | [Primary preprint](https://arxiv.org/abs/2406.03243) supports dynamic scheduling/migration; title/authors match. | Prefer final proceedings link; migration is outside CM-0.1. |
| `burstgpt2025` — introduction:16; related_work:21; workloads:6 | [KDD 2025 DOI](https://doi.org/10.1145/3711896.3737413) and [2024 preprint](https://arxiv.org/abs/2401.17644) identify the same work; publication-year difference is legitimate. | Retain dataset paper plus consumed release/file/license identity. |
| `azure2024trace` — related_work:21; workloads:7 | [Official Azure dataset description](https://github.com/Azure/AzurePublicDataset/blob/master/AzureLLMInferenceDataset2024.md) exists and identifies the 2024 source. | Pin revision and raw-file hash. Do not conflate with Azure 2023 or infer an independent provider from the dataset name. |
| `patel2024splitwise` — introduction:14; related_work:9; workloads:10 | [ISCA 2024 DOI](https://doi.org/10.1109/ISCA59077.2024.00019) matches; phase splitting supported. | Retain system background; a system paper is not a substitute for the specific trace's provenance. |
| `stojkovic2025dynamollm` — introduction:16; workloads:7 | [Primary preprint](https://arxiv.org/abs/2408.00741) matches title/authors and cluster energy/performance focus; the 2025 conference details were not independently resolved here. | Check final HPCA metadata if retained; identify actual trace relationship separately. |
| `sun2025geodistributed` — uncited | [Performance Evaluation DOI](https://doi.org/10.1016/j.peva.2025.102527) matches 2025, volume 170, article 102527. | No necessary role in this bounded comparison; remove unless making a directly relevant resource-allocation claim. |
| `jin2023s3` — related_work:13 | [Official NeurIPS 2023 paper](https://proceedings.neurips.cc/paper_files/paper/2023/hash/3a13be0c5dae69e0f08065f113fb10b8-Abstract-Conference.html) verifies title and four authors. Given `10.5555/3666122.3666913` returned Crossref 404. | Prefer official proceedings URL; verify or omit the unresolved DOI. Do not assert it is fake solely from that lookup. |
| `qin2025mooncake` — related_work:11 | [FAST 2025 publication](https://www.usenix.org/conference/fast25/presentation/qin) verifies the published nine-author title, *Trading More Storage for Less Computation*. Linked [arXiv version](https://arxiv.org/abs/2407.00079) has a different title/author list. | Correct the version/link pairing; the published title in M2 is not itself an error. |
| `sheng2024vtc` — related_work:12 | [OSDI 2024](https://www.usenix.org/conference/osdi24/presentation/sheng) verifies *Fairness in Serving Large Language Models*, authors and pages 965–988. | Retain token-accounting background; no inferred fairness guarantee for the historical implementation. |
| `kvcache_wild2025` — related_work:24 | [ATC 2025](https://www.usenix.org/conference/atc25/presentation/wang-jiahao) verifies title/authors/pages 465–482. Repeated “KVCache Cache” is the real title. | Use `@inproceedings`, not `@article` with a proceedings name as journal. Pin published URL. |
| `ayearinllmserving2026` — related_work:24 | [arXiv](https://arxiv.org/abs/2608.13573) verifies title/authors; preprint status. | Pin version if retained for workload evolution; do not imply peer review or use as evidence about this corpus. |
| `proserve2025` — uncited | [arXiv](https://arxiv.org/abs/2512.12928) verifies title/authors, multi-priority scheduling scope. | Optional only if needed to contrast priority information; otherwise remove. |
| `aptserve2025` — uncited | [PACMMOD DOI](https://doi.org/10.1145/3725394) verifies title/authors, 2025 volume 3(3), article 130. | Add at the explicit excluded-policy lineage statement only if that statement remains; otherwise omit. |
| `llmservingsim2_2025` — related_work:32 | [arXiv](https://arxiv.org/abs/2511.07229) verifies title/authors. Listed IEEE CAL volume/year were not independently established by that page in this audit. | Verify final publisher metadata or cite the exact preprint; contrast model purpose and validation, not just name. |
| `tracelab2026` — workloads:13 | [arXiv](https://arxiv.org/abs/2606.30560) verifies coding-agent workload title/authors. It is not part of this experiment. | Remove the future-source digression and its citation unless directly needed to delimit scope. |
| `servegen2026` — related_work:24 | [NSDI 2026](https://www.usenix.org/conference/nsdi26/presentation/xiang-servegen) verifies title/authors and workload-characterization/generation contribution. | Retain concise context; synthetic generation and frozen historical-window evaluation are different tasks. |
| `vidur2024` — related_work:32 | [MLSys 2024](https://proceedings.mlsys.org/paper_files/paper/2024/hash/b74a8de47d2b3c928360e0a011f48351-Abstract-Conference.html) verifies title/authors; a profiled predictive simulator with its own validation. | Expand the purpose/validation contrast. Do not present CM-0.1 as a more accurate replacement. |
| `llmservingsim2024` — related_work:32 | [Primary preprint](https://arxiv.org/abs/2408.05499) verifies title/authors and HW/SW co-simulation scope; final IISWC bibliographic details need publisher confirmation. | Retain and verify final record; distinguish hardware prediction from contract conformance. |
| `pars2025` — uncited | [arXiv](https://arxiv.org/abs/2510.03243) verifies request learning-to-rank title/authors. | Request ordering is not ranking stability of algorithms; do not add merely because both say “ranking.” |
| `jitserve2025` — uncited; named at model:42 | [NSDI 2026](https://www.usenix.org/conference/nsdi26/presentation/zhang-wei) verifies title/authors/year. | Cite if the named comparison remains. Key suffix 2025 is not a publication-date error. |
| `fastserve2024` — uncited; named at model:42 | [NSDI 2026](https://www.usenix.org/conference/nsdi26/presentation/wu-bingyang) verifies title/authors/year. | Cite the final publication for retained mechanism context; key suffix 2024 need not change. |
| `efficientllmscheduling2024` — related_work:13 | [arXiv](https://arxiv.org/abs/2408.15792) verifies title/authors and learned request scheduling. | Keep if needed for mechanism background; not precedent for cross-algorithm rank inference. Verify final NeurIPS record when finalizing metadata. |
| `slai2025` — related_work:14 | [POMACS DOI](https://doi.org/10.1145/3771574) verifies *Optimal Scheduling Algorithms for LLM Inference: Theory and Practice*, authors and 2025 volume 9(3), article 59. | Distinguish RAD theory, SLAI heuristic, local historical implementation and restricted CM adaptation. Never inherit optimality from the title. |
| `scorpio2025` — uncited | [arXiv](https://arxiv.org/abs/2505.23022) lists Bo Pan, omitted from M2's author list; title also differs by “the” before “Right Requests.” | If retained, correct to the selected version and full authors; otherwise remove unused entry. |
| `libra2026` — uncited | [NSDI 2026](https://www.usenix.org/conference/nsdi26/presentation/ruan-libra) verifies title/authors. | Optional context only; not needed to enlarge a background catalogue. |
| `lmetric2026` — uncited; named at model:42 | [arXiv](https://arxiv.org/abs/2603.15202) verifies title/authors; listed OSDI 2026 venue not independently confirmed here. | Cite at retained name and verify publisher record, or use the explicitly identified preprint. |
| `zakay2014resampling` — related_work:41 | [Journal DOI](https://doi.org/10.1002/cpe.3240) verifies 2014, 26(12), 2079–2105, title/authors. | Retain as foundational workload-resampling precedent. It does not justify IID treatment of LSSP windows. |
| `chen2026quickswap` — uncited | [Performance Evaluation DOI](https://doi.org/10.1016/j.peva.2025.102525) verifies 2026, volume 171, article 102525. DOI-year 2025 is not an error. | Remove unless explicitly needed; no reason to cite solely for journal proximity. |
| `yildiz2026dispatching` — related_work:40 | [Performance Evaluation DOI](https://doi.org/10.1016/j.peva.2026.102551) verifies title/authors, 2026 volume 172, article 102551. | Relevant broader workload-dependent dispatching context; not direct LLM evidence. |
| `li2026beyond` — uncited | [arXiv](https://arxiv.org/abs/2606.18431) verifies title/authors and tail-aware scheduling; listed ICML venue not independently confirmed here. | Optional only for a specific tail/prediction discussion; do not imply verified conference publication. |
| `liu2026hmas` — uncited | [ACL Anthology](https://aclanthology.org/2026.findings-acl.1946/) verifies title/authors/year/pages and DOI `10.18653/v1/2026.findings-acl.1946`. | Multi-agent/multi-tenant context is outside the core; remove unless used. Add DOI if retained. |
| `wang2026smetric` — uncited | [arXiv](https://arxiv.org/abs/2607.08565) verifies title/authors; session-centric scheduling. | Optional scope contrast, not essential for independent 200-request window replay. |
| `wang2026xperf` — uncited | [arXiv](https://arxiv.org/abs/2608.20370) verifies title/authors and agentic serving benchmark. | Cite only if comparing benchmark scope; no priority claim over all LLM benchmarking. |
| `ding2026cclbench` — uncited | [arXiv](https://arxiv.org/abs/2605.06544) verifies title/authors; broader trace-based LLM infrastructure benchmark. | Avoid equating its broader infrastructure coverage with this scheduler estimand. Optional, not mandatory padding. |
| `papaioannou2024workload` — related_work:39 | [EuroMLSys DOI](https://doi.org/10.1145/3642970.3655823) verifies metadata/pages 39–46. [Authors' presentation](https://thaleia-dimitradoudali.github.io/docs/2024_EuroMLSys_Presentation_Konstantinos.pdf) directly studies dataset and inference-scenario choice across serving systems. | Give this close precedent explicit credit. Differentiate fixed-model adaptation ranking, complete matched windows and resource/metric axes; avoid claiming discovery of workload dependence. Publisher full text was blocked, so no exhaustive full-paper comparison is claimed. |
| `bailianqwen2026` — related_work:21; workloads:9 | [Pinned upstream repository](https://github.com/alibaba-edu/qwen-bailian-usagetraces-anon/tree/5f7439c51ec248a0c585f7d90a41a6f57773b912) exists and provides source identity. | Retain commit plus consumed file hash and block-to-token transformation; verify release-specific redistribution terms. |
| `demsar2006comparisons` — related_work:71 | [JMLR 7:1–30](https://jmlr.org/papers/v7/demsar06a.html) verifies title/author/year and multiple-algorithm comparisons across datasets. | Retain if statistical background remains. Its setting does not make closely related windows independent or make Friedman a source-by-policy interaction test. |
| `benjamini2001dependency` — research_questions:145 | [Annals DOI](https://doi.org/10.1214/aos/1013699998), Crossref title/authors/year/29(4):1165–1188 match. Author-hosted paper also inspected; text extraction imperfect. | Retain; distinguish BH under appropriate dependence from BY's adjustment and the prerequisite of valid p-values. |
| `zakay2013resampling` — related_work:62 | [Official ICPE proceedings PDF](https://research.spec.org/icpe_proceedings/2013/proceedings/p149.pdf) supports user-subtrace/activity-cycle resampling. | Conference/journal versions are related, not an accidental duplicate key. Prefer the extended journal citation unless discussing a specifically conference-version detail. |

### 7.2 Missing essentials, rather than a larger bibliography

| Missing work | Verified primary identity | Why / when to add |
|---|---|---|
| Simulation verification versus validation | R. G. Sargent, *Verification and validation of simulation models*, Journal of Simulation 7(1):12–24 (2013), [DOI](https://doi.org/10.1057/jos.2012.20); metadata verified. | Essential framing for independent event conformance versus adequacy for real-system inference. It supports the distinction, not this model's adequacy by citation alone. |
| Original BH definition | Benjamini and Hochberg, JRSS B 57(1):289–300 (1995), [publisher record](https://onlinelibrary.wiley.com/doi/10.1111/j.2517-6161.1995.tb02031.x). | Needed when defining legacy and corrected BH comparisons; BY alone is an indirect citation. |
| Holm definition | Holm, *A Simple Sequentially Rejective Multiple Test Procedure*, Scandinavian Journal of Statistics 6(2):65–70 (1979), [original journal record](https://www.jstor.org/stable/4615733). | Needed if STAT01's Holm procedures appear. This audit retrieved a limited publisher shell; confirm full bibliographic export when adding. |
| Monte Carlo simultaneous-bound basis | Maurer and Pontil, *Empirical Bernstein Bounds and Sample Variance Penalization* (2009), [primary preprint](https://arxiv.org/abs/0907.3740); STAT01 already cites the COLT paper. | Needed for STAT01 integration: show bounded independent study endpoints and finite-look union accounting, not independence among all hypotheses. |
| Bounded concentration procedure | Hoeffding, *Probability Inequalities for Sums of Bounded Random Variables* (1963), [DOI already specified in STAT01](https://doi.org/10.1080/01621459.1963.10500830). | Import the protocol's attribution if bounded-Hoeffding results are discussed; final metadata check remains part of bibliography preparation. |
| Benchmarking/repetition methodology | Kalibera and Jones, *Rigorous benchmarking in reasonable time*, ISMM 2013:63–74, [DOI](https://doi.org/10.1145/2464157.2464160); metadata verified. | Optional useful support for distinguishing sources of variation and repetition. Do not import an uncertainty model into deterministic finite-corpus C01 merely to use this citation. |

No new scheduling-paper catalogue is essential. The present bibliography already covers continuous batching, KV management, scheduling information, predictive simulation, trace provenance, workload dependence and algorithm comparisons. Strengthen the relation to those sources. Temporal block-bootstrap theory is needed only if M3 makes a new inferential claim from such a method; the preferred descriptive common-model analysis does not require adding one.

## 8. Publication overlap and research integrity

This is a targeted conceptual/textual comparison, not a plagiarism-service similarity score. Exact duplicated passages beyond the inspected material were not exhaustively enumerated.

| Related material / inspected identity | Substantial overlap and distinction | Status and required action |
|---|---|---|
| Earlier LSSP JSC `b1f9a12021c25dff8ad7cc06ff9654b6a047c132`, PEVA `097547206b6e99286553f43190bfa14c5b542b35`, SMPT `cc25fcd14f6fe28ab30d9e46635a72c0d6285d00`; M1 `366752a76f86dec30190f3e7767124f684378de4` | Same historical campaign and many results/definitions, not fresh independent experiments. Original `paper/main.tex` had claims later corrected by M2, including reversal interpretation and native reproduction. | `paper/tompecs-m1/AUTHORITY.md` records the author's statement that JSC/PEVA/SMPT were rejected and none active. Rejected versions are not equivalent to prior peer-reviewed publication. Confirm current status and disclose any public versions or material editorial history where requested. Never revive superseded claims. |
| Heuristic-evolution local HEAD `327736bc07c79e9ac6a1f233473f5a289ca4438a`, `paper/performance_evaluation/main.tex:34–170` | Current title: *When Does LLM-Serving Scheduler Adaptation Matter? Action Opportunity and Causal Headroom in Production-Derived Replay*. Shares replay, policies, capacity/load axes, ANWG and workload-conditioned outcomes. Its main object is executable action opportunity and one-step counterfactual headroom, including concentrated effects and a bounded vLLM probe. LSSP's whole-window ranking object is different. | Directory/title/venue labels do not prove submission status. Author confirmation needed. Do not claim resource-pressure dependence, metric sensitivity or “no new scheduler” positioning as unique in isolation. Do not reuse its headroom/native findings as LSSP evidence. |
| Module-intervention local HEAD `ffae40a1d470624b3dc1da7c48673b12c6556152`, `paper/sections/abstract.tex` and `intro.tex` | Shares simulator/trace machinery, ANWG, request-level consequences and metric sensitivity. Its contribution is typed module transplants, downstream erasure, fidelity and counterfactual attribution. The abstract now reports a 3,940-cell metric-sensitivity analysis, contradicting the older ledger's claim of no such formal axis. | Current publication/submission status unknown. Update the ledger; distinguish whole-policy rankings from within-policy mechanism attribution. Its real-vLLM campaigns do not validate C01's full policy rankings or fixed timing. |
| Earlier 60-window public replay/load scaling, documented in `docs/OVERLAP_LEDGER.md` | 20 BurstGPT + 20 Azure-2023 conversation + 20 Azure-2023 code, 200 requests, eight policies, grid `{1,2,4,8,16,32,64,128}`. The historical ledger records a v1 horizon bug and only a visible v2 lambda=1 gate, not an independently rederived corrected full-grid result. | Do not republish the old sweep as new. LSSP uses Azure 2024/Bailian and a different design, but exact cross-project BurstGPT window overlap is unresolved. “Different seed” is not proof of disjoint data or statistical independence. A narrow manifest comparison can resolve this without new experiments. |
| HF dataset / Zenodo / local submission packages | Shared infrastructure, publicly released artifacts and preprints need attribution; a release is not necessarily a peer-reviewed article. | Verify actual versions, accessibility, licenses and any accompanying publication. No accepted/published status was established merely by finding these files. |

The author should provide one short status ledger covering all related titles, venue, submission ID/date if applicable, current disposition and public identifiers. The paper/cover letter should then state what code, windows and results are reused. No contacting editors or coauthors is authorized by this audit; nothing was sent.

## 9. Recommended narrative and contribution statement

### 9.1 Compare the three options

| Option | Strength | Risk | Verdict independent of unfinished outcomes |
|---|---|---|---|
| A — methodological ranking portability / historical limitations | Can be written from completed historical evidence and audits; offers a transparent cautionary case. | Established methods, policy–model confounding and repeated qualifications leave modest methodological novelty. | Credible fallback archival case study, weaker primary ToMPECS pitch. Do not promise a new inference method. |
| B — common-model performance evaluation | Coherent system object, explicit resources/information, controlled adaptation comparison, absolute performance and finite-corpus ranking analysis. | CM-0.1 is restrictive; findings may be null, saturated or mostly tied. Full results are not yet established. | Strong empirical center if complete and validated; no need to assume reversals. |
| C — integrated historical + common-model evidence | Explains why the shared contract matters, gives historical evidence a bounded role, and connects comparability to performance evaluation. | Can become three papers stapled together if all historical audits and calibration tables remain in the main text. | **Preferred: B as the main study; A as a compact motivation/case; STAT01 as a scoped inference diagnostic.** |

**Central research question:** Under a fixed execution, resource and policy-information contract, how stable are the relative and absolute performances of four LLM-serving scheduler adaptations across the frozen workload windows, inherited load settings, KV capacities and metric definitions?

**Four principal contributions, conditional where results remain unfinished:**

1. An explicit, auditable comparison contract separating policy intent from executed work and separating historical implementations from the four evaluated adaptations. This is an engineering/methodological contribution, not a novel scheduler or proof of native fidelity.
2. A complete finite-corpus performance evaluation across 120 windows, six inherited load settings and two KV capacities, with absolute metrics and matched policy differences **[insert only after validated full coverage]**.
3. A descriptive characterization of ranking stability, exact ties, missingness, practical reversals and performance trade-offs across source, operating condition and metric axes **[report actual validated outcomes, including zero reversals]**.
4. An evidence audit explaining what the historical comparison and inference pipeline can establish, with separately identified synthetic calibration results **[if complete and independently reviewed]** and a reproducible evidence chain.

The answer to earlier novelty criticism is not “we now use more methods.” It is: the paper resolves a specific comparison ambiguity using a transparent model and reports the resulting system-performance facts across a defined corpus. The scientific contribution depends on the insight and clarity of those facts; the event referee and artifact are supporting contributions.

### 9.2 RQs and historical material

Use three main questions:

1. **RQ1 — workload and operating conditions:** How do absolute performance and pairwise adaptation differences vary across windows, sources, inherited load settings and KV capacities? Include chronological/block descriptions here.
2. **RQ2 — ranking and metric choice:** Where do rankings agree, tie, become undefined or reverse by the predeclared practical threshold, and how does metric choice change the interpretation? Include mean/tail/throughput/completion/goodput trade-offs.
3. **RQ3 — interpretation boundaries:** Which comparisons are invariant to the specified reporting conventions, and what do historical execution and inference audits imply about interpreting these rankings? Keep calibration a bounded subsection, not a promise of universally valid inference.

Merge M2 Q1 and Q4's temporal component into RQ1; merge Q2/Q3 into RQ2. Keep finite-40-window recovery as an optional appendix, not a sample-size recommendation. Drop the old unanswered provider/domain isolation, synthetic-to-real transfer and native reproduction questions from the claimed scope. Descriptor prediction is supplementary descriptive material, not causal explanation or an online selector.

**Historical material in the main paper:** a compact policy–model comparability table; historical sample/metric definitions; the descriptive source-correlation range and properly qualified 36/990 historical-rule count if they motivate the comparison; one tie/missingness example. **Appendix/artifact:** full 13-policy tables, 18 nominal interval rows, detailed multiplicity variants, 66 Friedman audits, legacy physical-engine diagnosis, sample-recovery curves, SLO post-hoc analysis and descriptor fits. No historical number should be overwritten by a common-model result. If a historical result is not used to advance the argument, it can remain only in the artifact.

## 10. Section-by-section M3 rewrite blueprint

### 10.1 Candidate titles and abstract structure

Possible titles, with no result-dependent assertion:

1. **Ranking Stability of LLM-Serving Scheduler Adaptations Under a Shared Execution Model**
2. **Comparing LLM-Serving Schedulers Across Workloads, Resource Limits, and Metrics**
3. **From Historical Comparisons to Common-Model Evaluation of LLM-Serving Schedulers**

Proposed abstract structure (not a replacement abstract):

1. Problem: comparative rankings depend on both workload/metric and the execution contract; identify the particular ambiguity being studied.
2. Method: name CM-0.1's synthetic CPU discrete-event scope, four adaptations, three sources, 120 windows, six inherited load settings and two KV capacities; explain equal-window descriptive analysis.
3. Results: **[validated completed-cell count]**, **[absolute performance/trade-off finding]**, **[ranking/tie/missingness/reversal findings with denominators]**. Do not fill from startup observations or predict a preferred result.
4. Interpretation: contrast with **[qualified historical finding]**; optionally include one **[validated STAT01 conclusion under its assumptions]** if essential to the narrative.
5. Scope: finite-corpus behavior under a shared abstraction, with traceable validation; no native-engine ranking or general calibration claim.

### 10.2 Proposed organization and disposition of every M2 section

| M3 section | Current material and exact editorial action | Purpose / transition |
|---|---|---|
| 1. Introduction | Compress `introduction.tex` to problem, gap, central question, bounded contributions and principal validated findings. Remove repeated defenses. | End by saying the paper first establishes the comparison object, then evaluates it. |
| 2. Background and prior comparisons | Rework `related_work.tex`; foreground workload-choice, predictive-simulator and algorithm-comparison precedents. Add a short historical LSSP case from `model.tex`/`portability.tex`. | Explain why matching trace names and policy names is insufficient to identify a comparison. |
| 3. Common execution model and adaptations | Promote the CM-0.1 contract; preserve a small historical-vs-CM table. Move old implementation-detail catalogue and GPU failure history to appendix. | Define what changes between policies and what is fixed before any performance claim. |
| 4. Corpus, design, estimands and validation | Combine necessary `workloads.tex` and `research_questions.tex`. Include lineage, freeze chronology, absolute loads, whole-window unit, support, metric direction, strict practical threshold, ties and missingness; state referee and independent-analysis checks. | Translate the model into a finite, reproducible evaluation matrix. No long detour through every historical statistical calculation. |
| 5. Absolute performance and workload/resource dependence | Replace the role of `within.tex` with validated full CM results; integrate source/load/KV parts of `portability.tex`. | Show magnitudes and trade-offs before converting them into ranks. Retain negative and tied conditions. |
| 6. Ranking stability and metric trade-offs | Integrate `metrics.tex`, practical-reversal analysis and chronological descriptive sensitivities. Show matching/denominators explicitly. | Explain when different summaries change the practical interpretation, without claiming an independent source/metric causal decomposition. |
| 7. Historical and inferential interpretation | Condense historical `robustness.tex` into the pertinent comparison/inference lessons. Add a short, separately scoped STAT01 summary only after validation; put full scenario/method tables in supplement. | Distinguish historical arithmetic, finite-corpus description and synthetic calibration rather than use one to certify another. |
| 8. Discussion and limitations | Consolidate `limitations.tex` with practical implications: model abstraction, adaptation selection, corpus provenance/dependence, conditional metrics and external validity. | Explain what a reader can transfer and what remains conditional; avoid rehearsing every past development error. |
| 9. Conclusion | Replace `conclusion.tex`'s inventory with direct answers to the three RQs and the strongest supported conclusion. | No unsupported universal winner/instability claim and no open-ended list of new campaigns. |
| Artifact/declarations + appendices | Resolve `main.tex:59–78`; retain detailed historical analysis/validation and calibration definitions outside the main argument. | Make evidence reviewable without requiring a reader to reconstruct the project history. |

### 10.3 Figures and tables

Recommended core displays, to be populated only from verified final summaries:

- **Figure 1: comparison identity and validation chain.** Historical policy–model combinations versus fixed CM-0.1 engine with four adaptation modules; arrows from frozen inputs to journals, referee, metrics and independent analysis. No arrow implying hardware validation.
- **Figure 2: absolute performance across conditions.** Small multiples by source and KV capacity, inherited load on the horizontal axis, consistent policy colors. Separate latency/tail, throughput/completion and goodput panels; indicate undefined endpoints and horizon censoring. Publish all endpoints in supplementary tables.
- **Figure 3: matched-window policy differences.** Window distributions or all-window dot/ECDF displays for the predeclared endpoints; show zeros and practical thresholds. These are descriptive displays, not confidence intervals.
- **Figure 4: ranking and reversal summary.** Exact-tie and undefined categories, source/load/KV/metric panels with explicit eligible and total denominators. Keep source-mean and cross-window pair summaries visibly separate.
- **Figure 5, if useful: chronological stability.** Early/middle/late or frozen ten-window blocks within each source. Mark unequal durations; no independent-sample or time-series calibration assertion.
- **Table 1: contract and adaptation lineage.** Timing/resource/information differences and source citations; original algorithm, historical implementation and CM adaptation in separate columns.
- **Table 2: design/provenance/coverage.** Windows, requests, loads, capacities, reused/new counts, missing/invalid counts and validation status. Validation evidence belongs beside the matrix, not solely in the appendix.
- **Table 3: claim boundaries and inference summary.** A short historical-versus-CM-versus-STAT01 table; move full calibration grids to the supplement unless a major inference finding warrants a separate figure.

Avoid selecting only “interesting” windows for the main findings. An illustrative example may follow a complete aggregate display if selection is explicitly labeled. Preserve full tabular outputs for every condition.

### 10.4 High-impact sentence/claim edits

These are illustrative local changes for the later rewrite, not edits to the manuscript now.

| Current location / wording or claim | Recommended form and reason |
|---|---|
| `main.tex:23–24`, “We present a reproducible comparison methodology” | “We evaluate four scheduler adaptations under a shared execution and resource contract.” Follow with the actual novel empirical question; avoid suggesting new statistical methodology. |
| `portability.tex:32–37`, range “driven entirely” by source pair rather than region | “In these recorded comparisons, correlations differ more across source pairs than across the six region labels.” This describes the table without claiming identified causal or variance contributions. |
| `portability.tex:63–69`, “Supported” column | “Meets historical margin + nominal-interval rule.” State separately that coverage/FDR are unestablished. |
| `workloads.tex:57–58`, frozen before “any” scheduler outcome | “The expanded-window manifest was frozen before the corresponding campaign outcomes; earlier pilot outcomes already existed.” Specify the actual freeze scope rather than retrospective prespecification. |
| `workloads.tex:103–110`, “block bootstrap” for resampling whole windows | “Bootstrap over whole workload windows.” Reserve chronological/block-bootstrap terminology for the separately defined block scheme. |
| `robustness.tex:97`, “Benchmark sample-complexity” caption | “Recovery of the fixed 40-window reference ranking.” This avoids extrapolation to a population sample requirement. |
| `metrics.tex:33–66`, juxtaposed 31.9% and 57.8% | “Deterministic-ID winners agree in 316/990 comparisons; exact maximizing sets intersect in 572/990.” Both are retained, with their different questions explicit. |
| `model.tex:99–104`, deterministic agreement as validation | “Repeated execution reproduces the recorded model outcomes; independent event checks assess conformance to the declared model.” Neither sentence implies native-engine accuracy. |
| `limitations.tex` / conclusion, repeated “not faithful/native/causal” cautions | State once: “The conclusions concern these adaptations under CM-0.1; GPU timing, migration, preemption and production deployment are outside the model.” Then attach only claim-specific caveats where needed. |

The desired tone is direct: state what was measured, what was found, and the boundary needed to interpret it. Do not hedge reproduced arithmetic unnecessarily; do not use confident causal or universal language for descriptive patterns. Limitations should constrain conclusions, not substitute for them.

## 11. Final-results integration plan

### 11.1 C01-FULL acceptance gate and outcome-dependent wording

After the campaign ends, a separately authorized result review should follow its existing README. Require 5,760 distinct planned identities, compatible reuse provenance for 144 cells, immutable hashes, all event-referee passes, no silent exclusions, and explicit partial/unfinished requests. The recorded prelaunch tests (55 local, 55 pinned Wulver, 164 launch fingerprints) are useful engineering evidence, not final coverage.

Require `complete.json` to contain `EXECUTION_AND_INDEPENDENT_CHECKS_COMPLETE`, and `analysis/independent_analysis_validation.json` to report PASS with 5,760 absolute cell rows, 15,840 complete-or-explicitly-missing ranking records, and 95,040 matched policy/metric differences. Independently inspect the report denominators, metric support, negative/tied cases and source aggregation. A clean Slurm exit or a safe time-budget stop alone does not meet this gate. Do not run those checks or simulations as part of this editorial audit.

| Final outcome | Permissible manuscript treatment |
|---|---|
| Complete, valid, substantial ranking changes | Report exact frequencies and magnitudes under CM-0.1, split by window/source/load/KV/metric estimands. Do not call the historical 36 reversals reproduced: panel, policy identities, model and comparison definition differ. |
| Complete, valid, stable or mostly tied rankings | Report stability/ties and the operating conditions under which differences are negligible or absent. This may be scientifically useful counterevidence to broad historical portability claims. Do not manufacture instability by selecting metrics/windows or imply model realism from agreement. |
| Complete, valid, metric disagreement but little source dependence | State that metric choice, within this design, changes conclusions more visibly than source aggregation; avoid an unperformed causal decomposition. Retain absolute performance and completion support. |
| Conditional metrics missing or horizon censoring substantial | Report coverage and censoring as findings; abstain where rankings are undefined. Do not silently restrict to surviving requests/windows and label the result a complete ranking. |
| Incomplete campaign or integrity failure | Do not present full-matrix claims. If a subset is used, disclose exactly how completion determined inclusion and restrict claims to it. A blocker may prevent the preferred B-centered contribution; do not silently rerun or propose an additional campaign. Seek author decision on a narrower paper. |

Follow the frozen 10% rule exactly, including direction, strict inequality, zero-denominator and missingness behavior. Retain exact ties as primary; the predeclared numerical near-tie sensitivity is secondary. Pair counts across windows are dependent descriptive comparisons, not independent sample sizes. Full-corpus frequencies are not population probabilities.

### 11.2 STAT01 acceptance gate and outcome-dependent wording

Require a final accounting for all 18 scenarios, their original precision/max-count stop reasons, saved arrays/masks, independent batch checks, original failure regression (scenario 11, replicate 6628), exact historical-source equivalence, and distinct rational-definition tests. Recovery's reuse audit establishes raw-data compatibility, not that the full 17-method campaign is finished. Verify the 112,275 reused plus 21,725 missing inventory against the final target and distinguish additions recomputed on reused raw data from new synthetic studies.

Keep practical-reversal truth and sign-reversal truth separate. Report FDR/FWER/coverage/power and interval availability by scenario; do not average diagnostic and assumption-valid scenarios into a global pass. The simultaneous-bound allocation and availability denominators must match the selected summary family. Original precision stops at 2,000 studies for scenario 3 and 4,000 for scenario 17 are not to be relabeled failures to reach 8,000; the other 16 scenarios have 8,000 as their retained final planned look.

| Final outcome | Permissible manuscript treatment |
|---|---|
| Historical methods show inflated error or poor coverage | Present a calibration limitation in the tested synthetic scenarios. Historical 36/990 remains an archived-rule count, not statistically established population reversals. This does not invalidate descriptive C01 tables. |
| Some mathematically defined methods behave compatibly under assumptions | State which assumptions/scenarios and the simultaneous bounds. Empirical compatibility is not universal mathematical proof; oracle covariance is not a generally deployable method. Correct threshold arithmetic cannot rescue invalid p-values or selection-biased targets. |
| Legacy and exact methods differ only at boundaries | Report the implementation distinction and frequency without conflating fidelity with ideal correctness. Preserve both identities; do not silently retrofit historical results. |
| Bounds remain inconclusive or methods abstain | Report inconclusiveness and availability. High abstention or conservative power is a result, not a reason to change thresholds after seeing outcomes. No calibration-success claim. |
| Recovery incomplete or invalid | Retain M2's unestablished-calibration statement; omit empirical calibration conclusions. A descriptive common-model paper can still be viable if it does not rely on those guarantees. |

The nine post-diagnosis comparisons are useful diagnostics but not retrospectively prespecified. Original eight-procedure values can remain comparable to their frozen definitions without all eight being equivalent to the original historical source implementation. The amendment's additional exact historical-source comparator is essential to that distinction.

## 12. Submission-readiness checklist and bounded next steps

No new campaign is part of this blueprint. Recommended sequence after author review:

- [ ] Author approves the B-centered integrated narrative, three RQs and explicit synthetic-model scope. **No experiment.**
- [ ] At a later requested result review, establish final C01-FULL coverage, identity/referee checks and independently recomputed analyses; interpret all outcomes, including ties/nulls. **Review of already-running work.**
- [ ] Review STAT01 final validation, stop reasons, method identities and simultaneous uncertainty; otherwise retain “calibration unestablished.” **Review of already-running work; not a prerequisite for descriptive C01 validity.**
- [ ] Resolve source licenses, reviewer access, immutable release identities and exact related-corpus overlap where independence is claimed. **Existing-data/documentation work.**
- [ ] Author confirms related-paper status and disclosure, funding/contributions/AI statements, and current official ToMPECS instructions. **Administrative/documentation work.**
- [ ] Rewrite M3 only after authorization, with no selective omission of unfavorable results; correct the listed citations and update prior-work contrasts. **Editorial work.**
- [ ] Generate figures/tables from verified saved reports, cross-check all headline numbers and denominators, and compile/check the final document in the confirmed submission format. **Existing-data analysis and document validation.**
- [ ] Conduct one final claim-to-evidence and overlap review before submission. **Review, not another experiment.**

**Critical gap assessment:** No mandatory additional experimental gap has been established for the narrowly scoped common-model paper. The outstanding scientific gate is whether the authorized full-corpus outputs are complete, valid and informative enough to support the selected claims. Physical ranking transfer, causal provider/domain effects and general-purpose calibrated inference remain outside available evidence; removing those claims is a legitimate resolution. If the final corpus is mostly uninformative under CM-0.1, acceptance prospects may remain limited despite impeccable execution. That is an author decision about scope and contribution, not automatic authorization for more work.

## 13. Exact supporting evidence and reproduction pointers

### M2 and historical evidence

All following paths are in this repository at the M2 base identified above:

- `paper/tompecs-m2/revised/main.tex`, `revised/sections/*.tex`, `revised/references.bib`.
- `paper/tompecs-m2/M2_REFEREE_REPORT.md`, `M2_STATISTICAL_AUDIT.md`, `M2_CLAIM_CHANGES.md`, `M2_RQ_ALIGNMENT.md`, `VALIDATION.md`.
- `paper/tompecs-m2/evidence/statistical-audit.json`, `additional-checks.json`, `input-source-hashes.json`, `within-region.json`, `primary-reversal-intervals.json`, `ranking-intervals.json`, `multiplicity-families.json`, `friedman-audit.json`, `chronological-block-sensitivity.json`, `cross-metric-sets-and-matched.json`, `matched-pairwise-changes.json`, `document-validation.json`, `page-counts.json`, `package-check.json`, `literature-and-venue-check.json`.
- `paper/tompecs-m1/AUTHORITY.md`, `paper/tompecs-m1/evidence/submission-versions.json`, `paper/main.tex`, `paper/sections/artifact.tex`.
- `docs/OVERLAP_LEDGER.md`, `docs/PROVENANCE.md`, `docs/CLAIM_BOUNDARIES.md`, `docs/EVIDENCE_INDEPENDENCE_PLAN.md`, `docs/DATA_LICENSE_AUDIT.md`.

The recorded M2 preservation audit covers 571 inherited files and identifies historical consolidated SHA-256 `73adf7d97f06985ec8f8e1c2f794fd43178433eb198e1c00705e817f4bde9c26`. This report does not replace those preservation records or rerun the historical campaign.

### C01 and C01-FULL protocol/evidence

- Pilot checkout: `/home/soroush/repos/llm-serving-scheduler-lssp-c01/research/lssp-c01/PROTOCOL.md`; original Wulver root `/project/ikoutis/sv96/github/llm-serving-scheduler-lssp-c01-3c8e2d6/`, run `runs/c01-30f3af3717d536cb/`.
- Full checkout: `/home/soroush/repos/llm-serving-scheduler-lssp-c01-full/research/lssp-c01-full/` containing `PROTOCOL.md`, `README.md`, `REUSE_AND_REVIEW.md`, `input_manifest.json`, `LAUNCH_REPORT.md` and `evidence/`.
- Full reuse/test records: `evidence/pilot_audit.json`, `reuse_audit.json`, `reuse_index.json`, `local-tests.txt`, `wulver-final-tests.txt`, `wulver-prelaunch.txt`, `unchanged-contract.diff` beneath that directory.
- Full deployment: `/project/ikoutis/sv96/github/llm-serving-scheduler-lssp-c01-full-20261022/`.
- Full checkpoint: `runs/c01-full-167b9074e5711420/checkpoint.json`; eventual reports: `runs/c01-full-167b9074e5711420/analysis/`; logs: `logs/c01-full-167b9074e5711420-1440402.out` and `.err`, relative to the full deployment. These are evidence locations, **not a claim that final reports exist or passed**.

### STAT01 protocol/evidence

- Local checkout: `/home/soroush/lssp-stat01-recovery/research/lssp-stat01/PROTOCOL.md` and `recovery_v2/AMENDMENT.md`, `recovery_v2/LAUNCH_REPORT.md`.
- Recovery deployment: `/project/ikoutis/sv96/github/llm-serving-scheduler-lssp-stat01-recovery-v2-20261022/`.
- Checkpoint: `runs/stat01-recovery-v2-061933a64e27da20/checkpoint.json`; batches: `runs/stat01-recovery-v2-061933a64e27da20/batches/`; logs: `logs/stat01-recovery-v2-061933a64e27da20-1440206.out` and `.err`, relative to that deployment.
- Launch evidence in the PR's `recovery_v2/evidence/`: `launch.json`, `preflight.txt`, `submission.json`, `startup.json`. The amendment records the full reusable-study audit and its fingerprints. Original failed-run root remains `/project/ikoutis/sv96/github/llm-serving-scheduler-lssp-stat01-454168a00524/`.

### Audit execution boundary

Only this report is proposed for commit. No manuscript, bibliography, figures, frozen inputs or experimental results were edited; no Slurm command, experiment, GitHub Actions dispatch or merge was performed. The audit branch is `audit/lssp-m3-prewrite`, stacked on the authoritative M2 branch. The working tree's inherited hydrated-LFS status for `dataset/v1.1.0/scientific/campaign/consolidated.json` was preserved and excluded from the report commit. External-source checks were bounded metadata/content lookups; unresolved access and publication details remain explicitly marked above. Author review is the next step; M3 rewriting has not begun.

Report checks independently counted 43 bibliography keys, 28 cited keys and 15 uncited keys, with no unresolved citation keys; all 43 have an audit-table entry. Issue inventory checks confirm six P0, eight P1 and three P2 entries. The hydrated historical consolidated file's SHA-256 still matches the preservation record above. GitHub metadata confirms PRs #11, #14 and #15 are open drafts at heads `5ed2929d6012460ac43fd21730abd05ea45f9dcc`, `85cf892e155d96761b9a08bab35f60824e11dde2` and `eb6a703ef54a8b80609a073daef2cbf94650941d`, respectively; these are repository snapshots, not live execution observations. No manuscript rebuild or simulation test is necessary for this report-only change. Commit and PR carry `[skip ci]` to avoid the repository's push/pull-request workflows.
