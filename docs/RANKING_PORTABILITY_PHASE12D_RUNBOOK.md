# Phase-12D provenance repair / completed-validation runbook

This runbook executes **metadata enrichment and structural validation only**.
It must not execute a scheduler cell or run comparative/statistical analysis.

## Preconditions

Frozen campaign:

- campaign freeze: `81fa3d9b48a2241001e6820942d4542dcc5b5e30973ad9d2786e72972494f57a`
- full matrix: `832d96d7ff4d5e8843c233a6a4708bbbbc578ef6b65307c37f5ac127c62c1ccf`
- execution Git SHA: `2b9a21fb58798292c95980d35d05e53b3c6f14f6`
- Slurm array: `1215964`, 64/64 tasks completed `0:0`
- expected rows: 18,720

Raw Wulver namespace (READ ONLY):

`/project/ikoutis/sv96/github/llm-serving-scheduler-lssp-phase12-campaign-run/artifacts/campaign_results/81fa3d9b48a22410`

Never run Phase-12D from the raw campaign execution worktree if doing so would
modify it.  Use the dedicated repair branch/worktree and pass the raw path
explicitly.

## 1. Tests first

From the Phase-12D repair worktree:

```bash
python -m pytest -q tests/test_ranking_portability_phase12_provenance.py
python -m pytest -q
```

If the full suite is materially long, run it under TMUX or Slurm and inspect
about the first three minutes for healthy progress rather than attaching an
interactive session until completion.

## 2. Enrich provenance

Example on Wulver (replace `<REPAIR_WORKTREE>` with the checked-out repair
branch path):

```bash
cd <REPAIR_WORKTREE>
python scripts/ranking_portability/enrich_phase12_campaign_provenance.py \
  --raw-dir /project/ikoutis/sv96/github/llm-serving-scheduler-lssp-phase12-campaign-run/artifacts/campaign_results/81fa3d9b48a22410 \
  --enriched-dir /project/ikoutis/sv96/github/llm-serving-scheduler-lssp-phase12-provenance-repair/artifacts/campaign_results_enriched/81fa3d9b48a22410
```

This operation:

1. validates campaign/shard identities;
2. records SHA-256 + row count for every original raw shard;
3. fills only the seven approved provenance fields in derivative copies;
4. rejects any nonempty conflicting provenance;
5. checks raw→enriched non-provenance invariance row-by-row;
6. rechecks each raw shard hash after writing;
7. writes repaired-shard hashes and a deterministic consolidated artifact.

The raw namespace is never opened for writing.

### Historical hash limitation

No per-shard cryptographic ledger was recorded during the earlier completion
inspection.  Consequently Phase-12D cannot prove retrospectively that bytes
were identical between that inspection and the first Phase-12D ledger.  The
pre-ledger provenance evidence is instead the completed Slurm accounting,
64/64 clean shard structure, zero nonempty stderr logs, and the structural
18,720/18,720 inspection.  Once Phase-12D creates the raw ledger, every
subsequent step cryptographically enforces immutability against it.

Do not conceal this limitation in paper/artifact documentation.

## 3. Independent completed-campaign validation

```bash
python scripts/ranking_portability/validate_phase12_completed_campaign.py \
  --raw-dir /project/ikoutis/sv96/github/llm-serving-scheduler-lssp-phase12-campaign-run/artifacts/campaign_results/81fa3d9b48a22410 \
  --enriched-dir /project/ikoutis/sv96/github/llm-serving-scheduler-lssp-phase12-provenance-repair/artifacts/campaign_results_enriched/81fa3d9b48a22410
```

A successful validation creates:

`artifacts/manifests/ranking_portability_phase12_analysis_input.json`

and reports both:

`PHASE12_COMPLETED_CAMPAIGN_VALID = true`

`PHASE12_ANALYSIS_INPUT_ADMITTED = true`

If either is false, STOP.  Do not run ranking analysis.

## 4. Scientific safety

Phase-12D may parse metric/telemetry fields solely for schema validation and
byte/value invariance.  It must not aggregate them by policy, calculate a
winner, compute Kendall/Spearman/top-k/reversal statistics, or inspect
comparative direction.

The next scientific step after a PASS is the separately prefrozen statistical
analysis pipeline reading only the admitted consolidated artifact.
