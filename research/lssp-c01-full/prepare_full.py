"""Expand frozen input coverage only; no scheduling or outcome analysis."""
import argparse, collections, sys
from dataclasses import asdict
from pathlib import Path
from common import HERE,PILOT,read,sha,digest,immutable
sys.path.insert(0,str(HERE.parents[1]/'src'))
from prepare import FULL_HASH,CANONICAL_HASH,synthesize_requests_from_window,ExternalWorkloadRecord,_rebase_and_scale
from policies import Config,POLICIES
FREEZE_HASH='44a81e98d9a3fa6646bd716125726bf732530d243a54d0952e98b20fda1d564a'

def prepare(windows,freeze_path,pilot_inputs,out,manifest_path):
    if sha(windows)!=FULL_HASH or sha(freeze_path)!=FREEZE_HASH:raise ValueError('frozen corpus/file identity')
    full=read(windows);freeze=read(freeze_path)
    assert digest({k:v for k,v in full.items() if k not in ('generated_at_utc','content_sha256')})==CANONICAL_HASH
    ws=full['windows'];assert len(ws)==len({w['window_id'] for w in ws})==120
    assert collections.Counter(w['source_family'] for w in ws)=={s:40 for s in freeze['campaign_sources']}
    assert set(freeze['window_identities'])=={w['window_id'] for w in ws}
    seedsets=collections.defaultdict(set)
    for c in freeze['cells']:seedsets[c['window_id']].add(c['synthesis_seed'])
    metadata=[];conditions=[]
    for source in freeze['campaign_sources']:
        ordered=sorted((w for w in ws if w['source_family']==source),key=lambda w:(w['source_file_sha256'],w['arrival_time_s_min'],w['start_index_in_valid_rows'],w['window_id']))
        blocks={w['window_id']:i//10+1 for i,w in enumerate(ordered)}
        for w in (w for w in ws if w['source_family']==source):
            assert len(w['records'])==200 and digest(w['records'])==w['content_sha256']==freeze['window_identities'][w['window_id']]
            assert len(seedsets[w['window_id']])==1
            seed=next(iter(seedsets[w['window_id']]))
            raw=sorted(w['records'],key=lambda r:r['arrival_time_s'])
            base,report=synthesize_requests_from_window([ExternalWorkloadRecord(**r) for r in w['records']],window_id=w['window_id'],seed=seed)
            assert report.n_records_dropped_invalid==0 and len(base)==200
            metadata.append({**{k:w[k] for k in ('source_family','window_id','content_sha256','source_file','source_file_sha256','chronology_stratum','sampling_seed','start_index_in_valid_rows','arrival_time_s_min','arrival_time_s_max')},'block':blocks[w['window_id']]})
            for region in freeze['campaign_regions']:
                cid=source+'::'+w['window_id']+'::'+region;factor=freeze['region_assignment_index'][cid]['absolute_load_factor']
                scaled=_rebase_and_scale(base,factor);requests=[]
                for i,(r,original) in enumerate(zip(scaled,raw)):
                    assert r.request_id==i and (r.prompt_tokens,r.actual_output_tokens)==(original['input_tokens'],original['output_tokens'])
                    assert abs(r.arrival_time-(original['arrival_time_s']-raw[0]['arrival_time_s'])/factor)<1e-7
                    assert 0<r.prompt_tokens and 0<r.actual_output_tokens and r.prompt_tokens+r.actual_output_tokens<=32768
                    requests.append(dict(id=i,source_record_id=original['source_record_id'],derived_record_id=original['derived_record_id'],arrival=r.arrival_time,prompt=r.prompt_tokens,output=r.actual_output_tokens,deadline=r.slo_deadline,priority=r.priority,historical_prediction=r.predicted_output_tokens))
                conditions.append(dict(condition_id=cid,source=source,window=w['window_id'],region=region,synthesis_seed=seed,load_factor=factor,requests=requests,requests_sha256=digest(requests)))
    assert len(conditions)==720 and len({c['condition_id'] for c in conditions})==720
    original=read(pilot_inputs);byid={c['condition_id']:c for c in conditions}
    for c in original['conditions']:assert {k:v for k,v in c.items() if k!='historical'}==byid[c['condition_id']]
    assert len(original['conditions'])==18
    payload=dict(schema='lssp-c01-full-inputs/1',conditions=conditions)
    immutable(out,payload)
    overlap=[]
    for i,a in enumerate(metadata):
        for b in metadata[i+1:]:
            if a['source_file_sha256']==b['source_file_sha256']:
                n=max(0,min(a['start_index_in_valid_rows']+200,b['start_index_in_valid_rows']+200)-max(a['start_index_in_valid_rows'],b['start_index_in_valid_rows']))
                if n:overlap.append(dict(a=a['window_id'],b=b['window_id'],overlapping_row_coordinates=n))
    manifest=dict(schema='lssp-c01-full-manifest/1',input_sha256=sha(out),full_windows_sha256=FULL_HASH,full_windows_canonical=CANONICAL_HASH,freeze_sha256=FREEZE_HASH,
      conditions=[{k:v for k,v in c.items() if k!='requests'} for c in conditions],windows=metadata,row_overlaps=overlap,
      profiles=[dict(name='kv131072',config=asdict(Config())),dict(name='kv262144',config=asdict(Config(kv_capacity=262144)))],policies=list(POLICIES),regions=freeze['campaign_regions'],expected_cells=5760,pilot_matching_cells=144,
      sources=freeze['campaign_sources'],inference='DESCRIPTIVE_FINITE_CORPUS_ONLY',model='CM-0.1',burstgpt_disclosure=full['burstgpt_independence_disclosure'])
    immutable(manifest_path,manifest)
    print({'input_sha256':sha(out),'cells':5760,'pilot_exact_matches':144,'row_overlap_pairs':len(overlap)})
if __name__=='__main__':
    p=argparse.ArgumentParser()
    for n in ('windows','freeze','pilot-inputs','out','manifest'):p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();prepare(a.windows,a.freeze,a.pilot_inputs,a.out,a.manifest)
