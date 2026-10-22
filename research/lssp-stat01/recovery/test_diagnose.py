"""Tests expose the ambiguity; they do not bless a replacement procedure."""
from fractions import Fraction
import itertools
import math
import json
from pathlib import Path

import pytest

from diagnose import bh_variants, boundary_audit


def rational_oracle(ps):
    # Independently derive BH adjusted p-values via reverse cumulative minima.
    order = sorted(range(len(ps)), key=lambda j: ps[j])
    adjusted = [Fraction(1)] * len(ps)
    running = Fraction(1)
    for rank in range(len(ps), 0, -1):
        j = order[rank - 1]
        running = min(running, Fraction(str(ps[j])) * len(ps) / rank)
        adjusted[j] = running
    return [p <= Fraction(1, 20) for p in adjusted]


def test_original_failure_minimal_equal_p_family():
    result = bh_variants([.05] * 43)
    assert result['production'] == [False] * 43
    for name in ('reference', 'historical', 'exact_bootstrap'):
        assert result[name] == [True] * 43


def test_archived_exact_reproducer_vectors():
    fixture = json.loads((Path(__file__).parent / 'evidence/failing-study.json').read_text())
    result = bh_variants(fixture['eligible_p'])
    for name in ('production', 'reference', 'historical'):
        assert result[name] == fixture[name + '_reject']
    assert result['exact_bootstrap'] == rational_oracle(fixture['eligible_p'])
    assert result['exact_bootstrap'] == result['reference']
    assert [fixture['eligible_indices'][j] for j, (a, b) in enumerate(zip(
        result['production'], result['reference'])) if a != b] == [47]


def test_historical_and_reference_are_not_exact_bh_either():
    ps = [.001] * 6 + [.035] + [1.] * 3
    result = bh_variants(ps)
    assert not result['historical'][6]
    assert result['exact_bootstrap'][6]
    ps = [.001] * 34 + [.035] + [1.] * 15
    result = bh_variants(ps)
    assert not result['reference'][34]
    assert result['exact_bootstrap'][34]


def test_exhaustive_equality_audit():
    audit = boundary_audit()
    assert {k: len(v) for k, v in audit['falsely_excluded'].items()} == {
        'production': 8, 'reference': 5, 'historical': 19}


def test_independent_adjusted_p_oracle_and_tie_permutations():
    for size in range(5):
        for values in itertools.product([0., .025, .05, .051, 1.], repeat=size):
            assert bh_variants(values)['exact_bootstrap'] == rational_oracle(values)


def test_no_rounding_tolerance_or_out_of_grid_coercion():
    for p in [math.nextafter(.05, 0), math.nextafter(.05, 1), .0005]:
        with pytest.raises(ValueError, match='exactly reconstructible'):
            bh_variants([p])


def test_step_up_not_sequential_stop():
    assert bh_variants([.03, .04])['exact_bootstrap'] == [True, True]
    assert bh_variants([])['exact_bootstrap'] == []
