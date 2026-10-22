#!/usr/bin/env python3
"""Verify archived saved evidence only. Never import a simulator or generate studies."""
import argparse, collections, hashlib, json, pathlib, subprocess, sys

def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(8*1024*1024), b''):h.update(b)
    return h.hexdigest()

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('candidate',type=pathlib.Path)
    ap.add_argument('--output',type=pathlib.Path,required=True)
    ap.add_argument('--samples',action='store_true',help='Also referee the fixed 24 journals and 200 saved studies')
    a=ap.parse_args();root=a.candidate.resolve();a.output.mkdir(parents=True,exist_ok=True)
    manifest=json.loads((root/'MANIFEST.json').read_text());checked=0
    for name,rec in manifest['files'].items():
        p=root/name
        assert p.is_file() and not p.is_symlink(),name
        assert p.stat().st_size==rec['bytes'] and digest(p)==rec['sha256'],name
        checked+=1
    c01=root/'evidence/c01';stat=root/'evidence/stat';original=root/'evidence/stat-original'
    launch=json.loads((c01/'launch.json').read_text())
    for name,h in launch['files'].items():assert digest(c01/name)==h,name
    # Check the actual source-window lineage, without rerunning input synthesis.
    lineage=root/'evidence/input-lineage'
    cm=json.loads((c01/launch['manifest']).read_text())
    assert digest(lineage/'windows.json')==cm['full_windows_sha256']
    windows=json.loads((lineage/'windows.json').read_text())
    canonical=lambda x:hashlib.sha256(json.dumps(x,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
    assert canonical({k:v for k,v in windows.items() if k not in ('generated_at_utc','content_sha256')})==cm['full_windows_canonical']
    bywindow={w['window_id']:w for w in windows['windows']};assert len(bywindow)==120
    for w in bywindow.values():assert len(w['records'])==200 and canonical(w['records'])==w['content_sha256']
    inputs=json.loads((c01/launch['inputs']).read_text())
    bycondition={c['condition_id']:c for c in inputs['conditions']}
    for c in inputs['conditions']:
        raw=sorted(bywindow[c['window']]['records'],key=lambda r:r['arrival_time_s'])
        for r,o in zip(c['requests'],raw):
            assert (r['prompt'],r['output'])==(o['input_tokens'],o['output_tokens'])
            assert r['source_record_id']==o['source_record_id'] and r['priority']==1
            assert abs(r['arrival']-(o['arrival_time_s']-raw[0]['arrival_time_s'])/c['load_factor'])<1e-7
    pilot=json.loads((lineage/'pilot-inputs.json').read_text())
    for c in pilot['conditions']:assert {k:v for k,v in c.items() if k!='historical'}==bycondition[c['condition_id']]
    assert digest(lineage/'historical-consolidated.json')=='73adf7d97f06985ec8f8e1c2f794fd43178433eb198e1c00705e817f4bde9c26'
    historical=json.loads((lineage/'historical-pairwise-reversals.json').read_text())['records']['arrival_normalized_weighted_goodput']
    assert len(historical)==990 and sum(r['supported_after_fdr'] for r in historical)==36
    sl=json.loads((stat/'launch.json').read_text())
    for name,h in sl['files'].items():assert digest(stat/'code'/name)==h,name
    for name,h in sl['original_launch']['files'].items():assert digest(original/'code'/name)==h,name
    for name,h in sl['original_launch']['historical_reference_files'].items():assert digest(original/'reference'/name)==h,name
    assert json.loads((original/'launch.json').read_text())==sl['original_launch']
    assert digest(stat/'source-batches.json')==sl['source_index_sha256']
    assert digest(stat/'source-audit.json')==sl['source_audit_sha256']
    rows=json.loads((c01/'runs/c01-full-167b9074e5711420/analysis/absolute_metrics.json').read_text())
    for r in rows:
        p=c01/r['result_path']
        assert digest(p/'result.json')==r['result_sha256']
        assert digest(p/'events.jsonl.gz')==r['journal_sha256']
    batches=list((stat/'runs/stat01-recovery-v2-061933a64e27da20/batches').glob('*/*/integrity.json'))
    for p in batches:
        for name,h in json.loads(p.read_text())['hashes'].items():assert digest(p.parent/name)==h,(p,name)
    assert len(rows)==5760 and len(batches)==5360
    checks=['check_c01.py','check_stat_inventory.py']
    if a.samples:checks+=['check_c01_journals.py','check_stat_samples.py']
    for name in checks:
        out=a.output/(name.removesuffix('.py')+'.json')
        with (a.output/(name+'.log')).open('w') as log:
            subprocess.run([sys.executable,str(pathlib.Path(__file__).parent/'verification'/name),str(root),str(out)],check=True,stdout=log,stderr=subprocess.STDOUT)
    summary={'state':'COMPLETED_SUCCESS','manifest_files':checked,'c01_result_and_journal_hashes':len(rows),'stat_batches_all_three_payload_hashes':len(batches),'source_windows_checked':120,'input_conditions_checked':720,'pilot_input_conditions_matched':len(pilot['conditions']),'historical_archived_rule_count':'36/990','checks':checks,'experiments_executed':0,'scope':'All hashes and terminal/summary records; fixed sample record referees only, not exhaustive fresh replay'}
    (a.output/'candidate-verification.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary,indent=2))
if __name__=='__main__':main()
