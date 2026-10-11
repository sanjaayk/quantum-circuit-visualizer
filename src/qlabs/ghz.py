"""GHZ-state builders developed across Labs 1 and 2.

Each function returns a Qiskit ``QuantumCircuit`` that prepares the n-qubit
GHZ state (|00…0⟩ + |11…1⟩)/√2. They differ in *how* entanglement spreads, which
is what decides circuit depth and how well the circuit fits real hardware.
"""
from __future__ import annotations

from collections import deque
from typing import Iterable

from qiskit import ClassicalRegister, QuantumCircuit, QuantumRegister
from qiskit.circuit.classical import expr

__all__ = [
    "ghz_chain",
    "ghz_log_depth",
    "ghz_center_out_line",
    "ghz_from_tree",
    "bfs_spanning_tree",
    "ghz_on_coupling_map",
    "ghz_nearest_neighbor_3q",
    "dynamic_ghz_circuit",
]


def ghz_chain(n: int) -> QuantumCircuit:
    """Naive linear chain: H(0), CX(0,1), CX(1,2), … — depth grows as n."""
    _check_n(n)
    qc = QuantumCircuit(n, name=f"GHZ-chain-{n}")
    qc.h(0)
    for i in range(n - 1):
        qc.cx(i, i + 1)
    return qc


def ghz_log_depth(n: int) -> QuantumCircuit:
    """Doubling construction (Lab 1, Ex. 3): every entangled qubit copies itself
    onto a fresh one each layer, so depth is 1 + ceil(log2 n).

    For n = 16 this gives the depth-5 circuit from the lab.
    """
    _check_n(n)
    qc = QuantumCircuit(n, name=f"GHZ-log-{n}")
    qc.h(0)
    entangled = 1
    while entangled < n:
        for src in range(entangled):
            tgt = src + entangled
            if tgt < n:
                qc.cx(src, tgt)
        entangled *= 2
    return qc


def ghz_center_out_line(n: int) -> QuantumCircuit:
    """Start in the middle of a line and grow both ways (Lab 1, Ex. 5).

    Uses only nearest-neighbour CNOTs and roughly halves the depth of
    :func:`ghz_chain`.
    """
    _check_n(n)
    qc = QuantumCircuit(n, name=f"GHZ-center-{n}")
    mid = (n - 1) // 2
    qc.h(mid)
    left, right = mid - 1, mid + 1
    while left >= 0 or right < n:
        if left >= 0:
            qc.cx(left + 1, left)
            left -= 1
        if right < n:
            qc.cx(right - 1, right)
            right += 1
    return qc


def bfs_spanning_tree(
    edges: Iterable[tuple[int, int]], root: int, allowed: set[int] | None = None
) -> tuple[dict[int, int | None], dict[int, int]]:
    """Breadth-first spanning tree over a coupling map (Lab 1, Ex. 7).

    Returns ``(parent, depth)`` dictionaries keyed by qubit index.
    """
    adj: dict[int, set[int]] = {}
    for a, b in edges:
        if allowed is not None and (a not in allowed or b not in allowed):
            continue
        adj.setdefault(a, set()).add(b)
        adj.setdefault(b, set()).add(a)

    parent: dict[int, int | None] = {root: None}
    depth = {root: 0}
    queue = deque([root])
    while queue:
        node = queue.popleft()
        for nb in sorted(adj.get(node, ())):
            if nb not in parent:
                parent[nb] = node
                depth[nb] = depth[node] + 1
                queue.append(nb)
    return parent, depth


def ghz_from_tree(n: int, parent: dict[int, int | None], depth: dict[int, int]) -> QuantumCircuit:
    """Build a GHZ circuit layer-by-layer along a spanning tree.

    Every qubit receives one CX from its parent, and all qubits at the same tree
    depth are entangled in the same layer.
    """
    root = next(q for q, p in parent.items() if p is None)
    qc = QuantumCircuit(n, name=f"GHZ-tree-{n}")
    qc.h(root)
    for d in range(1, max(depth.values()) + 1):
        for q in sorted(q for q, dq in depth.items() if dq == d):
            qc.cx(parent[q], q)
    return qc


def ghz_on_coupling_map(edges: Iterable[tuple[int, int]], n: int, center: int) -> QuantumCircuit:
    """Hardware-aware GHZ on qubits ``0..n-1`` of a device, grown from ``center``.

    On FakeTorino with n=64 and center=25 this reproduces Sanjaay's Lab 1 result:
    transpiled depth 47 versus 256 for the naive chain.
    """
    parent, depth = bfs_spanning_tree(edges, center, allowed=set(range(n)))
    if len(parent) != n:
        raise ValueError(f"Qubits 0..{n-1} are not all connected to qubit {center}.")
    return ghz_from_tree(n, parent, depth)


def ghz_nearest_neighbor_3q() -> QuantumCircuit:
    """3-qubit GHZ using only nearest-neighbour CNOTs (Lab 1, Ex. 4).

    The non-local CX(0, 2) is replaced by the bridge identity
    CX(1,2) CX(0,1) CX(1,2) CX(0,1).
    """
    qc = QuantumCircuit(3, name="GHZ-bridge-3")
    qc.h(0)
    qc.cx(0, 1)
    qc.cx(1, 2)
    qc.cx(0, 1)
    qc.cx(1, 2)
    qc.cx(0, 1)
    return qc


def dynamic_ghz_circuit(num_qubits: int) -> QuantumCircuit:
    """Dynamic GHZ using mid-circuit measurement and classical feed-forward (Lab 2, Ex. 6).

    Sanjaay's graded solution. Even qubits start in |+⟩, odd "bridge" qubits are
    measured and reset, and the measurement outcomes drive X corrections, so
    the circuit trades depth for mid-circuit measurements.
    """
    if not isinstance(num_qubits, int) or num_qubits < 2:
        raise ValueError("num_qubits must be an integer >= 2.")

    qr = QuantumRegister(num_qubits, name="q")
    cr = ClassicalRegister(num_qubits, name="c")
    qc = QuantumCircuit(qr, cr, name=f"GHZ-dynamic-{num_qubits}")

    # 1. Hadamards on even qubits
    for i in range(0, num_qubits, 2):
        qc.h(i)
    # 2. CX(even -> previous odd): CX(2,1), CX(4,3), ...
    for i in range(2, num_qubits, 2):
        qc.cx(i, i - 1)
    # 3. CX(even -> next odd): CX(0,1), CX(2,3), ...
    _even_to_next_odd(qc, num_qubits)
    # 4. Measure + reset each bridge qubit; outcome flips the next pair
    for i in range(1, num_qubits - 1, 2):
        qc.measure(qr[i], cr[0])
        qc.reset(qr[i])
        targets = [t for t in (i + 1, i + 2) if t < num_qubits]
        with qc.if_test(expr.lift(cr[0])):
            for t in targets:
                qc.x(qr[t])
    if num_qubits % 2 == 0:  # boundary qubit: measure + reset, no correction
        qc.measure(qr[num_qubits - 1], cr[0])
        qc.reset(qr[num_qubits - 1])
    # 5. Re-entangle the reset odd qubits
    _even_to_next_odd(qc, num_qubits)

    qc.measure(qr, cr)
    return qc


def _even_to_next_odd(qc: QuantumCircuit, num_qubits: int) -> None:
    for i in range(0, num_qubits - 1, 2):
        qc.cx(i, i + 1)


def _check_n(n: int) -> None:
    if not isinstance(n, int) or n < 2:
        raise ValueError("n must be an integer >= 2.")
