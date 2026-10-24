"""Result-blindness guard (§Q of the analysis-prefreeze task).

No function in this analysis package resolves a default path into the
live campaign-results tree
(`artifacts/campaign_results/<freeze_prefix16>/shard_*.json`, written by
`scripts/ranking_portability/run_phase12_campaign_shard.py --execute`).
Every analysis entry point requires an explicit input path from its
caller; this module's one job is to make "explicit" enforceable rather
than a convention someone can forget.

PHASE12_ANALYSIS_PREFREEZE_RESULT_BLIND = YES
"""
from __future__ import annotations

from pathlib import Path

# The exact live-output root used by the Phase-12C shard runner
# (scripts/ranking_portability/run_phase12_campaign_shard.py,
# CAMPAIGN_OUTPUT_ROOT). Duplicated here (not imported) deliberately --
# this guard module must keep working even if the runner script is
# refactored, and importing it would pull the real execution machinery
# into every analysis test's import graph.
LIVE_CAMPAIGN_OUTPUT_ROOT_SUFFIX = ("artifacts", "campaign_results")


class LiveCampaignPathBlocked(RuntimeError):
    """Raised when analysis-prefreeze code is about to read from what
    looks like the real, live campaign-results directory. This task must
    never open real Phase-12 scientific output, even accidentally."""


def assert_not_live_campaign_path(path: Path, *, allow_live: bool = False) -> None:
    """Raises `LiveCampaignPathBlocked` if `path` resolves under a
    directory ending in `artifacts/campaign_results`, unless the caller
    passes `allow_live=True` explicitly (production consolidation, run
    only outside this prefreeze task, is the sole intended caller of
    that override -- test code and this task's own scripts never set it)."""
    if allow_live:
        return
    parts = tuple(p.lower() for p in path.resolve().parts)
    suffix = LIVE_CAMPAIGN_OUTPUT_ROOT_SUFFIX
    for i in range(len(parts) - len(suffix) + 1):
        if parts[i:i + len(suffix)] == suffix:
            raise LiveCampaignPathBlocked(
                f"Refusing to read {path} -- resolves under a live "
                f"'{'/'.join(suffix)}' directory. This analysis-prefreeze "
                "task must consume only fabricated fixtures under an "
                "explicit temp/test directory (see "
                "docs/RANKING_PORTABILITY_PHASE12_ANALYSIS_PREFREEZE.md)."
            )
