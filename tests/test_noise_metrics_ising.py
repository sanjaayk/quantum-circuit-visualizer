import numpy as np
import pytest

from qlabs import (
    construct_ising_circuit,
    count_swap_gates,
    ghz_chain,
    mirror_circuit,
    quantum_circuit_params,
    repeated_x_circuit,
    repeated_x_meas_x_circuit,
    survival_curve,
)


def test_repeated_x_gate_count():
    assert repeated_x_circuit(4).count_ops()["x"] == 8
    assert repeated_x_meas_x_circuit(3).count_ops()["h"] == 2


def test_noiseless_survival_is_one():
    assert survival_curve(0.0, [0, 5, 10], shots=200) == [1.0, 1.0, 1.0]


def test_depolarizing_survival_decays():
    p = survival_curve(0.04, [0, 30], shots=4000, seed=11)
    assert p[0] == 1.0 and p[1] < 0.75


def test_circuit_params():
    params = quantum_circuit_params(ghz_chain(4))
    assert params["Number of qubits"] == 4
    assert params["Multi-qubit gates"] == 3
    assert params["2-qubit depth"] == 3
    assert count_swap_gates(ghz_chain(4)) == 0


def test_mirror_returns_to_zero():
    from qiskit.quantum_info import Statevector

    ising = construct_ising_circuit(6, 2, np.pi / 8, barrier=False)
    mirror = mirror_circuit(ising, measure=False)
    assert np.isclose(abs(Statevector(mirror).data[0]) ** 2, 1.0)


@pytest.mark.parametrize("method", ["dd", "pt", "trex", "zne", "pec"])
def test_mitigation_presets(method):
    pytest.importorskip("qiskit_ibm_runtime")
    from qlabs.mitigation import estimator_options

    assert estimator_options(method) is not None
