"""Safe IBM Quantum login: the API key comes from the environment, never from code."""
from __future__ import annotations

import os

__all__ = ["get_service"]


def get_service(instance: str | None = None):
    """Return a ``QiskitRuntimeService``.

    Order of precedence:
    1. ``QISKIT_IBM_TOKEN`` (and optional ``QISKIT_IBM_INSTANCE``) environment variables,
       loaded from a local ``.env`` file if python-dotenv is installed.
    2. An account previously saved with ``QiskitRuntimeService.save_account(...)``.
    """
    from qiskit_ibm_runtime import QiskitRuntimeService

    try:
        from dotenv import load_dotenv

        load_dotenv()
    except ImportError:
        pass

    token = os.getenv("QISKIT_IBM_TOKEN")
    instance = instance or os.getenv("QISKIT_IBM_INSTANCE")
    if token:
        return QiskitRuntimeService(channel="ibm_quantum_platform", token=token, instance=instance)
    return QiskitRuntimeService(instance=instance)
