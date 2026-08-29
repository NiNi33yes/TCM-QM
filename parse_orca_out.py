#!/usr/bin/env python3
"""Batch-extract numerical descriptors from ORCA 6.x .out files.

Read-only with respect to source OUT files. Uses only Python's standard library.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import re
from collections import Counter
from pathlib import Path

FLOAT = r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[EeDd][-+]?\d+)?"

FIELDS = [
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


def cid_from_path(path: Path) -> str:
    """Return a trailing numeric CID while preserving the original source filename."""
    match = re.search(r"(\d+)$", path.stem)
    return match.group(1) if match else path.stem


def num(value: str | None):
    if value is None:
        return None
    try:
        return float(value.replace("D", "E").replace("d", "e"))
    except ValueError:
        return None


def last_group(text: str, pattern: str, flags=re.I | re.M):
    hits = list(re.finditer(pattern, text, flags))
    return hits[-1].group(1) if hits else None


def last_groups(text: str, pattern: str, flags=re.I | re.M):
    hits = list(re.finditer(pattern, text, flags))
    return hits[-1].groups() if hits else None


def formula(elements: list[str]) -> str:
    counts = Counter(elements)
    order = []
    if "C" in counts:
        order.append("C")
    if "H" in counts:
        order.append("H")
    order.extend(sorted(e for e in counts if e not in {"C", "H"}))
    return "".join(e + (str(counts[e]) if counts[e] != 1 else "") for e in order)


def parse_input(text: str):
    keyword = last_group(text, r"^\|\s*1>\s*!\s*(.*?)\s*$")
    xyz = last_groups(text, rf"^\|\s*\d+>\s*\*\s*xyz\s+(-?\d+)\s+(\d+)\s*$")
    atoms = []
    block_hits = list(re.finditer(
        rf"^\|\s*\d+>\s*\*\s*xyz\s+-?\d+\s+\d+\s*$([\s\S]*?)^\|\s*\d+>\s*\*\s*$",
        text, re.I | re.M,
    ))
    if block_hits:
        for line in block_hits[-1].group(1).splitlines():
            m = re.match(rf"^\|\s*\d+>\s+(\d+|[A-Za-z]{{1,2}})\s+({FLOAT})\s+({FLOAT})\s+({FLOAT})", line)
            if m:
                token = m.group(1)
                atoms.append(atomic_symbol(token))
    return keyword, xyz, atoms


ELEMENTS = "X H He Li Be B C N O F Ne Na Mg Al Si P S Cl Ar K Ca Sc Ti V Cr Mn Fe Co Ni Cu Zn Ga Ge As Se Br Kr Rb Sr Y Zr Nb Mo Tc Ru Rh Pd Ag Cd In Sn Sb Te I Xe Cs Ba La Ce Pr Nd Pm Sm Eu Gd Tb Dy Ho Er Tm Yb Lu Hf Ta W Re Os Ir Pt Au Hg Tl Pb Bi Po At Rn Fr Ra Ac Th Pa U Np Pu Am Cm Bk Cf Es Fm Md No Lr Rf Db Sg Bh Hs Mt Ds Rg Cn Nh Fl Mc Lv Ts Og".split()


def atomic_symbol(token: str) -> str:
    if token.isdigit():
        z = int(token)
        return ELEMENTS[z] if 0 < z < len(ELEMENTS) else f"Z{z}"
    return token[0].upper() + token[1:].lower()


def final_coordinates(text: str):
    markers = list(re.finditer(r"CARTESIAN COORDINATES \(ANGSTROEM\)", text, re.I))
    if not markers:
        return []
    tail = text[markers[-1].end():]
    coords = []
    started = False
    for line in tail.splitlines():
        m = re.match(rf"^\s*([A-Za-z]{{1,2}})\s+({FLOAT})\s+({FLOAT})\s+({FLOAT})\s*$", line)
        if m:
            started = True
            coords.append((atomic_symbol(m.group(1)), num(m.group(2)), num(m.group(3)), num(m.group(4))))
        elif started:
            break
    return coords


def orbital_frontier(text: str):
    markers = list(re.finditer(r"^\s*ORBITAL ENERGIES\s*$", text, re.I | re.M))
    if not markers:
        return (None,) * 6
    tail = text[markers[-1].end():]
    rows = []
    for line in tail.splitlines():
        m = re.match(rf"^\s*\d+\s+({FLOAT})\s+({FLOAT})\s+({FLOAT})\s*$", line)
        if m:
            rows.append(tuple(num(x) for x in m.groups()))
        elif rows:
            break
    occupied = [r for r in rows if r[0] is not None and r[0] > 1e-6]
    virtual = [r for r in rows if r[0] is not None and r[0] <= 1e-6]
    if not occupied or not virtual:
        return (None,) * 6
    homo, lumo = occupied[-1], virtual[0]
    return homo[1], homo[2], lumo[1], lumo[2], lumo[1] - homo[1], lumo[2] - homo[2]


def vibrational_data(text: str):
    markers = list(re.finditer(r"^\s*VIBRATIONAL FREQUENCIES\s*$", text, re.I | re.M))
    vals = []
    if markers:
        tail = text[markers[-1].end():]
        for line in tail.splitlines():
            m = re.match(rf"^\s*\d+:\s*({FLOAT})\s*cm\*\*-1", line, re.I)
            if m:
                vals.append(num(m.group(1)))
            elif vals and re.match(r"^\s*-{3,}", line):
                break
    physical = [x for x in vals if x is not None and abs(x) > 1e-6]
    positive = [x for x in physical if x > 0]
    negative = [x for x in physical if x < 0]
    return vals, physical, positive, negative


def ir_data(text: str):
    markers = list(re.finditer(r"^\s*IR SPECTRUM\s*$", text, re.I | re.M))
    intensities = []
    if markers:
        tail = text[markers[-1].end():]
        for line in tail.splitlines():
            # ORCA table normally: mode, frequency, epsilon, intensity, ...
            parts = line.split()
            if len(parts) >= 4 and parts[0].rstrip(":").isdigit():
                values = [num(x) for x in parts[1:4]]
                if all(v is not None for v in values):
                    intensities.append(values[2])
            elif intensities and re.match(r"^\s*-{3,}", line):
                break
    return intensities


def parse_file(path: Path):
    text = path.read_text(encoding="utf-8", errors="replace")
    row = {k: None for k in FIELDS}
    row.update(cid=cid_from_path(path), source_file=path.name, file_size_bytes=path.stat().st_size)
    row["orca_version"] = last_group(text, r"Program Version\s+([0-9.]+)")
    row["normal_termination"] = int("ORCA TERMINATED NORMALLY" in text)
    row["optimization_converged"] = int("THE OPTIMIZATION HAS CONVERGED" in text)
    keyword, xyz, input_atoms = parse_input(text)
    row["method_keywords"] = keyword
    row["basis"] = last_group(text, r"Your calculation utilizes the basis:\s*(\S+)")
    if xyz:
        row["charge"], row["multiplicity"] = int(xyz[0]), int(xyz[1])

    coords = final_coordinates(text)
    atoms = [x[0] for x in coords] or input_atoms
    row["atom_count"] = len(atoms) or num(last_group(text, r"Number of atoms\s*\.+\s*(\d+)"))
    row["heavy_atom_count"] = sum(a != "H" for a in atoms) if atoms else None
    row["element_count"] = len(set(atoms)) if atoms else None
    row["molecular_formula"] = formula(atoms) if atoms else None
    row["molecular_mass_amu"] = num(last_group(text, rf"Total Mass\s*\.+\s*({FLOAT})\s*AMU"))
    row["electron_count"] = num(last_group(text, rf"N\(Total\)\s*:\s*({FLOAT})\s*electrons"))
    row["final_electronic_energy_eh"] = num(last_group(text, rf"FINAL SINGLE POINT ENERGY\s+({FLOAT})"))

    scalar_patterns = {
        "zpe_eh": rf"Zero point energy\s*\.+\s*({FLOAT})\s*Eh",
        "zpe_kcal_mol": rf"Zero point energy\s*\.+\s*{FLOAT}\s*Eh\s*({FLOAT})\s*kcal/mol",
        "thermal_vibrational_correction_eh": rf"Thermal vibrational correction\s*\.+\s*({FLOAT})\s*Eh",
        "thermal_rotational_correction_eh": rf"Thermal rotational correction\s*\.+\s*({FLOAT})\s*Eh",
        "thermal_translational_correction_eh": rf"Thermal translational correction\s*\.+\s*({FLOAT})\s*Eh",
        "total_thermal_correction_eh": rf"Total thermal correction\s+({FLOAT})\s*Eh",
        "total_thermal_energy_eh": rf"Total thermal energy\s*(?:\.+)?\s*({FLOAT})\s*Eh",
        "enthalpy_correction_eh": rf"Thermal Enthalpy correction\s*\.+\s*({FLOAT})\s*Eh",
        "total_enthalpy_eh": rf"Total [Ee]nthalpy\s*\.+\s*({FLOAT})\s*Eh",
        "electronic_entropy_term_eh": rf"Electronic entropy\s*\.+\s*({FLOAT})\s*Eh",
        "vibrational_entropy_term_eh": rf"Vibrational entropy\s*\.+\s*({FLOAT})\s*Eh",
        "rotational_entropy_term_eh": rf"Rotational entropy\s*\.+\s*({FLOAT})\s*Eh",
        "translational_entropy_term_eh": rf"Translational entropy\s*\.+\s*({FLOAT})\s*Eh",
        "final_entropy_term_eh": rf"Final entropy term\s*\.+\s*({FLOAT})\s*Eh",
        "final_entropy_term_kcal_mol": rf"Final entropy term\s*\.+\s*{FLOAT}\s*Eh\s*({FLOAT})\s*kcal/mol",
        "gibbs_correction_eh": rf"G-E\(el\)\s*\.+\s*({FLOAT})\s*Eh",
        "final_gibbs_free_energy_eh": rf"Final Gibbs free energy\s*\.+\s*({FLOAT})\s*Eh",
        "dipole_magnitude_au": rf"Magnitude \(a\.u\.\)\s*:\s*({FLOAT})",
        "dipole_magnitude_debye": rf"Magnitude \(Debye\)\s*:\s*({FLOAT})",
    }
    for key, pattern in scalar_patterns.items():
        row[key] = num(last_group(text, pattern))

    frontier = orbital_frontier(text)
    for key, value in zip(("homo_eh", "homo_ev", "lumo_eh", "lumo_ev", "homo_lumo_gap_eh", "homo_lumo_gap_ev"), frontier):
        row[key] = value
    dip = last_groups(text, rf"Total Dipole Moment\s*:\s*({FLOAT})\s+({FLOAT})\s+({FLOAT})")
    if dip:
        row["dipole_x_au"], row["dipole_y_au"], row["dipole_z_au"] = map(num, dip)
    rot_cm = last_groups(text, rf"Rotational constants in cm-1:\s*({FLOAT})\s+({FLOAT})\s+({FLOAT})")
    rot_mhz = last_groups(text, rf"Rotational constants in MHz\s*:\s*({FLOAT})\s+({FLOAT})\s+({FLOAT})")
    if rot_cm:
        row["rot_const_a_cm1"], row["rot_const_b_cm1"], row["rot_const_c_cm1"] = map(num, rot_cm)
    if rot_mhz:
        row["rot_const_a_mhz"], row["rot_const_b_mhz"], row["rot_const_c_mhz"] = map(num, rot_mhz)

    vals, physical, positive, negative = vibrational_data(text)
    row["frequency_count"] = len(physical)
    row["imaginary_frequency_count"] = len(negative)
    row["lowest_frequency_cm1"] = min(physical) if physical else None
    row["lowest_positive_frequency_cm1"] = min(positive) if positive else None
    row["highest_frequency_cm1"] = max(physical) if physical else None
    intensities = ir_data(text)
    row["ir_peak_count"] = len(intensities)
    row["max_ir_intensity_km_mol"] = max(intensities) if intensities else None
    runtime = last_groups(text, r"TOTAL RUN TIME:\s*(\d+) days\s*(\d+) hours\s*(\d+) minutes\s*(\d+) seconds\s*(\d+) msec")
    if runtime:
        d, h, m, s, ms = map(int, runtime)
        row["runtime_seconds"] = d * 86400 + h * 3600 + m * 60 + s + ms / 1000
    row["warning_count"] = len(re.findall(r"^\s*WARNING\b", text, re.I | re.M))
    return row


def write_csv(path: Path, rows, fields):
    with path.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input_dir", type=Path, help="Directory containing ORCA .out files")
    ap.add_argument("output_dir", type=Path, help="Directory for generated reports")
    args = ap.parse_args()
    files = sorted(
        args.input_dir.glob("*.out"),
        key=lambda p: (not cid_from_path(p).isdigit(), int(cid_from_path(p)) if cid_from_path(p).isdigit() else cid_from_path(p)),
    )
    args.output_dir.mkdir(parents=True, exist_ok=True)
    rows, errors = [], []
    for path in files:
        try:
            rows.append(parse_file(path))
        except Exception as exc:
            errors.append({"cid": cid_from_path(path), "source_file": path.name, "error": f"{type(exc).__name__}: {exc}"})
    write_csv(args.output_dir / "orca_descriptors.csv", rows, FIELDS)
    coverage = []
    for field in FIELDS:
        present = sum(r.get(field) not in (None, "") for r in rows)
        coverage.append({"descriptor": field, "present": present, "total": len(rows), "coverage_percent": round(100 * present / len(rows), 2) if rows else 0})
    write_csv(args.output_dir / "descriptor_coverage.csv", coverage, ["descriptor", "present", "total", "coverage_percent"])
    write_csv(args.output_dir / "parse_errors.csv", errors, ["cid", "source_file", "error"])
    required = ["normal_termination", "final_electronic_energy_eh", "homo_ev", "lumo_ev", "dipole_magnitude_debye", "zpe_eh", "total_enthalpy_eh", "final_gibbs_free_energy_eh"]
    missing = {field: [r["cid"] for r in rows if r.get(field) in (None, "")] for field in required}
    cid_counts = Counter(r["cid"] for r in rows)
    duplicate_cids = {cid: count for cid, count in cid_counts.items() if count > 1}
    non_numeric_cids = [r["cid"] for r in rows if not r["cid"].isdigit()]
    summary = {
        "input_directory": str(args.input_dir.resolve()), "files_found": len(files),
        "parsed_rows": len(rows), "parse_error_count": len(errors),
        "normally_terminated": sum(r.get("normal_termination") == 1 for r in rows),
        "zero_imaginary_frequencies": sum(r.get("imaginary_frequency_count") == 0 for r in rows),
        "unique_cid_count": len(cid_counts),
        "duplicate_cids": duplicate_cids,
        "non_numeric_cids": non_numeric_cids,
        "required_field_missing_cids": missing,
    }
    (args.output_dir / "quality_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
