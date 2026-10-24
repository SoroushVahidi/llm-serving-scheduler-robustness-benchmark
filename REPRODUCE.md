# Reproduce saved-evidence analyses

These commands read saved experimental records. They do not regenerate simulations, submit SLURM jobs, acquire traces or publish anything. Use normal Python, not `python -O`, because frozen validators use assertions. Verify the external archive SHA-256 first; extract safely into a fresh directory, then run from the canonical package root:

```bash
sha256sum -c SHA256SUMS
python tools/verify_inventory.py .
python tools/verify_tables.py .
python tools/export_tables.py . --output ../tables-reexported
```

Create a Python 3.12 environment outside the artifact and install `requirements-verification.txt`. The top-level pins and previously tested resolved package inventory are supplied. They are not a hash-pinned portable wheel lock. System TeX Live 2023/Debian, BibTeX and Poppler are needed only for manuscript rebuilds. No GPU is required. Space for an extracted copy is about 3.4 GB plus a small writable paper copy; allow additional space if duplicating the complete archive.

```bash
python3.12 -m venv ../m3-venv
. ../m3-venv/bin/activate
python -m pip install -r requirements-verification.txt
python paper/tompecs-m3/artifact-release/verify_candidate.py . --output ../saved-checks --samples
```

The frozen verifier checks all launch/input/file identities, 5,760 result/journal pairs and 5,360 STAT01 batch payload sets. Independent semantic referees sample 24 journals and 200 saved studies; this is not exhaustive fresh replay of 134,000 studies. The C01 terminal-summary oracle and full statistical endpoint checks are separate from those sampled raw-record checks.

Some historical analysis scripts write beside their own source. Run them only in a separate writable copy of `paper/`, with the canonical evidence path passed explicitly:

```bash
mkdir ../m3-work
cp -a paper ../m3-work/
# Set this before changing directory; it is the pristine package's absolute path.
M3_ARTIFACT_ROOT="$PWD"
cd ../m3-work
python paper/tompecs-m3/scripts/render.py
python paper/tompecs-m3/editorial-revision/reduced_comparisons.py
bash paper/tompecs-m3/scripts/build.sh manuscript
bash paper/tompecs-m3/scripts/build.sh acmsmall
python paper/tompecs-m3/major-revision/verify_example.py "$M3_ARTIFACT_ROOT" --report ../worked-example.json
python paper/tompecs-m3/scripts/validate.py --standalone --report ../manuscript-validation.json
python paper/tompecs-m3/budget-sensitivity/verify_study.py "$M3_ARTIFACT_ROOT/evidence/budget" "$M3_ARTIFACT_ROOT"
python paper/tompecs-m3/urgency-analysis/check_certificate.py "$M3_ARTIFACT_ROOT" "$M3_ARTIFACT_ROOT/evidence/budget"
```

Do not pass --artifact-root to the standalone manuscript validator: its inherited internal worked-example output location violates the frozen output-protection guard. The separate worked-example command above uses an external report. The Git-history editorial checker is archived only in the source PR and is not a standalone archive command. Build scripts may create local build products; no generated build is copied into the frozen artifact.

Expected: all commands exit zero; 53 narrative checks, 7,200 endpoint rows, all C01 ranking/pairwise/reversal summaries pass; 72 budget records and 18 urgency certificates pass. The 16 regenerated main figure/table/supplement files matched their original bytes in this audit. The integrated principal PDF and alternative build are both 30 pages; exact hashes are in MANUSCRIPT_IDENTITY.json. The optional ACM-small build has 30 pages. Cross-environment TeX/PDF differences require inspection rather than altering scientific values.

The theorem and original saved validation records are in code/bound01 and evidence/bound01; proof/source hashes match PR #29's reviewed record. No new fixture execution was required here. Full upstream-window selection, full simulations, every statistical decision, a fresh OS/container and a second architecture were not rerun. Upstream raw traces require separate acquisition. Historical HPC scripts need site adaptation. Therefore the supported claim is reproducibility of saved-evidence analyses under the documented environment, not fully automated end-to-end campaign replication from fresh provider downloads.


## TIME01 and ABL01 saved analyses

Run in a fresh output directory outside the canonical package:

```bash
python tools/reproduce_extensions.py . --output ../m3-extension-checks
```

This portable adapter materializes read-only dependency views linking evidence/time01 and evidence/abl01 to their frozen code and the original C01 records. Frozen manifests and baseline paths are preserved; all 384 copied TIME01 baselines are retained exactly to preserve frozen analyzer expectations. It independently recomputes terminal metrics, pairing, source means, ranks and exact reversal counts, then reproduces all eight ABL01 CSVs and verification.json byte-for-byte. CSV schema order is restored without changing values. Original Git-blob linkage checks are archived; the portable run checks packaged code hashes against immutable source manifests. No Git checkout, remote account, upstream trace acquisition, journal reconstruction or simulation is required.

The default reuses the hash-linked independent review of all TIME01 journals and 36 stratified ABL01 controls with 72 source journals. Add --journals to repeat precisely that semantic coverage. All 1,440 derived ABL journal byte hashes are verified separately during rc3 packaging; byte verification is not a fresh semantic replay of the remaining 1,404 journals. C01/budget/BOUND01/STAT01 original evidence remains unchanged. Complete campaign reproduction requires site/path adaptation and upstream acquisition. Compact GitHub or dataset-only views cannot execute full-evidence checks without the canonical archive.
