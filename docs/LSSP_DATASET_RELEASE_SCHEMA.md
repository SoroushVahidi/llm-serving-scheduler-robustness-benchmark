# LSSP Dataset Release Schema

Design for the eventual `SoroushVahidi/llm-serving-scheduler-portability`
Hugging Face dataset. **Not published yet** — this document and the
`robustbench.dataset.lssp_release_contract` module define the target
structure; the actual `hf_fs_write`/upload step is Query-3 scope.

## 1. Why a separate release from GitHub

The GitHub repository (this one) carries code, tests, docs, and the paper
source. It deliberately does **not** carry the bulk scientific dataset: the
18,720-cell campaign matrix and its six canonical analysis outputs total
~110MB uncompressed and are the kind of large, versioned scientific
artifact Hugging Face Datasets exists for. Splitting this way lets a
reviewer `pip install` the code without a multi-hundred-MB clone, and lets
a data-only consumer load the dataset without cloning code at all.

## 2. What is LSSP-derived vs. third-party

Two categories, never mixed in one directory:

- **Third-party source data** (BurstGPT, Azure-2024, Bailian/Qwen): the raw
  traces LSSP workload windows are sampled from. **Not included as raw
  files in this release** — see §4 (license/redistribution).
- **LSSP-derived data**: everything computed by this project from those
  sources (window samples, region assignments, the 18,720-cell campaign
  matrix, analysis outputs). This is the actual release payload.

## 3. Directory structure

```
llm-serving-scheduler-portability/
  README.md                          # dataset card (docs/LSSP_HF_DATASET_CARD_DRAFT.md)
  manifests/
    phase10/  ranking_portability_pilot_v2_windows_index.json
    phase11/  ranking_portability_phase11_raw_fifo_calibration.json
              ranking_portability_phase11_region_assignments.json
    phase12/  ranking_portability_phase12_campaign_freeze.json
              ranking_portability_phase12_shard_plan.json
              ranking_portability_phase12_raw_shard_hashes.json
              ranking_portability_phase12_repaired_shard_hashes.json
  campaign/
    raw/          # per-shard scheduler_outcomes rows, pre-provenance-repair
    enriched/      # per-shard rows + consolidated.json (post-repair; the
                    # admitted input to the frozen Phase-12 analysis)
  analysis/
    canonical/     # the six frozen Phase-12 analysis-contract outputs,
                    # hashes pinned exactly as generated -- never re-derived
    table_data/    # paper/generated/table_data/*.json (RQ1-RQ5 inputs)
  real_vllm/
    provenance/    # engineering environment manifest, fidelity doc
                    # (RQ6 has no scientific data yet -- this subtree is
                    # empty of outcomes until REAL_VLLM_SCIENTIFIC_VALIDATION
                    # actually runs)
  schemas/
    ranking_portability_cell_result_v1.md   # from src/.../ranking_portability/schema.py
    telemetry_v1.md                          # from src/.../simulator/telemetry.py
  checksums/
    release_checksums.json           # every file in this release, SHA-256
  LICENSES/
    THIRD_PARTY_SOURCES.md           # per-source license + acquisition instructions
```

This intentionally deviates from a generic "workloads/descriptors/windows/
indices" split in favor of grouping by *pipeline phase* (10/11/12), because
that is how this project's own provenance chain (and its frozen-identity
hashes) are actually organized -- a HF user reproducing a manuscript table
needs the phase-12 canonical outputs and the phase-12 campaign matrix
together, not scattered across a generic taxonomy.

## 4. Tables (`robustbench.dataset.lssp_release_contract`)

Eight logical tables, four buildable now from already-frozen manifests
(never touch a scheduler outcome), two gated on the validated consolidated
artifact (already exists, staged, not yet packaged), one identity-only,
one reserved for extension configs not yet cleared for inclusion:

| Table | Rows | Buildable now | Source |
|---|---|---|---|
| `workload_windows` | 120 | Yes | Phase-10 windows index |
| `workload_descriptors` | 120 | Yes | Phase-10 windows index (embedded descriptor) |
| `load_region_assignments` | 720 | Yes | Phase-11 region-assignment provenance in the campaign-freeze manifest |
| `policy_registry` | 13 | Yes | Frozen policy panel (`docs/RANKING_PORTABILITY_POLICY_PANEL.md`) |
| `scheduler_outcomes` | 18,720 | Yes, from the validated `consolidated.json` (`73adf7d9...bde9c26`) | `scripts/dataset/build_lssp_release.py --consolidated-input ...` |
| `telemetry` | 18,720 (embedded in `scheduler_outcomes.telemetry`) | Yes, same input | same |
| `analysis_metadata` | 1 | Yes | the six canonical analysis artifacts' identity stamps |
| `extension_configs` | 0 | Not yet | pending `docs/EXPERIMENT_REUSE_AUDIT_20260902.md` clearance |

## 5. License / redistribution (full detail: `LICENSES/THIRD_PARTY_SOURCES.md`)

None of BurstGPT, Azure-2024, or Bailian/Qwen's **raw** files are included
in this release, independent of license permissiveness. This project has
consistently treated all three as read-only-referenced from their
canonical upstream location (`docs/DATA_ACQUISITION_STATUS.md`,
`docs/DATA_LICENSE_AUDIT.md`) rather than duplicated, and the HF release
preserves that convention. What ships instead: the derived, LSSP-specific
artifacts (window samples, descriptors, region assignments, scheduler
outcomes) plus exact acquisition instructions (canonical repo, release
tag/commit, and the SHA-256 this project independently verified against
its own local copy) so a user can reconstruct the exact raw input if they
have their own license-compliant access to it.

## 6. Reproduction without rerunning 18,720 cells

`analysis/canonical/*.json` are the actual inputs `paper/scripts/
generate_phase12_tables_figures.py` reads (hash-gated against
`EXPECTED_HASHES`). A user who downloads only `manifests/` + `analysis/
canonical/` + `analysis/table_data/` can regenerate every manuscript table
and figure without ever touching `campaign/raw/` or `campaign/enriched/`
(65MB and 76MB respectively) -- those exist for independent verification
of the analysis step itself, not for routine reproduction.

## 7. Checksums

`checksums/release_checksums.json` carries one entry per released file.
The six canonical Phase-12 outputs and the admitted `consolidated.json`
retain their exact existing hashes (verified unchanged throughout this
project's Query-1/Query-2 audits) -- this release process never
recomputes or normalizes them.

## 8. Versioning and archival strategy

Recommended, not yet executed:

- **GitHub.** Cut a semantic or paper-specific tag (e.g. `v1.0.0` or
  `paper-v1`) at the exact commit the manuscript's Data/Code Availability
  statement will cite, and publish it as an immutable GitHub Release
  (source archive + release notes naming the exact commit SHA). Do not
  reuse or move a tag after publication; a corrected release becomes
  `v1.0.1`/`v1.1.0`, never a rewritten `v1.0.0`.
- **Hugging Face.** Use HF's built-in dataset revision/commit mechanism
  to pin a specific, citable snapshot at release time (a tag or the
  release commit's hash), paired one-to-one with the GitHub tag above.
  A later RQ6 addition is a new revision (e.g. `v1.1`), never an in-place
  rewrite of the `v1.0` files a reader may have already cited or hashed.
  Every release revision ships its own `checksums/release_checksums.json`
  so a specific past revision remains independently verifiable even after
  a newer one is published.
- **Persistent identifier (Zenodo or equivalent archival DOI).** Recommended
  sequence once content is final: (1) cut the GitHub release tag; (2) use
  Zenodo's GitHub integration (or an equivalent institutional archive) to
  mint a DOI against that exact tagged release, which also archives a copy
  independent of GitHub's own availability; (3) update `CITATION.cff` and
  the manuscript's Code/Data Availability statement to cite the DOI, not
  the mutable repository URL, as the primary citation target; (4) a
  Hugging-Face-side persistent identifier (e.g. via a DOI-issuing
  integration, if HF offers one at publication time) should be minted the
  same way for the dataset half. **No DOI has been minted for this
  project; this section documents the intended sequence only and is not
  authorization to mint one.**
- **What the manuscript should ultimately cite.** Once available, the
  manuscript's Data/Code Availability statement (`paper/sections/
  declarations.tex`) should cite the persistent archival DOI(s) as the
  primary identifier, with the live GitHub/Hugging Face URLs as secondary,
  human-navigable pointers -- not a branch name, which is mutable and not
  a stable scholarly identifier.
