# LSSP M3 local research artifact candidate rc1 — 2026-10-22

This is a **local candidate for author approval**, not a published release or assigned DOI. It contains the complete frozen C01 and STAT01 records needed to inspect the executed comparison and recalibrate saved endpoint summaries. No command below runs new scientific experiments. The separate upstream-source archive is optional for verification because the exact executed request inputs are bundled here.

## Contents and reading order

1. `paper/tompecs-m3/m3-manuscript.pdf` (review layout) and `m3-acmsmall.pdf`; current reports under `paper/tompecs-m3/artifact-release/`.
2. `COMMITS.json` and `MANIFEST.json`: exact code identities and SHA-256/size of every payload file. The manifest identifies the manuscript working-tree snapshot; the external final report identifies the final PR commit. `.git`, credentials and correspondence are excluded.
3. `evidence/c01/`: full execution root, all 5,760 terminal records and compressed journals, 720 exact input conditions, 120-window provenance, reuse ledger, configuration, launch fingerprints, analysis and completion logs. The 144 reused cells are under `reused/`; the 5,616 new cells are under `runs/c01-full-167b9074e5711420/cells/`.
4. `evidence/stat/`: recovery code, launch/source ledger, all 5,360 batches containing raw arrays/masks, original study records, post-diagnosis records and integrity/moment records; all saved precision looks, checkpoint, completion and logs. `evidence/stat-original/` contains original frozen code, reference arithmetic and launch definition. Reused records are physically included in recovery batches; the redundant original campaign's entire raw tree is intentionally not duplicated.
5. `code/c01/` and `code/stat01/`: scoped `git archive` snapshots at exact execution commits, including model/loaders, configuration and protocols. Some code duplicates execution-root files so the commit-level source and launch-level bytes can be checked independently; the large raw files are not duplicated within an archive.
6. `THIRD_PARTY_NOTICES.md` and the paper's `artifact-release/SOURCE_PROVENANCE.md`: original source hashes, license coverage, attribution and transformation notices. Dataset licenses do not inherit the project software license.

`evidence/input-lineage/` also retains the exact frozen 120-window file, pilot-input payload, and historical consolidated/pairwise support; `input-lineage.json` in the paper documentation records their hashes. This permits inspection of the source-to-input chain and archived-rule support without substituting a fresh source selection.

The main archive contains no remotely-only C01/STAT01 raw-record dependency. Original source datasets are in `lssp-m3-rc1-20261022-upstream-sources.tar.gz`; see its own manifest. Historical submissions and unrelated raw campaigns are not presented as part of this complete **C01/STAT01** scope.

## Environment

Use Python 3.12.3 with NumPy 2.3.5, SciPy 1.17.1 and Matplotlib 3.10.9 for the locally checked saved-data workflow. `paper/tompecs-m3/artifact-release/requirements-display.txt` pins these packages. This is not a lockfile for the original experiment environment. C01's launch pins Python 3.12.13; original STAT01 pins Python 3.12.13 / NumPy 2.5.2 / SciPy 1.18.1. Those frozen records are preserved. No fresh campaign or clean installation of that execution environment was performed.

PDF build tools used: pdfTeX 3.141592653-2.6-1.40.25, BibTeX 0.99d, TeX Live 2023/Debian and Poppler. The included acmart files are the inherited byte-preserved template; a current official manual check is separate from replacing the template. Install these system tools and the pinned display requirements in a suitable environment. Network installation is a future reader action, not required by the verifier. A second OS/architecture and an air-gapped dependency installation have not been tested.

## Verify a clean extraction

From a new directory, verify the external `SHA256SUMS`, then extract the evidence archive. For example (archive names are literal):

```bash
sha256sum -c SHA256SUMS
mkdir extracted
python -c "import tarfile; tarfile.open('lssp-m3-rc1-20261022-evidence.tar.gz').extractall('extracted', filter='data')"
python extracted/paper/tompecs-m3/artifact-release/verify_candidate.py extracted --output verification --samples
```

The verifier checks every manifest hash, all C01 result/journal fingerprints against frozen analysis, all three payload hashes for each STAT batch, launch/code/source ledger fingerprints, all terminal metrics and chunked/decode terminal equality, every final STAT endpoint using independently recombined decimal moments, and every recorded stopping look. `--samples` additionally replays 24 structurally fixed event journals and referees 200 existing study records, including the preserved original numerical-boundary failure. It **does not simulate a request or generate a study**. Fresh complete journal/134,000-study referee replay is not claimed; prior exhaustive in-campaign checks remain separately identified.

Outputs go to the specified directory. Checks do not depend on the Wulver host or absolute development paths recorded in frozen provenance. Do not use Python `-O`, which disables assertions used by the frozen checkers.

## Recompute displays and build both PDFs

From the extracted root:

```bash
python paper/tompecs-m3/scripts/render.py
bash paper/tompecs-m3/scripts/build.sh manuscript
bash paper/tompecs-m3/scripts/build.sh acmsmall
python paper/tompecs-m3/scripts/validate.py --standalone
```

This verifies 37 saved input hashes, regenerates five tables, three vector figures and all CSV summaries, recomputes C01 ranking/reversal reports with an independent oracle, checks 54 numerical narrative anchors and 7,200 STAT endpoint rows, and checks final LaTeX/BibTeX logs. The fourth figure is TikZ; the other three tables are manuscript source. `--standalone` explicitly excludes the Git/history working-tree preservation check because archives have no `.git`; that check was performed in the author workspace and documented. Compare newly generated tables/CSVs/figure hashes with `MANIFEST.json` before changing files. PDF builds are visually/numerically reproducible; location-dependent PDF IDs may prevent byte-identical PDFs across extraction paths.

Regeneration changes display/build files, so run archive-integrity verification **before** regeneration, or preserve a second pristine extraction. All source/output identities stay available in the manifest. No default script runs `campaign.py`, `simulate`, a Monte Carlo runner, `sbatch`, or an upload.

## Reconstructing the original experiment — future action only

The launch manifests, protocols, exact scoped source snapshots, original input requests, scenario/seed definitions, batch size, method identities and environment records document reconstruction. Frozen original launch scripts contain site-specific paths and HPC settings, so they are historical evidence, not portable turnkey commands. A future authorized reconstruction would require adapting paths and dependencies, honoring original versus expanded method/uncertainty identities, then explicitly invoking the campaign entry points. This candidate's tested workflow stops at saved-data checks. No experiment reconstruction command was executed in this preparation.

## Access, rights and limitations

This candidate supplies a complete local C01/STAT01 payload and a portable saved-data workflow. Reviewer delivery, approved license scopes, archival versioning and DOI assignment remain author decisions. The historical Hugging Face/Zenodo artifacts do not constitute release of these campaigns. See `READINESS.md`, `AUTHOR_DECLARATIONS.md`, `RELATED_MANUSCRIPTS.md` and `VERIFICATION.md` in the paper's `artifact-release/` directory. Internal timestamps, host paths and immutable old labels are provenance, not instructions to contact a system or assertions of journal acceptance.
