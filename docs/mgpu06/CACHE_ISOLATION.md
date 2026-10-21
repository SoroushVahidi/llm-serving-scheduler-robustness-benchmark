# MGPU06 cache-placement correction

Scope: the already-authorized **Block 0 only**, two policy executions in one full-A100 allocation, at most 50 minutes (0.833334 GPU-hours). This is an engineering check, not permission for the remaining 22 executions. The frozen design, model, tokenizer, sampling, scheduler, numerical options and measurement rules are unchanged. No physical acceptance follows from CPU validation.

## Cause and preservation

The previous zero-GPU preflight found home usage at the 56,320 MiB hard limit (51,200 MiB soft quota, expired grace); its exclusive write probe failed with `EDQUOT`. The prepared launcher redirected three cache paths but left Triton's default home cache and other configuration/temp paths exposed. This was a preflight blocker, not an observed MGPU06 GPU failure.

Original evidence remains at `artifacts/mgpu06/preflight-20261021T2214Z/` in the isolated Wulver checkout and the local MGPU05 checkout. Nothing in HOME is removed, moved, truncated or changed to reclaim space. The Qwen snapshot remains at its original absolute path and is read offline. Historical MGPU03 evidence and the MGPU05 baseline evidence seal describe their original commits and are not rewritten to describe this amendment.

## Exact placement and reviewed implementation

Set `MGPU06_RUNTIME_PARENT=/project/ikoutis/sv96/r`. The batch wrapper creates `m6-$SLURM_JOB_ID/{b,n,s}` for bootstrap/client, native server/workers and SLAI server/workers respectively. Every directory below the project mount is owner-only mode 0700; files use umask 077. Existing nonprivate parents, symlinks, reused phase directories and paths inside HOME/the checkout fail. These directories are outside Git and research artifacts. Their configuration is copied into the durable block/execution manifests; generated kernels are not scientific evidence.

`src/robustbench/mgpu06/runtime.py` is the authoritative complete mapping. Relative to each phase root:

| Settings | Location |
|---|---|
| TRITON_CACHE_DIR / TRITON_HOME / TRITON_DUMP_DIR / TRITON_OVERRIDE_DIR | triton/cache, triton/home, triton/dump, triton/override |
| VLLM_CACHE_ROOT / VLLM_CONFIG_ROOT / VLLM_ASSETS_CACHE | vllm/cache, vllm/config, vllm/assets |
| VLLM_RPC_BASE_PATH | ipc (short enough for UUID Unix sockets) |
| XDG_CACHE_HOME / XDG_CONFIG_HOME / XDG_DATA_HOME / XDG_STATE_HOME / XDG_RUNTIME_DIR | xdg/cache, xdg/config, xdg/data, xdg/state, xdg/run |
| TORCHINDUCTOR_CACHE_DIR / TORCH_HOME / TORCH_EXTENSIONS_DIR | torch/inductor, torch/home, torch/extensions |
| CUDA_CACHE_PATH / CUDA_TILE_CACHE_DIR | cuda/compute, cutile |
| TMPDIR / TMP / TEMP | tmp |
| HF_HOME / HF_HUB_CACHE / HF_ASSETS_CACHE / HF_XET_CACHE / HF_MODULES_CACHE / HF_TOKEN_PATH | hf, hf/hub, hf/assets, hf/xet, hf/modules, hf/token |
| HUGGINGFACE_HUB_CACHE / HUGGINGFACE_ASSETS_CACHE | same hub/assets paths |
| FLASHINFER_WORKSPACE_BASE / FLASHINFER_CUBIN_DIR / VLLM_FLASHINFER_AUTOTUNE_CACHE_DIR | flashinfer, flashinfer/cubins, flashinfer/autotune |
| DG_JIT_CACHE_DIR / CUTE_DSL_CACHE_DIR / FLASH_ATTENTION_CUTE_DSL_CACHE_DIR | deep-gemm, cute, flash-attention-cute |
| NUMBA_CACHE_DIR / PYTHONPYCACHEPREFIX | numba, python/pycache |

The wrapper runs Python with `-B`, also sets PYTHONDONTWRITEBYTECODE=1, HF_HUB_OFFLINE=1, TRANSFORMERS_OFFLINE=1, HF_HUB_DISABLE_TELEMETRY=1, VLLM_NO_USAGE_STATS=1 and VLLM_DO_NOT_TRACK=1. These prevent bytecode/home configuration/telemetry writes and downloads; they do not change sampling or numerical kernels. HOME is never changed. Existing V2 runner, FlashInfer-sampler-off and OMP=4 settings remain as in MGPU05.

Pinned installed versions include vLLM 0.27.1, Torch 2.13.0, Triton 3.7.1, Transformers 5.16.1, tokenizers 0.23.1, huggingface_hub 1.29.0, FlashInfer 0.6.16.post3, CUDA runtime 13.0.96, NVRTC 13.0.88 and cuDNN 9.20.0.48. `scripts/mgpu06/runtime-sources.json` pins the inspected cache-path sources and installed CUDA/kernel distribution versions; the wrapper rejects drift before third-party imports. Existing asset/API/source pins are checked afterward. Local Torch/Transformers/tokenizers versions differ; local tests are unit tests, while Wulver is the execution authority.

Two optional features have unredirectable HOME caches in the inspected sources. The wrapper rejects the **presence** of CCCL_ENABLE_CACHE, FLASHINFER_TRACE_APPLY or FLASHINFER_TRACE_APPLY_PATH, even values `0`/empty. CCCL checks presence, not truthiness. Trace Apply substitutes external kernels and is not part of this experiment. Neither feature is enabled by the approved harness. This rejection preserves the existing computation; it does not silently switch algorithms.

Each server and descendants inherit their phase environment. Warmup/replay run in the bootstrap process with its separately isolated environment. Fresh per-policy writable caches preserve MGPU05's intended cache controls. OS/filesystem/driver caches are not cleared; startup remains separate from inference and this amendment makes no startup speed claim.

## CPU validation and remaining boundary

The CPU probe checks effective vLLM/HF/Torch/Triton destinations, creates a Triton cache entry without compiling a GPU kernel, binds a vLLM-length Unix socket on project storage, verifies child inheritance, and requires hidden GPUs and no initialized CUDA context. Run it under `strace -f -e trace=%file` to inspect filesystem access. Read-only model/config access in HOME is allowed; writes are not. A CPU trace cannot certify every GPU-time path; source inspection and fail-closed version/configuration pins address known runtime defaults. Any unexpected physical write/quota error remains a failed engineering run, never a retry authorization.

Use the same pre-import wrapper for `scripts/mgpu05/repeatability.py --check-only`; direct invocation without its recorded environment is rejected. The original 2940-second launcher timeout plus 45-second kill grace, 1200-second readiness bound, full-A100 provenance, stop-on-first-policy-failure and response/timing/oracle validation remain in effect.

Before submission recheck account/standard QoS, quotas, actual A100 availability, existing jobs and the 10 GPU-hour pilot ledger. Use Slurm `--test-only` for a zero-allocation scheduling estimate. A test-only display number is **not a submitted job ID**. If immediate service cannot be adequately established, stop without submitting a job that would remain pending beyond the supervised interval. Never automatically submit a second allocation.

The prepared command in MGPU05 now additionally requires `export MGPU06_RUNTIME_PARENT=/project/ikoutis/sv96/r` and the newly tested exact commit. Initial runtime configuration is printed to Slurm stdout and is also preserved in project runtime.json files and execution manifests. Audit physical evidence separately after the authorized initial health interval; first-pair instrumentation, timing observability, full-A100 identity and fidelity remain NOT VERIFIED until raw physical evidence passes independent review.
