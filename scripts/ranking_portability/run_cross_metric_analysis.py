#!/usr/bin/env python3
"""POST_PHASE12_RESULT_INDEPENDENT_ANALYSIS_EXTENSION launcher.

Computes cross-metric portability (does the policy ranking under metric
M agree with the ranking under metric N, for the SAME source and load
region?) over the already-admitted, already-validated Phase-12
consolidated result. Reuses `robustbench.analysis.cross_metric`'s
statistics (which itself reuses the sealed
`robustbench.ranking_portability.analysis` primitives as a library) and
writes into a wholly separate output namespace
(`artifacts/analysis/cross_metric_extension/<contract_sha256>/`).

This script does NOT touch, re-run, or overwrite anything the sealed
Phase-12 analysis package wrote. It is frozen per
docs/CROSS_METRIC_ANALYSIS_PROTOCOL_20260903.md +
configs/analysis/cross_metric_analysis_20260903.json, committed and
pushed BEFORE this script is ever run against the real consolidated
artifact.

FAIL-CLOSED GATES:
1. Path blindness: the consolidated-artifact path is checked against
   the sealed result-blindness guard; reading the live
   artifacts/campaign_results tree requires --allow-live.
2. Canonical normalized input-hash check: the SAME `_normalize_cells_
   container` + `_canonical_sha256` the sealed package uses is applied
   to the admitted artifact's `cells`, and the result must equal the
   contract's frozen `expected_canonical_normalized_input_sha256`
   EXACTLY. On any mismatch: STOP, nothing is analyzed, exit 2.
3. Output namespace: --output-dir must not already contain files (no
   silent overwrite) and must not overlap the input path.
"""
from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Mapping, Sequence

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT / "scripts" / "ranking_portability"))

from robustbench.analysis.cross_metric import (  # noqa: E402
    CrossMetricComparisonResult,
    CrossMetricPairwiseDisagreement,
    all_metric_pairs,
    apply_bh_fdr_to_family,
    classify_pairwise_disagreement,
    compare_metrics_for_condition,
    eligible_metric_names,
)
from robustbench.ranking_portability.analysis.contract import PRIMARY_POLICIES  # noqa: E402
from robustbench.ranking_portability.analysis.result_blindness import (  # noqa: E402
    assert_not_live_campaign_path,
)
from robustbench.ranking_portability.analysis.robustness import filter_primary_only  # noqa: E402

from run_phase12_analysis import _normalize_cells_container  # noqa: E402


class GateRefusal(RuntimeError):
    """A fail-closed launch gate refused the run. Nothing was analyzed."""


def _refuse(msg: str) -> None:
    raise GateRefusal(f"REFUSING TO RUN: {msg}")


def _canonical_sha256(payload) -> str:
    blob = json.dumps(payload, sort_keys=True, default=str).encode()
    return hashlib.sha256(blob).hexdigest()


def _git_sha() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO_ROOT).decode().strip()


def _rows_for(rows: Sequence[Mapping], *, source: str, region: str) -> List[Mapping]:
    return [r for r in rows if r["source_family"] == source and r["load_region"] == region]


def _unordered_pairs(items):
    return list(itertools.combinations(sorted(items), 2))


def _correlation_record(res: CrossMetricComparisonResult, *, contract_hash: str, input_hash: str, code_sha: str) -> dict:
    return {
        "source": res.source, "region": res.region,
        "metric_a": res.metric_a, "metric_b": res.metric_b,
        "effective_policy_count": res.effective_policy_count,
        "policy_panel": list(res.policy_panel),
        "kendall_tau_b": res.kendall_tau_b,
        "kendall_ci": list(res.kendall_ci) if res.kendall_ci is not None else None,
        "spearman_rho": res.spearman_rho,
        "spearman_ci": list(res.spearman_ci) if res.spearman_ci is not None else None,
        "top1_agreement": res.top1_agreement,
        "top3_overlap": res.top3_overlap,
        "bootstrap_count": res.bootstrap_count,
        "analysis_contract_hash": contract_hash,
        "input_hash": input_hash,
        "code_sha": code_sha,
        "status": res.status,
    }


def _disagreement_record(d: CrossMetricPairwiseDisagreement, *, contract_hash: str, input_hash: str, code_sha: str, supported_after_fdr) -> dict:
    return {
        "source": d.source, "region": d.region,
        "metric_a": d.metric_a, "metric_b": d.metric_b,
        "policy_x": d.policy_x, "policy_y": d.policy_y,
        "classification": d.classification,
        "supported_after_fdr": supported_after_fdr,
        "diff_a": d.diff_a, "diff_b": d.diff_b,
        "margin_a": d.margin_a, "margin_b": d.margin_b,
        "ci_a": list(d.ci_a) if d.ci_a is not None else None,
        "ci_b": list(d.ci_b) if d.ci_b is not None else None,
        "p_a": d.p_a, "p_b": d.p_b,
        "analysis_contract_hash": contract_hash,
        "input_hash": input_hash,
        "code_sha": code_sha,
    }


def run(
    *,
    consolidated_artifact_path: Path,
    contract_path: Path,
    output_dir: Path,
    allow_live: bool,
    n_resamples: int,
    disagreements: bool,
) -> Dict[str, Any]:
    assert_not_live_campaign_path(consolidated_artifact_path, allow_live=allow_live)
    assert_not_live_campaign_path(output_dir, allow_live=False)

    if output_dir.exists() and any(output_dir.iterdir()):
        _refuse(f"output dir {output_dir} already exists and is non-empty -- refusing to overwrite.")
    if not consolidated_artifact_path.exists():
        _refuse(f"consolidated artifact not found: {consolidated_artifact_path}")
    if not contract_path.exists():
        _refuse(f"contract not found: {contract_path}")

    with open(contract_path) as f:
        contract = json.load(f)
    contract_hash = hashlib.sha256(contract_path.read_bytes()).hexdigest()

    with open(consolidated_artifact_path) as f:
        consolidated = json.load(f)
    rows_dict = _normalize_cells_container(consolidated["cells"])
    input_hash = _canonical_sha256({cid: rows_dict[cid] for cid in sorted(rows_dict)})

    expected_input_hash = contract["expected_canonical_normalized_input_sha256"]
    if input_hash != expected_input_hash:
        _refuse(
            f"canonical normalized input hash mismatch: computed={input_hash!r} "
            f"expected={expected_input_hash!r}. STOPPING -- nothing analyzed."
        )

    code_sha = _git_sha()
    rows = filter_primary_only(list(rows_dict.values()))
    metrics = list(eligible_metric_names())
    pairs = all_metric_pairs(metrics)
    sources = contract["sources"]
    regions = contract["load_regions"]

    correlation_records: List[dict] = []
    for source in sources:
        for region in regions:
            condition_rows = _rows_for(rows, source=source, region=region)
            for metric_a, metric_b in pairs:
                res = compare_metrics_for_condition(
                    condition_rows, source=source, region=region,
                    metric_a=metric_a, metric_b=metric_b,
                    all_policies=PRIMARY_POLICIES, n_resamples=n_resamples,
                )
                correlation_records.append(_correlation_record(
                    res, contract_hash=contract_hash, input_hash=input_hash, code_sha=code_sha,
                ))

    disagreement_records: List[dict] = []
    if disagreements:
        policy_pairs = _unordered_pairs(PRIMARY_POLICIES)
        for source in sources:
            for region in regions:
                condition_rows = _rows_for(rows, source=source, region=region)
                for metric_a, metric_b in pairs:
                    family: List[CrossMetricPairwiseDisagreement] = []
                    for policy_x, policy_y in policy_pairs:
                        family.append(classify_pairwise_disagreement(
                            condition_rows, source=source, region=region,
                            metric_a=metric_a, metric_b=metric_b,
                            policy_x=policy_x, policy_y=policy_y,
                            n_resamples=n_resamples,
                        ))
                    fdr_flags = apply_bh_fdr_to_family(family)
                    for d, flag in zip(family, fdr_flags):
                        disagreement_records.append(_disagreement_record(
                            d, contract_hash=contract_hash, input_hash=input_hash,
                            code_sha=code_sha, supported_after_fdr=bool(flag),
                        ))

    status_records = [
        {
            "source": r["source"], "region": r["region"],
            "metric_a": r["metric_a"], "metric_b": r["metric_b"],
            "status": r["status"], "effective_policy_count": r["effective_policy_count"],
            "analysis_contract_hash": contract_hash, "input_hash": input_hash, "code_sha": code_sha,
        }
        for r in correlation_records
    ]

    output_dir.mkdir(parents=True, exist_ok=True)

    def _write(name: str, records: List[dict]) -> Path:
        p = output_dir / name
        with open(p, "w") as f:
            json.dump({
                "contract_kind": contract["contract_kind"],
                "label": contract["label"],
                "analysis_contract_hash": contract_hash,
                "input_hash": input_hash,
                "code_sha": code_sha,
                "records": records,
            }, f, indent=2, sort_keys=True, default=str)
        return p

    written = {
        "cross_metric_correlations.json": _write("cross_metric_correlations.json", correlation_records),
        "cross_metric_topk.json": _write("cross_metric_topk.json", correlation_records),
        "cross_metric_status.json": _write("cross_metric_status.json", status_records),
    }
    if disagreements:
        written["cross_metric_pairwise_disagreements.json"] = _write(
            "cross_metric_pairwise_disagreements.json", disagreement_records,
        )

    return {
        "written": {k: str(v) for k, v in written.items()},
        "n_correlation_records": len(correlation_records),
        "n_disagreement_records": len(disagreement_records),
        "contract_hash": contract_hash,
        "input_hash": input_hash,
        "code_sha": code_sha,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--consolidated-artifact", type=Path, required=True)
    ap.add_argument("--contract", type=Path, default=REPO_ROOT / "configs/analysis/cross_metric_analysis_20260903.json")
    ap.add_argument("--output-dir", type=Path, required=True)
    ap.add_argument("--allow-live", action="store_true")
    ap.add_argument("--n-resamples", type=int, default=2000)
    ap.add_argument("--no-disagreements", action="store_true", help="skip the optional pairwise-disagreement pass")
    args = ap.parse_args()

    try:
        summary = run(
            consolidated_artifact_path=args.consolidated_artifact.resolve(),
            contract_path=args.contract.resolve(),
            output_dir=args.output_dir.resolve(),
            allow_live=args.allow_live,
            n_resamples=args.n_resamples,
            disagreements=not args.no_disagreements,
        )
    except GateRefusal as e:
        print(str(e), file=sys.stderr)
        sys.exit(2)

    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
