#!/usr/bin/env python3
"""Export convenience CSV views from frozen saved inputs; no simulation imports."""
import argparse,csv,gzip,json,pathlib,shutil,hashlib
p=argparse.ArgumentParser(description=__doc__);p.add_argument('artifact',type=pathlib.Path);p.add_argument('--output',type=pathlib.Path,required=True);a=p.parse_args()
root=a.artifact.resolve();out=a.output.resolve()
if out==root or root in out.parents:raise SystemExit('Output must be outside the preserved artifact')
out.mkdir(parents=True,exist_ok=False)
schema=json.loads((root/'TABLE_SCHEMA.json').read_text())
for name,rec in schema.items():
 src=root/rec['source']['path'];assert hashlib.sha256(src.read_bytes()).hexdigest()==rec['source']['sha256']
 if rec['source']['transformation']=='byte-identical copy':shutil.copyfile(src,out/name)
 else:
  if src.suffix=='.gz':rows=json.loads(gzip.decompress(src.read_bytes()))
  else:rows=json.loads(src.read_text())['conditions']
  rows=[{k:json.dumps(v,sort_keys=True,separators=(',',':')) if isinstance(v,(dict,list)) else v for k,v in r.items()} for r in rows]
  with (out/name).open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
 assert hashlib.sha256((out/name).read_bytes()).hexdigest()==rec['sha256'],name
print('PASS: all',len(schema),'table exports match frozen hashes')
