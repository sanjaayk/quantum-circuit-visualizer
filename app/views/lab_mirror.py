import numpy as np
import pandas as pd
import streamlit as st
from ui import show_circuit

from qiskit import transpile
from qlabs import construct_ising_circuit, mirror_circuit

st.title("Mirror Circuits")
st.caption("From my Qiskit Global Summer School 2026 coursework. The full notebooks are in "
           "[qgss-2026-quantum-labs](https://github.com/sanjaayk/qgss-2026-quantum-labs).")
st.markdown(
    "Lab 3 benchmarks noise with **mirror circuits**: run a Trotterized Ising evolution U, then U†. "
    "A perfect computer always returns |0…0⟩, so every other outcome is caused by noise. "
    "Here the noise is simulated with a depolarizing model on the two-qubit CZ gates."
)

c1, c2, c3, c4 = st.columns(4)
nq = c1.slider("Qubits", 2, 10, 6)
steps = c2.slider("Trotter steps", 1, 6, 2)
angle = c3.select_slider("RX angle", options=["π/16", "π/8", "π/4", "π/2"], value="π/8")
p2q = c4.select_slider("CZ error", options=[0.0, 0.005, 0.01, 0.02, 0.05], value=0.01)
theta = np.pi / {"π/16": 16, "π/8": 8, "π/4": 4, "π/2": 2}[angle]

ising = construct_ising_circuit(nq, steps, theta, barrier=False)
mirror = mirror_circuit(ising)

with st.expander("Forward circuit U", expanded=True):
    show_circuit(ising)

from qiskit_aer import AerSimulator
from qiskit_aer.noise import NoiseModel, depolarizing_error

noise = NoiseModel()
if p2q > 0:
    noise.add_all_qubit_quantum_error(depolarizing_error(p2q, 2), ["cz"])
sim = AerSimulator(noise_model=noise, seed_simulator=7)
tqc = transpile(mirror, sim, optimization_level=0)
counts = sim.run(tqc, shots=4000).result().get_counts()
p_return = counts.get("0" * nq, 0) / 4000

m = st.columns(3)
m[0].metric("Return probability", f"{p_return:.3f}")
m[1].metric("CZ gates in mirror", tqc.count_ops().get("cz", 0))
m[2].metric("Depth", tqc.depth())

top = pd.Series(counts).sort_values(ascending=False).head(12)
st.bar_chart(top.rename("counts"))
st.caption("On real hardware Lab 3 goes further: NoiseLearnerV3 learns the noise of each boxed layer, "
           "and PEC/PNA use that model to cancel it.")
