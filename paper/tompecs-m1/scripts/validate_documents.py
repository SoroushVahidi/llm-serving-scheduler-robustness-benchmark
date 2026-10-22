"""Fail on unresolved manuscript references, altered originals or baseline drift."""
from pathlib import Path
import hashlib,json,re,subprocess
ROOT=Path(__file__).resolve().parents[3];r=ROOT/'paper/tompecs-m1';e=r/'evidence'
checks={};details={}
for variant in ['baseline','revised']:
 main=(r/variant/'main.tex').read_text();body='\n'.join((r/(name+'.tex')).read_text() for name in re.findall(r'\\input\{([^}]+)\}',main));text=main+'\n'+body
 labels=re.findall(r'\\label\{([^}]+)\}',text);refs=re.findall(r'\\(?:ref|pageref|autoref)\{([^}]+)\}',text)
 # Baseline intentionally retains historical missing cross-references, if present; record separately.
 missing=sorted(set(refs)-set(labels));details[variant]={'missing_refs':missing,'duplicate_labels':[x for x in labels if labels.count(x)>1]}
 if variant=='revised':checks['revised_refs_resolve']=not missing;checks['revised_unique_labels']=len(labels)==len(set(labels))
 bib=(r/('references.bib' if variant=='baseline' else 'revised/references.bib')).read_text();keys=re.findall(r'@\w+\{([^,]+),',bib);cites=[k.strip() for group in re.findall(r'\\cite\w*\{([^}]+)\}',text) for k in group.split(',')]
 checks[variant+'_citations_resolve']=not(set(cites)-set(keys));details[variant]['cited_keys']=len(set(cites));details[variant]['bib_entries']=len(keys)
 checks[variant+'_figure_descriptions']=len(re.findall(r'\\begin\{figure\}',body))==body.count('\\Description{')
 checks[variant+'_no_layout_overrides']=not any(s in main for s in ['\\geometry','\\fontsize','\\linespread','\\textheight','\\textwidth','\\baselinestretch'])
# Normalize only disclosed layout changes in the scientific body.
source='cc25fcd14f6fe28ab30d9e46635a72c0d6285d00'
for p in sorted((r/'baseline/sections').glob('*.tex')):
 original=subprocess.check_output(['git','show',source+':paper/sections/'+p.name],cwd=ROOT).decode();copy=p.read_text().replace('figures/','generated/figures/');copy=re.sub(r'\\Description\{[^}]*\}','',copy)
 checks['baseline_body_'+p.stem]=' '.join(original.split())==' '.join(copy.split())
original=subprocess.check_output(['git','show',source+':paper/main.tex'],cwd=ROOT).decode();abstract=lambda t:re.search(r'\\begin\{abstract\}(.*?)\\end\{abstract\}',t,re.S)[1]
checks['baseline_abstract_unchanged']=' '.join(abstract(original).split())==' '.join(abstract((r/'baseline/main.tex').read_text()).split())
checks['baseline_bibliography_unchanged']=subprocess.check_output(['git','show',source+':paper/references.bib'],cwd=ROOT)==(r/'references.bib').read_bytes()
# Validate every original tracked file against its Git blob, bypassing LFS filters.
rows=subprocess.check_output(['git','ls-tree','-r','HEAD'],cwd=ROOT).decode().splitlines();bad=[];n=0;lfs=[]
for line in rows:
 meta,name=line.split('\t',1);typ=meta.split()[1];expected=meta.split()[2]
 if typ!='blob' or name.startswith('paper/tompecs-m1/'):continue
 p=ROOT/name
 if not p.exists():bad.append(name);continue
 actual=subprocess.check_output(['git','hash-object','--no-filters',str(p)],cwd=ROOT).decode().strip();n+=1
 if expected!=actual:
  pointer=subprocess.check_output(['git','show','HEAD:'+name],cwd=ROOT)
  match=re.fullmatch(rb'version https://git-lfs.github.com/spec/v1\noid sha256:([0-9a-f]{64})\nsize ([0-9]+)\n',pointer)
  if match and hashlib.sha256(p.read_bytes()).hexdigest()==match[1].decode() and p.stat().st_size==int(match[2]): lfs.append(name)
  else: bad.append(name)
checks['original_tracked_files_unchanged']=not bad;details['preservation']={'checked_original_files':n,'mismatches':bad,'expanded_lfs_payloads_verified':lfs,'baseline_sha':'e73a3b711b65f9c181ff9a2674007efca22f1b65','note':'Git blobs or pinned LFS payload size/SHA-256 comparison. The known consolidated.json LFS display anomaly is not a byte change.'}
report={'checks':checks,'passed':sum(checks.values()),'failed':sum(not v for v in checks.values()),'details':details};(e/'document-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
if not all(checks.values()):raise SystemExit(1)
