# Reproducing STAT01

Do not rerun the observed-data M2 interval/sensitivity analyses. This directory contains a separate synthetic experiment. See PROTOCOL.md for population hypotheses, scenarios, methods, fixed precision looks and stopping rules; REUSE_AUDIT.md identifies reused evidence. Namespace 0 is engineering; namespace 1 is the scientific campaign.

## Local checks

From the repository root, activate the documented Python environment, then use a persistent TMUX session:

```bash
tmux new-session -d -s stat01-validation -n cpu \
 'export PATH=/home/soroush/modal-venv/bin:$PATH; bash research/lssp-stat01/checks.sh > research/lssp-stat01/evidence/validation.txt 2>&1'
```

Read the exit/PID/log once after the brief check. Prior logs must be preserved when repeating. This script runs focused tests, byte compilation, namespace-0 timing fixtures and Slurm syntax validation. It does not run a scientific campaign.

## Frozen deployment and identity

`launch.json` records the exact code commit, prospective protocol commit, all scenario specifications, method names, numerical environment, source hashes, seven unchanged historical reference files, seed namespaces and resource limits. The run ID is `stat01-` followed by the first 16 hexadecimal digits of the canonical JSON SHA-256. A separate staging hash check and the runner verify those files. The historical reference copy exists solely for synthetic-fixture equivalence tests; no historical outcome dataset enters the campaign.

The deployment contains `code/`, `reference/`, `launch.json`, `logs/` and `runs/<run-id>/`. Absolute paths and the actual single submission command are recorded in LAUNCH_REPORT.md. The provided campaign.sbatch requests general/standard, account ikoutis, 4 CPUs, 8 GiB, no GPU and 09:00:00, with automatic requeue disabled. BLAS uses one thread per worker. The runner stops scheduling batches after 8h45m.

## Resume and inspection

Each batch contains raw.npz (latent scores and masks), studies.json.gz (seeds, truth, all method decisions/intervals/endpoints) and integrity.json (identity, hashes and sufficient summaries). Complete directories are published atomically only after independent read-back validation. Partial directories are retained but never treated as complete. checkpoint.json is a convenience record; resume reconstructs state from verified immutable batches and rejects gaps, corruption, incompatible identities, and batches beyond prespecified stopping.

An explicitly authorized resume uses the same manifest and output directory:

```bash
"$STAT01_PYTHON" -u "$STAT01_ROOT/code/run.py" \
 --launch "$STAT01_ROOT/launch.json" --out "$STAT01_ROOT/runs/$STAT01_RUN_ID" --workers 4
```

Do not run this command on a login node or submit a duplicate job. Resume is technically supported, not automatically authorized. A later review should validate all batches and inspect completion.json, checkpoint.json, environment-*.json, slurm.exit, failure-*.json if present, and scheduled look-s*-n*.json summaries. No Monte Carlo confidence bounds are asserted at an arbitrary time-budget cutoff. Status COMPLETE_WITH_PRECISION_GAPS is distinct from meeting all precision objectives.

The historical selected-CI endpoint averages coverage within each emitting study, then across emitting studies; it is not pooled interval-weighted coverage. Ordinary fixed-contrast CI coverage and interval availability are separate endpoints. Compare methods only with their assumption status and sign/practical truth label visible. Do not reinterpret synthetic scores as serving performance or insert results into manuscript claims automatically.
