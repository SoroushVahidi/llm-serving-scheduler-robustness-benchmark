"""Regenerate frozen ABL tables in an isolated directory from saved result JSONs."""
import csv,hashlib,json,os,pathlib,shutil,sys,time
R=pathlib.Path(__file__).parent;S=R/'saved/abl01';D=R/'reproduction/abl01'
D.mkdir(parents=True,exist_ok=False)
for n in ['manifest.json','baseline-index.json']:shutil.copyfile(S/n,D/n)
m=json.loads((S/'manifest.json').read_text())
with (S/'analysis/telemetry.csv').open() as f:header=next(csv.reader(f))
meta={'cell_id','source','window','region','profile','arm'};order=[x for x in header if x not in meta]
derived={}
for c in m['cells']:
 r=json.loads((S/'derived-controls'/c['cell_id']/'result.json').read_text())
 # JSON object order is not semantic. Restore the frozen CSV schema order.
 for field in ['telemetry','baseline_telemetry']:
  assert set(r[field])==set(order)
  r[field]={k:r[field][k] for k in order}
 derived[c['cell_id']]=r
sys.dont_write_bytecode=True
sys.path.insert(0,str(S/'code/research/m3-abl01'))
from analysis import analyze
start=time.monotonic();analyze(D,m,derived)
checks={}
for p in (S/'analysis').iterdir():
 if p.is_file():
  a=hashlib.sha256(p.read_bytes()).hexdigest();b=hashlib.sha256((D/'analysis'/p.name).read_bytes()).hexdigest()
  checks[p.name]={'expected_sha256':a,'regenerated_sha256':b,'identical':a==b}
assert all(x['identical'] for x in checks.values()),checks
(R/'review/abl01-frozen-analysis-reproduction.json').write_text(json.dumps({'status':'PASS','seconds':time.monotonic()-start,'simulations':0,'journal_reconstruction_rerun':False,'columns':'Frozen telemetry header restored after JSON deserialization; no values changed','files':checks},indent=2)+'\n')
print('PASS: all eight CSVs and verification.json reproduced byte-for-byte without simulations.')

