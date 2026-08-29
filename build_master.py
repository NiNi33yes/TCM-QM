#!/usr/bin/env python3
"""Assemble the frozen 79-field master table from parsed ORCA descriptors + a
frozen PubChem metadata snapshot.

This closes the one step that was previously undocumented in the release: the
left join that turns `parse_orca_out.py` output (fields 0-59, 60 columns) into
the published `tcm_qm_master.csv` (79 columns = 60 ORCA + 19 PubChem).

Reproducibility contract
------------------------
The frozen master is byte-identical to the output of this script ONLY when all
of the following hold; `code/verify_rebuild.py` is the authoritative gate, not
this docstring.

1. `--descriptors` is the output of `code/parse_orca_out.py` over exactly the
   3,196 final OUT files (60 columns, 3,196 rows, `cid` as a string key).
2. `--pubchem` is the SAME PubChem snapshot used at freeze time (19 identity
   fields per CID). Its string values must match byte-for-byte, including any
   empty cells for the 20 CIDs with no PubChem title.
3. Output uses UTF-8 with BOM and CRLF line endings — the frozen tables were
   produced on Windows, so a Linux rebuild must force both to reproduce the
   frozen SHA-256. Rows are ordered by numeric CID ascending.
"""
from __future__ import annotations

import argparse
import csv
from pathlib import Path

# Fields 0-59 — exactly the columns emitted by code/parse_orca_out.py, in order.
ORCA_FIELDS = [
    "cid", "source_file", "file_size_bytes", "orca_version", "normal_termination",
    "optimization_converged", "method_keywords", "basis", "charge", "multiplicity",
    "atom_count", "heavy_atom_count", "element_count", "molecular_formula",
    "molecular_mass_amu", "electron_count", "final_electronic_energy_eh",
    "zpe_eh", "zpe_kcal_mol", "thermal_vibrational_correction_eh",
    "thermal_rotational_correction_eh", "thermal_translational_correction_eh",
    "total_thermal_correction_eh", "total_thermal_energy_eh", "enthalpy_correction_eh",
    "total_enthalpy_eh", "electronic_entropy_term_eh", "vibrational_entropy_term_eh",
    "rotational_entropy_term_eh", "translational_entropy_term_eh",
    "final_entropy_term_eh", "final_entropy_term_kcal_mol", "gibbs_correction_eh",
    "final_gibbs_free_energy_eh", "homo_eh", "homo_ev", "lumo_eh", "lumo_ev",
    "homo_lumo_gap_eh", "homo_lumo_gap_ev", "dipole_x_au", "dipole_y_au",
    "dipole_z_au", "dipole_magnitude_au", "dipole_magnitude_debye",
    "rot_const_a_cm1", "rot_const_b_cm1", "rot_const_c_cm1", "rot_const_a_mhz",
    "rot_const_b_mhz", "rot_const_c_mhz", "frequency_count", "imaginary_frequency_count",
    "lowest_frequency_cm1", "lowest_positive_frequency_cm1", "highest_frequency_cm1",
    "ir_peak_count", "max_ir_intensity_km_mol", "runtime_seconds", "warning_count",
]

# Fields 60-78 — the PubChem identity block, in the frozen column order.
PUBCHEM_FIELDS = [
    "pubchem_CID", "pubchem_Title", "pubchem_IUPACName", "pubchem_MolecularFormula",
    "pubchem_MolecularWeight", "pubchem_ExactMass", "pubchem_MonoisotopicMass",
    "pubchem_Charge", "pubchem_SMILES", "pubchem_ConnectivitySMILES", "pubchem_InChI",
    "pubchem_InChIKey", "pubchem_XLogP", "pubchem_TPSA", "pubchem_Complexity",
    "pubchem_HBondDonorCount", "pubchem_HBondAcceptorCount", "pubchem_RotatableBondCount",
    "pubchem_HeavyAtomCount",
]

ALL_FIELDS = ORCA_FIELDS + PUBCHEM_FIELDS


def resolve_column(fields: list[str], target: str) -> str | None:
    """Map a frozen PubChem field name to the snapshot's actual column.

    Prefers the exact `pubchem_X` name, then the bare `X`, then case-insensitive
    matches, so the same script accepts either a PUG-style snapshot or a legacy
    compound-master export.
    """
    if target in fields:
        return target
    bare = target[len("pubchem_"):]
    if bare in fields:
        return bare
    lowered = {f.lower(): f for f in fields}
    return lowered.get(target.lower()) or lowered.get(bare.lower())


def key_column(fields: list[str]) -> str:
    for candidate in ("cid", "pubchem_CID", "CID", "candidate_cid"):
        if candidate in fields:
            return candidate
    raise RuntimeError(f"PubChem snapshot has no CID key column; found: {fields}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--descriptors", required=True, type=Path,
                    help="orca_descriptors.csv from code/parse_orca_out.py (60 columns)")
    ap.add_argument("--pubchem", required=True, type=Path,
                    help="Frozen PubChem metadata snapshot (19 identity fields keyed by CID)")
    ap.add_argument("--output", required=True, type=Path,
                    help="Path to write tcm_qm_master.csv (79 columns)")
    args = ap.parse_args()

    with args.descriptors.open(encoding="utf-8-sig", newline="") as fh:
        descriptor_rows = list(csv.DictReader(fh))

    missing_orca = [f for f in ORCA_FIELDS if f not in descriptor_rows[0]]
    if missing_orca:
        raise RuntimeError(f"Descriptors file is missing ORCA columns: {missing_orca}")

    with args.pubchem.open(encoding="utf-8-sig", newline="") as fh:
        snapshot_rows = list(csv.DictReader(fh))
    pub_fields = list(snapshot_rows[0]) if snapshot_rows else []
    key = key_column(pub_fields)
    pub_by_cid = {str(r[key]).strip(): r for r in snapshot_rows}
    column_map = {target: resolve_column(pub_fields, target) for target in PUBCHEM_FIELDS}

    ordered_cids = sorted(descriptor_rows, key=lambda r: int(r["cid"]))
    out_rows = []
    for dr in ordered_cids:
        cid = dr["cid"]
        pub = pub_by_cid.get(cid, {})
        row = {f: dr.get(f, "") for f in ORCA_FIELDS}
        for target in PUBCHEM_FIELDS:
            col = column_map[target]
            row[target] = pub.get(col, "") if col else ""
        out_rows.append(row)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    # UTF-8 BOM + CRLF are required to reproduce the frozen Windows-origin bytes.
    with args.output.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=ALL_FIELDS, lineterminator="\r\n")
        writer.writeheader()
        writer.writerows(out_rows)

    print(f"wrote {len(out_rows)} rows x {len(ALL_FIELDS)} fields -> {args.output}")


if __name__ == "__main__":
    main()
