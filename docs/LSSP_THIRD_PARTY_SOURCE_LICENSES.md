# Third-Party Workload Source Licenses

Completes the license/redistribution audit for the three sources LSSP's
Phase-10/11/12 campaign actually draws from (`configs/workloads/
source_registry.yaml`). Re-reads and consolidates `docs/DATA_LICENSE_AUDIT.md`
(broader, six-source audit from an earlier bootstrap task) and
`docs/DATA_ACQUISITION_STATUS.md` (this project's own acquisition record);
where the two disagreed on acquisition status, `DATA_ACQUISITION_STATUS.md`
is authoritative for LSSP since it postdates actual Phase-10 acquisition.

| Source | Canonical reference | License | Raw redistribution | Derived redistribution | Attribution requirement | Special terms | Confidence |
|---|---|---|---|---|---|---|---|
| BurstGPT | `HPMLL/BurstGPT`, release tag v2.0 | CC-BY-4.0 | **RAW_OK** by license, but this project does not ship raw rows (see below) | DERIVED_ONLY (this release) | Yes, cite BurstGPT | None identified | HIGH (documented in adapter + independently re-derived in `DATA_ACQUISITION_STATUS.md`) |
| Azure LLM Inference Trace 2024 | Microsoft `Azure/AzurePublicDataset`, `AzureLLMInferenceDataset2024`, window 2024-05-10..2024-05-19 | CC-BY (AzurePublicDataset) | **RAW_OK** by license, not shipped raw | DERIVED_ONLY (this release) | Yes, cite AzurePublicDataset | None identified | HIGH |
| Bailian/Qwen anonymized traces | repository LICENSE + README (Apache-2.0 stated for the dataset release) | Apache-2.0 | **RAW_OK** by license, not shipped raw | DERIVED_ONLY (this release) | Per Apache-2.0 (notice preservation) | None identified | MEDIUM — license confirmed via repo LICENSE/README, not independently cross-checked against a second authoritative source |

## Why DERIVED_ONLY despite RAW_OK licenses

All three licenses would permit raw redistribution. This project has
nonetheless referenced all three **read-only** from their canonical
location throughout Phase 10-12 rather than duplicating them into any repo
(`docs/DATA_ACQUISITION_STATUS.md` §Acquisition path, `docs/
DATA_LICENSE_AUDIT.md`) — a deliberate, pre-existing project convention,
not a license restriction. The HF release preserves that convention: no
raw BurstGPT/Azure/Bailian files ship in `llm-serving-scheduler-portability`.
Instead, the dataset card and `LICENSES/THIRD_PARTY_SOURCES.md` (mirrored
from this file at release time) give the exact canonical source, release
tag, and the SHA-256 this project independently verified against its own
Wulver-local copy, so a user with their own access can reconstruct the
identical input.

## Sources explicitly out of scope for this release

`docs/DATA_LICENSE_AUDIT.md` also covers Azure 2023, TraceLab, ServeGen,
and Mooncake — none of these feed the LSSP Phase-10/11/12 campaign
(`configs/workloads/source_registry.yaml` lists only BurstGPT, Azure-2024,
Bailian/Qwen for the 120-window pilot, plus TraceLab for a separate,
outcome-blind workload-characterization experiment not part of the RQ1-RQ6
scheduler-comparison campaign). Mooncake in particular remains
`INTERNAL_ONLY` per that audit and must never appear in any LSSP release.
No LSSP artifact currently references Mooncake.

**Confidence caveat**: unlike BurstGPT/Azure-2024 (HIGH), the Bailian/Qwen
license is MEDIUM confidence — confirmed from the source repository's own
LICENSE and README, but not independently cross-verified against a second
authoritative statement. Per this task's own instruction ("if unclear, do
not infer permissive rights"), this is disclosed rather than silently
upgraded to HIGH; it does not block DERIVED_ONLY release since the
derived artifacts LSSP ships (window samples, descriptors) do not depend
on resolving this to a higher confidence, but should be revisited before
any future decision to ship raw Bailian/Qwen rows.
