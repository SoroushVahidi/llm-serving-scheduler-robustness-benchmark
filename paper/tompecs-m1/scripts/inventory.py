"""Inventory compiled PDFs and preserved submission sources, without edits."""
import collections,difflib,hashlib,json,re,subprocess
from pathlib import Path
import pymupdf
ROOT=Path(__file__).resolve().parents[3];r=ROOT/'paper/tompecs-m1';e=r/'evidence'
def blob(rev,path):return subprocess.check_output(['git','show',rev+':'+path],cwd=ROOT)
def sha(b):return hashlib.sha256(b).hexdigest()
versions={'JSC':('b1f9a12','paper/jsc_submission_package'),'PEVA':('0975472','paper/peva_submission_package'),'SMPT':('cc25fcd','paper/smpt_submission_package'),'SMPT_blind':('cc25fcd','paper/smpt_blind_submission_package'),'main_source':('e73a3b7','paper')}
records={};bodies={}
for label,(rev,prefix) in versions.items():
 files=subprocess.check_output(['git','ls-tree','-r','--name-only',rev,prefix],cwd=ROOT).decode().splitlines()
 files=[f for f in files if f.endswith(('.tex','.bib','.pdf','.zip'))]
 records[label]={'revision':subprocess.check_output(['git','rev-parse',rev],cwd=ROOT).decode().strip(),'prefix':prefix,'files':{}}
 bodies[label]={}
 for f in files:
  b=blob(rev,f);records[label]['files'][f]={'bytes':len(b),'sha256':sha(b)}
  if f.endswith('.tex'):bodies[label][Path(f).name]=b.decode()
  if f.endswith('.pdf'):
   try:records[label]['files'][f]['pages']=len(pymupdf.open(stream=b,filetype='pdf'))
   except Exception:pass
(e/'submission-versions.json').write_text(json.dumps(records,indent=2)+'\n')
changes=[]
for a,b in [('JSC','PEVA'),('PEVA','SMPT'),('SMPT','SMPT_blind'),('SMPT','main_source')]:
 for f in sorted(bodies[a].keys()&bodies[b].keys()):
  if bodies[a][f]!=bodies[b][f]:
   diff=list(difflib.unified_diff(bodies[a][f].splitlines(),bodies[b][f].splitlines(),fromfile=a+'/'+f,tofile=b+'/'+f))
   changes.extend(diff)
(e/'submission-source-differences.diff').write_text('\n'.join(changes)+'\n')
pages={}; inventories={}
for variant in ['baseline','revised']:
 for mode in ['manuscript','acmsmall']:
  key=variant+'-'+mode;p=r/'build'/key/(key+'.pdf');doc=pymupdf.open(p);toc=[t for t in doc.get_toc(simple=False) if t[0]==1];rows=[]
  # PDF bookmarks may point at stale LaTeX anchors. Locate visible headings instead.
  titles=[re.sub(r'^\d+ ', '', x[1]) for x in toc if x[1]!='Abstract']
  if variant=='revised':titles.append('Artifact availability and declarations')
  starts=[('Front matter',1,0.0,0.0)]
  for title in titles:
   hits=[]
   for pi,page in enumerate(doc):
    for block in page.get_text('dict')['blocks']:
     for line in block.get('lines',[]):
      visible=''.join(span['text'] for span in line['spans'])
      if visible.casefold().strip()==title.casefold().strip():hits.append((pi+1,line['bbox'][1]))
   if len(hits)!=1: raise RuntimeError((key,title,'heading match count',len(hits)))
   page,y=hits[0];starts.append((title,page,y,page-1+y/doc[page-1].rect.height))
  starts.sort(key=lambda x:x[3])
  for i,(title,page,y,position) in enumerate(starts):
   end=starts[i+1][3] if i+1<len(starts) else len(doc)
   assert end>=position
   rows.append({'title':title,'starts_page':page,'visible_heading_y_pt':y,'estimated_page_extent':round(end-position,3)})
  pages[key]={'pages':len(doc),'sha256':sha(p.read_bytes()),'sections':rows,'note':'Starts from exact visible PDF heading text, not potentially stale LaTeX bookmark destinations. Extents are geometric fractions of full media-box height, include intervening floats/white space, and are estimates.'}
  texs=list((r/variant/'sections').glob('*.tex'));floats=[];paras=[]
  for f in texs:
   t=f.read_text()
   for match in re.finditer(r'\\begin\{(figure|table)\}.*?\\end\{\1\}',t,re.S):
    block=match[0];caption=re.search(r'\\caption\{(.*?)\}.*?\\label\{(.*?)\}',block,re.S);floats.append({'file':str(f.relative_to(r)),'kind':match[1],'label':caption[2] if caption else None,'source_words':len(block.split()),'caption_source':caption[1] if caption else None})
   for block in t.split('\n\n'):
    if len(block.split())>=70:paras.append({'file':str(f.relative_to(r)),'words':len(block.split()),'beginning':block[:140]})
  inventories[variant]={'floats':floats,'largest_paragraphs':sorted(paras,key=lambda x:-x['words'])[:15],'section_source_words':{f.stem:len(f.read_text().split()) for f in texs}}
(e/'page-counts.json').write_text(json.dumps(pages,indent=2)+'\n');(e/'float-text-inventory.json').write_text(json.dumps(inventories,indent=2)+'\n')
budgets=[('Front matter',.75),('Introduction',2),('Background and Related Work',1.75),('Research Questions and Portability Measures',2.75),('Evaluation Model and Assumptions',3),('Workloads and Experimental Design',3),('Performance Within Operating Regions',2),('Portability Across Workloads and Regions',3.25),('Portability Across Metrics',2.75),('Robustness and Practical Implications',2),('Threats to Validity',2),('Conclusion',.5),('References',3.25)]
lines=['# Length inventory','','Planning budget: **29 pages including references**. No margin, font-size or spacing changes were made to fit it. ACM standard template typography is retained. Declarations are separately visible; they count in the total. The revised draft intentionally leaves headroom rather than padding uncertain claims.','','| Component | Target pages |','|---|---:|']+[f'| {x} | {v:.2f} |' for x,v in budgets]
for key,d in pages.items():
 lines+=['',f'## {key}: {d["pages"]} pages','','| Top-level component | Starts on PDF page | Estimated extent |','|---|---:|---:|']+[f'| {x["title"]} | {x["starts_page"]} | {x["estimated_page_extent"]:.2f} |' for x in d['sections']]
lines+=['','Page starts locate exact visible PDF headings. Extents are geometric full-page fractions, not typeset occupied area; shared pages and floats prevent treating each section as a separate integer page count. See `evidence/page-counts.json` for coordinates and PDF hashes. All PDF pages, including references and declarations, count in reported totals. No supplement has been used to bypass the cap.']
(r/'LENGTH_INVENTORY.md').write_text('\n'.join(lines)+'\n')
print({k:v['pages'] for k,v in pages.items()})
