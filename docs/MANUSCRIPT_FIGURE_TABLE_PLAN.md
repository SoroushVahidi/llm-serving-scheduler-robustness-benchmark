# MANUSCRIPT_FIGURE_TABLE_PLAN.md

Figure/table plan for the LSSP manuscript, produced during Query 3. No pending
figure is fabricated; each row states its exact data dependency.

## Figures

| ID | Section | Scientific question | Exact data | Statistic | Available now? | Pending dependency | Est. space |
|---|---|---|---|---|---|---|---|
| Fig 1 | 3.2 | What is the study design? | Schematic: sources × windows × policies × regions × metrics | n/a (diagram) | Yes | none | 1/3 page |
| Fig 2 | 4.5 | How do sources differ descriptively? | `window_descriptors.parquet` summary stats per source | distributional plots (e.g., prompt-token-length ECDF per source) | Yes | none | 1/2 page |
| Fig 3 | 4.7 | What drives source separability? | `attribution_summary.csv` (Tier-1/Tier-2) | permutation importance + single-feature balanced accuracy | Yes | none | 1/2 page |
| Fig 4 | 6.1 | How discriminable are policies per source/region? | Pilot-V2 non-tied-condition fractions | fraction non-tied, Wilson 95% CI | No | Pilot-V2 execution | 1/2 page |
| Fig 5 | 6.2 | How correlated are cross-source rankings? | Pilot-V2 per-source policy rankings | Kendall tau-b, Spearman rho, block-bootstrap CI | No | Pilot-V2 + ranking analysis | 1/2 page |
| Fig 6 | 6.3 | Where do practically meaningful reversals occur? | Pilot-V2 pairwise policy comparisons | reversal frequency map (policy × policy) | No | Pilot-V2 + ranking analysis | 1/2 page |
| Fig 7 | 6.5 | How does portability vary by load region? | Pilot-V2 × 6 regions | tau/reversal-frequency per region | No | Pilot-V2 + ranking analysis | 1/3 page |
| Fig 8 | 6.6 | How does portability vary by metric? | Pilot-V2 × metric contract | tau between metric-pair rankings | No | Pilot-V2 + ranking analysis | 1/3 page |
| Fig 9 | 7 | How many windows are needed for a stable ranking? | subsampling at n∈{5,10,20,30,40} | recovery probability vs. n, 0.9 threshold line | No | Pilot-V2 + sample-complexity analysis | 1/3 page |
| Fig 10 | 8 | Does simulated ranking agree with real vLLM? | frozen case-selection (largest-effect reversal + 1 stable control) | sign/tau/reversal agreement | No | Pilot-V2 §6.2/6.3 + real-system runs | 1/3 page |

## Tables

| ID | Section | Content | Available now? | Pending dependency |
|---|---|---|---|---|
| T1 | 4.1 | Workload-source table (name, provider/infrastructure, period, windows, role) | Yes | none |
| T2 | 5.1/5.2 | Scheduler/fidelity table (13 policies × mechanism family × fidelity class × panel status) | Yes | none |
| T3 | 5.5 | Metric-definition table (always-defined vs. completion-conditioned, undefined representation, ranking treatment) | Yes | none |
| T4 | 2.3 | Prior benchmark/simulator comparison (Vidur, LLMServingSim/2.0 vs. LSSP's benchmark object) | Yes | none |
| T5 | 6.2 | Headline ranking-result table (per-source policy rankings, tau/rho matrix) | No | Pilot-V2 + ranking analysis |
| T6 | 6.3 | Reversal table (policy pairs exceeding practical margin, CI) | No | Pilot-V2 + ranking analysis |
| T7 | 5.8/6.7 | Robustness table (high-fidelity subset, LOSO, window-size, metric-definition, load-grid, temporal-split, mechanism-family-exclusion sensitivity) | No | Pilot-V2 + robustness analysis |

## Rule

No figure or table above is populated with numbers until its stated
dependency is satisfied. `paper/sections/*.tex` reference these IDs as
`% FIGURE: FigN — see docs/MANUSCRIPT_FIGURE_TABLE_PLAN.md` placeholders where
not yet available.
