import numpy as np
import pytest
from qiskit import QuantumCircuit
from qiskit.quantum_info import Operator, Statevector

from qviz import (
    PRESETS,
    GateSpec,
    bloch_vectors,
    build_circuit,
    from_qasm,
    gate_trajectory,
    grover_circuit,
    optimal_iterations,
    rotation_of,
    single_qubit_path,
    step_states,
    success_curve,
    to_qasm,
)
from qviz.hardware import fidelity, ideal_distribution, run_local


# ---------- Bloch geometry ----------
@pytest.mark.parametrize("gates, expected", [
    ([], (0, 0, 1)),
    (["x"], (0, 0, -1)),
    (["h"], (1, 0, 0)),
    (["h", "s"], (0, 1, 0)),
    (["h", "z"], (-1, 0, 0)),
])
def test_bloch_vector_cardinal_states(gates, expected):
    qc = QuantumCircuit(1)
    for g in gates:
        getattr(qc, g)(0)
    assert np.allclose(bloch_vectors(Statevector(qc))[0], expected, atol=1e-9)


def test_entangled_qubits_have_zero_length_vectors():
    _, specs, _ = PRESETS["Bell state Φ+"]
    sv = step_states(2, specs)[-1]
    for v in bloch_vectors(sv):
        assert np.linalg.norm(v) < 1e-9


@pytest.mark.parametrize("gate, theta", [("x", None), ("h", None), ("s", None), ("t", None),
                                         ("rx", 0.7), ("ry", 2.1), ("rz", -1.3), ("sx", None)])
def test_trajectory_ends_where_the_gate_sends_the_state(gate, theta):
    from qiskit.circuit.library import get_standard_gate_name_mapping

    g = get_standard_gate_name_mapping()[gate]
    g = type(g)(theta) if theta is not None else g
    u = Operator(g).data
    start_qc = QuantumCircuit(1)
    start_qc.ry(0.9, 0)
    start_qc.rz(0.4, 0)
    start = bloch_vectors(Statevector(start_qc))[0]
    end = bloch_vectors(Statevector(start_qc).evolve(Operator(u)))[0]
    path = gate_trajectory(start, u, frames=10)
    assert np.allclose(path[-1], end, atol=1e-9)
    assert all(abs(np.linalg.norm(p) - 1) < 1e-9 for p in path)  # stays on the sphere


def test_rotation_takes_short_way():
    _, theta = rotation_of(Operator(QuantumCircuit(1).compose(_rz(-0.5))).data)
    assert theta <= np.pi + 1e-12


def _rz(t):
    qc = QuantumCircuit(1)
    qc.rz(t, 0)
    return qc


def test_single_qubit_path_frames():
    pts, idx = single_qubit_path([("h", None), ("rz", np.pi / 2)], frames_per_gate=8)
    assert len(pts) == 1 + 16 and idx[0] == -1 and idx[-1] == 1
    assert np.allclose(pts[-1], (0, 1, 0), atol=1e-9)


# ---------- circuits ----------
def test_step_states_match_full_circuit():
    for name, (n, specs, _) in PRESETS.items():
        states = step_states(n, specs)
        assert len(states) == len(specs) + 1
        assert states[-1].equiv(Statevector(build_circuit(n, specs))), name


def test_gate_validation():
    with pytest.raises(ValueError):
        GateSpec("cx", (0,))
    with pytest.raises(ValueError):
        GateSpec("rx", (0,))
    with pytest.raises(ValueError):
        GateSpec("cx", (1, 1))
    with pytest.raises(ValueError):
        build_circuit(2, [GateSpec("h", (2,))])


def test_qasm_round_trip():
    n, specs, _ = PRESETS["Phase kickback"]
    specs = specs + [GateSpec("ry", (1,), 0.25)]
    n2, back = from_qasm(to_qasm(n, specs))
    assert n2 == n and [g.name for g in back] == [g.name for g in specs]
    assert np.isclose(back[-1].theta, 0.25)


# ---------- Grover ----------
@pytest.mark.parametrize("n, marked", [(2, ["11"]), (3, ["101"]), (4, ["0110"]), (4, ["0001", "1110"]), (5, ["10011"])])
def test_grover_finds_marked(n, marked):
    qc = grover_circuit(n, marked, measure=False)
    probs = Statevector(qc).probabilities_dict()
    assert sum(probs.get(m, 0) for m in marked) > 0.9


def test_grover_curve_peaks_at_optimal():
    curve = success_curve(4, ["1010"], 6)
    assert int(np.argmax(curve)) == optimal_iterations(4) == 3
    assert curve[0] == pytest.approx(1 / 16)


# ---------- hardware (local) ----------
def test_ideal_run_matches_distribution():
    qc = build_circuit(2, PRESETS["Bell state Φ+"][1])
    counts, isa = run_local(qc, None, shots=4000)
    assert set(counts) <= {"00", "11"}
    assert fidelity(counts, ideal_distribution(qc)) > 0.99


def test_noisy_replica_runs():
    pytest.importorskip("qiskit_ibm_runtime")
    qc = build_circuit(3, PRESETS["GHZ (3 qubits)"][1])
    counts, isa = run_local(qc, "ibm_fez (Heron r2, 156 q)", shots=2000)
    f = fidelity(counts, ideal_distribution(qc))
    assert 0.5 < f <= 1.0
    assert "cz" in isa.count_ops()


def test_parse_sequence():
    from qviz.circuits import parse_sequence

    seq = parse_sequence("H, S → T  RX(pi/2) rz(-0.5) S† √X")
    assert [g for g, _ in seq] == ["h", "s", "t", "rx", "rz", "sdg", "sx"]
    assert np.isclose(seq[3][1], np.pi / 2) and np.isclose(seq[4][1], -0.5)
    for bad in ["", "CX", "RX", "RX(__import__)"]:
        with pytest.raises(ValueError):
            parse_sequence(bad)
