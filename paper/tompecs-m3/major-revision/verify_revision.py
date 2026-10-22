#!/usr/bin/env python3
"""Focused preservation/layout/source audit for the major revision; no experiment."""
from pathlib import Path
import hashlib,json,re,subprocess
root=Path(__file__).resolve().parents[1];repo=root.parents[1]
base='2a65c0e139d1410475170781469901559960265d'
def old(name):return subprocess.check_output(['git','show',base+':paper/tompecs-m3/'+name],cwd=repo,text=True)
def now(name):return (root/name).read_text()
checks={}
def check(key,value):
 assert value,key
 checks[key]=True
r=old('sections/rankings.tex');chron=r[r.index('\\subsection{Chronological summaries}'):r.index('\\paragraph{Answer to RQ2.}')]
check('chronology_moved_intact',chron.replace('\\subsection{Chronological summaries}','\\section{Chronological Summaries}\\label{app:chronology}',1).strip() in now('sections/appendix.tex'))
r=old('sections/inference.tex');detail=r[r.index('Other\nscenarios expose'):r.index('\\paragraph{Answer to RQ3.}')]
check('stat_detail_moved_intact',detail in now('sections/appendix.tex'))
check('all_original_appendix_equations_preserved',re.findall(r'\\begin\{(?:equation|align)\}.*?\\end\{(?:equation|align)\}',old('sections/appendix.tex'),re.S)==re.findall(r'\\begin\{(?:equation|align)\}.*?\\end\{(?:equation|align)\}',now('sections/appendix.tex'),re.S))
check('abstract_terminal_wording','produce identical per-request terminal states and metrics in all 1,440 matched conditions.' in now('main.tex'))
check('ranking_wording','Absence of a strict practical reversal is weaker than equality of rankings\nor top sets.' in now('sections/rankings.tex'))
check('no_worker_remark','worker' not in now('sections/declarations.tex'))
check('larger_scenario_type',r'\centering\small\setlength{\tabcolsep}{5pt}' in now('sections/appendix.tex'))
check('no_old_generated_data_changed',json.loads(now('major-revision/preservation.json'))['status']=='PASS')
check('example_pass',json.loads(now('major-revision/example-verification.json'))['status']=='PASS')
changed=subprocess.check_output(['git','diff','--name-only',base],cwd=repo,text=True).splitlines()
check('scope_preserved',all(p.startswith('paper/tompecs-m3/') or p=='dataset/v1.1.0/scientific/campaign/consolidated.json' for p in changed))
# Every cited figure/table label must resolve in the compiled document; validate.py
# separately checks all LaTeX/citation diagnostics and both source label namespaces.
for mode in ['manuscript','acmsmall']:
 aux=now(f'build/{mode}/m3-{mode}.aux')
 labels=dict(re.findall(r'\\newlabel\{([^}]+)\}\{\{([^}]+)\}',aux))
 expected={'fig:contract':'1','fig:absolute':'2','fig:matched':'3','fig:chronology':'4',
           'tab:example-aggregate':'5','tab:example-requests':'6','tab:scenarios':'10','app:stat':'A','app:evidence':'B','app:chronology':'C'}
 check(mode+'_display_labels',all(labels.get(k)==v for k,v in expected.items()))
check('all_local_comparison_pins_match',all(x['local_matches_pinned'] for project in json.loads(now('major-revision/related-local-identities.json')).values() for x in project['files'].values()))
out=dict(status='PASS',base_commit=base,checks=checks,experiments_executed=0)
(root/'major-revision/revision-verification.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
