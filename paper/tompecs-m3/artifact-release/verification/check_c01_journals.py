# Adapted from the PR17 saved-record checker; no experiment execution.
import argparse
_parser=argparse.ArgumentParser()
_parser.add_argument('candidate',type=str)
_parser.add_argument('output',type=str)
_args=_parser.parse_args()
import json,pathlib,sys,gzip,hashlib,time
sys.dont_write_bytecode=True;p=pathlib.Path(_args.candidate)/'evidence/c01';sys.path.insert(0,str(p/'research/lssp-c01'));from validator import validate
sp=json.loads((p/'launch.json').read_text());manifest=json.loads((p/sp['manifest']).read_text());inputs=json.loads((p/sp['inputs']).read_text());conditions={x['condition_id']:x for x in inputs['conditions']};profiles={x['name']:x['config'] for x in manifest['profiles']};sample=json.loads(pathlib.Path(__file__).with_name('c01-journal-sample-index.json').read_text());t=time.monotonic()
for x in sample:
 d=p/x['result_path'];r=json.loads((d/'result.json').read_text());assert hashlib.sha256((d/'events.jsonl.gz').read_bytes()).hexdigest()==x['journal_sha256']
 with gzip.open(d/'events.jsonl.gz','rt') as stream:metrics=validate(conditions[x['condition_id']]['requests'],profiles[x['profile']],(json.loads(line) for line in stream),r['terminal'])
 assert metrics==x['metrics']
result=dict(sample_journals=24,selection='first nonpilot window per source, both capacities, all four adaptations, HIGH_PRESSURE',event_referee='PASS',elapsed_seconds=time.monotonic()-t);print(result);pathlib.Path(_args.output).write_text(json.dumps(result,indent=2))

assert len(sample)==24
