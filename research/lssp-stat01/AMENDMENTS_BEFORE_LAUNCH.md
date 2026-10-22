# Pre-launch engineering amendments

Initial protocol commit:edbcfdf. No campaign was launched or calibration-error summaries inspected before these changes.

1. Initial synthetic unit run:37 passed,1 failed. Merged sum/squared-sum variance suffered cancellation for nearly constant FDP (MCSE4.3e-9 versus approximately zero). Replaced it with stable per-batch central second moments and the Chan/Welford merge. Mathematical estimands, bound and stopping thresholds unchanged. Original log/exit/PID retained.
2. Added a dedicated seed namespace to prevent engineering fixtures from overlapping campaign seeds. Final SeedSequence is `[2026102201, namespace, scenario_index, replicate_index, stream_id]`, namespace1 for campaign and0 for engineering. Initial tests used the earlier four-integer seed path; no final campaign stream uses that path. This changes only the prospective seed encoding, before campaign outcomes, and is recorded in the final protocol/code/launch hash. There is no seed search or outcome-based selection.
3. Sufficient-statistic merging is numerical implementation only. Raw per-study arrays, masks, rejection vectors and bounded endpoints remain independently reconstructable. Partial wall-time results receive no new MC confidence bounds between prespecified looks.
