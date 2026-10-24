"""Independent reconstruction from ordinary-start journals; no scheduler imports."""

def check(requests, config, events):
    budget=config['budget'];cap=min(config['max_sequences'],config['kv_capacity']//config['context'])
    assert type(budget) is int and budget>=1
    assert [r['id'] for r in requests]==list(range(len(requests)))
    assert [r['arrival'] for r in requests]==sorted(r['arrival'] for r in requests)
    assert all(type(r['prompt']) is int and type(r['output']) is int and 0<r['prompt']<=budget and r['output']>0 and r['prompt']+r['output']<=config['context'] for r in requests)
    progress=[[0,0] for r in requests];resident=set();done=set();ever=set()
    counts=dict(boundaries=0,binding_resident_offer=0,mixed_older_prefill_later_decode=0,
                raw_nonordinal_batches=0,admitted=0,ready_decode_opportunities=0,
                resident_min_slack=budget,max_residents=0,truncated_prefills=0)
    def inspect(t):
        ordered=sorted(resident)
        waiting=[i for i,r in enumerate(requests) if r['arrival']<=t and i not in ever]
        assert not ordered or not waiting or max(ordered)<min(waiting), 'nonmonotone admission'
        offers={i:1 if progress[i][0]==requests[i]['prompt'] else min(512,requests[i]['prompt']-progress[i][0]) for i in ordered}
        prefix=sum(offers[i] for i in ordered[:-1])
        assert prefix<budget, 'resident prefix slack invariant'
        if sum(offers.values())>budget:
            assert progress[ordered[-1]][0]<requests[ordered[-1]]['prompt'], 'last ready decode cannot cause excess'
        assert len(ordered)<=cap
        return ordered,waiting,offers
    for e in events:
        ordered,waiting,offers=inspect(e['time']);counts['boundaries']+=1
        counts['max_residents']=max(counts['max_residents'],len(ordered))
        counts['resident_min_slack']=min(counts['resident_min_slack'],budget-sum(offers[i] for i in ordered[:-1]))
        counts['binding_resident_offer']+=sum(offers.values())>budget
        ready={i for i in ordered if progress[i][0]==requests[i]['prompt']}
        counts['ready_decode_opportunities']+=len(ready)
        counts['mixed_older_prefill_later_decode']+=any(i<j and i not in ready and j in ready for i in ordered for j in ordered)
        ids=[s[0] for s in e['executed']]
        counts['raw_nonordinal_batches']+=ids!=sorted(ids)
        assert len(ids)==len(set(ids)) and set(ordered)<=set(ids), 'resident omission'
        assert ready<={i for i,k,a,b in e['executed'] if k=='decode'}, 'decode omission'
        new=sorted(set(ids)-resident)
        assert new==waiting[:len(new)], 'nonprefix admission'
        before={i:1 if progress[i][0]==requests[i]['prompt'] else min(512,requests[i]['prompt']-progress[i][0]) for i in ids}
        work={i:b-a for i,k,a,b in e['executed']}
        assert sum(work.values())<=budget and all(n>=1 for n in work.values())
        truncated=[i for i in ids if work[i]<before[i]]
        assert len(truncated)<=1
        if truncated:
            assert truncated==[max(ids)] and progress[max(ids)][0]<requests[max(ids)]['prompt']
            assert sum(work.values())==budget
        counts['truncated_prefills']+=len(truncated)
        for i,k,a,b in e['executed']:
            assert i not in done and requests[i]['arrival']<=e['time']
            if k=='prefill':
                assert a==progress[i][0] and b<=requests[i]['prompt'] and progress[i][1]==0
                progress[i][0]=b
            else:
                assert k=='decode' and i in resident and progress[i][0]==requests[i]['prompt']
                assert a==progress[i][1] and b==a+1 and b<=requests[i]['output']
                progress[i][1]=b
        resident.update(ids);ever.update(ids);counts['admitted']+=len(new)
        assert len(resident)<=cap
        complete={i for i in resident if progress[i][1]==requests[i]['output']}
        assert complete==set(e['completed'])
        resident.difference_update(complete);done.update(complete)
        successors,_,nextoffers=inspect(e['end'])
        for i in successors[:-1]:assert nextoffers[i]<=work[i], 'nonlast offer growth'
    counts['max_residents']=max(counts['max_residents'],len(resident))
    return counts
