from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]


def _load_module(name: str, rel_path: str):
    path = REPO_ROOT / rel_path
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


run_validation_mod = _load_module("run_rq6_validation", "scripts/real_vllm/run_rq6_validation.py")

REAL_MANIFEST_DIR = REPO_ROOT / "artifacts/manifests/rq6_real_vllm"
REAL_VALIDATION_MANIFEST = REPO_ROOT / "configs/real_vllm/rq6_validation_manifest_v1_20260903.json"


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


# ---------------------------------------------------------------------------
# Dry-run: real manifest + real workload manifests, if present in this
# worktree; otherwise skipped (mirrors test_rq6_calibration.py's convention
# for tests that need the real, large, regenerable workload artifacts).
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not REAL_MANIFEST_DIR.exists(), reason="RQ6 workload manifests not yet built")
def test_dry_run_plan_covers_full_240_cell_range(capsys):
    for array_index in (0, 1, 119, 239):
        args = run_validation_mod.argparse.Namespace(
            manifest_dir=REAL_MANIFEST_DIR, validation_manifest=REAL_VALIDATION_MANIFEST,
            array_index=array_index, calibration_dir=None,
            out_dir=REPO_ROOT / "artifacts/real_vllm/validation/rq6",
        )
        plan = run_validation_mod.build_execution_plan(args)
        assert plan["cell"].array_index == array_index
        assert plan["region"] == "HIGH_PRESSURE"


@pytest.mark.skipif(not REAL_MANIFEST_DIR.exists(), reason="RQ6 workload manifests not yet built")
def test_dry_run_plan_out_of_range_raises():
    args = run_validation_mod.argparse.Namespace(
        manifest_dir=REAL_MANIFEST_DIR, validation_manifest=REAL_VALIDATION_MANIFEST,
        array_index=240, calibration_dir=None,
        out_dir=REPO_ROOT / "artifacts/real_vllm/validation/rq6",
    )
    with pytest.raises(ValueError, match="out of range"):
        run_validation_mod.build_execution_plan(args)


@pytest.mark.skipif(not REAL_MANIFEST_DIR.exists(), reason="RQ6 workload manifests not yet built")
def test_dry_run_cli_prints_result_blind_plan_no_real_result_values(capsys):
    argv = [
        "run_rq6_validation.py", "--array-index", "0", "--dry-run",
        "--validation-manifest", str(REAL_VALIDATION_MANIFEST),
        "--manifest-dir", str(REAL_MANIFEST_DIR),
    ]
    import sys
    old_argv = sys.argv
    sys.argv = argv
    try:
        run_validation_mod.main()
    finally:
        sys.argv = old_argv
    out = capsys.readouterr().out
    row = json.loads(out)
    assert "arrival_normalized_weighted_goodput" not in row
    assert "slo_violation_rate" not in row
    assert row["array_index"] == 0
    assert row["region"] == "HIGH_PRESSURE"


# ---------------------------------------------------------------------------
# verify_manifest_chain: wrong SHA / wrong case-selection hash rejection
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not REAL_VALIDATION_MANIFEST.exists(), reason="validation manifest not present")
def test_verify_manifest_chain_passes_on_real_manifest():
    with open(REAL_VALIDATION_MANIFEST) as f:
        manifest = json.load(f)
    run_validation_mod.verify_manifest_chain(manifest, repo_root=REPO_ROOT)  # must not raise


@pytest.mark.skipif(not REAL_VALIDATION_MANIFEST.exists(), reason="validation manifest not present")
def test_verify_manifest_chain_rejects_stale_code_sha():
    with open(REAL_VALIDATION_MANIFEST) as f:
        manifest = json.load(f)
    manifest["frozen_code_sha"] = "0" * 40
    with pytest.raises(RuntimeError, match="frozen_code_sha"):
        run_validation_mod.verify_manifest_chain(manifest, repo_root=REPO_ROOT)


@pytest.mark.skipif(not REAL_VALIDATION_MANIFEST.exists(), reason="validation manifest not present")
def test_verify_manifest_chain_rejects_wrong_case_selection_hash():
    with open(REAL_VALIDATION_MANIFEST) as f:
        manifest = json.load(f)
    manifest["case_selection"]["manifest_sha256"] = "0" * 64
    with pytest.raises(RuntimeError, match="case_selection"):
        run_validation_mod.verify_manifest_chain(manifest, repo_root=REPO_ROOT)


@pytest.mark.skipif(not REAL_VALIDATION_MANIFEST.exists(), reason="validation manifest not present")
def test_verify_manifest_chain_rejects_wrong_calibration_manifest_hash():
    with open(REAL_VALIDATION_MANIFEST) as f:
        manifest = json.load(f)
    manifest["calibration_dependency"]["calibration_manifest_sha256"] = "0" * 64
    with pytest.raises(RuntimeError, match="calibration_manifest"):
        run_validation_mod.verify_manifest_chain(manifest, repo_root=REPO_ROOT)


# ---------------------------------------------------------------------------
# Atomic write + duplicate-output refusal
# ---------------------------------------------------------------------------

def test_write_atomic_json_produces_valid_file(tmp_path):
    out_path = tmp_path / "sub" / "out.json"
    run_validation_mod._write_atomic_json(out_path, {"a": 1, "run_status": "COMPLETED"})
    assert out_path.exists()
    assert json.loads(out_path.read_text()) == {"a": 1, "run_status": "COMPLETED"}
    # no leftover temp files
    leftovers = [p for p in out_path.parent.iterdir() if p.name.startswith(".")]
    assert leftovers == []


def test_existing_result_is_completed_true_for_completed(tmp_path):
    path = tmp_path / "r.json"
    path.write_text(json.dumps({"run_status": "COMPLETED"}))
    assert run_validation_mod._existing_result_is_completed(path) is True


def test_existing_result_is_completed_false_for_failed(tmp_path):
    path = tmp_path / "r.json"
    path.write_text(json.dumps({"run_status": "FAILED_SERVER_START"}))
    assert run_validation_mod._existing_result_is_completed(path) is False


def test_existing_result_is_completed_false_for_missing(tmp_path):
    assert run_validation_mod._existing_result_is_completed(tmp_path / "nope.json") is False


def test_existing_result_is_completed_false_for_corrupt_json(tmp_path):
    path = tmp_path / "r.json"
    path.write_text("not json")
    assert run_validation_mod._existing_result_is_completed(path) is False


# ---------------------------------------------------------------------------
# aggregate_calibration_hash: reproduces the manifest's documented formula
# ---------------------------------------------------------------------------

def test_aggregate_calibration_hash_matches_shell_equivalent(tmp_path):
    d = tmp_path / "cal"
    (d / "azure_llm_2024").mkdir(parents=True)
    (d / "azure_llm_2024" / "w00.json").write_text('{"a": 1}')
    (d / "azure_llm_2024" / "w01.json").write_text('{"a": 2}')
    got = run_validation_mod.aggregate_calibration_hash(d)

    expected = subprocess.run(
        "cd cal && find . -name '*.json' | sed 's|^\\./||' | sort | xargs sha256sum | sort -k2 | sha256sum | awk '{print $1}'",
        shell=True, cwd=tmp_path, capture_output=True, text=True, check=True,
    ).stdout.strip()
    assert got == expected


def test_aggregate_calibration_hash_empty_dir_is_hash_of_empty_string(tmp_path):
    d = tmp_path / "empty_cal"
    d.mkdir()
    got = run_validation_mod.aggregate_calibration_hash(d)
    assert got == hashlib.sha256(b"").hexdigest()


# ---------------------------------------------------------------------------
# sbatch: fail-closed required env vars, syntax-valid
# ---------------------------------------------------------------------------

SBATCH_PATH = REPO_ROOT / "scripts/real_vllm/run_rq6_validation.sbatch"


def test_sbatch_syntax_valid():
    result = subprocess.run(["bash", "-n", str(SBATCH_PATH)], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


def test_sbatch_fails_closed_on_required_env_vars():
    text = SBATCH_PATH.read_text()
    for var in ("REPO", "VENV", "VALIDATION_MANIFEST_HASH", "CALIBRATION_MANIFEST_HASH"):
        assert f'{var}:?' in text or f'{{{var}:?' in text, f"{var} must fail-closed with :?"


def test_sbatch_does_not_use_modulo_port_arithmetic():
    text = SBATCH_PATH.read_text()
    assert "% 100" not in text
    assert "SLURM_ARRAY_TASK_ID % " not in text


def test_sbatch_array_range_matches_240_cells():
    text = SBATCH_PATH.read_text()
    assert "--array=0-239" in text


# ---------------------------------------------------------------------------
# Full CLI end-to-end (mocked server/network/tokenizer/calibration): happy
# path writes a COMPLETED record with the full output schema, and a second
# invocation against the same cell refuses to overwrite it without --force.
# ---------------------------------------------------------------------------

class _FakeHandle:
    base_url = "http://127.0.0.1:1"

    def stop(self, timeout_s: float = 20.0) -> int:
        return 0


class _FakeTokenizer:
    def encode(self, text, add_special_tokens=False):
        return text.split()

    def decode(self, ids):
        return " ".join(ids)


@pytest.mark.skipif(not REAL_MANIFEST_DIR.exists(), reason="RQ6 workload manifests not yet built")
def test_main_cli_end_to_end_writes_completed_record_then_refuses_overwrite(tmp_path, monkeypatch):
    units_source = None
    from robustbench.real_llm.rq6_validation import enumerate_validation_cells
    cell0 = enumerate_validation_cells(REAL_MANIFEST_DIR)[0]

    with open(REAL_VALIDATION_MANIFEST) as f:
        manifest = json.load(f)
    cal_hash = manifest["calibration_dependency"]["calibration_manifest_sha256"]

    calibration_dir = tmp_path / "calibration"
    cal_subdir = calibration_dir / cell0.source
    cal_subdir.mkdir(parents=True)
    _, _, window_entry = run_validation_mod.load_window_requests(cell0.workload_manifest_path, cell0.window_id)
    (cal_subdir / f"{cell0.window_id}.json").write_text(json.dumps({
        "source": cell0.source, "window_id": cell0.window_id, "reference_policy": "vllm_faithful",
        # A large candidate_scale so real_arrival_i = base_relative_arrival_i
        # / scale compresses the whole real frozen window's trace-shape
        # timing into well under a second -- a scale of 1.0 here would make
        # this mocked test's wall-clock dispatch span the real window's own
        # (uncompressed) arrival timing, which for some HIGH_PRESSURE
        # windows is long enough to intermittently brush the internal
        # ThreadPoolExecutor wait timeout under load. The exact scale value
        # is irrelevant to what this test checks (schema/atomicity/refusal),
        # so a large constant is used rather than a realistic calibration
        # number -- never presented as a real calibration result.
        "real_lambda_ref": 1.0, "derived_high_pressure": 100000.0, "convergence_status": "CONVERGED",
        "window_content_sha256": window_entry["content_sha256"],
        "calibration_manifest_sha256": cal_hash, "repo_sha": "irrelevant-for-this-test",
    }))

    out_dir = tmp_path / "out"

    monkeypatch.setattr(run_validation_mod, "start_vllm_server", lambda **kwargs: _FakeHandle())
    monkeypatch.setattr(run_validation_mod, "wait_for_server_ready", lambda handle, timeout_s=600.0: True)
    monkeypatch.setattr(run_validation_mod, "_load_tokenizer", lambda model: _FakeTokenizer())
    monkeypatch.setattr(
        run_validation_mod, "call_non_streaming",
        lambda client, planned, timeout_s=280, extra_body=None: {"output_tokens": planned.max_tokens, "prompt_tokens": 10},
    )
    monkeypatch.chdir(REPO_ROOT)

    argv = [
        "run_rq6_validation.py", "--array-index", "0", "--model", "fake-model",
        "--out-dir", str(out_dir), "--calibration-dir", str(calibration_dir),
        "--validation-manifest", str(REAL_VALIDATION_MANIFEST), "--manifest-dir", str(REAL_MANIFEST_DIR),
    ]
    import sys
    old_argv = sys.argv
    sys.argv = argv
    try:
        run_validation_mod.main()
    finally:
        sys.argv = old_argv

    out_path = out_dir / cell0.policy / cell0.source / f"{cell0.window_id}.json"
    assert out_path.exists()
    written = json.loads(out_path.read_text())
    assert written["run_status"] == "COMPLETED"
    assert written["stamp"] == "RQ6_REAL_VLLM_SCIENTIFIC_VALIDATION"
    assert written["offered_request_count"] == 200
    assert written["completed_request_count"] == 200
    # This test checks schema/atomicity/refusal, not real timing behavior --
    # the large candidate_scale above makes the scaled SLO slack sub-
    # millisecond, so real dispatch overhead can plausibly miss it even
    # though every mocked call succeeds; exact ANWG value/timing semantics
    # are covered by tests/test_rq6_validation.py's dedicated ANWG tests.
    assert isinstance(written["arrival_normalized_weighted_goodput"], float)
    assert 0.0 <= written["arrival_normalized_weighted_goodput"] <= 1.0
    assert written["policy"] == cell0.policy
    assert written["case_selection_manifest_sha256"] == manifest["case_selection"]["manifest_sha256"]

    # Second invocation must refuse to overwrite the COMPLETED result.
    mtime_before = out_path.stat().st_mtime_ns
    sys.argv = argv
    try:
        run_validation_mod.main()
    finally:
        sys.argv = old_argv
    assert out_path.stat().st_mtime_ns == mtime_before
