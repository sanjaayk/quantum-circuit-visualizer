"""qlabs: reusable building blocks from Sanjaay Kumaraguru's Qiskit Global Summer School 2026 labs."""
from .ghz import (
    bfs_spanning_tree,
    dynamic_ghz_circuit,
    ghz_center_out_line,
    ghz_chain,
    ghz_from_tree,
    ghz_log_depth,
    ghz_nearest_neighbor_3q,
    ghz_on_coupling_map,
)
from .ising import construct_ising_circuit, mirror_circuit
from .metrics import compare_transpiled, count_swap_gates, quantum_circuit_params
from .noise import (
    PAULI_VISIBILITY,
    prob_of_zero,
    repeated_x_circuit,
    repeated_x_meas_x_circuit,
    survival_curve,
)

__version__ = "1.0.0"
