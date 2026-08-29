#!/usr/bin/env python3
"""Report scaffold-held-out ML uncertainty across many randomized scaffold splits.

Pre-submission checklist item 4 (second half). The released benchmark computes a
single deterministic scaffold split (``scaffold_split`` in ``build_ml_benchmark.py``
greedily buckets the largest scaffolds first), so the scaffold-held-out R^2 is a
single number with no variance. This script quantifies that variance by repeating
a RANDOMIZED scaffold split (``GroupShuffleSplit`` grouped by Murcko scaffold, so
no scaffold ever straddles train/test) over many seeds, and reports mean +/- SD
for the test R^2 (plus MAE/RMSE/Spearman) per model and target.

The feature pipeline, targets and model definitions are imported from
``build_ml_benchmark.py`` so the numbers are directly comparable with the released
``metrics_summary.csv``. Only the scaffold split is randomized/repeated.

Usage:
    python code/scaffold_split_uncertainty.py \
        02_数据冻结最新版_v5/tables/tcm_qm_master.csv \
        02_数据冻结最新版_v5/machine_learning/scaffold_uncertainty \
        --seeds 20
"""
from __future__ import annotations

import argparse
import json
import platform
from pathlib import Path

import numpy as np
import pandas as pd
import rdkit
import sklearn
from sklearn.compose import TransformedTargetRegressor  # noqa: F401  (kept for parity)
from sklearn.dummy import DummyRegressor
from sklearn.ensemble import ExtraTreesRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_ml_benchmark import TARGETS, mol_features, grouped_random_split, metric_rows  # noqa: E402


def build_models(repeat: int):
    """The three models used in the released benchmark (same hyperparameters)."""
    return {
        "mean_baseline": (DummyRegressor(strategy="mean"), "desc"),
        "ridge_2d": (make_pipeline(SimpleImputer(), StandardScaler(), Ridge(alpha=10.0)), "desc"),
        "extra_trees_morgan2_2d": (
            ExtraTreesRegressor(n_estimators=250, min_samples_leaf=2, max_features=0.5,
                                n_jobs=-1, random_state=repeat), "all"),
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("source", type=Path, help="Path to tcm_qm_master.csv")
    ap.add_argument("output", type=Path, help="Directory for uncertainty outputs")
    ap.add_argument("--seeds", type=int, default=20, help="Number of randomized scaffold splits")
    args = ap.parse_args()

    args.output.mkdir(parents=True, exist_ok=True)
    df = pd.read_csv(args.source, encoding="utf-8-sig", dtype={"cid": str})
    required = ["cid", "pubchem_SMILES", "pubchem_ConnectivitySMILES", *TARGETS]
    df = df.dropna(subset=required).reset_index(drop=True)
    n_before = len(df)

    fps, descs, scaffolds, valid = [], [], [], []
    for i, smi in enumerate(df["pubchem_SMILES"]):
        result = mol_features(smi)
        if result is not None:
            fp, desc, scaffold = result
            fps.append(fp); descs.append(desc); scaffolds.append(scaffold); valid.append(i)
    df = df.iloc[valid].reset_index(drop=True)
    X_desc = np.vstack(descs)
    X_all = np.hstack([np.vstack(fps), X_desc])
    y = df[list(TARGETS)].to_numpy(dtype=float)
    scaffold_arr = np.asarray(scaffolds)

    model_x = {"mean_baseline": X_desc, "ridge_2d": X_desc, "extra_trees_morgan2_2d": X_all}

    rows = []
    for seed in range(1, args.seeds + 1):
        # Randomized scaffold split: GroupShuffleSplit grouped by Murcko scaffold.
        tr, va, te = grouped_random_split(scaffold_arr, seed)
        sizes = (len(tr), len(va), len(te))
        for model_name, (model, _key) in build_models(seed).items():
            X = model_x[model_name]
            model.fit(X[tr], y[tr])
            pred = model.predict(X[te])
            if pred.ndim == 1:
                pred = pred[:, None]
            rows.extend(metric_rows(y[te], pred, model_name, "scaffold_random", seed, sizes))

    runs = pd.DataFrame(rows)
    summary = (runs.groupby(["model", "target", "target_label"], as_index=False)
               .agg(n_splits=("repeat", "nunique"),
                    r2_mean=("r2", "mean"), r2_sd=("r2", "std"),
                    r2_min=("r2", "min"), r2_max=("r2", "max"),
                    mae_mean=("mae", "mean"), mae_sd=("mae", "std"),
                    rmse_mean=("rmse", "mean"), rmse_sd=("rmse", "std"),
                    spearman_mean=("spearman_rho", "mean"), spearman_sd=("spearman_rho", "std")))

    runs.to_csv(args.output / "scaffold_split_uncertainty_runs.csv", index=False, encoding="utf-8-sig")
    summary.to_csv(args.output / "scaffold_split_uncertainty_summary.csv", index=False, encoding="utf-8-sig")

    manifest = {
        "source": str(args.source.resolve()), "records_used": len(df),
        "invalid_smiles": n_before - len(df),
        "unique_scaffolds": len(set(scaffolds)),
        "n_scaffold_splits": args.seeds,
        "split_method": "GroupShuffleSplit grouped by Murcko scaffold, 80/10/10 (train/validation/test)",
        "targets": TARGETS,
        "software": {"python": platform.python_version(), "rdkit": rdkit.__version__,
                     "scikit_learn": sklearn.__version__, "numpy": np.__version__,
                     "pandas": pd.__version__},
    }
    (args.output / "scaffold_split_uncertainty_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    print(summary.to_string(index=False))


if __name__ == "__main__":
    main()
