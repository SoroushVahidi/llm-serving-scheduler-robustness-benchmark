# Adapted from the PR17 saved-record checker; no experiment execution.
import argparse
_parser=argparse.ArgumentParser()
_parser.add_argument('candidate',type=str)
_parser.add_argument('output',type=str)
_args=_parser.parse_args()
import json,gzip,pathlib,hashlib,sys,importlib.util,math
sys.dont_write_bytecode=True
p=pathlib.Path(_args.candidate)/'evidence';sys.path[:0]=[str(p/'stat/code'),str(p/'stat-original/code'),str(p/'stat-original/reference')]
import numpy as np
from rv2_reference import validate
from reference import validate_record
spec=json.loads((p/'stat/launch.json').read_text());sc=spec['original_launch']['scenarios'];count=0;fail=None
stats_path=p/'stat-original/reference/robustbench/ranking_portability/analysis/stats.py';modspec=importlib.util.spec_from_file_location('frozenstats',stats_path);module=importlib.util.module_from_spec(modspec);sys.modules['frozenstats']=module;modspec.loader.exec_module(module)
for selected in json.loads(pathlib.Path(__file__).with_name('stat-sample-index.json').read_text()):
 path=p/'stat'/selected
 meta=json.loads((path/'integrity.json').read_text())
 for name,h in meta['hashes'].items():assert hashlib.sha256((path/name).read_bytes()).hexdigest()==h
 raw=np.load(path/'raw.npz',allow_pickle=False)
 with gzip.open(path/'studies.json.gz','rt') as f:rr=json.load(f)
 with gzip.open(path/'secondary.json.gz','rt') as f:aa=json.load(f)
 for i,(r,a) in enumerate(zip(rr,aa)):
  sid,rep=meta['scenario'],meta['start']+i;assert validate(sc[sid],raw['y'][i],raw['mask'][i],r,a,sid,rep)
  indices=[j for j,b in enumerate(r['historical']['eligible']) if b];ps=[r['methods']['historical_screened_BH']['p'][j] for j in indices];flags=module.benjamini_hochberg(ps,q=.05);expected=[False]*165
  for j,flag in zip(indices,flags):expected[j]=bool(flag and r['historical']['supported'][j])
  assert expected==a['legacy_source_screened_BH']['reject'];count+=1
  if (sid,rep)==(11,6628):
   try:validate_record(sc[sid],raw['y'][i],raw['mask'][i],r,sid,rep)
   except ValueError as e:assert str(e)=='independent multiplicity mismatch'
   else:raise AssertionError('original failure no longer fails')
   seq=sorted(enumerate(ps),key=lambda x:x[1]);m=len(ps);j=indices.index(47);rank=next(n for n,(idx,_) in enumerate(seq,1) if idx==j);pvalue=ps[j]
   fail=dict(scenario=sid,replicate=rep,index=47,screened_family=m,rank=rank,p=pvalue,p_hex=pvalue.hex(),port_threshold=.05*rank/m,legacy_threshold=(rank/m)*.05,port_reject=r['methods']['historical_screened_BH']['reject'][47],legacy_reject=a['legacy_source_screened_BH']['reject'][47],exact_reject=a['exact_historical_screened_BH']['reject'][47])
print(json.dumps(dict(saved_studies_refereed=count,frozen_source_BH_checks=count,original_failure=fail),indent=2));pathlib.Path(_args.output).write_text(json.dumps(dict(saved_studies_refereed=count,frozen_source_BH_checks=count,original_failure=fail),indent=2))

assert count==200 and fail is not None
