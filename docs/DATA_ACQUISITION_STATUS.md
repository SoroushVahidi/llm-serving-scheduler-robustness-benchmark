# DATA_ACQUISITION_STATUS.md

Resolves the second bootstrap blocker recorded in `docs/GO_NO_GO_GATES.md`
("real data not yet acquired for any of the three pilot sources"). No new
download was performed in this session -- all three Stage-0 sources were
already acquired to NJIT Wulver's shared project storage in an earlier
session (2026-07-24/25) for a related project, with their own provenance
manifests already recorded there. This project's own repo does not copy
these multi-GB files (per `docs/DATA_LICENSE_AUDIT.md`); it references them
read-only by absolute Wulver path and independently re-verified SHA-256.

All three checksums below were re-computed directly against the on-disk
files by this session (`sha256sum`, 2026-09-01), not copied from the prior
acquisition's manifest -- they are reported here only after matching the
prior manifest exactly.

## Azure LLM Inference Trace 2024

- Canonical source: Microsoft `Azure/AzurePublicDataset`,
  `AzureLLMInferenceDataset2024`, collection window 2024-05-10 to 2024-05-19.
- License: CC-BY (permits redistribution with attribution). Not
  redistributed by this project -- referenced read-only.
- Acquisition path (read-only, not duplicated into this repo):
  `/project/ikoutis/sv96/llmserveopt-data/datasets/azure_llm_2024/raw/AzureLLMInferenceTrace_conv_2024.csv`
  (conversation split, used for Stage-0) and
  `AzureLLMInferenceTrace_code_2024.csv` (code split, not used in Stage-0).
- File size (conversation split): 1,135,195,393 bytes.
- SHA-256 (conversation split, re-verified 2026-09-01):
  `a0cc9b969a9bbf0fd811802cbf4323edd3a209ace791e3799ad4f9207f213941` --
  matches the prior acquisition's `manifests/integrity_AzureLLMInferenceTrace_conv_2024.csv.json` exactly.
- Row count (per prior manifest, consistent with this session's streaming
  read used to build Stage-0 windows): 27,303,999 data rows.
- Field validation: header confirmed `TIMESTAMP,ContextTokens,GeneratedTokens`
  (matches `src/robustbench/workloads/external/adapters/azure_llm.py`'s
  expected schema exactly).
- Chronology validation: `TIMESTAMP` is a real, monotonic-non-decreasing
  ISO wall-clock field per the prior manifest (`first_timestamp`/
  `last_timestamp` span 2024-05-12T00:00:00 to 2024-05-19T00:00:00 UTC,
  consistent with the documented collection window).
- Malformed/dropped rows for this project's Stage-0 use: see
  `artifacts/manifests/stage0_windows.json`'s
  `source_sampling_reports.azure_llm_2024_conversation` field for the exact
  count of rows dropped for missing/non-positive token fields during Stage-0
  window construction.
- Redistribution status: permitted with attribution; this project does not
  redistribute the raw file, only its own small derived window manifest
  (extracted Layer-1 records for the 10 frozen Stage-0 windows, ~2,000 rows
  total out of 27.3M).

## Bailian/Qwen anonymized traces

- Canonical source: `alibaba-edu/qwen-bailian-usagetraces-anon`, pinned tip
  `commit:5f7439c51ec248a0c585f7d90a41a6f57773b912` (per the prior
  acquisition's provenance manifest; this session did not independently
  re-verify the upstream commit still matches, only the local file's
  checksum).
- License: Apache-2.0 (permits redistribution).
- Acquisition path (read-only): this project's Stage-0 pilot uses
  `/project/ikoutis/sv96/llmserveopt-data/datasets/bailian_qwen/raw/qwen_traceB_blksz_16.jsonl`
  -- the larger of the two general-traffic traces (`traceA`/`to_c`,
  `traceB`/`to_b`), chosen over the `coder`/`thinking` specialized traces so
  the Stage-0 sample represents general production traffic rather than a
  task-specialized subset. This is a documented convenience choice, not a
  scientific claim that traceB is more representative than traceA.
- File size: 96,209,982 bytes.
- SHA-256 (re-verified 2026-09-01):
  `68e3f98e2d601d60d0abf4b89bc8a3654372abab7b1cde6373a13d0054379d59` --
  matches the prior acquisition's `manifests/integrity_qwen_traceB_blksz_16.jsonl.json` exactly.
- Row count (per prior manifest): 172,800 data rows.
- Field validation: header keys confirmed
  `chat_id, hash_ids, input_length, output_length, parent_chat_id, timestamp, turn, type`
  -- matches `src/robustbench/workloads/external/adapters/bailian.py`'s
  expected field mapping.
- Chronology validation: `timestamp` is relative-to-trace-start (0.0 to
  7199.97 seconds, i.e. a ~2-hour trace), not an absolute calendar date --
  consistent with `docs/DATA_FIELD_PROVENANCE.md`'s documented caveat for
  this source. Sufficient for within-trace chronological windowing (used
  here), insufficient by itself for calendar-date temporal-OOD splits.
- Malformed/dropped rows for Stage-0: see
  `artifacts/manifests/stage0_windows.json`'s
  `source_sampling_reports.bailian_qwen_traceB` field.
- Redistribution status: permitted; this project does not redistribute the
  raw file.

## BurstGPT

- Canonical source: `HPMLL/BurstGPT`, release tag `v2.0`.
- License: CC-BY-4.0 (permits redistribution with attribution).
- Acquisition path (read-only): this project's Stage-0 BurstGPT windows are
  drawn specifically from
  `/project/ikoutis/sv96/llmserveopt-data/datasets/burstgpt_v2/raw/BurstGPT_without_fails_2.csv`
  -- see `src/robustbench/workloads/external/burstgpt_independent_sampling.py`
  for why file 2 (not file 1) was chosen (independence motivation, not a
  data-quality reason -- all three `_without_fails_{1,2,3}.csv` files are
  the same release's chunked shards).
- File size: 142,376,815 bytes.
- SHA-256 (re-verified 2026-09-01):
  `56193aa9b2bb26128ded43d2d29a960df6bf5af062bcfc9b005f3fcaa4e6e501` --
  matches the prior acquisition's `manifests/integrity_BurstGPT_without_fails_2.csv.json` exactly.
- Row count (per prior manifest): 3,784,213 data rows.
- Field validation: header confirmed
  `Timestamp,Model,Request tokens,Response tokens,Total tokens,Log Type` --
  matches `src/robustbench/workloads/external/adapters/burstgpt.py`'s
  expected schema (the adapter does not use the `Log Type` column).
- Chronology validation: `Timestamp` is numeric, seconds-from-local-midnight
  convention per the source's documented schema; file 2's range
  (first_timestamp=5270414.0, last_timestamp=10454395.0) is a later,
  disjoint time slice from file 1's range (first_timestamp=5.0,
  last_timestamp=5269973.0) -- i.e. files 1 and 2 are genuinely
  chronologically sequential shards of the same release, not overlapping
  copies, which is part of this project's BurstGPT independence rationale
  (see `burstgpt_independent_sampling.py`'s disclosure).
- Malformed/dropped rows for Stage-0: see
  `artifacts/manifests/stage0_windows.json`'s
  `source_sampling_reports.burstgpt` field.
- Redistribution status: permitted with attribution; this project does not
  redistribute the raw file.

## What this resolves

Per `docs/GO_NO_GO_GATES.md`'s bootstrap-time blocker list: "real data has
not been acquired for any of the three pilot sources" is resolved -- real
data was already acquired (a prior session, different project, same Wulver
project storage) and is now independently re-verified and wired into this
project's own Stage-0 window-freezing pipeline
(`scripts/build_stage0_windows.py`) read-only. No new multi-GB download was
performed, consistent with the instruction not to needlessly re-acquire data
that already exists on the target cluster.
