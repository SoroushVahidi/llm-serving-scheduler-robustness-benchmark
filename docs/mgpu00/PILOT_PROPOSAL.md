# Proposed MGPU01 pilot — NO GO, not authorized for execution

Machine-readable plan: [`pilot_proposal.json`](../../configs/mgpu00/pilot_proposal.json).
It is a proposal, not an executable launcher. MGPU00 contains no pilot submission
command or array script.

The requested factorial is two full-A100 deployments (1 GPU and 2 GPUs/TP2), two
mechanisms, three sources, four windows/source, one load region, three independent
repetitions: **144 measured physical executions**. Optional DP2 adds 72, for 216.

Windows were selected by a fixed SHA-256 ordering of their IDs with seed string
`LSSP-MGPU01-prespec-v1:`, without reading their outcomes:

| Source | Window IDs |
|---|---|
| Azure-2024 | pilot_v2_w21, pilot_v2_w20, pilot_v2_w37, pilot_v2_w17 |
| Bailian/Qwen | stage0_w02, pilot_v2_w10, stage0_w05, stage0_w03 |
| BurstGPT | pilot_v2_w37, pilot_v2_w36, pilot_v2_w32, pilot_v2_w21 |

Full names and hashes are in the JSON. All windows have 200 requests. The
proposed region is HIGH_PRESSURE, 1.5 times a newly bracketed native-reference
capacity for each deployment/window, holding per-request SLO budgets fixed.
Old MIG calibration rates cannot be reused. Bounds that already violate the
calibration criterion must be rebracketed or reported unresolved, not accepted
as measured knees. The precise knee criterion/model/decode limit require a new
protocol freeze before any pilot launch; no missing value is guessed here.

## Gates

1. MGPU00 local tests and full-A100 engineering smoke pass.
2. Extend and validate SLAI for the required prefill/KV-pressure conditions;
   the current guarded adapter does not claim general faithful support.
3. Validate TP2 semantics independently. The single-GPU adapter currently rejects
   TP2; no multi-GPU execution is authorized in MGPU00. Trace equivalence must
   include classes, admission, actual service/holds, LST clocks, active/KV state,
   and custom scheduler execution with the selected distributed backend.
4. Select and pin an appropriate model, tokenizer, numerical precision, context,
   serving budget, decode limit and complete software environment.
5. Calibrate full devices and demonstrate that the corrected injector is not
   saturated at each chosen operating point. Keep failure/preemption records.
6. Obtain the user's separate authorization for the 144 measured executions.

DP2 additionally requires a prespecified routing rule, independent scheduler/KV
state per replica, end-to-end metadata forwarding, summed offered-load metrics,
and routing/queue-imbalance telemetry. It is not two unrelated copies of the
single-GPU experiment. No DP implementation is silently assumed ready.

## Runtime and GPU-hours

Smoke job 1434545 failed its device-identity gate before server startup or replay,
using 0.043333 allocated GPU-hours. No serving-time result is available.
Therefore no numeric pilot GPU-hour estimate is justified yet. The historical
9.5 GiB, 0.5B-model observations are not full-device or TP2 runtime measurements.

After valid measurements, use per-cell allocated time including startup/reset:

`H_measured = 72 * t_1GPU_hours + 144 * t_TP2_hours`.

For optional DP2, add `144 * t_DP2_hours`. Add separately measured calibration,
mechanism validation and failed/preempted attempts. An explicit 20% rerun reserve
can be used for budgeting, but is a planning assumption, not a measured failure
rate. TP2/DP2 duration cannot be inferred as half the single-GPU duration. The
smoke's short synthetic window and eager execution also do not predict the
full 200-request trace replay or a larger scientific model.

A completed smoke can establish startup cost and the cost of its own fixture;
it cannot alone supply the missing TP2 calibration or a defensible campaign
point estimate. This proposal remains NO GO even if that restricted smoke passes.
