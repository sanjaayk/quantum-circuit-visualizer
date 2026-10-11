"""Run circuits on an ideal simulator, a noisy replica of an IBM device, or a real IBM QPU."""
from __future__ import annotations

from functools import lru_cache

from qiskit import QuantumCircuit
from qiskit.quantum_info import Statevector, hellinger_fidelity
from qiskit.transpiler import generate_preset_pass_manager

__all__ = ["FAKE_DEVICES", "ideal_distribution", "local_backend", "transpile_for", "run_local",
           "submit_ibm", "fetch_ibm", "fidelity"]

# Device replicas shipped with qiskit-ibm-runtime: real calibration data, simulated locally.
FAKE_DEVICES = {
    "ibm_fez (Heron r2, 156 q)": "FakeFez",
    "ibm_marrakesh (Heron r2, 156 q)": "FakeMarrakesh",
    "ibm_kingston (Heron r2, 156 q)": "FakeKingston",
    "ibm_torino (Heron r1, 133 q)": "FakeTorino",
    "ibm_brisbane (Eagle, 127 q)": "FakeBrisbane",
}


def ideal_distribution(qc: QuantumCircuit) -> dict[str, float]:
    """Exact output probabilities (measurements removed)."""
    return Statevector(qc.remove_final_measurements(inplace=False)).probabilities_dict()


@lru_cache(maxsize=8)
def local_backend(device: str | None):
    """``None`` → noiseless AerSimulator; otherwise a noisy simulator of the named device (cached: building one takes a few seconds)."""
    from qiskit_aer import AerSimulator

    if device is None:
        return AerSimulator()
    from qiskit_ibm_runtime import fake_provider

    return AerSimulator.from_backend(getattr(fake_provider, FAKE_DEVICES[device])())


def transpile_for(qc: QuantumCircuit, backend, optimization_level: int = 1, seed: int = 7) -> QuantumCircuit:
    pm = generate_preset_pass_manager(optimization_level=optimization_level, backend=backend, seed_transpiler=seed)
    return pm.run(qc)


def _counts(result) -> dict[str, int]:
    data = result[0].data
    reg = next(iter(data.keys()))
    return getattr(data, reg).get_counts()


def run_local(qc: QuantumCircuit, device: str | None = None, shots: int = 2048,
              optimization_level: int = 1, seed: int | None = None) -> tuple[dict[str, int], QuantumCircuit]:
    """Transpile and sample locally on Aer. Returns (counts, transpiled circuit)."""
    if not qc.num_clbits:
        qc = qc.copy()
        qc.measure_all()
    backend = local_backend(device)
    isa = transpile_for(qc, backend, optimization_level)
    counts = backend.run(isa, shots=shots, seed_simulator=seed).result().get_counts()
    return {k.replace(" ", ""): v for k, v in counts.items()}, isa


def submit_ibm(qc: QuantumCircuit, service, backend_name: str | None = None, shots: int = 2048,
               optimization_level: int = 1):
    """Send a circuit to a real IBM QPU. Returns (job_id, backend_name, transpiled circuit)."""
    import warnings

    from qiskit_ibm_runtime import SamplerV2

    warnings.filterwarnings("ignore", category=DeprecationWarning, module="qiskit_ibm_runtime")

    if not qc.num_clbits:
        qc = qc.copy()
        qc.measure_all()
    backend = (service.backend(backend_name) if backend_name
               else service.least_busy(operational=True, simulator=False, min_num_qubits=qc.num_qubits))
    isa = transpile_for(qc, backend, optimization_level)
    job = SamplerV2(mode=backend).run([isa], shots=shots)
    return job.job_id(), backend.name, isa


def fetch_ibm(service, job_id: str) -> tuple[str, dict[str, int] | None]:
    """(status, counts or None) for a previously submitted job."""
    job = service.job(job_id)
    status = job.status()
    status = getattr(status, "name", str(status))
    if status in ("DONE", "COMPLETED"):
        return status, _counts(job.result())
    return status, None


def fidelity(counts: dict[str, int], ideal: dict[str, float]) -> float:
    """Hellinger fidelity between measured counts and the ideal distribution (1.0 = perfect)."""
    total = sum(counts.values())
    return float(hellinger_fidelity({k: v / total for k, v in counts.items()}, ideal))
