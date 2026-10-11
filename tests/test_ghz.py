import numpy as np
import pytest
from qiskit.quantum_info import Statevector

from qlabs import ghz


def assert_ghz(qc):
    probs = np.abs(Statevector(qc).data) ** 2
    assert np.isclose(probs[0], 0.5) and np.isclose(probs[-1], 0.5)


@pytest.mark.parametrize("n", [2, 3, 5, 8, 16])
@pytest.mark.parametrize("builder", [ghz.ghz_chain, ghz.ghz_log_depth, ghz.ghz_center_out_line])
def test_builders_make_ghz(builder, n):
    assert_ghz(builder(n))


def test_log_depth_16_is_depth_5():  # Lab 1, Ex. 3
    assert ghz.ghz_log_depth(16).depth() == 5


def test_center_out_5_is_depth_4():  # Lab 1, Ex. 5
    assert ghz.ghz_center_out_line(5).depth() == 4


def test_bridge_uses_only_nearest_neighbours():  # Lab 1, Ex. 4
    qc = ghz.ghz_nearest_neighbor_3q()
    assert_ghz(qc)
    for inst in qc.data:
        if inst.operation.name == "cx":
            a, b = (qc.find_bit(q).index for q in inst.qubits)
            assert abs(a - b) == 1


def test_t_shape_tree():  # Lab 1, Ex. 6 (abstract numbering of the T-shaped subgraph)
    edges = [(0, 1), (1, 2), (2, 3), (3, 4), (2, 5), (5, 6)]
    parent, depth = ghz.bfs_spanning_tree(edges, root=2)
    qc = ghz.ghz_from_tree(7, parent, depth)
    assert_ghz(qc)
    assert qc.depth() == 5  # optimal for the T-shape, matching the grader


def test_dynamic_ghz_outcomes():  # Lab 2, Ex. 6
    from qiskit import transpile
    from qiskit_aer import AerSimulator

    sim = AerSimulator(seed_simulator=7)
    for n in range(2, 9):
        counts = sim.run(transpile(ghz.dynamic_ghz_circuit(n), sim), shots=500).result().get_counts()
        assert set(counts) <= {"0" * n, "1" * n}


def test_rejects_bad_sizes():
    with pytest.raises(ValueError):
        ghz.ghz_chain(1)
    with pytest.raises(ValueError):
        ghz.dynamic_ghz_circuit(1)


def test_torino_64_qubit_tree_beats_chain():  # Lab 1, Ex. 7
    fake = pytest.importorskip("qiskit_ibm_runtime.fake_provider")
    from qiskit.transpiler import generate_preset_pass_manager

    backend = fake.FakeTorino()
    tree = ghz.ghz_on_coupling_map(backend.coupling_map.get_edges(), n=64, center=25)
    chain = ghz.ghz_chain(64)
    pm = generate_preset_pass_manager(optimization_level=1, backend=backend, seed_transpiler=1)
    for qc in (tree, chain):
        qc.measure_all()
    assert pm.run(tree).depth() < pm.run(chain).depth() / 3
