#!/usr/bin/env python3
"""Package already-built review PDFs and hash the manuscript deliverables."""
import hashlib,json,pathlib,shutil,re
ROOT=pathlib.Path(__file__).resolve().parents[1]
v=json.loads((ROOT/'evidence/validation/validation.json').read_text());assert v['status']=='PASS'
for mode in ['manuscript','acmsmall']:
 shutil.copyfile(ROOT/f'build/{mode}/m3-{mode}.pdf',ROOT/f'm3-{mode}.pdf')
files={}
for p in sorted(ROOT.rglob('*')):
 rel=p.relative_to(ROOT)
 if not p.is_file() or 'build' in rel.parts or '__pycache__' in rel.parts or str(rel)=='evidence/package-manifest.json':continue
 files[str(rel)]={'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'bytes':p.stat().st_size}
tex='\n'.join(p.read_text() for p in (ROOT/'sections').glob('*.tex'))
out={'status':'COMPLETED_SUCCESS','review_base':'6b2eedd7aa254986b85c1bb901587641cbeac8b0','revision_base':'2a65c0e139d1410475170781469901559960265d','pages':{m:x['pages'] for m,x in v['builds'].items()},'figures':len(re.findall(r'\\begin\{figure\}',tex)),'tables':len(re.findall(r'\\begin\{table\}',tex)),'files':files}
(ROOT/'evidence/package-manifest.json').write_text(json.dumps(out,indent=2)+'\n')
print('Packaged',len(files),'files;',out['pages'])
