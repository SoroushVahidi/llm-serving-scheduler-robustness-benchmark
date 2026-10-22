#!/usr/bin/env python3
"""Copy the final small manuscript packet; never copy or modify raw evidence."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--destination',type=Path,required=True)
parser.add_argument('--implementation-commit',required=True)
args=parser.parse_args()
paper=Path(__file__).resolve().parents[1]
repo=paper.parents[1]
destination=args.destination.resolve()
assert not destination.exists(), 'Use a new versioned destination, preserving earlier candidates'
assert 'lssp-m3-rc1-20261022' not in destination.parts
manifest=json.loads((paper/'evidence/package-manifest.json').read_text())
for name,entry in manifest['files'].items():
    path=paper/name
    assert hashlib.sha256(path.read_bytes()).hexdigest()==entry['sha256'],name
    assert path.stat().st_size==entry['bytes']
final_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=repo,text=True).strip()
branch=subprocess.check_output(['git','branch','--show-current'],cwd=repo,text=True).strip()
assert branch=='manuscript/lssp-m3-major-revision'
assert not subprocess.check_output(['git','status','--porcelain','--','paper/tompecs-m3'],cwd=repo,text=True).strip()
destination.mkdir(parents=True)
for name in [*manifest['files'],'evidence/package-manifest.json']:
    target=destination/'paper/tompecs-m3'/name
    target.parent.mkdir(parents=True,exist_ok=True)
    shutil.copyfile(paper/name,target)
identities=dict(source_commit='2a65c0e139d1410475170781469901559960265d',
    implementation_commit=args.implementation_commit,final_commit=final_commit,branch=branch,
    evidence_archive_sha256='9543ed38051c95a3b781dd0bc1086e049d4d08b56aa0ad7e06d603dc93457e9b',
    upstream_sources_archive_sha256='a6d3ef2647492e79c580ab85eecf6cd47a9107d33ac4dc08757bda0900077853')
(destination/'COMMITS.json').write_text(json.dumps(identities,indent=2)+'\n')
(destination/'README.md').write_text(
    '# M3 major-revision manuscript companion v1\n\nLocal only; no public release or license grant. '
    'The complete revised manuscript packet is in `paper/tompecs-m3/`. '
    'Pair it with unchanged rc1 evidence; no raw archive is duplicated. '
    'See `paper/tompecs-m3/major-revision/COMPANION.md` for read-only reproduction, '
    'and `FINAL_REPORT.md` in that directory for the draft PR and scientific verdict.\n')
files={str(p.relative_to(destination)):{'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'bytes':p.stat().st_size}
       for p in sorted(destination.rglob('*')) if p.is_file()}
out=dict(schema='lssp-m3-major-revision-companion-v1',status='COMPLETED_SUCCESS',
         identities=identities,files=files,payload_bytes=sum(v['bytes'] for v in files.values()),
         raw_archives_included=False)
(destination/'MANIFEST.json').write_text(json.dumps(out,indent=2)+'\n')
for name,entry in files.items():
    assert hashlib.sha256((destination/name).read_bytes()).hexdigest()==entry['sha256']
print(json.dumps(dict(root=str(destination),files=len(files),payload_bytes=out['payload_bytes'],
    manifest_sha256=hashlib.sha256((destination/'MANIFEST.json').read_bytes()).hexdigest()),indent=2))
