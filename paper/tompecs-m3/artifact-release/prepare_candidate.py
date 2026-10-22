#!/usr/bin/env python3
"""Create local-only saved-evidence archives. No network, jobs or scientific generation.

Run after downloading frozen evidence into STAGING/evidence and source-data.
Use a new --output directory. Archives are intentionally outside the Git tree.
"""
import argparse,gzip,hashlib,json,pathlib,shutil,subprocess,tarfile
EPOCH=1792627200
C01='2d8342e699f35044044ac518c0b75a3c4a1c768c'
STAT='1ac4c8dd1421aabad05e6ce243cb911a6ed6c8e1'

def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(8*1024*1024),b''):h.update(b)
 return h.hexdigest()

def archive(root,dest):
 with dest.open('wb') as raw,gzip.GzipFile(filename='',mode='wb',fileobj=raw,mtime=EPOCH,compresslevel=1) as gz,tarfile.open(fileobj=gz,mode='w') as tf:
  for p in sorted(root.rglob('*')):
   if not p.is_file():continue
   assert not p.is_symlink(),p
   info=tf.gettarinfo(str(p),arcname=str(p.relative_to(root)));info.uid=info.gid=0;info.uname=info.gname='';info.mtime=EPOCH;info.mode=0o644
   with p.open('rb') as f:tf.addfile(info,f)
 return {'file':dest.name,'bytes':dest.stat().st_size,'sha256':sha(dest)}

def main():
 ap=argparse.ArgumentParser(description=__doc__)
 ap.add_argument('--staging',type=pathlib.Path,required=True)
 ap.add_argument('--output',type=pathlib.Path,required=True)
 ap.add_argument('--repo',type=pathlib.Path,default=pathlib.Path(__file__).resolve().parents[3])
 ap.add_argument('--stat-repo',type=pathlib.Path,help='Repository containing the pinned STAT01 commit; default --repo')
 ap.add_argument('--archives-only',action='store_true',help='Repack a previously prepared, reviewed tree')
 a=ap.parse_args();root=a.staging.resolve();out=a.output.resolve();out.mkdir(parents=True,exist_ok=True)
 assert not root.is_relative_to(a.repo.resolve()),'candidate must remain outside Git'
 if not a.archives_only:
  assert (root/'evidence/c01/launch.json').is_file() and (root/'evidence/stat/launch.json').is_file()
  paper=a.repo/'paper/tompecs-m3';target=root/'paper/tompecs-m3'
  assert not target.exists(),'use a new staging tree or --archives-only'
  shutil.copytree(paper,target,ignore=shutil.ignore_patterns('build','__pycache__'))
  for label,commit,paths in [('c01',C01,['src','configs','research/lssp-c01','research/lssp-c01-full','pyproject.toml','LICENSE','README.md']),('stat01',STAT,['src','research/lssp-stat01','pyproject.toml','LICENSE','README.md'])]:
   dest=root/'code'/label;dest.mkdir(parents=True)
   source_repo=(a.stat_repo or a.repo) if label=='stat01' else a.repo
   proc=subprocess.Popen(['git','-C',str(source_repo),'archive',commit,*paths],stdout=subprocess.PIPE)
   with tarfile.open(fileobj=proc.stdout,mode='r|') as tf:tf.extractall(dest,filter='data')
   assert proc.wait()==0
  shutil.copyfile(paper/'artifact-release/CANDIDATE_README.md',root/'README.md')
  shutil.copyfile(paper/'artifact-release/THIRD_PARTY_NOTICES.md',root/'THIRD_PARTY_NOTICES.md')
  commits={'paper_base':subprocess.check_output(['git','-C',str(a.repo),'rev-parse','HEAD'],text=True).strip(),'paper_identity':'Exact file hashes in MANIFEST.json; archive assembled from reviewed working tree. Final PR commit is reported externally.','c01':C01,'c01_pilot':'9aed0206de66886e9feb0b003b59f0b7dfea68c9','stat01':STAT,'stat01_original':'454168a005240341dc5a5ae88ac32c4b130f6bc5','evidence_review':'6b2eedd7aa254986b85c1bb901587641cbeac8b0','prewrite_audit':'d22c7751af9c563d5a4d8a304c007f26112c4d12'}
  (root/'COMMITS.json').write_text(json.dumps(commits,indent=2)+'\n')
  # Preserve frozen bytes; new sidecar notices identify transformed input/display files.
  notice='RESEARCH-DERIVED FILE: selected/filtered source lengths and arrivals, or CM saved-result display. See THIRD_PARTY_NOTICES.md at artifact root and paper/tompecs-m3/artifact-release/SOURCE_PROVENANCE.md for creators, licenses and transformations. Frozen bytes unchanged in this candidate.\n'
  for parent in [root/'evidence/c01/inputs',root/'evidence/c01/provenance',root/'evidence/input-lineage',target/'supplement']:
   for p in parent.rglob('*'):
    if p.is_file() and p.suffix in {'.json','.csv'}:p.with_name(p.name+'.NOTICE.txt').write_text(notice)
  licenses=root/'source-data/licenses';licenses.mkdir(exist_ok=True)
  for name in ['azure_license.txt','azure_readme.txt','alibaba_license.txt','alibaba_readme.txt','burst_license.txt','burst_readme.txt']:
   shutil.copyfile(paper/'artifact-release/official-sources'/name,licenses/name)
  for name in ['THIRD_PARTY_NOTICES.md','SOURCE_PROVENANCE.md']:
   shutil.copyfile(paper/'artifact-release'/name,root/'source-data'/name)
  for p in (root/'source-data').glob('*'):
   if p.is_file():p.with_name(p.name+'.NOTICE.txt').write_text('UNMODIFIED SOURCE DATA; Azure filename renamed only. See THIRD_PARTY_NOTICES.md and SOURCE_PROVENANCE.md in the main candidate.\n')
 # Separate optional original sources from the complete executed-input/result archive.
 files={}
 for p in sorted(root.rglob('*')):
  if not p.is_file() or p.relative_to(root).parts[0]=='source-data' or p.name=='MANIFEST.json':continue
  assert not p.is_symlink(),p
  files[str(p.relative_to(root))]={'bytes':p.stat().st_size,'sha256':sha(p)}
 manifest={'version':'lssp-m3-rc1-20261022','scope':'complete frozen C01/STAT01 records and executed inputs; original source-data in separate local archive','files':files}
 (root/'MANIFEST.json').write_text(json.dumps(manifest,indent=2)+'\n')
 # Tar main without moving or modifying source data.
 dest=out/'lssp-m3-rc1-20261022-evidence.tar.gz'
 with dest.open('wb') as raw,gzip.GzipFile(filename='',mode='wb',fileobj=raw,mtime=EPOCH,compresslevel=1) as gz,tarfile.open(fileobj=gz,mode='w') as tf:
  for name in [*files,'MANIFEST.json']:
   p=root/name;info=tf.gettarinfo(str(p),arcname=name);info.uid=info.gid=0;info.uname=info.gname='';info.mtime=EPOCH;info.mode=0o644
   with p.open('rb') as f:tf.addfile(info,f)
 records=[{'file':dest.name,'bytes':dest.stat().st_size,'sha256':sha(dest),'uncompressed_file_bytes':sum(x['bytes'] for x in files.values())+(root/'MANIFEST.json').stat().st_size,'files':len(files)+1}]
 sources=root/'source-data'
 source_records={str(p.relative_to(sources)):{'bytes':p.stat().st_size,'sha256':sha(p)} for p in sorted(sources.rglob('*')) if p.is_file() and p.name!='MANIFEST.json'}
 (sources/'MANIFEST.json').write_text(json.dumps({'files':source_records},indent=2)+'\n')
 records.append(archive(sources,out/'lssp-m3-rc1-20261022-upstream-sources.tar.gz'))
 (out/'archives.json').write_text(json.dumps(records,indent=2)+'\n')
 (out/'SHA256SUMS').write_text(''.join(f"{x['sha256']}  {x['file']}\n" for x in records))
 print(json.dumps(records,indent=2))
if __name__=='__main__':main()
