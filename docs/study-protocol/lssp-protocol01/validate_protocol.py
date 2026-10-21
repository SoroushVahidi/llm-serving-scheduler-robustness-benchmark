#!/usr/bin/env python3
"""Read-only consistency checks for the DRAFT; never launches or authorizes work."""
from __future__ import annotations

import argparse
import hashlib
import itertools
import json
from pathlib import Path
import re


def validate(directory: Path) -> tuple[int, list[str]]:
    root = directory.parents[2]
    checks = 0
    errors = []

    def check(condition, message):
        nonlocal checks
        checks += 1
        if not condition:
            errors.append(message)

    required = [
        'RESEARCH_QUESTIONS.md', 'NOVELTY_AND_OVERLAP.md', 'HYPOTHESES.md',
        'EXPERIMENTAL_MATRIX.md', 'METRICS_AND_STATISTICS.md',
        'FIDELITY_AND_EXCLUSION_GATES.md', 'STAGED_EXECUTION_PLAN.md',
        'RESOURCE_BUDGET.md', 'PREREGISTRATION_DRAFT.md', 'AUTHOR_DECISIONS.md',
    ]
    for name in required:
        path = directory / name
        check(path.is_file(), f'Missing {name}')
        if path.is_file():
            check('DRAFT' in path.read_text(), f'Missing draft label: {name}')
    m = json.loads((directory / 'design_manifest.json').read_text())
    check(m['status'] == 'DRAFT', 'This validator covers draft v0.1 only')
    check(m['execution_authorized'] is False, 'Draft cannot authorize execution')
    check(all(s['execution_authorized'] is False for s in m['stages']), 'Stage execution authorized')
    check(all(s['go_status'] == 'NO_GO' for s in m['stages']), 'Unreviewed stage marked GO')
    check([s['id'] for s in m['stages']] == list(range(5)), 'Missing/duplicate stage')
    check(len(m['deployments']) == 6, 'Expected six deployments')
    ids = {d['id'] for d in m['deployments']}
    check(len(ids) == 6, 'Duplicate deployment')
    for d in m['deployments']:
        check(d['allocated_gpus'] == d['tp'] * d['replicas'], f'GPU topology mismatch: {d["id"]}')
        check(d['physical_fidelity'] == 'NOT_VERIFIED', f'Unsupported physical claim: {d["id"]}')
    check(len({p['id'] for p in m['policies']}) == 4, 'Expected four unique policy candidates')
    check(all(p['physical_main_domain'] == 'NOT_VERIFIED' for p in m['policies']), 'Unsupported policy claim')
    check(len(m['sources']) == 3, 'Expected three source releases')
    for s in m['sources']:
        check(bool(re.fullmatch(r'[0-9a-f]{64}', s['raw_sha256'])), f'Malformed inherited source hash: {s["id"]}')
        check(s['new_windows_sha256'] is None, 'New windows have not been frozen')
    edges = m['primary_transfer_edges']
    check(len(edges) == len({tuple(e) for e in edges}) == 7, 'Expected seven unique edges')
    check(all(a in ids and b in ids and a != b for a, b in edges), 'Invalid transfer edge')
    dims = m['illustrative_design']
    check(dims['is_sample_size_commitment'] is False, 'Illustration cannot become a power claim')
    # Enumerate the cells rather than simply copying the prose multiplication.
    cells = list(itertools.product(m['deployments'], m['policies'], m['sources'],
                                   range(dims['windows_per_source']),
                                   m['load_views']['relative_pressure_regions'],
                                   range(dims['repetitions'])))
    n = len(cells)
    gpu_n = sum(c[0]['allocated_gpus'] for c in cells)
    extra = [c for c in cells if c[0]['id'] != 'a100_1']
    check(n == dims['single_view_executions'] == 3456, 'Single-view count mismatch')
    check(gpu_n == dims['single_view_gpu_executions'] == 5760, 'Weighted GPU count mismatch')
    check(n + len(extra) == dims['both_views_anchor_deduplicated_executions'] == 6336, 'Deduplicated count mismatch')
    check(gpu_n + sum(c[0]['allocated_gpus'] for c in extra) == dims['both_views_anchor_deduplicated_gpu_executions'] == 10944, 'Deduplicated GPU count mismatch')
    pairs = list(itertools.combinations(m['policies'], 2))
    interactions = list(itertools.product(pairs, edges, m['sources'], m['load_views']['relative_pressure_regions']))
    endpoints = list(itertools.product(pairs, m['deployments'], m['sources'], m['load_views']['relative_pressure_regions']))
    check(len(interactions) == dims['primary_interaction_contrasts'] == 252, 'Interaction family mismatch')
    check(len(endpoints) == dims['primary_endpoint_contrasts'] == 216, 'Endpoint family mismatch')
    check(len(interactions) + len(endpoints) == dims['joint_primary_family_contrasts'] == 468, 'Joint family mismatch')
    c = m['current_mgpu02_contract']
    check(all(r + (c['max_active'] - r) * c['max_prompt_tokens'] <= c['token_budget']
              for r in range(c['max_active'] + 1)), 'Whole-prefill bound violated')
    check(c['main_study_sufficient'] is False, 'Bounded contract is insufficient for main study')
    check(all(c[k] == 'REJECTED' for k in ['partial_prefill', 'kv_preemption', 'distributed']), 'Unsupported capability silently admitted')
    check(m['mgpu03']['performance_outcomes_used_for_design'] is False, 'Outcome-blind design boundary lost')
    check(m['mgpu03']['physical_acceptance_reviewed_here'] is False, 'Accounting is not physical acceptance')
    check(m['mgpu03']['execution_commit'] == m['base_execution_commit'], 'Commit mismatch')
    check((directory / m['mgpu03']['evidence']).is_file(), 'Missing accounting evidence')
    check(all(v is None for v in m['freeze_required'].values()), 'Unapproved freeze field filled without review')
    inventory = json.loads((directory / 'evidence/review_inventory.json').read_text())
    for item in inventory['local_files']:
        path = root / item['path']
        check(path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest() == item['sha256'],
              f'Review input changed: {item["path"]}')
    windows = json.loads((root / inventory['coverage_input']).read_text())['windows']
    for summary in inventory['coverage_summary']:
        rows = [w['descriptor'] for w in windows if w['source_family'] == summary['source']]
        actual = (len(rows), sum(w['prompt_tokens_p50'] > 256 for w in rows),
                  sum(w['prompt_tokens_p99'] > 256 for w in rows))
        expected = (summary['windows'], summary['windows_prompt_p50_gt_256'],
                    summary['windows_prompt_p99_gt_256'])
        check(actual == expected, f'Coverage summary mismatch: {summary["source"]}')
    for doc in directory.glob('*.md'):
        for target in re.findall(r'\]\(([^)]+)\)', doc.read_text()):
            if '://' in target or target.startswith('#'):
                continue
            check((doc.parent / target.split('#')[0]).exists(), f'Broken local link {doc.name}: {target}')
    return checks, errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--require-frozen', action='store_true', help='Also fail while required freeze decisions are unresolved')
    args = parser.parse_args()
    directory = Path(__file__).resolve().parent
    checks, errors = validate(directory)
    for error in errors:
        print('FAIL:', error)
    if errors:
        print(f'FAILED: {len(errors)} of {checks} consistency checks')
        return 1
    print(f'PASS: {checks} protocol consistency checks; no physical validation performed')
    m = json.loads((directory / 'design_manifest.json').read_text())
    missing = [key for key, value in m['freeze_required'].items() if value is None]
    print(f'DRAFT: {len(missing)} unresolved freeze fields; execution_authorized=false')
    if args.require_frozen:
        print('NOT FROZEN:', ', '.join(missing))
        return 2
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
