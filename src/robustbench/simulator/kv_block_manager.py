"""
Reusable KV-cache block/page infrastructure for faithful serving baselines.

Independently reimplemented from vLLM v0.1.0's paged KV-cache design
(commit 67d96c29fba9b72cb4c4edbc26211c208a00ebdd -- see
docs/vllm_faithful_scheduler_reference.md for the exact pinned source files
and algorithm summary). This is a from-scratch Python reimplementation
adapted to this simulator's single-sequence-per-request model; it is not a
copy of vLLM's source.

Used by the `vllm_faithful` policy (src/robustbench/policies/vllm_faithful.py).
Kept generic enough to be reused by future faithful baselines that also need
paged KV-cache bookkeeping (e.g. a faithful Llumnix baseline).

Backward compatibility
----------------------
This module is entirely new and opt-in: it is not imported by GPUState,
Simulator, or constraints.py, so every existing policy and experiment
continues to use the legacy scalar-KV-token abstraction (InternalRequest.kv_tokens,
GPUConfig.max_kv_tokens) completely unchanged.

Known simplifications vs. the pinned reference (see the reference doc's
"Exclusions" section for the full rationale)
----------------------------------------------------------------------------
- No copy-on-write / sequence forking (beam search): every request here is
  exactly one sequence, so block ref counts are always 0 or 1 in practice.
  The ref-counting machinery is kept for correct free/double-free semantics,
  not because forking is supported.
- No CPU swap space / swap-based preemption: only GPU blocks are modeled.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List


class KVBlockManagerError(Exception):
    """Raised on a genuine block-manager invariant violation (double free,
    allocating without free capacity, referencing an unknown request)."""


@dataclass
class KVBlock:
    """One fixed-size physical KV-cache block."""
    block_number: int
    ref_count: int = 0


class KVBlockAllocator:
    """Free-list allocator for fixed-size KV blocks on one device.

    Mirrors vLLM v0.1.0's BlockAllocator (vllm/core/block_manager.py).
    """

    def __init__(self, num_blocks: int) -> None:
        if num_blocks < 0:
            raise ValueError(f"num_blocks must be non-negative, got {num_blocks}")
        self.num_blocks = num_blocks
        self._free_blocks: List[KVBlock] = [
            KVBlock(block_number=i) for i in range(num_blocks)
        ]

    def allocate(self) -> KVBlock:
        if not self._free_blocks:
            raise KVBlockManagerError("Out of memory: no free KV blocks available.")
        block = self._free_blocks.pop()
        block.ref_count = 1
        return block

    def free(self, block: KVBlock) -> None:
        if block.ref_count <= 0:
            raise KVBlockManagerError(f"Double free of block {block.block_number}.")
        block.ref_count -= 1
        if block.ref_count == 0:
            self._free_blocks.append(block)

    @property
    def num_free_blocks(self) -> int:
        return len(self._free_blocks)

    @property
    def num_used_blocks(self) -> int:
        return self.num_blocks - self.num_free_blocks


@dataclass
class _RequestBlockState:
    block_table: List[KVBlock] = field(default_factory=list)
    num_tokens: int = 0  # exact tokens accounted for (prompt-so-far + decoded)


class KVBlockSpaceManager:
    """Maps requests (by request_id) to physical KV blocks on one GPU.

    Mirrors vLLM v0.1.0's BlockSpaceManager (vllm/core/block_manager.py).

    Parameters
    ----------
    block_size : tokens per block (vLLM default: 16).
    num_gpu_blocks : total blocks available on this device.
    watermark : fraction of GPU blocks reserved to avoid eviction thrashing
        (vLLM default: 0.01). ``can_allocate`` requires
        ``free_blocks - needed >= watermark_blocks``, not merely
        ``free_blocks >= needed``.
    """

    def __init__(
        self, block_size: int, num_gpu_blocks: int, watermark: float = 0.01,
    ) -> None:
        if block_size <= 0:
            raise ValueError(f"block_size must be positive, got {block_size}")
        if num_gpu_blocks < 0:
            raise ValueError(f"num_gpu_blocks must be non-negative, got {num_gpu_blocks}")
        if not (0.0 <= watermark < 1.0):
            raise ValueError(f"watermark must be in [0, 1), got {watermark}")
        self.block_size = block_size
        self.num_gpu_blocks = num_gpu_blocks
        self.watermark = watermark
        self.watermark_blocks = int(watermark * num_gpu_blocks)
        self._allocator = KVBlockAllocator(num_gpu_blocks)
        self._requests: Dict[int, _RequestBlockState] = {}

    @staticmethod
    def blocks_needed(num_tokens: int, block_size: int) -> int:
        """Number of fixed-size blocks needed to hold `num_tokens` tokens."""
        if num_tokens <= 0:
            return 0
        return -(-num_tokens // block_size)  # ceil division without float error

    # ------------------------------------------------------------------
    # Admission (new request; mirrors can_allocate / allocate)
    # ------------------------------------------------------------------

    def can_allocate(self, prompt_tokens: int) -> bool:
        """Would a new request with this many prompt tokens fit right now,
        respecting the watermark reserve?"""
        needed = self.blocks_needed(prompt_tokens, self.block_size)
        return self._allocator.num_free_blocks - needed >= self.watermark_blocks

    def allocate(self, request_id: int, prompt_tokens: int) -> None:
        """Reserve blocks for a new request's prompt. Raises
        KVBlockManagerError if there is not enough free capacity -- callers
        should check `can_allocate` first (matching the pinned reference's
        own can_allocate-then-allocate two-phase pattern)."""
        if request_id in self._requests:
            raise KVBlockManagerError(f"Request {request_id} already has an allocation.")
        needed = self.blocks_needed(prompt_tokens, self.block_size)
        block_table = [self._allocator.allocate() for _ in range(needed)]
        self._requests[request_id] = _RequestBlockState(
            block_table=block_table, num_tokens=prompt_tokens,
        )

    # ------------------------------------------------------------------
    # Decode-time growth (mirrors can_append_slot / append_slot)
    # ------------------------------------------------------------------

    def can_append_slot(self, request_id: int) -> bool:
        """Can this request receive one more token right now? True unless a
        new logical block would be needed and no physical block is free."""
        state = self._requests[request_id]
        blocks_after = self.blocks_needed(state.num_tokens + 1, self.block_size)
        if blocks_after <= len(state.block_table):
            return True  # fits in the already-allocated last block
        return self._allocator.num_free_blocks >= 1

    def append_slot(self, request_id: int) -> None:
        """Account for one more token, allocating a new block only when the
        current last block is full."""
        state = self._requests[request_id]
        state.num_tokens += 1
        blocks_needed_now = self.blocks_needed(state.num_tokens, self.block_size)
        if blocks_needed_now > len(state.block_table):
            state.block_table.append(self._allocator.allocate())

    # ------------------------------------------------------------------
    # Release
    # ------------------------------------------------------------------

    def free(self, request_id: int) -> None:
        """Free all blocks held by this request. A no-op if the request was
        never allocated or was already freed (mirrors the pinned
        reference's own free(), which tolerates double-free-by-omission at
        this level; KVBlockAllocator.free still raises on a true
        double-free of the same physical block)."""
        state = self._requests.pop(request_id, None)
        if state is None:
            return
        for block in state.block_table:
            self._allocator.free(block)

    def reset(self) -> None:
        for request_id in list(self._requests.keys()):
            self.free(request_id)

    # ------------------------------------------------------------------
    # Introspection
    # ------------------------------------------------------------------

    def is_allocated(self, request_id: int) -> bool:
        return request_id in self._requests

    def allocated_request_ids(self) -> List[int]:
        """All request_ids this manager currently tracks an allocation for."""
        return list(self._requests.keys())

    def num_blocks_for(self, request_id: int) -> int:
        return len(self._requests[request_id].block_table)

    def kv_tokens_for(self, request_id: int) -> int:
        """Exact token count currently accounted for by this request."""
        return self._requests[request_id].num_tokens

    def allocated_kv_capacity_for(self, request_id: int) -> int:
        """Block-rounded KV footprint (>= exact token count): the
        internal-fragmentation-inclusive figure real paged-KV serving
        actually reserves for this request."""
        return self.num_blocks_for(request_id) * self.block_size

    def internal_fragmentation_tokens(self) -> int:
        """Total wasted capacity across all currently-allocated requests:
        sum over requests of (blocks_allocated * block_size - exact tokens)."""
        return sum(
            len(s.block_table) * self.block_size - s.num_tokens
            for s in self._requests.values()
        )

    @property
    def num_free_blocks(self) -> int:
        return self._allocator.num_free_blocks

    @property
    def num_used_blocks(self) -> int:
        return self._allocator.num_used_blocks
