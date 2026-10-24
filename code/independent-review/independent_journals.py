"""Independent saved-event referee. No simulator, analyzer or production policy imports."""
import argparse,collections,gzip,hashlib,json,math,pathlib,time
R=pathlib.Path(__file__).parent;S=R/'saved';O=R/'review';O.mkdir(exist_ok=True)
BASE=pathlib.Path('/home/soroush/artifacts/m3-four-platform-refresh-20261024/prepared/canonical/evidence/c01')
def load(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def near(a,b):assert math.isclose(a,b,rel_tol=3e-12,abs_tol=1e-13),(a,b)
def q(a,f):
 a=sorted(a);x=(len(a)-1)*f;i=int(x);return a[i]+(a[min(i+1,len(a)-1)]-a[i])*(x-i)
def audit(requests,config,path,result,policy,variable):
 assert sha(path)==result['journal_sha256']
 N=len(requests);p=[0]*N;d=[0]*N;resident=set();waiting=set();done=set();anchor=[None]*N;first=[None]*N;completion=[None]*N;admission={}
 clock=requests[0]['arrival'];horizon=requests[-1]['arrival']+config['drain'];narr=0
 K=min(config['max_sequences'],config['kv_capacity']//config['context']);count=0;busy=0;durations=[];comp=collections.Counter();urg=collections.Counter();maxage=0;maxreserved=maxused=0
 normalized=hashlib.sha256();reordered=0;diff=0;arrival_inside=0
 with gzip.open(path,'rt') as f:
  for line in f:
   e=json.loads(line);count+=1;t=e['time'];end=e['end']
   while narr<N and requests[narr]['arrival']<=clock:
    waiting.add(narr);narr+=1
   if not resident and not waiting:
    clock=requests[narr]['arrival']
    while narr<N and requests[narr]['arrival']<=clock:waiting.add(narr);narr+=1
   assert t==clock
   ds=sorted(i for i in resident if p[i]==requests[i]['prompt']);ps=sorted(resident-set(ds));ws=sorted(waiting);slots=K-len(resident)
   ages=[t-anchor[i] for i in ds];critical=[i for i in ds if t-anchor[i]>=.495]
   if policy=='whole_fcfs_c01':order=ws if slots and ws else ds
   elif policy=='chunked_fcfs_c01':order=sorted(resident)+ws
   elif policy=='decode_first_c01':order=ds+ps+ws
   elif policy=='slo_gated_c01':order=critical+ps+sorted(ws,key=lambda i:(requests[i]['prompt'],i))+[i for i in ds if i not in critical]
   elif policy=='slo_gated_fcfs_c01':order=critical+ps+ws+[i for i in ds if i not in critical]
   else:raise AssertionError(policy)
   remaining=config['budget'];expected=[];slots_left=slots
   for i in order:
    if remaining==0:break
    if i not in resident and slots_left==0:continue
    if p[i]<requests[i]['prompt']:
     amount=requests[i]['prompt']-p[i]
     if policy=='whole_fcfs_c01':
      if amount>remaining:break
     else:amount=min(amount,512,remaining)
     expected.append([i,'prefill',p[i],p[i]+amount])
    else:amount=1;expected.append([i,'decode',d[i],d[i]+1])
    remaining-=amount
    if i not in resident:slots_left-=1
   assert e['intent']==e['executed']==expected,(policy,count,'intent')
   assert len({s[0] for s in expected})==len(expected)
   P=sum(z-a for i,k,a,z in expected if k=='prefill');D=sum(z-a for i,k,a,z in expected if k=='decode')
   duration=(.0005+P*(.0005/512)+D*(.0005/8)) if variable else .001
   assert end==t+duration and end<=horizon
   selected={i for i,k,a,z in expected if k=='decode'}
   u={'ready':len(ds),'critical':len(critical),'selected_critical':len(set(critical)&selected),'omitted':len(set(ds)-selected),'max_age':max(ages,default=0)}
   if variable:
    assert e['timing']=={'duration':duration,'prefill_tokens':P,'decode_tokens':D,'urgency':u}
   for k in ['ready','critical','selected_critical','omitted']:urg[k]+=u[k]
   maxage=max(maxage,u['max_age']);durations.append(duration);busy+=duration
   comp['prefill_tokens']+=P;comp['decode_tokens']+=D;comp['mixed_batches']+=P>0 and D>0;comp['prefill_only_batches']+=P>0 and D==0;comp['decode_only_batches']+=D>0 and P==0
   arrival_inside+=sum(t<r['arrival']<end for r in requests[narr:]) if narr<N else 0
   for i,kind,start,stop in expected:
    if i not in resident:
     assert i in waiting and kind=='prefill'
     waiting.remove(i);resident.add(i);admission[i]=t
    if kind=='prefill':
     assert start==p[i] and stop<=requests[i]['prompt'] and d[i]==0
     p[i]=stop
     if stop==requests[i]['prompt']:anchor[i]=end
    else:
     assert p[i]==requests[i]['prompt'] and start==d[i] and stop==d[i]+1<=requests[i]['output']
     d[i]=stop;anchor[i]=end
     if first[i] is None:first[i]=end
   reserved=len(resident)*config['context'];used=sum(((p[i]+d[i]+15)//16)*16 for i in resident)
   assert len(resident)<=K and e['reserved']==reserved and e['used']==used<=reserved
   maxreserved=max(maxreserved,reserved);maxused=max(maxused,used)
   finished=sorted(i for i in resident if d[i]==requests[i]['output'])
   assert finished==e['completed']
   for i in finished:completion[i]=end;resident.remove(i);done.add(i)
   # A normalized journal retains every field except permutation of selected work.
   ne={**e,'intent':sorted(e['intent']),'executed':sorted(e['executed'])}
   normalized.update((json.dumps(ne,sort_keys=True,separators=(',',':'))+'\n').encode())
   reordered+=e['executed']!=sorted(e['executed'])
   clock=end
 assert len(done)==N # All current saved cells complete; no censoring branch exercised.
 terminal=result['terminal']
 assert terminal['observed_end']==clock and terminal['batches']==count and not terminal['unfinished']
 for row in terminal['requests']:
  i=row['id'];assert row==dict(id=i,prefilled=p[i],generated=d[i],resident=i in resident,anchor=anchor[i],first=first[i],completion=completion[i])
 m=result['metrics'];near(busy,m['busy_device_seconds'])
 assert comp['prefill_tokens']==m['prefill_work'] and comp['decode_tokens']==m['decode_work'] and maxreserved==m['peak_reserved_kv'] and maxused==m['peak_used_kv']
 observed={'n':count,'min':min(durations),'mean':sum(durations)/count,'p50':q(durations,.5),'p95':q(durations,.95),'max':max(durations)}
 if variable:
  tt=result['telemetry'];assert dict(comp)==tt['composition'];assert {**dict(urg),'max_age':maxage}==tt['urgency']
  for k,v in observed.items():near(v,tt['duration'][k])
  near(sum(t-requests[i]['arrival'] for i,t in admission.items())/N,tt['admission']['mean_wait_to_admission'])
 else:
  tt=result.get('telemetry')
  if tt:
   for k,v in urg.items():assert v==tt[k]
   assert maxage==tt['max_age']
   near(sum(t-requests[i]['arrival'] for i,t in admission.items())/N,tt['mean_admission_wait'])
 return dict(events=count,normalized_sha256=normalized.hexdigest(),array_order_not_id_sorted_events=reordered,arrivals_inside_batches=arrival_inside,composition=dict(comp),urgency=dict(urg,max_age=maxage),duration=observed)
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--sample-one',action='store_true');args=ap.parse_args()
 start=time.monotonic();m=load(S/'time01/manifest.json');cs={c['condition_id']:c for c in load(S/'time01/inputs.json')['conditions']};records={};ts=[]
 for c in m['cells'][:1] if args.sample_one else m['cells']:
  cid=c['cell_id'];p=S/'time01/cells'/cid;r=load(p/'result.json')
  z=audit(cs[c['identity']['condition_id']]['requests'],c['identity']['config'],p/'events.jsonl.gz',r,c['identity']['policy'],True)
  records[(c['identity']['condition_id'],c['profile'],c['identity']['policy'])]=(z,r)
  ts.append(dict(cell_id=cid,**{k:c[k] for k in ['source','window','region','profile']},policy=c['identity']['policy'],**z))
 if args.sample_one:print(json.dumps({'one_cell_seconds':time.monotonic()-start,'events':ts[0]['events']}));return
 pairs=[]
 for (cond,profile,policy),(z,r) in records.items():
  if policy!='chunked_fcfs_c01':continue
  other,rr=records[(cond,profile,'decode_first_c01')]
  assert z['normalized_sha256']==other['normalized_sha256'] and r['terminal']==rr['terminal'] and r['metrics']==rr['metrics']
  pairs.append({'condition_id':cond,'profile':profile,'normalized_events':z['events'],'equal':True})
 (O/'time01-journal-validation.json').write_text(json.dumps({'status':'PASS','cells':len(ts),'pairs':pairs,'records':ts,'seconds':time.monotonic()-start},indent=2)+'\n')
 print('TIME01: all',len(ts),'journals; all 96 normalized pairs PASS',time.monotonic()-start,flush=True)
 m=load(S/'abl01/manifest.json');cs={c['condition_id']:c for c in load(S/'abl01/inputs.json')['conditions']};sample=[]
 for c in m['cells']:
  p=S/'abl01/derived-controls'/c['cell_id']
  if not (p/'events.jsonl.gz').exists():continue
  req=cs[c['identity']['condition_id']]['requests'];cfg=c['identity']['config'];r=load(p/'result.json')
  z=audit(req,cfg,p/'events.jsonl.gz',r,'slo_gated_fcfs_c01',False)
  cf=c['equivalent_control'];f=BASE/cf['result_path'];old=load(f/'result.json')
  w=audit(req,cfg,f/'events.jsonl.gz',old,'chunked_fcfs_c01',False);assert z['normalized_sha256']==w['normalized_sha256']
  baseline=c['baseline'];f=BASE/baseline['result_path'];b=load(f/'result.json')
  b['telemetry']=r['baseline_telemetry'];v=audit(req,cfg,f/'events.jsonl.gz',b,'slo_gated_c01',False)
  sample.append(dict(cell_id=c['cell_id'],source=c['source'],region=c['region'],profile=c['profile'],control=z,baseline=v,equivalent_source=w))
 assert len(sample)==36
 (O/'abl01-journal-validation.json').write_text(json.dumps({'status':'PASS','pairs_sampled':36,'selection':'first lexical window in each source/region/capacity stratum','source_journals':72,'derived_journals':36,'records':sample,'total_seconds_including_time01':time.monotonic()-start},indent=2)+'\n')
 print('ABL01: 36 sampled derived controls and 72 source journals PASS',time.monotonic()-start,flush=True)
if __name__=='__main__':main()

