# Validation and public verification

The original passing amended report is included at validation/phase12_amended_matrix_validation.json. Its pinned validator source SHA-256 is 904e6287812bf5b69aac51fd29eac0971ba79f9dcf3b44a8e2bd6e0dbba822dc. It reports PHASE12_COMPLETED_CAMPAIGN_VALID=true; 18,720 expected, unique and successful cells; 9,360 correct repetition pairs; zero missing, unexpected or duplicated cells; zero schema, telemetry, assignment, source-hash, shard-drift or unresolved failures; and problems=[]. Its independently recomputed design hash matches 832d96d7ff4d5e8843c233a6a4708bbbbc578ef6b65307c37f5ac127c62c1ccf.

Run from the package directory:

    python scripts/validate_release.py
    python scripts/validate_release.py --verify-public-smoke
    sha256sum -c checksums/v1.1.0.sha256

The first command reads only package files. It checks the exact release allowlist and SHA-256 ledger; seven frozen scientific hashes; campaign, source, policy, region, seed and simulator identities; all 18,720 complete unique keys and 9,360 deterministic pairs; schema and conditional-NaN behavior; six canonical analysis counts/identities; all 11 Parquet views against every original source row, with exact numeric comparison and NaN awareness; legacy v1 files; and the 468-key overlap sidecar. The optional second command also fetches the pinned approximately 976 KB public GitHub smoke file, checks its original SHA-256 and compares its 468 numerical/telemetry projections. Network access is needed only for that option.

The public validator does not run scientific simulations or recompute bootstrap/logistic/Friedman analyses. It checks the frozen analysis outputs and their source identity. The Parquet files are reproducible convenience conversions; validation compares every row and never changes original JSON. In private preparation, the public manuscript table generator successfully read all six unchanged canonical files and reproduced four public RQ table JSONs with equal scientific fields; only generation time and script checkout identity differed. The validator result and loader/table-test logs are in the preparation audit, rather than bundled as claims about future published bytes.

Release packaging must be rerun through the public validator after any edit, since a changed file invalidates the checksum ledger. A subsequent archive or HF revision should publish the exact allowlist, checksum ledger, revision commit, and any dataset DOI once issued.

The root checksums.json is the unchanged v1.0.0 legacy partial ledger. For this complete v1.1.0 release, use checksums/v1.1.0.sha256; the two ledgers have different scopes.
