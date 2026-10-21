"""Frozen synthetic engineering design, independent of measured outcomes."""
import random
from .evidence import digest

MODEL = 'Qwen/Qwen2.5-0.5B-Instruct'
REVISION = '7ae557604adf67be50417f59c2c2f167def9a775'
POLICIES = ['native_fcfs', 'slai_mgpu00_checked']
SEED = 20261021


def payload(window, index, region, *, warmup=False):
    if window not in ('balanced', 'boundary') or region not in ('spread', 'burst'):
        raise ValueError('Unreviewed engineering cell')
    prompt, output = (128, 128) if window == 'balanced' else [(1,256),(256,128),(64,256),(128,64)][index % 4]
    arrival = (index if region == 'spread' else index // 4) * .2
    rid = f'fixture-{window}-{index:02d}'
    if warmup:
        prompt, output, arrival, index, rid = 128, 4, 0., 999999, 'fixture-warmup'
    return dict(model=MODEL, request_id=rid, prompt=([63122,16614,12507] * (prompt//3+1))[:prompt],
        max_tokens=output, temperature=0., seed=0, ignore_eos=True, n=1, echo=False,
        stream=True, stream_options={'include_usage': True}, return_token_ids=True,
        skip_special_tokens=False, spaces_between_special_tokens=False,
        vllm_xargs={'lssp_schema':'mgpu00-v1', 'lssp_request_id':rid, 'lssp_ordinal':index,
                    'lssp_class_id':'tight' if warmup else ['loose','tight','medium'][index % 3], 'lssp_arrival_s':arrival,
                    'lssp_deadline_s':arrival+30., 'lssp_weight':1.})


def cohort(window, region):
    return [payload(window, i, region) for i in range(12 if window == 'balanced' else 16)]


def design():
    rng = random.Random(SEED)
    cells = [(w,r,k) for w in ('balanced','boundary') for r in ('spread','burst') for k in range(3)]
    rng.shuffle(cells)
    orders = [POLICIES, list(reversed(POLICIES))] * 6
    rng.shuffle(orders)
    blocks = []
    for i, ((w,r,k), order) in enumerate(zip(cells, orders)):
        requests = cohort(w,r)
        blocks.append(dict(block=i, window=w, region=r, repetition=k, policy_order=order,
                           payloads_sha256=digest(requests), requests=len(requests),
                           arrival_duration_s=requests[-1]['vllm_xargs']['lssp_arrival_s']+.2))
    return dict(schema='mgpu05-design-v1', status='DRAFT_AUTHOR_REVIEW_REQUIRED', seed=SEED,
                synthetic_only=True, model=MODEL, revision=REVISION, policies=POLICIES,
                maximum_policy_executions=24, maximum_allocations=12,
                allocation_minutes=50, maximum_gpu_hours=10., readiness_timeout_s=1200,
                request_timeout_s=120, warmup_timeout_s=60, independent_server_per_execution=True,
                contract={'prompt_cap':256,'max_active':16,'token_budget':4096,'max_model_len':512,
                          'chunked_prefill':True,'tp':1,'dp':1,'pp':1}, blocks=blocks)


def verify_design(value):
    if value != design():
        raise ValueError('Design differs from reviewed deterministic plan')
    for b in value['blocks']:
        for p in cohort(b['window'],b['region']):
            if not 1 <= len(p['prompt']) <= 256 or len(p['prompt'])+p['max_tokens']>512:
                raise ValueError('Unsupported request')
    # For any number R of occupied decode slots, every remaining whole prefill fits.
    assert all(r + (16-r)*256 <= 4096 for r in range(17))
    return value
