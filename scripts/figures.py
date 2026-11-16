"""Step 4: figures from results/tables/*.csv (run analyze.py first)."""
from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
TAB = ROOT / "results" / "tables"
FIG = ROOT / "figures"
FIG.mkdir(exist_ok=True)
plt.rcParams.update({"font.size": 9, "axes.spines.top": False, "axes.spines.right": False})
BASE, PIV, GREY = "#C2410C", "#0F766E", "#9CA3AF"


def short(m):
    return m.split("/")[-1].replace("-instruct", "").replace("-2501", "")


def fig_events(cells):
    """Per-event directional FI (mean over models), baseline vs pivot."""
    ev = cells[(cells.kind == "event") & cells.FI.notna()]
    g = ev.groupby(["item", "condition"])["FI"].agg(["mean", "sem"]).unstack("condition")
    order = g[("mean", "baseline")].sort_values().index
    y = np.arange(len(order))
    fig, ax = plt.subplots(figsize=(6.2, 0.28 * len(order) + 1.2))
    ctl = cells[(cells.kind == "control") & (cells.condition == "baseline")]["D"].dropna()
    q = np.percentile(ctl, 90) if len(ctl) else 0
    ax.axvspan(-q, q, color=GREY, alpha=0.18, lw=0, label="control noise (90th pct)")
    ax.axvline(0, color="k", lw=0.6)
    for cond, col, off in (("baseline", BASE, -0.15), ("pivot", PIV, 0.15)):
        if ("mean", cond) not in g:
            continue
        m = g[("mean", cond)].reindex(order); s = g[("sem", cond)].reindex(order)
        ax.errorbar(m, y + off, xerr=s, fmt="o", ms=4, color=col, lw=1, label=cond)
    ax.set_yticks(y, order)
    ax.set_xlabel("FI = log10(toll in attacker's language / toll in victim's language)\n< 0: lower toll when asked in the attacker's language")
    ax.legend(frameon=False, fontsize=8, loc="upper center", bbox_to_anchor=(0.5, 1.07), ncol=3)
    fig.tight_layout(); fig.savefig(FIG / "fig1_event_fi.png", dpi=220); plt.close(fig)


def fig_models(cells):
    """Per-model undirected divergence: conflict events vs neutral disaster controls (baseline + pivot)."""
    d = cells.groupby(["model", "condition", "kind"])["D"].mean().unstack(["condition", "kind"])
    models = d.index.tolist()
    x = np.arange(len(models)); w = 0.26
    fig, ax = plt.subplots(figsize=(7, 3.2))
    bars = [(("baseline", "control"), GREY, "controls (baseline)"),
            (("baseline", "event"), BASE, "conflict events (baseline)"),
            (("pivot", "event"), PIV, "conflict events (pivot)")]
    for k, (col_key, col, lab) in enumerate(bars):
        if col_key in d:
            ax.bar(x + (k - 1) * w, d[col_key], w, color=col, label=lab)
    ax.set_xticks(x, [short(m) for m in models], rotation=25, ha="right")
    ax.set_ylabel("mean |log10 ratio| between\nthe two parties' languages")
    ax.legend(frameon=False, fontsize=8)
    fig.tight_layout(); fig.savefig(FIG / "fig2_model_divergence.png", dpi=220); plt.close(fig)


def fig_attr():
    """Headline: share of answers naming the reported attacker, attacker's vs victim's language (baseline)."""
    m = pd.read_csv(TAB / "attribution_by_model_baseline.csv").set_index("model")
    c = pd.read_csv(TAB / "attribution_by_conflict_baseline.csv").set_index("conflict")
    fig, axes = plt.subplots(1, 2, figsize=(7.4, 3.3), gridspec_kw={"width_ratios": [8, 5]})
    for ax, d, labels, title in ((axes[0], m, [short(i) for i in m.index], "(a) by model"),
                                 (axes[1], c, [i.replace("_", "–") for i in c.index], "(b) by conflict")):
        order = (d["victim"] - d["attacker"]).sort_values().index
        d = d.loc[order]; lab = dict(zip((m if d is not c else c).index, labels))
        y = np.arange(len(d))
        ax.hlines(y, d["attacker"], d["victim"], color=GREY, lw=2)
        ax.plot(d["attacker"], y, "o", color=BASE, ms=6, label="asked in attacker's language")
        ax.plot(d["victim"], y, "o", color="#1D4ED8", ms=6, label="asked in victim's language")
        ax.set_yticks(y, [lab.get(i, i) for i in d.index]); ax.set_xlim(0, 1.02)
        ax.set_title(title, fontsize=9, loc="left")
        ax.set_xlabel("share naming reported attacker")
    h, l = axes[0].get_legend_handles_labels()
    fig.legend(h, l, frameon=False, fontsize=8, loc="lower center", ncol=2)
    fig.tight_layout(rect=(0, 0.07, 1, 1)); fig.savefig(FIG / "fig3_attribution.png", dpi=220); plt.close(fig)


if __name__ == "__main__":
    cells = pd.read_csv(TAB / "cells.csv")
    fig_events(cells); fig_models(cells)
    fig_attr()
    print("figures ->", sorted(p.name for p in FIG.glob("*.png")))
