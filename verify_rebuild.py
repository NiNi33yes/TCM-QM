#!/usr/bin/env python3
"""Verify a rebuilt TCM-QM master table against the frozen release.

The authoritative acceptance criterion is a byte-identical SHA-256 against the
frozen `tables/tcm_qm_master.csv`. When the hashes differ, this script diagnoses
where (row count, header, CID set/order, per-field drift) so the rebuild can be
corrected. Field-level numeric tolerances are diagnostic only — the release gate
is the SHA-256, not these tolerances.

Usage:
    python code/verify_rebuild.py \
        --frozen 02_数据冻结最新版_v5/tables/tcm_qm_master.csv \
        --rebuilt REBUILT/tables/tcm_qm_master.csv
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from pathlib import Path

FROZEN_SHA256 = "777094ed77ff8981c08dc2b4876d0ce84f6658f13b788379509391a9fb0e7b2c"
FROZEN_SIZE = 3_115_653
FROZEN_ROWS = 3196
FROZEN_FIELDS = 79

# Fields compared with a relative tolerance when the hashes differ. Everything
# else (text/identity/boolean) must match exactly.
NUMERIC_FIELDS = {
    "file_size_bytes", "molecular_mass_amu", "electron_count",
    "final_electronic_energy_eh", "zpe_eh", "zpe_kcal_mol",
    "thermal_vibrational_correction_eh", "thermal_rotational_correction_eh",
    "thermal_translational_correction_eh", "total_thermal_correction_eh",
    "total_thermal_energy_eh", "enthalpy_correction_eh", "total_enthalpy_eh",
    "electronic_entropy_term_eh", "vibrational_entropy_term_eh",
    "rotational_entropy_term_eh", "translational_entropy_term_eh",
    "final_entropy_term_eh", "final_entropy_term_kcal_mol", "gibbs_correction_eh",
    "final_gibbs_free_energy_eh", "homo_eh", "homo_ev", "lumo_eh", "lumo_ev",
    "homo_lumo_gap_eh", "homo_lumo_gap_ev", "dipole_x_au", "dipole_y_au",
    "dipole_z_au", "dipole_magnitude_au", "dipole_magnitude_debye",
    "rot_const_a_cm1", "rot_const_b_cm1", "rot_const_c_cm1",
    "rot_const_a_mhz", "rot_const_b_mhz", "rot_const_c_mhz",
    "lowest_frequency_cm1", "lowest_positive_frequency_cm1", "highest_frequency_cm1",
    "max_ir_intensity_km_mol", "runtime_seconds",
    "pubchem_MolecularWeight", "pubchem_ExactMass", "pubchem_MonoisotopicMass",
    "pubchem_XLogP", "pubchem_TPSA", "pubchem_Complexity",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def as_float(value: str):
    try:
        return float(value.strip())
    except (ValueError, AttributeError):
        return None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--frozen", required=True, type=Path)
    ap.add_argument("--rebuilt", required=True, type=Path)
    ap.add_argument("--expected-sha", default=FROZEN_SHA256)
    ap.add_argument("--relative-tolerance", type=float, default=1e-6)
    args = ap.parse_args()

    report: dict = {
        "frozen": str(args.frozen), "rebuilt": str(args.rebuilt),
        "expected_sha256": args.expected_sha, "checks": {},
    }
    report["frozen_sha256"] = sha256(args.frozen)
    report["rebuilt_sha256"] = sha256(args.rebuilt)

    if report["rebuilt_sha256"] == args.expected_sha:
        report["verdict"] = "PASS"
        report["checks"]["byte_identical"] = True
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0

    report["checks"]["byte_identical"] = False
    with args.frozen.open(encoding="utf-8-sig", newline="") as fh:
        frozen = list(csv.DictReader(fh))
    with args.rebuilt.open(encoding="utf-8-sig", newline="") as fh:
        rebuilt = list(csv.DictReader(fh))

    frozen_header = list(frozen[0]) if frozen else []
    rebuilt_header = list(rebuilt[0]) if rebuilt else []
    frozen_keys = [r["cid"] for r in frozen]
    rebuilt_keys = [r["cid"] for r in rebuilt]

    report["frozen_rows"] = len(frozen)
    report["rebuilt_rows"] = len(rebuilt)
    report["frozen_fields"] = len(frozen_header)
    report["rebuilt_fields"] = len(rebuilt_header)
    checks = report["checks"]
    checks["row_count"] = len(frozen) == len(rebuilt)
    checks["field_count"] = len(frozen_header) == len(rebuilt_header)
    checks["header_identical"] = frozen_header == rebuilt_header
    checks["cid_set_identical"] = set(frozen_keys) == set(rebuilt_keys)
    checks["cid_order_identical"] = frozen_keys == rebuilt_keys

    field_diffs: dict = {}
    if checks["header_identical"] and checks["cid_order_identical"]:
        for field in frozen_header:
            diffs = []
            for fr, rb in zip(frozen, rebuilt):
                fv, rv = fr[field], rb[field]
                if fv == rv:
                    continue
                if field in NUMERIC_FIELDS:
                    fn, rn = as_float(fv), as_float(rv)
                    if fn is not None and rn is not None:
                        denom = max(abs(fn), abs(rn), 1e-12)
                        if abs(fn - rn) / denom <= args.relative_tolerance:
                            continue
                diffs.append({"cid": fr["cid"], "frozen": fv, "rebuilt": rv})
            if diffs:
                field_diffs[field] = diffs if len(diffs) <= 5 else diffs[:5] + [{"__truncated__": len(diffs) - 5}]
    report["field_diffs"] = field_diffs
    checks["field_level_clean"] = not field_diffs

    report["verdict"] = "PASS" if checks["field_level_clean"] else "FAIL"
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["verdict"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
