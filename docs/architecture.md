# Architecture

```
 Streamlit pages (app/views/*.py)          what you see and click
            │
            ▼
 qviz  ── circuits ── bloch ── algorithms ── hardware ── plots
            │                                   │
            ▼                                   ▼
        Qiskit (Statevector, transpiler)    Qiskit Aer · qiskit-ibm-runtime
```

- **`qviz.circuits`:** A circuit is a list of `GateSpec(name, qubits, theta)`. `step_states` evolves |0…0⟩ one gate at a time, which is what powers the builder's step slider. Specs convert to and from Qiskit circuits and OpenQASM 2.
- **`qviz.bloch`:** `bloch_vectors` takes the partial trace down to each qubit and reads ⟨X⟩, ⟨Y⟩, ⟨Z⟩. `rotation_of` turns any 2×2 unitary into a rotation axis and angle (U = e^{iφ}·exp(−iθ/2·n·σ)), always taking the shorter way round. `gate_trajectory` interpolates that rotation with Rodrigues' formula for animation.
- **`qviz.algorithms`:** Grover's oracle is built from X gates and a multi-controlled Z. The diffuser is H·X·MCZ·X·H. `success_curve` evolves the statevector one iteration at a time.
- **`qviz.hardware`:** Noisy replicas use `AerSimulator.from_backend` with the calibration data shipped in `qiskit_ibm_runtime.fake_provider`. Building one takes a few seconds, so it is cached. Real-QPU jobs use the Runtime `SamplerV2` and are fetched later by job ID, because queues can take minutes.
- **`qviz.plots`:** These are pure Plotly figures with no Streamlit inside, so they also work in Jupyter.

## Why Qiskit is pinned below 2.5

With Qiskit 2.5.0, 2.5.1 and 2.5.2, a Streamlit app crashes with a segmentation fault the second time any page reruns, for example after moving a slider. The smallest reproduction is:

```python
import streamlit as st
from qiskit import QuantumCircuit
st.write(QuantumCircuit(3).num_qubits)
```

It crashes on the second run under Python 3.12 and 3.13, inside `QuantumCircuit.__init__` (Qiskit's Rust `CircuitData`). Qiskit 2.1.2, 2.2.3, 2.4.0 and 2.4.2 all work, so `requirements.txt` pins `qiskit>=2.1,<2.5`. Re-test before raising the pin.

## Security of IBM Quantum keys

- A key typed into the app is stored only in that visitor's `st.session_state`. It is never written to the environment, disk or logs, so other visitors of a public deployment cannot use it.
- `.env`, `.streamlit/secrets.toml` and `qiskit-ibm.json` are git-ignored, and CI fails if a hard-coded token appears in any `.py` or `.ipynb` file.
- If you set `QISKIT_IBM_TOKEN` as a secret on a **public** deployment, every visitor spends *your* QPU minutes (the free plan has 10 minutes a month). Leave it unset publicly and let visitors paste their own key.

## Deploying to Streamlit Community Cloud

1. Push this repo to GitHub.
2. On [share.streamlit.io](https://share.streamlit.io), open the existing *quantum-visualizer* app → **Settings**, point it at this repository, and set the main file to `app/streamlit_app.py`. Or create a new app with the same settings.
3. Under **Advanced settings**, choose Python 3.12.
4. Deploy. The first load takes about a minute while Qiskit installs.
