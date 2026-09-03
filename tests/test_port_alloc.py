from __future__ import annotations

import socket

from robustbench.real_llm.port_alloc import allocate_port


def test_allocate_port_returns_bindable_port():
    alloc = allocate_port("127.0.0.1")
    assert 1 <= alloc.port <= 65535
    # Immediately bindable (best-effort -- confirms the OS considers it free
    # right after allocate_port released it, the same tiny window the real
    # caller relies on).
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(("127.0.0.1", alloc.port))


def test_allocate_port_method_labeled():
    alloc = allocate_port("127.0.0.1")
    assert alloc.method == "os_ephemeral_bind0"
    assert alloc.host == "127.0.0.1"


def test_allocate_port_no_fixed_modulus_collision_across_many_calls():
    """Regression test for the calibration launcher's PORT=8100+task_id%100
    bug: a fixed 100-port modulus guarantees collision once more than 100
    concurrent tasks share a node. allocate_port has no such bound -- calling
    it many times in quick succession should not produce the kind of
    small-integer-periodicity collision that arithmetic scheme had (e.g.
    task 19 and task 119 both landing on port 8119)."""
    ports = [allocate_port("127.0.0.1").port for _ in range(60)]
    # Not asserting all-distinct (OS ephemeral port reuse after release is
    # possible in principle), but the vast majority of 60 rapid allocations
    # should be distinct -- a >=100-collision rate here would indicate the
    # allocator degenerated into a small fixed range, which it must not.
    assert len(set(ports)) >= 55
