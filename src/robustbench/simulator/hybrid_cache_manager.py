"""hybrid_cache_manager: Implements the Option C wrapped HybridCacheManager
enforcing dual-tier block allocations, atomic transitions, and state invariants.
"""
from __future__ import annotations

import math
from typing import Dict, List, Optional, Set, Tuple, Any

from robustbench.core.types import GPUConfig
from robustbench.policies.apt_serve_faithful import (
    CacheTier,
    CacheRepresentation,
    CacheAssignment,
    CacheTransitionKind,
    CacheTransitionRequest,
    CacheTransitionResult,
    CacheCapacitySnapshot,
    HybridCacheSnapshot,
    AptServeAdapterConfig,
    AptServeCapacityViolation
)
from robustbench.simulator.kv_block_manager import KVBlockSpaceManager


class HybridCacheInvariantError(Exception):
    """Raised when a hybrid cache state invariant is violated."""
    pass


class HybridCacheManager:
    """Wrapper memory manager coordinating a primary KV block manager
    and a parallel compressed hidden-state block manager.
    """
    def __init__(self, config: GPUConfig, block_size: int = 16):
        self.config = config
        self.block_size = block_size
        
        # Primary KV block manager (exactly same as legacy)
        self.kv_manager = KVBlockSpaceManager(
            block_size=block_size,
            num_gpu_blocks=config.max_kv_tokens // block_size,
            watermark=0.01
        )
        
        # Compressed hidden-state block manager
        if config.hybrid_cache_enabled:
            self.hidden_manager = KVBlockSpaceManager(
                block_size=block_size,
                num_gpu_blocks=config.hidden_cache_capacity_blocks,
                watermark=0.01
            )
        else:
            self.hidden_manager = None

        self.assignments: Dict[int, CacheTier] = {}
        self.num_tokens: Dict[int, int] = {}

    def blocks_needed(self, num_tokens: int) -> int:
        """Compute the exact number of KV blocks needed to hold a given token count."""
        if num_tokens <= 0:
            return 0
        return -(-num_tokens // self.block_size)

    def hidden_blocks_needed(self, kv_blocks: int) -> int:
        """Determine compressed hidden-state blocks from primary KV blocks using ceiling rule."""
        if kv_blocks <= 0:
            return 0
        hidden_blocks = math.ceil(kv_blocks * self.config.hidden_to_kv_memory_ratio)
        return max(1, hidden_blocks)

    def get_request_tier(self, request_id: int) -> CacheTier:
        """Get the current resident tier of a request."""
        return self.assignments.get(request_id, CacheTier.NONE)

    def get_request_capacity(self, request_id: int, tier: Optional[CacheTier] = None) -> int:
        """Get block allocation size for a request."""
        if request_id not in self.assignments:
            return 0
        if tier is None:
            tier = self.assignments[request_id]
            
        if tier == CacheTier.KV:
            return self.kv_manager.num_blocks_for(request_id)
        elif tier == CacheTier.HIDDEN:
            return self.hidden_manager.num_blocks_for(request_id) if self.hidden_manager else 0
        return 0

    def can_allocate(self, prompt_tokens: int, target_tier: CacheTier) -> bool:
        """Check if a new request can fit in the target tier."""
        if target_tier == CacheTier.KV:
            return self.kv_manager.can_allocate(prompt_tokens)
        elif target_tier == CacheTier.HIDDEN:
            if not self.config.hybrid_cache_enabled or self.hidden_manager is None:
                raise ValueError("Hybrid cache is disabled")
            kv_blocks = self.blocks_needed(prompt_tokens)
            hidden_blocks = self.hidden_blocks_needed(kv_blocks)
            # Watermark check on hidden tier (match kv_manager watermark behavior)
            return self.hidden_manager._allocator.num_free_blocks - hidden_blocks >= self.hidden_manager.watermark_blocks
        return False

    def allocate(self, request_id: int, prompt_tokens: int, target_tier: CacheTier) -> None:
        """Allocate a request to the target tier."""
        if request_id in self.assignments:
            raise ValueError(f"Request {request_id} already has an allocation.")
            
        if target_tier == CacheTier.KV:
            self.kv_manager.allocate(request_id, prompt_tokens)
            self.assignments[request_id] = CacheTier.KV
            self.num_tokens[request_id] = prompt_tokens
        elif target_tier == CacheTier.HIDDEN:
            if not self.config.hybrid_cache_enabled or self.hidden_manager is None:
                raise ValueError("Hybrid cache is disabled")
            kv_blocks = self.blocks_needed(prompt_tokens)
            hidden_blocks = self.hidden_blocks_needed(kv_blocks)
            if self.hidden_manager._allocator.num_free_blocks < hidden_blocks:
                raise AptServeCapacityViolation(f"Insufficient capacity on hidden tier: needed {hidden_blocks}, free {self.hidden_manager._allocator.num_free_blocks}")
            # We reserve the exact computed blocks by allocating hidden_blocks * block_size on the hidden manager
            self.hidden_manager.allocate(request_id, hidden_blocks * self.block_size)
            self.assignments[request_id] = CacheTier.HIDDEN
            self.num_tokens[request_id] = prompt_tokens
        else:
            raise ValueError(f"Invalid allocation target tier: {target_tier}")

    def release(self, request_id: int) -> None:
        """Idempotently release a request from the cache."""
        if request_id not in self.assignments:
            return
        tier = self.assignments[request_id]
        if tier == CacheTier.KV:
            self.kv_manager.free(request_id)
        elif tier == CacheTier.HIDDEN:
            if self.hidden_manager:
                self.hidden_manager.free(request_id)
        self.assignments.pop(request_id, None)
        self.num_tokens.pop(request_id, None)

    def begin_transition_release(self, request_id: int) -> Dict[str, Any]:
        """Phase 1 of a decoupled transition: release request_id's
        current tier allocation without yet acquiring the destination.

        Exists so a whole decision *batch* can release every request's
        source-tier allocation before acquiring any destination-tier
        allocation (see finish_transition_acquire). Per-request
        release-then-acquire cannot express a batch where a HIDDEN->KV
        restore needs room a KV->HIDDEN move elsewhere would free, AND a
        KV->HIDDEN move needs room a HIDDEN->KV restore elsewhere would
        free, in the same step -- whichever single direction is applied
        first would spuriously fail even though the batch's net effect
        is feasible. self.num_tokens[request_id] is deliberately left in
        place so the pending acquisition can still size itself.
        """
        if request_id not in self.assignments:
            raise ValueError(f"Unknown request {request_id}")
        curr_tier = self.assignments[request_id]
        kv_blocks_before = self.kv_manager.num_blocks_for(request_id) if curr_tier == CacheTier.KV else None
        hidden_blocks_before = (
            self.hidden_manager.num_blocks_for(request_id)
            if (curr_tier == CacheTier.HIDDEN and self.hidden_manager) else None
        )
        if curr_tier == CacheTier.KV:
            self.kv_manager.free(request_id)
        elif curr_tier == CacheTier.HIDDEN:
            if self.hidden_manager:
                self.hidden_manager.free(request_id)
        del self.assignments[request_id]
        return {
            "request_id": request_id, "source_tier": curr_tier,
            "kv_blocks_before": kv_blocks_before, "hidden_blocks_before": hidden_blocks_before,
        }

    def finish_transition_acquire(self, released: Dict[str, Any], target_tier: CacheTier) -> CacheTransitionResult:
        """Phase 2: acquire the destination-tier allocation for a
        request already released by begin_transition_release. On
        failure the request is left unassigned (neither tier) --
        callers applying a whole decision batch must roll back the
        entire manager on any failure here (the existing deepcopy-backup
        transaction in apt_serve_faithful.py already does this), not
        attempt to restore just this one request."""
        request_id = released["request_id"]
        curr_tier = released["source_tier"]
        tokens = self.num_tokens[request_id]

        if curr_tier == CacheTier.KV and target_tier == CacheTier.HIDDEN:
            if not self.config.hybrid_cache_enabled or self.hidden_manager is None:
                raise ValueError("Hybrid cache is disabled")
            hidden_blocks = self.hidden_blocks_needed(released["kv_blocks_before"])
            if self.hidden_manager._allocator.num_free_blocks < hidden_blocks:
                return CacheTransitionResult(
                    request_id=request_id, source_tier=curr_tier, destination_tier=target_tier,
                    transition_kind=CacheTransitionKind.KV_TO_HIDDEN, expected_delay=0.0,
                    recomputation_required=False, success=False, error_message="Insufficient destination hidden capacity"
                )
            self.hidden_manager.allocate(request_id, hidden_blocks * self.block_size)
            self.assignments[request_id] = CacheTier.HIDDEN
            return CacheTransitionResult(
                request_id=request_id, source_tier=curr_tier, destination_tier=target_tier,
                transition_kind=CacheTransitionKind.KV_TO_HIDDEN, expected_delay=self.config.cache_switch_latency,
                recomputation_required=False, success=True
            )

        elif curr_tier == CacheTier.HIDDEN and target_tier == CacheTier.KV:
            kv_blocks = self.blocks_needed(tokens)
            if self.kv_manager._allocator.num_free_blocks < kv_blocks:
                return CacheTransitionResult(
                    request_id=request_id, source_tier=curr_tier, destination_tier=target_tier,
                    transition_kind=CacheTransitionKind.HIDDEN_TO_KV, expected_delay=0.0,
                    recomputation_required=False, success=False, error_message="Insufficient destination KV capacity"
                )
            self.kv_manager.allocate(request_id, tokens)
            self.assignments[request_id] = CacheTier.KV
            delay = self.config.hidden_restore_latency * tokens
            recomp = (self.config.recomputation_cost_model == "full")
            return CacheTransitionResult(
                request_id=request_id, source_tier=curr_tier, destination_tier=target_tier,
                transition_kind=CacheTransitionKind.HIDDEN_TO_KV, expected_delay=delay,
                recomputation_required=recomp, success=True
            )

        else:
            raise ValueError(f"Invalid transition from {curr_tier} to {target_tier}")

    def _restore_release(self, released: Dict[str, Any]) -> None:
        """Reverse begin_transition_release for a single request whose
        subsequent finish_transition_acquire failed, used only by the
        single-request switch_tier() wrapper to preserve its own
        atomic-per-call contract (batch callers roll back the whole
        manager instead; see finish_transition_acquire)."""
        request_id = released["request_id"]
        curr_tier = released["source_tier"]
        tokens = self.num_tokens[request_id]
        if curr_tier == CacheTier.KV:
            self.kv_manager.allocate(request_id, tokens)
        elif curr_tier == CacheTier.HIDDEN:
            self.hidden_manager.allocate(request_id, released["hidden_blocks_before"] * self.block_size)
        self.assignments[request_id] = curr_tier

    def switch_tier(self, request_id: int, target_tier: CacheTier) -> CacheTransitionResult:
        """Atomically transition a single request's format and tier.
        Thin wrapper over begin_transition_release +
        finish_transition_acquire that restores the release on failure,
        for callers transitioning one request at a time (batch callers
        applying a whole decision should use the two phases directly --
        see apt_serve_faithful.py's select_action)."""
        if request_id not in self.assignments:
            raise ValueError(f"Unknown request {request_id}")

        curr_tier = self.assignments[request_id]
        if curr_tier == target_tier:
            return CacheTransitionResult(
                request_id=request_id, source_tier=curr_tier, destination_tier=target_tier,
                transition_kind=CacheTransitionKind.KV_TO_HIDDEN if target_tier == CacheTier.HIDDEN else CacheTransitionKind.HIDDEN_TO_KV,
                expected_delay=0.0, recomputation_required=False, success=True
            )
        if curr_tier not in (CacheTier.KV, CacheTier.HIDDEN) or target_tier not in (CacheTier.KV, CacheTier.HIDDEN):
            raise ValueError(f"Invalid transition from {curr_tier} to {target_tier}")

        released = self.begin_transition_release(request_id)
        result = self.finish_transition_acquire(released, target_tier)
        if not result.success:
            self._restore_release(released)
        return result

    def evict(self, request_id: int) -> CacheTransitionResult:
        """Evict a request fully from the cache, discarding all progress."""
        if request_id not in self.assignments:
            return CacheTransitionResult(
                request_id=request_id, source_tier=CacheTier.NONE, destination_tier=CacheTier.NONE,
                transition_kind=CacheTransitionKind.EVICT_FULL, expected_delay=0.0,
                recomputation_required=True, success=False, error_message="Request is not in cache"
            )
        curr_tier = self.assignments[request_id]
        self.release(request_id)
        return CacheTransitionResult(
            request_id=request_id, source_tier=curr_tier, destination_tier=CacheTier.NONE,
            transition_kind=CacheTransitionKind.EVICT_FULL, expected_delay=0.0,
            recomputation_required=True, success=True
        )

    def snapshot(self, step: int = 0, timestamp: float = 0.0) -> HybridCacheSnapshot:
        """Create a deterministic JSON-safe snapshot of cache state."""
        kv_snap = CacheCapacitySnapshot(
            tier=CacheTier.KV,
            total_capacity_blocks=self.kv_manager.num_gpu_blocks,
            used_blocks=self.kv_manager.num_used_blocks,
            free_blocks=self.kv_manager.num_free_blocks
        )
        if self.hidden_manager:
            hidden_snap = CacheCapacitySnapshot(
                tier=CacheTier.HIDDEN,
                total_capacity_blocks=self.hidden_manager.num_gpu_blocks,
                used_blocks=self.hidden_manager.num_used_blocks,
                free_blocks=self.hidden_manager.num_free_blocks
            )
        else:
            hidden_snap = CacheCapacitySnapshot(CacheTier.HIDDEN, 0, 0, 0)
            
        resident_ids = sorted(list(self.assignments.keys()))
        return HybridCacheSnapshot(
            step=step,
            timestamp=timestamp,
            kv_snapshot=kv_snap,
            hidden_snapshot=hidden_snap,
            resident_request_ids=resident_ids
        )

    def validate_invariants(self) -> None:
        """Verify strict dual-tier cache invariants, raising HybridCacheInvariantError on failure."""
        if not self.config.hybrid_cache_enabled:
            if self.hidden_manager is not None:
                raise HybridCacheInvariantError("Hidden manager initialized despite hybrid cache disabled.")
            if any(t == CacheTier.HIDDEN for t in self.assignments.values()):
                raise HybridCacheInvariantError("Resident request occupies HIDDEN tier while hybrid is disabled.")
                
        # 1. Total capacity bounds
        if self.kv_manager.num_used_blocks + self.kv_manager.num_free_blocks != self.kv_manager.num_gpu_blocks:
            raise HybridCacheInvariantError("KV manager allocation inconsistency: used + free != total")
        if self.hidden_manager:
            if self.hidden_manager.num_used_blocks + self.hidden_manager.num_free_blocks != self.hidden_manager.num_gpu_blocks:
                raise HybridCacheInvariantError("Hidden manager allocation inconsistency: used + free != total")
                
        # 2. No dual residency
        kv_resident_set = set(self.kv_manager._requests.keys())
        hidden_resident_set = set(self.hidden_manager._requests.keys()) if self.hidden_manager else set()
        
        intersection = kv_resident_set & hidden_resident_set
        if intersection:
            raise HybridCacheInvariantError(f"Duplicate residency detected: request IDs {intersection} occupy both tiers.")
            
        # 3. Ownership alignment
        for rid, tier in self.assignments.items():
            if tier == CacheTier.KV and rid not in kv_resident_set:
                raise HybridCacheInvariantError(f"Request {rid} mapped to KV but missing from KV manager.")
            if tier == CacheTier.HIDDEN and rid not in hidden_resident_set:
                raise HybridCacheInvariantError(f"Request {rid} mapped to HIDDEN but missing from Hidden manager.")
                
        # 4. Leaks check
        for rid in kv_resident_set:
            if self.assignments.get(rid) != CacheTier.KV:
                raise HybridCacheInvariantError(f"KV manager holds orphaned request {rid}.")
        for rid in hidden_resident_set:
            if self.assignments.get(rid) != CacheTier.HIDDEN:
                raise HybridCacheInvariantError(f"Hidden manager holds orphaned request {rid}.")
