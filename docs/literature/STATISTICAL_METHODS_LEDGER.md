# STATISTICAL_METHODS_LEDGER.md

This ledger maps the statistical methods that are already specified by the project and should be cited explicitly in the manuscript.

| method | verified reference / standard | manuscript mapping | safe claim |
|---|---|---|---|
| Kendall tau-b | standard nonparametric rank correlation method | ranking stability, pairwise ordering agreement | used to summarize pairwise agreement across workload sources and operating regions |
| Spearman rho | standard nonparametric rank correlation | secondary rank similarity robustness check | used as a corroborating metric, not the sole claim metric |
| paired comparison / paired inference | project-defined analysis plan | cross-source rank agreement and reversal counts | used only when conditions are paired within the same benchmark protocol |
| bootstrap confidence intervals | standard resampling method | uncertainty around reversal prevalence or agreement summaries | used for uncertainty quantification around estimated ranking properties |
| block bootstrap / window-level bootstrap | project-defined methodology | ranking uncertainty and sample complexity | must be tied to the exact project protocol and not re-labeled as a generic claim |
| probability of correct selection / benchmark sample complexity | project-defined analysis plan | sample-size and recovery analysis | distinct from absolute ranking outcome reporting and must not be mixed with a single best-scheduler claim |
| Demšar-style comparison | statistics literature on comparative algorithm ranking | ranking comparison across multiple algorithms | relevant when used for the exact benchmark object, not as a blanket generic assertion |

## Important rule

Statistical methods are not literature claims by themselves; they must be mapped to the exact planned manuscript sections and to the fixed benchmark protocol. The final manuscript should cite the relevant references and then specify the exact LSSP implementation detail used.
