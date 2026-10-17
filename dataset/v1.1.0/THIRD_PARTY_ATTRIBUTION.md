# Third-party workload attribution and transformations

The LSSP campaign selected 120 source windows, calculated numeric descriptors, synthesized simulator inputs, then generated scheduler outcomes and analyses. This package contains numeric window information and results, not original request-level CSV/JSONL records, prompts or completions. Obtain original traces from their publishers. LSSP licenses cover only rights the LSSP licensor controls. Attribution does not imply endorsement.

| Source | Pinned rights evidence | Input SHA-256 | LSSP change |
|---|---|---|---|
| [BurstGPT without-fails v2](https://github.com/HPMLL/BurstGPT/tree/v2.0), BurstGPT_without_fails_2.csv | [CC BY 4.0 at v2.0](https://github.com/HPMLL/BurstGPT/blob/v2.0/LICENSE); credit BurstGPT authors | 56193aa9b2bb26128ded43d2d29a960df6bf5af062bcfc9b005f3fcaa4e6e501 | Selected windows, numeric summaries, simulated outcomes; indicate these changes when sharing adapted source material. |
| [Azure LLM Inference Trace 2024](https://github.com/Azure/AzurePublicDataset), AzureLLMInferenceDataset2024, May 10–19, 2024 | [CC BY 4.0](https://github.com/Azure/AzurePublicDataset/blob/master/LICENSE); credit Microsoft/Azure dataset authors | a0cc9b969a9bbf0fd811802cbf4323edd3a209ace791e3799ad4f9207f213941 | Selected windows, numeric summaries, simulated outcomes; indicate these changes when sharing adapted source material. |
| [Bailian/Qwen anonymized trace B](https://github.com/alibaba-edu/qwen-bailian-usagetraces-anon/tree/5f7439c51ec248a0c585f7d90a41a6f57773b912), qwen_traceB_blksz_16.jsonl | [LICENSE](https://raw.githubusercontent.com/alibaba-edu/qwen-bailian-usagetraces-anon/5f7439c51ec248a0c585f7d90a41a6f57773b912/LICENSE) and [README](https://raw.githubusercontent.com/alibaba-edu/qwen-bailian-usagetraces-anon/5f7439c51ec248a0c585f7d90a41a6f57773b912/README.md) at frozen revision: Apache 2.0; credit source authors | 68e3f98e2d601d60d0abf4b89bc8a3654372abab7b1cde6373a13d0054379d59 | Selected windows, numeric summaries, simulated outcomes; Apache license text copied in THIRD_PARTY_LICENSES/BAILIAN_APACHE_2.0.txt as a conservative notice. |

The unchanged public LSSP_THIRD_PARTY_SOURCE_LICENSES.md predates direct verification of the frozen Bailian revision. The pinned evidence above supersedes only its medium-confidence wording about that source license. No claim is made that individual numeric facts are copyrightable. Preserve any applicable source notice and change indication if an adapted protected work is shared. TraceLab and Mooncake did not feed this 120-window matrix and are not bundled.

## Resource acknowledgments

The computational experiments supporting this dataset used Wulver, the high-performance computing system provided by the New Jersey Institute of Technology (NJIT). The author gratefully acknowledges NJIT for providing these computational resources.

[CloudRift](https://cloudrift.ai) provided $1,000 in research credits supporting this research and requested acknowledgment and a link. These credits do not establish ownership, authorship, licensing, approval or endorsement.
