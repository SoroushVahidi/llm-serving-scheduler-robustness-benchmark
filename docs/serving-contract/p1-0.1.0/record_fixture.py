"""Deterministic CPU event fixture; no tokenizer, scheduler, allocator or model."""
import json
from robustbench.serving_v2.ledger import (
    Ledger, RequestSpec, Plan, Acknowledgment, AllocationObservation, ClockStamp)

ledger = Ledger('p1-preserved-prefix-fixture', 'cpu_fixture')
clock = 0


def stamp(category='host_control'):
    global clock
    clock += 1
    return ClockStamp('synthetic/host/monotonic', float(clock), category)


def blocks(name, owned):
    return AllocationObservation(name, 'synthetic-pool', 9, 1, 7 if owned else 8,
                                 (1,) if owned else (), 0)


def work(name, epoch, start, end, samples):
    ledger.plan('r', Plan(name, name, epoch, start, end), stamp=stamp())
    ledger.acknowledge('r', Acknowledgment(name, epoch, start, end, samples), stamp=stamp())


ledger.enqueue(RequestSpec('r', 'engine-r', 4, 2, 'synthetic-input-identity',
    ClockStamp('synthetic/host/monotonic', 0., 'host_control')), stamp=stamp())
ledger.admit('r', blocks('admission-0', True), stamp=stamp())
work('partial', 0, 0, 2, ())
work('final-prefill', 0, 2, 4, (17,))
ledger.emit('r', 0, (17,), stamp=stamp('server_observation'))
ledger.preempt('r', blocks('external-preemption', False), stamp=stamp())
ledger.admit('r', blocks('admission-1', True), stamp=stamp())
work('replay-prompt', 1, 0, 4, ())
work('replay-retained-output', 1, 4, 5, (18,))
ledger.emit('r', 1, (18,), stamp=stamp('server_observation'))
ledger.observe('r', 0, (17, 18), stamp=stamp('client_observation'))
ledger.release('r', blocks('terminal-release', False), stamp=stamp())
print(json.dumps(ledger.export(), indent=2))
