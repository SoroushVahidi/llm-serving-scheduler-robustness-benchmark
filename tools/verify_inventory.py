#!/usr/bin/env python3
"""Verify an unmodified extracted package, including exact file-set equality."""
import argparse,hashlib,json,pathlib
p=argparse.ArgumentParser(description=__doc__);p.add_argument('artifact',type=pathlib.Path);a=p.parse_args();root=a.artifact.resolve()
m=json.loads((root/'MANIFEST.json').read_text())['files'];actual={p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file()}
assert actual==set(m)|{'MANIFEST.json','SHA256SUMS'},(actual-set(m),set(m)-actual)
for n,r in m.items():
 f=root/n;assert not f.is_symlink() and f.stat().st_size==r['bytes'],n
 h=hashlib.sha256()
 with f.open('rb') as s:
  for b in iter(lambda:s.read(8*1024*1024),b''):h.update(b)
 assert h.hexdigest()==r['sha256'],n
print('PASS:',len(m),'payload identities and exact file set; SHA256SUMS/manifest authenticated by external archive checksum')
