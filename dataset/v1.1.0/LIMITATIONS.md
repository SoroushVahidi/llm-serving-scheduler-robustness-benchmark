# Scientific and reuse limitations

1. The 18,720 rows represent 9,360 configurations with two equal deterministic verification passes. Neither count is an independent statistical sample size. Windows, including those drawn from related Microsoft/Azure provenance, are the relevant inferential units.
2. Results describe one frozen simulator and workload-window sample. Policy implementations and style approximations do not establish the behavior of every production scheduler or deployment.
3. The selected physical RQ6 check did not reproduce the simulator's largest predicted Azure/BurstGPT reversal. Its stable-order control retained qualitative ordering. The physical data belong to a separate 240-execution study already publicly summarized.
4. The historical discriminability pilot failed its preregistered BurstGPT criterion. The RQ3 synthetic-to-real transfer pilot is inconclusive. These are genuine negative and limiting outcomes.
5. Supported primary-metric reversal evidence is concentrated: 36 supported comparisons among 990 pairwise comparisons, all involving one policy pair and BurstGPT on one side. Do not generalize this rate to unseen traces.
6. Four hundred twenty-two successful matrix rows have undefined conditional metrics. Original JSON uses NaN and Parquet preserves IEEE NaN. Undefined is not zero or failure; missing-value handling changes downstream rankings.
7. Seed reuse and possible shared upstream provider history limit independence. Trace windows, not deterministic passes or individual policy cells, should be blocked in uncertainty estimates.
8. The public package has derived window descriptors and result records, not original request-level traces. A researcher cannot fully reconstruct input requests from this package alone; use upstream sources and the pinned source hashes.
9. The six canonical analysis outputs were not regenerated in preparation. Source hashes, campaign binding and row-equivalent Parquet views were verified. Reanalysis under altered metrics is a new researcher choice, not a correction of these frozen outputs.
10. The bounded prior external search found no demonstrably equivalent third-party result dataset; it cannot establish global originality. The 468 matching public smoke outcomes and previously published analytic projections are disclosed in [PUBLICATION_OVERLAP.md](PUBLICATION_OVERLAP.md).
