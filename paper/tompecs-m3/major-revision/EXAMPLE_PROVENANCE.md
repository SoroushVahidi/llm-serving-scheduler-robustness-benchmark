# Fixed saved-record example provenance

Outcome-selected illustration: among BurstGPT conditions with SLO mean latency lower, token throughput lower, and p95 latency higher than chunked-FCFS, take lexicographically first (window, region, profile). Not random or representative. Identity fixed here; regeneration never reselects.

Source commit: `2a65c0e139d1410475170781469901559960265d`. Execution commit: `2d8342e699f35044044ac518c0b75a3c4a1c768c`.

Run: `c01-full-167b9074e5711420`; condition: `burstgpt::burstgpt_pilot_v2_w12::HIGH_PRESSURE`; window `burstgpt_pilot_v2_w12`; region `HIGH_PRESSURE`; profile `kv262144` (8 full-context slots). The window name contains `pilot_v2`, but these two cells are new full-campaign records (`reused=false`).

Canonical request-array SHA-256: `b9948dfb1b172d32857ae09fad3f02e542e5dcf75f4535481fc224c7b41fb621`. Canonicalization is UTF-8 JSON with sorted keys, separators `,`/`:`, and `allow_nan=False`. The entire condition-input file is separately hashed below.

Paths below are relative to the unchanged rc1 extracted root (locally `/home/soroush/artifacts/lssp-m3-rc1-20261022/staging`). All 200 exact requests, full terminal states and journals stay there.

| File | Bytes | SHA-256 |
|---|---:|---|
| `evidence/c01/inputs/full-inputs.json` | 55407339 | `a77bf5420ca8a55c3765919dbf42e774794f471da6ff404d0ad19a53c43a8c8c` |
| `evidence/c01/launch.json` | 20587 | `6d89c212ecd41037c5fe4e5ede8fb10fdd2a8aa99dabf723aabc50f060b9e66b` |
| `evidence/c01/runs/c01-full-167b9074e5711420/cells/ecec167d9fb8e426ac67298b/result.json` | 47558 | `ee256fd9cfec5844d7c5148de9d211f68c3b9fd264edd953ec836049764268f4` |
| `evidence/c01/runs/c01-full-167b9074e5711420/cells/ecec167d9fb8e426ac67298b/events.jsonl.gz` | 29731 | `4ea21b3f0d1bfd29b6caea27d268f5d19c04b6926cee937331301b8d90edfb22` |
| `evidence/c01/runs/c01-full-167b9074e5711420/cells/9feed68339670e5b366d064f/result.json` | 47599 | `33fc8572bad1d715d5e20fe6d0cfcbf71b0d5cb18e3a60e758f85957614632fe` |
| `evidence/c01/runs/c01-full-167b9074e5711420/cells/9feed68339670e5b366d064f/events.jsonl.gz` | 31489 | `a35a5aa4ad758fdca7e1f704849001aad6d130a7c7c046036615d196f4ccf98b` |
| `code/c01/research/lssp-c01/policies.py` | 2591 | `d54e96880afb9001dc0fbc19511bb6338367eb828948a48cd68a516e871fdbb1` |
| `code/c01/research/lssp-c01/engine.py` | 4510 | `2907a198a3ede133000429c57aec3269faf47ac96e019b19302dcae3ccbc6836` |

Both result identities are `167b9074e57114203e6aaaf3ded08b7b4d8f0a72b35c69054fa995de8d4ef47a`. Policy IDs are `chunked_fcfs_c01` and `slo_gated_c01`; cell directory IDs are `ecec167d9fb8e426ac67298b`, `9feed68339670e5b366d064f`.

## Selected requests and event locations

Requests 13/14 mark the first change in admitted membership; 26 is the maximum completion-delay request and last completion in both runs; 196 is the maximum completion-improvement request. These choices are retrospective and fixed, not an exhaustive causal decomposition. Exact source and derived record IDs, all displayed times, first output, TTFT and first-prefill event indices are in `example-requests.csv`.

Zero-based journal event 13 completes request 5 at 0.014 s. Event 14 admits 13 under C and 14 under S; event 16 admits the other member. Request 26 begins prefill at C event 26 / S event 223. The two journals contain 1,150 / 1,347 events. Every terminal state was independently reconstructed, including prefill/output totals, first output, completion, anchor and residency; resource ledgers, intent/execution, spans and arrivals were checked.

## Computation and interpretation

`analyze_example.py` uses standard-library direct arithmetic on all terminal records plus journal admissions. `verify_example.py` uses NumPy and an independently written event-state reconstruction, without importing the generator or production engine/policies. It checks all compact CSV fields and printed table values, selection identity/count, all 400 terminal states, and journal/input hashes. Relative/absolute tolerance is 1e-12 for floating arithmetic; hashes, integer counts, identities and terminal states are exact.

Both schedules fully complete 200 requests with 3,520 emitted outputs. Throughput divides that fixed total by first-arrival-to-last-completion, including drain. Mean uses all 200 latencies, p95 uses linear interpolation; the single-condition p95 is not a source mean of window p95s. Waiting-to-prefill is distinct from TTFT and total latency. Output lengths are available only retrospectively, not to policies.

The 151 earlier / 29 later / 20 equal completions and -5.008 s sum explain compatibility of the mean with worse final completion; a few selected requests do not explain every aggregate effect. Request 26 determines the duration but is not a p95 bracket. Bracket IDs and values are retained in `example-verification.json`. No intervention or new simulated request was performed.

## Read-only reproduction

```bash
python paper/tompecs-m3/major-revision/analyze_example.py /path/to/rc1-extraction --output /tmp/m3-example
python paper/tompecs-m3/major-revision/verify_example.py /path/to/rc1-extraction --derived /tmp/m3-example --report /tmp/m3-example-check.json
```

Use Python without `-O` (assertions are checks). Generator requires Python standard library; independent checker requires NumPy. Output must be outside the frozen evidence root. Scripts never reselect an example, run a simulator, or write frozen files. A mismatch fails rather than selecting another condition. Full package hashes cover both analysis scripts; their SHA-256s are recorded in the final support verification report.
