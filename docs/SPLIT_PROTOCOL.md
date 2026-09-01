# SPLIT_PROTOCOL.md

Splits are constructed from workload metadata only (source identity,
timestamp, provider) — **never from observed scheduler performance.** Once a
manifest is frozen and hashed, changing which windows belong to which split
requires a new manifest version, not an edit.

## Split types

1. **`source-ID`** — windows from the same source family used for both
   "training"/exploration and confirmatory analysis (baseline, not a
   generalization test by itself).
2. **`source-OOD`** — a scheduler-ranking finding established on sources
   `{A, B, C}` evaluated (never re-tuned) against a held-out source `D`
   (e.g. TraceLab as the domain-OOD source, per
   `configs/workloads/source_registry.yaml`).
3. **`temporal-OOD`** — where timestamps support it (Azure 2023 vs. Azure
   2024 is the primary pair; BurstGPT/Bailian windows split by collection
   date if the adapter's `field_provenance` confirms real timestamps).
4. **`provider/domain-OOD`** — grouping by provider identity (Azure vs.
   Alibaba Bailian vs. HPMLL BurstGPT vs. UW SyFi TraceLab) rather than by
   time.
5. **`final untouched test split`** — a fixed fraction of windows from every
   source, held out and not inspected by any exploratory analysis, reserved
   for the single confirmatory report of each RQ.

## Manifest format

`configs/splits/*.yaml`, each with: split name, construction rule, list of
`workload_window_id`s (or the deterministic rule that generates them),
construction timestamp, and a SHA-256 manifest hash computed over the
serialized window-id list. The hash is what `docs/REPRODUCIBILITY_CONTRACT.md`
requires every downstream result to cite.

## Bootstrap status

`configs/splits/` contains **placeholder manifests only** (empty window-ID
lists, real source-family/type fields) — real window IDs do not exist yet
because no workload-window construction has been run against real trace data
in this bootstrap task (only fixture-derived smoke tests, per
`docs/PROVENANCE.md`). Populating real manifests is Stage 0/1 work
(`docs/EXPERIMENT_CAMPAIGN_PLAN.md`).
