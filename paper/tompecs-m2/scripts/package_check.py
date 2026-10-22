"""Bounded final packaging checks, independent of LaTeX jobs."""
import hashlib,json,re,subprocess
from pathlib import Path
B=Path(__file__).resolve().parents[1];E=B/'evidence';checks={}
# Local Markdown links including URL anchors; ignore web URLs.
missing=[]
for p in B.glob('*.md'):
 for link in re.findall(r'\]\(([^)]+)\)',p.read_text()):
  if '://' not in link and not (p.parent/link.split('#')[0]).exists():missing.append([p.name,link])
checks['markdown_links_resolve']=not missing
for name in ['audit-verified','additional-checks','cpu-checks','clean-build-final']:checks[name+'_exit_zero']=(E/'validation'/f'{name}.exit').read_text().strip()=='0'
s=json.loads((E/'statistical-audit.json').read_text());checks['numerical_counts']=s['ranking_intervals']['matched']==198 and s['primary_reversal_intervals']['matched']==72 and s['friedman']['matched']==66 and s['cross_metric_intervals']['differences_matched']==6890
checks['primary_classification_counts']=json.loads((E/'additional-checks.json').read_text())['primary_classifications']=={'tested':990,'matched':990}
checks['document_checks']=json.loads((E/'document-validation.json').read_text())['failed']==0
checks['complete_review_deliverables']=all((B/f).exists() for f in ['M2_STATISTICAL_AUDIT.md','M2_RQ_ALIGNMENT.md','M2_REFEREE_REPORT.md','M2_CLAIM_CHANGES.md','LENGTH_INVENTORY.md','VALIDATION.md','revised-manuscript.pdf','revised-acmsmall.pdf'])
result={'checks':checks,'failed':sum(not x for x in checks.values()),'missing_links':missing};(E/'package-check.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2));assert all(checks.values())
