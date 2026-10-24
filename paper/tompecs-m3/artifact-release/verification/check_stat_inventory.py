# Adapted from the PR17 saved-record checker; no experiment execution.
import argparse
_parser=argparse.ArgumentParser()
_parser.add_argument('candidate',type=str)
_parser.add_argument('output',type=str)
_args=_parser.parse_args()
from pathlib import Path
import json,hashlib,math,collections
from decimal import Decimal,localcontext
p=Path(_args.candidate)/'evidence/stat';q=p/'runs/stat01-recovery-v2-061933a64e27da20';fast=p;read=lambda f:json.loads(f.read_text());sp=read(fast/'launch.json');cp=read(fast/'runs/stat01-recovery-v2-061933a64e27da20/checkpoint.json');origin={(x['scenario'],x['start']):x for x in read(fast/'source-batches.json')};metadata=list(q.glob('batches/*/*/integrity.json'));assert len(metadata)==5360,len(metadata)
expected={(sid,start) for sid in range(18) for start in range(0,cp['scenarios'][str(sid)]['n'],25)};seen={};groups=collections.defaultdict(list);counts=collections.Counter();methods=sp['methods'];identity=hashlib.sha256(json.dumps(sp,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
for f in metadata:
 x=read(f);key=x['scenario'],x['start'];assert key not in seen;seen[key]=x;groups[x['scenario']].append(x);assert key in expected and x['count']==25 and x['identity']==identity and x['original_identity']==sp['original_identity'];assert x['validation_contract']=='FROZEN_BINARY64_AND_POSTDIAGNOSIS_EXACT_V1';assert set(x['hashes'])=={'raw.npz','studies.json.gz','secondary.json.gz'};assert set(x['sufficient'])==set(methods)
 if key in origin:
  assert x['origin']==origin[key]
  for n,h in origin[key]['artifact_hashes'].items():assert x['hashes'][n]==h
  counts['reused']+=25
 else:
  assert x['origin']==dict(generated=True,seed_namespace=1);counts['generated']+=25
 for method,ss in x['sufficient'].items():
  assert len(ss)==16
  for ep,a in ss.items():assert 0<=a['n']<=25 and 0<=a['mean']<=1 and a['m2']>=0
assert set(seen)==expected
errors=collections.defaultdict(float);screens=collections.Counter();total_fields=0;stops=[];independent_final={}
# Compute the final merged moments with decimal arithmetic, not the runner's sequential merge.
with localcontext() as ctx:
 ctx.prec=50
 for sid,batches in sorted(groups.items()):
  batches.sort(key=lambda x:x['start']);N=cp['scenarios'][str(sid)]['n'];look=read(fast/f'runs/stat01-recovery-v2-061933a64e27da20/look-s{sid:02d}-n{N:05d}.json');independent_final[sid]={}
  for family,M in [('original_prespecified',8),('expanded_postdiagnosis',17)]:
   delta=.05/(18*M*16*5);stored_delta=look[family]['simultaneous_mc_delta_per_endpoint_look'] if M==8 else look[family]['delta_per_endpoint_look'];assert stored_delta==delta
   for method,v in look[family]['methods'].items():
    recomputed={}
    for ep,target in v['endpoints'].items():
     ss=[b['sufficient'][method][ep] for b in batches];n=sum(z['n'] for z in ss);assert n==target['n'];S=sum((Decimal.from_float(z['mean'])*z['n'] for z in ss),Decimal(0));mean=S/n if n else Decimal(0);M2=sum((Decimal.from_float(z['m2'])+Decimal(z['n'])*(Decimal.from_float(z['mean'])-mean)**2 for z in ss),Decimal(0));var=float(M2/(n-1)) if n>1 else None;avg=float(mean) if n else None;L=math.log(4/delta);b=math.sqrt(2*var*L/n)+7*L/(3*(n-1)) if n>1 else 1.;fields=dict(mean=avg,lower=max(0.,avg-b) if n else 0.,upper=min(1.,avg+b) if n else 1.,halfwidth=b,mcse=math.sqrt(var/n) if n>1 else None,n=n);recomputed[ep]=fields
     for field,value in fields.items():
      if value is None:assert target[field] is None
      else:errors[field]=max(errors[field],abs(value-target[field]))
     total_fields+=1
    if M==8:
     fdr,ci=recomputed['fdp_practical'],recomputed['ci_coverage'];screen='ABSTAIN_OUTSIDE_DOMAIN' if v['assumption_status']=='ABSTAIN_OUTSIDE_DOMAIN' else 'CALIBRATION_CONCERN' if fdr['lower']>.05 or (ci['n'] and ci['upper']<.95) else 'EMPIRICALLY_COMPATIBLE_WITH_TOLERANCE' if fdr['upper']<=.06 and ci['n'] and ci['lower']>=.94 else 'INCONCLUSIVE';assert screen==v['calibration_screen'];screens[screen]+=1
    independent_final[sid][family+'::'+method]=recomputed
  # Check every recorded precision look directly from stored endpoint widths, including no premature stopping.
  all_looks=sorted((fast/'runs/stat01-recovery-v2-061933a64e27da20').glob(f'look-s{sid:02d}-n*.json'))
  for f in all_looks:
   z=read(f);precise=True
   for method,v in z['original_prespecified']['methods'].items():
    if v['assumption_status']=='ABSTAIN_OUTSIDE_DOMAIN':continue
    for ep,width in [('fdp_practical',.025),('fwer_practical',.025),('null_fraction_practical',.025),('ci_coverage',.03),('power_practical',.08)]:
     if ep=='power_practical' and v['endpoints'][ep]['n']==0:continue
     if v['endpoints'][ep]['halfwidth']>width:precise=False
   assert z['precision_objective_met']==precise
   if z['n_studies']<N:assert not precise
  assert cp['scenarios'][str(sid)]['status']==('PRECISION_STOP_ORIGINAL_EIGHT' if precise else 'MAXIMUM_COUNT');stops.append(dict(sid=sid,n=N,precision=precise))
result=dict(batches=len(metadata),studies=sum(counts.values()),origin_counts=dict(counts),all_scenario_ranges_complete=True,final_endpoint_summaries_checked=total_fields,independent_decimal_moment_max_abs_differences=dict(errors),original_calibration_screens=dict(screens),stops=stops)
print(json.dumps(result,indent=2));Path(_args.output).write_text(json.dumps(result,indent=2))

assert all(v<=1e-12 for v in errors.values()), dict(errors)
assert counts==dict(reused=112275,generated=21725)
