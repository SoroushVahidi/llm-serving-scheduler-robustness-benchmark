#!/usr/bin/env python3
"""Extract a candidate to a new directory, check saved data, rebuild displays/PDFs."""
import argparse,hashlib,json,pathlib,subprocess,sys,tarfile,time

def main():
 ap=argparse.ArgumentParser(description=__doc__)
 ap.add_argument('archive',type=pathlib.Path)
 ap.add_argument('destination',type=pathlib.Path)
 ap.add_argument('--output',type=pathlib.Path,required=True)
 a=ap.parse_args();assert not a.destination.exists(),'clean extraction requires a new directory'
 a.destination.mkdir(parents=True);a.output.mkdir(parents=True,exist_ok=True);t=time.monotonic()
 with tarfile.open(a.archive) as tf:tf.extractall(a.destination,filter='data')
 root=a.destination.resolve();paper=root/'paper/tompecs-m3';release=paper/'artifact-release'
 def run(cmd,name):
  with (a.output/name).open('w') as log:subprocess.run(cmd,cwd=root,check=True,stdout=log,stderr=subprocess.STDOUT)
 run([sys.executable,str(release/'verify_candidate.py'),str(root),'--output',str(a.output.resolve()/'records'),'--samples'],'records.log')
 manifest=json.loads((root/'MANIFEST.json').read_text())
 run([sys.executable,str(paper/'scripts/render.py')],'render.log')
 regenerated={}
 for area in ['tables','figures','supplement']:
  for p in sorted((paper/area).glob('*')):
   if p.suffix not in {'.csv','.tex','.pdf'}:continue
   name=str(p.relative_to(root));h=hashlib.sha256(p.read_bytes()).hexdigest();assert h==manifest['files'][name]['sha256'],name;regenerated[name]=h
 for mode in ['manuscript','acmsmall']:run(['bash',str(paper/'scripts/build.sh'),mode],mode+'-build.log')
 run([sys.executable,str(paper/'scripts/validate.py'),'--standalone'],'validation.log')
 v=json.loads((paper/'evidence/validation/validation.json').read_text())
 h=hashlib.sha256()
 with a.archive.open('rb') as f:
  for block in iter(lambda:f.read(8*1024*1024),b''):h.update(block)
 result={'state':'COMPLETED_SUCCESS','clean_extraction':True,'archive':a.archive.name,'archive_sha256':h.hexdigest(),'regenerated_displays_byte_identical':regenerated,'builds':v['builds'],'historical_checkout_check':v['historical_checkout_check'],'records':json.loads((a.output/'records/candidate-verification.json').read_text()),'elapsed_seconds':time.monotonic()-t,'experiments_executed':0,'environment_installation':'existing pinned display environment; no fresh installation'}
 (a.output/'clean-extraction.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
if __name__=='__main__':main()
