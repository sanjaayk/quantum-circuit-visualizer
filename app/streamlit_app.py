"""Quantum Circuit Visualizer by Sanjaay Kumaraguru.

Run locally:  streamlit run app/streamlit_app.py
"""
import ui  # noqa: F401  (sets up sys.path and matplotlib backend)
import streamlit as st

st.set_page_config(page_title="Quantum Circuit Visualizer", page_icon="⚛️", layout="wide")

pages = {
    "Visualizer": [
        st.Page("views/home.py", title="Home", icon=":material/blur_on:", default=True),
        st.Page("views/builder.py", title="Circuit builder", icon=":material/tune:"),
        st.Page("views/bloch_animator.py", title="Bloch sphere animator", icon=":material/360:"),
        st.Page("views/grover.py", title="Grover's search", icon=":material/search:"),
        st.Page("views/hardware.py", title="Run on IBM hardware", icon=":material/memory:"),
    ],
    "From my QGSS 2026 labs": [
        st.Page("views/lab_ghz.py", title="GHZ strategies", icon=":material/hub:"),
        st.Page("views/lab_noise.py", title="Noise lab", icon=":material/grain:"),
        st.Page("views/lab_mirror.py", title="Mirror circuits", icon=":material/flip:"),
    ],
}

with st.sidebar:
    st.caption("Built with Python, Qiskit 2 and Streamlit by Sanjaay Kumaraguru · "
               "[GitHub](https://github.com/sanjaayk)")

st.navigation(pages).run()
