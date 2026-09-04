#!/usr/bin/env python3
"""Generate the three predeclared Phase-12 figures (heatmap, reversal
matrix, sample-complexity curves) as vector PDFs from the already-written
table-data JSON files (paper/generated/table_data/*.json), which are
themselves generated deterministically from the frozen, hash-verified
canonical analysis artifacts by generate_phase12_tables_figures.py.

No manual numeric editing. Grayscale-readable, no truncated axes.
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

HERE = Path(__file__).resolve().parent
TABLE_DIR = HERE.parent / "generated" / "table_data"
FIG_DIR = HERE.parent / "generated" / "figures"
FIG_DIR.mkdir(parents=True, exist_ok=True)

SOURCES = ["azure_llm_2024", "bailian_qwen", "burstgpt"]
SOURCE_LABELS = {"azure_llm_2024": "Azure-2024", "bailian_qwen": "Bailian/Qwen", "burstgpt": "BurstGPT"}
REGIONS = ["LOW", "PRE_KNEE", "KNEE", "POST_KNEE", "OVERLOAD", "HIGH_PRESSURE"]
PAIRS = [("azure_llm_2024", "bailian_qwen"), ("azure_llm_2024", "burstgpt"), ("bailian_qwen", "burstgpt")]


def fig1_heatmap():
    rq1 = json.load(open(TABLE_DIR / "rq1_rq2_portability.json"))
    rows = rq1["primary_metric_source_pair_x_region_table"]
    lookup = {}
    for r in rows:
        sx, rx = r["condition_x"].split("::")
        sy, ry = r["condition_y"].split("::")
        assert rx == ry
        pair = tuple(sorted([sx, sy]))
        lookup[(pair, rx)] = r["kendall_tau"]

    data = np.full((len(PAIRS), len(REGIONS)), np.nan)
    for i, (a, b) in enumerate(PAIRS):
        pair = tuple(sorted([a, b]))
        for j, region in enumerate(REGIONS):
            v = lookup.get((pair, region))
            if v is not None and v == v:
                data[i, j] = v

    fig, ax = plt.subplots(figsize=(8.2, 3.2))
    im = ax.imshow(data, cmap="Greys", vmin=0.0, vmax=1.0, aspect="auto")
    ax.set_xticks(range(len(REGIONS)))
    ax.set_xticklabels(REGIONS, rotation=30, ha="right")
    ax.set_yticks(range(len(PAIRS)))
    ax.set_yticklabels([f"{SOURCE_LABELS[a]} vs {SOURCE_LABELS[b]}" for a, b in PAIRS])
    for i in range(len(PAIRS)):
        for j in range(len(REGIONS)):
            v = data[i, j]
            if v == v:
                color = "white" if v > 0.6 else "black"
                ax.text(j, i, f"{v:.2f}", ha="center", va="center", color=color, fontsize=8)
    cbar = fig.colorbar(im, ax=ax, fraction=0.035, pad=0.02)
    cbar.set_label("Kendall's tau-b (ANWG)")
    ax.set_title("Source-pair x load-region ranking-portability (11-policy PRIMARY panel)")
    fig.tight_layout()
    outp = FIG_DIR / "fig1_portability_heatmap.pdf"
    fig.savefig(outp)
    plt.close(fig)
    print("wrote", outp)


def fig2_reversal_matrix():
    rq3 = json.load(open(TABLE_DIR / "rq3_reversals.json"))
    by_region = rq3["primary_metric_by_region_class_counts"]
    classes = ["STABLE_NO_SIGN_CHANGE", "MICROSCOPIC_SIGN_CHANGE",
               "UNSUPPORTED_SIGN_CHANGE_WIDE_CI", "SUPPORTED_PRACTICAL_REVERSAL",
               "UNDEFINED_UNESTIMABLE"]
    class_labels = ["Stable\n(no sign change)", "Microscopic\nsign change",
                     "Unsupported\n(wide CI)", "Supported practical\nreversal", "Undefined\n(unestimable)"]
    data = np.array([[by_region[r][c] for r in REGIONS] for c in classes])

    fig, ax = plt.subplots(figsize=(8.5, 3.6))
    im = ax.imshow(data, cmap="Greys", aspect="auto")
    ax.set_xticks(range(len(REGIONS)))
    ax.set_xticklabels(REGIONS, rotation=30, ha="right")
    ax.set_yticks(range(len(classes)))
    ax.set_yticklabels(class_labels, fontsize=8)
    vmax = data.max()
    for i in range(len(classes)):
        for j in range(len(REGIONS)):
            v = data[i, j]
            color = "white" if v > vmax * 0.55 else "black"
            ax.text(j, i, str(int(v)), ha="center", va="center", color=color, fontsize=8)
    cbar = fig.colorbar(im, ax=ax, fraction=0.035, pad=0.02)
    cbar.set_label("record count (ANWG)")
    ax.set_title("Reversal-class counts by load region (165 pairwise records/region)")
    fig.tight_layout()
    outp = FIG_DIR / "fig2_reversal_class_matrix.pdf"
    fig.savefig(outp)
    plt.close(fig)
    print("wrote", outp)


def fig3_sample_complexity():
    # Visual-only legibility pass (no data values changed): azure_llm_2024
    # and bailian_qwen recovery curves both approach 1.0 in the top-1 panel
    # and were hard to tell apart there, so markers are now differentiated
    # by fill (solid vs. hollow) in addition to shape/linestyle, and sized
    # up slightly.
    rq4 = json.load(open(TABLE_DIR / "rq4_sample_complexity.json"))
    fig, axes = plt.subplots(1, 2, figsize=(8.5, 3.2), sharey=True)
    markers = {"azure_llm_2024": "o", "bailian_qwen": "s", "burstgpt": "^"}
    facecolors = {"azure_llm_2024": "black", "bailian_qwen": "white", "burstgpt": "black"}
    linestyles = {"azure_llm_2024": "-", "bailian_qwen": "--", "burstgpt": ":"}
    for row in rq4["primary_metric_rows"]:
        src = row["source"]
        ns = [p["n"] for p in row["points"]]
        exact = [p["p_exact_recovery"] for p in row["points"]]
        top1 = [p["p_topk_recovery"]["1"] for p in row["points"]]
        plot_kwargs = dict(
            marker=markers[src], color="black", linestyle=linestyles[src],
            markersize=7, markerfacecolor=facecolors[src], markeredgecolor="black",
            markeredgewidth=1.1, linewidth=1.3,
        )
        axes[0].plot(ns, exact, label=SOURCE_LABELS[src], **plot_kwargs)
        axes[1].plot(ns, top1, label=SOURCE_LABELS[src], **plot_kwargs)
    for ax, title in zip(axes, ["Exact-order recovery", "Top-1 recovery"]):
        ax.axhline(0.9, color="gray", linewidth=0.8, linestyle="-.")
        ax.set_xlabel("n (workload windows)")
        ax.set_xticks(rq4["ladder_n_values"])
        ax.set_ylim(-0.02, 1.02)
        ax.set_title(title)
    axes[0].set_ylabel("P(recovery of full n=40 reference ranking)")
    axes[0].legend(fontsize=8, loc="lower right")
    fig.suptitle(f"Benchmark sample complexity, primary metric ({rq4['draws_per_n']} draws/n, 0.9 threshold marked)")
    fig.tight_layout()
    outp = FIG_DIR / "fig3_sample_complexity_curves.pdf"
    fig.savefig(outp)
    plt.close(fig)
    print("wrote", outp)


if __name__ == "__main__":
    fig1_heatmap()
    fig2_reversal_matrix()
    fig3_sample_complexity()
