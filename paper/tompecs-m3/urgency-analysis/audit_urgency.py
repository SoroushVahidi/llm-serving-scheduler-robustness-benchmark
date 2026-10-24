#!/usr/bin/env python3
"""Read-only reconstruction of existing urgency histories and finite-work bounds.
No simulator or policy imports and no new workload execution.
"""
import argparse
import csv
import gzip
import hashlib
import json
from collections import Counter
from fractions import Fraction
from pathlib import Path

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('candidate', type=Path)
parser.add_argument('budget_artifacts', type=Path)
parser.add_argument('--output', type=Path, required=True)
a = parser.parse_args()
a.output.mkdir(parents=True, exist_ok=True)
frozen = a.candidate / 'evidence/c01'
read = lambda p: json.loads(p.read_text())
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
manifest = read(a.budget_artifacts / 'manifest.json')
for path, digest in manifest['identity']['frozen_files'].items():
    assert sha(frozen / path) == digest, path
conditions = {c['condition_id']: c for c in read(frozen / 'inputs/full-inputs.json')['conditions']}
rows, identities, episodes = [], [], []
for path in sorted((a.budget_artifacts / 'cells').glob('*/result.json')):
    result = read(path)
    if result['policy'] != 'slo_gated_c01':
        continue
    assert result['run_id'] == manifest['run_id']
    cfg = result['config']
    req = conditions[result['condition_id']]['requests']
    request_hash = hashlib.sha256(json.dumps(req, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()
    assert request_hash == result['requests_sha256']
    journal = path.parent / 'events.jsonl.gz'
    assert sha(journal) == result['journal_sha256']
    events = [json.loads(line) for line in gzip.open(journal, 'rt')]
    budget = cfg['budget']
    slots = min(cfg['max_sequences'], cfg['kv_capacity'] // cfg['context'])
    prompt_work = sum(r['prompt'] for r in req)
    denom = budget - slots + 1
    assert denom > 0
    bound_steps = prompt_work // denom
    # Rational contract arithmetic avoids the printed decimal boundary.
    bound_seconds = Fraction(bound_steps, 1000)
    assert cfg['dt'] == .001 and bound_seconds < Fraction(495, 1000)
    progress = [0] * len(req)
    active, anchors, streaks, completed = set(), {}, Counter(), set()
    counts = Counter()
    max_age = max_step = 0.0
    max_streak = 0
    prefill_total = 0
    last_output, token_gaps, first_decode_gaps = {}, [], []
    for event_index, e in enumerate(events):
        ready = {i for i in active if progress[i] == req[i]['prompt']}
        assert all(i in anchors for i in ready)
        ages = {i: e['time'] - anchors[i] for i in ready}
        critical = {i for i, age in ages.items() if age >= .495}
        counts['batches'] += 1
        counts['ready_batches'] += bool(ready)
        counts['ready_opportunities'] += len(ready)
        counts['critical_batches'] += bool(critical)
        counts['critical_opportunities'] += len(critical)
        max_age = max([max_age] + list(ages.values()))
        max_step = max(max_step, e['end'] - e['time'])
        decodes = {span[0] for span in e['executed'] if span[1] == 'decode'}
        omitted = ready - decodes
        counts['omitted_opportunities'] += len(omitted)
        counts['pre_first_output_omissions'] += sum(i not in last_output for i in omitted)
        counts['between_output_omissions'] += sum(i in last_output for i in omitted)
        work = sum(stop - start for _, _, start, stop in e['executed'])
        prefill = sum(stop - start for _, kind, start, stop in e['executed'] if kind == 'prefill')
        assert work <= budget and e['intent'] == e['executed']
        prefill_total += prefill
        if omitted:
            # Direct event-level necessary condition used by the proof.
            assert not critical and work == budget
            assert len(decodes) <= slots - 1 and prefill >= denom
        for i in omitted:
            streaks[i] += 1
            max_streak = max(max_streak, streaks[i])
        for i in decodes:
            if streaks[i]:
                episodes.append(dict(condition_id=result['condition_id'], budget=budget,
                    request_id=i, omitted_batches=streaks[i], resumed_batch=event_index,
                    anchor_age_s=ages[i]))
            streaks[i] = 0
        for i, kind, start, stop in e['executed']:
            active.add(i)
            if kind == 'prefill':
                assert start == progress[i]
                progress[i] = stop
                if stop == req[i]['prompt']:
                    anchors[i] = e['end']
            else:
                assert i in ready
                if i in last_output:
                    token_gaps.append(e['end'] - last_output[i])
                else:
                    first_decode_gaps.append(e['end'] - anchors[i])
                last_output[i] = e['end']
                anchors[i] = e['end']
        for i in e['completed']:
            active.remove(i)
            completed.add(i)
    assert not active and len(completed) == len(req) and prefill_total == prompt_work
    assert counts['critical_opportunities'] == 0
    assert max_streak <= bound_steps
    # Finite precision is harmless at this certificate's wide separation.
    assert bound_steps * max_step < .495
    rows.append(dict(condition_id=result['condition_id'], window=result['window'], region=result['region'],
        budget=budget, slots=slots, requests=len(req), prompt_work=prompt_work,
        work_per_omitted_batch_lower_bound=denom, certified_max_omitted_batches=bound_steps,
        certified_max_age_ms=bound_steps, **counts, max_consecutive_omissions=max_streak,
        observed_max_age_ms=max_age*1000, max_observed_batch_duration_s=max_step,
        completed_inter_output_gaps=len(token_gaps), gaps_within_0_5s=sum(g <= .5 for g in token_gaps),
        max_inter_output_gap_ms=max(token_gaps)*1000,
        max_post_prefill_first_decode_gap_ms=max(first_decode_gaps)*1000,
        requests_sha256=request_hash))
    identities.append(dict(result_path=str(path.relative_to(a.budget_artifacts)), result_sha256=sha(path),
        journal_sha256=sha(journal)))
assert len(rows) == 18
rows.sort(key=lambda r: (r['window'], r['region'], r['budget']))
for name, data in [('certificates.csv', rows), ('omission-episodes.csv', episodes)]:
    with (a.output / name).open('w') as f:
        writer = csv.DictWriter(f, fieldnames=list(data[0]), lineterminator='\n')
        writer.writeheader()
        writer.writerows(data)
summary = dict(state='COMPLETED_SUCCESS', scientific_experiments_executed=0,
    saved_slo_cells=len(rows), budgets=[], source_workload='Three existing BurstGPT windows, two settings; no new selection',
    universal_finite_window_bound=dict(N=200, B_min=1024, K_max=8,
        max_omissions=(200*1024)//(1024-7), max_age_ms=201, gate_ms=495,
        rationale='B/(B-7) decreases for B>=1024; P<=N*B follows from common domain.'),
    identities=identities, frozen_files=manifest['identity']['frozen_files'])
for b in [32768, 2048, 1024]:
    rr = [r for r in rows if r['budget'] == b]
    summary['budgets'].append(dict(budget=b, cells=len(rr),
        **{key:sum(r[key] for r in rr) for key in ['batches','ready_batches','ready_opportunities','critical_batches','critical_opportunities','omitted_opportunities','completed_inter_output_gaps','gaps_within_0_5s','pre_first_output_omissions','between_output_omissions']},
        max_consecutive_omissions=max(r['max_consecutive_omissions'] for r in rr),
        observed_max_age_ms=max(r['observed_max_age_ms'] for r in rr),
        max_inter_output_gap_ms=max(r['max_inter_output_gap_ms'] for r in rr),
        max_post_prefill_first_decode_gap_ms=max(r['max_post_prefill_first_decode_gap_ms'] for r in rr),
        certificates_ms={r['window']:r['certified_max_age_ms'] for r in rr}))
(a.output / 'saved-evidence-audit.json').write_text(json.dumps(summary, indent=2) + '\n')
print(json.dumps({k:v for k,v in summary.items() if k not in ['identities','frozen_files']}, indent=2))
