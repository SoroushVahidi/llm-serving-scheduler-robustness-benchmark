#!/usr/bin/env python3
"""Read saved terminal records and journal admissions; never import a simulator.

ARTIFACT_ROOT is rc1 staging or an unchanged evidence-archive extraction.
Outputs go only to --output, which must be outside that evidence root.
The manifest fixes the outcome-selected identity; this script never reselects.
"""
import argparse
import csv
import gzip
import hashlib
import json
import math
from pathlib import Path


def analyze(root, manifest):
    for name, identity in manifest['files'].items():
        data = (root / name).read_bytes()
        assert len(data) == identity['bytes']
        assert hashlib.sha256(data).hexdigest() == identity['sha256'], name
    conditions = json.loads((root / manifest['input_path']).read_text())['conditions']
    condition = next(c for c in conditions if c['condition_id'] == manifest['condition_id'])
    requests = condition['requests']
    canonical = json.dumps(requests, sort_keys=True, separators=(',', ':'), allow_nan=False)
    assert hashlib.sha256(canonical.encode()).hexdigest() == manifest['requests_sha256']
    assert len(requests) == 200 and [r['id'] for r in requests] == list(range(200))
    aggregates, per_request, events_selected = [], [], []
    for row in manifest['rows']:
        base = root / 'evidence/c01' / row['result_path']
        result = json.loads((base / 'result.json').read_text())
        for key in ['policy', 'profile', 'condition_id', 'requests_sha256', 'journal_sha256']:
            assert result[key] == row[key]
        assert result['identity'] == row['record_identity']
        assert result['metrics'] == row['metrics']
        terminal = result['terminal']['requests']
        admissions, event_ids = {}, {}
        with gzip.open(base / 'events.jsonl.gz', 'rt') as stream:
            for index, line in enumerate(stream):
                event = json.loads(line)
                new = []
                for rid, kind, start, stop in event['executed']:
                    if rid not in admissions:
                        assert kind == 'prefill' and start == 0
                        admissions[rid] = event['time']
                        event_ids[rid] = index
                        new.append(rid)
                if index in [13, 14, 15, 16, 26, 223]:
                    events_selected.append(dict(policy=row['policy'], event_zero_based=index,
                        time_s=event['time'], end_s=event['end'], admissions=new,
                        completed=event['completed'], reserved_tokens=event['reserved']))
        latencies = []
        for request, state in zip(requests, terminal):
            assert state['id'] == request['id']
            assert state['generated'] == request['output'] and state['prefilled'] == request['prompt']
            assert state['completion'] is not None and not state['resident']
            latency = state['completion'] - request['arrival']
            latencies.append(latency)
            per_request.append(dict(policy=row['policy'], id=request['id'],
                source_record_id=request['source_record_id'], derived_record_id=request['derived_record_id'],
                prompt=request['prompt'], output=request['output'], arrival_s=request['arrival'],
                first_prefill_start_s=admissions[request['id']],
                first_prefill_event=event_ids[request['id']],
                waiting_to_prefill_s=admissions[request['id']] - request['arrival'],
                first_output_s=state['first'], ttft_s=state['first'] - request['arrival'],
                completion_s=state['completion'], latency_s=latency))
        ordered = sorted(latencies)
        position = .95 * (len(ordered) - 1)
        lo = int(position)
        p95 = ordered[lo] + (ordered[lo + 1] - ordered[lo]) * (position - lo)
        duration = max(s['completion'] for s in terminal) - min(r['arrival'] for r in requests)
        outputs = sum(r['output'] for r in requests)
        agg = dict(policy=row['policy'], completed=len(terminal), output_tokens=outputs,
            mean_latency_s=math.fsum(latencies) / len(latencies), p95_latency_s=p95,
            first_arrival_to_final_completion_s=duration, token_throughput=outputs / duration,
            sum_latency_s=math.fsum(latencies))
        for new, old in [('mean_latency_s','mean_latency'),('p95_latency_s','p95_latency'),
                         ('token_throughput','token_throughput')]:
            assert math.isclose(agg[new], row['metrics'][old], rel_tol=1e-12, abs_tol=1e-12)
        aggregates.append(agg)
    a, b = aggregates
    deltas = [per_request[200+i]['completion_s'] - per_request[i]['completion_s'] for i in range(200)]
    summary = dict(aggregates=aggregates,
        relative_change_percent={k:100*(b[k]/a[k]-1) for k in
            ['mean_latency_s','p95_latency_s','token_throughput']},
        earlier=sum(d<0 for d in deltas), later=sum(d>0 for d in deltas), unchanged=sum(d==0 for d in deltas),
        sum_completion_difference_s=math.fsum(deltas),
        p95_convention='linear interpolation at zero-based position (200-1)*0.95=189.05',
        selected_requests=manifest['selected_request_ids'], events=events_selected)
    return summary, per_request


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('artifact_root', type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    root, output = args.artifact_root.resolve(), args.output.resolve()
    assert root != output and root not in output.parents, 'Keep outputs outside frozen artifact root'
    manifest = json.loads(Path(__file__).with_name('example-manifest.json').read_text())
    summary, requests = analyze(root, manifest)
    output.mkdir(parents=True, exist_ok=True)
    (output/'example-summary.json').write_text(json.dumps(summary, indent=2)+'\n')
    selected = [r for r in requests if r['id'] in manifest['selected_request_ids']]
    for name, rows in [('example-aggregates.csv',summary['aggregates']), ('example-requests.csv',selected)]:
        with (output/name).open('w', newline='') as stream:
            writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator='\n')
            writer.writeheader(); writer.writerows(rows)
    table = ['\\begin{tabular}{lrrrr}\\toprule',
             'Adaptation & Mean (ms) & p95 (ms) & Duration (s) & Tokens/s \\\\ \\midrule']
    for name, row in zip(['Chunked-FCFS','SLO-gated'], summary['aggregates']):
        table.append(f"{name} & {1000*row['mean_latency_s']:.3f} & {1000*row['p95_latency_s']:.3f} & {row['first_arrival_to_final_completion_s']:.3f} & {row['token_throughput']:.3f} " + r'\\')
    table += [r'\bottomrule\end{tabular}']
    (output/'example-aggregates.tex').write_text('\n'.join(table)+'\n')
    table = [r'\begin{tabular}{rrrrrrr}\toprule',
        r'ID & Prompt/output & Arrival & \multicolumn{2}{c}{Wait to prefill} & \multicolumn{2}{c}{Completion time} \\',
        r' & (tokens) & (ms) & C (ms) & S (ms) & C (ms) & S (ms) \\ \midrule']
    for rid in manifest['selected_request_ids']:
        c, s = requests[rid], requests[200+rid]
        values = [c['arrival_s'], c['waiting_to_prefill_s'], s['waiting_to_prefill_s'], c['completion_s'],s['completion_s']]
        table.append(f"{rid} & {c['prompt']}/{c['output']} & " + ' & '.join(f'{1000*v:.3f}' for v in values)+r' \\')
    table += [r'\bottomrule\end{tabular}']
    (output/'example-requests.tex').write_text('\n'.join(table)+'\n')
    print(json.dumps({k:v for k,v in summary.items() if k!='events'},indent=2))


if __name__ == '__main__':
    main()
