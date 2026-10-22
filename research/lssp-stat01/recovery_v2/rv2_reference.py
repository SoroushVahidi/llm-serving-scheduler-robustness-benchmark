"""Independent referee: no production-method, generator, or design imports.

Binary64 contracts are emulated by exact arithmetic and explicit rounding.
Mathematical corrections use adjusted p-values, not production critical ranks.
"""
from fractions import Fraction as Q
from functools import lru_cache
from itertools import combinations
import math
import numpy as np
from reference import labels, require

NAMES = ('historical_screened_BH', 'historical_full_BH', 'historical_plus1_BY',
         'iid_t_Holm', 'cluster_t_Holm', 'oracle_normal_Holm',
         'group_bootstrap_BY', 'bounded_Hoeffding_Holm')
EXTRA = ('legacy_source_screened_BH',) + tuple('exact_' + n for n in NAMES)


@lru_cache(None)
def binary_thresholds(m, kind, historical=False):
    alpha = Q.from_float(.05)
    if not m:
        return ()
    if historical:
        return tuple(float(Q.from_float(float(Q(r, m))) * alpha) for r in range(1, m + 1))
    if kind == 'holm':
        return tuple(float(alpha / (m - r + 1)) for r in range(1, m + 1))
    # CPython 3.12's compensated built-in sum is part of the frozen numerical
    # environment. A naive left fold does NOT reproduce that implementation.
    # Terms are independently rounded exact reciprocals; no production helper.
    h = sum(float(Q(1, k)) for k in range(1, m + 1)) if kind == 'by' else 1.0
    q = Q.from_float(float(alpha / Q.from_float(h)))
    return tuple(float(Q.from_float(float(q * r)) / m) for r in range(1, m + 1))


def binary_oracle(ps, kind, historical=False):
    # Historical NaNs do not consume ranks; frozen campaign input forbids them.
    order = sorted((j for j in range(len(ps)) if ps[j] == ps[j]), key=lambda j: ps[j])
    thresholds = binary_thresholds(len(order), kind, historical)
    hits = [ps[j] <= t for j, t in zip(order, thresholds)]
    if kind == 'holm':
        cutoff = next((j for j, hit in enumerate(hits) if not hit), len(hits))
    else:
        cutoff = max([j + 1 for j, hit in enumerate(hits) if hit] + [0])
    chosen = set(order[:cutoff])
    return [j in chosen for j in range(len(ps))]


def exact_oracle(ps, kind):
    """Independent adjusted-p algorithm with rational cumulative min/max."""
    order = sorted(range(len(ps)), key=lambda j: ps[j])
    m = len(order)
    adjusted = [Q(1)] * m
    if kind == 'holm':
        value = Q(0)
        for rank, j in enumerate(order, 1):
            value = max(value, ps[j] * (m - rank + 1))
            adjusted[j] = value
    else:
        factor = sum((Q(1, k) for k in range(1, m + 1)), Q(0)) if kind == 'by' else Q(1)
        value = Q(1)
        for rank in range(m, 0, -1):
            j = order[rank - 1]
            value = min(value, ps[j] * m * factor / rank)
            adjusted[j] = value
    return [p <= Q(1, 20) for p in adjusted]


def referee_probabilities(rec, name):
    # Independent finite-grid inversion by an integer search around the dyadic
    # quotient; acceptance requires exact reconstruction, never a tolerance.
    values = rec['methods'][name]['p']
    if name == 'historical_plus1_BY':
        values = rec['methods']['historical_full_BH']['p']
    finite = name.startswith('historical_') or name == 'group_bootstrap_BY'
    if not finite:
        return [Q(*float(p).as_integer_ratio()) for p in values]
    denominator = 2001 if name == 'group_bootstrap_BY' else 2000
    answer = []
    for j, p in enumerate(values):
        if p == 1:
            value = Q(1)
        else:
            ratio = Q.from_float(float(p)) * denominator / 2
            low = ratio.numerator // ratio.denominator
            candidates = [k for k in (low, low + 1) if 2 * float(Q(k, denominator)) == p]
            require(len(candidates) == 1, 'independent finite probability reconstruction')
            require(denominator != 2001 or candidates[0] >= 1, 'plus-one bootstrap count')
            value = Q(2 * candidates[0], denominator)
        if name == 'historical_plus1_BY':
            value = min(Q(1), (2000 * value + 2) / 2001) if rec['historical']['eligible'][j] else Q(1)
        answer.append(value)
    return answer


def expected_rejections(rec, method, interpretation):
    indices = ([j for j, flag in enumerate(rec['historical']['eligible']) if flag]
               if method == 'historical_screened_BH' else list(range(165)))
    kind = ('by' if method in ('historical_plus1_BY', 'group_bootstrap_BY')
            else 'bh' if method.startswith('historical_') else 'holm')
    if interpretation == 'exact':
        values = referee_probabilities(rec, method)
        chosen = exact_oracle([values[j] for j in indices], kind)
    else:
        chosen = binary_oracle([rec['methods'][method]['p'][j] for j in indices], kind,
                               historical=interpretation == 'legacy')
    result = [False] * 165
    for j, flag in zip(indices, chosen):
        result[j] = flag and (rec['historical']['supported'][j] if method.startswith('historical_') else True)
    return result


def validate_endpoints(spec, rec, result, historical):
    reject = result['reject']
    count = sum(reject)
    expected = {}
    for target in ('practical', 'sign'):
        truth = rec['truth'][target]
        false = sum(a and not b for a, b in zip(reject, truth))
        alt, null = sum(truth), len(truth) - sum(truth)
        expected.update({'fdp_' + target: false / max(count, 1),
                         'fwer_' + target: float(false > 0),
                         'null_fraction_' + target: false / null if null else None,
                         'power_' + target: (count - false) / alt if alt else None})
    ci = result['ci']
    candidates, empirical, truth = result['candidate_sets'], rec['empirical_top_sets'], rec['truth']
    selected = []
    family = [(s, t, a, b) for s, t in combinations(range(3), 2) for a, b in combinations(range(11), 2)]
    if historical:
        for item in rec['historical']['intervals']:
            s, t, a, b = family[item['h']]
            for source, bounds in zip((s, t), item['ci']):
                selected.append(float(bounds[0] <= spec['mu'][source][a] - spec['mu'][source][b] <= bounds[1]))
    expected.update(ci_available=float(ci is not None),
        ci_coverage=None if ci is None else float(ci[0] <= truth['fixed_difference'] <= ci[1]),
        topset_coverage=None if candidates is None else float(all(set(t) <= set(c) for t, c in zip(truth['top_sets'], candidates))),
        topset_size_fraction=None if candidates is None else sum(map(len, candidates)) / 33,
        empirical_topset_coverage=float(all(set(t) <= set(c) for t, c in zip(truth['top_sets'], empirical))),
        id_correct_fraction=sum(bool(c) and min(c) in t for t, c in zip(truth['top_sets'], empirical)) / 3,
        selected_available=float(bool(selected)), selected_coverage=sum(selected) / len(selected) if selected else None)
    require(result['endpoints'] == expected, 'independent complete endpoint reconstruction')
    require(all(v is None or (math.isfinite(v) and 0 <= v <= 1) for v in expected.values()), 'endpoint domain')


def validate(spec, y, mask, rec, secondary, sid, replicate, namespace=1):
    require((rec['scenario'], rec['replicate'], rec['seed_namespace']) == (sid, replicate, namespace), 'study identity')
    require(y.shape == mask.shape == (3, spec['n'], 11) and np.isfinite(y).all(), 'raw shape/values')
    require(mask.dtype == np.bool_, 'mask type')
    truth = labels(spec)
    require(all(rec['truth'][key] == value for key, value in truth.items()), 'independent truth')
    require(rec['truth']['fixed_difference'] == spec['mu'][0][0] - spec['mu'][0][1], 'contrast truth')
    if spec['missing'] == 'complete':
        require(mask.all(), 'complete missingness')
    if spec['missing'] == 'selective':
        expected = np.ones_like(mask)
        expected[0, :, 0] = y[0, :, 0] >= spec['mu'][0][0]
        expected[1, :, 1] = y[1, :, 1] >= spec['mu'][1][1]
        require(np.array_equal(mask, expected), 'selective missingness')
    if spec['distributions'] == ['uniform'] * 3:
        require(np.all((0 <= y) & (y <= 1)), 'bounded support')
    require(set(rec['methods']) == set(NAMES) and set(secondary) == set(EXTRA), 'method inventory')
    for name in NAMES:
        result = rec['methods'][name]
        require(len(result['p']) == len(result['reject']) == 165, 'complete family')
        require(all(math.isfinite(p) and 0 <= p <= 1 for p in result['p']), 'p-value domain')
        require(result['reject'] == expected_rejections(rec, name, 'frozen'), 'independent frozen-binary64 disagreement: ' + name)
        validate_endpoints(spec, rec, result, name.startswith('historical_'))
    for name in EXTRA:
        result = secondary[name]
        base = 'historical_screened_BH' if name == EXTRA[0] else name[6:]
        require(result['base_method'] == base and result['registration'] == 'POST_DIAGNOSIS_2026_10_22', 'secondary provenance')
        interpretation = 'legacy' if name == EXTRA[0] else 'exact'
        require(result['probability_semantics'] == ('FROZEN_HISTORICAL_BINARY64' if interpretation == 'legacy'
                else 'EXACT_BOOTSTRAP_OR_REPRESENTED_DYADIC'), 'probability semantics')
        require(result['reject'] == expected_rejections(rec, base, interpretation), 'independent secondary disagreement: ' + name)
        for field in ('ci', 'candidate_sets', 'assumption_status'):
            require(result[field] == rec['methods'][base][field], 'unchanged secondary field: ' + field)
        validate_endpoints(spec, rec, result, base.startswith('historical_'))
    return True
