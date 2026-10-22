"""Offline document consistency checks; deliberately not a scheduler oracle."""
import hashlib
import json
import math
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def read(name):
    return json.loads((HERE / name).read_text())


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    manifest = read('manifest.json')
    corpus = read('cases.json')
    checks = []
    assert manifest['status'] == corpus['status'] == 'DRAFT'
    assert manifest['author_approval'] is None
    assert manifest['physical_status'] == 'NOT_VERIFIED'
    assert manifest['implementation_status'] == 'NOT_IMPLEMENTED'
    assert manifest['future_execution_authorized'] is False
    assert manifest['gpu_allocations_this_task'] == 0
    assert set(manifest['decisions']) == {f'S{i:02}' for i in range(1, 9)}
    assert set(manifest['decisions'].values()) == {'UNRESOLVED'}
    assert digest(HERE / 'cases.json') == manifest['cases_sha256']
    checks.append('draft status, unresolved decisions and corpus hash')

    cases = corpus['cases']
    assert len(cases) == manifest['conformance_cases'] == 32
    assert [c['id'] for c in cases] == [f'C{i:02}' for i in range(1, 33)]
    for c in cases:
        assert c['scenario'] and c['inputs'] and c['expected_steps']
        assert c['physical_status'] == 'NOT_VERIFIED'
        assert set(c['requires_decisions']) <= set(manifest['decisions'])
        if c['basis'] == 'PROPOSED_ADAPTATION':
            assert c['approval_status'] == 'UNRESOLVED' and c['requires_decisions']
        else:
            assert c['basis'] == 'SOURCE_DERIVED_REFERENCE_DIFFERENCE'
            assert c['approval_status'] == 'SOURCE_OBSERVATION_ONLY'
            assert c['requires_decisions'] == []
        b = c['inputs']['B']
        assert type(b) is int and b > 0
        for step in c['expected_steps']:
            plan = step.get('plan', {})
            assert all(type(q) is int and q > 0 for q in plan.values())
            assert sum(plan.values()) <= b, c['id']
            if 'Y' in step:
                assert len(step['Y']) <= c['inputs'].get('O', corpus['defaults']['O'])
    checks.append('32 unique literal cases; status, references, token budgets and output limits')

    # Check arithmetic of the numeric illustrations, not their policy selection.
    by_id = {c['id']: c for c in cases}
    assert sum(s['plan']['r'] for s in by_id['C02']['expected_steps']) == 10
    assert by_id['C11']['expected_steps'][0]['state'] == 'RECOMPUTE_PAUSED'
    assert by_id['C10']['expected_steps'][0]['state'] == 'RECOMPUTE_WAITING'
    for key in ['C01', 'C02', 'C09', 'C11']:
        c = by_id[key]
        progress = c['inputs']['C_exec']
        prefix = c['inputs'].get('Y', [])
        for step in c['expected_steps']:
            progress += sum(step['plan'].values())
            assert progress == step['C_exec']
            assert step['Y'][:len(prefix)] == prefix
            prefix = step['Y']
    c = by_id['C20']
    i = c['inputs']
    mean = sum(i['batch_durations_s']) / len(i['batch_durations_s'])
    assert math.isclose(mean, i['mean_s'])
    for step in c['expected_steps'][:2]:
        offset = i['offset_high'] if step['KV_fraction'] >= i['threshold'] else i['offset_low']
        assert math.isclose(i['batch_end_s'] + i['TBT_s'] - offset * mean, step['expected_LST_s'])
    assert by_id['C32']['inputs']['P'] + by_id['C32']['inputs']['O'] > by_id['C32']['inputs']['L']
    checks.append('illustrative progress/prefix/context/LST arithmetic')

    links = 0
    for p in HERE.glob('*.md'):
        for target in re.findall(r'\[[^\]]*\]\(([^\s)]+)\)', p.read_text()):
            if '://' in target or target.startswith('#'):
                continue
            assert (p.parent / target.split('#')[0]).exists(), (p.name, target)
            links += 1
    decisions = (HERE / 'AUTHOR_DECISIONS.md').read_text()
    for i in range(1, 17):
        assert f'| A{i:02} |' in decisions
    checks.append(f'{links} local documentation links and all 16 original decision references')

    preserved = read('evidence/preservation.json')
    assert len(preserved['preserved_sha256']) == preserved['preserved_file_count'] == 29
    for name, expected in preserved['preserved_sha256'].items():
        assert digest(ROOT / name) == expected, name
    anomaly = preserved['preexisting_lfs_checkout_anomaly']
    assert digest(ROOT / anomaly['path']) == anomaly['baseline_raw_sha256']
    checks.append('29 frozen/protocol files and pre-existing historical raw-byte identity')

    trace = read('evidence/trace-audit.json')
    assert digest(ROOT / trace['index_path']) == trace['index_sha256']
    assert digest(ROOT / trace['parquet']['path']) == trace['parquet']['sha256']
    windows = json.loads((ROOT / trace['index_path']).read_text())['windows']
    assert len(windows) == trace['parquet']['rows'] == 120
    for family, expected in trace['families'].items():
        rows = [w['descriptor'] for w in windows if w['source_family'] == family]
        medians = [r['prompt_tokens_p50'] for r in rows]
        assert len(rows) == expected['windows'] == 40
        assert min(medians) == expected['input_p50_min']
        assert max(medians) == expected['input_p50_max']
        for cap, count in expected['windows_median_gt'].items():
            assert sum(v > int(cap) for v in medians) == count
        assert max(r['prompt_tokens_p99'] for r in rows) == expected['largest_window_input_p99']
        assert max(r['output_tokens_p99'] for r in rows) == expected['largest_window_output_p99']
    checks.append('120 frozen descriptors and independently recomputed length-summary arithmetic')
    sources = read('evidence/sources.json')
    assert len(sources['slai_source_files']) == 11
    assert len(sources['vllm_installed_files']) == 5
    for entry in sources['vllm_installed_files'].values():
        assert entry['installed_matches_upstream']
        assert entry['upstream_sha256'] == entry['sha256']
    checks.append('16 source identities; five recorded installed/upstream matches')

    print(json.dumps({'status': 'PASS_DOCUMENT_CHECKS', 'check_groups': checks,
                      'case_count': len(cases), 'scheduler_conformance_executed': False,
                      'physical_validation': 'NOT_VERIFIED'}, indent=2))


if __name__ == '__main__':
    main()
