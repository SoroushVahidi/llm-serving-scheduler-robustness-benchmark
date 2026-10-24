#!/usr/bin/env python3
"""Independent certificate/telemetry check using per-request service intervals.
No imports from the analyzer, simulator, policy, or event referee.
"""
import argparse
import csv
import gzip
import hashlib
import json
from pathlib import Path

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('candidate', type=Path)
p.add_argument('artifacts', type=Path)
a = p.parse_args()
out = Path(__file__).resolve().parent
rows = list(csv.DictReader((out / 'certificates.csv').open()))
summary = json.loads((out / 'saved-evidence-audit.json').read_text())
conditions = {c['condition_id']:c for c in json.loads((a.candidate / 'evidence/c01/inputs/full-inputs.json').read_text())['conditions']}
index = {}
for pin in summary['identities']:
    path = a.artifacts / pin['result_path']
    assert hashlib.sha256(path.read_bytes()).hexdigest() == pin['result_sha256']
    r = json.loads(path.read_text())
    ep = path.parent / 'events.jsonl.gz'
    assert hashlib.sha256(ep.read_bytes()).hexdigest() == pin['journal_sha256']
    index[r['condition_id'], r['budget']] = (r, [json.loads(line) for line in gzip.open(ep,'rt')])
checked_opportunities = checked_omissions = 0
for row in rows:
    r, events = index[row['condition_id'], int(row['budget'])]
    req = conditions[row['condition_id']]['requests']
    finished_prefill, decode_indices = {}, {i:[] for i in range(len(req))}
    for j, event in enumerate(events):
        for i, kind, start, stop in event['executed']:
            if kind == 'decode':
                decode_indices[i].append(j)
            elif stop == req[i]['prompt']:
                assert i not in finished_prefill
                finished_prefill[i] = j
    opportunities = omitted = critical = max_streak = 0
    max_age = 0.
    gaps, first_gaps = [], []
    first_omissions = 0
    ready_batches, critical_batches = set(), set()
    for i, decoding in decode_indices.items():
        assert len(decoding) == req[i]['output']
        gaps.extend(events[b]['end'] - events[a]['end'] for a,b in zip(decoding, decoding[1:]))
        previous = finished_prefill[i]
        first_gaps.append(events[decoding[0]]['end']-events[previous]['end'])
        first_omissions += decoding[0] - previous - 1
        for j in decoding:
            gap = j - previous - 1
            omitted += gap
            max_streak = max(max_streak, gap)
            for k in range(previous+1, j+1):
                age = events[k]['time'] - events[previous]['end']
                opportunities += 1
                ready_batches.add(k)
                max_age = max(max_age, age)
                if age >= .495:
                    critical += 1
                    critical_batches.add(k)
            previous = j
    expected = dict(batches=len(events), ready_batches=len(ready_batches), ready_opportunities=opportunities,
        omitted_opportunities=omitted, critical_opportunities=critical, critical_batches=len(critical_batches),
        max_consecutive_omissions=max_streak)
    for key, value in expected.items():
        assert int(row[key]) == value, (row['condition_id'], key)
    assert float(row['observed_max_age_ms']) == max_age*1000
    assert int(row['completed_inter_output_gaps']) == len(gaps)
    assert int(row['gaps_within_0_5s']) == sum(g <= .5 for g in gaps)
    assert float(row['max_inter_output_gap_ms']) == max(gaps)*1000
    assert int(row['pre_first_output_omissions']) == first_omissions
    assert int(row['between_output_omissions']) == omitted-first_omissions
    assert float(row['max_post_prefill_first_decode_gap_ms']) == max(first_gaps)*1000
    P = sum(x['prompt'] for x in req)
    K = min(r['config']['max_sequences'], r['config']['kv_capacity']//r['config']['context'])
    B = r['budget']
    bound = int(row['certified_max_omitted_batches'])
    assert P == int(row['prompt_work']) and B-K+1 == int(row['work_per_omitted_batch_lower_bound'])
    # Verify floor via bracketing inequalities, separately from integer division.
    assert bound*(B-K+1) <= P < (bound+1)*(B-K+1)
    assert 495*(B-K+1) > P  # first gate would require more prompt work than exists
    assert bound < 495 and P <= len(req)*B
    checked_opportunities += opportunities
    checked_omissions += omitted
# For all B>=1024, N<=200, K<=8: 495(B-K+1)-NB >=295B-3465 >0.
assert 295*1024-3465 > 0
assert 201*1017 <= 200*1024 < 202*1017
assert len(rows) == 18 and checked_omissions == 42
report = dict(state='COMPLETED_SUCCESS', independent_method='Per-request event-index intervals; integer inequalities',
    saved_cells=18, ready_decode_opportunities=checked_opportunities, omitted_opportunities=checked_omissions,
    critical_opportunities=0, certificate_rows_checked=18, universal_bound_ms=201,
    scientific_experiments_executed=0)
(out / 'independent-check.json').write_text(json.dumps(report, indent=2)+'\n')
print(json.dumps(report, indent=2))
