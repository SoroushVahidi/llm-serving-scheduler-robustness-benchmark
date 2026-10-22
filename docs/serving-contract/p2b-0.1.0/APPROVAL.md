# Prospective delegated S02 amendment

Authority: the author's P2B request explicitly delegates the technical selection below. This is a new prospective record, not an edit of the original unresolved registers. It records **author authorization of a working direction**, separately from CPU engineering acceptance and missing physical evidence.

**Frozen partial profile ID: `lssp-slai-s02-prefill-control/0.1.0`.** Literal expectations are frozen in [literal-cases.json](literal-cases.json); their hash is recorded with tested sources. Any changed ordering/meaning requires a new profile/corpus version. No historical run is relabeled.

| Choice | Adopted rule | Evidence boundary / deviation |
|---|---|---|
| S02 class | tight → strict; medium/loose → non-strict | Author-delegated adaptation of the reference's binary strict flag; replaces neither historical three-tier ordering nor past metadata. |
| S02 new admission priority | Strict first, immutable **original prompt** length ascending, then globally unique stable ordinal | Does not order by future output. Policy `View` has no output-limit/remaining-output field. Source SLAI uses mutable prompt length and stable waiting order; original length and explicit ordinal are declared adaptations. |
| S02 paused priority | Persistent FIFO; remove selected entries on successful ACK, append unfinished chunks in accepted-plan order after unserved entries | Never re-sort by class, prompt or arrival. A new strict request does not bypass already paused prefill. Proposal alone never advances FIFO. |
| S02 equal keys | Unique nonnegative ordinal, fixed for lifetime | Makes ties explicit; no ambiguous source Sequence-object comparison. Numerical LST tie ordering is not activated. |
| Partial profile service envelope | Paused then new prefill; if any prefill selected, hold all decodes. Otherwise decode by ordinal, including when no new admission slot is available. | **Deliberate partial implementation**, not source SLAI. No critical/residual LST phases or invented numerical threshold. Holding residual decodes also keeps this subset representable by the native phase structure. Any full SLAI extension needs separate review. |
| S01/S03 | Named common-vLLM adaptation; native final-prefill sample eligibility | Retains P1 delegated choices. Intermediate chunks: zero valid samples; final catch-up: one. CPU evidence only. |
| S05 | Separate host-policy feedback vs GPU/user clocks | No LST arithmetic, thresholds, offsets, inferred durations or measured policy feedback added. Numerical policy remains gated. |
| S06 | Immutable limits/arrival and lifetime prefix; no implicit retries | P1 preserved. P2B only epoch 0, successful quiescent synthetic attestations. General cancellation recovery, recomputation and prefix replay remain disabled. |
| S04 | Retain P2A conservative whole-run no-pressure bound; actual native allocation | Does not implement general reservations/victims/preemption or approve pressure policy. A known immutable output **cap** participates only in the whole-run safety-domain bound, never priority or individual waiting selection; no future realized output-length oracle is used. |
| S07/S08 | No new main model/tokenizer/trace/stop or distributed choices | UNRESOLVED. Existing tiny CPU config and synthetic token IDs are not realistic trace coverage. |

CPU tests freeze medium-long vs loose-short, strict precedence, equal-key ordinal order, paused-before-new-strict, held decode, and the cross-phase rejection. The partial policy alone supplies no ranking conclusion, starvation guarantee, production SLA or full SLAI fidelity claim.

The minimum next author review is whether to develop the real execution-side attestation bridge within this controlled no-pressure domain. A later complete SLAI phase needs an approved criticality/LST specification and a reviewed way to handle waiting-before-resident work; this task supplies neither. Pressure/victim and distributed semantics are independent decisions, not consequences of S02 approval.
