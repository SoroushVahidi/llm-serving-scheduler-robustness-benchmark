#!/usr/bin/env python3
"""Run frozen Stage-0 load calibration against the 30 frozen real windows.

Reads `artifacts/manifests/stage0_windows.json` (produced by
`build_stage0_windows.py`), synthesizes Requests for each window via
`benchmark_synthesis.synthesize_requests_from_window` (Layer 3), then runs
`calibration.stage0_load_calibration.calibrate_window` per window -- BEFORE
any of the six policies-under-study is run against these windows, per
docs/LOAD_CALIBRATION_PROTOCOL.md.

Per-window synthesis seed is `900000 + window_index` (window_index = the
window's 0-based position in the frozen windows list, stable given the
windows manifest is itself frozen) -- documented here, not chosen after
seeing any calibration result.

Pure Python/numpy -- does not require the real multi-GB source files (the
windows manifest already embeds the extracted Layer-1 records), so this
script runs from the committed manifest alone, on any machine with this
repo installed.
"""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from robustbench.calibration.stage0_load_calibration import calibrate_window  # noqa: E402
from robustbench.workloads.external.benchmark_synthesis import (  # noqa: E402
    SYNTHESIS_VERSION,
    synthesize_requests_from_window,
)
from robustbench.workloads.external.schema import ExternalWorkloadRecord  # noqa: E402

SYNTHESIS_SEED_BASE = 900_000


def _git_sha() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO_ROOT).decode().strip()


def _sha256_file(path: Path) -> str:
    import hashlib

    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _record_from_dict(d: dict) -> ExternalWorkloadRecord:
    return ExternalWorkloadRecord(**d)


def main() -> None:
    windows_path = REPO_ROOT / "artifacts" / "manifests" / "stage0_windows.json"
    out_path = REPO_ROOT / "artifacts" / "manifests" / "stage0_load_calibration.json"

    with open(windows_path) as f:
        windows_manifest = json.load(f)

    windows_manifest_sha256 = _sha256_file(windows_path)
    entries = []
    n_implausible = 0

    for i, w in enumerate(windows_manifest["windows"]):
        window_id = w["window_id"]
        source_family = w["source_family"]
        records = [_record_from_dict(r) for r in w["records"]]
        seed = SYNTHESIS_SEED_BASE + i
        requests, synth_manifest = synthesize_requests_from_window(records, window_id=window_id, seed=seed)
        if len(requests) < 2:
            raise SystemExit(
                f"STOP: window {window_id} synthesized only {len(requests)} usable requests "
                f"(dropped {synth_manifest.n_records_dropped_invalid} of {len(records)}) -- "
                "cannot calibrate load on a near-empty window. This indicates a data or "
                "windowing defect, not something to paper over."
            )
        cal = calibrate_window(requests, window_id=window_id, source_family=source_family)
        cal_dict = cal.to_dict()
        cal_dict["synthesis"] = synth_manifest.to_dict()
        entries.append(cal_dict)
        if not cal.sanity["plausible"]:
            n_implausible += 1
        print(
            f"[{i+1}/30] {window_id} ({source_family}): lambda_ref={cal.lambda_ref:.4f} "
            f"plausible={cal.sanity['plausible']} notes={cal.sanity['notes']}",
            file=sys.stderr,
        )

    manifest = {
        "manifest_kind": "stage0_load_calibration",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "repo_sha": _git_sha(),
        "windows_manifest_sha256": windows_manifest_sha256,
        "synthesis_version": SYNTHESIS_VERSION,
        "synthesis_seed_base": SYNTHESIS_SEED_BASE,
        "n_windows": len(entries),
        "n_windows_implausible_calibration": n_implausible,
        "calibrations": entries,
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(manifest, f, indent=2)

    manifest_sha256 = _sha256_file(out_path)
    print(f"Wrote {out_path} ({out_path.stat().st_size} bytes)", file=sys.stderr)
    print(f"manifest_sha256={manifest_sha256}")
    print(f"n_windows={len(entries)}")
    print(f"n_windows_implausible_calibration={n_implausible}")


if __name__ == "__main__":
    main()
