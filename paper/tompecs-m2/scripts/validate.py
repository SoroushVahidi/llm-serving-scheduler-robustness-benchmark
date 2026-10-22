"""M2 document and preservation checks. Never writes inherited paths."""
from pathlib import Path
import hashlib,json,re,subprocess
import pymupdf
ROOT=Path(__file__).resolve().parents[3];B=ROOT/'paper/tompecs-m2';E=B/'evidence';BASE='366752a76f86dec30190f3e7767124f684378de4';checks={};details={};sha=lambda b:hashlib.sha256(b).hexdigest()
main=(B/'revised/main.tex').read_text();body='\n'.join((B/(p+'.tex')).read_text() for p in re.findall(r'\\input\{([^}]+)\}',main));txt=main+'\n'+body
labels=re.findall(r'\\label\{([^}]+)\}',txt);refs=re.findall(r'\\(?:ref|pageref|autoref)\{([^}]+)\}',txt);bib=(B/'revised/references.bib').read_text();keys=re.findall(r'@\w+\{([^,]+),',bib);cites=[k.strip() for ss in re.findall(r'\\cite\w*\{([^}]+)\}',txt) for k in ss.split(',')]
checks['references_resolve']=not(set(refs)-set(labels));checks['labels_unique']=len(labels)==len(set(labels));checks['citations_resolve']=not(set(cites)-set(keys));checks['bibliography_keys_unique']=len(keys)==len(set(keys));checks['figure_descriptions']=len(re.findall(r'\\begin\{figure\}',txt))==txt.count('\\Description{');checks['no_template_overrides']=not any(s in txt for s in ['\\geometry','\\fontsize','\\linespread','\\setlength{\\text','\\baselinestretch','\\vspace{-','\\sloppy']);checks['unchanged_class']=(B/'template/acmart.cls').read_bytes()==(ROOT/'paper/tompecs-m1/template/acmart.cls').read_bytes()
bad=[];lfs=[];n=0
for line in subprocess.check_output(['git','ls-tree','-r',BASE],cwd=ROOT,text=True).splitlines():
 meta,name=line.split('\t',1)
 if meta.split()[1]!='blob':continue
 p=ROOT/name;n+=1
 if not p.exists():bad.append(name);continue
 actual=subprocess.check_output(['git','hash-object','--no-filters',str(p)],cwd=ROOT,text=True).strip()
 if actual!=meta.split()[2]:
  ptr=subprocess.check_output(['git','show',BASE+':'+name],cwd=ROOT);m=re.fullmatch(rb'version https://git-lfs.github.com/spec/v1\noid sha256:([0-9a-f]{64})\nsize ([0-9]+)\n',ptr)
  if m and sha(p.read_bytes())==m[1].decode() and p.stat().st_size==int(m[2]):lfs.append(name)
  else:bad.append(name)
checks['all_inherited_files_unchanged']=not bad;details['preservation']={'base':BASE,'files':n,'mismatches':bad,'hydrated_lfs':lfs,'consolidated_sha256':sha((ROOT/'dataset/v1.1.0/scientific/campaign/consolidated.json').read_bytes())}
review=[]
for p in sorted((ROOT/'paper/tompecs-m1').rglob('*')):
 if not p.is_file() or 'build' in p.parts:continue
 raw=p.read_bytes();row={'path':str(p.relative_to(ROOT)),'sha256':sha(raw),'bytes':len(raw)}
 if p.suffix=='.pdf':
  d=pymupdf.open(p);row['pages']=len(d);row['extracted_text_characters']=sum(len(page.get_text()) for page in d)
 elif p.suffix=='.json':row['json_parsed']=True;json.loads(raw)
 else:row['text_lines']=len(raw.decode(errors='replace').splitlines())
 review.append(row)
(E/'m1-review-inventory.json').write_text(json.dumps(review,indent=2)+'\n')
alloc={}
for mode in ['manuscript','acmsmall']:
 job='revised-'+mode;bd=B/'build'/job;pdf=bd/(job+'.pdf');doc=pymupdf.open(pdf);log=(bd/(job+'.log')).read_text();checks[mode+'_pages_under_30']=len(doc)<=30
 checks[mode+'_no_unresolved_refs_or_overfull']=not re.search(r'(There were undefined references|Citation .* undefined|Reference .* undefined|multiply defined|Overfull \\hbox|Overfull \\vbox)',log);checks[mode+'_no_tex_error']='! ' not in log
 titles=[re.sub(r'^\d+ ','',x[1]) for x in doc.get_toc() if x[0]==1 and x[1]!='Abstract']+['Artifact availability and declarations'];starts=[('Front matter',1,0.)]
 for title in titles:
  hits=[]
  for pi,page in enumerate(doc):
   for block in page.get_text('dict')['blocks']:
    for line in block.get('lines',[]):
     if ''.join(ss['text'] for ss in line['spans']).casefold().strip()==title.casefold().strip():hits.append((pi+1,line['bbox'][1]/page.rect.height))
  assert len(hits)==1,(title,hits)
  starts.append((title,*hits[0]))
 starts.sort(key=lambda x:x[1]+x[2]);sections=[]
 for i,(title,page,y) in enumerate(starts):
  end=starts[i+1][1]-1+starts[i+1][2] if i+1<len(starts) else len(doc);sections.append({'title':title,'page':page,'extent':round(end-(page-1+y),3)})
 alloc[mode]={'pages':len(doc),'sha256':sha(pdf.read_bytes()),'sections':sections}
 (E/'validation'/f'{job}.log.txt').write_text(log)
 for ext in ['bbl','blg','fls']:(E/'validation'/f'{job}.{ext}.txt').write_bytes((bd/(job+'.'+ext)).read_bytes())
 (B/(job+'.pdf')).write_bytes(pdf.read_bytes())
(E/'page-counts.json').write_text(json.dumps(alloc,indent=2)+'\n')
lines=['# M2 section/page allocation','','All pages include references and declarations. Extents are approximate geometric page fractions from visible headings; floats may cross section boundaries. ACM 2.20 typography is unchanged.']
for mode,x in alloc.items():
 lines+=['',f'## {mode}: {x["pages"]} pages','','| Section | Starts | Extent |','|---|---:|---:|']+[f'| {v["title"]} | {v["page"]} | {v["extent"]:.2f} |' for v in x['sections']]
(B/'LENGTH_INVENTORY.md').write_text('\n'.join(lines)+'\n')
report={'checks':checks,'passed':sum(checks.values()),'failed':sum(not x for x in checks.values()),'details':details};(E/'document-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2));assert all(checks.values())
