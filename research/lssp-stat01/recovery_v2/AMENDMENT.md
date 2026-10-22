# STAT01 recovery v2: author-approved post-diagnosis comparisons

Decision received 2026-10-22, after the failed experiment and PR #13 audit:
preserve the exact historical implementation for retrospective calibration and
also compare mathematically corrected multiple-testing procedures. This file is
an amendment, not a replacement or retrospective edit of the frozen protocol.

## Three distinct meanings

1. **Original eight STAT01 implementations.** Their IDs, code, streams, raw data,
   p-values, rejection vectors and all endpoints remain unchanged. In particular,
   the original ID `historical_screened_BH` describes the frozen STAT01 port,
   whose floating-point behavior is not fully identical to historical source.
   It must not be relabeled as mathematically exact BH or exact historical code.
2. **`legacy_source_screened_BH`.** An additional retrospective comparison of the
   actual frozen historical routine. It uses `(rank/m)*q`, inclusive binary64
   comparison, stable sorting, NaN rank omission, the existing bootstrap streams,
   original screening family and interval-support filter. Independent tests use
   SHA-verified frozen historical code, including full scenario 11 / replicate
   6628 and every attainable bootstrap equality boundary up to family size 165.
3. **Eight `exact_<original_method_id>` comparisons.** These add mathematical
   BH/BY/Holm corrections with exact alpha=1/20 and an exact rational harmonic
   constant for BY. Their generators, screens, intervals, candidate-best sets,
   component statistical assumptions and selected-interval definitions remain
   those of the explicitly linked base method. Only multiple-testing probability
   representation and rejection decisions change. This does not correct invalid
   p-values, historical screening bias, missingness assumptions or finite bootstrap
   calibration. Exact arithmetic alone is not statistical validity.

All nine additions are labeled `POST_DIAGNOSIS_2026_10_22`. Original code and
historical files are imported read-only from the original frozen deployment.

## Numerical contracts and independent validation

Historical bootstrap tail p-values have form `2*k/2000`. Reconstruct integer k
only when the frozen binary64 expression reconstructs the stored float exactly;
reject off-grid values, without any tolerance. Historical plus-one probabilities
are reconstructed as `min(1,(2*k+2)/2001)` from the saved uncorrected tail counts,
not from their rounded plus-one floats. Group-bootstrap probabilities are
`min(1,2*k/2001)` with k>=1; min/max IUT/orientation combinations preserve this
grid. Untested probabilities remain exactly one. No bootstrap resampling is
needed to recover these rational values from verified saved records.

Analytic p-values are the exact dyadic rationals represented by their finite
binary64 values (`as_integer_ratio`). No decimal-string rationalization, epsilon,
near-boundary snapping, or inferred infinitely precise tail probability is used.
For example, represented `.05` is slightly larger than mathematical 1/20, so
an analytic dyadic `.05` is excluded by a mathematical 1/20 boundary, whereas
a bootstrap p=50/1000 is exactly on it and included. NaN/infinite/out-of-domain
p-values are rejected in mathematical comparisons. This deterministic numerical
convention does not eliminate approximation error in the tail-probability solver.

The mathematical production implementation uses rational critical ranks. Its
independent referee uses rational adjusted p-values with reverse cumulative
minima (BH/BY) or forward cumulative maxima (Holm), separate probability
reconstruction, and no production helper imports. The original eight are checked
against an explicit frozen binary64 contract, not against the mathematically
different rearranged inequalities that caused the old referee failure. An
independent emulator rounds exact arithmetic at each specified floating operation;
the pinned CPython 3.12 built-in sum is retained for the frozen BY harmonic sum.
This preserves implementation behavior, not ideal mathematical correctness.

All 16 endpoints are independently reconstructed. Truth, identities, raw shape,
mask rules, p-value domains and method inventories are checked. Every new batch
undergoes hash verification and independent read-back before atomic publication.
No validation exception is suppressed. The old failing record still fails the
unchanged original referee in regression tests; it passes the explicitly revised
implementation contract, with different legacy and mathematical outputs retained
separately rather than replacing the original decision.

## Reuse and missing work

PR #13's full audit completed at 2026-10-22 13:57:48 UTC, exit 0. It checked all
4,491 finalized batches / 112,275 studies, hashes, original independent referee,
raw arrays/masks and sufficient statistics. No failed batches or changed source
snapshots were found. Its evidence log SHA-256 is
`7ac3221aa528545cfa839684c7ecddee8be67abb8bad5d98c5dbef8a33516c4d`.

All **112,275 raw studies and all eight original result records are reusable**.
Zero raw studies are invalidated. Raw and original compressed record files are
copied byte for byte into a distinct deployment, never hard-linked or overwritten.
Every reused batch is bound to its original metadata/artifact hashes and source
path. Reuse checks those hashes again before reading and rejects changes.

Exactly **31** original `historical_screened_BH` study records differ from the
actual historical-source interpretation (IDs in evidence/legacy-differences.json).
They remain valid records of the frozen port, but cannot be used unchanged as
claims about exact historical-code behavior. The added legacy results recompute
those decisions/endpoints. All nine additions are derived from saved p-values,
truth and interval diagnostics for every saved study; no original synthetic study
needs regeneration. Changed summaries are recomputed, not copied as authoritative.

The existing source inventory is 2,000 studies for scenario 3, 4,000 for scenario
17, 6,650 for scenarios 0,1,2,4,5,6,7,8,9,10,12, and 6,625 for scenarios
11,13,14,15,16. Scenarios 3/17 retain their original precision stops. The remaining
16 scenarios have their next and last prespecified look at 8,000. Therefore
**21,725 missing studies** remain on the original stopping plan, for a final
planned total of 134,000 (unless time/resource failure interrupts recovery).
The empty partial batch at scenario 11 / start 6625 remains preserved and is not
treated as finalized. Missing studies use the same original campaign seeds and
stream definitions; no generator, bootstrap count or experimental parameter changes.

## Monte Carlo uncertainty and stopping

The original eight-method summaries retain the original per-endpoint/look
allocation `.05/(18*8*16*5)` and their identities. They are emitted in
`original_prespecified`, with exactly the original sufficient statistics and
precision stopping rule. Original reported results are not overwritten.

Separate `expanded_postdiagnosis` summaries cover **17 methods** (8 frozen, one
actual historical source, eight exact comparisons), 18 scenarios, 16 endpoints
and five possible looks. Their per-endpoint/look allocation is
`.05/(18*17*16*5)`. All 17 methods receive bounds from this expanded family; one
must not combine old eight-method bounds with new bounds and claim the same joint
coverage. The same empirical-Bernstein formula is used, including conditional
availability counts. The added comparisons do not change original stopping:
only the original eight drive precision stops, and secondary precision may be
inadequate at those stops. No additional unplanned look drives a decision.

The method amendment was selected after diagnosis and inspection of earlier
records. Expanding the union-bound budget accounts for the explicitly enumerated
endpoints/looks, but does not erase post-diagnosis method-selection limitations
or make these additions prospectively registered. Any nominal simultaneous claim
for additions is conditional on this fixed amended family; unconditional claims
covering arbitrary data-dependent method selection are not established. Report
these results as post-diagnosis comparisons, not fresh prospective confirmation.

## Recovery authorization and completion boundary

Launch at most one CPU Slurm job after full audit evidence, source identity,
local/pinned tests and manifest preflight pass. Four CPUs, 8 GiB, no GPUs,
09:00:00 maximum allocation; stop scheduling at 8h45m, checkpoint immutable
batches and partial/time-budget status. Distinct run identity binds the source
audit, every source-batch fingerprint, original launch and recovery code hashes.
No automatic further job, manuscript edit, C01/M2 change, or historical overwrite.

Healthy startup, complete computation, code correctness, and scientific
calibration remain separate claims. Even a fully completed recovery requires
independent review of its output validation and assumption-specific results.
