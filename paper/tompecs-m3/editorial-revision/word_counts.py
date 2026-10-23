"""Reproducible approximate prose counts, not a journal word-limit calculation.
Exclude floats/captions, displayed and inline math, citations, labels/references,
section headings, and input directives. Keep prose inside formatting commands.
Separate abstract/conclusion; no bibliography or generated table cells.
"""
import json,re,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
BASE='dda5fcf0f8f2a6f543e799f20767c9272022afc8'
def count(s):
 s=re.sub(r'(?<!\\)%[^\n]*','',s)
 for env in ['table','figure','equation','align','tikzpicture']:
  s=re.sub(r'\\begin\{'+env+r'\*?\}.*?\\end\{'+env+r'\*?\}',' ',s,flags=re.S)
 s=re.sub(r'(?<!\\)\$.*?(?<!\\)\$',' ',s,flags=re.S)
 s=re.sub(r'\\(?:cite\w*|label|ref|eqref|input|path|section\*?|subsection\*?|paragraph\*?)\{[^}]*\}',' ',s)
 s=re.sub(r'\\(?:begin|end)\{[^}]*\}(?:\[[^]]*\])?',' ',s)
 s=re.sub(r'\\[A-Za-z]+\*?(?:\[[^]]*\])?',' ',s)
 return len(re.findall(r"[A-Za-z0-9]+(?:['’\-][A-Za-z0-9]+)*",s))
def pieces(old):
 def read(f):return subprocess.check_output(['git','show',BASE+':paper/tompecs-m3/'+f],cwd=ROOT,text=True) if old else (ROOT/f).read_text()
 result={}
 t=read('main.tex');result['abstract']=t.split(r'\begin{abstract}')[1].split(r'\end{abstract}')[0]
 for name in ['introduction','related','contract','design','performance','example','rankings','inference','discussion','declarations','appendix']:
  t=read('sections/'+name+'.tex')
  if name=='discussion':t,result['conclusion']=t.split(r'\section{Conclusion}')
  result[name]=t
 return {k:count(v) for k,v in result.items()}
a,b=pieces(True),pieces(False)
rows={k:dict(before=a[k],after=b[k],change=b[k]-a[k],percent_change=round(100*(b[k]-a[k])/a[k],2)) for k in a}
main=[k for k in a if k not in ('appendix','declarations')]
x,y=sum(a[k] for k in main),sum(b[k] for k in main)
report=dict(baseline=BASE,method=__doc__,sections=rows,main_prose=dict(before=x,after=y,change=y-x,percent_change=round(100*(y-x)/x,2)))
(ROOT/'editorial-revision/word-counts.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
