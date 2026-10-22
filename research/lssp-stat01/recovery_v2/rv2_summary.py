"""Preserved original looks plus explicitly post-diagnosis 17-method looks."""
import math
import numpy as np
from design import SCENARIOS, METHODS, LOOKS
from experiment import ENDPOINTS
from precision import summarize_stats as original_summary
from rv2_methods import ALL_METHODS

EXPANDED_DELTA = .05 / (18 * 17 * 16 * 5)


def sufficient(records, additions):
    result = {}
    for name in ALL_METHODS:
        result[name] = {}
        for field in ENDPOINTS:
            values = [(r['methods'] if name in METHODS else a)[name]['endpoints'][field]
                      for r, a in zip(records, additions)]
            xs = np.array([x for x in values if x is not None])
            average = float(xs.mean()) if len(xs) else 0.
            result[name][field] = dict(n=len(xs), mean=average,
                                      m2=float(np.sum((xs - average) ** 2)))
    return result


def merge(left, right):
    if left is None:
        return right
    result = {}
    for method in ALL_METHODS:
        result[method] = {}
        for endpoint in ENDPOINTS:
            a, b = left[method][endpoint], right[method][endpoint]
            n = a['n'] + b['n']
            difference = b['mean'] - a['mean']
            result[method][endpoint] = dict(n=n, mean=a['mean'] + difference*b['n']/n if n else 0.,
                m2=a['m2']+b['m2']+difference**2*a['n']*b['n']/n if n else 0.)
    return result


def summarize(sums, n, spec):
    original = original_summary({m: sums[m] for m in METHODS}, n, spec)
    methods = {}
    for name in ALL_METHODS:
        fields = {}
        for endpoint, ss in sums[name].items():
            size = ss['n']
            mean = ss['mean'] if size else None
            variance = ss['m2'] / (size - 1) if size > 1 else None
            log = math.log(4 / EXPANDED_DELTA)
            half = math.sqrt(2*variance*log/size)+7*log/(3*(size-1)) if size > 1 else 1.
            fields[endpoint] = dict(n=size, mean=mean, lower=max(0., mean-half) if size else 0.,
                upper=min(1., mean+half) if size else 1., halfwidth=half,
                mcse=math.sqrt(variance/size) if size > 1 else None)
        methods[name] = dict(endpoints=fields)
    return dict(n_studies=n, original_prespecified=original,
                expanded_postdiagnosis=dict(methods=methods,
                    delta_per_endpoint_look=EXPANDED_DELTA, family=dict(scenarios=18, methods=17, endpoints=16, looks=5),
                    selection_status='POST_DIAGNOSIS_NOT_PROSPECTIVE_REGISTRATION',
                    interpretation='Multiplicity expansion does not remove post-diagnosis selection limitations.'),
                precision_objective_met=original['precision_objective_met'],
                stopping_basis='ORIGINAL_EIGHT_ONLY_UNCHANGED')
