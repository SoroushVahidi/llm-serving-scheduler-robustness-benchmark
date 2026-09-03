# LSSP Artifact Reproducibility Prefreeze

Parent SHA:
`2b9a21fb58798292c95980d35d05e53b3c6f14f6`

Branch:
`research/lssp-artifact-repro-prefreeze-20260902`

Worktree:
`/home/soroush/repos/llm-serving-scheduler-lssp-artifact-repro`

This prefreeze is result-blind. It adds reviewer-facing reproducibility
commands, integrity verification, provenance snapshot generation, a synthetic
toy artifact path, CI-safe checks, and documentation. It does not inspect or
execute completed scientific campaign outcomes.

## Environment identities

Tier 1 - CPU-only benchmark validation:

- Python: `>=3.10` from `pyproject.toml`; CI uses Python 3.11.
- Install:
  `python -m pip install -e ".[dev]"`.
- Direct reviewer constraints:
  `requirements-artifact.txt`.
- Required packages: numpy, pandas, PyYAML, scipy, pytest.
- Outputs: local generated files under `artifacts/generated/`.
- Wulver: not required.

Tier 2 - CPU scientific simulation:

- Same Python/package contract as Tier 1.
- Wulver module documented by the Phase-12 freeze:
  `module load slurm/wulver`.
- Frozen full-window filesystem assumption:
  `/mmfs1/project/ikoutis/sv96/github/llm-serving-scheduler-ranking-portability-windows/artifacts/manifests/ranking_portability_pilot_v2_windows.json`
- Raw source data assumption:
  `/project/ikoutis/sv96/llmserveopt-data/datasets/{burstgpt_v2,azure_llm_2024,bailian_qwen}/raw/`
- Execution must use the explicit wrapper and confirmation flag, never
  `verify_artifact.sh`.

Tier 3 - real-system validation:

- Documented only in `docs/REAL_SYSTEM_VALIDATION_PLAN.md`.
- Requires future GPU/vLLM environment manifests.
- No real-vLLM command is executed or validated in this prefreeze.

Exact package versions for the active environment are recorded at reviewer
runtime by:

```bash
./scripts/artifact/verify_artifact.sh --quick
```

The snapshot path is
`artifacts/generated/lssp_artifact_repro_provenance_snapshot.json`.

## Validation entrypoints

- Quick smoke:
  `./scripts/artifact/verify_artifact.sh --quick`
- Full test suite:
  `./scripts/artifact/verify_artifact.sh --full-tests`
- Frozen manifest verification:
  `./scripts/artifact/verify_artifact.sh --validate-freeze`
- Explicit completed-result validation:
  `./scripts/artifact/verify_artifact.sh --validate-results PATH`
- Fabricated analysis fixture:
  `./scripts/artifact/verify_artifact.sh --analysis-fixture`
- Toy end-to-end:
  `./scripts/artifact/run_toy_reproduction.sh`

All validation commands export:

```text
LSSP_ARTIFACT_REPRO_PREFREEZE_RESULT_BLIND=YES
```

## Immutable hash verifier

Command:

```bash
LSSP_ARTIFACT_REPRO_PREFREEZE_RESULT_BLIND=YES \
  PYTHONPATH=src \
  python scripts/artifact/verify_immutable_artifacts.py
```

It verifies:

1. Phase-10 window hash.
2. Phase-10 compact index.
3. Phase-11 prelaunch freeze.
4. Phase-11 raw FIFO calibration.
5. Phase-11 region assignments.
6. Phase-12 campaign manifest hash.
7. Phase-12 full matrix hash.
8. Phase-12 shard-plan relationship.
9. Campaign expected cell count = 18,720.
10. Shard count = 64.

It returns nonzero on mismatch and never executes simulator cells.

## Toy reproduction contract

Command:

```bash
./scripts/artifact/run_toy_reproduction.sh
```

The toy fixture is generated data and records:

```text
SYNTHETIC_FIXTURE_NOT_SCIENTIFIC_EVIDENCE = YES
```

The fixture includes fake sources/windows, multiple policies, multiple
regions, rep0/rep1, zero completion, undefined conditional metrics,
normalized KV demand above 1, and a deliberate ranking change for analysis
code testing. It writes a miniature package under
`artifacts/generated/toy_reproduction/dataset_package/`.

The parallel analysis-prefreeze and dataset-release prefreeze worktrees own
the final scientific analysis and dataset-build implementations. This branch
keeps integration hooks clean and does not copy their in-flight uncommitted
code.

## Provenance snapshot schema

`scripts/artifact/write_provenance_snapshot.py` writes a JSON object with:

- repository SHA and branch;
- parent SHA;
- campaign freeze SHA;
- Phase-12 full-matrix hash;
- five immutable Phase-10/11 hashes;
- Python version and executable;
- package versions;
- OS/kernel information;
- selected environment variables;
- Wulver module assumptions;
- filesystem assumptions;
- simulator, policy-registry, schema, and telemetry implementation hashes;
- telemetry and cell schema versions.

This format is intended to be included in final dataset releases.

## Reviewer guide

Reviewer-facing instructions are in:

`docs/ARTIFACT_EVALUATION_GUIDE.md`

## Resource estimates

- Phase-12 campaign cells: 18,720.
- Shards: 64.
- Frozen shard-plan estimate:
  `113,975.99999999882` seconds, approximately 31.7 CPU-core-hours.
- Laptop quick checks and toy reproduction: seconds to a few minutes.
- No real-vLLM runtime estimate is claimed.

## Result-blindness guarantee

This prefreeze did not:

- execute real Phase-12 scientific cells;
- inspect campaign output directories;
- inspect scheduler-performance outcomes;
- run real statistical analysis;
- publish a dataset;
- run real-vLLM experiments.

Allowed and used:

- tracked frozen manifests;
- code and docs;
- synthetic fabricated fixture rows;
- existing result-blind validators.

## Implementation hashes

The provenance snapshot records live implementation hashes at reviewer
runtime. The frozen Phase-12 campaign manifest already records execution-file
hashes for the simulator, policy registry, schema, telemetry, synthesis, and
campaign modules. The artifact verifier confirms those frozen identities are
still connected to the manifest hash and full-matrix hash.

## Existing infrastructure reused

- `pyproject.toml` for package and dependency declaration.
- Existing Phase-12 manifest validator:
  `scripts/ranking_portability/validate_phase12_campaign_freeze.py`.
- Existing dry-run/execute separation:
  `scripts/ranking_portability/run_phase12_campaign_shard.py`.
- Existing Slurm generator:
  `scripts/ranking_portability/generate_phase12_sbatch.py`.
- Existing schema and telemetry validators:
  `src/robustbench/ranking_portability/schema.py` and
  `src/robustbench/simulator/telemetry.py`.
- Existing reproducibility docs:
  `docs/REPRODUCIBILITY_CONTRACT.md`, `docs/ARTIFACT_HASH_LEDGER.md`,
  `docs/DATASET_V2_SCHEMA.md`, and
  `docs/RANKING_PORTABILITY_PHASE12_CAMPAIGN_PRELAUNCH_FREEZE.md`.
- Generic artifact-review precedent from
  `llm-serving-module-intervention-benchmark` docs/scripts was used only as
  pattern guidance, not copied as scientific evidence.

## Prefreeze checklist

- Reviewer quick command: implemented.
- Immutable hash validator: implemented.
- Provenance snapshot writer: implemented.
- Toy reproduction: implemented.
- CI-safe quick check: implemented in `.github/workflows/artifact-safe.yml`.
- Large-artifact strategy: documented.
- Reproducibility levels: documented.
- Final completed-result analysis integration: pending analysis-prefreeze
  branch stabilization.
- Final dataset builder integration: pending dataset-release prefreeze branch
  stabilization.
- External dataset upload/DOI/Hugging Face publication: not performed.

LSSP_ARTIFACT_REPRO_PREFREEZE_VALID = YES

LSSP_ARTIFACT_REPRO_PREFREEZE_RESULT_BLIND = YES
