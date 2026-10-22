"""Two offline disposable wheel builds; isolated stdlib-only referee import."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import zipfile

ROOT=Path(__file__).resolve().parents[3]
with tempfile.TemporaryDirectory(prefix='lssp-p2b-wheel-') as directory:
    tmp=Path(directory); project=tmp/'project';project.mkdir()
    shutil.copy2(ROOT/'pyproject.toml',project/'pyproject.toml')
    shutil.copytree(ROOT/'src',project/'src',ignore=shutil.ignore_patterns('__pycache__','*.egg-info'))
    env=dict(os.environ,PIP_NO_INDEX='1',PIP_NO_CACHE_DIR='1',SOURCE_DATE_EPOCH='315532800',PYTHONDONTWRITEBYTECODE='1')
    hashes=[];logs=[]
    for i in range(2):
        dest=tmp/f'wheels-{i}'
        build=subprocess.run([sys.executable,'-B','-m','pip','wheel',str(project),'--no-deps',
            '--no-build-isolation','--no-index','--wheel-dir',str(dest)],capture_output=True,text=True,env=env,check=True)
        wheel,=dest.glob('*.whl');hashes.append(hashlib.sha256(wheel.read_bytes()).hexdigest())
        logs.append(build.stdout)
        with zipfile.ZipFile(wheel) as archive:
            for name in ('__init__.py','control.py','hook.py','s02.py','reference.py','pins.py'):
                assert 'robustbench/serving_v2/p2b/'+name in archive.namelist()
    assert hashes[0]==hashes[1],hashes
    code="""import sys
sys.path.insert(0,sys.argv[1])
from robustbench.serving_v2.p2b.reference import validate
assert not validate({}).valid
assert not any(n in sys.modules for n in ('torch','vllm','numpy','robustbench.serving_v2.ledger','robustbench.serving_v2.p2a.native','robustbench.serving_v2.p2b.control','robustbench.serving_v2.p2b.s02'))
from robustbench.serving_v2.p2a.types import Span
assert Span('r',0,0,1).end==1
print('PASS isolated wheel referee/types; producer and heavy imports absent')
"""
    smoke=subprocess.run([sys.executable,'-I','-S','-B','-c',code,str(wheel)],cwd=tmp,capture_output=True,text=True,check=True)
    print(json.dumps(dict(status='PASS_OFFLINE_REPRODUCIBLE_WHEEL',hashes=hashes,
        source_date_epoch=env['SOURCE_DATE_EPOCH'],build_stdout=logs,import_result=smoke.stdout),indent=2))
