# M3 artifact readiness and focused strengthening

Start with [READINESS.md](READINESS.md) for the **NOT_READY submission verdict and remaining author/venue gates**, [SOURCE_PROVENANCE.md](SOURCE_PROVENANCE.md) for resolved source identities/licenses, and [RELATED_MANUSCRIPTS.md](RELATED_MANUSCRIPTS.md) for user-verified dispositions and active-line distinctions.

The complete local candidate lives outside Git at `/home/soroush/artifacts/lssp-m3-rc1-20261022/`. [INVENTORY.md](INVENTORY.md) distinguishes original frozen locations, locally bundled evidence, historical public releases and unapproved external access. [CANDIDATE_README.md](CANDIDATE_README.md) is the practical reader guide copied into the archive. [VERIFICATION.md](VERIFICATION.md) and machine records describe checks and their limits. [AUTHOR_DECLARATIONS.md](AUTHOR_DECLARATIONS.md) supplies unmistakable author-confirmation fields.

## Local packaging recipe

First obtain read-only copies of the frozen C01 execution root, STAT recovery root and original STAT code/reference/launch at the exact paths in INVENTORY.md. Place them under a new `staging/evidence/{c01,stat,stat-original}` directory. Also copy the four frozen `evidence/input-lineage/` files identified by [input-lineage.json](input-lineage.json), checking their full hashes; these are existing inputs/historical records, not newly synthesized data. Place the three hash-verified source files under `staging/source-data`. Transfer via authenticated read-only download to new local destinations; do not modify remote evidence. Exclude `.git`, virtual environments and caches. All campaign payloads remain intact.

Then, with repository paths supplied explicitly:

```bash
python paper/tompecs-m3/artifact-release/prepare_candidate.py \
  --staging /path/outside-git/staging --output /path/outside-git/archives \
  --repo /path/to/this/checkout --stat-repo /path/to/stat01/checkout
python paper/tompecs-m3/artifact-release/test_extraction.py \
  /path/outside-git/archives/lssp-m3-rc1-20261022-evidence.tar.gz \
  /path/outside-git/new-extraction --output /path/outside-git/verification
```

`prepare_candidate.py` uses scoped `git archive` snapshots at hard-coded frozen execution commits, copies the reviewed manuscript, supplies notices, creates full SHA-256 manifests and deterministic gzip/tar payloads. It has no network call, scheduler submission, simulator invocation or upload. The archive excludes Git object stores and raw datasets from the main evidence payload; source files receive a separate optional archive with license texts. `--archives-only` deliberately repacks an already prepared tree; it does not regenerate experiments.

`test_extraction.py` creates a fresh destination, verifies every saved payload, runs the bounded saved-record checks, regenerates displays and builds the PDFs. It compares regenerated tables/CSVs/figures byte-for-byte. Reports are written outside the extracted payload; they are companion evidence rather than a self-referential archive hash. The final PR report and archive checksum records are finalized after this check, so those administrative companion files can be newer than their pre-packaging explanatory counterparts in the archive. Exact manuscript/code/data identities are in the archive manifest and commit ledger.

[Environment pins](requirements-display.txt) are versions actually used for the checked saved-data workflow. Execution-environment pins are separately preserved in launch records. Installing those dependencies elsewhere and reconstruction of original experiments are future actions; no such experiment was executed here.
