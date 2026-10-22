# M3 claim-to-evidence verification

## Scope and authority

M3 uses the completed campaigns reviewed in PR #17 (`6b2eedd7aa254986b85c1bb901587641cbeac8b0`), guided by PR #16 (`d22c7751af9c563d5a4d8a304c007f26112c4d12`). No new scientific data were generated. Numerical presentation was regenerated locally from immutable saved reports, with 27 source-byte fingerprints checked before rendering. The independent manuscript check is `scripts/validate.py`; machine-readable results are in `evidence/manuscript-validation.json`.

Evidence levels must remain distinct:

1. **Completed allocation checks:** exhaustive event/referee/batch validation before campaign completion. Inspected in the final-results review, not rerun as an experiment here.
2. **Final-results independent review:** full identity/inventory/summary checks, 24 fresh event-journal replays and 200 fresh saved-study checks, including scenario 11/replicate 6628. Its five copied result records are retained under `evidence/`.
3. **M3 presentation checks:** saved-report hashes; Cartesian coverage, reuse and completion; independent aggregate/headline arithmetic; all 5,760 CSV metric rows; exact reproduction of all 7,200 statistical summary rows; citation/reference checks; layout and preservation. This does not masquerade as another exhaustive raw-data replay.

## Principal claims and their boundaries

Locations name M3 source files. Data names below are under `evidence/data/`; table/plot scripts never import the simulation or synthetic generator.

| Claim / location | Evidence and check | Permissible interpretation |
|---|---|---|
| 5,760 cells, 144 reused, 5,616 new; abstract, design | `c01-absolute_metrics.json.gz`, final completion marker, original identity inventory; complete unique Cartesian set checked | Complete frozen design, not 5,760 independent samples |
| 120 windows, three sources, six settings, four IDs, two capacities; design | Input manifest, 720 conditions and output identities | Whole-window principal unit; repeated conditions and related windows are not independent |
| All 200 requests complete in every cell; performance | Every absolute row has `num_completed=200`, fraction 1, unfinished 0 | No administrative-horizon censoring in this corpus; no universal completion guarantee |
| Latency 0.008314–3.893923 s, p95 0.008560–7.300052 s; performance | Extrema of all saved metric rows; reviewed terminal-level accounting | Simulated time; conditional definitions, although all finish here |
| TPOT support 103–200; design/performance | Saved `n_tpot` per cell; definition excludes output lengths ≤1 | Not all request-level TPOT values exist; no missing cell endpoint |
| Latency reduction 11.3–34.0%, throughput reduction 1.65–4.01%; abstract, performance | Six source/capacity groups; stable-sum renderer and independent sequential-sum check; Figure 1/Table 4 | Relative differences of equal-window aggregates; not averages of per-request percentages |
| BurstGPT mean-window-p95 worsens 3.72%/18.97%; performance | Both capacities independently recomputed | Mean of window p95s, not pooled p95; unfavorable result retained |
| Bailian small-capacity ANWG falls 3.12% despite 24.05% lower latency | Source/capacity aggregates checked independently | Utility and latency answer different questions |
| Exact chunked/decode equality, 1,440 matches; model/rankings | All metric records checked; prior review checked all terminal records; work bound ≤4096 <32768 | Structural equality within contract, not native Sarathi/vLLM equivalence |
| Urgency gate does not bind; model | Pinned `policies.py`, available work budget and refreshed output anchors; prior review proof | Admission ordering is relevant; no active SLAI/urgency claim |
| Four/eight residents; used-KV peaks 47872/62880; model/performance | Context32768, capacity131072/262144, all saved resource peaks | Reservation-induced concurrency; not native allocator or used-cache exhaustion |
| Arrivals and deadline slack both scale; design | `_rebase_and_scale` lines59–95; prior independent check of all600 nonbaseline setting comparisons | Joint stress; no isolated arrival-load effect on ANWG |
| Exact source factors and LOW→HIGH Azure example | Saved load factors and per-setting equal-window means; PR17 §3.3 | Inherited FIFO labels; not common absolute load or CM saturation classes |
| Unique wins 1146/834/482/1004, source split480/468/198 | All frozen ranking records recomputed/count-checked | Exact top-set uniqueness, not ≥10% practical wins |
| No source-mean reversal, 0/2376; rankings | Full saved reversal table plus prior independent rational-boundary verifier | Null result under strict frozen definition; exact ranks need not coincide |
| Window34394/1847700, source109913/3788640, setting920/236853, KV350/47418, metric11795/473580 | All reversal groups summed, total=eligible+unestimable checked; full counts in Table3/CSV | Dependent comparison enumerations; no binomial CI or causal effect-size ranking |
| Top-set agreement307/396 and intersection323/396; complete ranks247/396 | Saved source-mean rankings; independent review's comparison | Aggregate rank changes below practical threshold may remain |
| Ties and mean-TPOT sensitivity1129/1440 | All11 metric groups in frozen rankings; complete table generated | Primary exact records retained; frozen sensitivity does not redefine decisions |
| Chronological negative counts8/48,24/48,0/48 | All frozen block memberships and matched means; generated Figure4/CSV | Unequal-duration corpus partitions; not independent time-series inference |
| Historical36/990; inference | Preserved M2 statistical audit and primary reversal reproduction | Archived-rule count only; no confirmed population discoveries/persistence |
| STAT134000=112275+21725,18 scenarios,5360 batches | Final completion/inventory review; all final looks; 4491 reused/869 new batches | Complete computation with precision gaps |
| Six precision stops; twelve maximum-count stops | Final looks: P for0,1,2,3,16,17; scenarios3/17 at2000/4000; rest8000 | Secondary additions do not drive stopping; no calibration-success stopping |
| 45 concern,74 inconclusive,9 compatible,16 abstaining original outcomes | Counted all18×8 screens; full Appendix Table7 | Compatibility permits conservative coverage; screens are not universal guarantees |
| Legacy IID FDR0.09025 [0.06878,0.11172], block0.918, AR0.980375 | Exact method ID and expanded-family bounds checked; Figure3 | Known synthetic nulls; explicitly post-diagnosis comparator |
| Historical/full-family/cluster/group coverage concerns; inference/appendix | Complete original and expanded endpoint summaries with denominators | Multiplicity cannot fix invalid components or selection/missingness targets |
| Bounded power0 and0.052632 despite observed zero FDR and coverage1 | Both bounded scenarios retained; Hoeffding assumptions separately stated | Conservative compatibility, not a broadly powerful replacement |
| 31 reused port/source differences; boundary at11/6628,index47 | Recovery amendment, frozen-source independent regression and saved-study referee review | Original port preserved; exact math and legacy fidelity distinct |
| Expanded 17-method allocation versus original8 | All final look family fields and endpoint bounds checked; amendment | Fixed amended family conditional accounting; not retrospective prespecification |
| Analytic exact p means represented dyadic value | Recovery numerical contract and original failure tests | Does not recover infinite-precision analytic tails or repair statistical validity |

## Research-question / contribution / display alignment

| RQ | Specific answer | Contribution / displays |
|---|---|---|
| RQ1 | Mean/throughput/tail/goodput trade-offs; reservation-induced concurrency; joint arrival/deadline stress; universal observed completion | Complete common-model evaluation; Tables1–2, Figure1, Figure2, Appendix Table4 |
| RQ2 | Stable source-mean strict practical comparisons alongside window/metric heterogeneity, equivalence, ties and numerical rank sensitivity | Descriptive ranking interpretation; Table3, Appendix Table5 and Figure4 |
| RQ3 | Historical reproduction does not establish common semantics or calibrated inference; synthetic failures are scenario-specific | Scoped inference diagnostic; Figure3, Appendix Tables6–7 and full endpoint CSV |

The four contributions are contract, completed performance evaluation, descriptive ranking interpretation and inferential boundaries. The RQs are M3's presentation; frozen historical protocols are not retrospectively rewritten.

## Exact source locations and anchors

Original completed C01-FULL root:
`/project/ikoutis/sv96/github/llm-serving-scheduler-lssp-c01-full-20261022/`

- `runs/c01-full-167b9074e5711420/complete.json`: SHA-256 `11c9c08432878932c0fca0501b2befd83f333dedf2686d3a5693d27a7a3fea72`.
- `runs/c01-full-167b9074e5711420/analysis/absolute_metrics.json`: `5700c4bbd7386b7227d678b6b09a715010c29ccdbdb8654e7dd93bde1c585666`.
- `runs/c01-full-167b9074e5711420/analysis/independent_analysis_validation.json`: `c48c0b8472c49309a0f7f3227ed2ea40c50345bfc93baa44d4f7347ae160df70`.
- Full raw evidence: `cells/*/{result.json,events.jsonl.gz}` and `reused/*/` under that run; `launch.json`, `reuse_index.json`, `inputs/full-inputs.json`, `research/lssp-c01-full/PROTOCOL.md` and `research/lssp-c01/PROTOCOL.md` under deployment.
- Engine/adaptation proof: `research/lssp-c01/policies.py`; scaling: `src/robustbench/calibration/stage0_load_calibration.py`.

Original completed STAT01 recovery root:
`/project/ikoutis/sv96/github/llm-serving-scheduler-lssp-stat01-recovery-v2-20261022/`

- `runs/stat01-recovery-v2-061933a64e27da20/completion.json`: `a658e16039d5a9be8b496792e038637df1cdf7507ff16b7de3411a79ac15e01e`.
- Final checkpoint: `a261866365b74bd6b240fb1916a0ce3c4bbc8ee76d08097b9dcb2048dc693c13`.
- `look-sXX-nNNNNN.json` final scenario summaries in that run; raw and decision files at `batches/scenario-XX/rep-NNNNNN/{raw.npz,studies.json.gz,secondary.json.gz,integrity.json}`.
- Failure-case batch: `batches/scenario-11/rep-006625/`, fourth saved study (rep6628).
- `code/AMENDMENT.md`, `code/rv2_methods.py`, `code/rv2_reference.py`, `code/rv2_summary.py`; `logs/tests-pinned.txt` records118 passed tests.

Unchanged failed STAT01 source:
`/project/ikoutis/sv96/github/llm-serving-scheduler-lssp-stat01-454168a00524/`

Prior review copies and checking scripts:
`/home/soroush/lssp-m3-final-review-evidence-20261022/`

Consumed raw source hashes (not a declaration of redistribution permission):

| File | SHA-256 |
|---|---|
| AzureLLMInferenceTrace_conv_2024.csv | `a0cc9b969a9bbf0fd811802cbf4323edd3a209ace791e3799ad4f9207f213941` |
| qwen_traceB_blksz_16.jsonl | `68e3f98e2d601d60d0abf4b89bc8a3654372abab7b1cde6373a13d0054379d59` |
| BurstGPT_without_fails_2.csv | `56193aa9b2bb26128ded43d2d29a960df6bf5af062bcfc9b005f3fcaa4e6e501` |

## Preservation and limits

The validator checks inherited tracked content against PR17 and verifies the pre-existing hydrated historical consolidated file against SHA-256 `73adf7d97f06985ec8f8e1c2f794fd43178433eb198e1c00705e817f4bde9c26`. Its inherited Git-LFS anomaly is excluded from this PR, not repaired. No M2 section, bibliography, figure, historical result or frozen protocol changes. Numerical formatting in M3 never feeds back into a scientific decision.

Source release permissions, external artifact accessibility, related-manuscript status and journal compliance remain unresolved as listed in `SUBMISSION_BLOCKERS.md`. The manuscript is not a certificate of acceptance, native accuracy or universal calibration.
