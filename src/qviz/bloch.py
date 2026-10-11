"""Bloch-sphere geometry: per-qubit Bloch vectors and smooth gate trajectories for animation."""
from __future__ import annotations

import numpy as np
from qiskit.circuit.library import get_standard_gate_name_mapping
from qiskit.quantum_info import DensityMatrix, Operator, Pauli, Statevector, partial_trace

__all__ = ["bloch_vectors", "rotation_of", "gate_trajectory", "single_qubit_path", "purity"]

_PAULIS = [Pauli("X").to_matrix(), Pauli("Y").to_matrix(), Pauli("Z").to_matrix()]


def _reduced(state, qubit: int) -> np.ndarray:
    n = state.num_qubits
    others = [q for q in range(n) if q != qubit]
    rho = partial_trace(state, others) if others else DensityMatrix(state)
    return np.asarray(rho.data)


def bloch_vectors(state: Statevector | DensityMatrix) -> list[np.ndarray]:
    """(x, y, z) for each qubit (index 0 first). Length < 1 means the qubit is entangled or mixed."""
    vecs = []
    for q in range(state.num_qubits):
        rho = _reduced(state, q)
        vecs.append(np.real([np.trace(rho @ p) for p in _PAULIS]))
    return vecs


def purity(state, qubit: int) -> float:
    rho = _reduced(state, qubit)
    return float(np.real(np.trace(rho @ rho)))


def rotation_of(unitary: np.ndarray) -> tuple[np.ndarray, float]:
    """Axis n and angle θ such that the 2×2 unitary is e^{iφ}·exp(-iθ/2 n·σ)."""
    u = unitary / np.sqrt(np.linalg.det(unitary))           # into SU(2)
    a = np.clip(np.real(np.trace(u)) / 2, -1.0, 1.0)         # cos(θ/2)
    theta = 2 * np.arccos(a)
    v = np.array([np.imag(np.trace(u @ p)) for p in _PAULIS]) * -0.5  # sin(θ/2)·n
    s = np.linalg.norm(v)
    if s < 1e-12:
        return np.array([0.0, 0.0, 1.0]), 0.0
    axis = v / s
    if theta > np.pi:  # take the shorter way round
        axis, theta = -axis, 2 * np.pi - theta
    return axis, float(theta)


def _rotate(vec: np.ndarray, axis: np.ndarray, angle: float) -> np.ndarray:
    # Rodrigues' rotation formula
    return (vec * np.cos(angle) + np.cross(axis, vec) * np.sin(angle)
            + axis * np.dot(axis, vec) * (1 - np.cos(angle)))


def gate_trajectory(start: np.ndarray, unitary: np.ndarray, frames: int = 20) -> list[np.ndarray]:
    """Points along the arc a single-qubit gate traces on the Bloch sphere (start and end included)."""
    axis, theta = rotation_of(unitary)
    return [_rotate(np.asarray(start, float), axis, theta * k / frames) for k in range(frames + 1)]


def single_qubit_path(gates: list[tuple[str, float | None]], frames_per_gate: int = 20):
    """Animate a 1-qubit gate sequence from |0⟩.

    Returns (points, gate_index) where gate_index[i] says which gate is playing at frame i
    (-1 for the initial frame).
    """
    mapping = get_standard_gate_name_mapping()
    point = np.array([0.0, 0.0, 1.0])
    points, idx = [point], [-1]
    for k, (name, theta) in enumerate(gates):
        gate = mapping[name]
        if theta is not None:
            gate = type(gate)(theta)
        u = Operator(gate).data
        arc = gate_trajectory(point, u, frames_per_gate)[1:]
        points += arc
        idx += [k] * len(arc)
        point = arc[-1]
    return points, idx
