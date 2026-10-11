import numpy as np
import pandas as pd
import streamlit as st
from ui import fake_device, show_circuit

from qiskit.quantum_info import Statevector
from qlabs import (
    dynamic_ghz_circuit,
    ghz_center_out_line,
    ghz_chain,
    ghz_log_depth,
    ghz_on_coupling_map,
    quantum_circuit_params,
)

st.title("GHZ Strategies")
st.caption("From my Qiskit Global Summer School 2026 coursework. The full notebooks are in "
           "[qgss-2026-quantum-labs](https://github.com/sanjaayk/qgss-2026-quantum-labs).")
st.markdown(
    "Every circuit here prepares the same state, (|00…0⟩ + |11…1⟩)/√2. "
    "They differ in **how entanglement spreads**, and that decides circuit depth, "
    "which in turn decides how much noise the circuit picks up on real hardware."
)

STRATEGIES = {
    "Linear chain (naive)": ghz_chain,
    "Log-depth doubling (Lab 1 Ex 3)": ghz_log_depth,
    "Centre-out line (Lab 1 Ex 5)": ghz_center_out_line,
    "Dynamic, mid-circuit measurement (Lab 2 Ex 6)": dynamic_ghz_circuit,
}

c1, c2 = st.columns([2, 1])
strategy = c1.selectbox("Strategy", list(STRATEGIES))
n = c2.slider("Qubits", 2, 12, 6)

qc = STRATEGIES[strategy](n)
show_circuit(qc)

params = quantum_circuit_params(qc)
m = st.columns(4)
m[0].metric("Depth", params["Depth"])
m[1].metric("2-qubit depth", params["2-qubit depth"])
m[2].metric("2-qubit gates", params["Multi-qubit gates"])
m[3].metric("Gates", sum(params["Gates"].values()))

if "Dynamic" not in strategy:
    probs = np.abs(Statevector(qc).data) ** 2
    labels = [format(i, f"0{n}b") for i in range(2**n)]
    nonzero = pd.DataFrame({"basis state": labels, "probability": probs}).query("probability > 1e-9")
    st.subheader("Ideal measurement probabilities")
    st.bar_chart(nonzero, x="basis state", y="probability")
else:
    st.info("Dynamic circuits contain mid-circuit measurements, so they are checked by sampling rather than with a statevector.")
    from qiskit import transpile
    from qiskit_aer import AerSimulator

    sim = AerSimulator()
    counts = sim.run(transpile(qc, sim), shots=2000).result().get_counts()
    st.bar_chart(pd.Series(counts, name="counts"))

st.divider()
st.subheader("On real hardware layout: 64-qubit GHZ on a Heron device (Lab 1 Ex 7)")
backend = fake_device("FakeTorino")
if backend is None:
    st.warning("Install `qiskit-ibm-runtime` to enable this section.")
else:
    center = st.number_input("Root qubit for the BFS spanning tree", 0, 63, 25)
    if st.button("Transpile chain vs. spanning tree"):
        from qiskit.transpiler import generate_preset_pass_manager

        with st.spinner("Transpiling for FakeTorino…"):
            pm = generate_preset_pass_manager(optimization_level=1, backend=backend, seed_transpiler=1)
            rows = []
            for name, circ in {
                "Naive chain": ghz_chain(64),
                f"BFS tree from q{center}": ghz_on_coupling_map(backend.coupling_map.get_edges(), 64, int(center)),
            }.items():
                circ.measure_all()
                isa = pm.run(circ)
                rows.append({"circuit": name, "transpiled depth": isa.depth(), "CZ gates": isa.count_ops().get("cz", 0)})
        st.table(pd.DataFrame(rows))
        st.caption("Sanjaay's lab result with root q25: depth 256 → 47 with the same 63 CZ gates.")
