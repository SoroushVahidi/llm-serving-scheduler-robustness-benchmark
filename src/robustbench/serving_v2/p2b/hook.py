"""Instance-local constrained copy of pinned Scheduler.schedule; no global patch.

Only six exact source insertions. Native allocation/output/update remain native.
No rollback: a post-entry exception permanently poisons this hook.
"""
import difflib
import hashlib
import inspect
import textwrap

from ..p2a.native import require, verify_sources
from ..p2a.types import Proposal, Span, BoundaryError
from .pins import PATCH_SHA256

HOOK_ID = 'vllm-0.27.1-exact-span-hook/0.1.0'


def patched_schedule():
    verify_sources()
    from vllm.v1.core.sched.scheduler import Scheduler
    original = textwrap.dedent(inspect.getsource(Scheduler.schedule))
    edits = [
        ('        request = self.running[req_index]\n',
         '        if request.request_id not in self._p2b_spans:\n            req_index += 1\n            continue\n'),
        ('        # Schedule newly needed KV blocks for the request.\n',
         '        num_new_tokens = self._p2b_count(request, num_new_tokens)\n'),
        ('                # The request cannot be scheduled.\n                # Preempt the lowest-priority request.\n',
         '                raise RuntimeError("P2B_NATIVE_ALLOCATION_REFUSAL_NO_RETRY")\n'),
        ('            request = request_queue.peek_request()\n',
         '            if request.request_id not in self._p2b_spans:\n                break\n'),
        ('            reserved_blocks = 0\n',
         '            num_new_tokens = self._p2b_count(request, num_new_tokens)\n'),
        ('            if new_blocks is None:\n',
         '                raise RuntimeError("P2B_NATIVE_ALLOCATION_REFUSAL_NO_RETRY")\n'),
    ]
    source = original
    for index,(anchor,insertion) in enumerate(edits):
        anchor = '\n'+anchor
        require(source.count(anchor) == 1, f'patch anchor {index} changed')
        # Inserts 1/4/6 after the anchor; 2/3/5 before it.
        replacement = anchor+insertion if index in (0,3,5) else '\n'+insertion+anchor[1:]
        source = source.replace(anchor,replacement,1)
    namespace = dict(Scheduler.schedule.__globals__)
    exec(compile(source, '<'+HOOK_ID+'>', 'exec'),namespace)
    patch = ''.join(difflib.unified_diff(original.splitlines(True),source.splitlines(True),
                                       fromfile='v0.27.1/Scheduler.schedule',tofile=HOOK_ID))
    digest = hashlib.sha256(source.encode()).hexdigest()
    require(digest == PATCH_SHA256, 'versioned patch digest changed')
    return namespace['schedule'], patch, digest


def preflight(s, proposal, holds):
    """Read-only native-domain checks, before queue/current-step/KV mutation."""
    from vllm.v1.request import RequestStatus
    require(type(proposal) is Proposal and type(proposal.spans) is tuple and
            bool(proposal.spans), 'nonempty typed proposal required')
    require(type(proposal.batch_id) is str and bool(proposal.batch_id.strip()), 'batch ID')
    require(type(proposal.token_budget) is int and proposal.token_budget == s.max_num_scheduled_tokens
            and type(proposal.active_limit) is int and proposal.active_limit == s.max_num_running_reqs,
            'budget/slots')
    require(not s.skipped_waiting and not s.num_waiting_for_streaming_input and
            s._pause_state.name == 'UNPAUSED', 'unsupported queue/pause state')
    require(all(s.requests.get(r.request_id) is r for r in list(s.running)+list(s.waiting)),
            'queue object identity')
    running = [r.request_id for r in s.running]
    waiting = [r.request_id for r in s.waiting]
    require(len(set(running+waiting)) == len(running+waiting) and
            set(running+waiting) == set(s.requests), 'queue/live identity')
    require(all(r.status == (RequestStatus.RUNNING if rid in running else RequestStatus.WAITING)
                and r.num_in_flight_tokens == 0 and r.num_preemptions == 0 and
                not r.num_output_placeholders and not r.spec_token_ids and
                r.next_decode_eligible_step <= s.current_step+1
                for rid,r in s.requests.items()), 'inconsistent native state')
    chosen = []
    saw_waiting = False
    for span in proposal.spans:
        require(type(span) is Span and type(span.request_id) is str and
                span.request_id in s.requests and span.request_id not in chosen, 'span ID')
        require(all(type(v) is int for v in (span.epoch,span.start,span.end)) and
                span.epoch == 0, 'span epoch/type')
        r = s.requests[span.request_id]
        require(span.start == r.num_computed_tokens and span.start < span.end <= r.num_tokens and
                span.end <= s.max_model_len-1, 'span position')
        if span.request_id in waiting:
            saw_waiting = True
        else:
            require(not saw_waiting, 'CROSS_PHASE_ORDER_UNREPRESENTABLE')
        chosen.append(span.request_id)
    require(sum(x.end-x.start for x in proposal.spans) <= proposal.token_budget, 'budget exceeded')
    require(len(running)+sum(r in waiting for r in chosen) <= proposal.active_limit, 'resident slot exceeded')
    require(type(holds) is tuple and all(type(r) is str for r in holds) and
            len(holds) == len(set(holds)) and set(holds) == set(running)-set(chosen), 'explicit resident holds')
    pool = s.kv_cache_manager.block_pool
    blocks = [b for rid in s.requests for b in s.kv_cache_manager.get_block_ids(rid)[0]]
    require(len(blocks) == len(set(blocks)) and pool.null_block.block_id not in blocks and
            len(blocks)+1+pool.get_num_free_blocks() == pool.num_gpu_blocks, 'KV conservation')
    require(sum((r.num_prompt_tokens+r.max_tokens+s.block_size-1)//s.block_size
                for r in s.requests.values()) <= pool.num_gpu_blocks-1, 'NO_PRESSURE_DOMAIN_NOT_PROVEN')


class ControlHook:
    def __init__(self, scheduler, *, enabled=False):
        require(enabled is True and str(scheduler.vllm_config.device_config.device) == 'cpu',
                'explicit CPU-only hook opt-in required')
        self.s = scheduler
        self.function,self.patch,self.digest = patched_schedule()
        self.armed = None
        self.stopped = False
        scheduler._p2b_count = self.count
        scheduler.schedule = self.schedule

    def count(self, request, upper):
        span = self.s._p2b_spans[request.request_id]
        require(request.num_computed_tokens == span.start and
                type(upper) is int and upper >= span.end-span.start,
                'native position/bound changed before allocation')
        return span.end-span.start

    def schedule(self, throttle_prefills=False):
        require(not self.stopped and self.armed is not None and throttle_prefills is False,
                'unarmed/stopped/throttled control hook')
        proposal,holds = self.armed
        self.armed = None
        preflight(self.s,proposal,holds)
        from vllm.v1.core.sched.request_queue import FCFSRequestQueue
        s = self.s
        original_running = list(s.running)
        original_waiting = list(s.waiting)
        selected = [x.request_id for x in proposal.spans]
        s._p2b_spans = {x.request_id:x for x in proposal.spans}
        # Constraints validated above. Mutations below are explicit, not atomic.
        s.running[:] = [s.requests[r] for r in selected if s.requests[r] in original_running]+[
            r for r in original_running if r.request_id not in selected]
        s.waiting = FCFSRequestQueue([s.requests[r] for r in selected if s.requests[r] in original_waiting]+[
            r for r in original_waiting if r.request_id not in selected])
        try:
            output = self.function(s)
            require(list(output.num_scheduled_tokens.items()) ==
                    [(x.request_id,x.end-x.start) for x in proposal.spans], 'native substituted work')
            require(not output.preempted_req_ids, 'preemption forbidden')
            # Restore canonical resident/remaining-waiting order, NOT KV/progress.
            new = [r for r in s.running if r not in original_running]
            s.running[:] = original_running+new
            remaining = {r.request_id for r in s.waiting}
            s.waiting = FCFSRequestQueue([r for r in original_waiting if r.request_id in remaining])
            return output
        except BaseException:
            self.stopped = True
            raise
