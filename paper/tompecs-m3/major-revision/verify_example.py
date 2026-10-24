#!/usr/bin/env python3
"""Independent NumPy/event reconstruction of the fixed illustration.

Does not import analyze_example, engine, policies, or a simulation runner.
Rebuilds all 200 request timelines from both saved journals, then compares
CSV/JSON and displayed table numbers. Writes only the requested report.
"""
import argparse
import csv
import gzip
import hashlib
import json
from pathlib import Path
import numpy as np

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('artifact_root', type=Path)
parser.add_argument('--derived', type=Path, default=Path(__file__).parent)
parser.add_argument('--report', type=Path, required=True)
args = parser.parse_args()
root = args.artifact_root.resolve()
assert root not in args.report.resolve().parents
support = Path(__file__).parent
m = json.loads((support/'example-manifest.json').read_text())
for path, expected in m['files'].items():
    raw = (root/path).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == expected['sha256'] and len(raw)==expected['bytes']
inputs = json.loads((root/m['input_path']).read_text())
req = next(c['requests'] for c in inputs['conditions'] if c['condition_id']==m['condition_id'])
assert hashlib.sha256(json.dumps(req,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()==m['requests_sha256']
n = len(req); assert n==200
arrival = np.array([r['arrival'] for r in req]); prompt = np.array([r['prompt'] for r in req]); output=np.array([r['output'] for r in req])
summary=json.loads((args.derived/'example-summary.json').read_text())
csvrequests=list(csv.DictReader((args.derived/'example-requests.csv').open()))
csvagg=list(csv.DictReader((args.derived/'example-aggregates.csv').open()))
calculations=[]; completions=[]; timelines=[]; reports=[]

def close(a,b):
    np.testing.assert_allclose(a,b,rtol=1e-12,atol=1e-12)

for pindex,row in enumerate(m['rows']):
    folder=root/'evidence/c01'/row['result_path']
    assert hashlib.sha256((folder/'result.json').read_bytes()).hexdigest()==row['result_sha256']
    assert hashlib.sha256((folder/'events.jsonl.gz').read_bytes()).hexdigest()==row['journal_sha256']
    saved=json.loads((folder/'result.json').read_text())
    progress=np.zeros((n,2),dtype=int); resident=np.zeros(n,dtype=bool)
    start=np.full(n,np.nan); first=np.full(n,np.nan); finish=np.full(n,np.nan); anchor=np.full(n,np.nan)
    admission_event=np.full(n,-1,dtype=int); clock=float(arrival.min()); event_checks=0
    event_rows=[]
    for j,line in enumerate(gzip.open(folder/'events.jsonl.gz','rt')):
        event=json.loads(line); t,end=event['time'],event['end']
        assert event['intent']==event['executed']
        available=(arrival<=clock)&np.isnan(finish)
        assert t==(clock if available.any() else float(arrival[arrival>clock].min()))
        close(end-t,.001)
        spans=np.array([[rid, int(kind=='decode'), a,b] for rid,kind,a,b in event['executed']],dtype=int)
        ids=spans[:,0]; assert len(set(ids))==len(ids)
        assert np.all(arrival[ids]<=t) and np.isnan(finish[ids]).all()
        newly=ids[np.isnan(start[ids])]
        start[newly]=t; admission_event[newly]=j
        for rid,kind,a,b in spans:
            assert a==progress[rid,kind] and b>a
            if kind:
                assert resident[rid] and progress[rid,0]==prompt[rid] and b==a+1 and b<=output[rid]
                if np.isnan(first[rid]):first[rid]=end
                anchor[rid]=end
            else:
                assert b<=prompt[rid] and b-a<=512 and progress[rid,1]==0
                if b==prompt[rid]:anchor[rid]=end
            progress[rid,kind]=b
            resident[rid]=True
        assert (spans[:,3]-spans[:,2]).sum()<=32768
        assert resident.sum()<=8
        assert event['reserved']==resident.sum()*32768
        assert event['used']==int((((progress[resident].sum(axis=1)+15)//16)*16).sum())
        completed=np.flatnonzero(resident & (progress[:,1]==output))
        assert completed.tolist()==event['completed']
        finish[completed]=end; resident[completed]=False
        if j in [13,14,15,16,26,223]:
            event_rows.append(dict(policy=row['policy'],event_zero_based=j,time_s=t,end_s=end,
                admissions=newly.tolist(),completed=completed.tolist(),reserved_tokens=event['reserved']))
        clock=end;event_checks+=1
    assert not resident.any() and np.isfinite(finish).all()
    assert saved['terminal']['batches']==event_checks and saved['terminal']['observed_end']==clock
    for i,state in enumerate(saved['terminal']['requests']):
        assert state==dict(id=i,prefilled=int(progress[i,0]),generated=int(progress[i,1]),resident=False,
                          first=float(first[i]),completion=float(finish[i]),anchor=float(anchor[i]))
    expected_events=[e for e in summary['events'] if e['policy']==row['policy']]
    assert expected_events==event_rows
    lat=finish-arrival; duration=finish.max()-arrival.min()
    numeric=dict(completed=n,output_tokens=int(output.sum()),mean_latency_s=float(lat.mean()),
        p95_latency_s=float(np.quantile(lat,.95,method='linear')),
        first_arrival_to_final_completion_s=float(duration),token_throughput=float(output.sum()/duration),
        sum_latency_s=float(lat.sum()))
    for key,val in numeric.items():
        close(val,summary['aggregates'][pindex][key]);close(val,float(csvagg[pindex][key]))
    for key,metric in [('mean_latency_s','mean_latency'),('p95_latency_s','p95_latency'),('token_throughput','token_throughput')]:
        close(numeric[key],saved['metrics'][metric]);close(numeric[key],row['metrics'][metric])
    table=(args.derived/'example-aggregates.tex').read_text()
    for val in [lat.mean()*1000,np.quantile(lat,.95)*1000,duration,output.sum()/duration]:assert f'{val:.3f}' in table
    for r in csvrequests:
        if r['policy']!=row['policy']:continue
        i=int(r['id'])
        for key in ['source_record_id','derived_record_id']:assert r[key]==req[i][key]
        numbers=dict(prompt=prompt[i],output=output[i],arrival_s=arrival[i],first_prefill_start_s=start[i],
            first_prefill_event=admission_event[i],waiting_to_prefill_s=start[i]-arrival[i],
            first_output_s=first[i],ttft_s=first[i]-arrival[i],completion_s=finish[i],latency_s=lat[i])
        for key,val in numbers.items():close(val,float(r[key]))
        request_table=(args.derived/'example-requests.tex').read_text()
        assert f'{prompt[i]}/{output[i]}' in request_table
        for val in [arrival[i],start[i]-arrival[i],finish[i]]:assert f'{val*1000:.3f}' in request_table
    order=np.argsort(lat,kind='stable');brackets=order[189:191]
    reports.append(dict(policy=row['policy'],journal_events=event_checks,terminal_states_verified=n,
        p95_bracket_ids=brackets.tolist(),p95_bracket_latency_s=lat[brackets].tolist(),
        final_request_ids=np.flatnonzero(finish==finish.max()).tolist()))
    calculations.append(numeric);completions.append(finish);timelines.append((start,first,finish,admission_event))

delta=completions[1]-completions[0]
for key,val in [('earlier',int((delta<0).sum())),('later',int((delta>0).sum())),('unchanged',int((delta==0).sum()))]:assert summary[key]==val
close(summary['sum_completion_difference_s'],delta.sum())
for key,val in summary['relative_change_percent'].items():close(val,100*(calculations[1][key]-calculations[0][key])/calculations[0][key])
assert int(delta.argmin())==196 and int(delta.argmax())==26
# Independently check the declared retrospective selection against frozen summary arrays.
rows=json.loads(gzip.decompress((support.parent/'evidence/inputs/c01-absolute_metrics.json.gz').read_bytes()))
groups={}
for r in rows:
    if r['source']=='burstgpt':groups.setdefault((r['window'],r['region'],r['profile']),{})[r['policy']]=r
keys=sorted(groups);values=np.array([[groups[k][p]['metrics'][metric] for p in ['chunked_fcfs_c01','slo_gated_c01'] for metric in ['mean_latency','token_throughput','p95_latency']] for k in keys])
mask=(values[:,3]<values[:,0])&(values[:,4]<values[:,1])&(values[:,5]>values[:,2])
assert int(mask.sum())==m['eligible_conditions']
assert keys[int(np.flatnonzero(mask)[0])]==(m['window'],m['region'],m['profile'])
# First differing admitted membership, ignoring harmless order within a batch.
start_c,start_s=timelines[0][0],timelines[1][0]
times=np.unique(np.concatenate([start_c,start_s]))
first_difference=next(t for t in times if set(np.flatnonzero(start_c==t))!=set(np.flatnonzero(start_s==t)))
close(first_difference,.014)
assert np.flatnonzero(start_c==first_difference).tolist()==[13]
assert np.flatnonzero(start_s==first_difference).tolist()==[14]
assert req[13]['arrival']==req[14]['arrival'] and prompt[14]<prompt[13]
text=(support.parent/'sections/example.tex').read_text()
for literal in ['40.60','33.17','14.63','151','29','20','5.008','189.05','191/195','139/68']:
    assert literal in text, literal
close(timelines[0][0][26],.026);close(timelines[1][0][26],.223)
close(timelines[0][1][26],.031);close(timelines[1][1][26],.228)
assert prompt[26]==1976 and output[26]==1120 and output.sum()==3520
assert [summary[k] for k in ['earlier','later','unchanged']]==[151,29,20]
assert [f"{abs(summary['relative_change_percent'][k]):.2f}" for k in ['mean_latency_s','p95_latency_s','token_throughput']]==['40.60','33.17','14.63']
assert f'{abs(delta.sum()):.3f}'=='5.008'
assert reports[0]['p95_bracket_ids']==[191,195] and reports[1]['p95_bracket_ids']==[139,68]
report=dict(status='PASS',method='NumPy array metrics from independently reconstructed saved event timelines; no analysis-generator imports',
    selection_verified=True,files_hashed=len(m['files']),requests_per_policy=n,policies=reports,
    maximum_numeric_tolerance=1e-12,all_derived_csv_fields_checked=True,displayed_tables_checked=True,
    first_membership_difference_s=float(first_difference),experiments_executed=0,
    support_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in
        [support/'analyze_example.py',support/'verify_example.py',support/'example-manifest.json',
         *[args.derived/name for name in ['example-summary.json','example-aggregates.csv','example-requests.csv','example-aggregates.tex','example-requests.tex']]]})
args.report.parent.mkdir(parents=True,exist_ok=True)
args.report.write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
