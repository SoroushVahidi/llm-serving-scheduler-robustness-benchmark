from __future__ import annotations

from pathlib import Path

import pytest

from robustbench.workloads.external.burstgpt_independent_sampling import (
    STAGE0_BURSTGPT_SOURCE_FILE,
    build_burstgpt_stage0_windows,
)


def test_rejects_wrong_filename(tmp_path):
    wrong = tmp_path / "BurstGPT_without_fails_1.csv"
    wrong.write_text("Timestamp,Model,Request tokens,Response tokens,Total tokens,Session ID\n")
    with pytest.raises(ValueError):
        build_burstgpt_stage0_windows(wrong)


def test_accepts_correct_filename_but_fails_on_too_small_fixture(tmp_path):
    # Confirms the frozen offset/window-count actually gets applied (raises
    # ValueError for an undersized file) rather than silently degrading.
    correct = tmp_path / STAGE0_BURSTGPT_SOURCE_FILE
    correct.write_text(
        "Timestamp,Model,Request tokens,Response tokens,Total tokens,Session ID\n"
        "0.0,GPT-4,10,10,20,s1\n"
    )
    with pytest.raises(ValueError):
        build_burstgpt_stage0_windows(correct)
