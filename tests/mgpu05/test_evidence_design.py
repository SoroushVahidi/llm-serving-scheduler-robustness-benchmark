import json
from pathlib import Path
import pytest
from robustbench.mgpu05.evidence import Journal, read_journal, seal, verify_seal
from robustbench.mgpu05.design import design, verify_design, cohort


def test_chain_seal_and_tampering(tmp_path):
    p=tmp_path/'events.jsonl'; j=Journal(p,synthetic=True)
    j.event('run_start'); j.event('run_end'); j.close()
    assert len(read_journal(p))==2
    seal(tmp_path); verify_seal(tmp_path)
    p.write_text(p.read_text().replace('run_start','bad_start'))
    with pytest.raises(ValueError): read_journal(p)
    with pytest.raises(ValueError): verify_seal(tmp_path)


def test_no_overwrite_or_sensitive_capture(tmp_path):
    with pytest.raises(ValueError): Journal(tmp_path/'secret',synthetic=False)
    j=Journal(tmp_path/'new',synthetic=True); j.close()
    with pytest.raises(FileExistsError): Journal(tmp_path/'new',synthetic=True)


def test_missing_and_added_file_detected(tmp_path):
    (tmp_path/'a').write_text('a'); seal(tmp_path)
    (tmp_path/'b').write_text('b')
    with pytest.raises(ValueError): verify_seal(tmp_path)
    (tmp_path/'b').unlink(); (tmp_path/'a').unlink()
    with pytest.raises(ValueError): verify_seal(tmp_path)


def test_plan_frozen_balanced_bounded():
    plan=verify_design(design())
    frozen=json.loads((Path(__file__).parents[2]/'scripts/mgpu05/design.json').read_text())
    assert frozen==plan and len(plan['blocks'])==12
    assert sum(b['policy_order'][0]=='native_fcfs' for b in plan['blocks'])==6
    assert len({(b['window'],b['region'],b['repetition']) for b in plan['blocks']})==12
    assert plan['maximum_gpu_hours']==12*50/60
    for b in plan['blocks']:
        ps=cohort(b['window'],b['region'])
        assert max(map(lambda p:len(p['prompt']),ps))<=256
        assert len(ps)<=16 and len({p['request_id'] for p in ps})==len(ps)
    assert all(r+(16-r)*256<=4096 for r in range(17))


def test_changed_frozen_design_rejected():
    plan=design(); plan['maximum_policy_executions']=25
    with pytest.raises(ValueError): verify_design(plan)


def test_warmup_preserves_prior_fixture():
    from robustbench.mgpu05.design import payload
    p=payload('balanced',0,'spread',warmup=True)
    assert (len(p['prompt']),p['max_tokens'],p['vllm_xargs']['lssp_class_id'])==(128,4,'tight')
    assert p['vllm_xargs']['lssp_ordinal']==999999
