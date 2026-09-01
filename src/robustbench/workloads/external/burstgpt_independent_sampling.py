"""BurstGPT Stage-0 independent window sampling.

Background (see docs/OVERLAP_LEDGER.md, docs/EVIDENCE_INDEPENDENCE_PLAN.md,
docs/CLAIM_BOUNDARIES.md): LLM 2026's `public_replay_load_scaling_v1/v2`
experiment consumed 20 BurstGPT windows (`WINDOW_SIZE=200` requests each) as
one third of its 60 canonical public-trace windows. This project's own
Stage-0 pilot must draw a demonstrably different BurstGPT sample, and must
not overclaim guaranteed non-overlap it cannot verify.

Independence audit performed 2026-09-01 (this session): the exact module
that produced LLM 2026's 20 BurstGPT windows
(`llmserveopt.policy_separation.public_trace_replay_v1.build_all_scenarios()`,
per docs/EVIDENCE_INDEPENDENCE_PLAN.md) does not exist in any locally
reachable checkout of that repository (read-only search across every
`llm-serving-heuristic-evolution*` checkout and
`integration-swissai-report-repair-20260809` on the Wulver cluster; grep for
`public_trace_replay_v1` / `PUBLIC_REPLAY_LOAD_SCALING` returned zero hits
outside documentation references). **Conclusion: the exact historical
BurstGPT row/window coordinates are not recoverable from anything available
to this project.**

DISCLOSURE (do not overclaim): given the above, this sampler cannot
guarantee byte-for-byte non-overlap with LLM 2026's 20 windows. What it does
guarantee, by construction, and what this project claims -- no more --:

1. **Different source file.** LLM 2026's BurstGPT ingestion pipeline (per
   its own provenance manifests) most plausibly drew from the first/primary
   released file in file-name order; this sampler deliberately draws from
   `BurstGPT_without_fails_2.csv`, the second of the three released
   without-fails files, never file 1.
2. **Different, large row offset.** Sampling starts only after skipping the
   first `BURSTGPT_OFFSET_VALID_ROWS` valid rows of that file (currently
   500,000 -- roughly a third of file 2's ~1.4-4M rows), far past any
   offset-0-anchored naive sampling a prior 20-window draw is likely to have
   used.
3. **Different window count and size target.** This project draws exactly
   10 windows (not 20) of 200 requests each, using a different, freshly
   frozen deterministic seed (`BURSTGPT_STAGE0_SEED`) and an independently
   documented stride rule (`stage0_window_selection.select_stride_windows`),
   never LLM 2026's `public_trace_replay_v1` code or parameters.

This is "different file region + different file + different seed +
different window-count target" separation, not a verified zero-overlap
guarantee. Any residual coincidental overlap with LLM 2026's 20 windows
cannot be ruled out and is disclosed here rather than hidden.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import List

from .adapters.burstgpt import BurstGPTAdapter
from .schema import ExternalWorkloadRecord
from .stage0_window_selection import WindowSelectionReport, select_stride_windows

STAGE0_BURSTGPT_SOURCE_FILE = "BurstGPT_without_fails_2.csv"
BURSTGPT_STAGE0_SEED = 20260901
BURSTGPT_OFFSET_VALID_ROWS = 500_000
BURSTGPT_WINDOW_SIZE = 200
BURSTGPT_N_WINDOWS = 10

INDEPENDENCE_DISCLOSURE = (
    "BurstGPT Stage-0 windows are drawn from BurstGPT_without_fails_2.csv "
    "(not file 1), starting 500,000 valid rows into the file, using a fresh "
    "seed (20260901) and this project's own stride-window selection rule "
    "(stage0_stride_window_selection_v1), never LLM 2026's "
    "public_trace_replay_v1 code or its 20-window/{1,2,4,8,16,32,64,128} "
    "design. The exact historical LLM 2026 BurstGPT row coordinates could "
    "not be recovered from any locally reachable checkout of that "
    "repository (searched 2026-09-01), so byte-for-byte non-overlap cannot "
    "be verified or guaranteed -- only 'different file + different large "
    "offset + different seed + different window-count target' separation is "
    "claimed."
)


@dataclass
class BurstGPTStage0Manifest:
    source_file: str
    seed: int
    offset_valid_rows: int
    window_size: int
    n_windows: int
    independence_disclosure: str
    selection_report: dict

    def to_dict(self) -> dict:
        return asdict(self)


def build_burstgpt_stage0_windows(
    path: Path,
) -> tuple[List[List[ExternalWorkloadRecord]], BurstGPTStage0Manifest]:
    """Build the 10 frozen Stage-0 BurstGPT windows from the real
    `BurstGPT_without_fails_2.csv` file at `path`. `path.name` must match
    `STAGE0_BURSTGPT_SOURCE_FILE` -- this is checked, not assumed, so a
    caller cannot silently point this at the wrong file."""
    if path.name != STAGE0_BURSTGPT_SOURCE_FILE:
        raise ValueError(
            f"Stage-0 BurstGPT sampling is frozen to {STAGE0_BURSTGPT_SOURCE_FILE!r}, "
            f"got path with filename {path.name!r}"
        )
    adapter = BurstGPTAdapter()
    windows, report = select_stride_windows(
        lambda: adapter.stream_records(path),
        window_size=BURSTGPT_WINDOW_SIZE,
        n_windows=BURSTGPT_N_WINDOWS,
        offset_valid_rows=BURSTGPT_OFFSET_VALID_ROWS,
        seed=BURSTGPT_STAGE0_SEED,
    )
    manifest = BurstGPTStage0Manifest(
        source_file=STAGE0_BURSTGPT_SOURCE_FILE,
        seed=BURSTGPT_STAGE0_SEED,
        offset_valid_rows=BURSTGPT_OFFSET_VALID_ROWS,
        window_size=BURSTGPT_WINDOW_SIZE,
        n_windows=BURSTGPT_N_WINDOWS,
        independence_disclosure=INDEPENDENCE_DISCLOSURE,
        selection_report=report.to_dict(),
    )
    return windows, manifest
