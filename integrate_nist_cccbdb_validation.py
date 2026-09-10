#!/usr/bin/env python3
"""Build the frozen and conformer-aware NIST CCCBDB dipole audit artifacts."""

from __future__ import annotations

import csv
import json
import math
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from scipy.stats import pearsonr, spearmanr


RELEASE = Path(__file__).resolve().parents[1]
SOURCE = (
    RELEASE
    / "audits"
    / "nist_cccbdb_dipole_validation"
    / "nist_cccbdb_dipole_validation_full.csv"
)
CID1032 = RELEASE / "audits" / "cid1032_conformer_sensitivity" / "cid1032_conformer_comparison.json"
AUDIT_DIR = RELEASE / "audits" / "nist_cccbdb_dipole_validation"
FULL_OUT = AUDIT_DIR / "nist_cccbdb_dipole_validation_full.csv"
SUMMARY_OUT = AUDIT_DIR / "nist_cccbdb_dipole_validation_summary.json"
METHOD_OUT = AUDIT_DIR / "README.md"
S7_OUT = RELEASE / "Supplementary_Table_S7_nist_cccbdb_dipole_validation.csv"


def stats(rows: list[dict], prediction_key: str) -> dict:
    pred = np.array([float(r[prediction_key]) for r in rows], dtype=float)
    exp = np.array([float(r["experimental_dipole_debye"]) for r in rows], dtype=float)
    err = pred - exp
    return {
        "n": int(len(rows)),
        "mae_debye": float(np.mean(np.abs(err))),
        "rmse_debye": float(math.sqrt(np.mean(err**2))),
        "median_absolute_error_debye": float(np.median(np.abs(err))),
        "mean_signed_error_debye": float(np.mean(err)),
        "pearson_r": float(pearsonr(pred, exp).statistic),
        "spearman_rho": float(spearmanr(pred, exp).statistic),
        "n_absolute_error_le_0_2_debye": int(np.sum(np.abs(err) <= 0.2)),
    }


def main() -> None:
    AUDIT_DIR.mkdir(parents=True, exist_ok=True)
    rows = list(csv.DictReader(SOURCE.open(encoding="utf-8-sig", newline="")))
    comparison = json.loads(CID1032.read_text(encoding="utf-8-sig"))
    lower_dipole = float(comparison["lower_energy_conformer_dipole_debye"])

    enhanced = []
    for row in rows:
        item = dict(row)
        cid = str(item["cid"]).strip()
        included = item["validation_status"] == "included_primary_benchmark"
        item["conformer_aware_dipole_debye"] = ""
        item["conformer_aware_signed_error_debye"] = ""
        item["conformer_aware_absolute_error_debye"] = ""
        item["conformer_adjudication"] = "not_applicable"
        if included:
            value = float(item["dft_dipole_debye"])
            item["conformer_adjudication"] = "frozen_value_retained"
            if cid == "1032":
                value = lower_dipole
                item["validation_status"] = "included_primary_benchmark_conformer_sensitive"
                item["review_flag"] = "resolved_by_targeted_two-conformer_audit"
                item["conformer_adjudication"] = "lower_energy_conformer_used_for_sensitivity_analysis_only"
            exp = float(item["experimental_dipole_debye"])
            item["conformer_aware_dipole_debye"] = f"{value:.9f}"
            item["conformer_aware_signed_error_debye"] = f"{value - exp:.9f}"
            item["conformer_aware_absolute_error_debye"] = f"{abs(value - exp):.9f}"
        enhanced.append(item)

    fields = list(enhanced[0])
    with FULL_OUT.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(enhanced)

    primary = [r for r in enhanced if r["validation_status"].startswith("included_primary_benchmark")]
    diagnostic = [r for r in primary if r["cid"] != "1032"]
    primary_stats = stats(primary, "dft_dipole_debye")
    diagnostic_stats = stats(diagnostic, "dft_dipole_debye")
    sensitivity_stats = stats(primary, "conformer_aware_dipole_debye")

    summary = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "source": {
            "database": "NIST Computational Chemistry Comparison and Benchmark Database (CCCBDB)",
            "standard_reference_database": "NIST SRD 101",
            "release": "Release 22 (May 2022)",
            "doi": "10.18434/T47C7Z",
            "source_url": "https://cccbdb.nist.gov/diplistx.asp",
        },
        "matching": {
            "candidate_rows": 65,
            "single_reference_candidates": 49,
            "primary_included_records": 48,
            "pre_statistical_exclusions": 1,
            "exclusion": {"cid": "5257127", "reason": "species/protonation-state mismatch"},
        },
        "primary_frozen_release_benchmark": primary_stats,
        "diagnostic_excluding_cid1032": diagnostic_stats,
        "conformer_aware_sensitivity_benchmark": sensitivity_stats,
        "cid1032_adjudication": {
            "frozen_release_dipole_debye": float(next(r for r in primary if r["cid"] == "1032")["dft_dipole_debye"]),
            "lower_energy_conformer_dipole_debye": lower_dipole,
            "experimental_dipole_debye": float(next(r for r in primary if r["cid"] == "1032")["experimental_dipole_debye"]),
            "interpretation": "The frozen value is reproducible for its geometry; the discrepancy is conformer-sensitive. The release row is retained, and the lower-energy conformer is used only in the sensitivity analysis.",
        },
    }
    SUMMARY_OUT.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    s7_fields = [
        "cid", "pubchem_title", "molecular_formula", "cas_rn", "cccbdb_name",
        "dft_dipole_debye", "experimental_dipole_debye", "absolute_error_debye",
        "conformer_aware_dipole_debye", "conformer_aware_absolute_error_debye",
        "validation_status", "conformer_adjudication", "reference", "doi",
    ]
    with S7_OUT.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=s7_fields)
        writer.writeheader()
        for row in enhanced:
            compact = {key: row.get(key, "") for key in s7_fields}
            for key in (
                "dft_dipole_debye", "experimental_dipole_debye", "absolute_error_debye",
                "conformer_aware_dipole_debye", "conformer_aware_absolute_error_debye",
            ):
                if compact[key] != "":
                    compact[key] = f"{float(compact[key]):.6f}"
            compact["validation_status"] = {
                "included_primary_benchmark": "primary",
                "included_primary_benchmark_conformer_sensitive": "conformer_sensitive",
                "excluded_species_state_mismatch": "excluded_species_mismatch",
            }.get(compact["validation_status"], compact["validation_status"])
            writer.writerow(compact)

    METHOD_OUT.write_text(
        "# NIST CCCBDB dipole-moment validation\n\n"
        "The frozen TCM-QM dipole magnitudes were matched to experimental gas-phase values from "
        "NIST CCCBDB (SRD 101, Release 22, May 2022; DOI 10.18434/T47C7Z) by CAS Registry Number "
        "and exact elemental composition. Of 65 candidate rows, 49 had a single usable reference. "
        "CID 5257127 was excluded before statistics because the TCM-QM/PubChem record is a zwitterion "
        "whereas the CCCBDB entry represents neutral gas-phase glycine, leaving 48 primary records.\n\n"
        "The primary statistics always use the frozen release values. CID 1032 is retained in that "
        "analysis. A targeted two-conformer calculation established that its large frozen dipole is "
        "geometry-specific; the lower-energy conformer is used only in a separately labelled "
        "conformer-aware sensitivity analysis. The 47-record calculation excluding CID 1032 is "
        "diagnostic and is not the primary benchmark.\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
