# STAT01 legacy and mathematical comparisons recovery

Start with [AMENDMENT.md](AMENDMENT.md): author decision, numerical definitions,
post-diagnosis method labels, exact reuse accounting, uncertainty budgets and the
unchanged stopping rule. Original STAT01 files are unchanged.

## Evidence and tests

- [Completed PR #13 audit](evidence/pr13-audit-summary.json): all 112,275 studies
  and 4,491 batches passed, zero integrity failures, original snapshots unchanged.
- [Exact source inventory](evidence/source-batches.json): per-batch metadata and
  artifact fingerprints consumed by recovery, derived from the checksum-verified
  PR #13 audit log.
- [31 legacy differences](evidence/legacy-differences.json): original port records
  that cannot be interpreted unchanged as exact historical-source decisions.
- [Local tests](evidence/tests-local-final.txt) and
  [pinned Wulver tests](evidence/tests-pinned.txt): **118 passed** in each environment.
  This includes 63 original tests, seven PR #13 diagnostic tests, and 48 recovery
  tests, including exact oracles, frozen-source equivalence, actual failing study,
  missingness, immutable reuse, checkpoint reconstruction, corruption rejection
  and single-submission gates.

The first development test exposed a naive harmonic-sum emulator that did not
match CPython 3.12's compensated built-in sum. Its failed log is retained as
`evidence/tests-development.txt.gz`; the emulator now explicitly retains the
pinned interpreter's sum primitive for the frozen BY contract. Exact BY uses a
separate rational harmonic constant. No tolerance or exception suppression fixes
that mismatch.

## Artifacts and identity

Every recovery batch contains `raw.npz`, `studies.json.gz` (unchanged original
eight-method records), `secondary.json.gz` (nine named additions), and
`integrity.json` (new run identity, original source fingerprints, hashes and
17-method sufficient statistics). Reused raw/record files are byte-for-byte
copies; no hard links or writes into the source deployment are used. Each batch
is independently validated on read-back before publication. Checkpoint recovery
reconstructs authority from these immutable batches.

`build_launch.py` creates a manifest only after recorded tests and original hashes
pass. `submit_once.py` rechecks the pinned test certificate and live preflight,
refuses duplicate attempts or an active recovery job, persists submission intent
before invoking Slurm, and never retries automatically. `recovery.sbatch` is CPU
only, four CPUs/8 GiB, at most nine hours. Monitoring stops within two minutes.

The deployment manifest and launch/startup record will be added as evidence
after freezing the code and submitting the single authorized recovery. A healthy
job is not completed computation or scientific calibration.
