# SERVEGEN_ADOPTION_AUDIT.md

Investigated via live web search and a direct repository fetch on 2026-08-31.

## Findings

- **Official artifact/repository:** `https://github.com/alibaba/ServeGen`,
  paper `arXiv:2505.09999` ("ServeGen: Workload Characterization and
  Generation of Large Language Model Serving in Production"), USENIX NSDI
  2026 (Xiang, Li, Qian, Zhang, Yu, Zhai, Jin, Zhou).
- **Licensing:** The repository carries an **Apache-2.0** license file
  (confirmed via direct repository fetch). The README does not separately
  address redistribution of *generated* workloads beyond the code license.
- **Redistribution of generated manifests/results:** Since ServeGen is a
  code generator (Apache-2.0), running it ourselves and redistributing the
  resulting benchmark manifests/results as our own derived artifacts is
  consistent with a standard Apache-2.0 code license. This differs from a
  fixed-trace source (BurstGPT/Azure/Bailian/TraceLab) where the *data*
  itself carries a separate license — here, what we would redistribute is
  our own generator output, not a third party's raw data.
- **Reproducible generation procedure:** Plausible given it's a released,
  documented framework, but not independently exercised in this audit (no
  installation/generation was run).
- **Workload categories:** three families per the repository — **Language
  Models** (`m-large`, `m-mid`, `m-small`), **Reasoning Models**
  (`deepseek-r1`), **Multimodal** (`mm-image`). Only the Language Model
  family is directly relevant to this project's text-serving scheduler
  scope; reasoning/multimodal are out of scope for the current RQs.
- **Characterization basis:** per the paper abstract, ServeGen is "powered by
  the analysis of billions of inference requests across 12 production models
  on **Alibaba Cloud Model Studio**." Alibaba Cloud Model Studio is the same
  underlying platform commonly referred to as "Bailian" — i.e., **ServeGen's
  characterization data traces back to the same provider as this project's
  Bailian/Qwen source**, not a distinct fourth/fifth provider.

## Independence assessment

ServeGen is **not** meaningfully independent of Bailian/Qwen at the
provider/domain level (`docs/EVIDENCE_INDEPENDENCE_PLAN.md`). What it *does*
offer, distinct from a raw Bailian trace replay, is a **controllable,
documented model of realistic production drift** — bursty arrivals beyond
simple Poisson models, and input/output length distributions shifting over
days/weeks — which is directly relevant background for RQ2 (temporal
stability) and could produce a more realistic synthetic-family member than
this project's existing hand-built `workloads/synthetic.py` generators for
RQ3 (synthetic-to-real transfer).

## Verdict: **OPTIONAL**

Reasons:
- Apache-2.0 licensing and a documented, citable generation procedure make
  adoption low-friction if pursued.
- It meaningfully strengthens the *synthetic-workload* side of RQ2/RQ3 with
  more realistic drift modeling than a hand-built Poisson/lognormal
  generator.
- **It must never be counted as a fifth independent provider source
  alongside BurstGPT/Azure×2/Bailian/TraceLab** for Go/No-Go Gate B's
  "≥4 independent workload families" criterion — it shares Bailian's
  underlying platform.
- No adoption blocker was identified (license is clear, scope is
  compatible), but it is not on the critical path for any of RQ1–RQ6 as
  currently scoped, so it is **not required** for this project's core
  contribution and should be adopted only if/when the synthetic-family side
  of RQ2/RQ3 needs strengthening — hence `OPTIONAL`, not `ADOPT`.
