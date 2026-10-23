"""Read-only editorial conformance checks; writes only the requested new report."""
from pathlib import Path
import hashlib,json,re,subprocess,sys
import pymupdf as fitz
r=Path(__file__).resolve().parents[1]; out=Path(sys.argv[1]);base='03efa8eabcf5304a514dfd002b70b05c042cde36'
h=lambda b:hashlib.sha256(b).hexdigest()
def old(n):return subprocess.check_output(['git','show',base+':paper/tompecs-m3/'+n],cwd=r)
def numbers(t):return re.findall(r'(?<![A-Za-z])[0-9]+(?:[.,][0-9]+)*',t)
checks={}
for name in ['performance','design','example','sensitivity','inference']:
 path=f'sections/{name}.tex';assert numbers(old(path).decode())==numbers((r/path).read_text()),path;checks[path+'_numbers_unchanged']=True
assert old('sections/rankings.tex')==(r/'sections/rankings.tex').read_bytes()
a=old('sections/appendix.tex').decode().split('\\section{Evidence Identities')[0]
b=(r/'sections/appendix.tex').read_text().split('\\section{Evidence Identities')[0]
assert numbers(a)==numbers(b);checks['appendix_statistical_numbers_unchanged']=True
pres=json.loads((r/'scientific-editorial-revision/preservation.json').read_text())
for name,digest in pres['protected_files'].items():assert h((r/name).read_bytes())==digest,name
assert old('PROJECT_HANDOFF.md')==(r/'PROJECT_HANDOFF.md').read_bytes();checks['frozen_handoff_unchanged']=True
tex='\n'.join(p.read_text() for p in [r/'main.tex',*sorted((r/'sections').glob('*.tex'))])
assert '\\[' not in tex and '$$' not in tex and not re.search(r'\\begin\{(?:equation|align)\*\}',tex)
labels=re.findall(r'\\label\{([^}]+)\}',tex);refs=re.findall(r'\\(?:eqref|ref)\{([^}]+)\}',tex)
assert len(labels)==len(set(labels));assert set(refs)<=set(labels)
displays=re.findall(r'\\begin\{equation\}(.*?)\\end\{equation\}',tex,re.S)
for block in displays:
 ls=re.findall(r'\\label\{([^}]+)\}',block);assert len(ls)==1 and ls[0] in refs,block
for label in labels:
 if label.startswith(('fig:','tab:')):assert label in refs,label
cites=re.findall(r'\\cite\w*(?:\[[^\]]*\])*\{([^}]+)\}',tex);assert all(len(c.split(','))<=4 for c in cites)
keys=set(re.findall(r'@\w+\{([^,]+),',(r/'references.bib').read_text()));assert keys=={k for c in cites for k in c.split(',')}
assert not any(x in tex for x in ['/home/','/project/','PEVA-D-','CONFIDENTIAL_DISCLOSURE','1444698','1444762'])
assert not any(x in tex for x in ['M3-TIME01','M3-ABL01'])
checks.update(numbered_referenced_equations=len(displays),cited_references=len(keys),figure_labels=sum(x.startswith('fig:') for x in labels),table_labels=sum(x.startswith('tab:') for x in labels),no_private_paths_or_parallel_submission_identifiers=True)
pdfs={}
for mode in ['manuscript','acmsmall']:
 p=r/f'build/{mode}/m3-{mode}.pdf';d=fitz.open(p);assert len(d)<=30
 log=p.with_suffix('.log').read_text();assert not re.search(r'Overfull|LaTeX Error|undefined references|undefined citations|multiply defined',log)
 assert len(re.findall(r'\\bibitem',p.with_suffix('.bbl').read_text()))==32
 pdfs[mode]={'pages':len(d),'sha256':h(p.read_bytes()),'bytes':p.stat().st_size}
assert json.loads((r/'scientific-editorial-revision/validation.json').read_text())['status']=='PASS'
report={'status':'PASS','base_commit':base,'checks':checks,'protected_file_count':len(pres['protected_files']),'pdfs':pdfs,'experiments_executed':0,'scientific_changes':'Only the BOUND01 theorem is newly integrated; empirical numerical claims are unchanged.'}
out.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
