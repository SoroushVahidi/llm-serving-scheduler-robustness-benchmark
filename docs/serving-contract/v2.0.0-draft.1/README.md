# LSSP serving semantics 2.0.0-draft.1

**DRAFT — AUTHOR APPROVAL UNRESOLVED. NOT IMPLEMENTED. NOT PHYSICALLY VALIDATED.**

This specification is a prospective contract, not an amendment to a frozen run. It follows draft PR #4 (`efc5243898d18bbb62ccb51dcf66a0767827dac6`), stacked on #3 (`b14992716c20b36d26e6f28e60b2c8e0b8b09a07`). No serving code, workload, manuscript, historical output or prior protocol file changes here. No GPU, Slurm or Actions work.

Read in order:

1. [Source comparison and PR #4 boundary review](SOURCE_COMPARISON.md).
2. [Versioned semantic and instrumentation contract](SPECIFICATION.md).
3. [State transitions and independent expected cases](CONFORMANCE.md), with literal [cases.json](cases.json).
4. [Trace length/tokenizer/context audit](TRACE_MAPPING.md).
5. [Author decisions](AUTHOR_DECISIONS.md): recommendations are not approvals.
6. [Gaps and implementation sequence](IMPLEMENTATION_PLAN.md).
7. [Future physical fidelity gates](FIDELITY_GATES.md).
8. [Validation record](VALIDATION.md) and [evidence register](evidence/).

The recommended candidate uses common native-vLLM execution and a **named, explicitly adapted SLAI decision profile**. It does not equate that profile with literal execution of the pinned Sarathi-based SLAI implementation. Source-exact legacy reproduction is an alternative requiring separate controls; it cannot be obtained by silently enabling chunking in MGPU02. Author choices S01–S08 block adoption of the proposed profile. Numeric cases are small conformance vectors, not workload or pressure prescriptions.

The current execution authority remains `mgpu02-whole-prefill-v1` and the existing approved MGPU06 commit/configuration. This branch provides no permission to substitute a new execution commit or run even the first pair. PR #4's previously recorded 271 tests are engineering evidence, not partial-prefill or distributed acceptance.

## Versioning and historical separation

Prospective run identity must include `semantics_id`, `semantics_revision_sha256`, `policy_profile_id`, `execution_schema_id`, `analysis_version`, implementation/source hashes, deployment and workload-manifest hashes. Candidate IDs are in [manifest.json](manifest.json). A stable release cannot be named `2.0.0` until author approval and its specified conformance gates are recorded. Draft revisions increment the draft suffix and retain their prior hashes/corpus; expectation changes after outcomes require a dated amendment, not rewriting an oracle to fit an adapter.

Never rewrite old runs as v2. Existing simulator names, `mgpu02-whole-prefill-v1`, MGPU05 measurement records, 240 historical physical executions and their known limitations retain original labels. Simulator progress/allocation changes require a new simulator semantics ID and separately generated evidence; old/new results cannot be pooled as repeated executions of one mechanism. Any bridge comparison is prospective, separately authorized and reports both contracts. A decision-only simulator match does not establish GPU timing or communication fidelity.

Interpretation: **verified** means source inspection or named CPU evidence; **proposed** means conditional expected behavior awaiting approval; **NOT VERIFIED** means missing implementation, raw coverage, runtime or physical evidence. No case below is a measured scheduler ranking.
