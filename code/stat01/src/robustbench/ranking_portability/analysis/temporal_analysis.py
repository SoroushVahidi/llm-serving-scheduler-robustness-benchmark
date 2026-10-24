"""Temporal / OOD ranking-portability design
(docs/RANKING_PORTABILITY_ANALYSIS_PLAN.md §D). Three source-specific
chronology treatments, never conflated:

- BurstGPT: native timestamps -> EARLY/MIDDLE/LATE terciles (primary
  split) or EARLY/LATE bisect (sensitivity split).
- Bailian/Qwen: relative-only ordering -- any finding must be labeled
  `RELATIVE_CHRONOLOGY_ONLY`, never presented as calendar-dated.
- Azure 2024: calendar-anchored split within its own collection window
  (this project's dedicated temporal-OOD axis, kept separate from
  provider/domain OOD).

Splitting logic only; the actual tau/reversal comparison between splits
reuses `ranking_analysis.compare_conditions` unchanged (temporal
portability is analyzed with the identical toolkit as cross-source
portability, source held fixed).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Mapping, Sequence

from .contract import BAILIAN_TEMPORAL_LABEL


def _sorted_windows_by_time(window_timestamps: Mapping[str, float]) -> List[str]:
    return [w for w, _ in sorted(window_timestamps.items(), key=lambda kv: (kv[1], kv[0]))]


def split_burstgpt_tercile(window_timestamps: Mapping[str, float]) -> Dict[str, List[str]]:
    ordered = _sorted_windows_by_time(window_timestamps)
    n = len(ordered)
    b1 = n // 3
    b2 = 2 * n // 3
    return {"EARLY": ordered[:b1], "MIDDLE": ordered[b1:b2], "LATE": ordered[b2:]}


def split_burstgpt_bisect(window_timestamps: Mapping[str, float]) -> Dict[str, List[str]]:
    ordered = _sorted_windows_by_time(window_timestamps)
    mid = len(ordered) // 2
    return {"EARLY": ordered[:mid], "LATE": ordered[mid:]}


@dataclass
class RelativeChronologySplit:
    chronology_type: str
    groups: Dict[str, List[str]]


def split_bailian_relative(window_relative_order: Mapping[str, int]) -> RelativeChronologySplit:
    """`window_relative_order`: {window_id: within-trace relative order
    index} -- NOT a calendar timestamp. Bisected into two halves; any
    downstream finding must carry the `RELATIVE_CHRONOLOGY_ONLY` label,
    never be presented as calendar-dated."""
    ordered = [w for w, _ in sorted(window_relative_order.items(), key=lambda kv: (kv[1], kv[0]))]
    mid = len(ordered) // 2
    return RelativeChronologySplit(
        chronology_type=BAILIAN_TEMPORAL_LABEL,
        groups={"EARLY_RELATIVE": ordered[:mid], "LATE_RELATIVE": ordered[mid:]},
    )


def split_azure_calendar(
    window_timestamps: Mapping[str, float],
    *,
    boundary_epoch_seconds: float,
) -> Dict[str, List[str]]:
    """Calendar-anchored split of Azure-2024 windows around an explicit
    boundary timestamp (the project's frozen collection-window boundary,
    e.g. 2024-05-10..2024-05-19, docs/EVIDENCE_INDEPENDENCE_PLAN.md) --
    the boundary is a caller-supplied parameter, never invented here, so
    this function cannot silently assume a date range that drifts from
    the frozen provenance doc."""
    before = [w for w, t in window_timestamps.items() if t < boundary_epoch_seconds]
    after = [w for w, t in window_timestamps.items() if t >= boundary_epoch_seconds]
    return {
        "BEFORE_BOUNDARY": sorted(before),
        "AT_OR_AFTER_BOUNDARY": sorted(after),
    }


def filter_rows_to_windows(rows: Sequence[Mapping], window_ids: Sequence[str]) -> List[Mapping]:
    window_set = set(window_ids)
    return [r for r in rows if r["window_id"] in window_set]
