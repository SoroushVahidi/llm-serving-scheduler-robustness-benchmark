# Provenance and frozen identities

The seven original JSON files in scientific/ are byte-for-byte copies of the admitted Phase-12 archive. Their absolute local source paths and SHA-256 values are in the private preparation report; the public checksum ledger records release bytes. No source JSON was repaired or recomputed during packaging.

| Identity | Frozen value |
|---|---|
| Campaign freeze SHA-256 | 81fa3d9b48a2241001e6820942d4542dcc5b5e30973ad9d2786e72972494f57a |
| Full design matrix hash | 832d96d7ff4d5e8843c233a6a4708bbbbc578ef6b65307c37f5ac127c62c1ccf |
| Execution source commit | 2b9a21fb58798292c95980d35d05e53b3c6f14f6 |
| Analysis source commit | eb574a8ce5c34a80fddbcfd4417f6626fbdddfd1 |
| Admitted matrix JSON SHA-256 | 73adf7d97f06985ec8f8e1c2f794fd43178433eb198e1c00705e817f4bde9c26 |
| Pinned matrix-validator source SHA-256 | 904e6287812bf5b69aac51fd29eac0971ba79f9dcf3b44a8e2bd6e0dbba822dc |
| Simulator configuration hash | a7a8920a43d4c1ba90da249f64d60e9929355e66f150aa1afd60f3599f98717b |

The included window, calibration, assignment, campaign-freeze, shard-plan and analysis-input manifests establish window, operating-region, policy, planned-key and source-to-analysis relationships. The admitted analysis-input manifest binds the exact consolidated artifact and validator identity. The original raw and repaired shard ledgers are identified by SHA-256 in that manifest but are omitted because they contain internal HPC paths; no shard result payload is needed to use the consolidated matrix.

Upstream input identities are BurstGPT without-fails v2 CSV SHA-256 56193aa9b2bb26128ded43d2d29a960df6bf5af062bcfc9b005f3fcaa4e6e501; Azure 2024 conversation CSV SHA-256 a0cc9b969a9bbf0fd811802cbf4323edd3a209ace791e3799ad4f9207f213941; Bailian/Qwen trace-B JSONL SHA-256 68e3f98e2d601d60d0abf4b89bc8a3654372abab7b1cde6373a13d0054379d59. Their request-level records are not included.

The included amended matrix-validation report is the passing pinned recheck of the admitted matrix. An earlier archived validation attempt had failed a prelaunch identity interpretation; the amended recheck resolves that identity and reports zero scientific row differences. See [VALIDATION.md](VALIDATION.md). The package's Parquet files are independently checked convenience views; the original JSON files determine scientific values.
