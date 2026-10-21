# Preregistration — DRAFT

**NOT REGISTERED. NOT AUTHOR-APPROVED. NO EXECUTION AUTHORIZATION.**

Protocol: LSSP-PROTOCOL01, prepared 2026-10-21. Repository research baseline: `4332b08b17e5b789e20a4fe042a6b007f0d43dd6`. This draft defines a future physical study. The author's archived simulation preregistration, historical 240 physical runs, MGPU00–02 development and MGPU03 smoke preceded it. They must never be described as preregistered under this document.

## Scope and primary estimand

Study policy-pair SLO-goodput advantages and their deployment interactions across six fixed A100/L40 single/TP2/DP2 deployments, at matched reference-relative pressure, with common offered-rate sensitivity. The primary outcome is request SLO goodput and its arrival-normalized paired contrast. Hypotheses H1–H4, practical-margin criteria, analysis families and failure rules are in [HYPOTHESES.md](HYPOTHESES.md) and [METRICS_AND_STATISTICS.md](METRICS_AND_STATISTICS.md). Mechanism interventions and the held-out transfer rule are prospective substudies with additional freeze requirements.

## Information already known

The current manuscript and public artifacts contain simulation ranking results and selected historical physical outcomes. Their methodological overlap is disclosed in [NOVELTY_AND_OVERLAP.md](NOVELTY_AND_OVERLAP.md). MGPU00 found MIG/replay/metadata problems; MGPU01 failed startup; MGPU02 reported 151 local tests under a bounded whole-prefill contract. Existing window-length descriptors were read to assess coverage. MGPU03 Slurm accounting was checked once and showed completion; serving/performance artifacts were not inspected in this design turn. These facts motivate validation and coverage requirements, not favorable window/policy selection.

The future pilot will expose feasibility and nuisance variances; all pilot windows remain development-only. Any policy-performance knowledge from it must be disclosed at the final freeze. No promise of outcome-blindness is made for already published historical windows.

## Freeze checklist — all required before confirmatory collection

- Author approves the research scope, publication overlap and claim boundaries; records approver/date.
- Pin exact source code, four independent mechanism specifications, oracle corpus and physical acceptance evidence.
- Freeze the six effective deployments, topology/host controls, model/tokenizer/assets, software and runtime flags.
- Audit raw trace units/licenses/hashes and eligibility coverage; freeze window coordinates, generated token work, SLO/tenant overlays, output limits and request hashes.
- Fix arrival intervals/prelude/drain rules, two pressure regions, calibration reference/capacity estimator and common-rate anchor.
- Approve numerical SLOs, primary all-gap contract or a prospectively amended observable alternative, δ/h and failure/censoring conventions.
- Freeze W/R from the pilot planning report, temporal/node/day blocks, permutation/seed and all 468 primary contrast identities (or an explicitly regenerated family).
- Validate statistical code on independent synthetic known-answer cases; lock multiplicity/resampling/degeneracy rules.
- Freeze C3 intervention choices, magnitudes, mediators and profile subset, and C4 development/hold-out coordinates, features, rule family and decision-risk criteria.
- Approve allocated-GPU-hour cap, wall/startup/drain bounds, stopping conditions and replacement policy.
- Fill all `freeze_required` fields in the manifest, set approval metadata, create an immutable signed/tagged commit or archive with SHA-256, and record external registration timestamp before main outcomes.

The draft validator checks consistency; it cannot grant approval or register the study. The manifest deliberately sets `execution_authorized: false` and leaves unresolved identities null.

## Analysis and stopping commitments

Publish every planned execution ID and disposition. Exclude only by predefined input/fidelity/infrastructure rules; policy failures and overload are outcomes. Stop affected work on semantic/hash/identity violations or resource-cap exhaustion. Do not continue until an approved correction and amendment exist. No winner-dependent selection, automatic reruns or significance-driven stopping. Stable, tied and inconclusive rankings are reportable outcomes. Report deviations and exploratory analyses beside, not in place of, the original plan.

## Amendment log

| Version | Date | Reason | Outcome access | Status |
|---|---|---|---|---|
| 0.1 | 2026-10-21 | Initial prospective physical-study design after MGPU02 | Historical literature/artifacts known; MGPU03 accounting only | DRAFT |

For each later change record old/new text and manifest hashes, author approval, which outcomes had been viewed, rationale independent of winners, affected estimands and whether new untouched data are required. An approved amendment after observing a result is prospective only for subsequent tests; it does not convert that result into preregistered evidence.
