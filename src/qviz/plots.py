"""Plotly figures: Bloch spheres (static and animated), probabilities, amplitudes with phase, Grover curve."""
from __future__ import annotations

import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

__all__ = ["PALETTE", "bloch_figure", "bloch_animation", "probability_figure", "amplitude_figure",
           "grover_figure", "counts_vs_ideal_figure"]

PALETTE = {
    "ink": "#1B1F3B",
    "violet": "#6929C4",   # state vector / primary
    "teal": "#0F9D8A",     # ideal / reference
    "amber": "#E8A33D",    # hardware / measured
    "grid": "#C9CEDD",
    "paper": "#FFFFFF",
}
FONT = dict(family="IBM Plex Sans, Helvetica, Arial, sans-serif", color=PALETTE["ink"], size=13)


def _sphere_traces():
    u, v = np.mgrid[0:2 * np.pi:40j, 0:np.pi:20j]
    surf = go.Surface(x=np.cos(u) * np.sin(v), y=np.sin(u) * np.sin(v), z=np.cos(v),
                      opacity=0.08, showscale=False, hoverinfo="skip",
                      colorscale=[[0, PALETTE["violet"]], [1, PALETTE["violet"]]])
    t = np.linspace(0, 2 * np.pi, 120)
    rings = [
        (np.cos(t), np.sin(t), 0 * t),   # equator
        (np.cos(t), 0 * t, np.sin(t)),   # x-z meridian
        (0 * t, np.cos(t), np.sin(t)),   # y-z meridian
    ]
    lines = [go.Scatter3d(x=x, y=y, z=z, mode="lines", hoverinfo="skip", showlegend=False,
                          line=dict(color=PALETTE["grid"], width=2)) for x, y, z in rings]
    axes = go.Scatter3d(
        x=[0, 0, 1.18, -1.18, 0, 0], y=[0, 0, 0, 0, 1.18, -1.18], z=[1.18, -1.18, 0, 0, 0, 0],
        mode="text", text=["|0⟩", "|1⟩", "|+⟩", "|−⟩", "|+i⟩", "|−i⟩"], hoverinfo="skip", showlegend=False,
        textfont=dict(size=13, color=PALETTE["ink"]))
    return [surf, *lines, axes]


def _vector_traces(vec, color=PALETTE["violet"], name="state"):
    x, y, z = (float(c) for c in vec)
    r = np.sqrt(x * x + y * y + z * z)
    hover = f"x={x:+.3f}<br>y={y:+.3f}<br>z={z:+.3f}<br>length={r:.3f}"
    shaft = go.Scatter3d(x=[0, x], y=[0, y], z=[0, z], mode="lines", line=dict(color=color, width=7),
                         hovertext=hover, hoverinfo="text", showlegend=False, name=name)
    tip = go.Scatter3d(x=[x], y=[y], z=[z], mode="markers", marker=dict(size=6, color=color),
                       hovertext=hover, hoverinfo="text", showlegend=False)
    return [shaft, tip]


_SCENE = dict(xaxis=dict(visible=False, range=[-1.25, 1.25]), yaxis=dict(visible=False, range=[-1.25, 1.25]),
              zaxis=dict(visible=False, range=[-1.25, 1.25]), aspectmode="cube",
              camera=dict(eye=dict(x=1.35, y=0.9, z=0.65)))


def bloch_figure(vectors, titles=None, cols: int = 3, height: int = 330) -> go.Figure:
    """One Bloch sphere per qubit."""
    n = len(vectors)
    cols = min(cols, n)
    rows = int(np.ceil(n / cols))
    titles = titles or [f"q{i}" for i in range(n)]
    fig = make_subplots(rows=rows, cols=cols, specs=[[{"type": "scene"}] * cols] * rows,
                        subplot_titles=titles, horizontal_spacing=0.02, vertical_spacing=0.06)
    for i, vec in enumerate(vectors):
        r, c = divmod(i, cols)
        for tr in _sphere_traces() + _vector_traces(vec):
            fig.add_trace(tr, row=r + 1, col=c + 1)
    for i in range(1, rows * cols + 1):
        fig.update_layout(**{f"scene{'' if i == 1 else i}": _SCENE})
    fig.update_layout(height=height * rows, margin=dict(l=0, r=0, t=30, b=0), font=FONT,
                      paper_bgcolor=PALETTE["paper"])
    return fig


def bloch_animation(points, gate_index, gate_labels, height: int = 520) -> go.Figure:
    """Animated single-qubit Bloch sphere with a trail showing the path so far."""
    pts = np.asarray(points)
    base = _sphere_traces()
    nb = len(base)

    def dynamic(k):
        trail = go.Scatter3d(x=pts[:k + 1, 0], y=pts[:k + 1, 1], z=pts[:k + 1, 2], mode="lines",
                             line=dict(color=PALETTE["amber"], width=4), hoverinfo="skip", showlegend=False)
        return [trail, *_vector_traces(pts[k])]

    def label(k):
        g = gate_index[k]
        return "Start: |0⟩" if g < 0 else f"Gate {g + 1}: {gate_labels[g]}"

    frames = [go.Frame(data=dynamic(k), traces=list(range(nb, nb + 3)), name=str(k),
                       layout=dict(title=dict(text=label(k)))) for k in range(len(pts))]
    fig = go.Figure(data=base + dynamic(0), frames=frames)
    steps = [dict(method="animate", label="", args=[[str(k)], dict(mode="immediate", frame=dict(duration=0, redraw=True),
                                                                    transition=dict(duration=0))])
             for k in range(len(pts))]
    fig.update_layout(
        scene=_SCENE, height=height, font=FONT, paper_bgcolor=PALETTE["paper"],
        margin=dict(l=0, r=0, t=40, b=0), title=dict(text=label(0), x=0.02),
        updatemenus=[dict(type="buttons", direction="left", showactive=False, x=0.0, y=0.0, xanchor="left", yanchor="bottom",
                          pad=dict(r=6, t=0),
                          buttons=[dict(label="▶ Play", method="animate",
                                        args=[None, dict(frame=dict(duration=45, redraw=True), fromcurrent=True,
                                                         transition=dict(duration=0))]),
                                   dict(label="❚❚ Pause", method="animate",
                                        args=[[None], dict(mode="immediate", frame=dict(duration=0, redraw=False))])])],
        sliders=[dict(steps=steps, x=0.24, len=0.76, y=0.0, yanchor="bottom", currentvalue=dict(visible=False),
                      tickcolor=PALETTE["paper"], font=dict(color=PALETTE["paper"]))],
    )
    return fig


def _bit_labels(n):
    return [format(i, f"0{n}b") for i in range(2 ** n)]


def probability_figure(probs: np.ndarray, num_qubits: int, highlight: list[str] | None = None,
                       height: int = 320) -> go.Figure:
    labels = _bit_labels(num_qubits)
    colors = [PALETTE["amber"] if highlight and lab in highlight else PALETTE["violet"] for lab in labels]
    fig = go.Figure(go.Bar(x=labels, y=probs, marker_color=colors,
                           hovertemplate="|%{x}⟩<br>P = %{y:.4f}<extra></extra>"))
    fig.update_layout(height=height, font=FONT, paper_bgcolor=PALETTE["paper"], plot_bgcolor=PALETTE["paper"],
                      margin=dict(l=10, r=10, t=10, b=10), yaxis=dict(range=[0, 1.02], title="Probability",
                                                                         gridcolor="#ECEEF4"),
                      xaxis=dict(title="Basis state (q(n−1) … q0)", type="category"), bargap=0.25)
    return fig


def amplitude_figure(amplitudes: np.ndarray, num_qubits: int, height: int = 320) -> go.Figure:
    """Bar height = |amplitude|, colour = phase (cyclic scale from −π to π)."""
    labels = _bit_labels(num_qubits)
    mag, phase = np.abs(amplitudes), np.angle(amplitudes)
    phase = np.where(mag < 1e-9, 0, phase)
    fig = go.Figure(go.Bar(
        x=labels, y=mag, customdata=np.stack([phase / np.pi, amplitudes.real, amplitudes.imag], axis=1),
        marker=dict(color=phase, colorscale="Twilight", cmin=-np.pi, cmax=np.pi,
                    colorbar=dict(title="Phase", tickvals=[-np.pi, -np.pi / 2, 0, np.pi / 2, np.pi],
                                  ticktext=["−π", "−π/2", "0", "π/2", "π"], thickness=12)),
        hovertemplate="|%{x}⟩<br>|amp| = %{y:.4f}<br>phase = %{customdata[0]:.3f}π"
                      "<br>%{customdata[1]:+.3f} %{customdata[2]:+.3f}i<extra></extra>"))
    fig.update_layout(height=height, font=FONT, paper_bgcolor=PALETTE["paper"], plot_bgcolor=PALETTE["paper"],
                      margin=dict(l=10, r=10, t=10, b=10), yaxis=dict(range=[0, 1.02], title="|Amplitude|",
                                                                         gridcolor="#ECEEF4"),
                      xaxis=dict(title="Basis state", type="category"), bargap=0.25)
    return fig


def grover_figure(curve: list[float], chosen: int, height: int = 300) -> go.Figure:
    k = list(range(len(curve)))
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=k, y=curve, mode="lines+markers", line=dict(color=PALETTE["violet"], width=3),
                             marker=dict(size=7), hovertemplate="%{x} iterations<br>P(success) = %{y:.3f}<extra></extra>",
                             showlegend=False))
    fig.add_trace(go.Scatter(x=[chosen], y=[curve[chosen]], mode="markers", showlegend=False, hoverinfo="skip",
                             marker=dict(size=16, color="rgba(0,0,0,0)", line=dict(color=PALETTE["amber"], width=3))))
    fig.update_layout(height=height, font=FONT, paper_bgcolor=PALETTE["paper"], plot_bgcolor=PALETTE["paper"],
                      margin=dict(l=10, r=10, t=10, b=10),
                      xaxis=dict(title="Grover iterations", dtick=1, gridcolor="#ECEEF4"),
                      yaxis=dict(title="P(marked)", range=[0, 1.05], gridcolor="#ECEEF4"))
    return fig


def counts_vs_ideal_figure(counts: dict[str, int], ideal: dict[str, float], height: int = 340,
                           max_states: int = 32) -> go.Figure:
    total = sum(counts.values())
    keys = sorted(set(ideal) | set(counts), key=lambda s: -(ideal.get(s, 0) + counts.get(s, 0) / total))[:max_states]
    keys = sorted(keys)
    fig = go.Figure()
    fig.add_trace(go.Bar(name="Ideal", x=keys, y=[ideal.get(k, 0) for k in keys], marker_color=PALETTE["teal"]))
    fig.add_trace(go.Bar(name="Measured", x=keys, y=[counts.get(k, 0) / total for k in keys],
                         marker_color=PALETTE["amber"]))
    fig.update_layout(barmode="group", height=height, font=FONT, paper_bgcolor=PALETTE["paper"],
                      plot_bgcolor=PALETTE["paper"], margin=dict(l=10, r=10, t=10, b=10),
                      legend=dict(orientation="h", y=1.08, x=0),
                      xaxis=dict(type="category", title="Outcome"), yaxis=dict(title="Probability", gridcolor="#ECEEF4"))
    return fig
