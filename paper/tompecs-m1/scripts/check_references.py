"""Bounded primary-source metadata retrieval; never edits bibliography."""
import concurrent.futures, hashlib, json, re
from pathlib import Path
import requests
import html
r=Path(__file__).resolve().parents[1]
entries=[]
for block in re.split(r'(?m)^@', (r/'revised/references.bib').read_text())[1:]:
 key=block.split('{',1)[1].split(',',1)[0];fields=dict(re.findall(r'(?m)^\s*(\w+)\s*=\s*\{(.*?)\},?\s*$',block))
 entries.append((key,fields))
def fetch(item):
 key,f=item;url=f.get('url') or ('https://doi.org/'+f['doi'] if f.get('doi') else None)
 row={'key':key,'bibliography_title':f.get('title'),'url':url,'status':'UNVERIFIED'}
 if not url:return row
 try:
  q=requests.get(url,timeout=8);row.update(http_status=q.status_code,resolved_url=q.url,response_sha256=hashlib.sha256(q.content).hexdigest())
  if q.status_code==200:
   title=re.search(r'<title[^>]*>(.*?)</title>',q.text,re.I|re.S); row['source_title']=html.unescape(re.sub('<[^>]+>','',title[1])).strip() if title else None
   row['status']='RETRIEVED_REQUIRES_METADATA_REVIEW'
 except requests.RequestException as e:row['error']=type(e).__name__
 return row
with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool: result=list(pool.map(fetch,entries))
(r/'evidence/bibliography-links.json').write_text(json.dumps(result,indent=2)+'\n')
print('Entries',len(result));print('\n'.join(x['key']+' '+x['status']+' '+str(x.get('http_status'))+' '+str(x.get('source_title',''))[:110] for x in result))
