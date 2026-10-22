"""Post-diagnosis comparisons; the original eight procedures are not edited."""
from copy import deepcopy
from fractions import Fraction
from functools import lru_cache
import math

from design import METHODS

LEGACY = 'legacy_source_screened_BH'
EXACT = tuple('exact_' + name for name in METHODS)
SECONDARY = (LEGACY,) + EXACT
ALL_METHODS = tuple(METHODS) + SECONDARY


def legacy_bh(ps, q=.05):
    """Frozen historical scalar evaluation order, including NaN rank omission."""
    indexed = [(p, j) for j, p in enumerate(ps) if p == p]
    indexed.sort(key=lambda item: item[0])
    m = len(indexed)
    cutoff = 0
    for rank, (p, _) in enumerate(indexed, 1):
        if p <= (rank / m) * q:
            cutoff = rank
    selected = {j for _, j in indexed[:cutoff]}
    return [j in selected for j in range(len(ps))]


def bootstrap_fraction(p, denominator, multiplier):
    """Invert a known finite-bootstrap grid only on exact float reconstruction."""
    if not math.isfinite(p) or not 0 <= p <= 1:
        raise ValueError('p-value domain')
    if p == 1:
        return Fraction(1)
    count = round(p * denominator / multiplier)
    if denominator == 2001 and count < 1:
        raise ValueError('plus-one bootstrap count')
    if multiplier * (count / denominator) != p:
        raise ValueError('finite-bootstrap grid mismatch')
    return Fraction(multiplier * count, denominator)


def exact_probabilities(record, method):
    ps = record['methods'][method]['p']
    if method in ('historical_screened_BH', 'historical_full_BH'):
        return [bootstrap_fraction(p, 2000, 2) for p in ps]
    if method == 'historical_plus1_BY':
        # Recover ideal (B*p + 2)/(B+1) from original integer tail counts;
        # do not rationalize its already rounded intermediate float result.
        base = record['methods']['historical_full_BH']['p']
        return [min(Fraction(1), (2000 * bootstrap_fraction(p, 2000, 2) + 2) / 2001)
                if eligible else Fraction(1)
                for p, eligible in zip(base, record['historical']['eligible'])]
    if method == 'group_bootstrap_BY':
        return [bootstrap_fraction(p, 2001, 2) for p in ps]
    if any(not math.isfinite(p) or not 0 <= p <= 1 for p in ps):
        raise ValueError('analytic p-value domain')
    # This is an exact comparison of the represented binary64 approximation,
    # not a claim to recover an infinitely precise distribution-tail probability.
    return [Fraction.from_float(float(p)) for p in ps]


@lru_cache(None)
def critical_values(m, kind):
    if kind not in ('bh', 'by', 'holm'):
        raise ValueError('unknown correction')
    if not m:
        return ()
    if kind == 'holm':
        return tuple(Fraction(1, 20 * (m - rank + 1)) for rank in range(1, m + 1))
    harmonic = sum((Fraction(1, k) for k in range(1, m + 1)), Fraction()) if kind == 'by' else Fraction(1)
    return tuple(Fraction(rank, 20 * m) / harmonic for rank in range(1, m + 1))


def exact_adjust(ps, kind):
    """Step-up BH/BY or step-down Holm with inclusive rational comparisons."""
    if any(p < 0 or p > 1 for p in ps):
        raise ValueError('rational p-value domain')
    order = sorted(range(len(ps)), key=lambda j: ps[j])
    cutoff = 0
    for rank, (j, threshold) in enumerate(zip(order, critical_values(len(ps), kind)), 1):
        if ps[j] <= threshold:
            cutoff = rank
        elif kind == 'holm':
            break
    selected = set(order[:cutoff])
    return [j in selected for j in range(len(ps))]


def update_decision_endpoints(base, reject, truth):
    result = deepcopy(base)
    result.pop('p')  # p-value provenance is the explicitly named original method.
    result['reject'] = reject
    r = sum(reject)
    for target in ('practical', 'sign'):
        alt = truth[target]
        false = sum(flag and not yes for flag, yes in zip(reject, alt))
        nulls, alternatives = len(alt) - sum(alt), sum(alt)
        result['endpoints'].update({
            'fdp_' + target: false / max(r, 1),
            'fwer_' + target: float(false > 0),
            'null_fraction_' + target: false / nulls if nulls else None,
            'power_' + target: (r - false) / alternatives if alternatives else None})
    return result


def derive(record):
    additions = {}
    for name in SECONDARY:
        method = 'historical_screened_BH' if name == LEGACY else name[len('exact_'):]
        base = record['methods'][method]
        screened = method == 'historical_screened_BH'
        indices = ([j for j, flag in enumerate(record['historical']['eligible']) if flag]
                   if screened else list(range(165)))
        if name == LEGACY:
            flags = legacy_bh([base['p'][j] for j in indices])
        else:
            ps = exact_probabilities(record, method)
            kind = ('by' if method in ('historical_plus1_BY', 'group_bootstrap_BY')
                    else 'bh' if method.startswith('historical_') else 'holm')
            flags = exact_adjust([ps[j] for j in indices], kind)
        reject = [False] * 165
        for j, flag in zip(indices, flags):
            reject[j] = flag and (record['historical']['supported'][j] if method.startswith('historical_') else True)
        result = update_decision_endpoints(base, reject, record['truth'])
        result.update(base_method=method, registration='POST_DIAGNOSIS_2026_10_22',
                      probability_semantics=('FROZEN_HISTORICAL_BINARY64' if name == LEGACY
                                             else 'EXACT_BOOTSTRAP_OR_REPRESENTED_DYADIC'))
        additions[name] = result
    return additions
