"""Campaign identity utilities; the CM-0.1 implementation remains untouched."""
import hashlib, json, os, sys, datetime
from pathlib import Path
HERE=Path(__file__).resolve().parent
PILOT=HERE.parent/'lssp-c01'
sys.path.insert(0,str(PILOT))
from engine import simulate
from policies import Config
from validator import validate
from run import events, checked_cell

def read(p): return json.loads(Path(p).read_text())
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def digest(x): return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
def stamp(): return datetime.datetime.now(datetime.timezone.utc).isoformat()
def atomic(p,x):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
    tmp=p.with_name(p.name+f'.{os.getpid()}.tmp')
    with tmp.open('w') as f:
        json.dump(x,f,sort_keys=True,indent=2,allow_nan=False);f.write('\n');f.flush();os.fsync(f.fileno())
    os.replace(tmp,p)
def immutable(p,x):
    p=Path(p)
    if p.exists():
        if read(p)!=x: raise ValueError('immutable artifact collision: '+str(p))
    else: atomic(p,x)
def key(c,p,policy): return c['condition_id']+'::'+p['name']+'::'+policy
def cell_id(k): return hashlib.sha256(k.encode()).hexdigest()[:24]
def plan(data,manifest):
    rows=[(key(c,p,a),c,p,a) for c in data['conditions'] for p in manifest['profiles'] for a in manifest['policies']]
    if len(rows)!=manifest['expected_cells'] or len({r[0] for r in rows})!=len(rows):raise ValueError('nonunique/incomplete plan')
    return rows

def check_inputs(data,manifest):
    actual=[{k:v for k,v in c.items() if k!='requests'} for c in data['conditions']]
    if actual!=manifest['conditions']:raise ValueError('manifest/condition mismatch')
    for c in data['conditions']:
        if digest(c['requests'])!=c['requests_sha256']:raise ValueError('request fingerprint mismatch')
    return plan(data,manifest)

def check_record(directory,c,p,a,identity,expected_hash=None):
    if expected_hash and sha(directory/'result.json')!=expected_hash:raise ValueError('reused result hash mismatch')
    r=checked_cell(directory,c,p,a,identity)
    if r['requests_sha256']!=c['requests_sha256'] or r['validated'] is not True:raise ValueError('record input/validation mismatch')
    return r
