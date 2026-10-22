# C01 validation and readiness

## Local checks

Final local command: `bash research/lssp-c01/check_final.sh`, tmux `lssp-c01-final-validation:cpu`, pane PID540290, shell PID540291. Logs `evidence/final-validation.txt`, exit `evidence/final-validation.exit` =0. **63 tests passed** in1.67s (42 new conformance/pipeline tests plus21 historical synthesis/campaign tests). Full input preparation then passed with unchanged payload SHA256 `56b216fdfedf34ca8a959cb764c9896cf7f6351319259cba13dc8fb98df05f1c`. Python compilation and shell syntax passed.

| Gate | Evidence / result |
|---|---|
| Reuse audit before design/execution | REUSE_AND_GAPS.md and evidence inventories; no equivalent target cells found |
| Prospective protocol | Initial commit8dd2c37; pre-launch corrections explicitly recorded in CHANGES_BEFORE_LAUNCH.md |
| Shared execution/service | Identical literal execution plans under all four policy IDs give identical journals and terminals; hand-derived1ms/prefill/decode fixture |
| Identity/completion | Duplicate/unknown IDs, duplicate spans, token discontinuity, premature completion, overgeneration, corrupt terminal all rejected |
| KV/batching | Full-context reservations, sequence limits, token-budget boundaries, partial-prefill continuity, held residents and release checked; independent cap/resource mutations rejected |
| No oracle/future leakage | Immutable field allowlist; scheduler module inspected; latent-length and future-arrival/metric-overlay changes leave identical public prefixes/decisions |
| Policy definitions | Literal FCFS, decode-first, whole-prefill and critical/prefill/SPF/residual ordering fixtures; no original/native fidelity assertion |
| Intent versus execution | Referee imports neither engine nor policy; journal/terminal reconstructed independently; injected intent/span/ID/time/KV/completion/budget failures rejected |
| Determinism/resume | Byte-equal synthetic replays; saved cells independently revalidated without rerunning; identity/input/hash/metric corruption fails closed |
| Frozen input correspondence | Full physical/canonical hash; selected window/record hashes;200 requests each, independent arrival compression and exact token/ID checks; historical seed/factor agreement |
| Conditional metrics/ties | Missing latency support retained; completed and emitted token throughput separate; exact/tolerance top sets and undefined all-tied Spearman tested |
| Inferential scope | No p-values, confidence intervals or FDR;36 full-corpus persistence records explicitly not evaluable with pilot support |

Synthetic test outputs are not scientific observations. No frozen-workload scheduler cell ran locally. The independent validator checks common execution correctness, not physical performance accuracy. Prior native-bridge limitations remain unresolved.

## Process provenance

| Process | tmux/session:window | Shell PID | Log | Exit |
|---|---|---:|---|---:|
| Copy immutable full-window payload | lssp-c01-input-copy:transfer |538572| `/home/soroush/lssp-c01-cache/transfer.log` |0|
| Initial fixtures | lssp-c01-validation:cpu |539477| evidence/local-validation-attempt1.txt |1 (incorrect fixture expectation; preserved)|
| Corrected fixtures/input freeze | lssp-c01-validation-2:cpu |539628| evidence/local-validation-input-freeze.txt |0|
| Pipeline fixtures | lssp-c01-validation-3:cpu |539916| evidence/local-validation-pipeline.txt |0|
| Margin correction tests | lssp-c01-validation-4:cpu |540063| evidence/local-validation.txt |0|
| Final regression/input check | lssp-c01-final-validation:cpu |540291| evidence/final-validation.txt |0|

Remote staging and startup evidence are recorded separately. A passed local gate authorizes staging/remote engineering validation; submission occurs only after those checks pass. A successful submission does not establish valid outcomes, historical reversal persistence or publication readiness.
