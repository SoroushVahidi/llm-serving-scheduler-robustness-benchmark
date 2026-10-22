#!/usr/bin/env python3
"""Freeze pilot inputs from historical bytes; does not execute a scheduler."""
import argparse, hashlib, json, sys
from dataclasses import asdict
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'src'))
from robustbench.workloads.external.schema import ExternalWorkloadRecord
from robustbench.workloads.external.benchmark_synthesis import synthesize_requests_from_window
from robustbench.calibration.stage0_load_calibration import _rebase_and_scale
from policies import POLICIES, HISTORICAL, Config

FULL_HASH = '97fbaf6a4b9b5f14cd19ce1c37193996c0758eebca73ab2adb1e944b404b3f4c'
CANONICAL_HASH = '0d1aa06ccbee352207327ea369ae75f12e91c0cda006c813a41b381effd29eef'
HIST_HASH = '73adf7d97f06985ec8f8e1c2f794fd43178433eb198e1c00705e817f4bde9c26'

def digest(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()

def filehash(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def prepare(full_path, out_path, manifest_path):
    assert filehash(full_path) == FULL_HASH
    full = json.loads(Path(full_path).read_text())
    assert digest({k:v for k,v in full.items() if k not in ('generated_at_utc','content_sha256')}) == CANONICAL_HASH
    fpath = ROOT/'artifacts/manifests/ranking_portability_phase12_campaign_freeze.json'
    freeze = json.loads(fpath.read_text())
    hist_path = ROOT/'dataset/v1.1.0/scientific/campaign/consolidated.json'
    assert filehash(hist_path) == HIST_HASH
    hist = {c['cell_id']:c for c in json.loads(hist_path.read_text())['cells']}
    rev_path = ROOT/'dataset/v1.1.0/scientific/analysis/pairwise_reversals.json'
    revs = json.loads(rev_path.read_text())['records']['arrival_normalized_weighted_goodput']
    targets = [r for r in revs if r['policy_a'] in HISTORICAL.values() and r['policy_b'] in HISTORICAL.values()]
    assert sum(r['supported_after_fdr'] for r in targets) == 36
    conditions = []
    chosen = []
    for source in freeze['campaign_sources']:
        w = next(w for w in full['windows'] if w['source_family'] == source)
        assert digest(w['records']) == w['content_sha256'] == freeze['window_identities'][w['window_id']]
        assert len(w['records']) == 200
        seed = next(c['synthesis_seed'] for c in freeze['cells'] if c['window_id'] == w['window_id'])
        raw = sorted(w['records'], key=lambda r:r['arrival_time_s'])
        base, synthesis = synthesize_requests_from_window([ExternalWorkloadRecord(**r) for r in w['records']], window_id=w['window_id'], seed=seed)
        assert synthesis.n_records_dropped_invalid == 0 and len(base) == len(raw)
        chosen.append({k:w[k] for k in ('source_family','window_id','content_sha256','source_file','source_file_sha256','chronology_stratum','sampling_seed','start_index_in_valid_rows')})
        for region in freeze['campaign_regions']:
            key = source+'::'+w['window_id']+'::'+region
            factor = freeze['region_assignment_index'][key]['absolute_load_factor']
            scaled = _rebase_and_scale(base, factor)
            requests = []
            for i,(r,original) in enumerate(zip(scaled,raw)):
                # Independently reconstruct input geometry without using synthesis/rebase helpers.
                assert r.request_id == i
                assert abs(r.arrival_time-(original['arrival_time_s']-raw[0]['arrival_time_s'])/factor) < 1e-7
                assert (r.prompt_tokens,r.actual_output_tokens) == (original['input_tokens'],original['output_tokens'])
                assert r.prompt_tokens+r.actual_output_tokens <= 32768
                requests.append(dict(id=i, source_record_id=original['source_record_id'],
                    derived_record_id=original['derived_record_id'], arrival=r.arrival_time,
                    prompt=r.prompt_tokens, output=r.actual_output_tokens, deadline=r.slo_deadline,
                    priority=r.priority, historical_prediction=r.predicted_output_tokens))
            historical = {}
            for p in POLICIES:
                c = hist[key+'::'+HISTORICAL[p]+'::rep0']
                assert c['success'] and c['synthesis_seed'] == seed and c['load_factor'] == factor
                historical[p] = {k:c[k] for k in ('cell_id','arrival_normalized_weighted_goodput','completion_fraction','mean_latency','p95_latency','mean_ttft','request_throughput','token_throughput','simulator_config_hash','policy_registry_hash')}
            conditions.append(dict(condition_id=key,source=source,window=w['window_id'],region=region,
                synthesis_seed=seed,load_factor=factor,requests=requests,requests_sha256=digest(requests),historical=historical))
    payload = dict(schema='lssp-c01-inputs/0.1.0',conditions=conditions,historical_comparisons=targets)
    out_path.parent.mkdir(parents=True,exist_ok=True)
    encoded = (json.dumps(payload,sort_keys=True,indent=2,allow_nan=False)+'\n').encode()
    if out_path.exists():
        assert out_path.read_bytes() == encoded, 'refuse overwrite different inputs'
    else:
        out_path.write_bytes(encoded)
    profiles = [dict(name='kv131072',config=asdict(Config())),dict(name='kv262144',config=asdict(Config(kv_capacity=262144)))]
    manifest = dict(schema='lssp-c01-manifest/0.1.0',scientific_base='880a37e8e7c19d089be124291e288269966a9147',
        status='PROSPECTIVE_CONFORMANCE_PILOT',full_windows_sha256=FULL_HASH,full_windows_canonical=CANONICAL_HASH,
        input_sha256=filehash(out_path),campaign_manifest_sha256=filehash(fpath),historical_sha256=HIST_HASH,
        historical_comparisons_sha256=filehash(rev_path),selected_windows=chosen,profiles=profiles,
        policies=list(POLICIES),historical_policy_mapping=HISTORICAL,conditions=[{k:v for k,v in c.items() if k not in ('requests','historical')} for c in conditions],
        expected_cells=len(conditions)*len(profiles)*len(POLICIES),inference='DESCRIPTIVE_ONLY',rng='No scheduling RNG; historical synthesis seeds recorded per condition')
    manifest_path.write_text(json.dumps(manifest,sort_keys=True,indent=2)+'\n')
    print(json.dumps(dict(input_sha256=manifest['input_sha256'],cells=manifest['expected_cells'],windows=[x['window_id'] for x in chosen])))

if __name__ == '__main__':
    p=argparse.ArgumentParser();p.add_argument('--windows',type=Path,required=True);p.add_argument('--inputs',type=Path,required=True);p.add_argument('--manifest',type=Path,required=True)
    a=p.parse_args();prepare(a.windows,a.inputs,a.manifest)
