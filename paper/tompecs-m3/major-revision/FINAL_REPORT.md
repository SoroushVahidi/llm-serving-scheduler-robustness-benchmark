# M3 focused major revision — final report

**Scientific verdict: READY_FOR_AUTHOR_AND_ADMINISTRATIVE_FINALIZATION.** The focused scientific revision is adequately supported by existing evidence. This is not submission authorization, a claim of native performance validity, or a prediction of journal acceptance. Administrative and author-review blockers remain.

Draft PR: https://github.com/SoroushVahidi/llm-serving-scheduler-robustness-benchmark/pull/22 . Exactly one new draft PR was opened, stacked on #21 with base `manuscript/lssp-m3-artifact-readiness`. Its base was confirmed at source commit `2a65c0e139d1410475170781469901559960265d`. Branch: `manuscript/lssp-m3-major-revision`. Implementation commit: `780108ea53a91bb829e270e7c42735de6419e723`. The following report commit contains this document; its exact final hash is recorded in `/home/soroush/lssp-m3-major-revision-20261022/completion.json` and the local companion's `COMMITS.json`, avoiding an impossible self-referential hash.

## Scientific result and principal revisions

The abstract, introduction, model justification, discussion and conclusion now center on what the execution contract reveals. Four adaptation names yield three observed behaviors: chunked-FCFS and decode-first have exactly equal per-request terminal states and metrics in all 1,440 matched conditions, although journal span order can differ. Fixed batch timing removes composition-dependent execution cost; bounded residency preserves admission competition while the chunk work budget cannot bind. The SLO urgency gate remains inactive, while prompt-length admission and whole-prefill decode deferral remain active. These claims were checked directly against frozen execution source, not inferred from scheduler names or asserted as ex-ante design intent.

The result is positioned as a reproducible case study connecting those exact structural consequences to measured residual trade-offs and ranking interpretation. Existing aggregate latency/throughput/tail findings and 0/2,376 strict source-mean practical reversals remain unchanged. Window/metric changes, exact ties, redundant endpoints and negligible TPOT distinctions remain explicit. Absence of a strict practical reversal is correctly distinguished from equal rankings or top sets. STAT01 supports interpretation of historical inference rather than supplying population significance for C01.

The new worked example is the first lexically qualifying saved BurstGPT condition with the requested three directions: `burstgpt::burstgpt_pilot_v2_w12::HIGH_PRESSURE`, `kv262144`, eight resident slots. It is explicitly outcome-selected and illustrative. Chunked cell `ecec167d9fb8e426ac67298b` and SLO cell `9feed68339670e5b366d064f` complete the same 200 requests and emit 3,520 outputs. Mean latency falls 61.681→36.641 ms; p95 rises 110.741→147.480 ms; full-duration throughput falls 3060.870→2613.215 tokens per simulated second. The duration grows 1.150→1.347 s including drain.

Actual journals show the first differing admission membership at 14 ms (requests 13/14), a long-output request 26 admitted at 26/223 ms and completing last, and the strongest improving request 196. Across all requests, 151 complete earlier, 29 later and 20 equally; latency changes sum to -5.008 s. The p95 brackets involve other requests, so the final request is not asserted to explain the tail quantile. Waiting-to-first-prefill is distinguished from TTFT and total latency. Output lengths are used retrospectively and were hidden from policies. This is an explanatory saved execution, not a causal intervention, representative estimate or account of every aggregate effect.

Chronological sensitivity and its unchanged Figure 4 moved intact to Appendix C. Detailed STAT classifications, low-power results, post-diagnosis identities, uncertainty families and precision/max-count distinctions remain in Appendix A, with a concise null diagnostic in the main text. The former Table 8 (now 10) uses larger type and more available width. Existing figure and numeric-table bytes are unchanged.

Dai, Deng, Li and Peng's requested **arXiv:2504.07347v3, May 18, 2026** was verified against both primary URLs. Related Work contrasts batching/stability and batch-size constraints with fixed timing, full-context residency and finite drained completion rates; no theorem is transferred or refuted. The three active adjacent manuscripts are distinguished using pinned local text, while acknowledging their existing inactive-mechanism and metric-sensitivity contributions. Historical windows/reconstruction/36/990 reuse is attributed. Local-source versus uploaded-version uncertainty and unresolved overlap identities remain qualified; settled rejections/withdrawal and source licenses are not reopened. Publication-facing declarations no longer contain worker-internal remarks.

## Deliverables

Workspace: `/home/soroush/repos/llm-serving-scheduler-lssp-m3-major-revision`.

| PDF relative to workspace | Pages | Bytes | SHA-256 |
|---|---:|---:|---|
| `paper/tompecs-m3/m3-manuscript.pdf` |24|728978|`a5e8d45d63bd404944a55c6efcb202b3fd52e06589ed7b64c90921eab0b6a39f`|
| `paper/tompecs-m3/m3-acmsmall.pdf` |26|728933|`d41dbfa68eb4a18df9bff28d318992c21f3b2b6917b8d837379ca62514760fcb`|

The new support is under `paper/tompecs-m3/major-revision/`: [claim audit](CLAIM_TO_EVIDENCE.md), [changelog](CHANGELOG.md), [example provenance](EXAMPLE_PROVENANCE.md), fixed identity manifest, compact CSV/TeX tables, read-only `analyze_example.py`, independent `verify_example.py`, [validation](VALIDATION.md), [related-work disclosure](RELATED_MANUSCRIPTS.md), [author fields](AUTHOR_DECISIONS.md), and [blocker register](REMAINING_BLOCKERS.md). Full hashes and exact input/result/journal/source-record identities are preserved there. Historical reports have explicit supersession links.

The unchanged rc1 candidate remains at `/home/soroush/artifacts/lssp-m3-rc1-20261022/`; it contains the earlier manuscript snapshot, not this revision. Its evidence archive SHA-256 remains `9543ed38051c95a3b781dd0bc1086e049d4d08b56aa0ad7e06d603dc93457e9b` (2,597,049,129 bytes), and upstream-source archive remains `a6d3ef2647492e79c580ab85eecf6cd47a9107d33ac4dc08757bda0900077853` (337,808,093 bytes).

The versioned local companion is assembled after this report commit at `/home/soroush/artifacts/lssp-m3-major-revision-companion-v1-20261022/`. Its external `MANIFEST.json` and `COMMITS.json` identify the final manuscript packet and Git version. [Pairing instructions](COMPANION.md) use rc1 raw evidence directly; no 3 GB raw archive is duplicated. The persistent completion record confirms assembly and its manifest hash. Neither candidate nor companion is externally released.

## Validation and independent checks

Both ACM builds pass at 24/26 pages with no overfull boxes, unresolved references/citations, duplicate labels or errors. All 25 references and four-figure/ten-table labels resolve. Full layout overviews and focused final renders show readable example/scenario tables without clipping. Three inherited optional bibliography advisories and the suppressed ACM reference block remain documented; no full accessibility/TAPS acceptance is claimed.

The complete independent C01 saved-analysis oracle passes 5,760 cells, 15,840 rankings, 95,040 pairwise rows and 26,136 reversal groups. All 54 existing narrative anchors and 7,200 STAT endpoint rows pass. Existing figures, tables, supplements and 37 compressed inputs remain byte-identical. No frozen check was weakened.

Every new worked-example quantity was checked by separate calculation paths: standard-library terminal arithmetic and an independent NumPy reconstruction from both journals, with no shared generator or engine/policy imports. All 400 terminal states and 2,497 events match; full input/result/journal hashes, arrival eligibility, spans, resource ledgers, anchors, first outputs, completion times, compact CSV/table values and p95 brackets pass. Selection is independently checked and frozen. Reproduction against rc1's separate clean extraction produces all five derived files byte-identically and independently verifies again. Floating arithmetic tolerance is 1e-12; identities/hashes/integer counts/terminal dictionaries are exact.

Both raw archive digests were rechecked, scoped frozen source matches the execution commit, and the hydrated historical file still hashes to `73adf7d97f06985ec8f8e1c2f794fd43178433eb198e1c00705e817f4bde9c26`. It is unstaged; M2, prior manuscripts and frozen campaigns remain unchanged. Package hashes are generated after final documentation. Full logs/checkpoints are in `/home/soroush/lssp-m3-major-revision-20261022/`. PR21's full inventory/clean-extraction checks remain historical evidence; this pass does not claim a fresh exhaustive replay of every campaign journal or synthetic study.

## Remaining blockers

**Scientific:** no remaining demonstrated blocker within the focused contract-specific question. The scientific contribution is supported by exact model reasoning, unchanged complete results and independently verified explanation. Its restricted model/corpus and noncausal illustrative selection remain explicit. Journal novelty/acceptance remains an editorial judgment; author approval alone cannot establish scientific merit.

**Administrative/access/disclosure:** human review and declarations (authorship/affiliation/contributions, funding/support, COI, research-AI methods/history and responsibility); approved external reviewer access, immutable archive/version/retention plan and final compilation/code/synthetic-data license scopes; active-manuscript submitted/public identities and qualified overlap questions; and current official ToMPECS rules. The journal endpoint still returns 403, so format/anonymity/length/supplement requirements are unverified and no page cap is invented. Source identities/licenses and historical dispositions are settled.

No new experiments, simulations, Monte Carlo generation, Slurm jobs, explicit Actions invocations, raw-data uploads, releases, DOI minting, visibility changes, merge, journal submission or correspondence occurred. Every commit and the single draft PR title use `[skip ci]`. Work stops for author review after the final report, companion and persistent completion record.
