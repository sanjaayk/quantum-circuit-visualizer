import numpy as np
import streamlit as st
from ui import plot

from qviz import single_qubit_path
from qviz.plots import bloch_animation

st.title("Quantum Circuit Visualizer")
st.markdown(
    "#### See what a quantum circuit does to its qubits, one gate at a time, "
    "then run it on a real IBM quantum computer."
)

left, right = st.columns([3, 2], gap="large")
with left:
    seq = [("h", None), ("s", None), ("t", None), ("ry", np.pi / 3)]
    pts, idx = single_qubit_path(seq, frames_per_gate=24)
    plot(bloch_animation(pts, idx, ["H", "S", "T", "RY(π/3)"], height=470))
    st.caption("Press ▶ Play. One qubit starts at |0⟩: H tips it onto the equator, S and T turn it "
               "around the z-axis, and RY lifts it back toward |0⟩. The orange line is the path it took.")

with right:
    st.markdown("##### What you can do here")
    links = [
        ("views/builder.py", "Build a circuit", ":material/tune:",
         "Add gates one at a time and step through the state after each: Bloch spheres, probabilities, amplitudes and phases."),
        ("views/bloch_animator.py", "Animate a qubit", ":material/360:",
         "Type a gate sequence and watch the path it traces on the Bloch sphere."),
        ("views/grover.py", "Search with Grover's algorithm", ":material/search:",
         "See why the best number of iterations is about π/4·√N, and what happens if you overshoot."),
        ("views/hardware.py", "Run on IBM hardware", ":material/memory:",
         "Compare ideal results with a noisy replica of an IBM Heron chip, or send the job to a real QPU."),
        ("views/lab_ghz.py", "Explore my QGSS 2026 labs", ":material/hub:",
         "GHZ circuits on real chip layouts, noise experiments and mirror circuits."),
    ]
    for page, label, icon, desc in links:
        st.page_link(page, label=f"**{label}**", icon=icon)
        st.caption(desc)

st.divider()
a, b, c = st.columns(3, gap="large")
a.markdown("**Simulated exactly.** Small circuits use Qiskit's statevector, so every amplitude and phase "
           "you see is exact, not sampled.")
b.markdown("**Grounded in real devices.** Noisy runs use calibration data from IBM's 156-qubit Heron "
           "processors, the same chips I used during the Qiskit Global Summer School.")
c.markdown("**Your key stays yours.** To use a real QPU, paste your own IBM Quantum API key. It is kept in "
           "this browser session only and never saved.")
