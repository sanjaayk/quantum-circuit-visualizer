"""Grover's search: oracle, diffuser, full circuit and the amplitude-amplification curve."""
from __future__ import annotations

import math

import numpy as np
from qiskit import QuantumCircuit
from qiskit.quantum_info import Statevector

__all__ = ["grover_oracle", "diffuser", "grover_circuit", "optimal_iterations", "success_curve"]


def _check(n: int, marked: list[str]) -> None:
    if not marked:
        raise ValueError("Mark at least one bitstring.")
    for m in marked:
        if len(m) != n or set(m) - {"0", "1"}:
            raise ValueError(f"{m!r} is not a {n}-bit string")


def _mcz(qc: QuantumCircuit, n: int) -> None:
    """Phase-flip |11…1⟩ on all n qubits."""
    if n == 1:
        qc.z(0)
        return
    qc.h(n - 1)
    qc.mcx(list(range(n - 1)), n - 1)
    qc.h(n - 1)


def grover_oracle(n: int, marked: list[str]) -> QuantumCircuit:
    """Flip the sign of each marked basis state. Bitstrings are written q(n-1)…q0, like Qiskit counts."""
    _check(n, marked)
    qc = QuantumCircuit(n, name="Oracle")
    for m in marked:
        zeros = [q for q in range(n) if m[n - 1 - q] == "0"]
        if zeros:
            qc.x(zeros)
        _mcz(qc, n)
        if zeros:
            qc.x(zeros)
    return qc


def diffuser(n: int) -> QuantumCircuit:
    """Reflection about the uniform superposition (inversion about the mean)."""
    qc = QuantumCircuit(n, name="Diffuser")
    qc.h(range(n))
    qc.x(range(n))
    _mcz(qc, n)
    qc.x(range(n))
    qc.h(range(n))
    return qc


def optimal_iterations(n: int, num_marked: int = 1) -> int:
    return max(1, math.floor(math.pi / 4 * math.sqrt(2**n / num_marked)))


def grover_circuit(n: int, marked: list[str], iterations: int | None = None, measure: bool = True,
                   barriers: bool = True) -> QuantumCircuit:
    _check(n, marked)
    k = optimal_iterations(n, len(marked)) if iterations is None else iterations
    oracle, diff = grover_oracle(n, marked), diffuser(n)
    qc = QuantumCircuit(n, name=f"Grover-{n}")
    qc.h(range(n))
    for _ in range(k):
        if barriers:
            qc.barrier()
        qc.compose(oracle, inplace=True)
        qc.compose(diff, inplace=True)
    if measure:
        qc.measure_all()
    return qc


def success_curve(n: int, marked: list[str], max_iterations: int) -> list[float]:
    """Probability of measuring a marked state after 0, 1, …, max_iterations Grover steps."""
    _check(n, marked)
    idx = [int(m, 2) for m in marked]
    step = grover_oracle(n, marked).compose(diffuser(n))
    init = QuantumCircuit(n)
    init.h(range(n))
    sv = Statevector(init)
    out = [float(np.sum(np.abs(sv.data[idx]) ** 2))]
    for _ in range(max_iterations):
        sv = sv.evolve(step)
        out.append(float(np.sum(np.abs(sv.data[idx]) ** 2)))
    return out
