from __future__ import annotations

import argparse
import csv
import json
import platform
import sys
from collections import Counter, defaultdict
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import rdkit
import sklearn
from rdkit import Chem
from rdkit.Chem import AllChem, Descriptors, Lipinski, rdMolDescriptors
from rdkit.Chem.Scaffolds import MurckoScaffold
from sklearn.compose import TransformedTargetRegressor
from sklearn.dummy import DummyRegressor
from sklearn.ensemble import ExtraTreesRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import GroupShuffleSplit
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler


TARGETS = {
    "homo_lumo_gap_ev": "HOMO-LUMO gap (eV)",
    "dipole_magnitude_debye": "Dipole magnitude (Debye)",
    "gibbs_correction_eh": "Gibbs correction (Eh)",
    "highest_frequency_cm1": "Highest frequency (cm-1)",
}


def mol_features(smiles: str):
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return None
    fp = AllChem.GetMorganGenerator(radius=2, fpSize=2048).GetFingerprintAsNumPy(mol).astype(np.float32)
    desc = np.array([
        Descriptors.MolWt(mol), Descriptors.ExactMolWt(mol), Descriptors.MolLogP(mol),
        rdMolDescriptors.CalcTPSA(mol), Lipinski.NumHDonors(mol), Lipinski.NumHAcceptors(mol),
        Lipinski.NumRotatableBonds(mol), mol.GetNumHeavyAtoms(),
        rdMolDescriptors.CalcFractionCSP3(mol), rdMolDescriptors.CalcNumRings(mol),
        rdMolDescriptors.CalcNumAromaticRings(mol), rdMolDescriptors.CalcNumHeteroatoms(mol),
        Chem.GetFormalCharge(mol),
    ], dtype=np.float32)
    scaffold = MurckoScaffold.MurckoScaffoldSmiles(mol=mol, includeChirality=False) or f"ACYCLIC:{Chem.MolToSmiles(mol, isomericSmiles=False)}"
    return fp, desc, scaffold


def grouped_random_split(groups, seed):
    idx = np.arange(len(groups))
    gss = GroupShuffleSplit(n_splits=1, test_size=0.20, random_state=seed)
    train_idx, hold_idx = next(gss.split(idx, groups=groups))
    hold_groups = np.asarray(groups)[hold_idx]
    gss2 = GroupShuffleSplit(n_splits=1, test_size=0.50, random_state=seed + 1000)
    val_rel, test_rel = next(gss2.split(hold_idx, groups=hold_groups))
    return train_idx, hold_idx[val_rel], hold_idx[test_rel]


def scaffold_split(scaffolds):
    buckets = defaultdict(list)
    for i, scaffold in enumerate(scaffolds):
        buckets[scaffold].append(i)
    ordered = sorted(buckets.values(), key=lambda x: (-len(x), x[0]))
    targets = np.array([0.80, 0.10, 0.10]) * len(scaffolds)
    splits = [[], [], []]
    counts = np.zeros(3, dtype=int)
    for group in ordered:
        ratios = (counts + len(group)) / targets
        choice = int(np.argmin(ratios))
        splits[choice].extend(group)
        counts[choice] += len(group)
    return tuple(np.array(x, dtype=int) for x in splits)


def spearman(y_true, y_pred):
    return float(pd.Series(y_true).corr(pd.Series(y_pred), method="spearman"))


def metric_rows(y_true, y_pred, model, split_type, repeat, split_sizes):
    rows = []
    for j, (field, label) in enumerate(TARGETS.items()):
        yt, yp = y_true[:, j], y_pred[:, j]
        rows.append({
            "split_type": split_type, "repeat": repeat, "model": model,
            "target": field, "target_label": label,
            "n_train": split_sizes[0], "n_validation": split_sizes[1], "n_test": split_sizes[2],
            "r2": r2_score(yt, yp), "mae": mean_absolute_error(yt, yp),
            "rmse": mean_squared_error(yt, yp) ** 0.5, "spearman_rho": spearman(yt, yp),
        })
    return rows


def parse_args():
    parser = argparse.ArgumentParser(
        description="Run leakage-controlled molecular ML benchmarks for TCM-QM."
    )
    parser.add_argument("source", type=Path, help="Path to tcm_qm_master.csv")
    parser.add_argument("output", type=Path, help="Directory for benchmark outputs")
    return parser.parse_args()


def main(source: Path | None = None, output: Path | None = None):
    if source is None or output is None:
        args = parse_args()
        source, output = args.source, args.output
    source = source.resolve()
    output = output.resolve()
    output.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(source, encoding="utf-8-sig", dtype={"cid": str})
    required = ["cid", "pubchem_SMILES", "pubchem_ConnectivitySMILES", *TARGETS]
    missing_cols = [c for c in required if c not in df.columns]
    if missing_cols:
        raise ValueError(f"Missing columns: {missing_cols}")
    df = df.dropna(subset=required).reset_index(drop=True)
    records_before_smiles_validation = len(df)

    fps, descs, scaffolds, valid = [], [], [], []
    for i, smi in enumerate(df["pubchem_SMILES"]):
        result = mol_features(smi)
        if result is not None:
            fp, desc, scaffold = result
            fps.append(fp); descs.append(desc); scaffolds.append(scaffold); valid.append(i)
    df = df.iloc[valid].reset_index(drop=True)
    X_fp = np.vstack(fps)
    X_desc = np.vstack(descs)
    X_all = np.hstack([X_fp, X_desc])
    y = df[list(TARGETS)].to_numpy(dtype=float)
    connectivity_groups = df["pubchem_ConnectivitySMILES"].astype(str).to_numpy()

    results, predictions, assignments = [], [], []
    split_specs = [("random_grouped", seed, grouped_random_split(connectivity_groups, seed)) for seed in range(1, 6)]
    split_specs.append(("scaffold", 1, scaffold_split(scaffolds)))

    for split_type, repeat, (tr, va, te) in split_specs:
        sizes = (len(tr), len(va), len(te))
        for idx, role in [(tr, "train"), (va, "validation"), (te, "test")]:
            for i in idx:
                assignments.append({"split_type": split_type, "repeat": repeat, "cid": df.at[i, "cid"], "role": role, "scaffold": scaffolds[i]})

        models = {
            "mean_baseline": (DummyRegressor(strategy="mean"), X_desc),
            "ridge_2d": (make_pipeline(SimpleImputer(), StandardScaler(), Ridge(alpha=10.0)), X_desc),
            "extra_trees_morgan2_2d": (ExtraTreesRegressor(n_estimators=250, min_samples_leaf=2, max_features=0.5, n_jobs=-1, random_state=repeat), X_all),
        }
        for model_name, (model, X) in models.items():
            model.fit(X[tr], y[tr])
            pred = model.predict(X[te])
            if pred.ndim == 1:
                pred = pred[:, None]
            results.extend(metric_rows(y[te], pred, model_name, split_type, repeat, sizes))
            for row_idx, i in enumerate(te):
                for j, field in enumerate(TARGETS):
                    predictions.append({"split_type": split_type, "repeat": repeat, "model": model_name, "cid": df.at[i, "cid"], "target": field, "observed": y[i, j], "predicted": pred[row_idx, j], "residual": pred[row_idx, j] - y[i, j]})

    results_df = pd.DataFrame(results)
    predictions_df = pd.DataFrame(predictions)
    assignments_df = pd.DataFrame(assignments)
    summary_df = (results_df.groupby(["split_type", "model", "target", "target_label"], as_index=False)
                  .agg(repeats=("repeat", "nunique"), n_test_mean=("n_test", "mean"),
                       r2_mean=("r2", "mean"), r2_sd=("r2", "std"), mae_mean=("mae", "mean"),
                       mae_sd=("mae", "std"), rmse_mean=("rmse", "mean"), rmse_sd=("rmse", "std"),
                       spearman_mean=("spearman_rho", "mean"), spearman_sd=("spearman_rho", "std")))

    results_df.to_csv(output / "metrics_all_runs.csv", index=False, encoding="utf-8-sig")
    summary_df.to_csv(output / "metrics_summary.csv", index=False, encoding="utf-8-sig")
    predictions_df.to_csv(output / "test_predictions.csv", index=False, encoding="utf-8-sig")
    assignments_df.to_csv(output / "split_assignments.csv", index=False, encoding="utf-8-sig")

    # NOTE: this inline figure block is a quick preview only. The scaffold bars
    # here use a single deterministic split (repeat=1), so r2_sd is NaN and the
    # error bar collapses to zero. The submission figure, whose scaffold bars
    # carry the 20-seed mean ± SD (gap 0.772 ± 0.070, dipole 0.530 ± 0.074,
    # Gibbs 0.694 ± 0.065, highest-frequency 0.980 ± 0.007), is produced by
    # code/build_fig6_r2_comparison.py from
    # machine_learning/scaffold_uncertainty/scaffold_split_uncertainty_summary.csv.
    fig, axes = plt.subplots(2, 2, figsize=(12, 9), constrained_layout=True)
    model_colors = {"mean_baseline": "#9CA3AF", "ridge_2d": "#0F766E", "extra_trees_morgan2_2d": "#D97706"}
    for ax, (target, label) in zip(axes.flat, TARGETS.items()):
        sub = summary_df[summary_df.target == target]
        labels, vals, errs, colors = [], [], [], []
        for split in ["random_grouped", "scaffold"]:
            for model in model_colors:
                row = sub[(sub.split_type == split) & (sub.model == model)].iloc[0]
                labels.append(f"{split.replace('_grouped','')}\n{model.replace('_morgan2_2d','').replace('_2d','')}")
                vals.append(row.r2_mean); errs.append(0 if pd.isna(row.r2_sd) else row.r2_sd); colors.append(model_colors[model])
        ax.bar(range(len(vals)), vals, yerr=errs, color=colors, capsize=3)
        ax.axhline(0, color="#374151", lw=0.8)
        ax.set_xticks(range(len(vals)), labels, rotation=35, ha="right", fontsize=8)
        ax.set_ylabel("Test R²"); ax.set_title(label); ax.grid(axis="y", alpha=0.2)
    fig.suptitle("Grouped-random versus scaffold generalization", fontsize=15)
    fig.savefig(output / "benchmark_r2_comparison.png", dpi=220)
    plt.close(fig)

    best = predictions_df[(predictions_df.split_type == "scaffold") & (predictions_df.model == "extra_trees_morgan2_2d")]
    fig, axes = plt.subplots(2, 2, figsize=(10, 9), constrained_layout=True)
    for ax, (target, label) in zip(axes.flat, TARGETS.items()):
        sub = best[best.target == target]
        ax.scatter(sub.observed, sub.predicted, s=13, alpha=0.55, color="#0F766E", edgecolors="none")
        lo = min(sub.observed.min(), sub.predicted.min()); hi = max(sub.observed.max(), sub.predicted.max())
        ax.plot([lo, hi], [lo, hi], "--", color="#D97706", lw=1.2)
        ax.set_xlabel("Observed"); ax.set_ylabel("Predicted"); ax.set_title(label); ax.grid(alpha=0.2)
    fig.suptitle("Scaffold-split test predictions: Extra Trees", fontsize=15)
    fig.savefig(output / "scaffold_predictions.png", dpi=220)
    plt.close(fig)

    manifest = {
        "source": str(source), "records_used": len(df),
        "invalid_smiles": records_before_smiles_validation - len(df),
        "unique_connectivity_groups": int(df.pubchem_ConnectivitySMILES.nunique()),
        "unique_scaffolds": len(set(scaffolds)), "targets": TARGETS,
        "random_grouped_repeats": 5, "split_ratio_nominal": "80/10/10",
        "software": {"python": platform.python_version(), "rdkit": rdkit.__version__, "scikit_learn": sklearn.__version__, "numpy": np.__version__, "pandas": pd.__version__},
    }
    (output / "benchmark_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    print(summary_df.to_string(index=False))


if __name__ == "__main__":
    main()
