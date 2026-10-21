# MGPU00 validation ledger

**MGPU01 follow-up:** job 1434644 ultimately failed readiness after 892 allocated
seconds; all 15 full-device identity checks passed, but no inference ran.
[The MGPU01 report](../mgpu01/REPORT.md) preserves final evidence, resolves the
unsupported chunked-prefill configuration, and records why no further GPU retry
was submitted. Entries below remain the historical MGPU00 ledger.

Date: 2026-10-21. Branch: `research/lssp-mgpu00-integrity-20261021`.
Base: `e73a3b711b65f9c181ff9a2674007efca22f1b65`.

## Completed before physical submission

- Exhaustive 240-task historical audit: 240 MIG_VERIFIED, zero FULL_GPU_VERIFIED,
  zero UNVERIFIABLE allocation classes. Device/parent UUID mappings remain unknown.
- Audit JSON SHA-256:
  `b310b79a1728a3c84563f29cc24ae2b75d1b5274c1daa94c13b5826bde83fb38`.
- Local tests: **27 passed**, 14 existing Torch deprecation warnings, 9.12 seconds.
  Evidence: `artifacts/mgpu00/local-validation/pytest.log` and `pytest.xml`.
  Command: `PYTHONPATH=src /home/soroush/modal-venv/bin/python -m pytest tests/mgpu00 tests/test_anwg_metric.py -q`.
- Shell syntax, Python compilation and `git diff --check` passed.
- Draft manuscript compiled with pdflatex/bibtex/pdflatex/pdflatex, without
  undefined citations/references. Generated PDF is a separate local artifact at
  `artifacts/mgpu00/draft-manuscript/main.pdf`; the released PDF is unchanged.
- Existing account `ikoutis` grants low QoS; the `gpu` partition accepts it.
  Full A100 resource type is `gpu:a100`; `gpu:a100_10g` is excluded from the smoke.

## Physical validation

Job **1434545** ran code commit `3aaaa3012193091519cbdf5e5e27ea87a9f4b25e`
and failed the initial independent full-A100 verification gate before any server
or replay started. Slurm allocated one `gpu:a100` on `n0003` for 156 seconds:
**0.043333 allocated GPU-hours**. No retry was attempted. Detailed command,
logs, limitations and failure are in [`SMOKE_JOB_1434545.md`](SMOKE_JOB_1434545.md).
The compound probe error did not preserve the raw CUDA/NVML record, so the exact
failed identity field remains unknown. No pilot, DP or multi-node job was run.

## Pilot decision

**NO GO.** General prefill/KV-pressure SLAI fidelity and TP2 behavior remain
unvalidated. The guarded adapter explicitly rejects unsupported regimes.
Passing the restricted single-GPU smoke cannot resolve these blockers.
The 144-run proposal is a non-executable specification; numeric pilot GPU-hour
estimates await representative full-device/TP2 measurements and calibration.

Historical files, measurements, release tags and published dataset versions are
unchanged. No GitHub Actions are used: pushed commits include `[skip ci]`, which
suppresses this repository's push/pull_request workflow triggers.
