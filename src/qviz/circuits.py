"""Gate-by-gate circuit model: build circuits from simple gate specs and track the state after every step."""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from qiskit import QuantumCircuit, qasm2
from qiskit.quantum_info import Statevector

__all__ = ["GateSpec", "GATES", "PRESETS", "build_circuit", "step_states", "from_qasm", "to_qasm", "specs_from_circuit"]


@dataclass(frozen=True)
class GateInfo:
    qubits: int          # number of qubits the gate acts on
    param: bool          # takes a rotation angle
    label: str
    help: str


GATES: dict[str, GateInfo] = {
    "h":    GateInfo(1, False, "H",  "Hadamard: |0⟩ → |+⟩, creates superposition"),
    "x":    GateInfo(1, False, "X",  "Pauli-X: bit flip, half-turn about the x-axis"),
    "y":    GateInfo(1, False, "Y",  "Pauli-Y: half-turn about the y-axis"),
    "z":    GateInfo(1, False, "Z",  "Pauli-Z: phase flip, half-turn about the z-axis"),
    "s":    GateInfo(1, False, "S",  "Quarter-turn about the z-axis (√Z)"),
    "sdg":  GateInfo(1, False, "S†", "Inverse of S"),
    "t":    GateInfo(1, False, "T",  "Eighth-turn about the z-axis (√S)"),
    "tdg":  GateInfo(1, False, "T†", "Inverse of T"),
    "sx":   GateInfo(1, False, "√X", "Quarter-turn about the x-axis, a native IBM gate"),
    "rx":   GateInfo(1, True,  "RX", "Rotate by θ about the x-axis"),
    "ry":   GateInfo(1, True,  "RY", "Rotate by θ about the y-axis"),
    "rz":   GateInfo(1, True,  "RZ", "Rotate by θ about the z-axis"),
    "cx":   GateInfo(2, False, "CNOT", "Flip the target when the control is |1⟩"),
    "cz":   GateInfo(2, False, "CZ", "Phase-flip |11⟩, the native two-qubit gate on IBM Heron"),
    "swap": GateInfo(2, False, "SWAP", "Exchange two qubits"),
    "ccx":  GateInfo(3, False, "Toffoli", "Flip the target when both controls are |1⟩"),
}


@dataclass(frozen=True)
class GateSpec:
    name: str
    qubits: tuple[int, ...]
    theta: float | None = None

    def __post_init__(self):
        info = GATES.get(self.name)
        if info is None:
            raise ValueError(f"Unknown gate {self.name!r}")
        if len(self.qubits) != info.qubits:
            raise ValueError(f"{info.label} acts on {info.qubits} qubit(s), got {len(self.qubits)}")
        if len(set(self.qubits)) != len(self.qubits):
            raise ValueError(f"{info.label} needs distinct qubits")
        if info.param and self.theta is None:
            raise ValueError(f"{info.label} needs an angle")

    @property
    def text(self) -> str:
        info = GATES[self.name]
        angle = f"({self.theta / np.pi:.3g}π)" if self.theta is not None else ""
        return f"{info.label}{angle} on q{', q'.join(map(str, self.qubits))}"


def _apply(qc: QuantumCircuit, g: GateSpec) -> None:
    if any(q >= qc.num_qubits for q in g.qubits):
        raise ValueError(f"{g.text} uses a qubit outside 0..{qc.num_qubits - 1}")
    method = getattr(qc, g.name)
    method(*(([g.theta] if g.theta is not None else []) + list(g.qubits)))


def build_circuit(num_qubits: int, gates: list[GateSpec], measure: bool = False) -> QuantumCircuit:
    qc = QuantumCircuit(num_qubits)
    for g in gates:
        _apply(qc, g)
    if measure:
        qc.measure_all()
    return qc


def step_states(num_qubits: int, gates: list[GateSpec]) -> list[Statevector]:
    """State before any gate, then after each gate in order (len = len(gates) + 1)."""
    sv = Statevector.from_label("0" * num_qubits)
    states = [sv]
    for g in gates:
        step = QuantumCircuit(num_qubits)
        _apply(step, g)
        sv = sv.evolve(step)
        states.append(sv)
    return states


def specs_from_circuit(qc: QuantumCircuit) -> list[GateSpec]:
    """Convert a circuit (e.g. parsed from QASM) back to gate specs; barriers/measures are skipped."""
    specs = []
    for inst in qc.data:
        name = inst.operation.name
        if name in ("barrier", "measure"):
            continue
        if name not in GATES:
            raise ValueError(f"Gate {name!r} is not supported by the visualizer")
        qubits = tuple(qc.find_bit(q).index for q in inst.qubits)
        theta = float(inst.operation.params[0]) if GATES[name].param else None
        specs.append(GateSpec(name, qubits, theta))
    return specs


def from_qasm(text: str) -> tuple[int, list[GateSpec]]:
    qc = qasm2.loads(text, custom_instructions=qasm2.LEGACY_CUSTOM_INSTRUCTIONS)
    return qc.num_qubits, specs_from_circuit(qc)


def to_qasm(num_qubits: int, gates: list[GateSpec], measure: bool = True) -> str:
    return qasm2.dumps(build_circuit(num_qubits, gates, measure=measure))


def _g(name, *qubits, theta=None):
    return GateSpec(name, tuple(qubits), theta)


PRESETS: dict[str, tuple[int, list[GateSpec], str]] = {
    "Superposition": (1, [_g("h", 0)], "One Hadamard: equal chance of 0 and 1."),
    "Phase on the equator": (1, [_g("h", 0), _g("s", 0), _g("t", 0)],
                             "H puts the qubit on the equator; S and T then turn it around the z-axis."),
    "Bell state Φ+": (2, [_g("h", 0), _g("cx", 0, 1)],
                      "Two entangled qubits: always measured equal. Each Bloch vector shrinks to the centre."),
    "Bell state Ψ−": (2, [_g("x", 1), _g("h", 0), _g("cx", 0, 1), _g("z", 0)],
                      "The singlet: always measured opposite."),
    "GHZ (3 qubits)": (3, [_g("h", 0), _g("cx", 0, 1), _g("cx", 1, 2)],
                       "Three-way entanglement: 000 or 111, nothing else."),
    "Phase kickback": (2, [_g("x", 1), _g("h", 0), _g("h", 1), _g("cx", 0, 1), _g("h", 0)],
                       "The target is an eigenstate of X, so the phase kicks back onto the control."),
    "Qiskit logo state (QGSS Lab 0)": (6, [_g("h", 0), _g("x", 1)] + [_g("cx", 0, t) for t in range(1, 6)],
                                       "From Lab 0: the state whose Q-sphere draws the Qiskit logo."),
}


def parse_sequence(text: str) -> list[tuple[str, float | None]]:
    """Parse a single-qubit gate sequence such as ``"H S T RX(pi/2) RZ(-0.5)"``.

    Gates are separated by spaces, commas or arrows; angles accept numbers and ``pi`` / ``π``.
    """
    import re

    out = []
    tokens = re.findall(r"[A-Za-z√†]+\s*(?:\([^)]*\))?", text.replace("→", " ").replace("√X", "sx"))
    for tok in tokens:
        m = re.fullmatch(r"([A-Za-z†]+)\s*(?:\(([^)]*)\))?", tok.strip())
        if not m:
            raise ValueError(f"Could not read {tok!r}")
        name = m.group(1).lower().replace("†", "dg")
        info = GATES.get(name)
        if info is None or info.qubits != 1:
            raise ValueError(f"{m.group(1)} is not a single-qubit gate")
        theta = None
        if info.param:
            if not m.group(2):
                raise ValueError(f"{m.group(1).upper()} needs an angle, e.g. {m.group(1).upper()}(pi/2)")
            expr = m.group(2).replace("π", "pi").replace(" ", "")
            if not re.fullmatch(r"[-+*/().0-9pi]+", expr):
                raise ValueError(f"Bad angle {m.group(2)!r}")
            theta = float(eval(expr, {"__builtins__": {}}, {"pi": np.pi}))
        out.append((name, theta))
    if not out:
        raise ValueError("Enter at least one gate, e.g. H S T")
    return out
