# M2 research-question alignment

The manuscript now presents four **retrospective manuscript questions**, Q1–Q4, avoiding a numbering collision with original RQ1–RQ6. The frozen protocol is unchanged. An answered corpus-level description is not an answered population-transfer question.

| New manuscript question | Evidence and answer | Historical provenance |
|---|---|---|
| Q1: Cross-source and operating-region ranking portability | All 18 ANWG tau values positive, 0.551–1.000; source-pair differences dominate the reported mean-region pattern. New within-region outcome table supplies absolute utility context. | Original RQ1, parts of RQ2, frozen region sensitivity; new absolute-value tabulation is retrospective. |
| Q2: Practically meaningful pairwise reversals | 36/990 meet historical 10% point-margin and nominal interval rule; five pairs, all BurstGPT comparisons. Calibrated significance/FDR withdrawn. | Pairwise decomposition of original cross-source question. M2 multiplicity/dependence checks are post hoc. |
| Q3: Cross-metric and SLO-definition sensitivity | Historical median tau .419 and ID agreement 316/990. New set intersection 572/990, explicit missing-support checks; saved SLO extension has 13/30 ID changes and six/72 reversal-direction changes. | Broad metric/SLO sensitivity was contemplated in older plans, but concrete implementations/extensions followed primary outcomes. M2 set/matched analyses are new post-hoc work. |
| Q4: Temporal and finite-reference ranking stability | Mostly high temporal correlations with BurstGPT LOW exception −.10. Exact finite-reference recovery ≥.9 at n=30 for Azure and n=40 for other sources; n=40 is automatic. | Temporal part of RQ2 and restricted answer to original RQ5. No independent-window population requirement is inferred. |

## Mapping every original question

| Original frozen question | M2 status | Reason and destination |
|---|---|---|
| RQ1: How stable are scheduler rankings across independent workload sources? | **ANSWERED descriptively for the frozen corpus; independence/generalization unestablished** | Q1/Q2. Replace ambiguity of “independent” with separately released sources. |
| RQ2: Stability under temporal, provider and domain shifts? | **PARTIALLY ANSWERED** | Temporal partitions in Q4; source contrasts in Q1. Provider effects confounded; no standalone domain-shift experiment. |
| RQ3: Synthetic stress rankings transfer to independent real-trace-derived rankings? | **UNANSWERED at intended scientific scope** | Pilot is engineering context, not a central manuscript question or full validation. Limitations remain visible. |
| RQ4: Source-native characteristics associated with reversals? | **PARTIALLY ANSWERED, weak descriptive association only** | 42 usable fits/990 retained in robustness discussion; no causal explanation, reliable directional inference or validated predictor. No new regression fit was manufactured. |
| RQ5: Number of independent windows needed for statistical ranking stability? | **PARTIALLY ANSWERED** | Q4 answers recovery of the 40-window reference and deterministic tie ordering, not population sample complexity or independence. |
| RQ6: Do simulated rankings/reversals reproduce on a real serving engine? | **UNANSWERED for faithful native policies** | Legacy MIG runner observations do not meet required execution/metadata/admission fidelity. No physical transfer or failure-to-transfer conclusion follows. |

## Why fewer questions are scientifically justified

The change makes the paper's promises match its evidence. Unanswered protocol questions remain in a main-text mapping table and limitations; they are not deleted from history. RQ4's limited explanatory evidence remains a supporting limitation rather than being elevated into a causal manuscript question. Cross-metric sensitivity deserves a clear question because the frozen extension and M2 tie/support checks permit a bounded answer, but its retrospective prominence does not make it preregistered.

The old plans explicitly mention metric dependence and SLO sensitivity. M1's claim that SLO sensitivity was never contemplated by the protocol is too categorical. M2 distinguishes the earlier intention from the concrete post-campaign extension and its selection of regions containing saved reversals. Neither the intention nor a later immutable extension hash establishes that its detailed analysis was frozen before primary outcomes.

Every conclusion paragraph now answers Q1, Q2, Q3 or Q4 directly. The final paragraph preserves the unresolved original synthetic-to-real and native-transfer questions. Historical protocol files, M1 source/PDF and PRs #3–#9 are unchanged.
