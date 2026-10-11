"""Shared helpers for every page of the app."""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

CHART_CONFIG = {"displaylogo": False, "modeBarButtonsToRemove": ["toImage", "lasso2d", "select2d"]}


def show_circuit(qc, fold: int = 28, scale: float = 0.8, idle_wires: bool = True):
    """Draw a circuit in IBM Quantum style; fall back to text if matplotlib drawing fails."""
    try:
        fig = qc.draw("mpl", fold=fold, style="iqp", scale=scale, idle_wires=idle_wires)
        st.pyplot(fig, clear_figure=True, width="content")
        plt.close(fig)
    except Exception:
        st.code(str(qc.draw("text", fold=110, idle_wires=idle_wires)), language=None)


def plot(fig):
    st.plotly_chart(fig, width="stretch", config=CHART_CONFIG)


@st.cache_resource(show_spinner=False)
def fake_device(cls_name: str):
    from qiskit_ibm_runtime import fake_provider

    return getattr(fake_provider, cls_name)()


def ibm_service():
    """IBM Quantum service from Streamlit secrets, the environment, or a key typed into this session.

    Returns None when no key is available. A typed key is kept only in this browser session's state
    and is never written to the environment, so other visitors of a deployed app cannot use it.
    """
    import os

    from qiskit_ibm_runtime import QiskitRuntimeService

    token = st.session_state.get("ibm_token")
    if not token:
        try:
            token = st.secrets.get("QISKIT_IBM_TOKEN")
        except Exception:
            token = None
    token = token or os.getenv("QISKIT_IBM_TOKEN")
    if not token:
        return None
    key = f"_ibm_service_{hash(token)}"
    if key not in st.session_state:
        st.session_state[key] = QiskitRuntimeService(channel="ibm_quantum_platform", token=token)
    return st.session_state[key]
