"""The four benchmark circuits from the technical brief, run as one batch.

Sending all four circuits in a single Sampler job keeps real-QPU usage to a few seconds
and gives one job ID that holds every result needed for the brief's table.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from qiskit import QuantumCircuit

from .algorithms import grover_circuit
from .circuits import PRESETS, build_circuit
from .hardware import FAKE_DEVICES, ideal_distribution, run_local, transpile_for

__all__ = ["BenchmarkCircuit", "brief_circuits", "summarize", "run_models", "submit_batch", "fetch_batch",
           "BRIEF_SHOTS", "BRIEF_SEED"]

BRIEF_SHOTS = 4096
BRIEF_SEED = 2026  # seed used for the noise-model numbers printed in the brief


@dataclass(frozen=True)
class BenchmarkCircuit:
    key: str
    label: str
    circuit: QuantumCircuit
    good: tuple[str, ...]   # outcomes theory allows (or the marked answer)
    metric: str             # "leak" -> report % outside `good`; "success" -> report % inside `good`

    def value(self, counts: dict[str, int]) -> float:
        total = sum(counts.values())
        inside = sum(counts.get(g, 0) for g in self.good) / total * 100
        return inside if self.metric == "success" else 100 - inside

    def describe(self, counts: dict[str, int]) -> str:
        v = self.value(counts)
        if self.metric == "success":
            return f"|{self.good[0]}⟩ {v:.1f}%"
        if self.key == "bell":
            return f"{v:.1f}% in |01⟩ + |10⟩"
        return f"{v:.1f}% in other states"


def brief_circuits() -> list[BenchmarkCircuit]:
    return [
        BenchmarkCircuit("bell", "Bell state (H + CNOT), 2 qubits",
                         build_circuit(2, PRESETS["Bell state Φ+"][1]), ("00", "11"), "leak"),
        BenchmarkCircuit("grover2", "Grover search for |11⟩, 2 qubits, 1 iteration",
                         grover_circuit(2, ["11"], iterations=1, measure=False, barriers=False), ("11",), "success"),
        BenchmarkCircuit("ghz3", "GHZ state, 3 qubits",
                         build_circuit(3, PRESETS["GHZ (3 qubits)"][1]), ("000", "111"), "leak"),
        BenchmarkCircuit("grover3", "Grover search for |101⟩, 3 qubits, 2 iterations",
                         grover_circuit(3, ["101"], iterations=2, measure=False, barriers=False), ("101",), "success"),
    ]


def summarize(counts_list: list[dict[str, int]], isa_list=None) -> list[dict]:
    """Table rows (one per circuit) in the same terms as the brief."""
    rows = []
    for i, (b, counts) in enumerate(zip(brief_circuits(), counts_list)):
        ideal = ideal_distribution(b.circuit)
        ideal_good = sum(ideal.get(g, 0) for g in b.good) * 100
        row = {
            "circuit": b.label,
            "ideal": f"|{b.good[0]}⟩ {ideal_good:.1f}%" if b.metric == "success" else "0% outside ideal",
            "result": b.describe(counts),
            "value_%": round(b.value(counts), 1),
            "shots": sum(counts.values()),
            "top outcomes": ", ".join(f"{k}: {v}" for k, v in sorted(counts.items(), key=lambda x: -x[1])[:5]),
        }
        if isa_list is not None:
            ops = isa_list[i].count_ops()
            row["CZ gates"] = ops.get("cz", 0) + ops.get("ecr", 0)
            row["depth on chip"] = isa_list[i].depth()
        rows.append(row)
    return rows


def run_models(devices=("ibm_fez (Heron r2, 156 q)", "ibm_torino (Heron r1, 133 q)"),
               shots: int = BRIEF_SHOTS, seed: int = BRIEF_SEED) -> dict[str, list[dict]]:
    """Reproduce the brief's noise-model columns."""
    out = {}
    for dev in devices:
        counts, isas = zip(*(run_local(b.circuit, dev, shots, seed=seed) for b in brief_circuits()))
        out[dev] = summarize(list(counts), list(isas))
    return out


def submit_batch(service, backend_name: str | None = None, shots: int = BRIEF_SHOTS):
    """Send all four circuits to a real QPU as ONE job. Returns (job_id, backend_name)."""
    import warnings

    from qiskit_ibm_runtime import SamplerV2

    warnings.filterwarnings("ignore", category=DeprecationWarning, module="qiskit_ibm_runtime")
    backend = (service.backend(backend_name) if backend_name
               else service.least_busy(operational=True, simulator=False, min_num_qubits=3))
    isas = []
    for b in brief_circuits():
        qc = b.circuit.copy()
        qc.measure_all()
        isas.append(transpile_for(qc, backend, optimization_level=1))
    job = SamplerV2(mode=backend).run(isas, shots=shots)
    try:
        job.update_tags(["qviz-brief-benchmark"])
    except Exception:
        pass
    return job.job_id(), backend.name


def fetch_batch(service, job_id: str) -> dict:
    """Status, backend, date, QPU seconds used and (when done) counts for each circuit."""
    job = service.job(job_id)
    status = job.status()
    status = getattr(status, "name", str(status))
    info = {"status": status, "backend": job.backend().name, "counts": None, "qpu_seconds": None, "date": None}
    try:
        created = job.creation_date
        info["date"] = created.strftime("%Y-%m-%d") if isinstance(created, datetime) else str(created)[:10]
    except Exception:
        pass
    if status in ("DONE", "COMPLETED"):
        result = job.result()
        counts_list = []
        for pub in result:
            reg = next(iter(pub.data.keys()))
            counts_list.append(getattr(pub.data, reg).get_counts())
        info["counts"] = counts_list
        try:
            info["qpu_seconds"] = float(job.usage())
        except Exception:
            try:
                info["qpu_seconds"] = float(job.metrics()["usage"]["quantum_seconds"])
            except Exception:
                pass
    return info
