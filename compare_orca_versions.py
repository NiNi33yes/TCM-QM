#!/usr/bin/env python3
"""Compare paired ORCA 6.0.1 / 6.1.1 outputs of the SAME molecule.

This is the analysis half of pre-submission checklist item 3. After the paired
re-computation is complete (see ``ORCA_VERSION_PAIRED_PROTOCOL.md``), this script
parses each ``<cid>_601.out`` / ``<cid>_611.out`` pair with the same field
extraction used for the release, computes the 6.1.1-minus-6.0.1 difference for
every descriptor, and issues a PASS/FAIL verdict against declared tolerances.

Three field classes are handled:

* **EXACT**  — identity/structural fields that must be identical because the
  input is identical (charge, multiplicity, atom counts, formula, mass, basis,
  keyword line, termination/convergence flags, frequency/IR counts).
* **TOLERANCE** — numeric descriptors compared against an absolute and/or
  relative tolerance. Tolerances are chosen ~2-3 orders of magnitude looser
  than the expected optimizer round-off, so PASS means "the version effect is
  negligible below the declared threshold", and any FAIL flags a real
  regression to investigate.
* **SKIP** — run-specific fields that are not a version-consistency criterion
  (ORCA version, source filename, byte size, runtime, warning count).

Reuses ``parse_orca_out.py`` (same directory) so the comparison uses exactly
the extraction logic that produced the frozen release.

Usage:
    python code/compare_orca_versions.py \
        --dir601 REBUILD/out_601 \
        --dir611 REBUILD/out_611 \
        --sample audits/orca_version_paired_sample.csv \
        --output-dir audits/orca_version_paired
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from parse_orca_out import parse_file, FIELDS  # noqa: E402

# Fields that must match exactly across versions (same input -> same answer).
EXACT_FIELDS = {
    "charge", "multiplicity", "atom_count", "heavy_atom_count", "element_count",
    "molecular_formula", "molecular_mass_amu", "electron_count", "basis",
    "method_keywords", "normal_termination", "optimization_converged",
    "frequency_count", "imaginary_frequency_count", "ir_peak_count",
}

# Fields excluded from the version-consistency gate (run/machine specific or
# expected to differ by design).
SKIP_FIELDS = {
    "cid", "source_file", "file_size_bytes", "orca_version", "runtime_seconds",
    "warning_count",
}

# Numeric descriptors: (absolute_tolerance, relative_tolerance_or_None).
# A value passes if |delta| <= abs_tol, or (when rel_tol is set and both values
# are non-zero) |delta| / max(|a|,|b|) <= rel_tol.
TOLERANCE = {
    # energies / thermochemistry (hartree)
    "final_electronic_energy_eh": (1e-4, None),
    "zpe_eh": (1e-4, None), "zpe_kcal_mol": (1e-3, None),
    "thermal_vibrational_correction_eh": (1e-4, None),
    "thermal_rotational_correction_eh": (1e-4, None),
    "thermal_translational_correction_eh": (1e-4, None),
    "total_thermal_correction_eh": (1e-4, None),
    "total_thermal_energy_eh": (1e-4, None),
    "enthalpy_correction_eh": (1e-4, None), "total_enthalpy_eh": (1e-4, None),
    "electronic_entropy_term_eh": (1e-4, None),
    "vibrational_entropy_term_eh": (1e-4, None),
    "rotational_entropy_term_eh": (1e-4, None),
    "translational_entropy_term_eh": (1e-4, None),
    "final_entropy_term_eh": (1e-4, None), "final_entropy_term_kcal_mol": (1e-3, None),
    "gibbs_correction_eh": (1e-4, None), "final_gibbs_free_energy_eh": (1e-4, None),
    # frontier orbitals
    "homo_eh": (1e-4, None), "homo_ev": (1e-3, None),
    "lumo_eh": (1e-4, None), "lumo_ev": (1e-3, None),
    "homo_lumo_gap_eh": (1e-4, None), "homo_lumo_gap_ev": (1e-3, None),
    # dipole
    "dipole_x_au": (1e-4, None), "dipole_y_au": (1e-4, None), "dipole_z_au": (1e-4, None),
    "dipole_magnitude_au": (1e-4, None), "dipole_magnitude_debye": (1e-2, None),
    # rotational constants
    "rot_const_a_cm1": (1e-3, 1e-3), "rot_const_b_cm1": (1e-3, 1e-3),
    "rot_const_c_cm1": (1e-3, 1e-3), "rot_const_a_mhz": (1e-1, 1e-3),
    "rot_const_b_mhz": (1e-1, 1e-3), "rot_const_c_mhz": (1e-1, 1e-3),
    # vibrations / IR
    "lowest_frequency_cm1": (1.0, None),
    "lowest_positive_frequency_cm1": (1.0, None),
    "highest_frequency_cm1": (1.0, None),
    "max_ir_intensity_km_mol": (0.5, 1e-2),
}


def cid_of(path: Path) -> str:
    """CID of a paired output ``<cid>_601.out`` / ``<cid>_611.out``."""
    stem = re.sub(r"_(601|611)$", "", path.stem)
    m = re.search(r"(\d+)$", stem)
    return m.group(1) if m else stem


def to_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def within(a, b, abs_tol, rel_tol):
    fa, fb = to_float(a), to_float(b)
    if fa is None or fb is None:
        return False
    delta = abs(fa - fb)
    if rel_tol is not None and max(abs(fa), abs(fb)) > 0:
        if delta / max(abs(fa), abs(fb)) <= rel_tol:
            return True
    return delta <= abs_tol


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dir601", required=True, type=Path)
    ap.add_argument("--dir611", required=True, type=Path)
    ap.add_argument("--sample", type=Path, default=None)
    ap.add_argument("--output-dir", required=True, type=Path)
    ap.add_argument("--tolerance-config", type=Path, default=None,
                    help="Optional JSON overriding the built-in TOLERANCE table")
    args = ap.parse_args()

    tolerance = dict(TOLERANCE)
    if args.tolerance_config:
        tolerance.update(json.loads(args.tolerance_config.read_text(encoding="utf-8")))

    by601 = {cid_of(p): p for p in args.dir601.glob("*.out")}
    by611 = {cid_of(p): p for p in args.dir611.glob("*.out")}

    if args.sample:
        with args.sample.open(encoding="utf-8-sig", newline="") as fh:
            wanted = {r["cid"] for r in csv.DictReader(fh)}
    else:
        wanted = set(by601) & set(by611)

    missing601 = wanted - set(by601)
    missing611 = wanted - set(by611)

    compared_fields = [f for f in FIELDS if f not in SKIP_FIELDS]
    rows = []
    field_deltas = {f: [] for f in compared_fields}
    field_failures = {f: [] for f in compared_fields}

    for cid in sorted(wanted, key=int):
        r601 = parse_file(by601[cid])
        r611 = parse_file(by611[cid])
        row = {"cid": cid}
        ok = True
        for f in compared_fields:
            a, b = r601.get(f), r611.get(f)
            if f in EXACT_FIELDS:
                match = (a == b)
                row[f"{f}_601"] = a
                row[f"{f}_611"] = b
                row[f"{f}_within"] = int(match)
                if not match:
                    ok = False
                    field_failures[f].append(cid)
            else:
                abs_tol, rel_tol = tolerance.get(f, (0.0, None))
                delta = None
                fa, fb = to_float(a), to_float(b)
                if fa is not None and fb is not None:
                    delta = fb - fa
                match = within(a, b, abs_tol, rel_tol)
                row[f"{f}_601"] = a
                row[f"{f}_611"] = b
                row[f"{f}_delta"] = delta
                row[f"{f}_within"] = int(match)
                if delta is not None:
                    field_deltas[f].append(delta)
                if not match:
                    ok = False
                    field_failures[f].append(cid)
        row["verdict"] = "PASS" if ok else "FAIL"
        rows.append(row)

    # Write per-CID comparison table.
    args.output_dir.mkdir(parents=True, exist_ok=True)
    fieldnames = ["cid"] + [
        col for f in compared_fields for col in
        ([f"{f}_601", f"{f}_611", f"{f}_within"] if f in EXACT_FIELDS
         else [f"{f}_601", f"{f}_611", f"{f}_delta", f"{f}_within"])
    ] + ["verdict"]
    with (args.output_dir / "orca_version_paired_consistency.csv").open("w", encoding="utf-8-sig", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fieldnames, lineterminator="\r\n")
        w.writeheader()
        w.writerows(rows)

    # Build summary.
    def stat(vals):
        vals = [abs(v) for v in vals if v is not None]
        if not vals:
            return None
        return {"n": len(vals), "mean_abs": sum(vals) / len(vals), "max_abs": max(vals)}

    summary = {
        "pairs_compared": len(rows),
        "missing_601": sorted(missing601),
        "missing_611": sorted(missing611),
        "tolerance_source": "built-in + override" if args.tolerance_config else "built-in",
        "per_field": {},
    }
    for f in compared_fields:
        entry = {
            "class": "exact" if f in EXACT_FIELDS else "tolerance",
            "delta_stats": stat(field_deltas[f]),
            "failures": field_failures[f],
        }
        if f not in EXACT_FIELDS:
            entry["tolerance"] = {"abs": tolerance.get(f, (0.0, None))[0],
                                  "rel": tolerance.get(f, (0.0, None))[1]}
        summary["per_field"][f] = entry

    all_ok = all(r["verdict"] == "PASS" for r in rows) and not missing601 and not missing611
    summary["verdict"] = "PASS" if all_ok else "FAIL"
    (args.output_dir / "orca_version_paired_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
