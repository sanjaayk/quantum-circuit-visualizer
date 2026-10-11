"""Noise experiments from Lab 2.

Repeating X an even number of times should return |0⟩. On a noisy device it
drifts, and how fast it drifts shows how strong the gate error is.
"""
from __future__ import annotations

from qiskit import QuantumCircuit

__all__ = [
    "repeated_x_circuit",
    "repeated_x_meas_x_circuit",
    "depolarizing_x_simulator",
    "run_counts",
    "prob_of_zero",
    "survival_curve",
    "PAULI_VISIBILITY",
]

# Lab 2, Ex. 4: which single-qubit Pauli errors each experiment can detect.
PAULI_VISIBILITY = {
    "X error": {"bit-flip sensitive": True, "phase-flip sensitive": False},
    "Y error": {"bit-flip sensitive": True, "phase-flip sensitive": True},
    "Z error": {"bit-flip sensitive": False, "phase-flip sensitive": True},
}


def repeated_x_circuit(n: int) -> QuantumCircuit:
    """2n X gates on |0⟩, then measure in Z. Ideal result is always 0 (bit-flip probe)."""
    qc = QuantumCircuit(1, 1, name=f"XX^{n}")
    for _ in range(2 * n):
        qc.x(0)
    qc.measure(0, 0)
    return qc


def repeated_x_meas_x_circuit(n: int) -> QuantumCircuit:
    """Prepare |+⟩, apply 2n X gates, measure in X. Ideal result is always 0 (phase-flip probe)."""
    qc = QuantumCircuit(1, 1, name=f"+XX^{n}")
    qc.h(0)
    for _ in range(2 * n):
        qc.x(0)
    qc.h(0)
    qc.measure(0, 0)
    return qc


def depolarizing_x_simulator(lam: float):
    """Aer simulator where every X gate suffers single-qubit depolarizing noise of strength ``lam``."""
    from qiskit_aer import AerSimulator
    from qiskit_aer.noise import NoiseModel, depolarizing_error

    noise_model = NoiseModel()
    noise_model.add_all_qubit_quantum_error(depolarizing_error(lam, 1), ["x"])
    return AerSimulator(noise_model=noise_model)


def run_counts(backend, circuit: QuantumCircuit, shots: int = 4096) -> dict[str, int]:
    """Run one circuit with SamplerV2 and return its counts dictionary."""
    from qiskit_ibm_runtime import SamplerV2 as Sampler

    result = Sampler(mode=backend).run([circuit], shots=shots).result()
    registers = list(result[0].data.keys())
    if len(registers) != 1:
        raise ValueError(f"Expected exactly one classical register, got {len(registers)}")
    return result[0].data[registers[0]].get_counts()


def prob_of_zero(counts: dict[str, int], nbits: int = 1) -> float:
    """Fraction of shots that returned the all-zeros bitstring."""
    return counts.get("0" * nbits, 0) / sum(counts.values())


def survival_curve(lam: float, n_values, shots: int = 4000, basis: str = "Z", seed: int | None = None):
    """Pr(0) after 2n noisy X gates for each n, using an Aer depolarizing model.

    ``basis="Z"`` uses :func:`repeated_x_circuit` and ``basis="X"`` uses
    :func:`repeated_x_meas_x_circuit`.
    """
    from qiskit import transpile

    sim = depolarizing_x_simulator(lam)
    if seed is not None:
        sim.set_options(seed_simulator=seed)
    build = repeated_x_circuit if basis.upper() == "Z" else repeated_x_meas_x_circuit
    out = []
    for n in n_values:
        # optimization_level=0 so the transpiler does not cancel the X·X pairs
        tqc = transpile(build(n), sim, optimization_level=0)
        counts = sim.run(tqc, shots=shots).result().get_counts()
        out.append(prob_of_zero(counts))
    return out
