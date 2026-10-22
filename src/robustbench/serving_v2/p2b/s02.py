"""Delegated S02 partial policy; NO LST, criticality, pressure or future lengths.

Paused FIFO then strict/original-prompt/ordinal waiting. If any prefill is
chosen, hold all decodes; otherwise decode by ordinal. This deliberately
omits SLAI's critical/residual numerical phases and is a separate partial ID.
"""
from dataclasses import dataclass
from .control import ControlPlan, S02_PROFILE
from ..p2a.types import Span, Proposal, BoundaryError


@dataclass(frozen=True)
class View:
    request_id: str
    original_prompt: int
    computed: int
    generated: int
    class_id: str
    ordinal: int
    resident: bool


class PrefillPolicy:
    profile_id = S02_PROFILE

    def __init__(self):
        self.paused = []
        self._identity = {}
        self._pending = None

    def propose(self, batch_id, views, budget, slots):
        if self._pending is not None:
            raise BoundaryError('S02 pending acknowledgment')
        if type(budget) is not int or budget <= 0 or type(slots) is not int or slots <= 0:
            raise BoundaryError('S02 bounds')
        if type(views) not in (list,tuple) or not all(type(r) is View for r in views):
            raise BoundaryError('S02 view types')
        ids = [r.request_id for r in views]
        ordinals = [r.ordinal for r in views]
        if len(ids) != len(set(ids)) or len(ordinals) != len(set(ordinals)):
            raise BoundaryError('S02 duplicate identity/ordinal')
        for r in views:
            if type(r) is not View or type(r.request_id) is not str or not r.request_id or \
               r.class_id not in ('tight','medium','loose') or type(r.resident) is not bool or \
               any(type(v) is not int or v < 0 for v in (r.original_prompt,r.computed,r.generated,r.ordinal)) or \
               r.original_prompt < 1 or r.computed >= r.original_prompt+r.generated:
                raise BoundaryError('S02 invalid view')
            key = (r.original_prompt,r.class_id,r.ordinal)
            if r.request_id in self._identity and self._identity[r.request_id] != key:
                raise BoundaryError('S02 immutable identity changed')
            if any(rid != r.request_id and old[2] == r.ordinal for rid,old in self._identity.items()):
                raise BoundaryError('S02 lifetime ordinal reused')
        byid = {r.request_id:r for r in views}
        partial = {r.request_id for r in views if r.resident and r.computed < r.original_prompt}
        if set(self.paused) != partial or len(self.paused) != len(partial):
            raise BoundaryError('S02 paused FIFO differs from acknowledged history')
        residents = sum(r.resident for r in views)
        if residents > slots:
            raise BoundaryError('S02 resident overcommitment')
        waiting = sorted((r for r in views if not r.resident),
                         key=lambda r:(r.class_id != 'tight',r.original_prompt,r.ordinal))
        chosen = []
        remaining = budget
        for r in [byid[rid] for rid in self.paused]+waiting:
            if remaining == 0 or (not r.resident and residents == slots):
                break
            if not r.resident:
                if r.computed != 0 or r.generated != 0:
                    raise BoundaryError('S02 recomputation unsupported')
                residents += 1
            count = min(r.original_prompt-r.computed,remaining)
            chosen.append(Span(r.request_id,0,r.computed,r.computed+count))
            remaining -= count
        if not chosen:
            for r in sorted((r for r in views if r.resident),key=lambda r:r.ordinal):
                if not remaining:
                    break
                if r.computed != r.original_prompt+r.generated-1 or r.generated < 1:
                    raise BoundaryError('S02 decode frontier')
                chosen.append(Span(r.request_id,0,r.computed,r.computed+1))
                remaining -= 1
        if not chosen:
            raise BoundaryError('S02 empty execution')
        selected = {s.request_id for s in chosen}
        holds = tuple(r.request_id for r in views if r.resident and r.request_id not in selected)
        proposal = ControlPlan(Proposal(batch_id,tuple(chosen),budget,slots),holds)
        self._pending = (proposal,byid)
        self._identity.update({r.request_id:(r.original_prompt,r.class_id,r.ordinal) for r in views})
        return proposal

    def acknowledged(self, batch_id):
        """Only invoke after successful boundary validation, never at proposal time."""
        if self._pending is None or self._pending[0].proposal.batch_id != batch_id:
            raise BoundaryError('S02 stale ACK')
        plan,views = self._pending
        selected = {s.request_id for s in plan.proposal.spans}
        self.paused = [rid for rid in self.paused if rid not in selected]+[
            s.request_id for s in plan.proposal.spans if s.end < views[s.request_id].original_prompt]
        self._pending = None


from .control import ControlledBoundary


class S02Boundary(ControlledBoundary):
    """Integrated partial S02 profile: only this planner may supply its plans."""
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.policy = PrefillPolicy()
        self._ordinals = set()

    def enqueue(self,spec,prompt_ids,*,stamp):
        from ..p2a.types import Reason
        try:
            spec.validate()
            metadata = dict(spec.metadata)
            if metadata.get('s02_class') not in ('tight','medium','loose'):
                raise BoundaryError('S02 missing/invalid class')
            ordinal = int(metadata['s02_ordinal'])
            if str(ordinal) != metadata['s02_ordinal'] or ordinal < 0 or ordinal in self._ordinals:
                raise BoundaryError('S02 invalid/duplicate ordinal')
            super().enqueue(spec,prompt_ids,stamp=stamp)
            self._ordinals.add(ordinal)
        except Exception as e:
            self._stop(Reason.INVALID,e)
            raise BoundaryError(str(e)) from e

    def schedule(self,*args,**kwargs):
        raise BoundaryError('use schedule_s02; arbitrary plans have a different profile')

    def schedule_s02(self,batch_id,*,stamp):
        from ..p2a.types import Reason
        try:
            self._live()
            views = []
            for rid in self.s.requests:
                r = self._ledger.snapshot(self._ids[rid])
                m = dict(r.spec.metadata)
                views.append(View(rid,r.spec.prompt_tokens,r.acknowledged,len(r.generated),
                                  m['s02_class'],int(m['s02_ordinal']),r.resident))
            plan = self.policy.propose(batch_id,views,self.s.max_num_scheduled_tokens,self.s.max_num_running_reqs)
            return ControlledBoundary.schedule(self,plan,stamp=stamp)
        except Exception as e:
            self._stop(Reason.INVALID,e)
            raise BoundaryError(str(e)) from e

    def acknowledge(self,attestation,runner_output,*,stamp):
        super().acknowledge(attestation,runner_output,stamp=stamp)
        self.policy.acknowledged(attestation.batch_id)

    def export(self):
        result = super().export()
        result['control_profile'] = S02_PROFILE
        result['paused_fifo'] = list(self.policy.paused)
        return result
