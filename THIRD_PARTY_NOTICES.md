# Provenance and rights

Verified 2026-10-23 using pinned upstream license bytes and existing source-identity manifests. Code/result licensing was already approved by the author; no renewed approval is requested.

## License scopes

- Eligible original software and new packaging/verification code: MIT; `licenses/MIT.txt` and each preserved source LICENSE. This is not a claim of ownership over third-party implementations or datasets. The four adaptations and their implementation lineage remain identified in the frozen code/protocol and manuscript references.
- Eligible original experimental results, synthetic STAT01 arrays/study records, original analysis tables and compiled research-result contributions: CC BY 4.0, attributed to Soroush Vahidi; legal text in `licenses/CC-BY-4.0.txt`. Preserve the distinction between original result rights and upstream transformed-input rights.
- Derived Azure/BurstGPT inputs retain CC BY 4.0 attribution/change notices. Derived Bailian inputs retain Apache 2.0 terms; they are NOT relicensed wholesale as CC BY. Mixed-source files are compilations with component-level upstream terms, documented below.
- ACM class/source files retain their original LPPL/copyright notices; ACM-Reference-Format.bst declares public-domain status. The matching complete upstream v2.20 source snapshot, LPPL legal text and distribution provenance are included under licenses/upstream (see ACM_TEMPLATE_DISTRIBUTION.md). Third-party license/readme texts retain their upstream terms. Manuscript text/PDF retains author copyright; it is not automatically covered by the code/data licenses. This candidate does not grant ACM publication rights or certify future publishing agreements.

## Exact upstream identities and acquisition

Original third-party trace files are excluded, including the optional rc1 upstream-source archive. A reviewer may independently obtain the following originals from their providers, verify the SHA-256, and apply the pinned loaders if reconstructing input selection. Saved-evidence verification does not download them.

| Source | Official acquisition URL | Exact bytes / SHA-256 | Terms and pinned documentation |
|---|---|---|---|
| Azure conversation trace | https://github.com/Azure/AzurePublicDataset/releases/download/dataset-llm-2024/AzureLLMInferenceTrace_conv_1week.csv | 1,135,195,393 / `a0cc9b969a9bbf0fd811802cbf4323edd3a209ace791e3799ad4f9207f213941` | CC BY 4.0; https://github.com/Azure/AzurePublicDataset/tree/215becdacba1ce682c7368642ce97d5a332de7a6 |
| Bailian/Qwen To-B | https://github.com/alibaba-edu/qwen-bailian-usagetraces-anon/blob/5f7439c51ec248a0c585f7d90a41a6f57773b912/qwen_traceB_blksz_16.jsonl | 96,209,982 / `68e3f98e2d601d60d0abf4b89bc8a3654372abab7b1cde6373a13d0054379d59` | Apache 2.0; pinned repository, Git LFS object SHA-256. Use the download/raw control or Git LFS; the pointer is not the dataset. |
| BurstGPT v2.0 | https://github.com/HPMLL/BurstGPT/releases/download/v2.0/BurstGPT_without_fails_2.csv | 142,376,815 / `56193aa9b2bb26128ded43d2d29a960df6bf5af062bcfc9b005f3fcaa4e6e501` | CC BY 4.0; https://github.com/HPMLL/BurstGPT/tree/d895a53bb7b8ec137d0d2fe203b335835a78c10a |

License URLs (all returned HTTP 200 and matched saved bytes on verification date):
https://raw.githubusercontent.com/Azure/AzurePublicDataset/215becdacba1ce682c7368642ce97d5a332de7a6/LICENSE
https://raw.githubusercontent.com/alibaba-edu/qwen-bailian-usagetraces-anon/5f7439c51ec248a0c585f7d90a41a6f57773b912/LICENSE
https://raw.githubusercontent.com/HPMLL/BurstGPT/d895a53bb7b8ec137d0d2fe203b335835a78c10a/LICENSE

The original complete license and README texts are in `licenses/upstream/`. No separate Alibaba NOTICE was present in the previously verified pinned tree. Azure's local `_conv_2024.csv` filename was a byte-identical rename of `_conv_1week.csv`; no inference from filename similarity is needed. Source-file hashes are retained even though those files are excluded.

## Attribution and modifications

Credit Microsoft Azure and Stojkovic et al., *DynamoLLM* (HPCA 2025), https://doi.org/10.1109/HPCA61900.2025.00102; Alibaba Cloud and Wang et al., *KVCache Cache in the Wild* (ATC 2025), https://www.usenix.org/conference/atc25/presentation/wang-jiahao; and the BurstGPT authors, *BurstGPT* (KDD 2025), https://doi.org/10.1145/3711896.3737413. Complete supplied attribution/readme notices are retained. No provider endorsement is implied.

Transformations: valid-row filtering; deterministic selection of 120 windows of 200 requests; arrival rebasing; direct numeric prompt/output lengths; uniform priorities; seeded output-length prediction and synthetic deadlines; six arrival/deadline compression conditions. Exact seeds, valid-row indices, costs and rounding remain in the frozen manifests and `code/c01/src/` loaders/synthesis implementation. Hash-block size is not a token-length multiplier. Source windows contain 8,000 records per source. Bailian's 8,000 transformed records retain anonymous session/reuse identifiers and cache hashes; no prompt/response text is present in the inspected record schema, and `extra` is empty. They are transformed anonymous workload records, not independent provider latency measurements.

The generated result/journal/terminal files are outputs of the common execution contract, not physical GPU measurements. STAT01 raw arrays are original synthetic study data, not upstream workload traces. Preserve original versus expanded-method identities and the recorded numerical-boundary discrepancy.

Prominent directory notices and existing input sidecars identify transformed files without modifying frozen scientific bytes. Original upstream terms continue to govern identifiable upstream portions in mixed files. Pattern scanning cannot prove the absence of all possible sensitive information; see the integrity report for exact coverage and limitations.

Follow-up Bailian assessment (2026-10-23): all 8,000 source-window records were joined exactly to the pinned public upstream trace. Session IDs and cache IDs are linkable to those public records; they are not claimed unlinkable. No account mapping, prompt/response text or nonempty extra field was found. These fields are unused by C01 scheduling but preserve the frozen input provenance. The provider documents salted SipHash, integer remapping and replacement of chat IDs; its Apache 2.0 license and complete attribution/change notices are retained. No concrete additional privacy restriction or redistribution prohibition was identified, so these frozen fields were not changed. This does not independently certify the provider’s anonymization or regulatory claims.
