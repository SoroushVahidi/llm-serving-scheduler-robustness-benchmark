"""Real-engine load-calibration harness (docs/LOAD_CALIBRATION_PROTOCOL.md
§ "recalibrated against the real engine's own saturation point",
docs/REAL_SYSTEM_VALIDATION_PLAN.md's PRE_KNEE/KNEE/OVERLOAD real-engine
recalibration requirement).

This module is the HARNESS only: given a model, a workload manifest (a
list of prompts/max_tokens), a request-rate ladder, concurrency bounds,
and a repetition count, it drives `calibration_common.run_requests`
against a live vLLM server and returns per-rate-point aggregate
statistics. It does not decide what the real-engine knee point *is* --
that determination happens in a later, separate scientific task.

In THIS task it is exercised only against the tiny fabricated engineering
fixture (`engineering_fixture.py`); any measurements it produces here are
stamped ENGINEERING_CALIBRATION_SMOKE_ONLY and must never be used to set
the paper's real-engine load regions.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Sequence

from . import calibration_common as cc
from .vllm_openai_client import call_non_streaming, call_streaming, make_client

ENGINEERING_CALIBRATION_SMOKE_ONLY = True


@dataclass(frozen=True)
class RatePoint:
    concurrency: int
    requests_per_cell: int


def _build_args(*, resume: bool, stream: bool, timeout_seconds: int) -> argparse.Namespace:
    return argparse.Namespace(
        resume=resume,
        rpm_limit=10_000,  # local/allocated server, not a rate-limited external API
        stream=stream,
        fail_fast=False,
        min_output_token_ratio=0.0,
        record_output_text_preview_chars=0,
        timeout_seconds=timeout_seconds,
        max_total_requests=10_000,
        max_total_input_tokens=10_000_000,
        max_total_output_tokens=10_000_000,
        max_estimated_cost_usd=1e9,  # self-hosted: no per-token billing
    )


def run_rate_ladder(
    *,
    base_url: str,
    model: str,
    experiment_id: str,
    prompt_buckets: Sequence[str],
    max_tokens_list: Sequence[int],
    rate_ladder: Sequence[RatePoint],
    out_dir: Path,
    seed: int,
    timeout_seconds: int = 60,
    stream: bool = True,
) -> Dict[str, Any]:
    """Runs one cell per (bucket, max_tokens, rate_point.concurrency),
    `rate_point.requests_per_cell` requests each. Returns aggregated
    stats per cell via `calibration_common.aggregate_results`. Caller is
    responsible for stamping ENGINEERING_CALIBRATION_SMOKE_ONLY on any
    output derived from a non-scientific (fixture) workload manifest.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    concurrency_list = [rp.concurrency for rp in rate_ladder]
    # requests_per_cell must be uniform across a single expand_call_plan
    # call; rate points here are expected to share the same count (the
    # engineering smoke uses a small constant), so take the first.
    requests_per_cell = rate_ladder[0].requests_per_cell if rate_ladder else 0

    plan = cc.expand_call_plan(
        experiment_id=experiment_id,
        model=model,
        prompt_buckets=prompt_buckets,
        max_tokens_list=max_tokens_list,
        concurrency_list=concurrency_list,
        requests_per_cell=requests_per_cell,
        seed=seed,
    )

    args = _build_args(resume=False, stream=stream, timeout_seconds=timeout_seconds)
    client = make_client(base_url, timeout_s=float(timeout_seconds))
    try:
        cc.run_requests(
            plan,
            args,
            out_dir,
            mock=False,
            build_client_fn=lambda: client,
            call_streaming_fn=call_streaming,
            call_non_streaming_fn=call_non_streaming,
            price_per_m_input_usd=0.0,
            price_per_m_output_usd=0.0,
        )
    finally:
        client.close()

    aggregated = cc.aggregate_results(
        out_dir, price_per_m_input_usd=0.0, price_per_m_output_usd=0.0,
    )
    return {
        "engineering_calibration_smoke_only": ENGINEERING_CALIBRATION_SMOKE_ONLY,
        "requests_path": str(out_dir / "requests.jsonl"),
        "aggregated": aggregated,
    }
