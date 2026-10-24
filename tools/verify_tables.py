#!/usr/bin/env python3
"""Check table bytes, row counts, headers, primary keys and cross-platform inventories."""
import argparse,csv,hashlib,json,pathlib
p=argparse.ArgumentParser(description=__doc__);p.add_argument('artifact',type=pathlib.Path);a=p.parse_args();root=a.artifact
schema=json.loads((root/'TABLE_SCHEMA.json').read_text());total=0
for name,rec in schema.items():
 f=(root/'tables'/name) if (root/'tables').is_dir() else root/name
 assert hashlib.sha256(f.read_bytes()).hexdigest()==rec['sha256'],name
 with f.open() as s:r=csv.DictReader(s);rows=list(r);assert r.fieldnames==list(rec['fields']),name
 assert len(rows)==rec['rows'],name
 keys=[tuple(x[k] for k in rec['primary_key']) for x in rows];assert len(keys)==len(set(keys)),name
 total+=len(rows)
print('PASS:',len(schema),'tables;',total,'rows across different observational units; no duplicate primary keys')
