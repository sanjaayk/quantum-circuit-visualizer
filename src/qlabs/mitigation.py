"""Ready-made EstimatorV2 option presets for each error-handling method (Lab 3, Ex. 1)."""
from __future__ import annotations

__all__ = ["METHODS", "estimator_options"]

METHODS = {
    "dd": "Dynamical decoupling (XY4): suppresses idle-qubit dephasing",
    "pt": "Pauli twirling: turns coherent gate errors into stochastic Pauli noise",
    "trex": "Twirled readout error extinction: mitigates measurement errors",
    "zne": "Zero-noise extrapolation with PEA amplification (noise factors 1, 3, 5)",
    "pec": "Probabilistic error cancellation: unbiased, but sampling cost grows exponentially",
}


def estimator_options(method: str):
    """Return an ``EstimatorOptions`` object configured for one method key in :data:`METHODS`."""
    from qiskit_ibm_runtime.options import EstimatorOptions

    opts = EstimatorOptions()
    m = method.lower()
    if m == "dd":
        opts.dynamical_decoupling.enable = True
        opts.dynamical_decoupling.sequence_type = "XY4"
    elif m == "pt":
        opts.twirling.enable_gates = True
        opts.twirling.strategy = "active"
        opts.twirling.num_randomizations = 32
    elif m == "trex":
        opts.resilience.measure_mitigation = True
    elif m == "zne":
        opts.resilience.zne_mitigation = True
        opts.resilience.zne.noise_factors = [1, 3, 5]
        opts.resilience.zne.amplifier = "pea"
    elif m == "pec":
        opts.resilience.pec_mitigation = True
        opts.resilience.pec.max_overhead = 100
    else:
        raise ValueError(f"Unknown method {method!r}; choose from {sorted(METHODS)}")
    return opts
