"""Immutable transport types; ACK evidence is external, never inferred."""
from dataclasses import dataclass
from enum import Enum


class Reason(str, Enum):
    INVALID = 'INVALID_PROPOSAL'
    UNSUPPORTED = 'UNSUPPORTED_OPERATION'
    CAPACITY = 'NO_PRESSURE_DOMAIN_NOT_PROVEN'
    MODIFIED = 'NATIVE_PLAN_DISAGREEMENT'
    ACK = 'INVALID_OR_INCOMPLETE_ACK'
    POISONED = 'BOUNDARY_STOPPED'


class BoundaryError(ValueError):
    pass


@dataclass(frozen=True)
class Span:
    request_id: str  # native engine ID; P1 application identity is separately bound
    epoch: int
    start: int
    end: int


@dataclass(frozen=True)
class Proposal:
    batch_id: str
    spans: tuple[Span, ...]
    token_budget: int
    active_limit: int


@dataclass(frozen=True)
class Acceptance:
    batch_id: str
    native_step: int
    spans: tuple[Span, ...]
    tokens: int
    active_slots: int  # includes resident requests receiving no work
    sample_mask: tuple[bool, ...]  # aligned with spans; validity, not sampled IDs


@dataclass(frozen=True)
class Rejection:
    batch_id: str
    reason: Reason
    detail: str
    native_called: bool


@dataclass(frozen=True)
class RunnerAck:
    batch_id: str
    native_step: int
    spans: tuple[Span, ...]
    sample_mask: tuple[bool, ...]
    provenance: str  # only synthetic_cpu accepted in P2A
    success: bool
    quiescent: bool
