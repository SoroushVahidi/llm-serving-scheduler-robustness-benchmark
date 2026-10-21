from dataclasses import replace
import random

import pytest
from vllm.sampling_params import SamplingParams
from vllm.v1.outputs import ModelRunnerOutput
from vllm.v1.request import Request, RequestStatus
from robustbench.mgpu00.metadata import RequestMetadata
from robustbench.mgpu00.slai import Candidate, SlaiCore, UnsupportedSemantics


def request(i, cls='tight', prompt=128, output=8):
    metadata = RequestMetadata(f'r{i}', i, cls, 0., 30., 1.)
    return Request(request_id=f'r{i}', prompt_token_ids=[12]*prompt, pooling_params=None,
        arrival_time=float(i), sampling_params=SamplingParams(max_tokens=output,
            ignore_eos=True, extra_args=metadata.xargs()))


def finish(scheduler, output):
    scheduler.test_time += .002
    ids = list(output.num_scheduled_tokens)
    return scheduler.update_from_output(output, ModelRunnerOutput(req_ids=ids,
        req_id_to_index={rid: i for i, rid in enumerate(ids)}, sampled_token_ids=[[42] for _ in ids]))


def test_real_scheduler_prefill_decode_and_holds(scheduler_factory):
    scheduler = scheduler_factory()
    for i, cls in enumerate(['loose', 'tight', 'medium']):
        scheduler.add_request(request(i, cls))
    first = scheduler.schedule()
    assert first.num_scheduled_tokens == {'r1': 128, 'r2': 128, 'r0': 128}
    finish(scheduler, first)
    second = scheduler.schedule()
    assert second.num_scheduled_tokens == {'r1': 1, 'r2': 1}
    assert len(scheduler.running) == 3
    finish(scheduler, second)
    assert sum(e['event'] == 'execution_verified' for e in scheduler.test_events) == 2


def reference_selection(running, waiting, lst, now, slots, limit):
    """Independent declarative oracle: maximize lexicographic service bits.

    Enumerate feasible subsets; do not call the adapter/core/simulator. The
    priority vector is specified from pinned SLAI stage ordering, with project's
    documented three-tier and ordinal adaptations. Only whole prompts fit here.
    """
    from itertools import product
    tbt = {'tight': .1, 'medium': .3, 'loose': .5}
    rank = lambda r: (lst[r.request_id], int(r.request_id[1:]))
    critical = sorted([r for r in running if lst[r.request_id] <= now], key=rank)
    residual = sorted([r for r in running if lst[r.request_id] > now], key=rank)
    prefills = sorted(waiting, key=lambda r: (
        tbt[r.sampling_params.extra_args['lssp_class_id']], r.num_prompt_tokens,
        r.sampling_params.extra_args['lssp_ordinal']))
    ordered = critical + prefills + residual
    running_ids = {r.request_id for r in running}
    feasible = []
    for bits in product((0, 1), repeat=len(ordered)):
        chosen = [r for r, bit in zip(ordered, bits) if bit]
        decodes = sum(r.request_id in running_ids for r in chosen)
        admissions = len(chosen)-decodes
        if decodes <= limit and admissions + len(running) <= slots:
            feasible.append((bits, chosen))
    chosen = max(feasible, key=lambda x: x[0])[1]
    return {r.request_id: 1 if r.request_id in running_ids else r.num_prompt_tokens for r in chosen}


def test_exhaustive_oracle_against_real_native_scheduler(scheduler_factory):
    rng = random.Random(20261021)
    for case in range(40):
        s = scheduler_factory(slots=5)
        for i in range(3):
            s.add_request(request(i, rng.choice(['tight', 'medium', 'loose']),
                                  rng.choice([1, 16, 128, 256]), 128))
        finish(s, s.schedule())
        for i in range(3, 6):
            s.add_request(request(i, rng.choice(['tight', 'medium', 'loose']),
                                  rng.choice([1, 16, 128, 256]), 128))
        s.mgpu_core.lst = {r.request_id: rng.choice([9., s.test_time, 11.]) for r in s.running}
        expected = reference_selection(s.running, list(s.waiting), s.mgpu_core.lst,
                                       s.test_time, 5, 2)
        output = s.schedule()
        assert output.num_scheduled_tokens == expected, case
        finish(s, output)


@pytest.mark.parametrize('slai', [False, True])
def test_overload_capacity_and_all_requests_finish(scheduler_factory, slai):
    s = scheduler_factory(slai=slai, slots=3)
    requests = [request(i, ['loose', 'medium', 'tight'][i % 3], 256 if i % 2 else 1,
                        32 if i == 0 else 3) for i in range(10)]
    for r in requests:
        s.add_request(r)
    for _ in range(100):
        if not s.requests:
            break
        out = s.schedule()
        assert len(s.running) <= 3
        assert out.num_scheduled_tokens
        finish(s, out)
    assert not s.requests
    assert all(r.num_output_tokens == r.max_tokens for r in requests)


def test_enabled_vs_disabled_native_token_equivalence(scheduler_factory):
    # Actual unmodified Scheduler, not a mocked schedule method. Disabling is
    # ONLY a CPU counterfactual, never proposed as a supported serving setup.
    engines = [scheduler_factory(slai=False, checked=False, chunked=flag, slots=3)
               for flag in (False, True)]
    for s in engines:
        for i in range(6):
            s.add_request(request(i, prompt=256 if i % 2 else 16, output=4))
    for _ in range(10):
        outputs = [s.schedule() for s in engines]
        assert outputs[0].num_scheduled_tokens == outputs[1].num_scheduled_tokens
        for s, output in zip(engines, outputs):
            finish(s, output)
    assert all(not s.requests for s in engines)


@pytest.mark.parametrize('slai', [False, True])
@pytest.mark.parametrize('prompt', [1, 255, 256])
def test_prompt_boundaries_are_whole(scheduler_factory, slai, prompt):
    s = scheduler_factory(slai=slai)
    s.add_request(request(0, prompt=prompt))
    out = s.schedule()
    assert out.num_scheduled_tokens == {'r0': prompt}
    finish(s, out)
    assert s.requests['r0'].num_computed_tokens == prompt
    assert s.requests['r0'].num_output_tokens == 1


@pytest.mark.parametrize('slai', [False, True])
def test_prompt_over_boundary_rejected_before_admission(scheduler_factory, slai):
    s = scheduler_factory(slai=slai)
    with pytest.raises(UnsupportedSemantics, match='Prompt exceeds'):
        s.add_request(request(0, prompt=257))
    assert not s.requests


@pytest.mark.parametrize('slai', [False, True])
def test_real_kv_admission_pressure_is_rejected(scheduler_factory, slai):
    s = scheduler_factory(slai=slai, blocks=9)
    s.add_request(request(0))
    s.add_request(request(1))
    with pytest.raises(UnsupportedSemantics, match='deviated'):
        s.schedule()


@pytest.mark.parametrize('slai', [False, True])
def test_real_kv_decode_preemption_is_rejected(scheduler_factory, slai):
    s = scheduler_factory(slai=slai, blocks=9)
    s.add_request(request(0))
    finish(s, s.schedule())
    # Eight blocks consumed by 128-token prompt; one reserved null block.
    # Token 129 requires a new block and native tries to preempt.
    with pytest.raises(UnsupportedSemantics, match='KV preemption'):
        s.schedule()


@pytest.mark.parametrize('slai', [False, True])
def test_partial_progress_and_overlap_rejected(scheduler_factory, slai):
    s = scheduler_factory(slai=slai)
    s.add_request(request(0))
    out = s.schedule()
    with pytest.raises(UnsupportedSemantics, match='overlapping'):
        s.schedule()
    finish(s, out)
    s.running[0].num_computed_tokens = 127
    with pytest.raises(UnsupportedSemantics, match='Partial-prefill'):
        s.schedule()


@pytest.mark.parametrize('mutation', ['missing', 'extra', 'two_tokens', 'bad_index'])
def test_execution_is_checked_separately(scheduler_factory, mutation):
    s = scheduler_factory()
    s.add_request(request(0))
    out = s.schedule()
    runner = ModelRunnerOutput(req_ids=['r0'], req_id_to_index={'r0': 0}, sampled_token_ids=[[42]])
    if mutation == 'missing':
        runner.sampled_token_ids = []
    elif mutation == 'extra':
        runner.req_ids += ['unplanned']
    elif mutation == 'two_tokens':
        runner.sampled_token_ids = [[42, 43]]
    else:
        runner.req_id_to_index = {'r0': 1}
    with pytest.raises(UnsupportedSemantics, match='Model-runner completion'):
        s.update_from_output(out, runner)
    assert not s.mgpu_core.batches  # no manufactured completion/LST update


@pytest.mark.parametrize('bad', [None, {}, {'lssp_schema': 'mgpu00-v1'},
    dict(RequestMetadata('r0', 0, 'tight', 0., 10., 1.).xargs(), lssp_class_id='unknown')])
def test_bad_transport_metadata_is_rejected(scheduler_factory, bad):
    s = scheduler_factory()
    r = request(0)
    r.sampling_params.extra_args = bad
    with pytest.raises(ValueError):
        s.add_request(r)


def test_duplicate_ordinal_rejected(scheduler_factory):
    s = scheduler_factory()
    s.add_request(request(0))
    r = request(1)
    r.sampling_params.extra_args['lssp_ordinal'] = 0
    with pytest.raises(ValueError, match='ordinal'):
        s.add_request(r)


def test_deadline_order_and_holds_do_not_refresh_lst(scheduler_factory):
    s = scheduler_factory()
    for i in range(3):
        s.add_request(request(i))
    finish(s, s.schedule())
    s.mgpu_core.lst = {'r0': 12., 'r1': 9., 'r2': 10.}
    # Absolute workload deadline is evaluation metadata, NOT SLAI's decode LST.
    s.mgpu_metadata['r0'] = replace(s.mgpu_metadata['r0'], deadline_s=.001)
    out = s.schedule()
    assert out.num_scheduled_tokens == {'r1': 1, 'r2': 1}
    finish(s, out)
    assert s.mgpu_core.lst['r0'] == 12.
    assert s.mgpu_core.lst['r1'] == pytest.approx(10.094)


@pytest.mark.parametrize('kv,expected', [(.959999, 10.09), (.96, 10.08), (1., 10.08)])
def test_independently_computed_lst_memory_threshold(kv, expected):
    core = SlaiCore(2)
    c = Candidate('r0', RequestMetadata('r0', 0, 'tight', 0., 30., 1.), 128)
    core.batch_completed(start_s=9.998, end_s=10., progressed=[c], kv_utilization=kv)
    assert core.lst['r0'] == pytest.approx(expected)


def test_explicit_contention_reference_table():
    core = SlaiCore(2)
    cs = [Candidate(f'r{i}', RequestMetadata(f'r{i}', i, 'tight', 0., 30., 1.), 4)
          for i in range(4)]
    core.lst = {'r0': .9, 'r1': 1.1, 'r2': 1.2}
    # One critical decode, full prefill, then one residual decode fits exactly.
    plan, _, held = core.plan(now_s=1., decoding=cs[:3], waiting=cs[3:],
        token_budget=6, active_count=3, max_active=4)
    assert plan == {'r0': 1, 'r3': 4, 'r1': 1}
    assert [c.engine_id for c in held] == ['r2']
    # Five tokens fits critical + prefill, but no residual decode.
    plan, _, _ = core.plan(now_s=1., decoding=cs[:3], waiting=cs[3:],
        token_budget=5, active_count=3, max_active=4)
    assert plan == {'r0': 1, 'r3': 4}
    with pytest.raises(UnsupportedSemantics, match='partial-prefill'):
        core.plan(now_s=1., decoding=cs[:3], waiting=cs[3:],
            token_budget=4, active_count=3, max_active=4)


@pytest.mark.parametrize('slai', [False, True])
def test_full_token_bound_with_maximum_admissions(scheduler_factory, slai):
    s = scheduler_factory(slai=slai)
    for i in range(17):
        s.add_request(request(i, prompt=256, output=1))
    out = s.schedule()
    assert len(out.num_scheduled_tokens) == 16
    assert sum(out.num_scheduled_tokens.values()) == 4096
    assert len(s.waiting) == 1
    finish(s, out)
    out = s.schedule()
    assert out.num_scheduled_tokens == {'r16': 256}
    finish(s, out)
    assert not s.requests


@pytest.mark.parametrize('slai', [False, True])
def test_actual_native_partial_split_is_caught(scheduler_factory, slai, monkeypatch):
    s = scheduler_factory(slai=slai)
    s.add_request(request(0))
    # Fault injection after effective configuration validation: force native
    # threshold splitting. No schedule method is mocked.
    s.scheduler_config.long_prefill_token_threshold = 127
    with pytest.raises(UnsupportedSemantics, match='deviated|partial-prefill'):
        s.schedule()


@pytest.mark.parametrize('slai', [False, True])
def test_context_limit_is_rejected(scheduler_factory, slai):
    s = scheduler_factory(slai=slai)
    with pytest.raises(UnsupportedSemantics, match='context'):
        s.add_request(request(0, prompt=256, output=257))


def test_model_runner_nan_rejected(scheduler_factory):
    s = scheduler_factory()
    s.add_request(request(0))
    out = s.schedule()
    runner = ModelRunnerOutput(req_ids=['r0'], req_id_to_index={'r0': 0},
        sampled_token_ids=[[42]], num_nans_in_logits={'r0': 1})
    with pytest.raises(UnsupportedSemantics, match='Nonfinite'):
        s.update_from_output(out, runner)
    assert not s.mgpu_core.batches
