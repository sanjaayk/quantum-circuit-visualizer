import pandas as pd
import streamlit as st
from ui import show_circuit

from qlabs import PAULI_VISIBILITY, repeated_x_circuit, repeated_x_meas_x_circuit, survival_curve

st.title("Noise Lab")
st.caption("From my Qiskit Global Summer School 2026 coursework. The full notebooks are in "
           "[qgss-2026-quantum-labs](https://github.com/sanjaayk/qgss-2026-quantum-labs).")
st.markdown(
    "Applying **X** an even number of times should leave the qubit unchanged. "
    "On a noisy device, each X adds a little error, and the chance of reading **0** decays "
    "toward 50%. The decay rate shows how strong the gate noise is (Lab 2, Ex 2–4)."
)

c1, c2, c3 = st.columns(3)
lams = c1.multiselect("Depolarizing strength λ", [0.0, 0.01, 0.02, 0.04, 0.08], default=[0.0, 0.02, 0.04])
n_max = c2.slider("Max n (2n X gates)", 5, 50, 30)
basis = c3.radio("Experiment", ["Z (bit-flip probe)", "X (phase-flip probe)"])
b = basis[0]

show_circuit((repeated_x_circuit if b == "Z" else repeated_x_meas_x_circuit)(3))
st.caption("Example with n = 3")

if lams:
    n_values = list(range(0, n_max + 1))
    with st.spinner("Simulating…"):
        data = {f"λ={lam}": survival_curve(lam, n_values, shots=4000, basis=b, seed=42) for lam in lams}
    df = pd.DataFrame(data, index=pd.Index(n_values, name="n"))
    st.line_chart(df, y_label="Pr(0)", x_label="n")

st.subheader("Which Pauli errors can each experiment see?")
st.table(pd.DataFrame(PAULI_VISIBILITY).T.replace({True: "✅ visible", False: "— invisible"}))
st.caption("Z errors leave |0⟩ unchanged but flip |+⟩ to |−⟩, so they only show up in the X-basis experiment.")
