"""Run the technical-brief benchmark on a real IBM QPU from the terminal.

Usage (from the project folder, with the environment activated):
    python scripts/run_brief_benchmark.py submit --backend ibm_fez
    python scripts/run_brief_benchmark.py results <JOB_ID>
    python scripts/run_brief_benchmark.py models          # noise-model columns only, no QPU time

The API key is read from QISKIT_IBM_TOKEN (environment or .env) or asked for without echoing.
"""
import argparse
import getpass
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from qviz.benchmark import fetch_batch, run_models, submit_batch, summarize  # noqa: E402


def service():
    from qiskit_ibm_runtime import QiskitRuntimeService

    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass
    token = os.getenv("QISKIT_IBM_TOKEN") or getpass.getpass("IBM Quantum API key (hidden): ").strip()
    return QiskitRuntimeService(channel="ibm_quantum_platform", token=token)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("submit")
    s.add_argument("--backend", default=None, help="e.g. ibm_fez; default: least busy QPU")
    r = sub.add_parser("results")
    r.add_argument("job_id")
    sub.add_parser("models")
    args = ap.parse_args()

    if args.cmd == "models":
        for dev, rows in run_models().items():
            print(f"\n{dev}")
            for row in rows:
                print(f"  {row['circuit']}: {row['result']}  ({row['CZ gates']} CZ, depth {row['depth on chip']})")
        return

    svc = service()
    if args.cmd == "submit":
        job_id, name = submit_batch(svc, args.backend)
        print(f"Submitted to {name}.\nJOB ID: {job_id}\nSave this ID. Check later with:\n"
              f"  python scripts/run_brief_benchmark.py results {job_id}")
        return

    info = fetch_batch(svc, args.job_id)
    print(f"Status: {info['status']}  Backend: {info['backend']}  Date: {info['date']}")
    if not info["counts"]:
        print("Not finished yet. Try again in a few minutes.")
        return
    rows = summarize(info["counts"])
    print(f"QPU time used: {info['qpu_seconds']} s\n")
    for row in rows:
        print(f"{row['circuit']}: {row['result']}\n    top outcomes: {row['top outcomes']}")
    out = Path(f"brief_benchmark_{info['backend']}_{info['date']}.json")
    out.write_text(json.dumps({"job_id": args.job_id, **{k: v for k, v in info.items() if k != "counts"},
                               "circuits": [{**r, "counts": c} for r, c in zip(rows, info["counts"])]}, indent=2))
    print(f"\nSaved full results to {out}")


if __name__ == "__main__":
    main()
