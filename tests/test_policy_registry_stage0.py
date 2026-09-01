"""Regression test: all six frozen Stage-0 policies must be constructible
via a single resolver. Found during Stage-0 harness construction that
`vllm_faithful`/`sarathi_faithful` were never added to ANY registry dict
(despite being mature, extensively-used-elsewhere policy classes), and
`kv_constrained_online` lives in `_POLICY_LIBRARY_V2_REGISTRY`, not
`_REGISTRY` -- so the plain `make_policy()` Stage-0's runner originally
called could resolve only 3 of the 6 frozen policy names."""
from __future__ import annotations

import pytest

from robustbench.policies.registry import (
    FAITHFUL_POLICY_NAMES,
    make_policy,
    make_policy_any,
)
from robustbench.stage0.cell import STAGE0_POLICIES


def test_all_six_frozen_stage0_policies_resolve_via_make_policy_any():
    for name in STAGE0_POLICIES:
        policy = make_policy_any(name)
        assert policy is not None


def test_faithful_policy_names_include_vllm_and_sarathi():
    assert "vllm_faithful" in FAITHFUL_POLICY_NAMES
    assert "sarathi_faithful" in FAITHFUL_POLICY_NAMES


def test_make_policy_any_unknown_name_raises_keyerror():
    with pytest.raises(KeyError):
        make_policy_any("not_a_real_policy")


def test_make_policy_unchanged_for_pre_existing_baseline_names():
    """Backward compatibility: make_policy()'s existing behavior for names
    already in _REGISTRY must be untouched by this fix."""
    assert make_policy("fifo") is not None
    with pytest.raises(KeyError):
        make_policy("vllm_faithful")  # still NOT resolvable via plain make_policy() -- unchanged
