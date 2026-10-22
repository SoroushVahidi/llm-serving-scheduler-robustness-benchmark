"""Opt-in CPU control and execution-attestation boundary over unchanged P2A."""
from dataclasses import dataclass, asdict
from ..ledger import ClockStamp
from ..p2a.native import NativeBoundary, require
from ..p2a.types import Proposal, Span, RunnerAck, Rejection, Reason, BoundaryError
from .hook import ControlHook, preflight, HOOK_ID

CONTROL_PROFILE = 'lssp-native-span-control/0.1.0'
S02_PROFILE = 'lssp-slai-s02-prefill-control/0.1.0'


@dataclass(frozen=True)
class ControlPlan:
    proposal: Proposal
    holds: tuple[str, ...]


@dataclass(frozen=True)
class ExecutionAttestation:
    batch_id: str
    native_step: int
    accepted: tuple
    executed: tuple
    sample_mask: tuple[bool, ...]
    completion: str
    quiescent: bool
    quiescence_evidence: str
    start: ClockStamp
    end: ClockStamp
    provenance: str = 'synthetic_cpu'


class ControlledBoundary(NativeBoundary):
    def __init__(self, scheduler, run_id, *, enabled=False):
        super().__init__(scheduler,run_id,enabled=enabled)
        self.hook = ControlHook(scheduler,enabled=True)
        self._control_attempts = []
        self._attestations = set()

    def schedule(self, control, *, stamp):
        try:
            self._live()
            self._stamp(stamp)
            require(type(control) is ControlPlan, 'control plan type')
            require(self._pending is None, 'unacknowledged batch')
            require(control.proposal.batch_id not in self._used, 'reused batch ID')
            # Check known monotonic-domain causality before native mutation.
            times = [e['stamp']['seconds'] for e in self._ledger.export()['events']
                     if e['stamp']['domain'] == stamp.domain and e['stamp']['category'] == stamp.category]
            require(not times or stamp.seconds >= max(times), 'control clock reversal')
            preflight(self.s,control.proposal,control.holds)
            self._control_attempts.append(dict(control=asdict(control),stamp=asdict(stamp),preflight='PASS'))
            self.hook.armed = (control.proposal,control.holds)
            result = super().schedule(control.proposal,stamp=stamp)
            self.hook.armed = None
            if self._batches and self._batches[-1]['proposal']['batch_id'] == control.proposal.batch_id:
                self._batches[-1]['control'] = asdict(control)
            if isinstance(result,Rejection):
                self.hook.stopped = True
                self._control_attempts[-1]['failure_native_snapshot'] = self._snapshot()
                self._control_attempts[-1]['native_step_after_failure'] = self.s.current_step
            return result
        except Exception as e:
            self._control_attempts.append(dict(preflight='FAIL',detail=str(e)))
            self._stop(Reason.INVALID,e)
            self.hook.stopped = True
            return Rejection(getattr(getattr(control,'proposal',None),'batch_id',''),Reason.INVALID,str(e),False)

    def acknowledge(self, attestation, runner_output, *, stamp):
        try:
            self._live()
            require(self._pending is not None, 'no accepted batch')
            accepted,_,record = self._pending
            require(type(attestation) is ExecutionAttestation, 'attestation type')
            record['attestation_attempt'] = asdict(attestation)
            a = attestation
            require(a.provenance == 'synthetic_cpu' and a.completion == 'complete' and
                    a.quiescent is True and type(a.quiescence_evidence) is str and
                    bool(a.quiescence_evidence.strip()) and a.quiescence_evidence not in self._attestations,
                    'partial/missing/nonquiescent/synthetic evidence')
            require(all(type(v) is tuple and all(type(x) is Span and
                    type(x.request_id) is str and all(type(n) is int for n in (x.epoch,x.start,x.end))
                    for x in v) for v in (a.accepted,a.executed)), 'attested span types')
            require(a.accepted == accepted.spans and a.executed == a.accepted, 'executed span disagreement')
            require(type(a.start) is ClockStamp and type(a.end) is ClockStamp, 'attestation clocks')
            a.start.validate(); a.end.validate(); self._stamp(stamp)
            require(a.start.category == a.end.category == 'host_control' and
                    a.start.domain == a.end.domain == stamp.domain and
                    a.start.seconds <= a.end.seconds <= stamp.seconds, 'clock domain/causality')
            planned = self._ledger.export()['events'][record['ledger_start']:record['ledger_planned']]
            require(all(e['stamp']['domain'] == a.start.domain and
                        e['stamp']['seconds'] <= a.start.seconds for e in planned), 'execution before schedule')
            super().acknowledge(RunnerAck(a.batch_id,a.native_step,a.executed,a.sample_mask,
                                         a.provenance,True,True),runner_output,stamp=stamp)
            record['attestation'] = asdict(a)
            self._attestations.add(a.quiescence_evidence)
        except Exception as e:
            self._stop(Reason.ACK,e)
            self.hook.stopped = True
            raise BoundaryError(str(e)) from e

    def export(self):
        result = super().export()
        result.update(schema='lssp-p2b-control/0.1.0',control_profile=CONTROL_PROFILE,
                      hook_id=HOOK_ID,patched_schedule_sha256=self.hook.digest,
                      control_attempts=list(self._control_attempts))
        # Detach even nested failed-attempt records.
        import json
        return json.loads(json.dumps(result,allow_nan=False))
