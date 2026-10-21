"""CPU-only conformance: real scheduler/KV objects, synthetic runner replies.

The literal decision/state tables below are independently specified. These
tests neither run a model nor authorize partial-prefill serving experiments.
"""
import pytest

from vllm.v1.outputs import ModelRunnerOutput
from vllm.v1.request import RequestStatus
from robustbench.mgpu00.metadata import RequestMetadata
from robustbench.mgpu00.slai import Candidate, SlaiCore
from test_scheduler import request, finish


@pytest.mark.parametrize('slai', [False, True])
@pytest.mark.parametrize('phase', ['waiting', 'running', 'finished'])
def test_engine_identity_reuse_rejected_without_state_mutation(scheduler_factory, slai, phase):
    s = scheduler_factory(slai=slai)
    original = request(0, output=1 if phase == 'finished' else 2)
    s.add_request(original)
    if phase != 'waiting':
        finish(s, s.schedule())
    metadata = dict(s.mgpu_metadata)
    admitted = set(s.mgpu_admitted)
    waiting, running, requests = list(s.waiting), list(s.running), dict(s.requests)
    events = list(s.test_events)
    replacement = request(1)  # Distinct workload ID and ordinal, same engine ID.
    replacement.request_id = original.request_id
    with pytest.raises(ValueError, match='engine request identity'):
        s.add_request(replacement)
    assert s.mgpu_metadata == metadata
    assert s.mgpu_admitted == admitted
    assert (list(s.waiting), list(s.running), s.requests) == (waiting, running, requests)
    assert s.test_events == events
    # Failed admission cannot poison an otherwise valid request stream.
    s.add_request(request(1))
    assert len(s.mgpu_metadata) == 2


@pytest.mark.parametrize('utilization', [float('nan'), float('inf'), -float('inf'),
                                        -.01, 1.01, None])
def test_invalid_kv_observation_cannot_change_lst_or_batch_history(utilization):
    core = SlaiCore(2)
    c = Candidate('r0', RequestMetadata('r0', 0, 'tight', 0., 30., 1.), 128)
    core.batch_completed(start_s=1., end_s=1.002, progressed=[c], kv_utilization=.5)
    before = (core.batches, core.total_batch_s, dict(core.lst))
    with pytest.raises(ValueError, match='KV utilization'):
        core.batch_completed(start_s=2., end_s=2.002, progressed=[c],
                             kv_utilization=utilization)
    assert (core.batches, core.total_batch_s, core.lst) == before


def synthetic_output(s, scheduled, token_lists):
    """Deliver explicitly chosen samples; partial-prefill chunks emit none."""
    ids = list(scheduled.num_scheduled_tokens)
    s.update_from_output(scheduled, ModelRunnerOutput(req_ids=ids,
        req_id_to_index={rid: i for i, rid in enumerate(ids)},
        sampled_token_ids=token_lists))


def test_native_partial_prefill_progress_and_first_sample(scheduler_factory):
    s = scheduler_factory(slai=False, checked=False, budget=128)
    r = request(0, prompt=300, output=2)
    s.add_request(r)
    # Computed tokens advance optimistically at schedule(), not at GPU completion.
    # No sample for the first two chunks; first sample at the FINAL prefill.
    table = [(128, 128, 0, []), (128, 256, 0, []),
             (44, 300, 0, [42]), (1, 301, 1, [43])]
    for tokens, computed, prior_samples, sampled in table:
        out = s.schedule()
        assert out.num_scheduled_tokens == {'r0': tokens}
        assert (r.num_computed_tokens, r.num_output_tokens) == (computed, prior_samples)
        synthetic_output(s, out, [sampled])
        assert r.num_output_tokens == prior_samples + len(sampled)
    assert r.status == RequestStatus.FINISHED_LENGTH_CAPPED
    assert list(r.output_token_ids) == [42, 43]


def test_native_decode_and_long_prefill_share_budget(scheduler_factory):
    s = scheduler_factory(slai=False, checked=False, budget=128)
    s.add_request(request(0, prompt=1, output=8))
    first = s.schedule()
    synthetic_output(s, first, [[42]])
    s.add_request(request(1, prompt=300))
    for expected in ({'r0': 1, 'r1': 127}, {'r0': 1, 'r1': 127},
                     {'r0': 1, 'r1': 46}):
        out = s.schedule()
        assert out.num_scheduled_tokens == expected
        synthetic_output(s, out, [[42], [42] if expected['r1'] == 46 else []])
    assert s.requests['r1'].num_output_tokens == 1


def test_native_full_input_fit_check_is_not_full_allocation(scheduler_factory):
    # One reserved null block; 17 blocks leave exactly 256 tokens of capacity.
    s = scheduler_factory(slai=False, checked=False, budget=128, blocks=17)
    s.add_request(request(0, prompt=256))
    assert s.scheduler_reserve_full_isl is True
    out = s.schedule()
    assert out.num_scheduled_tokens == {'r0': 128}
    assert s.kv_cache_manager.block_pool.get_num_free_blocks() == 8
    synthetic_output(s, out, [[]])
    out = s.schedule()
    assert out.num_scheduled_tokens == {'r0': 128}
    assert s.kv_cache_manager.block_pool.get_num_free_blocks() == 0
    # If only the first chunk fits, full-input admission waits instead.
    short = scheduler_factory(slai=False, checked=False, budget=128, blocks=9)
    short.add_request(request(0, prompt=256))
    assert short.schedule().num_scheduled_tokens == {}
    assert len(short.waiting) == 1 and not short.running
    assert short.kv_cache_manager.block_pool.get_num_free_blocks() == 8


def test_native_recompute_preserves_generated_prefix(scheduler_factory):
    s = scheduler_factory(slai=False, checked=False, blocks=9)
    r = request(0, prompt=128)
    s.add_request(r)
    synthetic_output(s, s.schedule(), [[42]])
    # Token 129 needs a ninth usable block, but only eight exist.
    out = s.schedule()
    assert out.num_scheduled_tokens == {}
    assert out.preempted_req_ids == {'r0'}
    assert r.status == RequestStatus.PREEMPTED
    assert r.num_computed_tokens == 0 and r.num_preemptions == 1
    assert list(r.output_token_ids) == [42] and r.num_tokens == 129
    assert s.kv_cache_manager.block_pool.get_num_free_blocks() == 8


@pytest.mark.parametrize('slai,expected', [(False, ['r0', 'r1']), (True, ['r1', 'r0'])])
def test_admission_follows_policy_not_declared_deadline(scheduler_factory, slai, expected):
    s = scheduler_factory(slai=slai, slots=1)
    for i, cls in [(0, 'loose'), (1, 'tight')]:
        r = request(i, cls, output=1)
        # Both have already arrived at the engine. Evaluation deadlines do
        # not turn FCFS or SLAI's class/length admission into an EDF policy.
        r.sampling_params.extra_args['lssp_deadline_s'] = .01 if i == 0 else 30.
        s.add_request(r)
    for rid in expected:
        out = s.schedule()
        assert out.num_scheduled_tokens == {rid: 128}
        finish(s, out)
