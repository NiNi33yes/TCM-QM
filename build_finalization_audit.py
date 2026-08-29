from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats


ROOT: Path
SRC_MASTER: Path
SRC_MAP: Path
SRC_JUDGMENT: Path
SRC_FINAL: Path
SRC_XYZ: Path
SRC_ML: Path

HARTREE_TO_EV = 27.211386245988
HARTREE_TO_KCAL = 627.5094740631


def require_new_root() -> None:
    if ROOT.exists():
        raise FileExistsError(f"Refusing to overwrite existing output: {ROOT}")
    for sub in ["tables", "audits", "code", "structures_xyz", "machine_learning", "manifests"]:
        (ROOT / sub).mkdir(parents=True, exist_ok=False)


def write_csv(df: pd.DataFrame, path: Path) -> None:
    df.to_csv(path, index=False, encoding="utf-8-sig", lineterminator="\n")


def parse_formula(formula: str) -> dict[str, int]:
    out: dict[str, int] = {}
    for el, n in re.findall(r"([A-Z][a-z]?)(\d*)", str(formula)):
        out[el] = out.get(el, 0) + (int(n) if n else 1)
    return out


def bh_adjust(pvals: list[float]) -> list[float]:
    p = np.asarray(pvals, dtype=float)
    order = np.argsort(p)
    ranked = p[order]
    q = ranked * len(p) / np.arange(1, len(p) + 1)
    q = np.minimum.accumulate(q[::-1])[::-1]
    result = np.empty_like(q)
    result[order] = np.minimum(q, 1.0)
    return result.tolist()


def robust_ols(y: np.ndarray, x: np.ndarray, coefficient_index: int) -> tuple[float, float, float, float, float]:
    # OLS point estimate with HC3 heteroskedasticity-consistent covariance.
    xtx_inv = np.linalg.pinv(x.T @ x)
    beta = xtx_inv @ x.T @ y
    resid = y - x @ beta
    h = np.sum((x @ xtx_inv) * x, axis=1)
    scaled = resid / np.maximum(1.0 - h, 1e-8)
    meat = x.T @ ((scaled ** 2)[:, None] * x)
    cov = xtx_inv @ meat @ xtx_inv
    se = math.sqrt(max(float(cov[coefficient_index, coefficient_index]), 0.0))
    b = float(beta[coefficient_index])
    z = b / se if se else math.inf
    p = float(2 * stats.norm.sf(abs(z)))
    return b, se, b - 1.96 * se, b + 1.96 * se, p


def source_and_flow(master: pd.DataFrame) -> dict:
    mapping = pd.read_csv(SRC_MAP)
    mapping["candidate_cid"] = pd.to_numeric(mapping["candidate_cid"], errors="coerce").astype("Int64")
    master_cids = set(pd.to_numeric(master["cid"]).astype(int))
    mapped = mapping[mapping["candidate_cid"].isin(master_cids)].copy()
    mapped["cid"] = mapped["candidate_cid"].astype(int)
    mapped["provenance_record_id"] = [f"TCMSP-{i:07d}" for i in range(1, len(mapped) + 1)]
    mapped["source_database"] = "TCMSP"
    mapped["source_locator"] = mapped["herb_compound_source"]
    mapped["source_snapshot"] = mapped["tcmsp_snapshot_version"]
    cols = ["provenance_record_id", "cid", "compound_id", "herb_id", "herb_name", "tcmsp_mol_id",
            "match_confidence", "match_method", "source_database", "source_locator", "source_snapshot"]
    write_csv(mapped[cols], ROOT / "tables" / "tcm_source_provenance.csv")

    cid_summary = (mapped.groupby("cid").agg(
        herb_count=("herb_id", "nunique"),
        herb_names=("herb_name", lambda s: " | ".join(sorted(set(map(str, s))))),
        relation_count=("herb_id", "size"),
        source_snapshot_count=("source_snapshot", "nunique"),
    ).reset_index())
    cid_summary["has_tcm_source_mapping"] = 1
    all_cids = pd.DataFrame({"cid": sorted(master_cids)})
    cid_summary = all_cids.merge(cid_summary, on="cid", how="left")
    cid_summary["has_tcm_source_mapping"] = cid_summary["has_tcm_source_mapping"].fillna(0).astype(int)
    cid_summary[["herb_count", "relation_count", "source_snapshot_count"]] = cid_summary[["herb_count", "relation_count", "source_snapshot_count"]].fillna(0).astype(int)
    cid_summary["provenance_status"] = np.where(cid_summary["has_tcm_source_mapping"].eq(1), "mapped_to_TCMSP_source_record", "no_TCMSP_mapping_in_available_snapshot")
    write_csv(cid_summary, ROOT / "tables" / "cid_tcm_provenance_summary.csv")

    judgment = pd.read_csv(SRC_JUDGMENT)
    final = pd.read_csv(SRC_FINAL)
    judgment["cid_original"] = judgment["cid"].astype(str)
    judgment["cid"] = judgment["cid_original"].str.extract(r"(\d+)$", expand=False)
    if judgment["cid"].isna().any():
        raise RuntimeError("Judgment ledger contains CID labels with no trailing numeric identifier")
    judgment["cid"] = judgment["cid"].astype(int)
    final["cid_original"] = final["cid"].astype(str)
    final["cid"] = final["cid_original"].str.extract(r"(\d+)$", expand=False)
    if final["cid"].isna().any():
        raise RuntimeError("Final-qualified table contains CID labels with no trailing numeric identifier")
    final["cid"] = final["cid"].astype(int)
    steps = [
        ("F0", "候选计算记录进入判定总表", len(judgment), f"共 {judgment.cid.nunique()} 个规范化 CID；同一 CID 可有多份候选计算记录"),
        ("F1", "排除：无频率结果或仅 SCF", int((judgment["status"] == "无频率或仅SCF").sum()), "不能形成完整优化+频率性质记录"),
        ("F2", "排除：存在显著虚频", int((judgment["status"] == "有虚频").sum()), "原始判定阈值下不满足稳定结构要求"),
        ("F3", "排除：几何优化未收敛", int((judgment["status"] == "未收敛").sum()), "未满足优化收敛"),
        ("F4", "初判合格", int((judgment["status"] == "合格").sum()), "通过原始计算质量判定"),
        ("F5", "初判合格但分组去重/汇总未纳入", int(((judgment["status"] == "合格") & (judgment["copied"] == "否")).sum()), "同组择优与汇总去重"),
        ("F6", "最终纳入发布数据集", len(final), "copied=是，且与最终主表 CID 完全一致"),
    ]
    flow = pd.DataFrame(steps, columns=["step_id", "stage", "record_count", "criterion_or_reason"])
    flow["denominator_initial"] = len(judgment)
    flow["percent_of_initial"] = (flow["record_count"] / len(judgment) * 100).round(3)
    write_csv(flow, ROOT / "tables" / "inclusion_exclusion_flow.csv")

    checks = {
        "judgment_unique_cids": int(judgment.cid.nunique()),
        "final_table_rows": int(len(final)),
        "final_master_rows": int(len(master)),
        "final_vs_master_cids_identical": set(final.cid) == master_cids,
        "selected_in_judgment": int((judgment["copied"] == "是").sum()),
        "selected_cids_equal_final": set(judgment.loc[judgment["copied"] == "是", "cid"]) == set(final.cid),
        "mapped_relationships": int(len(mapped)),
        "mapped_unique_cids": int(mapped.cid.nunique()),
        "mapped_unique_herbs": int(mapped.herb_id.nunique()),
        "unmapped_final_cids": int(len(master_cids - set(mapped.cid))),
        "source_snapshot_versions": sorted(map(str, mapped.source_snapshot.dropna().unique())),
    }
    (ROOT / "audits" / "provenance_and_flow_summary.json").write_text(json.dumps(checks, ensure_ascii=False, indent=2), encoding="utf-8")
    return checks


def version_analysis(master: pd.DataFrame) -> pd.DataFrame:
    formulas = [parse_formula(x) for x in master["molecular_formula"]]
    elements = sorted({e for f in formulas for e in f})
    comp = pd.DataFrame([{e: f.get(e, 0) for e in elements} for f in formulas])
    varying = [c for c in comp.columns if comp[c].nunique() > 1]
    cov = comp[varying].astype(float)
    # Standardize composition covariates; direct elemental counts provide exact composition control without derived-mass collinearity.
    cov = (cov - cov.mean()) / cov.std(ddof=0).replace(0, 1)
    version = (master["orca_version"].astype(str) == "6.1.1").astype(float).to_numpy()
    x = np.column_stack([np.ones(len(master)), version, cov.to_numpy()])
    targets = [
        "final_electronic_energy_eh", "homo_ev", "lumo_ev", "homo_lumo_gap_ev",
        "dipole_magnitude_debye", "zpe_kcal_mol", "final_entropy_term_kcal_mol",
        "final_gibbs_free_energy_eh", "lowest_positive_frequency_cm1", "highest_frequency_cm1",
        "max_ir_intensity_km_mol", "runtime_seconds",
    ]
    rows = []
    for target in targets:
        y0 = pd.to_numeric(master[target], errors="coerce").to_numpy(float)
        mask = np.isfinite(y0) & np.all(np.isfinite(x), axis=1)
        y = y0[mask]
        xx = x[mask]
        sd = float(np.std(y, ddof=0))
        yz = (y - np.mean(y)) / sd if sd else y * 0
        b, se, lo, hi, p = robust_ols(yz, xx, 1)
        raw_diff = float(np.nanmean(y0[version == 1]) - np.nanmean(y0[version == 0]))
        rows.append({
            "descriptor": target, "n": int(mask.sum()), "n_orca_6_0_1": int(((version == 0) & mask).sum()),
            "n_orca_6_1_1": int(((version == 1) & mask).sum()), "unadjusted_mean_difference_6_1_1_minus_6_0_1": raw_diff,
            "adjusted_standardized_beta": b, "robust_hc3_se": se, "ci95_lower": lo, "ci95_upper": hi,
            "p_value": p, "outcome_sd_original_unit": sd, "composition_covariates": ";".join(varying),
            "interpretation_scope": "association_after_element-count_adjustment_not_causal",
        })
    result = pd.DataFrame(rows)
    result["bh_fdr_q_value"] = bh_adjust(result["p_value"].tolist())
    result["materiality_flag_abs_beta_ge_0_10"] = (result["adjusted_standardized_beta"].abs() >= 0.10).astype(int)
    result["statistical_flag_q_lt_0_05"] = (result["bh_fdr_q_value"] < 0.05).astype(int)
    write_csv(result, ROOT / "tables" / "orca_version_composition_adjusted_analysis.csv")
    summary = {
        "model": "OLS with HC3 robust standard errors",
        "version_contrast": "ORCA 6.1.1 minus ORCA 6.0.1",
        "composition_control": f"standardized elemental counts: {', '.join(varying)}",
        "orca_6_0_1_n": int((version == 0).sum()), "orca_6_1_1_n": int((version == 1).sum()),
        "tested_descriptors": len(targets),
        "fdr_significant_descriptors": result.loc[result["statistical_flag_q_lt_0_05"].eq(1), "descriptor"].tolist(),
        "material_standardized_difference_descriptors": result.loc[result["materiality_flag_abs_beta_ge_0_10"].eq(1), "descriptor"].tolist(),
        "caveat": "Version assignment was not randomized; residual differences may reflect unmeasured batch or molecule-set factors.",
    }
    (ROOT / "audits" / "orca_version_analysis_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return result


def closure_analysis(master: pd.DataFrame) -> pd.DataFrame:
    def num(c): return pd.to_numeric(master[c], errors="coerce").to_numpy(float)
    checks = [
        ("orbital_gap_eh", num("homo_lumo_gap_eh"), num("lumo_eh") - num("homo_eh"), 5e-7, "Eh"),
        ("homo_eh_to_ev", num("homo_ev"), num("homo_eh") * HARTREE_TO_EV, 5e-4, "eV"),
        ("lumo_eh_to_ev", num("lumo_ev"), num("lumo_eh") * HARTREE_TO_EV, 5e-4, "eV"),
        ("gap_eh_to_ev", num("homo_lumo_gap_ev"), num("homo_lumo_gap_eh") * HARTREE_TO_EV, 5e-4, "eV"),
        ("gap_from_ev_levels", num("homo_lumo_gap_ev"), num("lumo_ev") - num("homo_ev"), 1e-3, "eV"),
        ("zpe_eh_to_kcal", num("zpe_kcal_mol"), num("zpe_eh") * HARTREE_TO_KCAL, 0.01, "kcal/mol"),
        ("entropy_eh_to_kcal", num("final_entropy_term_kcal_mol"), num("final_entropy_term_eh") * HARTREE_TO_KCAL, 0.01, "kcal/mol"),
        ("thermal_correction_component_sum", num("total_thermal_correction_eh"), num("thermal_vibrational_correction_eh") + num("thermal_rotational_correction_eh") + num("thermal_translational_correction_eh"), 5e-7, "Eh"),
        ("thermal_energy_closure", num("total_thermal_energy_eh"), num("final_electronic_energy_eh") + num("zpe_eh") + num("total_thermal_correction_eh"), 5e-7, "Eh"),
        ("enthalpy_closure", num("total_enthalpy_eh"), num("total_thermal_energy_eh") + num("enthalpy_correction_eh"), 5e-7, "Eh"),
        ("gibbs_correction_closure", num("gibbs_correction_eh"), num("zpe_eh") + num("total_thermal_correction_eh") + num("enthalpy_correction_eh") - num("final_entropy_term_eh"), 5e-7, "Eh"),
        ("gibbs_energy_closure", num("final_gibbs_free_energy_eh"), num("total_enthalpy_eh") - num("final_entropy_term_eh"), 5e-7, "Eh"),
    ]
    summaries, failures = [], []
    cids = master["cid"].astype(str).to_numpy()
    for name, observed, expected, tol, unit in checks:
        residual = observed - expected
        valid = np.isfinite(residual)
        passed = valid & (np.abs(residual) <= tol)
        summaries.append({
            "check": name, "n_evaluable": int(valid.sum()), "n_pass": int(passed.sum()),
            "n_fail": int((valid & ~passed).sum()), "pass_percent": round(100 * passed.sum() / max(valid.sum(), 1), 6),
            "absolute_tolerance": tol, "unit": unit, "max_absolute_residual": float(np.nanmax(np.abs(residual))),
            "median_absolute_residual": float(np.nanmedian(np.abs(residual))),
        })
        for i in np.where(valid & ~passed)[0]:
            failures.append({"cid": cids[i], "check": name, "observed": observed[i], "expected": expected[i], "residual": residual[i], "absolute_tolerance": tol, "unit": unit})
    summary = pd.DataFrame(summaries)
    write_csv(summary, ROOT / "tables" / "numerical_closure_summary.csv")
    write_csv(pd.DataFrame(failures, columns=["cid", "check", "observed", "expected", "residual", "absolute_tolerance", "unit"]), ROOT / "tables" / "numerical_closure_failures.csv")
    audit = {"records": len(master), "checks": len(checks), "all_checks_100_percent": bool((summary.n_fail == 0).all()), "total_failures": int(summary.n_fail.sum()), "constants": {"hartree_to_ev": HARTREE_TO_EV, "hartree_to_kcal_mol": HARTREE_TO_KCAL}}
    (ROOT / "audits" / "numerical_closure_audit.json").write_text(json.dumps(audit, indent=2), encoding="utf-8")
    return summary


def copy_release_assets(master: pd.DataFrame) -> dict:
    shutil.copy2(SRC_MASTER, ROOT / "tables" / "tcm_qm_master.csv")
    xyz_files = list(SRC_XYZ.glob("*.xyz"))
    if len(xyz_files) != len(master):
        raise RuntimeError(f"XYZ count mismatch: {len(xyz_files)} vs {len(master)}")
    for src in xyz_files:
        shutil.copy2(src, ROOT / "structures_xyz" / src.name)
    if SRC_ML.exists():
        for src in SRC_ML.rglob("*"):
            if src.is_file():
                rel = src.relative_to(SRC_ML)
                dest = ROOT / "machine_learning" / rel
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dest)
    return {"xyz_files": len(xyz_files), "ml_files": sum(p.is_file() for p in (ROOT / "machine_learning").rglob("*"))}


def write_docs(prov: dict, version: pd.DataFrame, closure: pd.DataFrame, assets: dict) -> None:
    significant = version.loc[version.statistical_flag_q_lt_0_05.eq(1), "descriptor"].tolist()
    material = version.loc[version.materiality_flag_abs_beta_ge_0_10.eq(1), "descriptor"].tolist()
    text = f"""# TCM-QM — quantum-chemical properties of 3,196 compounds associated with traditional Chinese medicine

Generated: 2026-08-28 (Asia/Shanghai)

## Scope and frozen facts

- 3,196 unique PubChem CIDs and 3,196 unique full InChIKeys.
- All records terminated normally and passed geometry-optimization convergence checks.
- 3,191 records have no imaginary frequency; five have a single minor negative mode between −4.83 and −2.08 cm⁻¹ and remain explicitly flagged.
- Quantum chemistry level: B3LYP-D3BJ/def2-TZVP, gas phase, 298.15 K and 1 atm, QRRHO reference frequency 100 cm⁻¹.
- ORCA versions: 6.0.1 (2,407 records), 6.1.1 (789 records).

## 1. Source provenance and inclusion flow

The available TCMSP snapshot provides {prov['mapped_relationships']:,} auditable herb–compound relationship rows, covering {prov['mapped_unique_cids']:,} of the 3,196 final CIDs and {prov['mapped_unique_herbs']:,} unique herbs. Each relationship retains the original workbook/sheet/row locator and snapshot identifier. The remaining {prov['unmapped_final_cids']:,} CIDs are retained as valid quantum-chemical records but are explicitly marked as having no TCMSP mapping in the available snapshot; absence is not interpreted as evidence that a compound is unrelated to traditional Chinese medicine.

The selection ledger starts with 6,948 candidate calculation records representing 6,106 normalized CIDs; a CID can have more than one candidate calculation. It records 2,860 exclusions for missing frequency/full optimization evidence, 63 for significant imaginary frequencies, and 13 for non-convergence. Of 4,012 initially qualified records, 816 were not selected during grouped deduplication/summary assembly, leaving exactly 3,196 final CIDs. The selected CID set is identical across the judgment ledger, final-qualified table, and frozen master table.

## 2. ORCA-version batch analysis

For each selected descriptor, an OLS model with HC3 robust standard errors was fitted. The contrast is ORCA 6.1.1 minus 6.0.1, while controlling for standardized elemental counts parsed from each molecular formula. P-values were corrected across the tested descriptors using Benjamini–Hochberg FDR. This is an association analysis, not a causal software-version experiment, because version assignment was not randomized.

- FDR-significant descriptors: {', '.join(significant) if significant else 'none'}.
- Descriptors with |adjusted standardized beta| ≥ 0.10: {', '.join(material) if material else 'none'}.

The complete coefficients, HC3 uncertainty intervals, raw mean differences, and FDR values are in `tables/orca_version_composition_adjusted_analysis.csv`.

## 3. Numerical closure

Twelve executable checks cover orbital gaps, Hartree/eV and Hartree/kcal conversions, component sums, and thermal/enthalpy/Gibbs identities. Tolerances are declared per equation and are chosen to accommodate the printed precision of the ORCA-derived CSV. Total failing row–check pairs: {int(closure.n_fail.sum())}. See `tables/numerical_closure_summary.csv` and `tables/numerical_closure_failures.csv`.

## 4. Frozen package

- Master records: 3,196
- XYZ structures: {assets['xyz_files']:,}
- Machine-learning benchmark files copied: {assets['ml_files']:,}
- Every payload file is listed with byte size and SHA-256 in `manifests/files_sha256.csv`.

## Release boundary

This package freezes the locally available publication data and validation artifacts. Raw ORCA OUT/GBW files are not included because they are held on the remote server and were not present in the local release workspace. A public DOI, author list, repository URL, and final license remain publication metadata decisions; placeholders are not fabricated here.
"""
    (ROOT / "README.md").write_text(text, encoding="utf-8")
    (ROOT / "CITATION.cff").write_text("cff-version: 1.2.0\ntitle: 'TCM-QM: Quantum-chemical properties of 3,196 compounds associated with traditional Chinese medicine'\ntype: dataset\nversion: '1.0.0-rc2'\ndate-released: '2026-08-28'\nmessage: 'Authors and DOI must be completed before public deposition.'\n", encoding="utf-8")
    (ROOT / "LICENSE_PENDING.txt").write_text("No public reuse license has been selected in the available project records. Select and add the approved license before public deposition. This notice is not a license.\n", encoding="utf-8")


def manifest() -> dict:
    rows = []
    for path in sorted(p for p in ROOT.rglob("*") if p.is_file() and "manifests" not in p.relative_to(ROOT).parts):
        h = hashlib.sha256()
        with path.open("rb") as f:
            for block in iter(lambda: f.read(1024 * 1024), b""):
                h.update(block)
        rows.append({"relative_path": path.relative_to(ROOT).as_posix(), "size_bytes": path.stat().st_size, "sha256": h.hexdigest()})
    df = pd.DataFrame(rows)
    write_csv(df, ROOT / "manifests" / "files_sha256.csv")
    summary = {
        "release_name": ROOT.name, "release_version": "1.0.0-rc2", "frozen_at": datetime.now(timezone.utc).isoformat(),
        "payload_file_count": len(df), "payload_size_bytes": int(df.size_bytes.sum()),
        "manifest_scope": "all files except files inside manifests/", "hash_algorithm": "SHA-256",
    }
    (ROOT / "manifests" / "release_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    mh = hashlib.sha256((ROOT / "manifests" / "files_sha256.csv").read_bytes()).hexdigest()
    (ROOT / "manifests" / "files_sha256.csv.sha256").write_text(f"{mh}  files_sha256.csv\n", encoding="ascii")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Build and audit a TCM-QM release directory.")
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--master", required=True, type=Path)
    parser.add_argument("--herb-mapping", required=True, type=Path)
    parser.add_argument("--judgment-ledger", required=True, type=Path)
    parser.add_argument("--final-qualified", required=True, type=Path)
    parser.add_argument("--xyz-directory", required=True, type=Path)
    parser.add_argument("--ml-directory", required=True, type=Path)
    args = parser.parse_args()
    global ROOT, SRC_MASTER, SRC_MAP, SRC_JUDGMENT, SRC_FINAL, SRC_XYZ, SRC_ML
    ROOT = args.output.resolve(); SRC_MASTER = args.master.resolve()
    SRC_MAP = args.herb_mapping.resolve(); SRC_JUDGMENT = args.judgment_ledger.resolve()
    SRC_FINAL = args.final_qualified.resolve(); SRC_XYZ = args.xyz_directory.resolve()
    SRC_ML = args.ml_directory.resolve()
    require_new_root()
    master = pd.read_csv(SRC_MASTER)
    if len(master) != 3196 or master.cid.nunique() != 3196:
        raise RuntimeError("Master table does not contain 3196 unique CIDs")
    prov = source_and_flow(master)
    version = version_analysis(master)
    closure = closure_analysis(master)
    assets = copy_release_assets(master)
    shutil.copy2(Path(__file__), ROOT / "code" / Path(__file__).name)
    write_docs(prov, version, closure, assets)
    summary = manifest()
    print(json.dumps({"root": str(ROOT), "provenance": prov, "assets": assets, "manifest": summary}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
