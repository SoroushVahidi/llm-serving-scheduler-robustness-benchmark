"""Four fixed-mode compatibility checks; never run the scientific timing cells."""
import argparse,json,pathlib,dataclasses
from support import save_new
from campaign import preflight,read
from policies import Config,POLICIES
from timing import Timing
from timed_engine import simulate
from timed_validator import validate

def main():
    ap=argparse.ArgumentParser();ap.add_argument('root',type=pathlib.Path);ap.add_argument('report',type=pathlib.Path);a=ap.parse_args()
    m,cs=preflight(a.root)
    windows=sorted(c['window'] for c in m['cells'] if c['source']=='burstgpt')
    selected=[c for c in m['cells'] if c['window']==windows[0] and c['region']=='LOW' and c['profile']=='kv131072']
    assert len(selected)==4;reports=[]
    for cell in selected:
        i=cell['identity'];rs=cs[i['condition_id']]['requests'];es=[]
        terminal=simulate(rs,i['policy'],Config(**i['config']),es.append,Timing())
        metrics=validate(rs,i['config'],es,terminal)
        baseline=read(a.root/cell['baseline']['local_file'])
        assert terminal==baseline['terminal'] and metrics==baseline['metrics']
        reports.append(dict(cell_id=cell['cell_id'],baseline_result_sha256=cell['baseline']['result_sha256'],status='EXACT_TERMINAL_AND_METRIC_MATCH'))
    save_new(a.report,dict(status='PASS',fixed_regression_checks=4,new_scientific_cells=0,cells=reports))
    print('PASS: four fixed-mode regression checks exactly match saved C01 terminals/metrics')
if __name__=='__main__':main()
