# STAT01 validation and readiness gates

No namespace-1 campaign outcomes were generated or inspected before freezing the design. Namespace 0 is reserved for engineering fixtures. The initial protocol/reuse audit was committed as `edbcfdfce5649a0c53502f9cc67da6b91e02c3d8`, directly on M2 `880a37e8e7c19d089be124291e288269966a9147`. Pre-launch implementation corrections are recorded in AMENDMENTS_BEFORE_LAUNCH.md.

## Local validation

Final run: **63 tests passed**, exit 0, 2026-10-22T04:22:08Z–04:22:10Z. TMUX session/window `lssp-stat01-final-validation:cpu`; shell PID 545932. Command: `bash research/lssp-stat01/checks.sh`, with `/home/soroush/modal-venv/bin` first on PATH. Python 3.12.3, NumPy 2.3.5, SciPy 1.17.1, pytest 9.0.3. See evidence/validation.txt, validation.pid and validation.exit.

Checks cover:

* Independently enumerated Decimal versus rational population truth for every scenario, all 165 hypotheses, exact practical boundaries, and sign-only alternatives.
* Analytically known generator means, variances, policy covariance, block/AR covariance, bounded support and missingness rules.
* Historical implementation equivalence on complete and missing synthetic fixtures with 2,000 draws; identical ordering and RNG stream within each comparison.
* BH/BY against SciPy and independent Holm verification; Gaussian, Student, cluster, observed-submatrix covariance, Hoeffding and directional-union formulas.
* Information isolation: changing latent unobserved outcomes cannot change observed-data tests. Missing results, all-missing fixtures, tied candidate sets, finite bootstrap resolution and grouped resampling are explicit.
* Deterministic replay, disjoint engineering/campaign seed namespaces, all-scenario end-to-end integrity, and independently rejected mutations of truth, identities, p-values, decisions and endpoints.
* Empirical-Bernstein formula and stable summary merging; immutable batch hashes/read-back; resume, precision/cap/time stopping, and rejection of corrupt or incompatible inputs.

`reference.py` imports no simulator/generator/method implementation. It independently validates truth, multiplicity, accounting, intervals, domain labels and stored integrity. It does not independently recompute every statistical p-value at runtime; focused formula and historical-equivalence tests provide that additional check. This distinction limits the claim of independence appropriately.

Compilation and Slurm shell syntax passed. Three namespace-0 B=2,000 fixtures took approximately 0.033 s, 0.018 s and 0.159 s locally. These are engineering timing checks, not scientific outcomes or promised cluster throughput.

The first test run found cancellation in sums-of-squares variance; the implementation was corrected to centered second moments with Chan/Welford merging. The failing log remains in evidence/validation-attempt1.*. Subsequent passing runs are preserved as validation-stable-merge.*, validation-61tests.* and validation.*. No generator or method was tuned to campaign results.

## Wulver gate

Production is pinned to Python 3.12.13, NumPy 2.5.2, SciPy 1.18.1 in the existing `.venv312` environment. The production runner rejects environment, protocol, implementation or historical-reference hash mismatches. A second engineering-only validation on this exact environment must pass before submission; its log, PID, session/window and exit code will be preserved here.

Scientific launch readiness means the synthetic study is specified and its implementation passes these checks. It does not mean historical inference is calibrated, that an unknown real workload satisfies these sampling assumptions, or that the manuscript is publication-ready. Selective missingness, unknown dependence, provider sampling, native implementation comparability and finite bootstrap resolution remain substantive limitations.

Wulver gate **passed**: 63 tests, exit 0, 2026-10-22T04:26:45Z–04:27:18Z; TMUX `lssp-stat01-validation:cpu`, pane PID 3116912, shell PID 3116913. Logs/PID/exit are evidence/wulver-validation.*; exact command is in validate-remote.sh. Pinned environment and every staged protocol/code/reference hash matched. Namespace-0 timing fixtures passed (0.186/0.103/0.796 s); no namespace-1 outcomes were inspected. Slurm syntax passed.

Readiness decision: **GO for one synthetic calibration job**, not for a claim of calibrated historical error rates. The reuse gap, explicit truth, independent checks, frozen identity and resumable output gates pass. No changes outside research/lssp-stat01 are committed. The inherited LFS anomaly has the same bytes as M2 (SHA-256 `73adf7d97f06985ec8f8e1c2f794fd43178433eb198e1c00705e817f4bde9c26`) and remains unstaged.
