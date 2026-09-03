# LSSP Artifact Evaluation Guide

This guide is for external artifact reviewers. It describes how to validate
the repository and future dataset submission without accidentally executing
the scientific campaign or inspecting unpublished scientific outcomes.

`LSSP_ARTIFACT_REPRO_PREFREEZE_RESULT_BLIND = YES`

## 1. What the artifact contains

- Source code for the CPU simulator, scheduler policy registry, workload
  adapters, ranking-portability schemas, and Phase-12 campaign manifest logic.
- Frozen, repository-contained manifests under `artifacts/manifests/`.
- Result-blind integrity validators under `scripts/artifact/` and
  `scripts/ranking_portability/`.
- A fabricated toy fixture that exercises schema validation, consolidation,
  simple ranking-code paths, and miniature dataset export without using real
  LSSP outcomes.
- Documentation for future large artifacts and real-system validation.

The repository does not contain the completed 18,720-cell outcome dataset in
this prefreeze state.

## 2. What can be reproduced on a laptop

Level-1 integrity checks and the toy end-to-end fixture are laptop-safe:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
./scripts/artifact/verify_artifact.sh --quick
./scripts/artifact/run_toy_reproduction.sh
```

These commands do not submit Slurm jobs, pass `--execute`, start real-vLLM,
or read any live campaign result directory.

## 3. What requires a cluster

Re-running the frozen 18,720-cell CPU simulation campaign is Level-3
simulation reproducibility. It is expected to require Wulver or an equivalent
CPU cluster because the frozen shard plan contains 64 shards and estimates
approximately 31.7 CPU-core-hours.

Cluster execution is intentionally outside `verify_artifact.sh`. The explicit
execution wrapper is:

```bash
LSSP_ALLOW_SCIENTIFIC_EXECUTION=YES \
  ./scripts/artifact/run_frozen_campaign.sh \
  --confirm-scientific-execution --execute-shard 0
```

That command runs one shard locally. Slurm users should generate and inspect
the sbatch file with:

```bash
python scripts/ranking_portability/generate_phase12_sbatch.py
```

Then submit under the local cluster policy. The generator writes a dry-run
sbatch by default; it does not call `sbatch`.

## 4. What requires GPUs

Level-4 real-system replication requires GPU serving infrastructure and a
future real-vLLM validation manifest. This branch documents that requirement
only in `docs/REAL_SYSTEM_VALIDATION_PLAN.md`; it does not execute real-vLLM
and does not fabricate runtime estimates.

## 5. Quick validation

```bash
./scripts/artifact/verify_artifact.sh --quick
```

Runs:

- Python/package import sanity check.
- Result-blind provenance snapshot generation to `artifacts/generated/`.
- Immutable manifest/hash checks.
- Focused schema, policy registry, dry-run, and artifact tests.
- Fabricated toy fixture validation and miniature export.

Expected terminal marker:

```text
ARTIFACT_QUICK_VERIFY_PASS = YES
```

## 6. Full software tests

```bash
./scripts/artifact/verify_artifact.sh --full-tests
```

This runs the repository pytest suite. It must remain CPU-only and must not
launch the Phase-12 campaign.

## 7. Frozen campaign verification

```bash
./scripts/artifact/verify_artifact.sh --validate-freeze
```

This verifies:

- Phase-10 window hash.
- Phase-10 compact index hash.
- Phase-11 prelaunch freeze hash.
- Phase-11 raw FIFO calibration hash.
- Phase-11 region-assignment hash.
- Phase-12 campaign manifest hash and freeze identity.
- Phase-12 full-matrix hash.
- 18,720 expected campaign cells.
- 64 shards.
- Shard-plan coverage and manifest relationship.

It also delegates to the existing independent matrix validator:
`scripts/ranking_portability/validate_phase12_campaign_freeze.py`.

## 8. Running the toy end-to-end example

```bash
./scripts/artifact/run_toy_reproduction.sh
```

The fixture is fabricated and labels itself:

```text
SYNTHETIC_FIXTURE_NOT_SCIENTIFIC_EVIDENCE = YES
```

It contains fake sources/windows, three toy policies, two regions, rep0/rep1,
a zero-completion case, an undefined conditional TTFT metric case, telemetry
with normalized KV demand above 1, and a deliberate ranking change between
regions. Outputs are written under `artifacts/generated/toy_reproduction/`,
which is ignored by Git.

## 9. Reproducing the 18,720 campaign

Inputs:

- `artifacts/manifests/ranking_portability_phase12_campaign_freeze.json`
- `artifacts/manifests/ranking_portability_phase12_shard_plan.json`
- The frozen full window manifest documented in
  `docs/RANKING_PORTABILITY_PHASE12_CAMPAIGN_PRELAUNCH_FREEZE.md`.
- The same simulator/policy implementation identities recorded in the
  campaign manifest.

Command shape:

```bash
LSSP_ALLOW_SCIENTIFIC_EXECUTION=YES \
  ./scripts/artifact/run_frozen_campaign.sh \
  --confirm-scientific-execution --execute-shard SHARD_ID
```

Expected outputs are shard checkpoint JSON files under
`artifacts/campaign_results/<freeze-prefix>/`. Those outputs are not tracked
in Git and are not read by validation commands unless a reviewer passes an
explicit path.

## 10. Consolidating completed results

Future completed-campaign validation is explicit-path only:

```bash
./scripts/artifact/verify_artifact.sh --validate-results path/to/completed.json
```

This branch provides schema and manifest-membership validation for a supplied
artifact. The full consolidation implementation is owned by the parallel
Phase-12 statistical-analysis prefreeze branch and should be integrated by
cherry-pick or merge after that branch stabilizes.

## 11. Reproducing statistical analysis

The result-blind command available in this branch is:

```bash
./scripts/artifact/verify_artifact.sh --analysis-fixture
```

It uses fabricated fixture rows only. Once scientific results exist, the
analysis-prefreeze branch should provide the final released-outcome analysis
entrypoint. That future command must consume an explicit completed artifact
path and must not default to a private campaign output directory.

## 12. Building the public dataset

This prefreeze branch does not publish a dataset. The dataset-release
prefreeze branch owns the final builder and release validator. The artifact
package reserves this contract:

- Inputs: completed 18,720-cell outcome artifact, frozen manifests,
  provenance snapshot, schema documentation.
- Outputs: dataset package files plus checksums.
- Hash connection: every external file must publish its SHA-256 and the
  campaign freeze/full-matrix hashes it corresponds to.

## 13. Real-system validation

Real-system validation is Level 4. It requires a separately frozen hardware
manifest, vLLM/native serving environment, scheduler mapping, workload
selection, and repetition plan. See `docs/REAL_SYSTEM_VALIDATION_PLAN.md`.
No real-system command is run by this artifact package.

## 14. Expected compute/storage

- Integrity checks: seconds to a few minutes on a laptop.
- Toy end-to-end fixture: seconds, no Wulver requirement.
- Full pytest suite: CPU-only, expected to be practical locally.
- Frozen campaign: 18,720 cells, 64 shards, approximately 31.7
  CPU-core-hours from the frozen shard plan.
- Completed outcome dataset, analysis outputs, and release bundles are
  expected to be too large or too mutable for source control.

No real-vLLM runtime estimate is claimed in this branch.

## 15. Troubleshooting

- If imports fail, recreate the virtual environment and run
  `python -m pip install -e ".[dev]"`.
- If `verify_immutable_artifacts.py` reports a hash mismatch, stop; the
  tracked frozen manifests no longer match the prefreeze contract.
- If `--validate-results` fails because a path is missing, pass the completed
  artifact path explicitly. There is intentionally no default.
- If Wulver modules are unavailable, Level-1 and toy checks should still work;
  only Level-3 campaign execution needs the cluster environment.

## 16. Artifact integrity hashes

- Phase-10 window:
  `0d1aa06ccbee352207327ea369ae75f12e91c0cda006c813a41b381effd29eef`
- Phase-10 compact index:
  `d78ec1087fedae02174ca093a9860c70468be336ccb1d7e6de756c81ba331e53`
- Phase-11 prelaunch freeze:
  `e2564ea9484190832de50f63173c4b73ae054d6ae7008bb4ff6648c8dc917f7b`
- Phase-11 raw FIFO calibration:
  `201caaf04476ad8737ef6079fc0d6cb4e864601711d0b96c88750a717d8b2a6a`
- Phase-11 region assignments:
  `9fcb92f9ea1206ce185194527ada35d0e3b91bf4904be7ae23ba9ea997c17574`
- Phase-12 campaign manifest file:
  `44a81e98d9a3fa6646bd716125726bf732530d243a54d0952e98b20fda1d564a`
- Phase-12 campaign freeze:
  `81fa3d9b48a2241001e6820942d4542dcc5b5e30973ad9d2786e72972494f57a`
- Phase-12 full matrix:
  `832d96d7ff4d5e8843c233a6a4708bbbbc578ef6b65307c37f5ac127c62c1ccf`
- Phase-12 shard plan file:
  `27d2740c5f1585f1b781680a813890c473236bbd2feb8e3a669bd2cf7d857511`

## Reproducibility levels

Level 1 - Integrity reproducibility:
inputs are tracked manifests and code; command is
`./scripts/artifact/verify_artifact.sh --validate-freeze`; output is a pass/fail
hash report; deterministic.

Level 2 - Analysis reproducibility:
inputs are a released completed-outcome artifact plus frozen manifests; command
will be the analysis-prefreeze entrypoint after integration; outputs are tables,
statistics, and dataset-ready summaries; deterministic except for explicitly
seeded/bootstrap intervals if the analysis plan uses resampling.

Level 3 - Simulation reproducibility:
inputs are frozen manifests, full frozen windows, and CPU simulator code;
command is the explicit scientific-execution wrapper per shard; outputs are
18,720 cell results; deterministic by fixed inputs and rep0/rep1 identity
checks, subject to Python/platform floating-point drift.

Level 4 - Real-system replication:
inputs are a future hardware/vLLM manifest and targeted workload/scheduler
plan; command is not implemented in this branch; outputs are hardware
validation measurements; nondeterministic aspects include GPU scheduling,
driver/runtime versions, thermal/load variation, and serving-engine changes.

## Large-artifact strategy

Keep Git for source code, schemas, freeze manifests, documentation, and small
synthetic fixtures. Store large artifacts externally:

- Raw source manifests: project storage or archival object storage with
  per-file SHA-256, source license records, and source version metadata.
- 18,720 outcome dataset: Hugging Face Dataset and/or archival DOI storage,
  with checksums and the Phase-12 campaign freeze/full-matrix hashes.
- Analysis results: release bundle adjacent to the dataset, with checksums and
  explicit input artifact hashes.
- Dataset release files: Hugging Face for reviewer-friendly access plus DOI
  archive for permanence.

No upload is performed by this branch.

## Artifact badge readiness

Available: repository-side source, manifests, docs, and commands are prepared;
external outcome and archive locations remain to be filled after results exist.

Functional: quick validation and toy end-to-end checks are implemented; full
completed-outcome validation depends on the analysis/dataset prefreeze branches.

Reusable: environment tiers, provenance snapshot schema, and command contracts
are documented; final reuse improves once public dataset files and DOI/HF links
exist.

Reproduced/Reproducible: Level-1 is ready now; Level-2 requires released
outcomes; Level-3 requires running the frozen campaign; Level-4 requires future
GPU validation.
