# M3 compact source and verification asset

PREPARED_NOT_PUBLISHED, proposed version m3-v1.0.0. This is a subset of the complete canonical evidence archive: it includes source, tests, paper sources and frozen summary inputs, analysis scripts, table views and scoped licenses. It excludes full evidence/ journals, request inputs, STAT01 arrays and saved BOUND01 fixtures.

Display regeneration and table checks can run here. Commands in REPRODUCE.md that require evidence/ must use the complete Zenodo artifact, whose DOI is not yet created. The source inventory identifies execution and manuscript commits; this directory defines the proposed release source tree in the existing repository. Its local packaging commit is recorded separately in the release handoff and does not replace any experiment-execution commit.

# Common-contract LLM-serving scheduler reproducibility artifact

**Prepared, not published.** Proposed release: `m3-v1.0.0`; preparation `rc3`, 24 October 2026 UTC. No M3 archival DOI has been issued or reserved by this task.

This artifact supports *Scheduler Equivalence and Performance Trade-offs under a Common LLM-Serving Contract*, Soroush Vahidi. Manuscript source: [commit 42170fdcdc7c4b68ae2639b319a4892d097532a0](https://github.com/SoroushVahidi/llm-serving-scheduler-robustness-benchmark/tree/42170fdcdc7c4b68ae2639b319a4892d097532a0), integrated manuscript branch stacked on draft PR #29. The integrated manuscript and optional ACM-small build each have 30 pages. The manuscript's existing availability statement describes its preparation-time status and is not a claim that this candidate is public.

The scientific question is how a shared execution contract constrains scheduler behavior and observed performance. The package contains saved CPU discrete-event simulations, statistical-method calibration data, a written equivalence proof, and analysis/verification programs. These are not measurements of GPU performance. Four policy adaptations share the CM-0.1 contract; they are not unchanged production implementations.

## Evidence included

| Identifier | Meaning and scope | Records |
|---|---|---:|
| C01-FULL | Four-policy common-contract comparison: 120 windows × 6 settings × 2 capacities × 4 policies | 5,760 cells; 144 reused pilot cells and 5,616 additional executions |
| C01 rankings | One four-policy ranking per condition, capacity and endpoint | 15,840 rows |
| C01 pairwise | Six policy pairs for each ranking context | 95,040 rows |
| STAT01 | Synthetic calibration of statistical procedures; original and postdiagnosis families distinguished | 5,360 saved batches, 134,000 studies, 7,200 final endpoint summaries |
| Budget sensitivity | Six selected conditions × three budgets × four policies | 72 saved cells |
| Urgency certificate | Structural and telemetry checks for the selected budget conditions | 18 certificate rows |
| BOUND01 | Fixed-policy, empty-start selected-work equivalence under the stated contract | Written proof; seven historical fixtures and 36 saved journals |

Result counts are not counts of independent statistical samples. C01 uses related windows and repeated conditions; its analysis is descriptive for a finite corpus. STAT01 rows distinguish methods and endpoints and are not additional studies. The proof is mathematical, not machine checked; finite tests check implementation assumptions.

TIME01 and ABL01 are included after independent scientific review and author-authorized integration. TIME01 contains 384 new variable-duration executions and 384 reused fixed baselines across 24 purposively selected windows, two settings, two capacities and four adaptations. ABL01 has 1,440 paired original/derived controls and zero new simulations; its frozen simulated:false identities are preserved. These dependent views are not additional independent experiments. TIME01 is synthetic, not hardware-calibrated; selected BurstGPT mean latency is worse under both clocks. ABL01 isolates the prompt-ordering trade-off within the original nonbinding contract; it does not establish universal optimality. Historical frozen scientific_review_required:true flags remain unchanged and are superseded by the dated hash-linked independent review verdict, not silently edited.

## Navigation

- `REPRODUCE.md`: checked saved-evidence commands and limits.
- `DATA_DICTIONARY.md`, `TABLE_SCHEMA.json`: table meaning, fields, keys and null handling.
- `WORKLOADS_AND_CONFIGURATIONS.md`: workload acquisition, transformations, policies, seeds and environments.
- `PROVENANCE_AND_RIGHTS.md`, `THIRD_PARTY_NOTICES.md`, `licenses/`: component rights and attribution.
- `PROVENANCE_INVENTORY.csv`: per-file source, creator, license scope, purpose and release role.
- `COMMITS.json`, `MANIFEST.json`, `SHA256SUMS`: immutable source and byte identities.
- `DUPLICATION_ASSESSMENT.json`: reuse of historical LSSP evidence and current pilot cells.
- `PLATFORM_PLAN.md`: one release inventory, multiple access routes.

## Access and citation

The existing GitHub repository is the source home. The public LSSP Hugging Face dataset and DOI [10.5281/zenodo.22306798](https://doi.org/10.5281/zenodo.22306798) describe older scientific scope and do not identify this M3 release. Use `CITATION.cff` for the proposed artifact title/version; add the actual M3 archival identifier only after publication and verification. HF and Kaggle are intended to carry identical convenience result tables, not additional experiments. The complete Zenodo snapshot will remain the canonical evidence package.

Original project software is MIT; eligible original results and package documentation are CC BY 4.0. Transformed inputs retain source-specific CC BY 4.0 or Apache 2.0 terms. ACM support retains its own license; manuscript text/PDF retains author copyright. No blanket license is asserted for the mixed archive. Original third-party traces and confidential reviewer packages are excluded.
