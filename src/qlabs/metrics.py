"""Circuit metrics from Lab 2 (Ex. 5 and Ex. 7)."""
from __future__ import annotations

from qiskit import QuantumCircuit

__all__ = ["quantum_circuit_params", "count_swap_gates", "compare_transpiled"]


def count_swap_gates(circuit: QuantumCircuit) -> int:
    """Number of SWAP gates in a circuit."""
    return sum(1 for inst in circuit.data if inst.operation.name == "swap")


def quantum_circuit_params(circuit: QuantumCircuit) -> dict:
    """Main cost figures for a circuit: qubits, depth, 2-qubit depth, gate counts, ancillas."""
    return {
        "Number of qubits": circuit.num_qubits,
        "Depth": circuit.depth(),
        "2-qubit depth": circuit.depth(filter_function=lambda inst: len(inst.qubits) == 2),
        "Gates": dict(circuit.count_ops()),
        "Multi-qubit gates": sum(1 for inst in circuit.data if len(inst.qubits) > 1),
        "Number of ancillas": circuit.num_ancillas,
    }


def compare_transpiled(circuits: dict[str, QuantumCircuit]) -> list[dict]:
    """Side-by-side table rows (depth, size, 2-qubit gates, SWAPs) for named circuits."""
    rows = []
    for name, qc in circuits.items():
        rows.append({
            "circuit": name,
            "depth": qc.depth(),
            "total gates": qc.size(),
            "2-qubit gates": qc.num_nonlocal_gates(),
            "SWAPs": count_swap_gates(qc),
        })
    return rows
