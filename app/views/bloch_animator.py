import numpy as np
import pandas as pd
import streamlit as st
from ui import plot

from qiskit.circuit.library import get_standard_gate_name_mapping
from qiskit.quantum_info import Operator
from qviz import GATES, rotation_of, single_qubit_path
from qviz.circuits import parse_sequence
from qviz.plots import bloch_animation

st.title("Bloch sphere animator")
st.markdown("Every single-qubit gate is a rotation of the Bloch sphere. Type a sequence and watch "
            "the state vector follow it, starting from |0⟩.")

EXAMPLES = {
    "Hadamard sandwich": "H Z H",
    "Clifford tour": "H S S S S",
    "T-gate staircase": "H T T T T T T T T",
    "√X twice is X": "SX SX",
    "Arbitrary rotation": "RY(pi/3) RZ(pi/2) RX(-pi/4)",
}
ss = st.session_state
ss.setdefault("anim_seq", "H S T RY(pi/3)")

c1, c2 = st.columns([3, 1])
choice = c2.selectbox("Examples", ["—"] + list(EXAMPLES))
if choice != "—" and EXAMPLES[choice] != ss.anim_seq and ss.get("_anim_choice") != choice:
    ss.anim_seq = EXAMPLES[choice]
ss._anim_choice = choice
text = c1.text_input("Gate sequence", key="anim_seq",
                     help="Single-qubit gates: H X Y Z S S† T T† SX, or RX/RY/RZ(angle) with angles like pi/2")
speed = st.select_slider("Smoothness", options=[8, 16, 24, 32], value=24,
                         help="Frames drawn per gate. More frames give a smoother animation.")

try:
    seq = parse_sequence(text)
except ValueError as e:
    st.error(f"{e}. Example: H S T RX(pi/2)")
    st.stop()

labels = [GATES[g].label + (f"({t / np.pi:.3g}π)" if t is not None else "") for g, t in seq]
pts, idx = single_qubit_path(seq, frames_per_gate=speed)

left, right = st.columns([3, 2], gap="large")
with left:
    plot(bloch_animation(pts, idx, labels, height=540))
with right:
    st.markdown("**Each gate as a rotation**")
    mapping = get_standard_gate_name_mapping()
    rows = []
    for (g, t), lab in zip(seq, labels):
        gate = type(mapping[g])(t) if t is not None else mapping[g]
        axis, angle = rotation_of(Operator(gate).data)
        axis = np.round(axis, 2) + 0.0  # avoid "-0.00"
        rows.append({"gate": lab, "axis (x, y, z)": f"({axis[0]:+.2f}, {axis[1]:+.2f}, {axis[2]:+.2f})",
                     "angle": f"{angle / np.pi:.3g}π"})
    st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")
    end = pts[-1]
    p0 = (1 + end[2]) / 2
    st.markdown(f"**Final state:** P(0) = {p0:.3f}, P(1) = {1 - p0:.3f}")
    st.caption("Measurement only sees the z-coordinate. Two states with the same height but different "
               "longitude give identical measurement statistics; the difference is their phase.")
