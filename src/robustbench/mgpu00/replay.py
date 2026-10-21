"""Open-loop asynchronous replay with prepared token inputs and explicit overload.

No worker pool, per-request prompt generation, or semaphore that silently shifts
arrivals. A capacity overrun is an invalid observation, not deferred traffic.
HTTP dispatch is an observable client event; scheduler admission is joined from
server instrumentation and is never inferred from an HTTP response timestamp.
"""
import asyncio
from dataclasses import dataclass
import hashlib
import json
import math
import time

import httpx

from .metadata import RequestMetadata


@dataclass(frozen=True)
class PreparedRequest:
    metadata: RequestMetadata
    prompt_token_ids: tuple[int, ...]
    output_tokens: int

    def __post_init__(self):
        if not self.prompt_token_ids or any(type(x) is not int or x < 0 for x in self.prompt_token_ids):
            raise ValueError("Prepared nonempty token-ID input required")
        if type(self.output_tokens) is not int or self.output_tokens < 1:
            raise ValueError("Positive output target required")

    def payload(self, model):
        return {"model": model, "prompt": list(self.prompt_token_ids), "max_tokens": self.output_tokens,
                "temperature": 0.0, "seed": 0, "ignore_eos": True, "stream": True,
                "stream_options": {"include_usage": True}, "request_id": self.metadata.request_id,
                "vllm_xargs": self.metadata.xargs()}


def quantile(values, q):
    if not values:
        return None
    values = sorted(values)
    return values[min(len(values) - 1, math.ceil(q * len(values)) - 1)]


async def replay(requests, *, model, client, max_inflight, timeout_s, max_dispatch_delay_s,
                 start_delay_s=.1):
    if not requests or max_inflight < 1 or timeout_s <= 0 or max_dispatch_delay_s <= 0:
        raise ValueError("Invalid replay parameters")
    ids = [r.metadata.request_id for r in requests]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate workload request IDs")
    # Serialization and all token preparation finish BEFORE the timed injection epoch.
    encoded = [json.dumps(r.payload(model), sort_keys=True, separators=(",", ":")).encode() for r in requests]
    input_hash = hashlib.sha256(b"\n".join(encoded)).hexdigest()
    clock = time.monotonic
    start = clock() + start_delay_s
    inflight = 0
    peak = 0

    async def send(request, body):
        nonlocal inflight, peak
        m = request.metadata
        row = {"request_id": m.request_id, "ordinal": m.ordinal, "class_id": m.class_id,
               "scheduled_arrival_s": m.arrival_s, "deadline_s": m.deadline_s, "weight": m.weight,
               "dispatch_s": None, "transport_send_s": None, "scheduler_received_s": None,
               "server_admission_s": None, "first_token_s": None, "completion_s": None,
               "prompt_tokens_target": len(request.prompt_token_ids), "output_tokens_target": request.output_tokens,
               "prompt_tokens": None, "output_tokens": None, "status": "NOT_DISPATCHED"}
        await asyncio.sleep(max(0., start + m.arrival_s - clock()))
        row["wake_s"] = clock() - start
        if inflight >= max_inflight:
            row["status"] = "CLIENT_SATURATED"
            return row
        inflight += 1
        peak = max(peak, inflight)

        async def trace(name, info):
            if name.endswith("send_request_headers.started") and row["transport_send_s"] is None:
                row["transport_send_s"] = clock() - start

        row["dispatch_s"] = clock() - start
        finish_reason = None
        done = False
        try:
            async with asyncio.timeout(timeout_s):
                async with client.stream("POST", "/v1/completions", content=body,
                                         headers={"Content-Type": "application/json"},
                                         extensions={"trace": trace}) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if not line.startswith("data:"):
                            continue
                        value = line[5:].strip()
                        if value == "[DONE]":
                            done = True
                            break
                        data = json.loads(value)
                        if "error" in data:
                            raise RuntimeError(str(data["error"]))
                        for choice in data.get("choices", []):
                            # First observed text-bearing token chunk, not a fabricated server TTFT.
                            if choice.get("text") and row["first_token_s"] is None:
                                row["first_token_s"] = clock() - start
                            finish_reason = choice.get("finish_reason") or finish_reason
                        if data.get("usage"):
                            row["prompt_tokens"] = data["usage"].get("prompt_tokens")
                            row["output_tokens"] = data["usage"].get("completion_tokens")
            row["completion_s"] = clock() - start
            row["finish_reason"] = finish_reason
            row["status"] = ("COMPLETED" if done and finish_reason and row["first_token_s"] is not None and
                             row["prompt_tokens"] == len(request.prompt_token_ids) and
                             row["output_tokens"] == request.output_tokens else "INCOMPLETE")
        except (Exception, asyncio.CancelledError) as exc:
            row["completion_s"] = clock() - start
            row["status"] = "TIMEOUT" if isinstance(exc, TimeoutError) else "FAILED"
            row["error"] = f"{type(exc).__name__}: {exc}"
        finally:
            inflight -= 1
        row["dispatch_delay_s"] = row["dispatch_s"] - m.arrival_s
        row["transport_dispatch_delay_s"] = (None if row["transport_send_s"] is None else
                                              row["transport_send_s"] - m.arrival_s)
        row["client_observed_latency_s"] = row["completion_s"] - row["dispatch_s"]
        row["arrival_to_completion_s"] = row["completion_s"] - m.arrival_s
        row["client_ttft_s"] = (None if row["first_token_s"] is None else
                                 row["first_token_s"] - row["dispatch_s"])
        return row

    rows = await asyncio.gather(*(send(r, body) for r, body in zip(requests, encoded)))
    elapsed = clock() - start
    sent = [r for r in rows if r["dispatch_s"] is not None]
    completed = [r for r in rows if r["status"] == "COMPLETED"]
    delays = [r["dispatch_delay_s"] for r in sent]
    transport_delays = [r["transport_dispatch_delay_s"] for r in sent if r["transport_dispatch_delay_s"] is not None]
    span = max(r.metadata.arrival_s for r in requests) - min(r.metadata.arrival_s for r in requests)
    actual_span = max((r["dispatch_s"] for r in sent), default=0) - min((r["dispatch_s"] for r in sent), default=0)
    return {"schema": "mgpu00-replay-v1", "input_sha256": input_hash, "clock": "monotonic",
            "client_start_monotonic_s": start, "measurement_interval_s": elapsed,
            "offered": len(sent), "scheduled": len(rows), "completed": len(completed), "peak_inflight": peak,
            "intended_arrival_rate_rps": ((len(rows) - 1) / span if span > 0 else None),
            "actual_dispatch_rate_rps": ((len(sent) - 1) / actual_span if actual_span > 0 else None),
            "dispatch_rate_definition": "(count-1)/(last-first); simultaneous burst rate is undefined",
            "achieved_request_throughput_rps": len(completed) / elapsed,
            "achieved_token_throughput_tps": sum(r["output_tokens"] for r in completed) / elapsed,
            "dispatch_delay_p95_s": quantile(delays, .95), "dispatch_delay_max_s": max(delays, default=None),
            "transport_delay_max_s": max(transport_delays, default=None),
            "transport_timing_complete": len(transport_delays) == len(sent),
            "max_allowed_dispatch_delay_s": max_dispatch_delay_s,
            "valid_replay": (len(completed) == len(rows) and bool(delays) and
                             len(transport_delays) == len(sent) and
                             max(delays) <= max_dispatch_delay_s and
                             all(x <= max_dispatch_delay_s for x in transport_delays)),
            "rows": rows}


def make_client(base_url, max_inflight):
    return httpx.AsyncClient(base_url=base_url, timeout=None, trust_env=False,
                             limits=httpx.Limits(max_connections=max_inflight,
                                                max_keepalive_connections=max_inflight))
