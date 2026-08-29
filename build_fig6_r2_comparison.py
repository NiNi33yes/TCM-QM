#!/usr/bin/env python3
"""Rebuild Fig. 6 (benchmark_r2_comparison.png) with scaffold error bars.

Why this script exists
----------------------
``build_ml_benchmark.py`` draws the "scaffold" bars from a single deterministic
scaffold split (repeat=1), so ``r2_sd`` is NaN and the error bar collapses to
zero. The manuscript's Technical Validation reports scaffold generalization as
the mean +/- SD over 20 randomized Bemis-Murcko scaffold-group splits, computed
by ``scaffold_split_uncertainty.py``. This script re-plots the figure from the
two already-frozen summaries so the figure matches the text:

  * machine_learning/metrics_summary.csv
        -> the "random_grouped" bars (5 repeats, unchanged)
  * machine_learning/scaffold_uncertainty/scaffold_split_uncertainty_summary.csv
        -> the "scaffold" bars (20 splits, with mean +/- SD)

It recomputes nothing and does not overwrite any CSV, so the frozen data and
its SHA-256 digests are untouched.

Usage:
    python code/build_fig6_r2_comparison.py <machine_learning_dir>
"""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd


TARGETS = {
    "homo_lumo_gap_ev": "HOMO-LUMO gap (eV)",
    "dipole_magnitude_debye": "Dipole magnitude (Debye)",
    "gibbs_correction_eh": "Gibbs correction (Eh)",
    "highest_frequency_cm1": "Highest frequency (cm-1)",
}
MODEL_COLORS = {"mean_baseline": "#9CA3AF", "ridge_2d": "#0F766E", "extra_trees_morgan2_2d": "#D97706"}
SPLITS = ["random_grouped", "scaffold"]


def bar_label(split: str, model: str) -> str:
    # Identical to build_ml_benchmark.py so the axis labels are unchanged.
    return f"{split.replace('_grouped', '')}\n{model.replace('_morgan2_2d', '').replace('_2d', '')}"


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("usage: python build_fig6_r2_comparison.py <machine_learning_dir>")
    mldir = Path(sys.argv[1]).resolve()

    summary = pd.read_csv(mldir / "metrics_summary.csv", encoding="utf-8-sig")
    grouped = summary[summary.split_type == "random_grouped"]
    scaffold = pd.read_csv(
        mldir / "scaffold_uncertainty" / "scaffold_split_uncertainty_summary.csv",
        encoding="utf-8-sig",
    )

    fig, axes = plt.subplots(2, 2, figsize=(12, 9), constrained_layout=True)
    for ax, (target, label) in zip(axes.flat, TARGETS.items()):
        labels, vals, errs, colors = [], [], [], []
        for split in SPLITS:
            src = grouped if split == "random_grouped" else scaffold
            for model in MODEL_COLORS:
                rows = src[(src.target == target) & (src.model == model)]
                if rows.empty:
                    continue
                row = rows.iloc[0]
                labels.append(bar_label(split, model))
                vals.append(row.r2_mean)
                errs.append(0 if pd.isna(row.r2_sd) else row.r2_sd)
                colors.append(MODEL_COLORS[model])
        ax.bar(range(len(vals)), vals, yerr=errs, color=colors, capsize=3)
        ax.axhline(0, color="#374151", lw=0.8)
        ax.set_xticks(range(len(vals)), labels, rotation=35, ha="right", fontsize=8)
        ax.set_ylabel("Test R²"); ax.set_title(label); ax.grid(axis="y", alpha=0.2)
    fig.suptitle("Grouped-random versus scaffold generalization", fontsize=15)
    out = mldir / "benchmark_r2_comparison.png"
    fig.savefig(out, dpi=220)
    plt.close(fig)
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
