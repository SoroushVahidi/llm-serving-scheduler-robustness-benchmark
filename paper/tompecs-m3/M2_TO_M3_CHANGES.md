# M2 to M3: principal changes

M3 is a separate source tree stacked on reviewed evidence. M2 and every historical experiment remain unchanged.

1. **Changed the central object.** Replaced a historical ranking-portability/methodology narrative with an explicit common-model performance evaluation. The working title is *Scheduler Rankings and Performance Trade-offs in a Common-Model LLM-Serving Evaluation*. No new algorithm, rank statistic, test or hardware predictor is claimed.
2. **Rebuilt the organization around three answered RQs.** Contract and corpus precede absolute performance; rankings follow magnitudes; historical inference is a short diagnostic afterward. Four contributions correspond to contract, complete performance evaluation, descriptive ranking interpretation and inference boundaries.
3. **Integrated the complete C01-FULL evidence.** All 5,760 cells, 144 reused pilot cells, 120 windows and both capacities are accounted for. Four vector figures and seven main/appendix tables accompany complete numerical CSV supplements.
4. **Made unfavorable and null findings central.** Mean-latency gains appear alongside throughput loss, BurstGPT p95 degradation and Bailian goodput loss. Zero source-mean practical reversals, exact chunked/decode equivalence, inactive urgency gate and redundant rankings constrain the contribution.
5. **Corrected operating-condition interpretation.** The inherited transformation scales both arrival gaps and synthetic deadline slack. Capacities permit four/eight full-context reservations; they do not demonstrate native used-cache exhaustion. Equivalence is explained from the 4,096-versus-32,768 work bound, not marketed as a native-system result.
6. **Kept calibration separate.** Main text uses three null scenarios as a concise diagnostic; the appendix reports all 18 original-family screens, stop reasons and procedure contracts. The full supplement preserves all 17 methods and all 16 endpoints in both uncertainty families. Numerical correctness, historical fidelity and statistical validity remain distinct.
7. **Reduced historical material.** The 36/990 count remains only as an archived-rule motivation. The old 13-policy leaderboard, interval replication, Friedman tables, descriptor fits, physical-runner history and finite-reference recovery remain in the preserved M2/artifact rather than being copied into the core paper. No historical-reversal persistence or population sample-complexity claim survives.
8. **Reworked related work and citations.** Explicitly credits workload-choice evaluation, predictive simulators and verification/validation foundations. Retains 16 relevant M2 references and adds five foundational references (Sargent, BH, Holm, Hoeffding, Maurer–Pontil), for 21 cited entries. Unused, unresolved-version catalogue items are omitted; retained final publications receive corrected links/pages/metadata. See `CITATION_VERIFICATION.md`.
9. **Corrected a provenance instruction in the prewrite audit.** The audit suggested documenting a Bailian block-to-token conversion. The pinned upstream README and actual adapter instead show direct `input_length`/`output_length` token counts; 16-token blocks describe `hash_ids`. M3 states the verified behavior. No frozen data or adapter was altered.
10. **Added conspicuous author-review obligations.** Artifact access, release-specific permissions, related-paper status/overlap, authorship/funding/conflicts/AI disclosure and current ToMPECS instructions are not silently declared resolved.

## Section disposition

| M2 material | M3 disposition |
|---|---|
| Introduction / related work | Rewritten around the comparison contract and empirical findings; direct prior-work contrasts |
| Four manuscript questions and six original protocol questions | Three current manuscript RQs; historical protocols remain immutable, not retrospectively rewritten |
| Historical model / workloads | New CM-0.1 specification and frozen-corpus provenance; historical differences condensed into Section 7 |
| Within-region / portability / metrics | New absolute-performance Section 5 and ranking Section 6, with full data supplements |
| Robustness / historical statistical audit | Short inference diagnostic plus Appendix B; full historical analyses remain in M2 |
| Limitations | Claim-specific qualifications plus focused discussion, without repeating an audit diary |
| Conclusion | Direct three-RQ synthesis |
| Artifact / declarations | Specific unresolved author items, without invented confirmations |

## What the rewrite does not establish

The evidence remains a synthetic fixed-cost CPU model, not native GPU performance. The nominal four adaptation IDs do not represent four distinct observed mechanisms. Synthetic calibration does not determine the truth of every historical trace finding. The paper is ready for substantive author review, not yet for submission. No additional scientific experiment is proposed or required for its stated scope.
