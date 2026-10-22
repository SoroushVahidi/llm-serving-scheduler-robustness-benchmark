# LSSP-STAT01 — independent statistical calibration

New synthetic investigation from M2 draft#10, `880a37e8e7c19d089be124291e288269966a9147`. Independent of C01; no C01 job inspection, cancellation or modification. Historical data/manuscripts and PRs are unchanged. The inherited LFS anomaly is preserved.

Review [reuse audit](REUSE_AUDIT.md), [prospective protocol](PROTOCOL.md), [pre-launch amendments](AMENDMENTS_BEFORE_LAUNCH.md), [validation](VALIDATION.md), and [conditional future-analysis recommendation](PROSPECTIVE_RECOMMENDATION.md). No M2 interval reproduction or saved-data sensitivity is rerun.

The new campaign uses18 synthetic scenarios with explicit population means: nulls, practical-boundary cases, controlled reversals, exact/near ties, correlated policies, independent/block/AR windows, unequal variances/distributions, and complete/MCAR/selective observations. Every study has3 sources,11 policies and165 prespecified comparisons. Eight methods include the historical screened-bootstrap/BH procedure, complete-family diagnostics, practical-effect Student/cluster/known-covariance tests, centered group resampling, and bounded Hoeffding tests. Assumption-valid procedures, oracle benchmarks, diagnostic methods and domain abstentions remain distinct.

Primary truth is a population reversal with >10% advantage on both sides; sign-only truth is separately reported. Outputs include raw generated outcomes/masks, all rejection vectors, FDR/FWER/null rejection fractions/power, ordinary and selection-conditional CI coverage, set-valued best-policy coverage and Monte Carlo uncertainty. **CI calibration here concerns a predeclared mean-difference interval, not tau-b/rank-correlation intervals or Friedman omnibus calibration.** Synthetic scores are not measured serving performance.

Study seeds use `[2026102201, namespace, scenario, replicate, stream]`; namespace1 is campaign,0 engineering. Per-scenario looks500/1000/2000/4000/8000 use simultaneous empirical-Bernstein Monte Carlo bounds. Early stopping is precision-based, never outcome-favorability-based. Ordinary MCSE is also reported but does not justify the stopping rule. A time-limited partial run reports only bounds from completed prespecified looks.

One Slurm job requests4 CPUs,8GiB, zero GPUs, general/standard,09:00:00 maximum. Workers stop taking new batches after8h45m. Raw batches are immutable, hashed and independently validated before checkpointing; corrupt results stop resume. Maximum-count, precision-stop and time-budget termination are distinct. No automatic rerun or follow-up campaign.

See REPRODUCIBILITY.md and LAUNCH_REPORT.md once launch provenance is recorded. Startup health is not scientific completion. All empirical calibration conclusions require complete output validation and assumption-specific author review; no finite scenario suite proves universal validity.
