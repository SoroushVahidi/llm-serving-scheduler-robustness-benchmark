# STAT01 validation failure: diagnosis and decision gate

This is a diagnosis and audit-tools change, not an applied statistical repair.
The failed deployment, frozen protocol, production methods, reference validator,
historical source, C01 and M2 are unchanged. No recovery is authorized by these
tools. A scientific definition must be selected before changing the procedure.

## Exact reproduction

Original execution commit: `454168a005240341dc5a5ae88ac32c4b130f6bc5`.
Original job: `1438961`, failed with exit `1:0` at 2026-10-22 04:49:36 UTC.
Original root:
`/project/ikoutis/sv96/github/llm-serving-scheduler-lssp-stat01-454168a00524/`.

The first failing replicate in the partial batch is **scenario 11 (`ar_reversal`),
replicate 6628, campaign namespace 1, master seed 2026102201, B=2000**.
Replicates 6625–6627 passed the original referee in the bounded reproducer.
The reproduction used the frozen Python 3.12.13 / NumPy 2.5.2 / SciPy 1.18.1
environment and unmodified frozen source. The exact record, all 43 eligible
p-values, rejection vectors and raw-array hashes are in
`evidence/failing-study.json`.

Procedure: `historical_screened_BH`. Hypothesis 47 is sources (0,1), policies
(6,9). Its bootstrap side p-values are 0.013 and 0.05, so the combined p-value
is 0.05. Both percentile intervals exclude zero. It is the unique maximum
eligible p-value, ranked 43 of 43. All observations are present; no missingness,
NaN filtering or tied maximum is involved. The original production and reference
rejection vectors differ only at hypothesis 47.

| Calculation | Value / decision |
|---|---|
| Mathematical BH critical value `(1/20) * 43/43` | `1/20`, include equality |
| Production `.05 * 43 / 43` | `0.049999999999999996`, excludes p=.05 |
| Referee `.05 * 43 <= .05 * 43` | `2.15 <= 2.15`, includes |
| Frozen historical `(43 / 43) * .05` | `.05`, includes |

The production threshold is one representable float below the stored `.05`.
Its step-up cutoff is 42 instead of 43. This is an observed floating-point
evaluation-order defect, not an inference from the error message alone.

Exact reproducer (read-only; use the pinned Python, set bytecode writing off):

```bash
env PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 \
  /project/ikoutis/sv96/github/llm-serving-scheduler-robustness-benchmark/.venv312/bin/python \
  tools/diagnose.py \
  --frozen-code /project/ikoutis/sv96/github/llm-serving-scheduler-lssp-stat01-454168a00524/code
```

Run from the separate diagnosis deployment documented in `AUDIT_STATUS.md`.
No Slurm experiment runner is called by this reproducer.

## Why swapping multiplication order is not a sufficient mathematical repair

The protocol promises both BH at q=.05 and equivalence to the frozen historical
procedure. The frozen historical implementation uses `(rank/m)*q`; it is itself
not exact BH at every attainable bootstrap equality boundary. For example,
p=.035 at rank 7/10 has exact threshold .035, but that implementation evaluates
the threshold as `.034999999999999996` and excludes equality. The referee also
fails an attainable boundary: at rank 35/50, `.035*50` becomes
`1.7500000000000002`, exceeding `.05*35 == 1.75`.

An exhaustive diagnostic over family sizes 1..165 and attainable B=2000
bootstrap equality boundaries finds 8 false exclusions for the production
expression, 5 for the referee expression, and 19 for the historical expression.
These are counts of scalar critical-value comparisons, **not counts of affected
archived studies**. Full-family step-up cutoffs and interval support still matter.
See `evidence/boundary-audit.json`.

The independent exact-BH diagnostic reconstructs the integer bootstrap numerator
only when `numerator/1000` exactly equals the stored float, then compares
`20 * numerator * m <= 1000 * rank` using integers. No epsilon, tolerance or
near-boundary coercion is used. A separately implemented Fraction-based adjusted
p-value oracle uses reverse cumulative minima. It agrees in deterministic tests
covering the observed vector, ties, permutations, empty families, step-up behavior
and bootstrap grid cases. Off-grid and neighboring-float inputs are rejected by
this diagnostic rather than rounded into the grid.

## Scientific decision required before repair or recovery

Two defensible targets differ at these boundaries:

1. **Actual frozen historical procedure.** Preserve its floating-point behavior
   for the historical baseline, independently validate that explicit definition,
   and disclose that it differs from ideal mathematical BH at some boundaries.
2. **Exact mathematical procedure.** Use inclusive exact critical comparisons
   with a documented treatment of bootstrap rational probabilities and numerical
   analytic probabilities. Label this a corrected procedure, not exact
   reproduction of the historical implementation. BH/BY/Holm and their
   independent validators must be checked under the selected representation.

The first option serves historical implementation calibration; the second serves
calibration of an idealized corrected procedure. Silently choosing either would
change one of the frozen protocol's promises. The author was asked to select the
target. Until then no production/reference repair is applied, no prior result is
declared invalid solely from a diagnostic alternative, and no recovery is launched.

## Evidence reuse and limitations

The initial read-only inventory examined all 4,491 finalized batch metadata
records: 112,275 studies, 1,626,455,353 bytes of referenced artifacts, contiguous
25-study indices, with no metadata inconsistencies found. Frozen code/reference
hashes and launch identity matched in the preceding bounded checks. The checkpoint
lags finalized outputs by 75 studies in scenarios 9, 10 and 12. The partial
scenario-11 directory is preserved and excluded from finalized counts.

The persistent audit rechecks every artifact hash, invokes the **original**
independent referee on saved raw arrays/records, compares sufficient statistics,
and records which historical rejection decisions differ under the two candidate
BH interpretations. It generates no random studies and overwrites no original
artifact. It writes a separate append-only batch evidence log and audit progress.
It is not a corrected-code compatibility certificate; in particular its candidate
comparison is BH-only and does not approve a BY/Holm repair. Final safe-reuse and
recomputation counts require the scientific decision and completed audit.

The original referee can agree with production while both are mathematically
wrong at a boundary. An original-validator pass therefore establishes a narrower
fact than validity under corrected mathematical procedures. Data integrity, code
correctness, completed computation and scientific calibration are separate claims.
No calibration success or publication readiness is asserted.
