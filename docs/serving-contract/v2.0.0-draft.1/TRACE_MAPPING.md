# Length, tokenizer and context mapping audit

**Verified scope:** existing adapter field mappings, frozen 120-window descriptor index and the 120-row published `workload_windows.parquet` metadata table. The table contains descriptor summaries, not raw request-token arrays/text. No raw-source download, new selection, length truncation or request filtering occurred. **Not verified:** exact target-tokenized per-request coverage and joint P+O distribution for future main-study windows.

| Source | Current mapping | Primary-source cross-check | What cannot be inferred |
|---|---|---|---|
| Azure 2024 conversation | `ContextTokens -> input_tokens`, `GeneratedTokens -> output_tokens`, timestamp -> invocation time | [Azure schema](https://github.com/Azure/AzurePublicDataset/blob/master/AzureLLMInferenceDataset2024.md) explicitly describes lengths and privacy-based absence of prompt content. | No source text/token IDs or universal source tokenizer to retokenize into Qwen; context lengths must not be reinterpreted as just the latest conversation turn. |
| Bailian trace B | `input_length`, `output_length` are token counts; relative timestamp; session/turn/hash fields separate | [Bailian schema](https://github.com/alibaba-edu/qwen-bailian-usagetraces-anon/blob/main/README.md) identifies length fields as tokens and `hash_ids` as 16-token blocks. | Do not multiply lengths by 16, concatenate previous turns again or infer identical Qwen checkpoint/tokenizer. Salted hashes do not recover text. Current adapter's inherited 5f7439c5 provenance pin remains explicitly unverified; current README is not raw historical-file verification. |
| BurstGPT without-fails v2/file 2 | `Request tokens`, `Response tokens`, total, timestamp; model label retained | [BurstGPT schema](https://github.com/HPMLL/BurstGPT/blob/main/README.md) names these lengths and distinguishes elapsed whole-response time from TTFT. | GPT-family lengths are not an exact Qwen retokenization. Without-fails conditioning belongs to the source release, not permission to drop future serving failures. |

Current engineering checkpoint: Qwen/Qwen2.5-0.5B-Instruct revision `7ae557604adf67be50417f59c2c2f167def9a775`; hashes in `scripts/mgpu02/prompt.json` and `scripts/mgpu05/environment.json`. Effective checked context=512, prompt cap=256, N16/B4096. Engineering requests use actual token-ID arrays (no chat template); the preflight checks source IDs and tokenizer files. The historical text constructor verifies `encode(text, add_special_tokens=False)` length and refuses round-trip mismatch. Neither proves semantic-text equivalence to production prompts. BPE encode/decode is not generally an inverse.

Prospective main tokenizer/model/context is **not selected**: the protocol only recommends a dense 7–8B candidate. It is therefore impossible to truthfully report completed target retokenization or final eligibility percentages. Advertised model maximum position count is not the approved engine context, nor a guarantee of A100/L40 memory feasibility.

## Existing descriptor coverage (recomputed; no new windows)

| Source | Windows | Median range, source tokens | Medians >256 | Medians >512 |
|---|---:|---:|---:|---:|
| Azure | 40 | 628.5–1595 | 40 | 40 |
| Bailian | 40 | 343.5–1150 | 40 | 22 |
| BurstGPT | 40 | 140.5–620.5 | 9 | 3 |

Index SHA `d78ec1087fedae02174ca093a9860c70468be336ccb1d7e6de756c81ba331e53`. All 120 window medians exceed 128. Median>P/context demonstrates a coverage mismatch, not an exact excluded fraction. The largest window p99 input lengths are approximately 7704.94/8444.22/2367.32 respectively; p99 is not a maximum or a permissible truncation rule. Separate input/output quantiles cannot be summed to recover joint context eligibility. [Audit evidence](evidence/trace-audit.json) records exact descriptor values and metadata-file identity.

## Proposed mapping and pre-implementation audit (S07 / A04 / A10)

Recommend compute-shape replay: preserve each approved source row's declared input/output lengths and temporal correlations; construct synthetic inputs at those **target-token counts** using the approved immutable tokenizer. This transfers the declared lengths, not original text or equivalent linguistic content. Numeric equality of counts across tokenizers is a workload construction rule, not evidence of source-tokenizer identity. Keep `source_input_count`, `target_input_count`, construction kind/seed, tokenizer revision and provenance separate.

If real text is available and permitted, retokenize explicitly and retain both source and target lengths; this is another declared workload mapping. Do not combine both mappings under one source label without a stratum. Prefix reuse, multilingual/content/quality effects and multimodal records need separate contracts. Do not turn an image/file trace row into a text-only record without recording an approved scope decision.

Before any main-window implementation/freeze:

1. Recover exact raw-file hashes/row coordinates and units, including malformed/zero-output/multimodal records; preserve an unfiltered ledger. Source identity and licensing must be verified, not inferred from current README text.
2. Approve target checkpoint/tokenizer/template/special-token behavior. For token-vector replay, record every actual input ID and validate legal vocabulary/special-token handling offline. For text replay, tokenize fully before timed dispatch and verify the exact received vector; no hidden template tokens.
3. For **every** prospective row compute P and O and test P>0, O>0, P+O<=L, implementation prompt/output limits and empty-deployment KV feasibility with measured per-group capacities. Distinguish temporarily waiting from permanently impossible input. An O=0 row remains visible until the author decides eligibility; never coerce it to one token.
4. Report request-weighted and token-work-weighted eligibility by source/class/window/time stratum, using joint lengths and including all reasons. If limits exclude important regimes, choose larger context/implementation or explicitly approve a narrower question. Never choose exclusions from policy performance.
5. Freeze original/derived hashes, source/target mapping, output-work rule and independent windows. Retain covariance, arrivals and errors; do not split or stitch requests to fit the engine without a new declared study.

This review supplies the audit method and demonstrated mismatch. It does not certify raw historical-source unit provenance, recover missing source text, authorize a synthetic distribution, or freeze a new main model/window/context limit.
