"""Run-order / repetition / resume orchestration machinery for the future
real-system validation campaign (docs/REAL_SYSTEM_VALIDATION_PLAN.md).

This module implements the ORCHESTRATION MECHANICS only: given an
abstract list of cell keys (scheduler, workload_family, load_region) it
knows how to order repetitions (deterministic-seeded random, or ABBA),
assign repetition ids, detect duplicate cells, and provide idempotent
resume/skip behavior against a completed-cell ledger. It contains no
Phase-12 case list and no scientific case-selection logic -- those are
frozen in a later, separate task only after the admitted Phase-12
analysis completes and passes structural validation.
"""
from __future__ import annotations

import json
import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple


@dataclass(frozen=True)
class CellKey:
    scheduler: str
    workload_family: str
    load_region: str

    def as_tuple(self) -> Tuple[str, str, str]:
        return (self.scheduler, self.workload_family, self.load_region)

    def cell_id(self) -> str:
        return f"{self.scheduler}::{self.workload_family}::{self.load_region}"


@dataclass(frozen=True)
class RunUnit:
    """One (cell, repetition) unit of execution, with a stable, globally
    unique run_id derived from the cell id and repetition index (never
    from execution order), so resume/duplicate detection is order-
    independent."""
    cell: CellKey
    repetition: int

    def run_id(self) -> str:
        return f"{self.cell.cell_id()}::rep{self.repetition}"


def expand_cells_to_run_units(cells: List[CellKey], repetitions: int) -> List[RunUnit]:
    if repetitions < 1:
        raise ValueError(f"repetitions must be >= 1, got {repetitions}")
    seen = set()
    for c in cells:
        if c.cell_id() in seen:
            raise ValueError(f"duplicate cell in input: {c.cell_id()}")
        seen.add(c.cell_id())
    return [RunUnit(cell=c, repetition=r) for c in cells for r in range(repetitions)]


def deterministic_random_order(units: List[RunUnit], seed: int) -> List[RunUnit]:
    """Deterministic-seeded shuffle. Same `units` + `seed` always produces
    the same order (no wall-clock or hash-randomization dependence)."""
    rng = random.Random(seed)
    indexed = list(enumerate(units))
    rng.shuffle(indexed)
    return [u for _, u in indexed]


def abba_order(units: List[RunUnit]) -> List[RunUnit]:
    """ABBA ordering across the distinct schedulers present in `units`,
    within each (workload_family, load_region, repetition) group, to
    balance time-of-day / GPU-sharing drift across paired schedulers.
    Falls back to input order for any group with != 2 schedulers (ABBA
    is only meaningful for pairwise comparison groups)."""
    groups: Dict[Tuple[str, str, int], List[RunUnit]] = {}
    for u in units:
        key = (u.cell.workload_family, u.cell.load_region, u.repetition)
        groups.setdefault(key, []).append(u)

    ordered: List[RunUnit] = []
    for key in sorted(groups.keys()):
        group = groups[key]
        schedulers = sorted({u.cell.scheduler for u in group})
        if len(schedulers) != 2:
            ordered.extend(sorted(group, key=lambda u: u.cell.scheduler))
            continue
        a, b = schedulers
        by_sched = {u.cell.scheduler: u for u in group}
        # ABBA within this single-rep-index group degenerates to A,B (one
        # unit per scheduler here); true ABBA balance across repetitions
        # is achieved by alternating which repetition-index group starts
        # with A vs B.
        rep = key[2]
        pair = [by_sched[a], by_sched[b]] if rep % 2 == 0 else [by_sched[b], by_sched[a]]
        ordered.extend(pair)
    return ordered


@dataclass
class CompletedLedger:
    """Tracks which run_ids have already completed, for idempotent
    resume. Persisted as a JSON Lines file: one {"run_id": ..., "status":
    ...} object per line, matching the write-once-append discipline of
    `calibration_common.JsonlWriter`."""
    path: Path
    _completed: Dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self._completed = {}
        if self.path.exists():
            with open(self.path) as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    row = json.loads(line)
                    self._completed[row["run_id"]] = row["status"]

    def is_completed(self, run_id: str) -> bool:
        return self._completed.get(run_id) == "success"

    def record(self, run_id: str, status: str) -> None:
        self._completed[run_id] = status
        with open(self.path, "a") as f:
            f.write(json.dumps({"run_id": run_id, "status": status}) + "\n")


def filter_pending(units: List[RunUnit], ledger: CompletedLedger) -> List[RunUnit]:
    """Resume protection: drop run units already marked successful in the
    ledger. Units that previously failed/errored are retried (not
    silently skipped)."""
    return [u for u in units if not ledger.is_completed(u.run_id())]


def unique_output_namespace(base_dir: Path, run_id: str) -> Path:
    """One directory per run unit, named by its stable run_id (never by
    execution order or timestamp), so re-running never collides with a
    prior attempt's output."""
    safe = run_id.replace("::", "__")
    ns = base_dir / safe
    ns.mkdir(parents=True, exist_ok=True)
    return ns


@dataclass(frozen=True)
class WarmupMeasurementSplit:
    warmup_requests: int
    measurement_requests: int

    def total(self) -> int:
        return self.warmup_requests + self.measurement_requests
