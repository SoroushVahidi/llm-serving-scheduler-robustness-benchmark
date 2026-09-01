"""apt_serve_faithful: Interface scaffolding, configuration schemas, typed contracts,
and JSON-based versioned IPC schemas for Apt-Serve's upcoming implementation.

This is a Phase E implementation of the multi-step simulator policy integration.
"""
from __future__ import annotations

import json
import os
import sys
import subprocess
import hashlib
import copy
from dataclasses import asdict, dataclass, field
from enum import Enum, auto
from typing import Dict, List, Optional, Protocol, Set, Tuple, Union, Any

from .base import BasePolicy
from ..core.action import Action
from ..core.types import GPUConfig, ObservableRequest, ObservableState, ObservableGPUState


# ======================================================================
# 1. TYPED CACHE INTERFACES (Step 5)
# ======================================================================

class CacheTier(str, Enum):
    KV = "kv"
    HIDDEN = "hidden"
    NONE = "none"


class CacheRepresentation(str, Enum):
    KV_BLOCKED = "kv_blocked"
    COMPRESSED_HIDDEN = "compressed_hidden"


@dataclass(frozen=True)
class CacheAssignment:
    request_id: int
    target_tier: CacheTier
    required_units: int
    current_tier: CacheTier
    reason: str
    scheduler_metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class CacheTransitionKind(str, Enum):
    KV_TO_HIDDEN = "kv_to_hidden"
    HIDDEN_TO_KV = "hidden_to_kv"
    EVICT_FULL = "evict_full"


@dataclass(frozen=True)
class CacheTransitionRequest:
    request_id: int
    transition_kind: CacheTransitionKind
    source_tier: CacheTier
    destination_tier: CacheTier


@dataclass(frozen=True)
class CacheTransitionResult:
    request_id: int
    source_tier: CacheTier
    destination_tier: CacheTier
    transition_kind: CacheTransitionKind
    expected_delay: float
    recomputation_required: bool
    success: bool
    error_message: Optional[str] = None


@dataclass(frozen=True)
class CacheCapacitySnapshot:
    tier: CacheTier
    total_capacity_blocks: int
    used_blocks: int
    free_blocks: int


@dataclass(frozen=True)
class HybridCacheSnapshot:
    step: int
    timestamp: float
    kv_snapshot: CacheCapacitySnapshot
    hidden_snapshot: CacheCapacitySnapshot
    resident_request_ids: List[int] = field(default_factory=list) # sorted for determinism

    def __post_init__(self) -> None:
        if self.resident_request_ids != sorted(self.resident_request_ids):
            raise ValueError("resident_request_ids must be sorted deterministically")


@dataclass(frozen=True)
class AptServeRequestView:
    request_id: int
    waiting_duration: float
    running_duration: float
    ttft_slo: float
    tbt_slo: float
    current_cache_tier: CacheTier
    kv_blocks_needed: int
    hidden_blocks_needed: int
    recomputation_cost_model: str
    priority: float
    slo_violation_state: bool


@dataclass(frozen=True)
class AptServeSchedulerDecision:
    selected_request_ids: List[int]
    cache_assignments: Dict[int, CacheTier]
    evictions: List[int]
    deprioritized_requests: List[int]
    value_scores: Dict[int, float]
    schema_version: int = 1


# ======================================================================
# 2. ADAPTER ERROR HIERARCHY & CONTRACTS (Step 6)
# ======================================================================

class AptServeAdapterError(Exception):
    """Base exception for all Apt-Serve adapter errors."""
    pass


class AptServeSourceCheckoutMissing(AptServeAdapterError):
    """Raised when the official Apt-Serve checkout cannot be found."""
    pass


class AptServeWrongCommit(AptServeAdapterError):
    """Raised when the checkout commit does not match the pinned commit."""
    pass


class AptServeSourceHashMismatch(AptServeAdapterError):
    """Raised when the source code file hashes do not match known provenance."""
    pass


class AptServeEnvironmentMissing(AptServeAdapterError):
    """Raised when the pinned Python 3.11 environment is not available."""
    pass


class AptServeProtocolMismatch(AptServeAdapterError):
    """Raised when the subprocess IPC schema version does not match."""
    pass


class AptServeSubprocessTimeout(AptServeAdapterError):
    """Raised when the external scheduler subprocess times out."""
    pass


class AptServeMalformedResponse(AptServeAdapterError):
    """Raised when the subprocess stdout contains invalid JSON."""
    pass


class AptServeInvalidSchedulerDecision(AptServeAdapterError):
    """Raised when the returned decision is invalid or mathematically impossible."""
    pass


class AptServeCapacityViolation(AptServeAdapterError):
    """Raised when the scheduler tries to allocate beyond physical bounds."""
    pass


class AptServeUnsupportedConfiguration(AptServeAdapterError):
    """Raised when the given configuration is not supported by the adapter."""
    pass


@dataclass(frozen=True)
class AptServeAdapterConfig:
    checkout_path: str
    conda_env_name: str = "apt-serve"
    subprocess_timeout_seconds: float = 10.0
    python_executable: Optional[str] = None
    execution_mode: str = "official" # "official", "test", or "recorded_trace"


@dataclass(frozen=True)
class AptServeEnvironmentSpec:
    required_python_version: str = "3.11"
    required_torch_version: str = "2.3.0"
    required_vllm_version: str = "0.5.0.post1"


@dataclass(frozen=True)
class AptServeSourceProvenance:
    official_repo_url: str = "https://github.com/eddiegaoo/Apt-Serve"
    pinned_commit: str = "c953217988274a761da35cf06c01033b18dadf68"
    schema_version: int = 1


class AptServeSchedulerClient(Protocol):
    """Protocol defining the interface for the upcoming subprocess scheduler client."""
    def initialize(self, config: AptServeAdapterConfig) -> None:
        """Verify checkout, environment, and launch the subprocess."""
        ...

    def schedule_step(self, state_input: AptServeSchedulerInput) -> AptServeSchedulerDecision:
        """Serialize state, run subprocess, and parse returned decision."""
        ...

    def terminate(self) -> None:
        """Terminate the subprocess cleanly."""
        ...


APT_SERVE_EXPECTED_HASHES = {
    "additional_designs/aptserve_block.py": "771d3590abfef2e6fc3a71a37bce231c276bade4188c0eadd12bf48d642980c5",
    "additional_designs/aptserve_sequence.py": "e50a546a267c832256eaa554e74cecd8e3e50ef8cd737e4e4ba8647c9943ac52",
    "additional_designs/core/aptserve_block_manager.py": "8ec4fed8417227f2bdd40c695b9c4bbe3d7164272f771200e72aeef9ad552943",
    "additional_designs/core/aptserve_interfaces.py": "703009b951c1bf61e34c6a1bc92123334ea6568b6b668d2f966192df76e036d1",
    "additional_designs/core/aptserve_scheduler.py": "b381415aafeb46d8cdad3598a00983dfad7a1c9ff992b0a3a7708596b979b02e"
}


class AptServeSubprocessClient:
    """Subprocess client running Apt-Serve scheduler in isolated python 3.11 environment."""
    def __init__(self, config: AptServeAdapterConfig) -> None:
        self.config = config
        self.provenance = AptServeSourceProvenance()
        self.proc: Optional[subprocess.Popen] = None

    def __enter__(self) -> AptServeSubprocessClient:
        self.initialize()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.terminate()

    def initialize(self) -> None:
        self.terminate() # ensure clean start

        if self.config.execution_mode == "official":
            # 1. Verify checkout path exists
            if not self.config.checkout_path or not os.path.exists(self.config.checkout_path):
                raise AptServeSourceCheckoutMissing(
                    f"Official Apt-Serve checkout directory missing: {self.config.checkout_path}"
                )

            # 2. Run git verification
            git_dir = os.path.join(self.config.checkout_path, ".git")
            if not os.path.exists(git_dir):
                raise AptServeSourceCheckoutMissing(
                    f"Apt-Serve checkout path is not a git repository: {self.config.checkout_path}"
                )

            try:
                commit = subprocess.check_output(
                    ["git", "rev-parse", "HEAD"],
                    cwd=self.config.checkout_path,
                    text=True,
                    stderr=subprocess.DEVNULL
                ).strip()
            except subprocess.CalledProcessError as e:
                raise AptServeSourceCheckoutMissing(f"Failed to check git commit on {self.config.checkout_path}: {e}")

            if commit != self.provenance.pinned_commit:
                raise AptServeWrongCommit(
                    f"Official Apt-Serve commit mismatch: expected {self.provenance.pinned_commit}, got {commit}"
                )

            # 3. Verify file hashes
            for rel_path, expected_sha in APT_SERVE_EXPECTED_HASHES.items():
                abs_path = os.path.join(self.config.checkout_path, rel_path)
                if not os.path.exists(abs_path):
                    raise AptServeSourceHashMismatch(f"Expected source file missing: {rel_path}")
                h = hashlib.sha256()
                with open(abs_path, "rb") as f:
                    h.update(f.read())
                actual_sha = h.hexdigest()
                if actual_sha != expected_sha:
                    raise AptServeSourceHashMismatch(
                        f"Source file hash mismatch for {rel_path}: expected {expected_sha}, got {actual_sha}"
                    )

            # 4. Verify external python environment
            py_exe = self.config.python_executable or "python3"
            env_check_code = """
import sys
if sys.version_info[:2] != (3, 11):
    sys.exit(11)
try:
    import torch
    import vllm
    import xformers
    import vllm_flash_attn
except ImportError as e:
    print(e)
    sys.exit(12)
"""
            try:
                res = subprocess.run(
                    [py_exe, "-c", env_check_code],
                    capture_output=True,
                    text=True,
                    check=False
                )
                if res.returncode == 11:
                    raise AptServeEnvironmentMissing(f"Python 3.11 required, but {py_exe} version is different.")
                elif res.returncode == 12:
                    raise AptServeEnvironmentMissing(f"Missing required imports in 3.11 environment: {res.stdout.strip()}")
                elif res.returncode != 0:
                    raise AptServeEnvironmentMissing(f"Conda/Python environment check failed with exit code {res.returncode}: {res.stderr.strip()}")
            except FileNotFoundError:
                raise AptServeEnvironmentMissing(f"External Python executable '{py_exe}' not found.")

        # Launch the subprocess worker in corresponding mode
        policy_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(policy_dir)))
        
        if self.config.execution_mode == "official":
            worker_path = os.path.join(project_root, "scripts", "apt_serve", "apt_serve_scheduler_worker.py")
            py_exe = self.config.python_executable or "python3"
            cmd = [py_exe, worker_path, "--checkout", self.config.checkout_path]
        else:
            worker_path = os.path.join(project_root, "scripts", "apt_serve", "fake_scheduler_worker.py")
            py_exe = sys.executable
            cmd = [py_exe, worker_path]

        try:
            self.proc = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1
            )
        except Exception as e:
            raise AptServeAdapterError(f"Failed to start subprocess worker: {e}")

    def schedule_step(self, state_input: AptServeSchedulerInput) -> AptServeSchedulerDecision:
        # Re-initialize process if not running (enabling multiple sequential one-shot calls)
        if not self.proc or self.proc.poll() is not None:
            self.initialize()

        # Serialize request
        payload = state_input.serialize_json().decode("utf-8") + "\n"
        if len(payload) > 10 * 1024 * 1024:
            raise AptServeUnsupportedConfiguration("Request payload size exceeds maximum limit of 10MB.")

        # Non-blocking communication with timeout
        try:
            stdout_data, stderr_data = self.proc.communicate(
                input=payload,
                timeout=self.config.subprocess_timeout_seconds
            )
        except subprocess.TimeoutExpired:
            self.terminate()
            raise AptServeSubprocessTimeout("External scheduler subprocess timed out.")
        except Exception as e:
            raise AptServeAdapterError(f"Subprocess communication failed: {e}")

        # Post-execution cleanup for one-shot worker lifecycle
        ret_code = self.proc.poll()
        if ret_code is not None and ret_code != 0:
            raise AptServeAdapterError(f"Subprocess worker exited with non-zero code {ret_code}. Stderr: {stderr_data.strip()}")

        if not stdout_data.strip():
            raise AptServeMalformedResponse("Subprocess worker returned empty response.")

        try:
            output = AptServeSchedulerOutput.deserialize_json(stdout_data.encode("utf-8"))
        except AptServeProtocolMismatch:
            raise
        except Exception as e:
            raise AptServeMalformedResponse(f"Failed to parse subprocess JSON output: {e}. Output was: {stdout_data}")

        # Validate response consistency
        # Validate that every selected ID was present in input
        input_ids = {r["request_id"] for r in state_input.waiting_requests} | {r["request_id"] for r in state_input.running_requests}
        for sid in output.selected_request_ids:
            if sid not in input_ids:
                raise AptServeInvalidSchedulerDecision(f"Selected request ID {sid} was not present in input requests.")

        return AptServeSchedulerDecision(
            selected_request_ids=output.selected_request_ids,
            cache_assignments={int(k): CacheTier(v) for k, v in output.cache_assignments.items()},
            evictions=output.evictions,
            deprioritized_requests=output.deprioritized_requests,
            value_scores={int(k): v for k, v in output.value_scores.items()}
        )

    def terminate(self) -> None:
        if self.proc:
            try:
                self.proc.stdin.close()
            except Exception:
                pass
            try:
                self.proc.terminate()
                self.proc.wait(timeout=1.0)
            except subprocess.TimeoutExpired:
                self.proc.kill()
            except Exception:
                pass
            self.proc = None


# ======================================================================
# 3. VERSIONED IPC SCHEMAS (Step 7)
# ======================================================================

@dataclass(frozen=True)
class AptServeSchedulerInput:
    schema_version: int
    request_id: int
    simulator_step: int
    timestamp: float
    gpus: List[Dict[str, Any]]
    waiting_requests: List[Dict[str, Any]]
    running_requests: List[Dict[str, Any]]
    cache_snapshot: Dict[str, Any]

    def serialize_json(self) -> bytes:
        """Return a deterministic JSON byte string (sorted keys)."""
        d = asdict(self)
        return json.dumps(d, sort_keys=True).encode("utf-8")

    @classmethod
    def deserialize_json(cls, data: bytes) -> AptServeSchedulerInput:
        payload = json.loads(data.decode("utf-8"))
        if payload.get("schema_version") != 1:
            raise AptServeProtocolMismatch(f"Expected schema_version=1, got {payload.get('schema_version')}")
        return cls(
            schema_version=payload["schema_version"],
            request_id=payload["request_id"],
            simulator_step=payload["simulator_step"],
            timestamp=payload["timestamp"],
            gpus=payload["gpus"],
            waiting_requests=payload["waiting_requests"],
            running_requests=payload["running_requests"],
            cache_snapshot=payload["cache_snapshot"]
        )


@dataclass(frozen=True)
class AptServeSchedulerOutput:
    schema_version: int
    request_id: int
    selected_request_ids: List[int]
    cache_assignments: Dict[str, str] # mapped request_id as str -> CacheTier name as str
    evictions: List[int]
    deprioritized_requests: List[int]
    value_scores: Dict[str, float] # mapped request_id as str -> float

    def serialize_json(self) -> bytes:
        d = asdict(self)
        return json.dumps(d, sort_keys=True).encode("utf-8")

    @classmethod
    def deserialize_json(cls, data: bytes) -> AptServeSchedulerOutput:
        payload = json.loads(data.decode("utf-8"))
        if payload.get("schema_version") != 1:
            raise AptServeProtocolMismatch(f"Expected schema_version=1, got {payload.get('schema_version')}")
        return cls(
            schema_version=payload["schema_version"],
            request_id=payload["request_id"],
            selected_request_ids=payload["selected_request_ids"],
            cache_assignments=payload["cache_assignments"],
            evictions=payload["evictions"],
            deprioritized_requests=payload["deprioritized_requests"],
            value_scores=payload["value_scores"]
        )


# ======================================================================
# 4. ACTIVE RUNTIME POLICY INTEGRATION (Step 4)
# ======================================================================

class AptServeSchedulerPolicy(BasePolicy):
    """Faithful implementation of Apt-Serve's adaptive request scheduling
    running inside the simulator via JSON IPC subprocess worker.
    """
    name = "apt_serve_faithful"

    def __init__(
        self,
        adapter_config: Optional[AptServeAdapterConfig] = None,
        hybrid_cache_enabled: bool = False,
        hidden_cache_capacity_blocks: int = 0,
        hidden_to_kv_memory_ratio: float = 0.1,
        cache_switch_latency: float = 0.0,
        hidden_restore_latency: float = 0.0,
        recomputation_cost_model: str = "full",
        apt_serve_rho: float = 0.5,
        apt_serve_ttft_slo: float = 2.0,
        apt_serve_tbt_slo: float = 0.05,
        block_size: int = 16
    ) -> None:
        self.adapter_config = adapter_config
        self.hybrid_cache_enabled = hybrid_cache_enabled
        self.hidden_cache_capacity_blocks = hidden_cache_capacity_blocks
        self.hidden_to_kv_memory_ratio = hidden_to_kv_memory_ratio
        self.cache_switch_latency = cache_switch_latency
        self.hidden_restore_latency = hidden_restore_latency
        self.recomputation_cost_model = recomputation_cost_model
        self.apt_serve_rho = apt_serve_rho
        self.apt_serve_ttft_slo = apt_serve_ttft_slo
        self.apt_serve_tbt_slo = apt_serve_tbt_slo
        self.block_size = block_size
        
        self._cache_managers: Dict[int, Any] = {}
        self._client: Optional[AptServeSubprocessClient] = None
        self.provenance = AptServeSourceProvenance()
        self.stats: Dict[str, float] = self._empty_stats()

    @staticmethod
    def _empty_stats() -> Dict[str, float]:
        return {
            "kv_to_hidden_transitions": 0,
            "hidden_to_kv_transitions": 0,
            "evictions": 0,
            "recomputations": 0,
            "switch_latency_paid": 0.0,
            "restore_latency_paid": 0.0,
        }

    def reset(self) -> None:
        self._cache_managers = {}
        self.stats = self._empty_stats()
        self.terminate_client()

    def terminate(self) -> None:
        self.terminate_client()

    def terminate_client(self) -> None:
        if self._client:
            self._client.terminate()
            self._client = None

    def _get_cache_manager(self, gpu: ObservableGPUState) -> Any:
        from ..simulator.hybrid_cache_manager import HybridCacheManager
        mgr = self._cache_managers.get(gpu.gpu_id)
        if mgr is None:
            # Reconstruct GPUConfig from ObservableGPUState and policy configs
            gpu_config = GPUConfig(
                gpu_id=gpu.gpu_id,
                max_active_sequences=gpu.max_active_sequences,
                max_batch_tokens=gpu.max_batch_tokens,
                max_kv_tokens=gpu.max_kv_tokens,
                role=gpu.role,
                hybrid_cache_enabled=self.hybrid_cache_enabled,
                hidden_cache_capacity_blocks=self.hidden_cache_capacity_blocks,
                hidden_to_kv_memory_ratio=self.hidden_to_kv_memory_ratio,
                cache_switch_latency=self.cache_switch_latency,
                hidden_restore_latency=self.hidden_restore_latency,
                recomputation_cost_model=self.recomputation_cost_model,
                apt_serve_rho=self.apt_serve_rho,
                apt_serve_ttft_slo=self.apt_serve_ttft_slo,
                apt_serve_tbt_slo=self.apt_serve_tbt_slo
            )
            mgr = HybridCacheManager(gpu_config, block_size=self.block_size)
            self._cache_managers[gpu.gpu_id] = mgr
        return mgr

    def select_action(self, state: ObservableState) -> Action:
        action = Action()
        if not state.gpu_states:
            return action

        gpu = state.gpu_states[0]
        mgr = self._get_cache_manager(gpu)

        # 1. Reconcile completed sequences on our HybridCacheManager
        active_ids = set(gpu.active_request_ids)
        for rid in list(mgr.assignments.keys()):
            if rid not in active_ids:
                mgr.release(rid)

        # Reconcile untracked active sequences
        for req in gpu.active_requests_info:
            rid = req.request_id
            if rid not in mgr.assignments:
                decoded = gpu.tokens_decoded_per_request.get(rid, 0)
                mgr.allocate(rid, req.prompt_tokens + decoded, CacheTier.KV)

        # 2. Lazy initializer for persistent subprocess client
        if self._client is None and self.adapter_config is not None:
            self._client = AptServeSubprocessClient(self.adapter_config)
            self._client.initialize()

        if self._client is None:
            # Replay/No-adapter mode
            return action

        # 3. Map state to AptServeSchedulerInput
        waiting_requests = []
        for ir in state.waiting_queue:
            waiting_requests.append({
                "request_id": ir.request_id,
                "prompt_tokens": ir.prompt_tokens,
                "arrival_time": ir.arrival_time,
                "predicted_output_tokens": ir.predicted_output_tokens,
                "slo_deadline": ir.slo_deadline,
                "priority": ir.priority,
                "current_cache_tier": "none"
            })

        running_requests = []
        for req in gpu.active_requests_info:
            rid = req.request_id
            decoded = gpu.tokens_decoded_per_request.get(rid, 0)
            running_dur = state.time - req.arrival_time
            running_requests.append({
                "request_id": rid,
                "prompt_tokens": req.prompt_tokens,
                "arrival_time": req.arrival_time,
                "predicted_output_tokens": req.predicted_output_tokens,
                "slo_deadline": req.slo_deadline,
                "priority": req.priority,
                "current_cache_tier": mgr.get_request_tier(rid).value,
                "running_duration": running_dur
            })

        gpus_info = [{
            "gpu_id": gpu.gpu_id,
            "max_active_sequences": gpu.max_active_sequences,
            "max_batch_tokens": gpu.max_batch_tokens,
            "max_kv_tokens": gpu.max_kv_tokens,
            "apt_serve_ttft_slo": self.apt_serve_ttft_slo,
            "apt_serve_tbt_slo": self.apt_serve_tbt_slo,
            "hidden_cache_capacity_blocks": self.hidden_cache_capacity_blocks
        }]

        cache_snapshots = asdict(mgr.snapshot(step=state.step, timestamp=state.time))

        scheduler_input = AptServeSchedulerInput(
            schema_version=1,
            request_id=state.step,
            simulator_step=state.step,
            timestamp=state.time,
            gpus=gpus_info,
            waiting_requests=waiting_requests,
            running_requests=running_requests,
            cache_snapshot=cache_snapshots
        )

        # 4. Invoke client
        try:
            decision = self._client.schedule_step(scheduler_input)
        except Exception as e:
            raise AptServeAdapterError(f"Step {state.step} schedule_step failed: {e}")

        # 5. Atomic Decision-Application Transaction & Rollback mapping (Step 6) using copy.deepcopy()
        backup_mgr = copy.deepcopy(mgr)

        def rollback() -> None:
            mgr.assignments = backup_mgr.assignments
            mgr.num_tokens = backup_mgr.num_tokens
            mgr.kv_manager = backup_mgr.kv_manager
            mgr.hidden_manager = backup_mgr.hidden_manager

        try:
            # 5a. Apply Evictions first (Reclaim capacity)
            for rid in decision.evictions:
                res = mgr.evict(rid)
                if not res.success:
                    raise AptServeCapacityViolation(f"Eviction failed for request {rid}: {res.error_message}")
                self.stats["evictions"] += 1

                # Preempt maps to preempt action
                if gpu.gpu_id not in action.preempt:
                    action.preempt[gpu.gpu_id] = []
                action.preempt[gpu.gpu_id].append(rid)

            # 5b. Apply Cache Transitions (switch and restorations) in two
            # phases: release every transitioning request's *current*
            # tier allocation first, then acquire every destination-tier
            # allocation. A whole decision batch's net capacity effect
            # can be feasible even when a HIDDEN->KV restore needs room a
            # KV->HIDDEN move elsewhere would free, AND that KV->HIDDEN
            # move needs room the HIDDEN->KV restore would free, in the
            # same step -- a mutual dependency in both directions at
            # once. No single per-request application order (raw client
            # dict order, or any static tier-based priority) can resolve
            # that; decoupling every release from every acquisition does,
            # since by the time any acquisition is attempted all releases
            # in the batch have already freed their capacity.
            pending_transitions = []
            for rid, target_tier in decision.cache_assignments.items():
                if rid in mgr.assignments and mgr.get_request_tier(rid) != target_tier:
                    pending_transitions.append((rid, target_tier))

            released_by_rid = {
                rid: mgr.begin_transition_release(rid) for rid, _ in pending_transitions
            }
            for rid, target_tier in pending_transitions:
                res = mgr.finish_transition_acquire(released_by_rid[rid], target_tier)
                if not res.success:
                    raise AptServeCapacityViolation(
                        f"Transition failed for request {rid} to tier {target_tier}: {res.error_message}"
                    )
                if res.transition_kind == CacheTransitionKind.KV_TO_HIDDEN:
                    self.stats["kv_to_hidden_transitions"] += 1
                    self.stats["switch_latency_paid"] += res.expected_delay
                else:
                    self.stats["hidden_to_kv_transitions"] += 1
                    self.stats["restore_latency_paid"] += res.expected_delay
                    if res.recomputation_required:
                        self.stats["recomputations"] += 1
                # Inject transition delay by adding to hold_decode
                if res.expected_delay > 0.0:
                    if gpu.gpu_id not in action.hold_decode:
                        action.hold_decode[gpu.gpu_id] = []
                    action.hold_decode[gpu.gpu_id].append(rid)

            # 5c. Allocate newly selected waiting requests
            # Build local waiting_map to support fast and correct lookup
            waiting_map = {ir.request_id: ir for ir in state.waiting_queue}
            for rid in decision.selected_request_ids:
                if rid not in active_ids:
                    # Brand new admission from waiting queue
                    ir = waiting_map.get(rid)
                    if ir is None:
                        raise AptServeAdapterError(f"Selected request {rid} not found in waiting queue.")
                    
                    target_tier = decision.cache_assignments.get(rid, CacheTier.KV)
                    mgr.allocate(rid, ir.prompt_tokens, target_tier)

                    if gpu.gpu_id not in action.admit:
                        action.admit[gpu.gpu_id] = []
                    action.admit[gpu.gpu_id].append(rid)

            # 5d. Enforce strict invariants
            mgr.validate_invariants()

        except Exception as e:
            rollback()
            raise AptServeAdapterError(f"Decision transaction failed and state rolled back: {e}")

        return action


# Alias name
AptServeFaithfulPolicy = AptServeSchedulerPolicy
