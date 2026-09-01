# REPRODUCIBILITY_CONTRACT.md

Every generated artifact from this project (a results row, a figure, a table,
a dataset release row) must contain, or be linked via `provenance_manifest`
(`docs/DATASET_V2_SCHEMA.md`) to, all of:

- **Repository SHA** — this repo's own commit hash at generation time (never
  a source repo's hash for this project's own outputs; source-repo SHAs are
  recorded once in `docs/PROVENANCE.md`, not re-derived per artifact).
- **Experiment config hash** — SHA-256 of the resolved experiment config
  (after defaults are applied), not just the config file's on-disk hash.
- **Workload manifest hash** — `manifest_sha256` from the relevant file in
  `configs/splits/` (`docs/SPLIT_PROTOCOL.md`).
- **Policy registry version** — a version string bumped whenever
  `configs/policies/canonical_policy_registry.yaml` changes in a way that
  could affect results (new policy, changed provenance_class,
  changed primary_analysis flag).
- **Dataset-source versions/checksums** — from
  `configs/workloads/source_registry.yaml`.
- **Environment version** — Python version + a locked dependency set
  (`pyproject.toml` pins minimum versions only at bootstrap time; a future
  `requirements-lock.txt` should pin exact versions before Stage 2, following
  the precedent in `llm-serving-module-intervention-benchmark/requirements-lock.txt`).
- **Seed** — where relevant (per-cell, not per-run).

## Fixing the existing HF release's provenance weakness

`SoroushVahidi/llm-serving-scheduler-baselines` does not, as far as this
bootstrap's audit could confirm, resolve to a citable, permanent commit for
every row's generating code. This project's `provenance_manifest` table
(`docs/DATASET_V2_SCHEMA.md`, table 10) exists specifically so that **every
row of any future release can be regenerated from this repo's own commit
history alone** — no dependency on an external, possibly-rewritten or
possibly-deleted historical commit in another repository.

## Enforcement (bootstrap status)

Not yet enforced in code — `PolicyOutcomeRow`
(`src/robustbench/schemas/policy_outcome.py`) already requires
`experiment_version`, `code_sha`, and `config_hash` as non-optional fields
and `validate_policy_outcome_row` rejects a row missing them (see
`tests/test_windows_and_schema.py`). Wiring `code_sha`/`config_hash`
population automatically into the evaluation harness is Stage 0/1 work, not
done in this bootstrap.
