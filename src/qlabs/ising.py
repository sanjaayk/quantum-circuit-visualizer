"""Trotterized transverse-field Ising circuits and mirror circuits (Lab 3)."""
from __future__ import annotations

import numpy as np
from qiskit import QuantumCircuit

__all__ = ["construct_ising_circuit", "mirror_circuit"]


def construct_ising_circuit(
    num_qubits: int, num_trotter_steps: int, rx_angle: float = np.pi / 8, barrier: bool = True
) -> QuantumCircuit:
    """Kicked-Ising Trotter circuit: an RX layer, then two brick layers of S†·CZ (ZZ) interactions."""
    qc = QuantumCircuit(num_qubits, name=f"Ising-{num_qubits}q-{num_trotter_steps}s")
    for _ in range(num_trotter_steps):
        qc.rx(rx_angle, range(num_qubits))
        if barrier:
            qc.barrier()
        for first_qubit in (1, 2):
            for idx in range(first_qubit, num_qubits, 2):
                qc.sdg([idx - 1, idx])
                qc.cz(idx - 1, idx)
        if barrier:
            qc.barrier()
    return qc


def mirror_circuit(circuit: QuantumCircuit, measure: bool = True) -> QuantumCircuit:
    """U followed by U†. Ideally returns |0…0⟩, so any other outcome is noise.

    The barrier stops the transpiler from cancelling the two halves.
    """
    mirror = QuantumCircuit(circuit.num_qubits, name=f"mirror({circuit.name})")
    mirror.compose(circuit, inplace=True)
    mirror.barrier()
    mirror.compose(circuit.inverse(), inplace=True)
    if measure:
        mirror.measure_all()
    return mirror
