import math

import streamlit as st
from ui import plot, show_circuit

from qiskit.quantum_info import Statevector
from qviz import grover_circuit, optimal_iterations, success_curve
from qviz.plots import grover_figure, probability_figure

st.title("Grover's search")
st.markdown(
    "Grover's algorithm finds a marked item among N = 2ⁿ possibilities in about √N steps instead of N. "
    "Each iteration does two reflections: the **oracle** flips the sign of the marked state, then the "
    "**diffuser** reflects every amplitude about the mean. Together they push probability toward the answer."
)

c1, c2, c3 = st.columns([1, 2, 2])
n = c1.number_input("Qubits", 2, 6, 3)
all_states = [format(i, f"0{n}b") for i in range(2 ** n)]
default = [all_states[-3]] if len(all_states) > 3 else [all_states[-1]]
marked = c2.multiselect("Marked state(s)", all_states, default=default)
if not marked:
    st.info("Pick at least one state for the oracle to mark.")
    st.stop()
best = optimal_iterations(n, len(marked))
k = c3.slider("Grover iterations", 0, max(2 * best + 2, 4), best,
              help=f"The best choice is ⌊π/4·√(N/M)⌋ = {best} for N = {2 ** n}, M = {len(marked)}.")

qc = grover_circuit(n, marked, iterations=k, measure=False)
probs = Statevector(qc).probabilities()
p_success = sum(probs[int(m, 2)] for m in marked)

m = st.columns(4)
m[0].metric("Search space", f"{2 ** n} states")
m[1].metric("Iterations", k, delta=None if k == best else f"{k - best:+d} vs best", delta_color="off")
m[2].metric("P(finding a marked state)", f"{p_success:.1%}")
m[3].metric("Random guessing", f"{len(marked) / 2 ** n:.1%}")

left, right = st.columns(2, gap="large")
with left:
    st.markdown("**Output probabilities** (marked states in amber)")
    plot(probability_figure(probs, n, highlight=marked))
with right:
    st.markdown("**Success probability vs. iterations**")
    plot(grover_figure(success_curve(n, marked, max(2 * best + 2, 4)), chosen=k))
    st.caption("Too many iterations rotate the state past the answer, so success rises and falls like a sine wave. "
               f"Each iteration rotates by 2·asin(√(M/N)) = {2 * math.degrees(math.asin(math.sqrt(len(marked) / 2 ** n))):.1f}°.")

with st.expander("Show the circuit", expanded=n <= 3):
    show_circuit(grover_circuit(n, marked, iterations=min(k, 2), measure=True), fold=40, scale=0.65)
    if k > 2:
        st.caption(f"Showing the first 2 of {k} iterations.")

st.session_state["grover_for_hw"] = (n, tuple(marked), k)
st.page_link("views/hardware.py", label="Run this search on a noisy IBM device or a real QPU",
             icon=":material/memory:")
