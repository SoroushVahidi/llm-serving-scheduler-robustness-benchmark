"""Build/test a wheel in a disposable external directory, without network/CI."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import zipfile

root = Path(__file__).resolve().parents[3]
with tempfile.TemporaryDirectory(prefix='lssp-p1-package-') as directory:
    tmp = Path(directory)
    project = tmp/'project'; project.mkdir()
    shutil.copy2(root/'pyproject.toml', project/'pyproject.toml')
    shutil.copytree(root/'src', project/'src', ignore=shutil.ignore_patterns('__pycache__', '*.egg-info'))
    environment = dict(os.environ, PIP_NO_INDEX='1', SOURCE_DATE_EPOCH='315532800', PYTHONDONTWRITEBYTECODE='1')
    build = subprocess.run([sys.executable,'-B','-m','pip','wheel',str(project),'--no-deps',
        '--no-build-isolation','--no-index','--wheel-dir',str(tmp/'wheels')],
        capture_output=True, text=True, env=environment, check=True)
    wheel, = (tmp/'wheels').glob('*.whl')
    with zipfile.ZipFile(wheel) as z:
        members = z.namelist()
        for part in ('__init__.py','ledger.py','reference.py'):
            assert 'robustbench/serving_v2/'+part in members
    code = '''import sys
sys.path.insert(0, sys.argv[1])
from robustbench.serving_v2.reference import validate
assert 'robustbench.serving_v2.ledger' not in sys.modules
from robustbench.serving_v2.ledger import Ledger
assert validate(Ledger('wheel-test').export()).valid
assert not any(name in sys.modules for name in ('torch','vllm','numpy'))
print('wheel imports isolated; no heavy dependencies; reference independent')
'''
    smoke = subprocess.run([sys.executable,'-I','-S','-B','-c',code,str(wheel)],cwd=tmp,
                            capture_output=True,text=True,check=True)
    print(json.dumps({'status':'PASS_CPU_PACKAGING','python':sys.version,
        'wheel':wheel.name,'wheel_sha256':hashlib.sha256(wheel.read_bytes()).hexdigest(),
        'source_date_epoch':environment['SOURCE_DATE_EPOCH'],
        'source_directory_modified':False,'build_stdout':build.stdout,'build_stderr':build.stderr,
        'import_check':smoke.stdout},indent=2))
