# Measurement and response contract

## Scope and identity

Capture is restricted to synthetic engineering fixtures (`LSSP_MGPU05_SYNTHETIC=1`). Raw prompts are token-ID arrays made from the pinned three-token fixture. Full output text, token IDs and SSE envelopes are retained only in these new synthetic artifacts. The collector rejects non-synthetic journals; the scheduler capture class requires the explicit synthetic flag. This is an operational guard, not a privacy classifier: real traces require a separately reviewed data-minimization design. Digests of low-entropy real text are not automatically anonymous.

The declared ID is stable across paired policy executions and repetitions; directory + block + policy + repetition + commit identifies an execution. A request must map to API `cmpl-{request_id}` and exactly one engine `cmpl-{request_id}-0-{8hex}`. `n=1`, no echo, no speculative outputs, forced output length (`ignore_eos=true`), pinned model/tokenizer, temperature 0 and seed 0 are explicit. Class/ordinal/arrival/deadline/weight must survive receipt exactly. Engine suffix checks are version-specific and fail closed if changed.

Request payloads, model/tokenizer/config/source hashes, software versions, command, environment controls, hardware provenance and startup/cleanup records are durable. Each request records dispatch, pre-header-write transport trace, HTTP status, every complete SSE data event, finish reason, usage and `[DONE]`, terminal status, text and token IDs. Stream framing buffers partial UTF-8/lines until a complete SSE event; its timestamp is observation of that event, not first-byte arrival.

The independent validator reads raw client journals and server logs; it does not trust collector PASS flags or previously saved `validation.json`. It joins IDs, checks prompt IDs/hash/count, metadata, sampled IDs, executed sample counts, usage, output limit, finish and DONE. The existing independent MGPU02 decision oracle also runs over warmup plus scored requests. Native must have no SLAI holds; SLAI must exhibit holds and independent decision agreement. Original adapters and semantic guards remain unchanged.

## Four different correctness statements

| Statement | Evidence / treatment |
|---|---|
| Syntactic/API validity | Exactly one mapped response, valid SSE choices/index/model/object, HTTP 200, length finish, one usage record and DONE; otherwise failed or incomplete, never successful inference |
| Token-count and identity consistency | Prompt vector length and actual received IDs; output API IDs exactly equal runner sampled IDs and counts per execution step; usage and forced target agree |
| Content transport consistency | Independently load hashed `tokenizer.json` through the Rust tokenizer; decode the complete sampled ID sequence with special tokens retained and require exact equality to concatenated API text; persist text/ID digests and raw synthetic text |
| Semantic answer correctness / numerical reproducibility | **NOT VERIFIED** by repetitive synthetic prompts. There is no reference factual answer or independently computed logits. Record cross-run ID/text equality descriptively; differences across policies are not automatically correctness failures |

Independent re-encoding of returned text is also recorded. BPE is not a one-to-one representation: `encode(decode(ids))` may differ in IDs/count. A difference is reported explicitly; it cannot override exact runner/API ID agreement or be silently called a counting error. These synthetic token vectors are the actual inputs; they are not a claim that a realistic text trace was tokenized faithfully. Corrupted text that does not decode from captured output IDs fails acceptance.

The pinned primary source contract is [completion request/response schema](https://github.com/vllm-project/vllm/blob/v0.27.1/vllm/entrypoints/openai/completion/protocol.py), [streaming implementation](https://github.com/vllm-project/vllm/blob/v0.27.1/vllm/entrypoints/openai/completion/serving.py), and [engine ID processing](https://github.com/vllm-project/vllm/blob/v0.27.1/vllm/v1/engine/input_processor.py). Local/upstream checksums are preserved in `artifacts/mgpu05/local-validation/api-upstream.json`. This capture depends on `return_token_ids=true`, `skip_special_tokens=false`, `spaces_between_special_tokens=false`, and final usage enabled.

## Clock domains and observable boundaries

All elapsed times use `time.monotonic()` / CLOCK_MONOTONIC. Client and engine record host, boot ID and Linux time-namespace inode. Cross-process subtraction requires exact domain equality, single-node deployment and physical device evidence. Synthetic test histories are explicitly labeled; passing synthetic tests cannot produce a physical PASS. Wall-clock UTC is provenance only. No clock is replaced with the SLAI simulated clock.

| Quantity | Observation / limitation |
|---|---|
| Scheduled arrival | Shared client monotonic epoch + frozen relative arrival; request bodies are serialized before epoch |
| Client dispatch | Entry to asynchronous HTTP request; offered workload uses open-loop tasks, no intentional semaphore throttling |
| Transport send | HTTPX/httpcore `send_request_headers.started`, before actual header write; detects client connection-pool delay, not NIC emission |
| HTTP server receipt | **NOT VERIFIED**: no API ingress hook; never substitute scheduler receipt and call it HTTP receipt |
| Scheduler receipt | Monotonic entry into scheduler `add_request`, with metadata and prompt digest after validation |
| Scheduler admission | Existing `admitted` event when the first native allocation is recorded; an observation after allocation, not exact GPU dispatch |
| Runner token observation | Host `update_from_output` callback entry associated with exact sampled token IDs; one sample/request per step enforced; **not GPU generation time** |
| Client token observation | Complete SSE event time + associated delta token IDs. A multi-token event is one coalesced observation group |
| Completion | Client terminal event following verified finish/usage/DONE; also keep last token-bearing event and terminal observation for failures |
| Client queueing | Dispatch − scheduled arrival; additionally transport-start − dispatch, capturing connection-pool wait |
| Server queueing | Admission − scheduler receipt only; HTTP preprocessing/IPC/transport is not separately identified |
| Actual token generation/emission | **NOT VERIFIED**. No invented interpolation, equal spacing or back-calculation of token timestamps |

Instrumentation writes may perturb scheduling and SLAI's measured batch-time estimate. Existing timing semantics are retained, but equivalence of instrumented and old uninstrumented performance has **not** been established. CPU tests do not measure that perturbation. The proposed pilot is a fully instrumented engineering stratum; main performance evidence still requires protocol F8's separately authorized overhead check.

## Metric eligibility

- Client-observed TTFT: first token-bearing SSE observation − scheduled arrival. Also report dispatch-to-first-group separately; include client lag in the primary arrival-based quantity.
- Client E2E: successful completion − scheduled arrival; failure/timeout is not a completed latency observation.
- Client-observed TPOT: `(last token-bearing group time − first group time)/(N−1)` for complete N>1. Coalescing can bias this value, including zero; it is an endpoint observation summary, not mean GPU generation interval. N=1 is undefined.
- Client inter-token gaps: available only if every token-bearing event contains exactly one returned ID. Still a client observation metric, never a server generation metric. Coalesced streams have NOT VERIFIED individual gaps. Host runner-callback gaps remain a separately named diagnostic.
- Throughput: completed requests or their output tokens divided by scheduled epoch through run-end/drain. Failures remain in the offered denominator, and partial output counts are reported separately by request. These tiny transients do not estimate steady-state capacity.
- Client SLO goodput: successful requests meeting arrival-based TTFT≤1 s, class-specific observed gaps≤0.1/0.3/0.5 s and E2E≤30 s, divided by the frozen offered-arrival interval. These are **engineering conventions**, not fitted service promises or the main preregistration thresholds. LST is not an E2E deadline.

SLO logic is three-valued. Observed TTFT/E2E breach or terminal failure is FAIL. Complete valid single-token-observation streams meeting all thresholds are PASS. If gap observations are coalesced, otherwise acceptable requests are NOT VERIFIED. Lower goodput counts PASS only; upper counts PASS + NOT VERIFIED. Report both, never silently drop missing gaps. A single output token has a vacuous gap condition.

## Failure, censoring and evidence

HTTP errors, client errors, timeout, explicit cancellation, EOF without DONE and client saturation are terminal failures, not censored successes. A missing terminal is administratively incomplete: mark NOT VERIFIED before its E2E deadline, known SLO failure after that deadline; retain unknown latency. Cancellation before dispatch is distinct from dispatch and is counted as an offered failure. A partially observed output must match a prefix of runner IDs. A malformed ID, count, clock or state invalidates acceptance, even when text is nonempty.

A hash chain covers client event order; terminal/run-end events fsync. Server diagnostics fsync log lines and retain readiness polling, startup milestones and process exits. After server cleanup a seal hashes all files in the execution directory. An offline audit rejects missing/added/changed sealed files. This detects alteration against the seal, not malicious rewriting of both artifacts and seal. External storage permissions/backups remain necessary. Cache files sit outside the sealed execution directory. Hard kill/storage loss can leave an unsealed run: **NOT VERIFIED**, never fill in missing records.

The offline auditor requires both warmup and scored cohorts, source plan identity, physical A100 checks, matching clock domains, valid cleanup, all requests complete, independent decisions and dispatch limits. Request errors are handled/tested locally, but recovery from such errors has not been physically validated. Per-request generation timestamps, ingress timing, numeric reproducibility and overhead remain separate NOT VERIFIED fields even if the engineering acceptance is PASS.
