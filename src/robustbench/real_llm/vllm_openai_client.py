"""vLLM-specific call functions for reuse with
`real_llm.calibration_common.execute_one_request` /
`run_requests` (the generic, provider-agnostic measurement plumbing
docs/REAL_SYSTEM_VALIDATION_PLAN.md designates for reuse "for
measurement plumbing only").

`execute_one_request` injects `call_streaming_fn` / `call_non_streaming_fn`
as `Callable[[client, PlannedRequest, timeout_s], Dict[str, Any]]`
returning a dict with keys: text, finish_reason, prompt_tokens,
output_tokens, ttft_seconds. This module implements those two functions
against vLLM's OpenAI-compatible `/v1/completions` endpoint.
"""
from __future__ import annotations

import time
from typing import Any, Dict

import httpx

from .calibration_common import PlannedRequest


def make_client(base_url: str, timeout_s: float = 120.0) -> httpx.Client:
    return httpx.Client(base_url=base_url, timeout=timeout_s)


def call_non_streaming(client: httpx.Client, planned: PlannedRequest, timeout_s: int) -> Dict[str, Any]:
    resp = client.post(
        "/v1/completions",
        json={
            "model": planned.model,
            "prompt": planned.prompt_text,
            "max_tokens": planned.max_tokens,
            "temperature": 0.0,
        },
        timeout=timeout_s,
    )
    resp.raise_for_status()
    data = resp.json()
    choice = data["choices"][0]
    usage = data.get("usage") or {}
    return {
        "text": choice.get("text", ""),
        "finish_reason": choice.get("finish_reason"),
        "prompt_tokens": float(usage["prompt_tokens"]) if "prompt_tokens" in usage else None,
        "output_tokens": float(usage["completion_tokens"]) if "completion_tokens" in usage else None,
        "ttft_seconds": None,  # not observable in a non-streaming call
    }


def call_streaming(client: httpx.Client, planned: PlannedRequest, timeout_s: int) -> Dict[str, Any]:
    t0 = time.monotonic()
    ttft: float = None
    text_parts = []
    finish_reason = None
    prompt_tokens = None
    output_tokens = None
    with client.stream(
        "POST",
        "/v1/completions",
        json={
            "model": planned.model,
            "prompt": planned.prompt_text,
            "max_tokens": planned.max_tokens,
            "temperature": 0.0,
            "stream": True,
            "stream_options": {"include_usage": True},
        },
        timeout=timeout_s,
    ) as resp:
        resp.raise_for_status()
        for line in resp.iter_lines():
            if not line or not line.startswith("data: "):
                continue
            payload = line[len("data: "):]
            if payload.strip() == "[DONE]":
                break
            import json as _json
            chunk = _json.loads(payload)
            choices = chunk.get("choices") or []
            if choices:
                delta_text = choices[0].get("text", "")
                if delta_text and ttft is None:
                    ttft = time.monotonic() - t0
                text_parts.append(delta_text)
                fr = choices[0].get("finish_reason")
                if fr:
                    finish_reason = fr
            usage = chunk.get("usage")
            if usage:
                prompt_tokens = float(usage.get("prompt_tokens", 0))
                output_tokens = float(usage.get("completion_tokens", 0))
    return {
        "text": "".join(text_parts),
        "finish_reason": finish_reason,
        "prompt_tokens": prompt_tokens,
        "output_tokens": output_tokens,
        "ttft_seconds": ttft,
    }
