> **Historical snapshot:** the focused major revision is documented in [the current final report](../major-revision/FINAL_REPORT.md) and [claim audit](../major-revision/CLAIM_TO_EVIDENCE.md). This dated report retains its original provenance; rc1 itself is unchanged.

> **Historical PR20 assessment (retained).** Current status, provenance, artifact and readiness findings supersede the pending questions below: [artifact-readiness assessment](../artifact-release/READINESS.md), [verified related-manuscript statuses](../artifact-release/RELATED_MANUSCRIPTS.md), and [source provenance](../artifact-release/SOURCE_PROVENANCE.md). Rejected/withdrawn dispositions no longer require confirmation. This body records what was known in the earlier review.

# Submission requirements, placeholders, and author decisions

Review date: **2026-10-22**. Verdict: **NOT_READY**. These are unresolved gates and decisions, not newly authorized experiments or correspondence. They supersede the original checklist where verification has advanced.

## Official-source check

| Item | What was independently established | Remaining uncertainty/action |
|---|---|---|
| Journal-specific instructions | [Official ToMPECS author guidelines](https://dl.acm.org/journal/tompecs/author-guidelines) returned HTTP 403 through both web access and a direct public HTTP fetch. The journal hostname was also inaccessible. | **UNVERIFIED:** currently required initial-review format, anonymity model, article categories, length/reference/appendix rules, supplement upload rules, and specific portal declarations. Obtain a current official copy or inspect the author portal before submission. Do not transfer conference or another journal's rules to ToMPECS. |
| ACM format mapping | The indexed [ACM-hosted current acmart manual](https://portalparts.acm.org/hippo/latex_templates/acmart.pdf), Table 1, explicitly lists TOMPECS under `acmsmall`; it also describes `manuscript`/`review`. Direct PDF fetch was blocked, so this is indexed official documentation, not a newly downloaded template. | Both supplied formats are reasonable review artifacts. This does **not** establish which file ToMPECS currently requests at first submission. Existing M2 template bytes are preserved. |
| General submission template | [ACM submission template](https://www.acm.org/binaries/content/assets/publications/taps/acm_layout_submission_template.pdf) indexed official text describes a single-column submission document. General author/submission pages returned 403. | Does not settle journal-specific anonymity or length. No page cap is asserted; 21/22 pages describe this build only. |
| Current authorship/AI policy | Indexed official [ACM authorship policy, updated May 14, 2026](https://prod-www.acm.bloomreach.cloud/publications/policies/new-acm-policy-on-authorship) was readable in search; canonical direct fetch returned 403. It distinguishes research-AI methods disclosure from writing assistance, for which disclosure is no longer required; human accountability and ORCID before eRights remain. | Author must confirm the complete research-AI scope, including earlier work, and finalize the methods disclosure. Do not reuse obsolete conference summaries as current general policy. |
| Concurrent/prior work | The same current authorship policy requires no concurrent review of the submitted work and appropriate identification of prior work and incremental contribution. The [separate simultaneous-submission policy](https://www.acm.org/publications/policies/simultaneous-submissions) could not be fetched directly. | Confirm current statuses and any required editorial treatment of related work; no exception or disclosure sufficiency is presumed. See [overlap audit](OVERLAP_AUDIT.md). |
| Publication rights, third-party materials, OA costs/agreements | No author-specific rights, institutional agreement, payment eligibility, or permission was established. | Author must confirm rights and applicable current arrangements; no APC amount or waiver is invented. |
| Accessibility and production metadata | All four figures have LaTeX `Description` text. Both ACM builds succeed. | Source/PDF checks are not TAPS acceptance or complete accessibility certification. Assigned publication metadata and rights blocks must follow actual publisher instructions. |

The 403 responses were recorded during this review; they are access limitations, not evidence that a policy does not exist. The indexed policy/template records are explicitly separated from unavailable journal instructions.

Artifact access was checked separately: the [historical Hugging Face landing page](https://huggingface.co/datasets/SoroushVahidi/llm-serving-scheduler-portability) is accessible, but its automatic viewer reports a schema `CastError`. This does not prove file downloads fail or that C01/STAT01 raw artifacts are present. The [historical Zenodo DOI](https://doi.org/10.5281/zenodo.22306798) could not be accessed through the web tool. Neither check establishes a complete immutable M3 release; no repair or external upload was attempted.

## Complete visible author-review inventory

There are **four** `authorreview` invocations, all in `sections/declarations.tex`, expanding to conspicuous **AUTHOR REVIEW REQUIRED** paragraphs. No `TODO`/`TBD` was found in the manuscript body. The four paragraphs contain multiple decisions:

| Location / item | What remains unresolved |
|---|---|
| Declaration 1 — C01 and STAT01 reviewer access | How reviewers obtain complete pinned requests, execution journals and raw synthetic-study evidence, rather than only saved summaries; permission to share; stable access credentials/process if not public. |
| Declaration 1 — public artifact identity | Immutable versions/DOIs, exact contents, and whether public HF/Zenodo artifacts actually include the new campaigns. Historical release links cannot establish this. |
| Declaration 1 — Azure rights/provenance | Consumed `AzureLLMInferenceTrace_conv_2024.csv` hash and acquisition must be reconciled with release/rename history. The current README claims CC-BY and requests DynamoLLM citation, now added. That is not a certification of all release-specific redistribution conditions. |
| Declaration 1 — Bailian/Qwen rights/provenance | Pinned README and LICENSE establish an Apache-2.0 repository claim (LICENSE blob `7a4a3ea2424c09fbe48d455aed1eaa94d9124835`). Confirm coverage and notices for the consumed trace and any derivative/raw redistribution. KVCache attribution is now added; confirm preferred dataset release-date citation. |
| Declaration 1 — BurstGPT rights/provenance | Confirm exact terms and attribution for `BurstGPT_without_fails_2.csv`, acquisition and intended release. A KDD citation and a historical license assertion are insufficient to certify permission. |
| Declaration 2 — historical LSSP statuses | Current JSC, old LSSP PEVA and SMPT statuses, exact upload identities and public versions. Historical rejection statements remain author-provided, not independently verified. |
| Declaration 2 — adjacent manuscripts | Current headroom PEVA, module counterfactuals, and older LLM2026/FGCS line statuses; exact submitted versions; required disclosures/citations. The module manuscript also has an anonymized prior-artifact reference needing identification by the author. |
| Declaration 2 — overlap | Approve explicit shared-corpus/infrastructure/results/conclusion disclosures. Exact cross-project BurstGPT row overlap remains unresolved. No disjointness or independent-evidence claim is permitted on current documentation. |
| Declaration 3 — identity and contributions | Confirm Soroush Vahidi, NJIT affiliation, `sv96@njit.edu`, complete author list and contribution roles. These inherited front-matter values are not newly certified. |
| Declaration 3 — interests and support | Confirm competing interests and exact funding/support. Historical names: Google Cloud Research Credits, CloudRift AI Builder Grant, Cohere Labs Catalyst Grant Program, NJIT/Wulver. Do not infer that all apply or that no competing interests exist. |
| Declaration 4 — AI and responsibility | Confirm full research-AI use and review responsibility; the revised question reflects the current policy distinction. Known Codex manuscript/display/validation assistance is not a complete history of the research lifecycle. |
| Declaration 4 — journal instructions | Format, anonymity, length, supplement handling and declarations remain journal-specific checks. |

Additional non-prose placeholders: `main.tex` leaves `acmDOI` empty, uses `setcopyright{none}` and suppresses `printacmref`. `acmsmall` renders default volume/number/article/date footer metadata; these are template review placeholders, **not publication facts**. `acmYear{2026}` and the inherited author front matter require final workflow review. Do not invent DOI, license, acceptance date or article number.

## Concise decisions requested from the author

1. **Scientific positioning:** approve the bounded common-model evaluation and explain why its three observed behaviors, model-implied ties, and finite-corpus trade-offs are a sufficient journal contribution. Keep all unfavorable/null findings and avoid native-SLAI or hardware-selection claims.
2. **Related manuscripts:** supply current status/ID/date and exact uploaded version for each line above; approve the overlap/disclosure text and actual public citations. Supply the unavailable FGCS intermediate if relevant. Clarification was requested during the review; no current confirmation was available when this report was prepared.
3. **Artifact release and rights:** choose the reviewer access path and immutable release versions; confirm source-file licenses/attribution and raw/derived redistribution rights. No release is published by this task.
4. **Author declarations:** approve author list/contact/affiliation, contributions, funding/support, competing interests and research-AI methods disclosure; confirm human review of the complete paper.
5. **Venue compliance:** verify current official ToMPECS instructions and author-specific rights/OA arrangements, then select the appropriate review PDF and resolve production placeholders only as instructed.

None of these questions has been answered by a favorable default. The correction PR is for author review only; no merge, journal upload, editor message, or external submission is authorized or performed.
