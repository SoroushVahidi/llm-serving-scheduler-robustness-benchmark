# Revised manuscript companion v1 and unchanged rc1 evidence

The rc1 snapshot at `/home/soroush/artifacts/lssp-m3-rc1-20261022/` is unchanged. It contains PR21-era manuscript bytes and complete frozen C01/STAT01 evidence. **It does not contain this revised manuscript or worked-example support.** The current revision is based on `2a65c0e139d1410475170781469901559960265d`; its implementation commit and draft PR are in `FINAL_REPORT.md`, and the final report commit is recorded externally in the run's `completion.json`.

After final documentation and packaging, `assemble_companion.py` creates `/home/soroush/artifacts/lssp-m3-major-revision-companion-v1-20261022/`. This small versioned directory contains the complete revised manuscript packet (including saved display summaries), a payload checksum manifest and Git identities. It contains **no raw C01/STAT campaign tree, source dataset or multi-GB archive**. The final run completion record identifies its manifest. No external publication is authorized or performed.

The paired frozen archives remain:

| rc1 file under `archives/` | Bytes | SHA-256 |
|---|---:|---|
| `lssp-m3-rc1-20261022-evidence.tar.gz` | 2597049129 | `9543ed38051c95a3b781dd0bc1086e049d4d08b56aa0ad7e06d603dc93457e9b` |
| `lssp-m3-rc1-20261022-upstream-sources.tar.gz` | 337808093 | `a6d3ef2647492e79c580ab85eecf6cd47a9107d33ac4dc08757bda0900077853` |

## Pair without copying raw archives

1. Keep rc1 pristine. Verify its original archive/manifest as documented by PR21 before any regeneration. The present task rechecked both archive digests and selected example payloads; the earlier full clean-extraction checks remain separately dated.
2. Use the companion's `paper/tompecs-m3/` for the revised paper. Its external `MANIFEST.json` hashes all included files; the paper's `evidence/package-manifest.json` hashes the final manuscript payload except itself. `COMMITS.json` records the final Git identity without a self-referential report hash.
3. Pass the unchanged rc1 staging or extracted root to both example scripts. The code resolves `evidence/c01/` beneath that root, so no raw duplication or site-specific historical absolute path is needed.

```bash
python /path/to/companion/paper/tompecs-m3/major-revision/analyze_example.py /path/to/rc1-extraction --output /tmp/m3-example
python /path/to/companion/paper/tompecs-m3/major-revision/verify_example.py /path/to/rc1-extraction --derived /tmp/m3-example --report /tmp/m3-example-check.json
```

Use Python without `-O`; install the display requirements documented by PR21 (NumPy is needed by the independent checker). The standard-library generator and independent array/event reconstruction both accept an artifact root, verify full hashes and fail on identity mismatch. They never select another window.

For rebuilding, use a working copy of the small companion packet, because display/build/validation scripts write reports and PDFs there:

```bash
python paper/tompecs-m3/scripts/render.py
bash paper/tompecs-m3/scripts/build.sh manuscript
bash paper/tompecs-m3/scripts/build.sh acmsmall
python paper/tompecs-m3/scripts/validate.py --standalone --artifact-root /path/to/rc1-extraction
python paper/tompecs-m3/scripts/package.py
```

With no artifact root, validation explicitly checks only the saved example report and support hashes; it does not pretend to reconstruct raw journals. `--standalone` omits the Git/history checkout check and labels that omission. No experiment entry point is called. Existing source notices and unresolved final license scopes accompany the packet; the companion is not a license grant or an immutable public release. A later approved release must pair these revised manuscript bytes with the pinned unchanged rc1 evidence and assign the approved access/version/retention information.
