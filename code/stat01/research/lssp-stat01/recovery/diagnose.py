"""Read-only, deterministic diagnosis; never invokes a campaign runner."""
import argparse
import hashlib
import json
import sys
from pathlib import Path
from fractions import Fraction


def bh_variants(ps):
    """Compare three frozen floating expressions with exact bootstrap-grid BH.

    The exact comparator is diagnostic, not a silently substituted procedure.
    B=2000 two-sided historical tail probabilities lie on the 1/1000 grid.
    Require exact reconstruction of each stored float; no tolerance is used.
    """
    m = len(ps)
    order = sorted(range(m), key=lambda j: ps[j])
    counts = [round(p * 1000) for p in ps]
    if any(n / 1000 != p for n, p in zip(counts, ps)):
        raise ValueError('not an exactly reconstructible B=2000 historical p-value')
    hits = {
        'production': lambda j, rank: ps[j] <= .05 * rank / m,
        'reference': lambda j, rank: ps[j] * m <= .05 * rank,
        'historical': lambda j, rank: ps[j] <= (rank / m) * .05,
        'exact_bootstrap': lambda j, rank: counts[j] * 20 * m <= 1000 * rank,
    }
    answer = {}
    for name, accept in hits.items():
        k = max([rank for rank, j in enumerate(order, 1) if accept(j, rank)] + [0])
        selected = set(order[:k])
        answer[name] = [j in selected for j in range(m)]
    return answer


def boundary_audit():
    """All attainable exact-BH equality boundaries for family sizes 1..165."""
    excluded = {name: [] for name in ('production', 'reference', 'historical')}
    equalities = 0
    for m in range(1, 166):
        for rank in range(1, m + 1):
            p = Fraction(rank, 20 * m)
            if (p * 1000).denominator != 1:
                continue
            equalities += 1
            x = float(p)
            checks = dict(production=x <= .05 * rank / m,
                          reference=x * m <= .05 * rank,
                          historical=x <= (rank / m) * .05)
            for name, ok in checks.items():
                if not ok:
                    excluded[name].append(dict(m=m, rank=rank, p=str(p), float_p=x))
    return dict(equalities=equalities, falsely_excluded=excluded)


def reproduce(code, sid=11, replicate=6628):
    # Use the supplied frozen deployment and its pinned Python environment.
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(Path(code).resolve()))
    from design import SCENARIOS, FAMILY
    from experiment import study
    from reference import validate_record
    y, mask, record = study(sid, replicate)
    try:
        validate_record(SCENARIOS[sid], y, mask, record, sid, replicate)
    except ValueError as exc:
        failure = str(exc)
    else:
        raise AssertionError('the frozen failure did not reproduce')
    indices = [i for i, yes in enumerate(record['historical']['eligible']) if yes]
    result = record['methods']['historical_screened_BH']
    ps = [result['p'][i] for i in indices]
    variants = bh_variants(ps)
    observed = [result['reject'][i] for i in indices]
    variants = {name: [flag and record['historical']['supported'][i]
                       for flag, i in zip(flags, indices)]
                for name, flags in variants.items()}
    assert observed == variants['production']
    differences = [i for j, i in enumerate(indices)
                   if variants['production'][j] != variants['reference'][j]]
    return dict(scenario=sid, scenario_name=SCENARIOS[sid]['name'], replicate=replicate,
                error=failure, all_observed=bool(mask.all()), eligible_indices=indices,
                eligible_p=ps, decisions=variants, differences=differences,
                families=[FAMILY[i] for i in differences],
                raw_y_sha256=hashlib.sha256(y.tobytes()).hexdigest(),
                raw_mask_sha256=hashlib.sha256(mask.tobytes()).hexdigest())


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--frozen-code', type=Path)
    args = parser.parse_args()
    result = boundary_audit()
    if args.frozen_code:
        result['reproducer'] = reproduce(args.frozen_code)
    print(json.dumps(result, indent=2, sort_keys=True))
