import json,hashlib,urllib.request
from pathlib import Path
from robustbench.serving_v2.p2b.hook import patched_schedule
from robustbench.serving_v2.p2a.pins import PINS
import vllm
h=Path('docs/serving-contract/p2b-0.1.0/evidence')
_,patch,digest=patched_schedule()
(h/'scheduler.patch').write_text(patch)
(h/'patch-identity.json').write_text(json.dumps(dict(patched_schedule_sha256=digest,hook_id='vllm-0.27.1-exact-span-hook/0.1.0'),indent=2)+'\n')
Path('src/robustbench/serving_v2/p2b/pins.py').write_text('"""Identity metadata only; no policy or adapter logic."""\nPATCH_SHA256 = '+repr(digest)+'\n')
root=Path(vllm.__file__).parent
records={}
for name in list(PINS)+['config/scheduler.py']:
 data=(root/name).read_bytes()
 url='https://raw.githubusercontent.com/vllm-project/vllm/v0.27.1/vllm/'+name
 if name in ('v1/core/sched/scheduler.py','config/scheduler.py'):
  assert urllib.request.urlopen(url,timeout=20).read()==data
 records[name]={'sha256':hashlib.sha256(data).hexdigest(),'url':url,'matches_prior_pin':name not in PINS or hashlib.sha256(data).hexdigest()==PINS[name]}
 assert records[name]['matches_prior_pin']
(h/'source-hashes.json').write_text(json.dumps(records,indent=2)+'\n')
print('PASS patch/source identity',digest)
