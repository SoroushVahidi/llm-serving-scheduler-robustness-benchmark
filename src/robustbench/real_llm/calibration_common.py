"""
Shared infrastructure for real-LLM API calibration harnesses.

Extracted from the first working implementation (Cohere,
scripts/run_cohere_api_calibration.py) so that Gemini/Vertex, Azure OpenAI,
Fireworks, and any future provider can reuse identical grid construction,
prompt generation, hard-cap enforcement, JSONL logging schema, aggregation,
and reproducibility metadata — producing byte-for-byte comparable output
across providers.

Provider-specific pieces (how to build a client, how to make one streaming
or non-streaming call, per-token pricing, which env var holds the API key)
are injected by each provider script via plain callables/values — this
module has no import-time dependency on any specific provider SDK.
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import platform
import socket
import subprocess
import sys
import threading
import time
from collections import deque
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from itertools import product
from pathlib import Path
from typing import Any, Callable, Dict, FrozenSet, List, Optional, Sequence

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

KNOWN_PROMPT_BUCKETS = ("short", "medium", "long")
PROMPT_BUCKET_TARGET_TOKENS = {"short": 100, "medium": 512, "long": 2048}

DEFAULT_RETRYABLE_ERROR_NAMES: FrozenSet[str] = frozenset({
    "TooManyRequestsError",
    "GatewayTimeoutError",
    "ServiceUnavailableError",
    "InternalServerError",
    "TimeoutException",
    "ReadTimeout",
    "ConnectTimeout",
    "RateLimitError",
    "APITimeoutError",
})
MAX_RETRIES_PER_REQUEST = 2
RETRY_BACKOFF_SECONDS = (1.0, 2.0)


# ---------------------------------------------------------------------------
# Deterministic prompt generation
# ---------------------------------------------------------------------------

# Generic, safe, non-copyrighted synthetic sentences about LLM serving. Reused
# across buckets; repeated/trimmed deterministically to hit a target word
# count that approximates PROMPT_BUCKET_TARGET_TOKENS.
_SENTENCE_BANK = [
    "The request scheduler assigns incoming jobs to available GPU workers.",
    "Each worker maintains a key-value cache that grows during decoding.",
    "Batching multiple requests together can improve overall throughput.",
    "A scheduling policy decides the order in which requests are served.",
    "Prefill computes the initial hidden state for the full input prompt.",
    "Decoding produces one output token at a time using the cached state.",
    "Admission control can reject requests when the system is overloaded.",
    "Latency service-level objectives constrain how long a request may wait.",
    "Preemption allows a scheduler to pause one request to serve another.",
    "Throughput and tail latency are often in tension with each other.",
    "A simulator can replay traffic traces to compare scheduling policies.",
    "Token generation speed depends on batch size and sequence length.",
    "Streaming responses let a client observe output as it is produced.",
    "Fairness across tenants is one goal of a multi-tenant serving system.",
    "Cache eviction policies determine which sequences are dropped first.",
]


def build_prompt(bucket: str, seed: int, variant_index: int) -> str:
    """Deterministically build a synthetic prompt for a bucket + variant.

    A per-request variant suffix is included so identical requests do not
    trigger provider-side prompt caching, which would understate real
    per-request cost/latency for a production-representative workload.
    """
    target_tokens = PROMPT_BUCKET_TARGET_TOKENS[bucket]
    target_words = max(8, int(target_tokens * 0.75))
    words: List[str] = []
    idx = 0
    while len(words) < target_words:
        sentence = _SENTENCE_BANK[idx % len(_SENTENCE_BANK)]
        words.extend(sentence.split())
        idx += 1
    body = " ".join(words[:target_words])
    variant_tag = f"(request variant {seed}-{bucket}-{variant_index})"
    instruction = (
        "In one short plain-text sentence, restate the main topic of the "
        "text above. Do not use lists, markdown, or code blocks."
    )
    return f"{body} {variant_tag}\n\n{instruction}"


def approx_token_count(text: str) -> int:
    """Rough word-based approximation; only used for pre-flight caps."""
    return max(1, int(len(text.split()) / 0.75))


# ---------------------------------------------------------------------------
# Proposed v2 workload: length-targeted prompts (NOT wired into any live
# script — see docs/real_llm_v2_workload_proposal.md). build_prompt() above
# asks for "one short sentence," so generated output stayed ~22-35 tokens
# regardless of max_tokens in both the Cohere and Gemini v1 pilots, never
# exercising output-length scaling. build_length_targeted_prompt() is a
# candidate replacement that instructs the model to write approximately
# `target_output_tokens` tokens of content, reusing the same deterministic,
# non-copyrighted synthetic sentence bank as build_prompt() so a v2 pilot
# keeps the same safety properties (no real user data, no scraped text).
# ---------------------------------------------------------------------------

PROPOSED_V2_TARGET_OUTPUT_TOKENS = (64, 128, 256)


def build_length_targeted_prompt(bucket: str, target_output_tokens: int, seed: int, variant_index: int) -> str:
    """Deterministically build a prompt whose instruction asks for
    approximately `target_output_tokens` tokens of output, using the same
    input-side prompt-bucket body and synthetic sentence bank as
    build_prompt(). Word-count instructions are a heuristic, not a
    guarantee — a v2 pilot should measure actual output_tokens per target
    and report the achieved-vs-target ratio, the same way this codebase
    discovered v1's gap.
    """
    target_input_tokens = PROMPT_BUCKET_TARGET_TOKENS[bucket]
    target_input_words = max(8, int(target_input_tokens * 0.75))
    words: List[str] = []
    idx = 0
    while len(words) < target_input_words:
        sentence = _SENTENCE_BANK[idx % len(_SENTENCE_BANK)]
        words.extend(sentence.split())
        idx += 1
    body = " ".join(words[:target_input_words])
    variant_tag = f"(request variant {seed}-{bucket}-{target_output_tokens}-{variant_index})"
    target_output_words = max(20, int(target_output_tokens * 0.75))
    instruction = (
        f"Using only the concepts mentioned in the text above, write a "
        f"plain-text explanation of approximately {target_output_words} "
        "words (not more than a few words short or over). Use complete "
        "sentences and paragraphs. Do not use lists, markdown, headings, "
        "or code blocks. Do not introduce any topic not mentioned above."
    )
    return f"{body} {variant_tag}\n\n{instruction}"


# ---------------------------------------------------------------------------
# Plan data structures (shared schema across all providers)
# ---------------------------------------------------------------------------

@dataclass
class PlannedRequest:
    request_id: str
    experiment_id: str
    model: str
    prompt_bucket: str
    max_tokens: int
    concurrency_level: int
    request_index: int  # index within the (bucket, max_tokens, concurrency) cell
    intended_prompt_tokens: int
    prompt_text: str = field(repr=False)
    # Set only by the v2 length-targeted grid (expand_call_plan_length_targeted);
    # None/"v1" for the original build_prompt() grid.
    target_output_tokens: Optional[int] = None
    workload_version: str = "v1"

    def to_manifest_dict(self) -> Dict[str, Any]:
        return {
            "request_id": self.request_id,
            "experiment_id": self.experiment_id,
            "model": self.model,
            "prompt_bucket": self.prompt_bucket,
            "max_tokens": self.max_tokens,
            "concurrency_level": self.concurrency_level,
            "request_index": self.request_index,
            "intended_prompt_tokens": self.intended_prompt_tokens,
            "target_output_tokens": self.target_output_tokens,
            "workload_version": self.workload_version,
        }


@dataclass
class RequestResult:
    request_id: str
    experiment_id: str
    model: str
    prompt_bucket: str
    intended_prompt_tokens: int
    actual_prompt_tokens: Optional[float]
    max_tokens: int
    concurrency_level: int
    request_index: int
    start_time_iso: str
    end_time_iso: str
    rate_limiter_wait_seconds: float
    provider_request_latency_seconds: Optional[float]
    ttft_seconds: Optional[float]
    total_wall_time_seconds: float
    output_text_length_chars: int
    output_tokens: Optional[float]
    billed_units: Optional[Dict[str, Optional[float]]]
    finish_reason: Optional[str]
    status: str  # success | error | timeout | rate_limited | skipped
    error_type: Optional[str]
    error_message: Optional[str]
    retry_count: int
    was_resumed: bool
    # v2 length-targeted workload fields (None/"v1" for the original grid).
    target_output_tokens: Optional[int] = None
    workload_version: str = "v1"
    # Short, truncated preview only (see output_text_preview_chars); the full
    # generated text is never persisted anywhere in this schema.
    output_text_preview: Optional[str] = None
    reached_target_output_range: Optional[bool] = None


REQUEST_RESULT_FIELDS = frozenset(RequestResult.__dataclass_fields__.keys())


def expand_call_plan(
    experiment_id: str,
    model: str,
    prompt_buckets: Sequence[str],
    max_tokens_list: Sequence[int],
    concurrency_list: Sequence[int],
    requests_per_cell: int,
    seed: int,
) -> List[PlannedRequest]:
    plan: List[PlannedRequest] = []
    for bucket, max_tokens, concurrency in product(
        prompt_buckets, max_tokens_list, concurrency_list
    ):
        for i in range(requests_per_cell):
            prompt_text = build_prompt(bucket, seed, i)
            request_id = f"{bucket}__mt{max_tokens}__c{concurrency}__i{i}"
            plan.append(
                PlannedRequest(
                    request_id=request_id,
                    experiment_id=experiment_id,
                    model=model,
                    prompt_bucket=bucket,
                    max_tokens=max_tokens,
                    concurrency_level=concurrency,
                    request_index=i,
                    intended_prompt_tokens=approx_token_count(prompt_text),
                    prompt_text=prompt_text,
                )
            )
    return plan


DEFAULT_MAX_TOKENS_HEADROOM_MULTIPLIER = 2.0


def expand_call_plan_length_targeted(
    experiment_id: str,
    model: str,
    prompt_buckets: Sequence[str],
    target_output_tokens_list: Sequence[int],
    concurrency_list: Sequence[int],
    requests_per_cell: int,
    seed: int,
    max_tokens_headroom_multiplier: float = DEFAULT_MAX_TOKENS_HEADROOM_MULTIPLIER,
) -> List[PlannedRequest]:
    """v2 grid: one cell per (bucket, target_output_tokens, concurrency), using
    build_length_targeted_prompt() instead of build_prompt(). `max_tokens` is
    set to `target_output_tokens * max_tokens_headroom_multiplier` so the
    model has headroom to reach the target without being truncated first —
    see docs/real_llm_v2_workload_proposal.md.
    """
    plan: List[PlannedRequest] = []
    for bucket, target_output_tokens, concurrency in product(
        prompt_buckets, target_output_tokens_list, concurrency_list
    ):
        max_tokens = int(round(target_output_tokens * max_tokens_headroom_multiplier))
        for i in range(requests_per_cell):
            prompt_text = build_length_targeted_prompt(bucket, target_output_tokens, seed, i)
            request_id = f"{bucket}__tgt{target_output_tokens}__c{concurrency}__i{i}"
            plan.append(
                PlannedRequest(
                    request_id=request_id,
                    experiment_id=experiment_id,
                    model=model,
                    prompt_bucket=bucket,
                    max_tokens=max_tokens,
                    concurrency_level=concurrency,
                    request_index=i,
                    intended_prompt_tokens=approx_token_count(prompt_text),
                    prompt_text=prompt_text,
                    target_output_tokens=target_output_tokens,
                    workload_version="v2",
                )
            )
    return plan


def estimate_cost_usd(
    total_input_tokens: float,
    total_output_tokens: float,
    price_per_m_input_usd: float,
    price_per_m_output_usd: float,
) -> float:
    return (
        (total_input_tokens / 1_000_000) * price_per_m_input_usd
        + (total_output_tokens / 1_000_000) * price_per_m_output_usd
    )


def validate_call_plan(
    plan: List[PlannedRequest],
    args: argparse.Namespace,
    *,
    price_per_m_input_usd: float,
    price_per_m_output_usd: float,
) -> List[str]:
    """Return a list of hard-cap violation messages (empty = OK).

    All checks use worst-case assumptions (every request hits max_tokens)
    so the plan is refused up front if it could ever exceed caps, not just
    on average.
    """
    violations: List[str] = []
    if len(plan) > args.max_total_requests:
        violations.append(
            f"Planned {len(plan)} requests exceeds --max-total-requests={args.max_total_requests}"
        )
    total_input = sum(r.intended_prompt_tokens for r in plan)
    total_output_worst_case = sum(r.max_tokens for r in plan)
    if total_input > args.max_total_input_tokens:
        violations.append(
            f"Planned worst-case input tokens {total_input} exceeds "
            f"--max-total-input-tokens={args.max_total_input_tokens}"
        )
    if total_output_worst_case > args.max_total_output_tokens:
        violations.append(
            f"Planned worst-case output tokens {total_output_worst_case} exceeds "
            f"--max-total-output-tokens={args.max_total_output_tokens}"
        )
    worst_case_cost = estimate_cost_usd(
        total_input, total_output_worst_case, price_per_m_input_usd, price_per_m_output_usd
    )
    if worst_case_cost > args.max_estimated_cost_usd:
        violations.append(
            f"Planned worst-case cost ${worst_case_cost:.4f} exceeds "
            f"--max-estimated-cost-usd={args.max_estimated_cost_usd}"
        )
    return violations


# ---------------------------------------------------------------------------
# Reproducibility metadata
# ---------------------------------------------------------------------------

def _run_git(root: Path, args: List[str]) -> str:
    try:
        return subprocess.run(
            ["git"] + args, cwd=root, capture_output=True, text=True, timeout=10,
        ).stdout.strip()
    except Exception:
        return ""


def collect_reproducibility_metadata(
    cfg: Dict[str, Any],
    out_dir: Path,
    *,
    root: Path,
    api_key_env_var: str,
    sdk_package_name: Optional[str],
) -> Dict[str, Any]:
    branch = _run_git(root, ["rev-parse", "--abbrev-ref", "HEAD"])
    commit = _run_git(root, ["rev-parse", "HEAD"])
    dirty = bool(_run_git(root, ["status", "--porcelain"]))
    diff_stat = _run_git(root, ["diff", "--stat"])

    diff_file = None
    if dirty:
        full_diff = _run_git(root, ["diff"])
        diff_path = out_dir / "git_diff.patch"
        diff_path.write_text(full_diff)
        diff_file = str(diff_path.name)

    sdk_version = None
    if sdk_package_name:
        try:
            import importlib.metadata as importlib_metadata
            sdk_version = importlib_metadata.version(sdk_package_name)
        except Exception:
            sdk_version = None

    meta = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "git_branch": branch or None,
        "git_commit": commit or None,
        "git_dirty": dirty,
        "git_diff_stat": diff_stat or None,
        "git_diff_file": diff_file,
        "python_version": sys.version,
        "platform": platform.platform(),
        "hostname": socket.gethostname(),
        "cwd": str(Path.cwd()),
        "sdk_package_name": sdk_package_name,
        "sdk_version": sdk_version,
        "command_line": " ".join(sys.argv),
        "env_var_presence": {
            f"{api_key_env_var}_present": bool(os.environ.get(api_key_env_var, "")),
        },
        "config": cfg,
    }
    return meta


def write_reproducibility_md(meta: Dict[str, Any], out_dir: Path) -> Path:
    lines = [
        "# Reproducibility Metadata",
        "",
        f"- Generated: {meta['generated_at_utc']}",
        f"- Git branch: `{meta['git_branch']}`",
        f"- Git commit: `{meta['git_commit']}`",
        f"- Git dirty: {meta['git_dirty']}",
    ]
    if meta.get("git_diff_file"):
        lines.append(f"- Full diff saved to: `{meta['git_diff_file']}`")
    if meta.get("git_diff_stat"):
        lines += ["", "```", meta["git_diff_stat"], "```"]
    env_presence = meta["env_var_presence"]
    env_line = ", ".join(f"{k}={v}" for k, v in env_presence.items())
    lines += [
        "",
        f"- Python version: `{meta['python_version'].splitlines()[0]}`",
        f"- Platform: `{meta['platform']}`",
        f"- Hostname: `{meta['hostname']}`",
        f"- CWD: `{meta['cwd']}`",
        f"- SDK package: `{meta.get('sdk_package_name')}` version `{meta.get('sdk_version')}`",
        f"- Command line: `{meta['command_line']}`",
        f"- Env var presence: {env_line}",
        "",
        "## Config",
        "```json",
        json.dumps(meta["config"], indent=2),
        "```",
    ]
    path = out_dir / "reproducibility.md"
    path.write_text("\n".join(lines) + "\n")
    return path


# ---------------------------------------------------------------------------
# Rate limiting and budget tracking
# ---------------------------------------------------------------------------

class RpmLimiter:
    """Blocks callers so that no more than `rpm` calls start per rolling 60s."""

    def __init__(self, rpm: int) -> None:
        self._rpm = max(1, rpm)
        self._lock = threading.Lock()
        self._timestamps: deque = deque()

    def acquire(self) -> None:
        while True:
            with self._lock:
                now = time.monotonic()
                while self._timestamps and now - self._timestamps[0] > 60.0:
                    self._timestamps.popleft()
                if len(self._timestamps) < self._rpm:
                    self._timestamps.append(now)
                    return
                sleep_for = 60.0 - (now - self._timestamps[0]) + 0.01
            time.sleep(max(0.01, sleep_for))


class BudgetTracker:
    """Thread-safe running totals used to enforce hard caps at runtime.

    Concurrent workers within a cell can call try_reserve() before any of
    them have completed, so a worst-case reservation is committed
    immediately (not just checked against completed-request totals) to
    prevent concurrent overshoot past a cap. record_actual() reconciles the
    reservation with the true usage once the request completes, so caps
    reflect real consumption for subsequent cells rather than staying
    pinned to worst-case forever.
    """

    def __init__(
        self,
        args: argparse.Namespace,
        *,
        price_per_m_input_usd: float,
        price_per_m_output_usd: float,
    ) -> None:
        self._lock = threading.Lock()
        self.max_requests = args.max_total_requests
        self.max_input_tokens = args.max_total_input_tokens
        self.max_output_tokens = args.max_total_output_tokens
        self.max_cost_usd = args.max_estimated_cost_usd
        self._price_in = price_per_m_input_usd
        self._price_out = price_per_m_output_usd
        self.dispatched = 0
        self.actual_input_tokens = 0.0
        self.actual_output_tokens = 0.0
        self._reserved_input_tokens = 0.0
        self._reserved_output_tokens = 0.0

    def try_reserve(self, planned: PlannedRequest) -> bool:
        """Reserve worst-case budget for a request. Returns False if it would
        exceed any cap (caller should mark the request skipped and stop)."""
        with self._lock:
            projected_requests = self.dispatched + 1
            projected_input = (
                self.actual_input_tokens + self._reserved_input_tokens
                + planned.intended_prompt_tokens
            )
            projected_output = (
                self.actual_output_tokens + self._reserved_output_tokens
                + planned.max_tokens
            )
            projected_cost = estimate_cost_usd(
                projected_input, projected_output, self._price_in, self._price_out
            )
            if projected_requests > self.max_requests:
                return False
            if projected_input > self.max_input_tokens:
                return False
            if projected_output > self.max_output_tokens:
                return False
            if projected_cost > self.max_cost_usd:
                return False
            self.dispatched = projected_requests
            self._reserved_input_tokens += planned.intended_prompt_tokens
            self._reserved_output_tokens += planned.max_tokens
            return True

    def record_actual(
        self,
        planned: PlannedRequest,
        input_tokens: Optional[float],
        output_tokens: Optional[float],
    ) -> None:
        """Release this request's worst-case reservation and record truth."""
        with self._lock:
            self._reserved_input_tokens -= planned.intended_prompt_tokens
            self._reserved_output_tokens -= planned.max_tokens
            self.actual_input_tokens += input_tokens or 0
            self.actual_output_tokens += output_tokens or 0


class FailFastTracker:
    """Tracks attempted/failed counts and consecutive rate-limit hits."""

    MIN_SAMPLE = 10
    ERROR_RATE_THRESHOLD = 0.10
    CONSECUTIVE_RATE_LIMIT_THRESHOLD = 3

    def __init__(self, enabled: bool) -> None:
        self.enabled = enabled
        self._lock = threading.Lock()
        self.attempted = 0
        self.failed = 0
        self._consecutive_rate_limited = 0
        self.abort_event = threading.Event()
        self.abort_reason: Optional[str] = None

    def record(self, status: str) -> None:
        if not self.enabled:
            return
        with self._lock:
            if status == "skipped":
                return
            self.attempted += 1
            if status == "rate_limited":
                self._consecutive_rate_limited += 1
            else:
                self._consecutive_rate_limited = 0
            if status in ("error", "timeout", "rate_limited"):
                self.failed += 1

            if (
                self._consecutive_rate_limited
                >= self.CONSECUTIVE_RATE_LIMIT_THRESHOLD
            ):
                self.abort_event.set()
                self.abort_reason = (
                    f"{self._consecutive_rate_limited} consecutive rate-limited "
                    "responses"
                )
                return
            if (
                self.attempted >= self.MIN_SAMPLE
                and self.failed / self.attempted > self.ERROR_RATE_THRESHOLD
            ):
                self.abort_event.set()
                self.abort_reason = (
                    f"error rate {self.failed}/{self.attempted} "
                    f"({self.failed / self.attempted:.1%}) exceeds "
                    f"{self.ERROR_RATE_THRESHOLD:.0%} threshold"
                )


# ---------------------------------------------------------------------------
# Exception classification (generic, SDK-agnostic heuristics)
# ---------------------------------------------------------------------------

def _http_status_code(exc: Exception) -> Optional[int]:
    """Best-effort HTTP status extraction across SDKs.

    Different provider SDKs name this attribute differently: Cohere's
    httpx-based errors use `.status_code` (e.g. TooManyRequestsError sets
    status_code=429); google-genai's APIError uses `.code`. Checking both
    generically avoids hardcoding a per-provider attribute name here.
    """
    for attr in ("status_code", "code"):
        val = getattr(exc, attr, None)
        if isinstance(val, int):
            return val
    return None


def classify_exception(exc: Exception, retryable_error_names: FrozenSet[str]) -> str:
    name = type(exc).__name__
    status = _http_status_code(exc)
    if name == "TooManyRequestsError" or status == 429:
        return "rate_limited"
    if name in retryable_error_names:
        return "timeout" if "Timeout" in name else "error"
    if status is not None and status >= 500:
        return "error"
    return "error"


def is_retryable(exc: Exception, retryable_error_names: FrozenSet[str]) -> bool:
    name = type(exc).__name__
    status = _http_status_code(exc)
    if status == 429 or (status is not None and status >= 500):
        return True
    return name in retryable_error_names or name == "TooManyRequestsError"


def mock_call(planned: PlannedRequest, stream: bool) -> Dict[str, Any]:
    """Generic deterministic stub shared by every provider's --mock path."""
    time.sleep(0.001)
    text = "OK mock response."
    return {
        "text": text,
        "finish_reason": "COMPLETE",
        "prompt_tokens": float(planned.intended_prompt_tokens),
        "output_tokens": float(min(planned.max_tokens, 8)),
        "ttft_seconds": 0.01 if stream else None,
    }


# ---------------------------------------------------------------------------
# Request execution (provider call functions injected)
# ---------------------------------------------------------------------------

CallFn = Callable[[Any, PlannedRequest, int], Dict[str, Any]]


def execute_one_request(
    planned: PlannedRequest,
    *,
    client: Any,
    stream: bool,
    timeout_s: int,
    mock: bool,
    rpm_limiter: RpmLimiter,
    was_resumed: bool,
    call_streaming_fn: Optional[CallFn],
    call_non_streaming_fn: Optional[CallFn],
    retryable_error_names: FrozenSet[str] = DEFAULT_RETRYABLE_ERROR_NAMES,
    mock_call_fn: Callable[[PlannedRequest, bool], Dict[str, Any]] = mock_call,
    min_output_token_ratio: float = 0.0,
    output_text_preview_chars: int = 0,
) -> RequestResult:
    retry_count = 0
    last_exc: Optional[Exception] = None
    start = datetime.now(timezone.utc)
    t_wall_start = time.monotonic()
    total_wait = 0.0

    while retry_count <= MAX_RETRIES_PER_REQUEST:
        wait_t0 = time.monotonic()
        rpm_limiter.acquire()
        total_wait += time.monotonic() - wait_t0
        t_provider_start = time.monotonic()
        try:
            if mock:
                out = mock_call_fn(planned, stream)
            elif stream:
                out = call_streaming_fn(client, planned, timeout_s)
            else:
                out = call_non_streaming_fn(client, planned, timeout_s)
            end = datetime.now(timezone.utc)
            provider_latency = time.monotonic() - t_provider_start
            wall_time = time.monotonic() - t_wall_start
            output_tokens = out["output_tokens"]
            reached_target: Optional[bool] = None
            if planned.target_output_tokens is not None and output_tokens is not None:
                reached_target = output_tokens >= min_output_token_ratio * planned.target_output_tokens
            preview: Optional[str] = None
            if output_text_preview_chars > 0 and out["text"]:
                preview = out["text"][:output_text_preview_chars]
            return RequestResult(
                request_id=planned.request_id,
                experiment_id=planned.experiment_id,
                model=planned.model,
                prompt_bucket=planned.prompt_bucket,
                intended_prompt_tokens=planned.intended_prompt_tokens,
                actual_prompt_tokens=out["prompt_tokens"],
                max_tokens=planned.max_tokens,
                concurrency_level=planned.concurrency_level,
                request_index=planned.request_index,
                start_time_iso=start.isoformat(),
                end_time_iso=end.isoformat(),
                rate_limiter_wait_seconds=round(total_wait, 4),
                provider_request_latency_seconds=round(provider_latency, 4),
                ttft_seconds=round(out["ttft_seconds"], 4) if out["ttft_seconds"] is not None else None,
                total_wall_time_seconds=round(wall_time, 4),
                output_text_length_chars=len(out["text"]),
                output_tokens=output_tokens,
                billed_units={
                    "input_tokens": out["prompt_tokens"],
                    "output_tokens": output_tokens,
                },
                finish_reason=out["finish_reason"],
                status="success",
                error_type=None,
                error_message=None,
                retry_count=retry_count,
                was_resumed=was_resumed,
                target_output_tokens=planned.target_output_tokens,
                workload_version=planned.workload_version,
                output_text_preview=preview,
                reached_target_output_range=reached_target,
            )
        except Exception as exc:  # noqa: BLE001 - classify broadly, log safely
            last_exc = exc
            if is_retryable(exc, retryable_error_names) and retry_count < MAX_RETRIES_PER_REQUEST:
                time.sleep(RETRY_BACKOFF_SECONDS[min(retry_count, len(RETRY_BACKOFF_SECONDS) - 1)])
                retry_count += 1
                continue
            break

    end = datetime.now(timezone.utc)
    wall_time = time.monotonic() - t_wall_start
    status = classify_exception(last_exc, retryable_error_names) if last_exc else "error"
    return RequestResult(
        request_id=planned.request_id,
        experiment_id=planned.experiment_id,
        model=planned.model,
        prompt_bucket=planned.prompt_bucket,
        intended_prompt_tokens=planned.intended_prompt_tokens,
        actual_prompt_tokens=None,
        max_tokens=planned.max_tokens,
        concurrency_level=planned.concurrency_level,
        request_index=planned.request_index,
        start_time_iso=start.isoformat(),
        end_time_iso=end.isoformat(),
        rate_limiter_wait_seconds=round(total_wait, 4),
        provider_request_latency_seconds=None,
        ttft_seconds=None,
        total_wall_time_seconds=round(wall_time, 4),
        output_text_length_chars=0,
        output_tokens=None,
        billed_units=None,
        finish_reason=None,
        status=status,
        error_type=type(last_exc).__name__ if last_exc else "UnknownError",
        error_message=str(last_exc)[:500] if last_exc else None,
        retry_count=retry_count,
        was_resumed=was_resumed,
        target_output_tokens=planned.target_output_tokens,
        workload_version=planned.workload_version,
        output_text_preview=None,
        reached_target_output_range=None,
    )


def make_skipped_result(planned: PlannedRequest, reason: str) -> RequestResult:
    now = datetime.now(timezone.utc).isoformat()
    return RequestResult(
        request_id=planned.request_id,
        experiment_id=planned.experiment_id,
        model=planned.model,
        prompt_bucket=planned.prompt_bucket,
        intended_prompt_tokens=planned.intended_prompt_tokens,
        actual_prompt_tokens=None,
        max_tokens=planned.max_tokens,
        concurrency_level=planned.concurrency_level,
        request_index=planned.request_index,
        start_time_iso=now,
        end_time_iso=now,
        rate_limiter_wait_seconds=0.0,
        provider_request_latency_seconds=None,
        ttft_seconds=None,
        total_wall_time_seconds=0.0,
        output_text_length_chars=0,
        output_tokens=None,
        billed_units=None,
        finish_reason=None,
        status="skipped",
        error_type=None,
        error_message=reason[:500],
        retry_count=0,
        was_resumed=False,
        target_output_tokens=planned.target_output_tokens,
        workload_version=planned.workload_version,
        output_text_preview=None,
        reached_target_output_range=None,
    )


# ---------------------------------------------------------------------------
# JSONL writer (thread-safe, append-and-flush)
# ---------------------------------------------------------------------------

class JsonlWriter:
    def __init__(self, path: Path):
        self._path = path
        self._lock = threading.Lock()
        self._fh = open(path, "a")

    def write(self, result: RequestResult) -> None:
        with self._lock:
            self._fh.write(json.dumps(asdict(result)) + "\n")
            self._fh.flush()
            os.fsync(self._fh.fileno())

    def close(self) -> None:
        self._fh.close()


def load_completed_request_ids(requests_jsonl: Path) -> Dict[str, dict]:
    """Return {request_id: last record} for requests already logged."""
    records: Dict[str, dict] = {}
    if not requests_jsonl.exists():
        return records
    with open(requests_jsonl) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            records[row["request_id"]] = row
    return records


# ---------------------------------------------------------------------------
# Live/mock run driver
# ---------------------------------------------------------------------------

def run_requests(
    plan: List[PlannedRequest],
    args: argparse.Namespace,
    out_dir: Path,
    *,
    mock: bool,
    build_client_fn: Optional[Callable[[], Any]],
    call_streaming_fn: Optional[CallFn],
    call_non_streaming_fn: Optional[CallFn],
    price_per_m_input_usd: float,
    price_per_m_output_usd: float,
    retryable_error_names: FrozenSet[str] = DEFAULT_RETRYABLE_ERROR_NAMES,
    mock_call_fn: Callable[[PlannedRequest, bool], Dict[str, Any]] = mock_call,
) -> None:
    import concurrent.futures

    requests_path = out_dir / "requests.jsonl"
    already_done: Dict[str, dict] = {}
    if args.resume:
        already_done = load_completed_request_ids(requests_path)
        logging.info(
            "Resume: found %d prior records (%d successful) in %s",
            len(already_done),
            sum(1 for r in already_done.values() if r.get("status") == "success"),
            requests_path,
        )

    writer = JsonlWriter(requests_path)
    rpm_limit = getattr(args, "rpm_limit", 60)
    stream = getattr(args, "stream", False)
    fail_fast_enabled = getattr(args, "fail_fast", False)
    min_output_token_ratio = getattr(args, "min_output_token_ratio", 0.0)
    output_text_preview_chars = getattr(args, "record_output_text_preview_chars", 0)
    rpm_limiter = RpmLimiter(rpm_limit)
    budget = BudgetTracker(
        args,
        price_per_m_input_usd=price_per_m_input_usd,
        price_per_m_output_usd=price_per_m_output_usd,
    )
    fail_fast = FailFastTracker(fail_fast_enabled)

    # Seed budget tracker with already-successful actual usage so resumed
    # runs respect the original caps cumulatively.
    for row in already_done.values():
        if row.get("status") == "success":
            budget.dispatched += 1
            budget.actual_input_tokens += row.get("actual_prompt_tokens") or 0
            budget.actual_output_tokens += row.get("output_tokens") or 0

    client = None
    if not mock and build_client_fn is not None:
        client = build_client_fn()

    # Group plan by cell, preserving plan order (bucket, max_tokens, concurrency).
    cells: Dict[tuple, List[PlannedRequest]] = {}
    for p in plan:
        key = (p.prompt_bucket, p.max_tokens, p.concurrency_level)
        cells.setdefault(key, []).append(p)

    for cell_key, cell_requests in cells.items():
        if fail_fast.abort_event.is_set():
            for planned in cell_requests:
                if planned.request_id not in already_done:
                    writer.write(make_skipped_result(planned, f"aborted: {fail_fast.abort_reason}"))
            continue

        to_run = [p for p in cell_requests if not (
            args.resume and already_done.get(p.request_id, {}).get("status") == "success"
        )]
        if not to_run:
            continue

        concurrency = cell_key[2]
        logging.info(
            "Cell bucket=%s max_tokens=%d concurrency=%d: dispatching %d requests",
            cell_key[0], cell_key[1], concurrency, len(to_run),
        )

        def _run_one(planned: PlannedRequest) -> RequestResult:
            if fail_fast.abort_event.is_set():
                return make_skipped_result(planned, f"aborted: {fail_fast.abort_reason}")
            if not budget.try_reserve(planned):
                return make_skipped_result(planned, "hard cap reached")
            was_resumed = planned.request_id in already_done
            result = execute_one_request(
                planned,
                client=client,
                stream=stream,
                timeout_s=args.timeout_seconds,
                mock=mock,
                rpm_limiter=rpm_limiter,
                was_resumed=was_resumed,
                call_streaming_fn=call_streaming_fn,
                call_non_streaming_fn=call_non_streaming_fn,
                retryable_error_names=retryable_error_names,
                mock_call_fn=mock_call_fn,
                min_output_token_ratio=min_output_token_ratio,
                output_text_preview_chars=output_text_preview_chars,
            )
            budget.record_actual(planned, result.actual_prompt_tokens, result.output_tokens)
            return result

        with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as pool:
            futures = [pool.submit(_run_one, p) for p in to_run]
            for fut in concurrent.futures.as_completed(futures):
                result = fut.result()
                writer.write(result)
                fail_fast.record(result.status)
                logging.info(
                    "%s status=%s ttft=%s provider_latency=%s rpm_wait=%s",
                    result.request_id, result.status,
                    result.ttft_seconds, result.provider_request_latency_seconds,
                    result.rate_limiter_wait_seconds,
                )

    writer.close()
    if fail_fast.abort_event.is_set():
        logging.warning("Fail-fast triggered: %s", fail_fast.abort_reason)


# ---------------------------------------------------------------------------
# Aggregation
# ---------------------------------------------------------------------------

def _percentile(values: List[float], p: float) -> Optional[float]:
    if not values:
        return None
    s = sorted(values)
    k = (len(s) - 1) * p
    f = int(k)
    c = min(f + 1, len(s) - 1)
    if f == c:
        return s[f]
    return s[f] + (s[c] - s[f]) * (k - f)


def _stats_block(latencies: List[float], ttfts: List[float]) -> Dict[str, Optional[float]]:
    return {
        "count": len(latencies),
        "mean_latency_s": sum(latencies) / len(latencies) if latencies else None,
        "p50_latency_s": _percentile(latencies, 0.50),
        "p95_latency_s": _percentile(latencies, 0.95),
        "p99_latency_s": _percentile(latencies, 0.99),
        "mean_ttft_s": sum(ttfts) / len(ttfts) if ttfts else None,
        "p50_ttft_s": _percentile(ttfts, 0.50),
        "p95_ttft_s": _percentile(ttfts, 0.95),
        "p99_ttft_s": _percentile(ttfts, 0.99),
    }


def aggregate_results(
    out_dir: Path,
    *,
    price_per_m_input_usd: float,
    price_per_m_output_usd: float,
) -> Dict[str, Any]:
    import pandas as pd

    requests_path = out_dir / "requests.jsonl"
    rows = list(load_completed_request_ids(requests_path).values())

    status_counts: Dict[str, int] = {}
    for row in rows:
        status_counts[row["status"]] = status_counts.get(row["status"], 0) + 1

    successes = [r for r in rows if r["status"] == "success"]
    latencies = [
        r["provider_request_latency_seconds"] for r in successes
        if r.get("provider_request_latency_seconds") is not None
    ]
    ttfts = [r["ttft_seconds"] for r in successes if r.get("ttft_seconds") is not None]
    waits = [r["rate_limiter_wait_seconds"] for r in rows if r.get("rate_limiter_wait_seconds") is not None]
    output_tokens = [r["output_tokens"] for r in successes if r.get("output_tokens")]
    total_input_tokens = sum(r.get("actual_prompt_tokens") or 0 for r in successes)
    total_output_tokens = sum(r.get("output_tokens") or 0 for r in successes)
    estimated_cost = estimate_cost_usd(
        total_input_tokens, total_output_tokens, price_per_m_input_usd, price_per_m_output_usd
    )

    tokens_per_sec = [
        r["output_tokens"] / r["provider_request_latency_seconds"]
        for r in successes
        if r.get("output_tokens") and r.get("provider_request_latency_seconds")
    ]

    reached_flags = [
        r["reached_target_output_range"] for r in successes
        if r.get("reached_target_output_range") is not None
    ]

    overall = {
        "total_records": len(rows),
        "status_counts": status_counts,
        "mean_output_tokens": (sum(output_tokens) / len(output_tokens)) if output_tokens else None,
        "mean_tokens_per_sec": (sum(tokens_per_sec) / len(tokens_per_sec)) if tokens_per_sec else None,
        "total_billed_input_tokens": total_input_tokens,
        "total_billed_output_tokens": total_output_tokens,
        "estimated_cost_usd": round(estimated_cost, 6),
        "n_requests_with_rate_limiter_wait": sum(1 for w in waits if w > 0),
        "total_rate_limiter_wait_seconds": round(sum(waits), 4) if waits else 0.0,
        "max_rate_limiter_wait_seconds": round(max(waits), 4) if waits else 0.0,
        "frac_reached_target_output_range": (
            sum(reached_flags) / len(reached_flags) if reached_flags else None
        ),
        **_stats_block(latencies, ttfts),
    }

    df = pd.DataFrame(rows) if rows else pd.DataFrame()

    def _group_agg(group_cols: List[str]) -> "pd.DataFrame":
        if df.empty:
            return pd.DataFrame()
        records = []
        for keys, sub in df.groupby(group_cols):
            keys = keys if isinstance(keys, tuple) else (keys,)
            sub_success = sub[sub["status"] == "success"]
            lat = sub_success["provider_request_latency_seconds"].dropna().tolist()
            ttft = sub_success["ttft_seconds"].dropna().tolist()
            rec = dict(zip(group_cols, keys))
            rec.update({
                "n_total": len(sub),
                "n_success": len(sub_success),
                "n_failed": int((sub["status"].isin(["error", "timeout", "rate_limited"])).sum()),
                "n_skipped": int((sub["status"] == "skipped").sum()),
                **_stats_block(lat, ttft),
            })
            records.append(rec)
        return pd.DataFrame(records)

    by_cell = _group_agg(["prompt_bucket", "max_tokens", "concurrency_level"])
    by_concurrency = _group_agg(["concurrency_level"])
    by_bucket = _group_agg(["prompt_bucket"])

    by_cell.to_csv(out_dir / "aggregate_by_cell.csv", index=False)
    by_concurrency.to_csv(out_dir / "aggregate_by_concurrency.csv", index=False)
    by_bucket.to_csv(out_dir / "aggregate_by_prompt_bucket.csv", index=False)

    # v2-only: achieved-vs-target output length, one row per distinct
    # target_output_tokens value (empty for v1 runs, where this field is
    # always None on every row).
    by_target_records: List[Dict[str, Any]] = []
    if not df.empty and "target_output_tokens" in df.columns:
        sub = df[df["target_output_tokens"].notna()]
        for target_raw, g in sub.groupby("target_output_tokens"):
            target = float(target_raw)
            g_success = g[g["status"] == "success"]
            out_toks = [float(v) for v in g_success["output_tokens"].dropna().tolist()]
            reached = [bool(v) for v in g_success["reached_target_output_range"].dropna().tolist()]
            by_target_records.append({
                "target_output_tokens": int(target),
                "n_total": int(len(g)),
                "n_success": int(len(g_success)),
                "mean_output_tokens": (sum(out_toks) / len(out_toks)) if out_toks else None,
                "p50_output_tokens": _percentile(out_toks, 0.50),
                "mean_output_token_ratio": (
                    sum(ot / target for ot in out_toks) / len(out_toks) if out_toks else None
                ),
                "frac_reached_target_range": (sum(reached) / len(reached)) if reached else None,
            })
    by_target_records.sort(key=lambda r: r["target_output_tokens"])
    pd.DataFrame(by_target_records).to_csv(
        out_dir / "aggregate_by_target_output_tokens.csv", index=False
    )
    overall["by_target_output_tokens"] = by_target_records

    errors = [r for r in rows if r["status"] in ("error", "timeout", "rate_limited")]
    with open(out_dir / "errors.jsonl", "w") as f:
        for row in errors:
            f.write(json.dumps(row) + "\n")

    return overall


# ---------------------------------------------------------------------------
# Legacy log reprocessing
# ---------------------------------------------------------------------------
#
# Logs written before the rate_limiter_wait_seconds / provider_request_latency
# _seconds split (see execute_one_request above) only recorded a single
# elapsed_seconds/total_latency_seconds field that could include time spent
# blocked in the local RPM limiter. That split cannot be recovered exactly
# after the fact — the raw records don't say how much of the elapsed time was
# limiter wait vs. provider response. What CAN be done without rerunning any
# API calls: (1) ttft_seconds was always measured from inside the provider
# call itself, so it was never polluted by limiter wait and remains fully
# reliable in old logs; (2) requests whose recorded latency is far larger
# than their ttft_seconds are very likely RPM-wait-polluted (a request that
# streamed its first token in ~0.2s does not organically take 53s to finish
# ~30 more tokens), so they can be heuristically flagged and excluded to
# produce a "corrected" percentile view alongside the untouched raw one.

LEGACY_LATENCY_FIELDS = ("provider_request_latency_seconds", "total_latency_seconds")


def legacy_latency_seconds(row: Dict[str, Any]) -> Optional[float]:
    for field_name in LEGACY_LATENCY_FIELDS:
        if row.get(field_name) is not None:
            return row[field_name]
    return None


def flag_likely_rate_limiter_wait_outliers(
    rows: List[Dict[str, Any]],
    *,
    min_ttft_gap_seconds: float = 5.0,
    min_absolute_latency_seconds: float = 10.0,
) -> List[str]:
    """Heuristically flag successful requests whose recorded latency is
    implausibly larger than their TTFT, suggesting most of the recorded time
    was local RPM-limiter wait rather than provider response time.

    A request is flagged if `latency - ttft > min_ttft_gap_seconds` (when
    ttft is known), or if ttft is unknown (e.g. non-streaming) and latency
    alone exceeds `min_absolute_latency_seconds`. This is a heuristic, not an
    exact recovery: it cannot distinguish "genuinely slow provider response"
    from "RPM wait" for a request with no ttft. It is intended for legacy
    logs that predate rate_limiter_wait_seconds.
    """
    flagged: List[str] = []
    for row in rows:
        if row.get("status") != "success":
            continue
        latency = legacy_latency_seconds(row)
        if latency is None:
            continue
        ttft = row.get("ttft_seconds")
        if ttft is not None:
            if latency - ttft > min_ttft_gap_seconds:
                flagged.append(row["request_id"])
        elif latency > min_absolute_latency_seconds:
            flagged.append(row["request_id"])
    return flagged


def reprocess_legacy_summary(
    requests_path: Path,
    *,
    min_ttft_gap_seconds: float = 5.0,
    min_absolute_latency_seconds: float = 10.0,
) -> Dict[str, Any]:
    """Regenerate a corrected-vs-raw latency summary from an existing
    requests.jsonl written before the rate_limiter_wait_seconds field
    existed. Makes no API calls; reads only what's already on disk.

    Returns raw stats (all successful requests, exactly what summary.json
    already reported), corrected stats (excluding heuristically flagged
    likely-RPM-wait outliers), the flagged request_ids, and a caveat
    explaining what is and is not recoverable from these fields.
    """
    rows = list(load_completed_request_ids(requests_path).values())
    successes = [r for r in rows if r.get("status") == "success"]
    has_new_schema = any(r.get("rate_limiter_wait_seconds") is not None for r in rows)

    flagged_ids = set(
        flag_likely_rate_limiter_wait_outliers(
            rows,
            min_ttft_gap_seconds=min_ttft_gap_seconds,
            min_absolute_latency_seconds=min_absolute_latency_seconds,
        )
    )
    clean = [r for r in successes if r["request_id"] not in flagged_ids]

    raw_latencies = [legacy_latency_seconds(r) for r in successes]
    raw_latencies = [v for v in raw_latencies if v is not None]
    corrected_latencies = [legacy_latency_seconds(r) for r in clean]
    corrected_latencies = [v for v in corrected_latencies if v is not None]
    ttfts = [r["ttft_seconds"] for r in successes if r.get("ttft_seconds") is not None]

    return {
        "requests_path": str(requests_path),
        "n_total_records": len(rows),
        "n_success": len(successes),
        "n_flagged_likely_rate_limiter_wait": len(flagged_ids),
        "flagged_request_ids": sorted(flagged_ids),
        "has_rate_limiter_wait_field": has_new_schema,
        "raw_stats": _stats_block(raw_latencies, ttfts),
        "corrected_stats_excluding_flagged": _stats_block(corrected_latencies, ttfts),
        "caveat": (
            "This log predates the rate_limiter_wait_seconds/"
            "provider_request_latency_seconds split, so the exact amount of "
            "local RPM-limiter wait inside each request's recorded latency "
            "cannot be recovered. 'corrected_stats_excluding_flagged' drops "
            f"requests where latency exceeded ttft by more than "
            f"{min_ttft_gap_seconds}s (or exceeded "
            f"{min_absolute_latency_seconds}s absolute for non-streaming "
            "requests with no ttft) as likely-RPM-wait-polluted, rather than "
            "correcting their value. ttft_seconds was always measured from "
            "inside the provider call and is unaffected by this artifact in "
            "either raw or corrected form. p50 latency is typically also "
            "reliable since the artifact affects a small number of outliers "
            "concentrated at the tail (compare raw vs. corrected p50 below "
            "to confirm for this specific log)."
        ) if not has_new_schema else (
            "This log already has rate_limiter_wait_seconds/"
            "provider_request_latency_seconds recorded per-request; use "
            "aggregate_results()/summary.json directly rather than this "
            "heuristic reprocessing path."
        ),
    }


def write_legacy_reprocessed_summary(out_dir: Path, reprocessed: Dict[str, Any]) -> None:
    (out_dir / "summary_corrected.json").write_text(json.dumps(reprocessed, indent=2))

    def _fmt_stats(stats: Dict[str, Optional[float]], prefix: str) -> List[str]:
        return [
            f"- {prefix} count: {stats.get('count')}",
            f"- {prefix} mean / p50 / p95 / p99 latency (s): "
            f"{stats.get('mean_latency_s')} / {stats.get('p50_latency_s')} / "
            f"{stats.get('p95_latency_s')} / {stats.get('p99_latency_s')}",
            f"- {prefix} mean / p50 / p95 / p99 TTFT (s): "
            f"{stats.get('mean_ttft_s')} / {stats.get('p50_ttft_s')} / "
            f"{stats.get('p95_ttft_s')} / {stats.get('p99_ttft_s')}",
        ]

    lines = [
        "# Corrected Summary (reprocessed from existing requests.jsonl)",
        "",
        f"Source: `{reprocessed['requests_path']}`",
        f"Has native rate_limiter_wait_seconds field: {reprocessed['has_rate_limiter_wait_field']}",
        "",
        "## Caveat",
        "",
        reprocessed["caveat"],
        "",
        "## Raw stats (all successful requests, unmodified)",
        *_fmt_stats(reprocessed["raw_stats"], "raw"),
        "",
        "## Corrected stats (flagged likely-RPM-wait outliers excluded)",
        *_fmt_stats(reprocessed["corrected_stats_excluding_flagged"], "corrected"),
        "",
        f"## Flagged requests ({reprocessed['n_flagged_likely_rate_limiter_wait']} of "
        f"{reprocessed['n_success']} successful)",
        "```",
        *(reprocessed["flagged_request_ids"] or ["(none)"]),
        "```",
    ]
    (out_dir / "summary_corrected.md").write_text("\n".join(lines) + "\n")


def write_summary(
    out_dir: Path,
    overall: Dict[str, Any],
    cfg: Dict[str, Any],
    *,
    provider_display_name: str,
) -> None:
    (out_dir / "summary.json").write_text(json.dumps(overall, indent=2))

    lines = [
        f"# {provider_display_name} API Calibration — Summary",
        "",
        f"**Model:** `{cfg.get('model')}`",
        f"**Generated:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}",
        "",
        "## Status counts",
        "```json",
        json.dumps(overall.get("status_counts", {}), indent=2),
        "```",
        "",
        "## Latency / TTFT (successful requests)",
        "Latency here is `provider_request_latency_seconds` — timed from after",
        "the local RPM limiter released the request, so it excludes local",
        "rate-limiter wait. See 'Local rate-limiter wait' below for that.",
        f"- count: {overall.get('count')}",
        f"- mean latency (s): {overall.get('mean_latency_s')}",
        f"- p50 / p95 / p99 latency (s): {overall.get('p50_latency_s')} / "
        f"{overall.get('p95_latency_s')} / {overall.get('p99_latency_s')}",
        f"- mean TTFT (s): {overall.get('mean_ttft_s')}",
        f"- p50 / p95 / p99 TTFT (s): {overall.get('p50_ttft_s')} / "
        f"{overall.get('p95_ttft_s')} / {overall.get('p99_ttft_s')}",
        "",
        "## Local rate-limiter wait (all dispatched requests)",
        f"- requests with nonzero wait: {overall.get('n_requests_with_rate_limiter_wait')}",
        f"- total wait (s): {overall.get('total_rate_limiter_wait_seconds')}",
        f"- max wait (s): {overall.get('max_rate_limiter_wait_seconds')}",
        "",
        "## Throughput / cost",
        f"- mean output tokens: {overall.get('mean_output_tokens')}",
        f"- mean tokens/sec (provider latency basis): {overall.get('mean_tokens_per_sec')}",
        f"- total billed input tokens: {overall.get('total_billed_input_tokens')}",
        f"- total billed output tokens: {overall.get('total_billed_output_tokens')}",
        f"- estimated cost (USD, approximate pricing): ${overall.get('estimated_cost_usd')}",
        "",
    ]

    by_target = overall.get("by_target_output_tokens") or []
    if cfg.get("workload_version") == "v2" and by_target:
        lines += [
            "## Output length vs. target (v2 length-targeted workload)",
            f"- overall fraction reaching target range (>= "
            f"{cfg.get('min_output_token_ratio')} x target): "
            f"{overall.get('frac_reached_target_output_range')}",
            "",
            "| target_output_tokens | n_success | mean_output_tokens | "
            "p50_output_tokens | mean_output_token_ratio | frac_reached_target_range |",
            "|---|---|---|---|---|---|",
        ]
        for rec in by_target:
            lines.append(
                f"| {rec['target_output_tokens']} | {rec['n_success']} | "
                f"{rec['mean_output_tokens']} | {rec['p50_output_tokens']} | "
                f"{rec['mean_output_token_ratio']} | {rec['frac_reached_target_range']} |"
            )
        lines.append("")

    lines += [
        "See `aggregate_by_cell.csv`, `aggregate_by_concurrency.csv`, "
        "`aggregate_by_prompt_bucket.csv` for breakdowns, "
        "`aggregate_by_target_output_tokens.csv` for v2 achieved-vs-target "
        "output length, and `errors.jsonl` for failure detail.",
    ]
    (out_dir / "summary.md").write_text("\n".join(lines) + "\n")


# ---------------------------------------------------------------------------
# CLI helpers
# ---------------------------------------------------------------------------

def csv_str_list(raw: str) -> List[str]:
    return [x.strip() for x in raw.split(",") if x.strip()]


def csv_int_list(raw: str) -> List[int]:
    return [int(x.strip()) for x in raw.split(",") if x.strip()]


def add_common_arguments(
    parser: argparse.ArgumentParser,
    *,
    default_model: str,
    default_max_total_requests: int = 180,
    default_max_total_input_tokens: int = 250_000,
    default_max_total_output_tokens: int = 50_000,
    default_max_estimated_cost_usd: float = 5.0,
) -> argparse.ArgumentParser:
    """Add the flags shared by every provider's calibration script.

    Provider scripts may add extra flags on top (e.g. Cohere adds
    --rpm-limit, --fail-fast, --stream/--no-stream).
    """
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--allow-live-api", action="store_true")
    parser.add_argument(
        "--mock", "--mock-provider", dest="mock", action="store_true",
        help="Use a local stub instead of the real API (tests only).",
    )
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--model", default=default_model)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--prompt-buckets", type=csv_str_list, default=list(KNOWN_PROMPT_BUCKETS))
    parser.add_argument("--max-tokens-list", type=csv_int_list, default=[64, 128, 256])
    parser.add_argument("--concurrency-list", type=csv_int_list, default=[1, 2, 4, 8])
    parser.add_argument("--requests-per-cell", type=int, default=5)
    parser.add_argument("--timeout-seconds", type=int, default=90)
    parser.add_argument("--max-total-requests", type=int, default=default_max_total_requests)
    parser.add_argument("--max-total-input-tokens", type=int, default=default_max_total_input_tokens)
    parser.add_argument("--max-total-output-tokens", type=int, default=default_max_total_output_tokens)
    parser.add_argument("--max-estimated-cost-usd", type=float, default=default_max_estimated_cost_usd)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--verbose", action="store_true")
    return parser


def repo_path(root: Path, raw: str) -> Path:
    p = Path(raw)
    return p if p.is_absolute() else root / p


# ---------------------------------------------------------------------------
# Shared main() orchestration
# ---------------------------------------------------------------------------

def run_calibration_main(
    args: argparse.Namespace,
    *,
    root: Path,
    provider_display_name: str,
    api_key_env_var: str,
    sdk_package_name: Optional[str],
    price_per_m_input_usd: float,
    price_per_m_output_usd: float,
    live_implemented: bool,
    build_client_fn: Optional[Callable[[], Any]] = None,
    call_streaming_fn: Optional[CallFn] = None,
    call_non_streaming_fn: Optional[CallFn] = None,
    retryable_error_names: FrozenSet[str] = DEFAULT_RETRYABLE_ERROR_NAMES,
    mock_call_fn: Callable[[PlannedRequest, bool], Dict[str, Any]] = mock_call,
    extra_cfg: Optional[Dict[str, Any]] = None,
) -> int:
    """Shared CLI orchestration used by every provider's main().

    Returns the process exit code. Exit codes are stable across providers:
    0 ok, 2 bad CLI usage, 3 output-dir already has results (no --resume),
    4 hard-cap violation, 5 missing API key in live mode, 6 live mode not
    yet implemented for this provider.
    """
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )

    unknown_buckets = set(args.prompt_buckets) - set(KNOWN_PROMPT_BUCKETS)
    if unknown_buckets:
        print(
            f"ERROR: unknown prompt buckets: {sorted(unknown_buckets)}. "
            f"Known: {KNOWN_PROMPT_BUCKETS}", file=sys.stderr,
        )
        return 2

    if not args.dry_run and not args.allow_live_api:
        print(
            "ERROR: specify --dry-run or --allow-live-api.\n"
            "Run with --dry-run first to see the planned request grid.",
            file=sys.stderr,
        )
        return 2

    out_dir = repo_path(root, args.output_dir)
    requests_path = out_dir / "requests.jsonl"
    if out_dir.exists() and requests_path.exists() and requests_path.stat().st_size > 0 and not args.resume:
        print(
            f"ERROR: output dir {out_dir} already has a non-empty requests.jsonl.\n"
            "Pass --resume to continue an existing run, or choose a new --output-dir.",
            file=sys.stderr,
        )
        return 3
    out_dir.mkdir(parents=True, exist_ok=True)

    workload_version = getattr(args, "workload_version", "v1")
    target_output_tokens_list = getattr(args, "target_output_tokens_list", None)
    if workload_version == "v2" and not target_output_tokens_list:
        print(
            "ERROR: --workload-version v2 requires --target-output-tokens-list "
            "(e.g. 64,128,256).", file=sys.stderr,
        )
        return 2

    experiment_id = out_dir.name
    if workload_version == "v2":
        plan = expand_call_plan_length_targeted(
            experiment_id=experiment_id,
            model=args.model,
            prompt_buckets=args.prompt_buckets,
            target_output_tokens_list=target_output_tokens_list,
            concurrency_list=args.concurrency_list,
            requests_per_cell=args.requests_per_cell,
            seed=args.seed,
        )
    else:
        plan = expand_call_plan(
            experiment_id=experiment_id,
            model=args.model,
            prompt_buckets=args.prompt_buckets,
            max_tokens_list=args.max_tokens_list,
            concurrency_list=args.concurrency_list,
            requests_per_cell=args.requests_per_cell,
            seed=args.seed,
        )

    violations = validate_call_plan(
        plan, args,
        price_per_m_input_usd=price_per_m_input_usd,
        price_per_m_output_usd=price_per_m_output_usd,
    )
    if violations:
        print("HARD CAP VIOLATIONS — refusing to proceed:", file=sys.stderr)
        for v in violations:
            print(f"  {v}", file=sys.stderr)
        return 4

    cfg = {
        "provider": provider_display_name,
        "experiment_id": experiment_id,
        "model": args.model,
        "seed": args.seed,
        "prompt_buckets": args.prompt_buckets,
        "max_tokens_list": args.max_tokens_list,
        "concurrency_list": args.concurrency_list,
        "requests_per_cell": args.requests_per_cell,
        "timeout_seconds": args.timeout_seconds,
        "max_total_requests": args.max_total_requests,
        "max_total_input_tokens": args.max_total_input_tokens,
        "max_total_output_tokens": args.max_total_output_tokens,
        "max_estimated_cost_usd": args.max_estimated_cost_usd,
        "resume": args.resume,
        "mock": args.mock,
        "mode": "live" if args.allow_live_api else "dry_run",
        "workload_version": workload_version,
    }
    if hasattr(args, "rpm_limit"):
        cfg["rpm_limit"] = args.rpm_limit
    if hasattr(args, "fail_fast"):
        cfg["fail_fast"] = args.fail_fast
    if hasattr(args, "stream"):
        cfg["stream"] = args.stream
    if workload_version == "v2":
        cfg["target_output_tokens_list"] = target_output_tokens_list
        cfg["min_output_token_ratio"] = getattr(args, "min_output_token_ratio", 0.0)
        cfg["record_output_text_preview_chars"] = getattr(args, "record_output_text_preview_chars", 0)
    if extra_cfg:
        cfg.update(extra_cfg)

    (out_dir / "run_config.json").write_text(json.dumps(cfg, indent=2))
    repro_meta = collect_reproducibility_metadata(
        cfg, out_dir, root=root,
        api_key_env_var=api_key_env_var, sdk_package_name=sdk_package_name,
    )
    (out_dir / "manifest.json").write_text(json.dumps({
        **repro_meta,
        "planned_requests": len(plan),
        "cells": sorted({(p.prompt_bucket, p.max_tokens, p.concurrency_level) for p in plan}),
        "requests_preview": [p.to_manifest_dict() for p in plan[:5]],
    }, indent=2))
    write_reproducibility_md(repro_meta, out_dir)

    total_input = sum(r.intended_prompt_tokens for r in plan)
    total_output_worst = sum(r.max_tokens for r in plan)
    print(f"{provider_display_name} API calibration")
    print(f"  output_dir:        {out_dir}")
    print(f"  planned_requests:  {len(plan)}")
    print(f"  worst_case_input_tokens:  {total_input}")
    print(f"  worst_case_output_tokens: {total_output_worst}")
    print(
        f"  worst_case_cost_usd:      "
        f"${estimate_cost_usd(total_input, total_output_worst, price_per_m_input_usd, price_per_m_output_usd):.4f}"
    )

    if args.dry_run and not args.allow_live_api:
        write_summary(out_dir, {"count": 0, "status_counts": {}}, cfg, provider_display_name=provider_display_name)
        print("  No API calls were made (dry-run).")
        return 0

    if args.allow_live_api and not args.mock:
        if not live_implemented:
            print(
                f"ERROR: live mode is not yet implemented for {provider_display_name}.\n"
                "Use --dry-run or --mock to exercise this script; live execution "
                "requires a tested provider call implementation (see "
                "docs/real_llm_multi_provider_plan.md).",
                file=sys.stderr,
            )
            return 6
        if not os.environ.get(api_key_env_var, ""):
            print(
                f"ERROR: {api_key_env_var} is not set. Export it before running live mode.",
                file=sys.stderr,
            )
            return 5

    run_requests(
        plan, args, out_dir, mock=args.mock,
        build_client_fn=build_client_fn,
        call_streaming_fn=call_streaming_fn,
        call_non_streaming_fn=call_non_streaming_fn,
        price_per_m_input_usd=price_per_m_input_usd,
        price_per_m_output_usd=price_per_m_output_usd,
        retryable_error_names=retryable_error_names,
        mock_call_fn=mock_call_fn,
    )
    overall = aggregate_results(
        out_dir,
        price_per_m_input_usd=price_per_m_input_usd,
        price_per_m_output_usd=price_per_m_output_usd,
    )
    write_summary(out_dir, overall, cfg, provider_display_name=provider_display_name)

    print(f"  completed: {overall['status_counts'].get('success', 0)}")
    print(f"  failed:    {sum(overall['status_counts'].get(s, 0) for s in ('error', 'timeout', 'rate_limited'))}")
    print(f"  skipped:   {overall['status_counts'].get('skipped', 0)}")
    print(f"  estimated_cost_usd: ${overall.get('estimated_cost_usd')}")
    return 0
