# Figure, table and text inventory

`evidence/float-text-inventory.json` lists every float's source file, label, caption and source size, plus the 15 largest paragraphs and all section word counts. Visible PDF heading coordinates/page counts are separate in `evidence/page-counts.json`.

| Historical visual | M1 treatment | Evidence |
|---|---|---|
| Source-pair/region tau heatmap (`fig1_portability_heatmap.pdf`) | Preserved unchanged; retained with Description | Six-source-analysis hash ledger; all 18 plotted point values independently recomputed from matrix |
| Reversal-class matrix (`fig2_reversal_class_matrix.pdf`) | Preserved unchanged in baseline/assets; revised text uses an exact count table | All 990 saved primary records independently classified; table rows 165 each, 990 total |
| Recovery curves (`fig3_sample_complexity_curves.pdf`) | Preserved unchanged; retained with Description | Saved sample-complexity JSON; original generated table reproduced |
| Per-region mean/min/max tau table | Preserved in baseline; redundant with heatmap/full 18-row revised table | Saved ranking correlations |
| Recovery-threshold table | Preserved in baseline; removed from revision because curves/prose retain values | Saved recovery ladder |
| Legacy physical-effect table | Preserved in baseline/history; no longer a faithful-policy validation result in revision | MGPU00 contradicts interpretation; original observations unchanged |
| Simulation assumptions table | Retained with hardware-boundary language corrected | Historical execution model plus fidelity audit |
| New denominator, policy-role and source-length tables | Added for independent interpretation | Frozen keys/registry/window descriptors; explicit scope, no new workload |
| New 18-row correlation/interval table | Added for complete comparison coverage | Points independently recomputed; intervals read from saved output, not regenerated |

The largest baseline passages are the practical-reversal taxonomy, simulation execution model, policy catalogue and repeated interpretation/physical-validation discussions. The original Section 5 methodology and related-work catalogue were major length drivers. The revision consolidates repeated motivation but deliberately retains the taxonomy, edge cases, missingness, information-model and physical-fidelity limitations.

Large revised floats are the 18-row correlation table, policy-role table and model-assumptions table; the recovery plot is the widest retained figure. They use normal ACM page geometry. Floats may appear before a section heading on a shared page; the length inventory does not falsely assign whole pages exclusively to sections. No plot is relabeled as a new measurement. Full plotted-point extraction of every PDF is not claimed; table-data reproduction, source hashes and visual inspection are separate checks.
