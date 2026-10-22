import copy
from fractions import Fraction as Q
import hashlib
import importlib.util
import itertools
import json
import math
import os
from pathlib import Path
import sys

import numpy as np
import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, os.environ.get('STAT01_FROZEN_CODE', str(HERE.parent)))
from design import SCENARIOS, METHODS, FAMILY, rng
from methods import adjust
from experiment import study
from reference import validate_record
from precision import sufficient as original_sufficient, summarize_stats, DELTA
from rv2_methods import (legacy_bh, bootstrap_fraction, exact_probabilities, critical_values,
                         exact_adjust, derive, ALL_METHODS, SECONDARY)
from rv2_reference import binary_oracle, exact_oracle, referee_probabilities, validate
from rv2_summary import sufficient, summarize, EXPANDED_DELTA


@pytest.fixture(scope='module')
def failure():
    return study(11, 6628)


def frozen_stats():
    root = Path(os.environ.get('STAT01_REFERENCE_SRC', str(HERE.parents[2] / 'src')))
    sys.path.insert(0, str(root))
    path = root / 'robustbench/ranking_portability/analysis/stats.py'
    launch = json.loads(Path(os.environ.get('STAT01_FROZEN_LAUNCH', str(HERE.parent/'launch.json'))).read_text())
    assert hashlib.sha256(path.read_bytes()).hexdigest() == launch['historical_reference_files']['robustbench/ranking_portability/analysis/stats.py']
    spec = importlib.util.spec_from_file_location('frozen_stats_for_recovery', path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_failure_full_legacy_procedure_against_frozen_classifier(failure):
    frozen = frozen_stats()
    from robustbench.ranking_portability.analysis.reversal_analysis import classify_pairwise_reversal
    from robustbench.ranking_portability.analysis import reversal_analysis
    manifest = json.loads(Path(os.environ.get('STAT01_FROZEN_LAUNCH', str(HERE.parent/'launch.json'))).read_text())
    assert hashlib.sha256(Path(reversal_analysis.__file__).read_bytes()).hexdigest() == manifest['historical_reference_files']['robustbench/ranking_portability/analysis/reversal_analysis.py']
    y, mask, rec = failure
    rows = [[dict(window_id=str(i), policy_id=f'p{j:02d}', score=float(y[s,i,j]) if mask[s,i,j] else None)
             for i in range(40) for j in range(11)] for s in range(3)]
    stream = rng(11, 6628, 2)
    classifications = [classify_pairwise_reversal(rows[s], rows[t], policy_a=f'p{a:02d}',
        policy_b=f'p{b:02d}', metric='score', rng=stream, n_resamples=2000) for s,t,a,b in FAMILY]
    indices = [j for j,x in enumerate(classifications) if x.p_x is not None and x.p_y is not None]
    probabilities = [max(classifications[j].p_x, classifications[j].p_y) for j in indices]
    assert probabilities == [rec['methods']['historical_screened_BH']['p'][j] for j in indices]
    expected = [False]*165
    for j, flag in zip(indices, frozen.benjamini_hochberg(probabilities, q=.05)):
        expected[j] = flag and classifications[j].classification.value == 'SUPPORTED_PRACTICAL_REVERSAL'
    assert derive(rec)['legacy_source_screened_BH']['reject'] == expected


def test_original_failure_and_nonmutation(failure):
    y, mask, rec = failure
    original = copy.deepcopy(rec)
    with pytest.raises(ValueError, match='independent multiplicity mismatch'):
        validate_record(SCENARIOS[11], y, mask, rec, 11, 6628)
    extra = derive(rec)
    assert rec == original
    assert rec['methods']['historical_screened_BH']['reject'][47] is False
    assert extra['legacy_source_screened_BH']['reject'][47] is True
    assert extra['exact_historical_screened_BH']['reject'][47] is True
    assert validate(SCENARIOS[11], y, mask, rec, extra, 11, 6628)


def test_legacy_against_frozen_source_at_all_bootstrap_boundaries():
    frozen = frozen_stats()
    for m in range(1, 166):
        for rank in range(1, m + 1):
            critical = Q(rank, 20*m)
            if (critical*1000).denominator != 1:
                continue
            p = float(critical)
            for boundary in [math.nextafter(p, 0.), p, math.nextafter(p, 1.)]:
                values = [0.]*(rank-1) + [boundary] + [1.]*(m-rank)
                expected = frozen.benjamini_hochberg(values, q=.05)
                assert legacy_bh(values) == expected
                assert binary_oracle(values, 'bh', historical=True) == expected
    for values in [[], [float('nan'), .025, .05], [.035]*7 + [1.]*3, [.05]*43]:
        assert legacy_bh(values) == frozen.benjamini_hochberg(values, q=.05)


@pytest.mark.parametrize('kind', ['bh', 'by', 'holm'])
def test_frozen_binary_emulator_boundaries(kind):
    for m in range(1, 166):
        for rank in set([1, m//2+1, m]):
            if kind == 'holm':
                t = .05/(m-rank+1)
            else:
                q = .05/(sum(1/k for k in range(1, m+1)) if kind == 'by' else 1.)
                t = q*rank/m
            for p in [math.nextafter(t, 0.), t, math.nextafter(t, 1.)]:
                values = [0.]*(rank-1)+[p]+[1.]*(m-rank)
                assert binary_oracle(values, kind) == adjust(values, kind).tolist()


@pytest.mark.parametrize('kind', ['bh', 'by', 'holm'])
def test_exact_critical_values_neighbors_and_independent_adjusted_p(kind):
    for m in [1, 2, 10, 43, 50, 165]:
        for rank, critical in enumerate(critical_values(m, kind), 1):
            values = [Q(0)]*(rank-1)+[critical]+[Q(1)]*(m-rank)
            assert exact_adjust(values, kind) == exact_oracle(values, kind)
            assert exact_adjust(values, kind)[rank-1]
            # Analytic floats are dyadic inputs, not rounded critical values.
            for p in [math.nextafter(float(critical), 0.), float(critical), math.nextafter(float(critical), 1.)]:
                values[rank-1] = Q.from_float(p)
                assert exact_adjust(values, kind) == exact_oracle(values, kind)
                assert exact_adjust(values, kind)[rank-1] == (Q.from_float(p) <= critical)


@pytest.mark.parametrize('kind', ['bh', 'by', 'holm'])
def test_sorting_ties_and_permutations(kind):
    for values in itertools.product([Q(0), Q(1, 40), Q(1, 20), Q(1)], repeat=4):
        assert exact_adjust(values, kind) == exact_oracle(values, kind)
    assert exact_adjust([], kind) == []
    assert exact_adjust([Q(1)]*165, kind) == [False]*165


def test_grid_and_analytic_representation():
    assert bootstrap_fraction(.05, 2000, 2) == Q(1, 20)
    for p in [math.nextafter(.05, 0.), math.nextafter(.05, 1.), float('nan')]:
        with pytest.raises(ValueError):
            bootstrap_fraction(p, 2000, 2)
    assert Q.from_float(.05) > Q(1, 20)
    assert exact_adjust([Q.from_float(.05)], 'holm') == [False]
    assert exact_adjust([Q.from_float(math.nextafter(.05, 0.))], 'holm') == [True]


@pytest.mark.parametrize('sid', range(18))
def test_all_scenarios_and_independent_probability_reconstruction(sid):
    y, mask, rec = study(sid, 17, engineering=True)
    original = copy.deepcopy(rec)
    extra = derive(rec)
    assert rec == original
    for name in METHODS:
        assert exact_probabilities(rec, name) == referee_probabilities(rec, name)
    assert validate(SCENARIOS[sid], y, mask, rec, extra, sid, 17, namespace=0)


@pytest.mark.parametrize('field', ['original_decision', 'secondary_decision', 'endpoint', 'identity', 'mask', 'p', 'method'])
def test_referee_rejects_corruption(failure, field):
    y, mask, rec = failure
    rec = copy.deepcopy(rec)
    mask = mask.copy()
    extra = derive(rec)
    if field == 'original_decision':rec['methods']['iid_t_Holm']['reject'][0] ^= True
    if field == 'secondary_decision':extra['exact_iid_t_Holm']['reject'][0] ^= True
    if field == 'endpoint':extra['exact_iid_t_Holm']['endpoints']['ci_available'] = .123
    if field == 'identity':rec['replicate'] += 1
    if field == 'mask':mask[0, 0, 0] = False
    if field == 'p':rec['methods']['iid_t_Holm']['p'][0] = float('nan')
    if field == 'method':extra.pop('exact_iid_t_Holm')
    with pytest.raises((ValueError, KeyError)):
        validate(SCENARIOS[11], y, mask, rec, extra, 11, 6628)


def test_preserved_original_statistics_and_expanded_budget(failure):
    rec = failure[2]
    extra = derive(rec)
    sums = sufficient([rec], [extra])
    assert {m:sums[m] for m in METHODS} == original_sufficient([rec])
    report = summarize(sums, 1, SCENARIOS[11])
    assert report['original_prespecified'] == summarize_stats(original_sufficient([rec]), 1, SCENARIOS[11])
    assert EXPANDED_DELTA == .05/(18*17*16*5) < DELTA
    assert len(report['expanded_postdiagnosis']['methods']) == 17
    assert report['precision_objective_met'] == report['original_prespecified']['precision_objective_met']


def test_saved_batch_reuse_readback_resume_and_corruption(tmp_path, monkeypatch):
    import run as frozen_runner
    import rv2_run as runner
    old = tmp_path/'old'
    frozen_runner.execute_batch(str(old), 7, 0, 2, 'old-identity', engineering=True)
    source_path = old/'batches/scenario-07/rep-000000'
    metadata = json.loads((source_path/'integrity.json').read_text())
    source = dict(path=str(source_path), scenario=7, start=0, count=2,
                  integrity_sha256=runner.sha(source_path/'integrity.json'), artifact_hashes=metadata['hashes'])
    before = {f.name:runner.sha(f) for f in source_path.iterdir()}
    monkeypatch.setattr(runner, 'study', lambda *a, **k: (_ for _ in ()).throw(AssertionError('must not regenerate saved data')))
    new = tmp_path/'new'
    result = runner.execute_batch(new, 7, 0, 2, 'new-identity', 'old-identity', source, engineering=True)
    assert result[-1] == 'REUSED_AUDITED_ORIGINAL'
    assert before == {f.name:runner.sha(f) for f in source_path.iterdir()}
    path = new/'batches/scenario-07/rep-000000'
    assert (path/'studies.json.gz').read_bytes() == (source_path/'studies.json.gz').read_bytes()
    assert (path/'raw.npz').read_bytes() == (source_path/'raw.npz').read_bytes()
    again = runner.execute_batch(new, 7, 0, 2, 'new-identity', 'old-identity', source, engineering=True)
    assert again[:3] == result[:3] and again[-1] == 'RESUMED_VERIFIED'
    with pytest.raises(ValueError, match='identity'):
        runner.checked_batch(path, 7, 0, 2, 'wrong', source, namespace=0)
    with (path/'raw.npz').open('ab') as stream:stream.write(b'corruption')
    with pytest.raises(ValueError, match='hash mismatch'):
        runner.execute_batch(new, 7, 0, 2, 'new-identity', 'old-identity', source, engineering=True)
    assert before == {f.name:runner.sha(f) for f in source_path.iterdir()}


def test_missing_study_batch_roundtrip(tmp_path):
    import rv2_run as runner
    result = runner.execute_batch(tmp_path, 11, 6628, 1, 'new', 'old')
    assert result[-1] == 'GENERATED_MISSING_STUDIES'
    path = tmp_path/'batches/scenario-11/rep-006628'
    assert runner.checked_batch(path, 11, 6628, 1, 'new') == result[2]


def test_runner_counts_and_original_only_stopping(tmp_path, monkeypatch, failure):
    import concurrent.futures
    import rv2_run as runner
    from rv2_summary import sufficient
    record = failure[2]
    sums = sufficient([record]*25, [derive(record)]*25)
    spec = dict(original_root=str(tmp_path/'old'), original_identity='old')
    source = {(0,0):dict(count=25)}
    monkeypatch.setattr(runner, 'preflight', lambda _: (spec, source))
    monkeypatch.setattr(runner, 'SCENARIOS', SCENARIOS[:2])
    monkeypatch.setattr(runner, 'LOOKS', (25,50))
    monkeypatch.setattr(runner.concurrent.futures, 'ProcessPoolExecutor', concurrent.futures.ThreadPoolExecutor)
    calls = []
    def batch(out, sid, start, count, identity, original_identity, source=None):
        calls.append((sid,start))
        return sid,start,sums,'MOCK_VERIFIED'
    monkeypatch.setattr(runner, 'execute_batch', batch)
    monkeypatch.setattr(runner, 'summarize', lambda *a:dict(precision_objective_met=False))
    assert runner.run(tmp_path/'runs/out', tmp_path/'launch.json', workers=2) == 0
    done = json.loads((tmp_path/'runs/out/completion.json').read_text())
    assert done['reused_studies'] == 25 and done['generated_studies'] == 75
    assert sorted(calls) == [(0,0),(0,25),(1,0),(1,25)]
    assert done['status'] == 'COMPLETE_WITH_ORIGINAL_PRECISION_GAPS'


def test_source_identity_corruption_rejected_before_reuse(tmp_path):
    import rv2_run as runner
    path = tmp_path/'source';path.mkdir()
    (path/'integrity.json').write_text('{}')
    with pytest.raises(ValueError, match='metadata changed'):
        runner.verify_source(dict(path=str(path), integrity_sha256='wrong'), 'old')


def test_actual_checkpoint_resume_without_regeneration(tmp_path, monkeypatch):
    import concurrent.futures
    import rv2_run as runner
    spec = dict(original_root=str(tmp_path/'old'), original_identity='old')
    monkeypatch.setattr(runner, 'preflight', lambda _: (spec, {}))
    monkeypatch.setattr(runner, 'SCENARIOS', SCENARIOS[:1])
    monkeypatch.setattr(runner, 'LOOKS', (1,2))
    monkeypatch.setattr(runner, 'BATCH', 1)
    monkeypatch.setattr(runner.concurrent.futures, 'ProcessPoolExecutor', concurrent.futures.ThreadPoolExecutor)
    out = tmp_path/'runs/out'
    assert runner.run(out, tmp_path/'launch.json', workers=1) == 0
    batch_hashes = {str(p.relative_to(out)):runner.sha(p) for p in (out/'batches').glob('*/*/*')}
    monkeypatch.setattr(runner, 'study', lambda *a,**k: (_ for _ in ()).throw(AssertionError('resume regenerated a study')))
    # Mutable checkpoint is not authoritative: reconstruct from immutable batches.
    (out/'checkpoint.json').write_text('{}')
    assert runner.run(out, tmp_path/'launch.json', workers=1) == 0
    assert batch_hashes == {str(p.relative_to(out)):runner.sha(p) for p in (out/'batches').glob('*/*/*')}
    assert json.loads((out/'checkpoint.json').read_text())['scenarios']['0']['n'] == 2


@pytest.mark.parametrize('gate', ['pass', 'test_hash', 'preflight_failure', 'active_job'])
def test_single_submission_fail_closed(tmp_path, monkeypatch, gate):
    import subprocess
    from types import SimpleNamespace
    import submit_once
    root = tmp_path/'deployment';(root/'code').mkdir(parents=True);(root/'logs').mkdir()
    (root/'logs/tests-pinned.exit').write_text('0\n')
    (root/'logs/tests-pinned.txt').write_text('passed\n')
    digest = hashlib.sha256(b'passed\n').hexdigest()
    launch = dict(recovery_root=str(root), original_root=str(tmp_path/'old'), code_commit='test',
                  validation=dict(pinned_log_sha256='bad' if gate == 'test_hash' else digest))
    (root/'launch.json').write_text(json.dumps(launch))
    monkeypatch.setattr(submit_once, '__file__', str(root/'code/submit_once.py'))
    monkeypatch.setenv('SBATCH_GPUS', '8')
    calls = []
    def run(command, **kwargs):
        calls.append(command[0])
        assert 'SBATCH_GPUS' not in kwargs['env']
        if command[0] != 'sbatch' and gate == 'preflight_failure':
            raise subprocess.CalledProcessError(1, command)
        return SimpleNamespace(returncode=0, stdout='12345\n', stderr='')
    monkeypatch.setattr(submit_once.subprocess, 'run', run)
    monkeypatch.setattr(submit_once.subprocess, 'check_output', lambda *a, **k: 'active' if gate == 'active_job' else '')
    if gate == 'pass':
        submit_once.main()
        assert calls.count('sbatch') == 1
        assert json.loads((root/'submission.json').read_text())['stdout'] == '12345\n'
        with pytest.raises(ValueError, match='already attempted'):
            submit_once.main()
        assert calls.count('sbatch') == 1
    else:
        with pytest.raises((ValueError, subprocess.CalledProcessError)):
            submit_once.main()
        assert 'sbatch' not in calls
        assert not (root/'submission-intent.json').exists()
