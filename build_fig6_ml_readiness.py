#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Rebuild Fig. 6 (Fig6_ml_readiness.png) to match manuscript v6.2.

Manuscript v6.2 figure legend (authoritative):

    "Extra Trees test-set R2 (mean +/- SD) is shown for four representative
     targets under repeated connectivity-grouped random splitting (five repeats)
     and repeated scaffold-held-out evaluation (20 Bemis-Murcko scaffold-group
     splits)."

So Fig. 6 is a single-model (Extra Trees), two-condition benchmark: each of the
four targets is one panel with two bars -- grouped-random (5 repeats) and
scaffold-held-out (20 splits) -- each carrying its between-repeat / between-split
standard deviation as an error bar.

The original figure (dated 2026-08-28) plotted the scaffold bar from a SINGLE
deterministic scaffold split (r2_sd NaN, no error bar). This script re-plots from
the two frozen summaries so the figure matches the text and carries the 20-seed
scaffold uncertainty. It recomputes nothing and overwrites no CSV.

Output is written as an exact-pixel replacement for figures/Fig6_ml_readiness.png
(2822 x 1757), the file embedded as image6.png in the Word review draft.
"""
import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from PIL import Image

import pandas as pd

MODEL = "extra_trees_morgan2_2d"
GROUPED_COLOR = "#207070"  # teal, from the original figure's dominant bar color
SCAFFOLD_COLOR = "#D0A040"  # gold, the original figure's secondary bar color
FIG_W, FIG_H = 3848, 2396
DPI = 300

# target -> (grouped_mean, grouped_sd, scaffold_mean, scaffold_sd, label)
_ap = argparse.ArgumentParser(description="Rebuild Fig. 6 (Extra Trees, grouped-random vs scaffold-held-out).")
_ap.add_argument("--mldir", default="machine_learning",
                 help="machine_learning dir (contains metrics_summary.csv and scaffold_uncertainty/)")
_ap.add_argument("--figdir", default="figures", help="output figure directory")
_argv = _ap.parse_args()
MLDIR = Path(_argv.mldir)
FIGDIR = Path(_argv.figdir)


def load_targets() -> dict:
    grouped = pd.read_csv(MLDIR / "metrics_summary.csv", encoding="utf-8-sig")
    grouped = grouped[(grouped.split_type == "random_grouped") & (grouped.model == MODEL)]
    scaffold = pd.read_csv(
        MLDIR / "scaffold_uncertainty" / "scaffold_split_uncertainty_summary.csv",
        encoding="utf-8-sig",
    )
    scaffold = scaffold[scaffold.model == MODEL]

    targets = {}
    for _, g in grouped.iterrows():
        t = g.target
        s = scaffold[scaffold.target == t].iloc[0]
        targets[t] = {
            "grouped_mean": float(g.r2_mean),
            "grouped_sd": float(g.r2_sd),
            "scaffold_mean": float(s.r2_mean),
            "scaffold_sd": float(s.r2_sd),
            "label": g.target_label,
        }
    return targets


def main() -> None:
    targets = load_targets()

    plt.rcParams.update({
        "font.family": "DejaVu Sans",
        "font.size": 20,
        "axes.edgecolor": "#555555",
        "axes.linewidth": 1.0,
        "xtick.color": "#333333",
        "ytick.color": "#333333",
    })

    fig, axes = plt.subplots(
        2, 2, figsize=(FIG_W / DPI, FIG_H / DPI), dpi=DPI, constrained_layout=True
    )

    for ax, (target, d) in zip(axes.flat, targets.items()):
        grouped_mean = d["grouped_mean"]
        grouped_sd = d["grouped_sd"]
        scaffold_mean = d["scaffold_mean"]
        scaffold_sd = d["scaffold_sd"]

        x = [0, 1]
        vals = [grouped_mean, scaffold_mean]
        errs = [grouped_sd, scaffold_sd]
        colors = [GROUPED_COLOR, SCAFFOLD_COLOR]

        ax.bar(x, vals, yerr=errs, color=colors, width=0.55,
               capsize=6, error_kw={"elinewidth": 2.0, "capthick": 2.0, "ecolor": "#333333"},
               edgecolor="none", zorder=3)

        # value annotations: "mean +/- sd"
        for xi, v, e in zip(x, vals, errs):
            ax.annotate(
                f"{v:.3f} \u00b1 {e:.3f}",
                xy=(xi, v + e),
                xytext=(0, 8),
                textcoords="offset points",
                ha="center", va="bottom", fontsize=16, color="#333333",
            )

        ax.set_xticks(x)
        ax.set_xticklabels(["Grouped\n(5 repeats)", "Scaffold\n(20 splits)"], fontsize=17)
        ax.set_ylim(0, 1.08)
        ax.set_ylabel("Test R\u00b2", fontsize=18)
        ax.set_title(d["label"], fontsize=21, pad=10, color="#1a1a1a")
        ax.grid(axis="y", alpha=0.25, linewidth=0.8, zorder=0)
        ax.set_axisbelow(True)
        for side in ("top", "right"):
            ax.spines[side].set_visible(False)

    out = FIGDIR / "Fig6_ml_readiness.png"
    fig.savefig(out, dpi=DPI)
    plt.close(fig)

    # enforce exact pixel size expected by the docx embedding
    img = Image.open(out)
    if img.size != (FIG_W, FIG_H):
        img = img.resize((FIG_W, FIG_H), Image.LANCZOS)
        img.save(out)
    print(f"wrote {out}  ({img.size[0]}x{img.size[1]})")

    for t, d in targets.items():
        print(f"  {t}: grouped {d['grouped_mean']:.3f}\u00b1{d['grouped_sd']:.3f}  "
              f"scaffold {d['scaffold_mean']:.3f}\u00b1{d['scaffold_sd']:.3f}")


if __name__ == "__main__":
    main()
