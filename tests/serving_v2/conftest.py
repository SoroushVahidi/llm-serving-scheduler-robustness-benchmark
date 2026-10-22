import hashlib
import pytest
from robustbench.serving_v2.ledger import (
    Acknowledgment, AllocationObservation, ClockStamp, Ledger, Plan, RequestSpec)


class Harness:
    def __init__(self, p=4, o=3):
        self.ledger = Ledger('unit-run')
        self.t = 0
        self.serial = 0
        self.p = p
        self.o = o
        self.ledger.enqueue(self.spec(), stamp=self.time())

    def time(self, category='host_control', domain='host/boot/monotonic'):
        self.t += 1
        return ClockStamp(domain, float(self.t), category)

    def spec(self, rid='r', engine='e'):
        return RequestSpec(rid, engine, self.p, self.o, hashlib.sha256(b'synthetic').hexdigest(),
                           ClockStamp('host/boot/monotonic', 0., 'host_control'),
                           (('fixture', 'synthetic'),))

    def alloc(self, owned=True):
        self.serial += 1
        return AllocationObservation(f'obs{self.serial}', 'fixture-pool', 9, 1,
                                     7 if owned else 8, (1,) if owned else (), 0)

    def admit(self):
        return self.ledger.admit('r', self.alloc(), stamp=self.time())

    def work(self, start, end, epoch, samples=()):
        self.serial += 1
        plan = Plan(f'plan{self.serial}', f'batch{self.serial}', epoch, start, end)
        before = self.ledger.snapshot('r')
        self.ledger.plan('r', plan, stamp=self.time())
        # Planning is not acknowledged progress or generated output.
        planned = self.ledger.snapshot('r')
        assert planned.acknowledged == before.acknowledged
        assert planned.generated == before.generated
        return self.ledger.acknowledge('r', Acknowledgment(plan.plan_id, epoch, start, end, samples),
                                       stamp=self.time())

    def preempt(self):
        return self.ledger.preempt('r', self.alloc(False), stamp=self.time())

    def drain(self):
        s = self.ledger.snapshot('r')
        if s.emitted < len(s.generated):
            self.ledger.emit('r', s.emitted, s.generated[s.emitted:],
                             stamp=self.time('server_observation'))
        s = self.ledger.snapshot('r')
        if s.observed < s.emitted:
            self.ledger.observe('r', s.observed, s.generated[s.observed:s.emitted],
                                stamp=self.time('client_observation', 'client/boot/monotonic'))
        if s.allocation and s.allocation.owned_blocks:
            self.ledger.release('r', self.alloc(False), stamp=self.time())


@pytest.fixture
def harness():
    return Harness
