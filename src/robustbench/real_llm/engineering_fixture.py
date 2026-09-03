"""Tiny, fabricated, deterministic request fixture for real-vLLM
infrastructure smoke tests (docs/REAL_SYSTEM_VALIDATION_PLAN.md
engineering preflight -- NOT the scientific validation itself).

Every request here is synthetic text with no relation to any Phase-12
workload source, window, or load-region calibration. This fixture exists
only to exercise server startup, request flow, and orchestration
plumbing before the scientific validation cases are frozen (which must
happen only after the admitted Phase-12 statistical analysis completes
and is structurally validated).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List

ENGINEERING_SMOKE_ONLY = True
NOT_FOR_PAPER_EVIDENCE = True

FIXTURE_ID = "real_vllm_engineering_smoke_v1"


@dataclass(frozen=True)
class SmokeRequest:
    request_id: str
    prompt: str
    max_tokens: int
    concurrency_group: str  # "single" or "concurrent"


def _short_prompt() -> str:
    return "Say the single word 'ready' and nothing else."


def _longer_prompt() -> str:
    # Deterministic, synthetic, repeated filler -- no scientific content,
    # no BurstGPT/Azure/Bailian text, no Phase-12 identifiers.
    filler = " ".join(f"token{i}" for i in range(200))
    return (
        "Below is a list of synthetic placeholder tokens used only to "
        "exercise a longer prefill for an infrastructure smoke test. "
        f"{filler} Now reply with the single word 'ready'."
    )


def build_engineering_fixture() -> List[SmokeRequest]:
    """Deterministic, small, fixed fixture covering:
    - a single request (short prefill, short output);
    - a longer-prefill single request;
    - a small concurrent batch (short prefill, short output).
    Runtime is intentionally tiny (short max_tokens throughout).
    """
    requests: List[SmokeRequest] = [
        SmokeRequest(
            request_id="smoke__single__short",
            prompt=_short_prompt(),
            max_tokens=8,
            concurrency_group="single",
        ),
        SmokeRequest(
            request_id="smoke__single__longer_prefill",
            prompt=_longer_prompt(),
            max_tokens=8,
            concurrency_group="single",
        ),
    ]
    for i in range(4):
        requests.append(
            SmokeRequest(
                request_id=f"smoke__concurrent__{i}",
                prompt=_short_prompt(),
                max_tokens=8,
                concurrency_group="concurrent",
            )
        )
    return requests


def fixture_manifest() -> dict:
    reqs = build_engineering_fixture()
    return {
        "fixture_id": FIXTURE_ID,
        "ENGINEERING_SMOKE_ONLY": ENGINEERING_SMOKE_ONLY,
        "NOT_FOR_PAPER_EVIDENCE": NOT_FOR_PAPER_EVIDENCE,
        "request_count": len(reqs),
        "request_ids": [r.request_id for r in reqs],
    }
