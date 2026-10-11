import numpy as np
import pandas as pd
import streamlit as st
from ui import plot, show_circuit

from qlabs import quantum_circuit_params
from qviz import GATES, PRESETS, GateSpec, bloch_vectors, build_circuit, from_qasm, step_states, to_qasm
from qviz.bloch import purity
from qviz.plots import amplitude_figure, bloch_figure, probability_figure

MAX_QUBITS = 6
ss = st.session_state
ss.setdefault("n", 2)
ss.setdefault("gates", list(PRESETS["Bell state Φ+"][1]))

st.title("Circuit builder")
st.caption("Add gates on the left. Drag the step slider to see the state after any gate.")

# ---------------------------------------------------------------- controls
ctrl, view = st.columns([1, 2.6], gap="large")
with ctrl:
    preset = st.selectbox("Start from an example", ["—"] + list(PRESETS), index=0)
    if preset != "—":
        st.caption(PRESETS[preset][2])
        if st.button("Load example", width="stretch"):
            ss.n, ss.gates = PRESETS[preset][0], list(PRESETS[preset][1])
            st.rerun()

    n = st.number_input("Qubits", 1, MAX_QUBITS, ss.n)
    if n != ss.n:
        dropped = [g for g in ss.gates if max(g.qubits) >= n]
        ss.gates = [g for g in ss.gates if max(g.qubits) < n]
        ss.n = n
        if dropped:
            st.toast(f"Removed {len(dropped)} gate(s) that used qubits beyond q{n - 1}.")
        st.rerun()

    st.markdown("**Add a gate**")
    available = [k for k, v in GATES.items() if v.qubits <= n]
    gname = st.selectbox("Gate", available, format_func=lambda k: f"{GATES[k].label} — {GATES[k].help}")
    info = GATES[gname]
    roles = {1: ["Qubit"], 2: ["Control", "Target"], 3: ["Control 1", "Control 2", "Target"]}[info.qubits]
    if gname in ("cz", "swap"):
        roles = ["Qubit A", "Qubit B"]
    cols = st.columns(len(roles))
    qubits = tuple(c.selectbox(r, range(n), index=min(i, n - 1), key=f"role_{r}") for i, (c, r) in enumerate(zip(cols, roles)))
    theta = None
    if info.param:
        theta = st.slider("Angle θ (multiples of π)", -2.0, 2.0, 0.5, 0.125) * np.pi
    if st.button(f"Add {info.label}", type="primary", width="stretch"):
        try:
            ss.gates = ss.gates + [GateSpec(gname, qubits, theta)]
            st.rerun()
        except ValueError as e:
            st.error(str(e))

    c1, c2 = st.columns(2)
    if c1.button("Undo last", width="stretch", disabled=not ss.gates):
        ss.gates = ss.gates[:-1]
        st.rerun()
    if c2.button("Clear all", width="stretch", disabled=not ss.gates):
        ss.gates = []
        st.rerun()

    with st.expander("Import or export OpenQASM 2"):
        st.download_button("Download .qasm", to_qasm(ss.n, ss.gates), file_name="circuit.qasm",
                           width="stretch")
        text = st.text_area("Paste OpenQASM 2.0", height=140,
                            placeholder='OPENQASM 2.0;\ninclude "qelib1.inc";\nqreg q[2];\nh q[0];\ncx q[0],q[1];')
        if st.button("Import", width="stretch", disabled=not text.strip()):
            try:
                n2, specs = from_qasm(text)
                if n2 > MAX_QUBITS:
                    raise ValueError(f"The visualizer shows up to {MAX_QUBITS} qubits; this circuit has {n2}.")
                ss.n, ss.gates = n2, specs
                st.rerun()
            except Exception as e:  # qasm parser errors are varied
                st.error(f"Could not import: {e}")

# ---------------------------------------------------------------- views
with view:
    qc = build_circuit(ss.n, ss.gates)
    show_circuit(qc)
    states = step_states(ss.n, ss.gates)

    if ss.gates:
        step = st.select_slider(
            "Show the state after", options=list(range(len(ss.gates) + 1)), value=len(ss.gates),
            format_func=lambda k: "start (|0…0⟩)" if k == 0 else f"gate {k}: {ss.gates[k - 1].text}")
    else:
        step = 0
        st.info("The circuit is empty. Add a gate or load an example to get started.")
    sv = states[step]

    tab_bloch, tab_prob, tab_amp, tab_table = st.tabs(
        ["Bloch spheres", "Probabilities", "Amplitudes & phase", "State vector"])
    with tab_bloch:
        vecs = bloch_vectors(sv)
        titles = [f"q{i}  ·  purity {purity(sv, i):.2f}" for i in range(ss.n)]
        plot(bloch_figure(vecs, titles, cols=3 if ss.n > 2 else ss.n, height=300))
        if any(np.linalg.norm(v) < 0.99 for v in vecs):
            st.caption("A vector shorter than the sphere's radius means that qubit is entangled with the others: "
                       "on its own it is no longer a pure state. Purity 0.5 is maximal entanglement for one qubit.")
    with tab_prob:
        plot(probability_figure(sv.probabilities(), ss.n))
    with tab_amp:
        plot(amplitude_figure(sv.data, ss.n))
        st.caption("Bar height is the amplitude's size; colour is its phase. Phases don't change the "
                   "probabilities, but they decide how amplitudes interfere in later gates.")
    with tab_table:
        amps = sv.data
        df = pd.DataFrame({
            "basis state": [f"|{format(i, f'0{ss.n}b')}⟩" for i in range(2 ** ss.n)],
            "amplitude": [f"{a.real:+.4f} {a.imag:+.4f}i" for a in amps],
            "probability": np.round(np.abs(amps) ** 2, 4),
            "phase (π)": np.round(np.where(np.abs(amps) > 1e-9, np.angle(amps) / np.pi, 0), 4),
        })
        st.dataframe(df, hide_index=True, width="stretch")

    p = quantum_circuit_params(qc)
    m = st.columns(4)
    m[0].metric("Gates", len(ss.gates))
    m[1].metric("Depth", p["Depth"])
    m[2].metric("2-qubit gates", p["Multi-qubit gates"])
    m[3].metric("2-qubit depth", p["2-qubit depth"])
    if ss.gates:
        st.page_link("views/hardware.py", label="Run this circuit on a noisy device or a real QPU",
                     icon=":material/memory:")
