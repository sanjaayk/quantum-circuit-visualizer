import streamlit as st
from ui import ibm_service, plot, show_circuit

from qlabs import count_swap_gates, quantum_circuit_params
from qviz import PRESETS, build_circuit, grover_circuit
from qviz.hardware import FAKE_DEVICES, fetch_ibm, fidelity, ideal_distribution, run_local, submit_ibm
from qviz.plots import counts_vs_ideal_figure

ss = st.session_state
st.title("Run on IBM hardware")
st.markdown("A perfect simulator and a real quantum chip give different answers. This page shows how "
            "different, and why: the circuit is rewritten into the chip's native gates and fitted to its wiring, "
            "and every extra gate adds noise.")

# ------------------------------------------------------------ choose circuit
sources = []
if ss.get("gates"):
    sources.append("My circuit from the builder")
if ss.get("grover_for_hw"):
    sources.append("My Grover search")
sources += list(PRESETS)
src = st.selectbox("Circuit", sources, index=0 if len(sources) > len(PRESETS) else sources.index("GHZ (3 qubits)"))
if src == "My circuit from the builder":
    qc = build_circuit(ss.n, ss.gates)
elif src == "My Grover search":
    n, marked, k = ss.grover_for_hw
    qc = grover_circuit(n, list(marked), iterations=k, measure=False, barriers=False)
else:
    qc = build_circuit(PRESETS[src][0], PRESETS[src][1])

target = st.radio("Where to run", ["Ideal simulator", "Noisy replica of an IBM device", "Real IBM quantum computer"],
                  horizontal=True)
c1, c2, c3 = st.columns(3)
device = c1.selectbox("Device", list(FAKE_DEVICES), disabled=target != "Noisy replica of an IBM device")
shots = c2.select_slider("Shots", [256, 512, 1024, 2048, 4096, 8192], value=2048)
opt = c3.select_slider("Transpiler optimization", [0, 1, 2, 3], value=1,
                       help="Higher levels search harder for a shorter circuit on the chip's layout.")

ideal = ideal_distribution(qc)


def show_results(counts, isa, label):
    p = quantum_circuit_params(isa)
    m = st.columns(4)
    m[0].metric("Fidelity vs. ideal", f"{fidelity(counts, ideal):.3f}",
                help="Hellinger fidelity: 1.000 means the measured distribution matches the ideal one exactly.")
    m[1].metric("Depth on chip", p["Depth"], delta=f"{p['Depth'] - qc.depth():+d} vs. your circuit", delta_color="inverse")
    m[2].metric("2-qubit gates", p["Multi-qubit gates"])
    m[3].metric("SWAPs inserted", count_swap_gates(isa))
    plot(counts_vs_ideal_figure(counts, ideal))
    with st.expander(f"Circuit as it ran on {label}"):
        show_circuit(isa.remove_final_measurements(inplace=False), fold=40, scale=0.6, idle_wires=False)
        st.caption("Gates are rewritten into the native set (RZ, SX, X, CZ on Heron). "
                   "Idle qubits are hidden when the chip has many.")


# ------------------------------------------------------------ local runs
if target != "Real IBM quantum computer":
    label = "the ideal simulator" if target == "Ideal simulator" else device
    if st.button(f"Run {shots} shots", type="primary"):
        with st.spinner(f"Transpiling and simulating on {label}…"):
            ss.hw_result = (*run_local(qc, None if target == "Ideal simulator" else device, shots, opt), label, src)
    if ss.get("hw_result") and ss.hw_result[3] == src:
        counts, isa, label, _ = ss.hw_result
        show_results(counts, isa, label)

# ------------------------------------------------------------ real QPU
else:
    service = None
    try:
        service = ibm_service()
    except Exception as e:
        st.error(f"IBM Quantum rejected the key: {e}")
    if service is None:
        st.markdown("To use a real QPU you need a free IBM Quantum account. Create an API key at "
                    "[quantum.cloud.ibm.com](https://quantum.cloud.ibm.com) and paste it below. "
                    "It is kept only in this browser session.")
        key = st.text_input("IBM Quantum API key", type="password")
        if st.button("Connect", disabled=not key):
            ss.ibm_token = key.strip()
            st.rerun()
        st.stop()

    st.success("Connected to IBM Quantum.")
    if st.button("Forget my key"):
        for k in [k for k in ss if k.startswith("_ibm_service_") or k == "ibm_token"]:
            del ss[k]
        st.rerun()

    # ---------------- brief benchmark: four circuits in one job ----------------
    import json

    import pandas as pd
    from qviz.benchmark import BRIEF_SHOTS, brief_circuits, fetch_batch, submit_batch, summarize

    st.subheader("Technical-brief benchmark")
    st.markdown("Sends the four circuits from the brief (Bell state, 2-qubit Grover, 3-qubit GHZ, 3-qubit Grover) "
                f"to one QPU as a **single job** with {BRIEF_SHOTS:,} shots each. It usually uses well under a minute "
                "of QPU time; time spent waiting in the queue is free.")
    if "ibm_backends" not in ss:
        try:
            ss.ibm_backends = sorted(b.name for b in service.backends(simulator=False, operational=True))
        except Exception as e:
            ss.ibm_backends = []
            st.warning(f"Could not list your QPUs ({e}). The least busy one will be used.")
    names = ss.ibm_backends or ["(least busy)"]
    default = names.index("ibm_fez") if "ibm_fez" in names else 0
    bcol, scol = st.columns([2, 1])
    chosen = bcol.selectbox("QPU", names, index=default,
                            help="ibm_fez matches the first noise-model column in the brief.")
    if scol.button("Submit benchmark job", type="primary", width="stretch"):
        with st.spinner("Compiling four circuits for the chip and submitting…"):
            try:
                job_id, used = submit_batch(service, None if chosen == "(least busy)" else chosen)
                ss.bench_job = job_id
                ss.bench_job_box = job_id
                st.success(f"Submitted to {used}. Job ID: {job_id}. Save this ID somewhere safe.")
            except Exception as e:
                st.error(f"Submission failed: {e}")

    st.markdown("**Get results.** Paste a job ID (the one above is filled in for you) and check its status. "
                "You can close the app and come back later with the same ID.")
    jcol, gcol = st.columns([2, 1])
    job_box = jcol.text_input("Job ID", key="bench_job_box", label_visibility="collapsed",
                              placeholder="Job ID, e.g. d3abc123…")
    if gcol.button("Check status / get results", width="stretch", disabled=not job_box.strip()):
        with st.spinner("Asking IBM Quantum…"):
            try:
                ss.bench_info = (job_box.strip(), fetch_batch(service, job_box.strip()))
            except Exception as e:
                st.error(f"Could not fetch the job: {e}")

    if ss.get("bench_info"):
        jid, info = ss.bench_info
        if not info["counts"]:
            st.info(f"Status: **{info['status']}** on {info['backend']}. "
                    "QUEUED or RUNNING means it is still waiting; check again in a few minutes.")
        else:
            rows = summarize(info["counts"])
            m = st.columns(3)
            m[0].metric("Backend", info["backend"])
            m[1].metric("Date", info["date"] or "—")
            m[2].metric("QPU time used", f"{info['qpu_seconds']:.1f} s" if info["qpu_seconds"] else "—")
            df = pd.DataFrame(rows)[["circuit", "ideal", "result", "top outcomes"]]
            df.columns = ["Circuit", "Ideal", f"Real hardware ({info['backend']}, {info['date']})", "Top outcomes (counts)"]
            st.dataframe(df, hide_index=True, width="stretch")
            st.markdown("**Ready to paste into the brief's table:**")
            st.code("\n".join(f"{r['circuit']}: {r['result']}" for r in rows) +
                    f"\nBackend: {info['backend']}, {info['date']}, {rows[0]['shots']:,} shots per circuit, job {jid}",
                    language=None)
            export = {"job_id": jid, "backend": info["backend"], "date": info["date"],
                      "qpu_seconds": info["qpu_seconds"],
                      "circuits": [{**r, "counts": c} for r, c in zip(rows, info["counts"])]}
            st.download_button("Download results (JSON)", json.dumps(export, indent=2),
                               file_name=f"brief_benchmark_{info['backend']}_{info['date']}.json")
            for b, counts in zip(brief_circuits(), info["counts"]):
                with st.expander(b.label):
                    plot(counts_vs_ideal_figure(counts, ideal_distribution(b.circuit)))

    st.divider()
    st.subheader("Run one circuit")

    if st.button(f"Submit {shots} shots to the least busy QPU", type="primary"):
        with st.spinner("Transpiling and submitting…"):
            try:
                job_id, backend_name, isa = submit_ibm(qc, service, shots=shots, optimization_level=opt)
                ss.ibm_job = (job_id, backend_name, isa, src)
            except Exception as e:
                st.error(f"Submission failed: {e}")

    if ss.get("ibm_job"):
        job_id, backend_name, isa, job_src = ss.ibm_job
        st.markdown(f"Job `{job_id}` on **{backend_name}** (circuit: {job_src}). Jobs wait in a queue; "
                    "check back in a few minutes.")
        if st.button("Check job status"):
            try:
                status, counts = fetch_ibm(service, job_id)
                st.write(f"Status: **{status}**")
                if counts:
                    ss.ibm_counts = (job_id, counts)
            except Exception as e:
                st.error(f"Could not fetch the job: {e}")
        if ss.get("ibm_counts") and ss.ibm_counts[0] == job_id and job_src == src:
            show_results(ss.ibm_counts[1], isa, backend_name)
