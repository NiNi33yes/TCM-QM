#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
import math
import re
import argparse
import sys
import time
import urllib.error
import urllib.request
from collections import Counter
from pathlib import Path

import numpy as np

PERIODIC = [
    "", "H", "He", "Li", "Be", "B", "C", "N", "O", "F", "Ne",
    "Na", "Mg", "Al", "Si", "P", "S", "Cl", "Ar", "K", "Ca",
    "Sc", "Ti", "V", "Cr", "Mn", "Fe", "Co", "Ni", "Cu", "Zn",
    "Ga", "Ge", "As", "Se", "Br", "Kr", "Rb", "Sr", "Y", "Zr",
    "Nb", "Mo", "Tc", "Ru", "Rh", "Pd", "Ag", "Cd", "In", "Sn",
    "Sb", "Te", "I", "Xe",
]
ATOMIC_NUMBER = {symbol: number for number, symbol in enumerate(PERIODIC) if symbol}
FIELDS = [
    "cid", "orca_version", "atom_count", "heavy_atom_count", "charge", "multiplicity",
    "pubchem_3d_status", "comparison_status", "heavy_atom_rmsd_angstrom", "classification",
    "source_out", "pubchem_sdf", "error",
]


def normalize_symbol(token: str):
    if token.isdigit():
        return PERIODIC[int(token)]
    return token[0].upper() + token[1:].lower()


def read_master(path: Path):
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def extract_input_geometry(path: Path):
    text = path.read_text(encoding="utf-8", errors="replace")
    start = text.find("INPUT FILE")
    if start < 0:
        raise ValueError("INPUT FILE section not found")
    end = text.find("END OF INPUT", start)
    block = text[start:] if end < 0 else text[start:end]
    payload = []
    for line in block.splitlines():
        match = re.match(r"^\s*\|\s*\d+>\s?(.*)$", line)
        if match:
            payload.append(match.group(1).strip())
    begin = None
    charge = multiplicity = None
    for index, line in enumerate(payload):
        match = re.match(r"^\*\s+xyz\s+(-?\d+)\s+(\d+)\s*$", line, re.I)
        if match:
            begin = index + 1
            charge, multiplicity = int(match.group(1)), int(match.group(2))
            break
    if begin is None:
        raise ValueError("xyz input header not found")
    atoms = []
    for line in payload[begin:]:
        if line == "*":
            break
        parts = line.split()
        if len(parts) >= 4:
            atoms.append((normalize_symbol(parts[0]), float(parts[1]), float(parts[2]), float(parts[3])))
    if not atoms:
        raise ValueError("no input atoms parsed")
    return charge, multiplicity, atoms


def download(cid: str, destination: Path, retries=4):
    if destination.exists() and destination.stat().st_size > 100:
        return "cached", ""
    url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/{cid}/SDF?record_type=3d"
    for attempt in range(retries):
        try:
            request = urllib.request.Request(url, headers={"User-Agent": "TCM-QM-Atlas/1.0 academic-research"})
            with urllib.request.urlopen(request, timeout=60) as response:
                payload = response.read()
            if b"V2000" not in payload[:1000] and b"V3000" not in payload[:1000]:
                raise ValueError("response is not SDF")
            destination.write_bytes(payload)
            return "downloaded", ""
        except urllib.error.HTTPError as exc:
            if exc.code in (404, 400):
                return f"http_{exc.code}", exc.read().decode("utf-8", errors="replace")[:200].replace("\n", " ")
            error = f"HTTP {exc.code}"
        except Exception as exc:
            error = f"{type(exc).__name__}: {exc}"
        time.sleep(2 ** attempt)
    return "error", error


def parse_sdf_coordinates(path: Path):
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    if len(lines) < 4:
        raise ValueError("short SDF")
    counts = lines[3]
    if "V2000" not in counts:
        raise ValueError("only V2000 SDF is supported in fast full audit")
    atom_count = int(counts[:3])
    atoms = []
    for line in lines[4:4 + atom_count]:
        atoms.append((line[31:34].strip(), float(line[0:10]), float(line[10:20]), float(line[20:30])))
    return atoms


def kabsch_rmsd(reference, probe):
    reference = np.asarray(reference, dtype=float)
    probe = np.asarray(probe, dtype=float)
    reference -= reference.mean(axis=0)
    probe -= probe.mean(axis=0)
    u, _, vt = np.linalg.svd(probe.T @ reference)
    rotation = u @ vt
    if np.linalg.det(rotation) < 0:
        u[:, -1] *= -1
        rotation = u @ vt
    aligned = probe @ rotation
    return float(np.sqrt(np.mean(np.sum((aligned - reference) ** 2, axis=1))))


def heavy(atoms):
    return [atom for atom in atoms if atom[0] != "H"]


def classify(value):
    if value <= 0.02:
        return "coordinate_identity_consistent"
    if value <= 0.20:
        return "same_geometry_with_minor_relaxation"
    if value <= 0.75:
        return "same_or_similar_conformer"
    return "different_conformer_or_source"


def compare(initial_atoms, pubchem_atoms):
    initial = heavy(initial_atoms)
    pubchem = heavy(pubchem_atoms)
    initial_symbols = [a[0] for a in initial]
    pubchem_symbols = [a[0] for a in pubchem]
    if initial_symbols != pubchem_symbols:
        return None, "atom_order_or_element_sequence_mismatch"
    initial_xyz = [(a[1], a[2], a[3]) for a in initial]
    pubchem_xyz = [(a[1], a[2], a[3]) for a in pubchem]
    return kabsch_rmsd(pubchem_xyz, initial_xyz), "direct_atom_order"


def load_existing(path: Path):
    if not path.exists():
        return {}, []
    with path.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    return {row["cid"]: row for row in rows}, rows


def append_row(path: Path, row):
    new = not path.exists()
    with path.open("a", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        if new:
            writer.writeheader()
        writer.writerow(row)


def summarize(rows, destination: Path):
    rmsd = [float(r["heavy_atom_rmsd_angstrom"]) for r in rows if r.get("heavy_atom_rmsd_angstrom")]
    classes = Counter(r["classification"] for r in rows)
    versions = Counter(r["orca_version"] for r in rows)
    summary = {
        "records_processed": len(rows),
        "orca_versions": dict(versions),
        "pubchem_3d_available": sum(r["pubchem_3d_status"] in ("downloaded", "cached") for r in rows),
        "rmsd_comparable_direct_atom_order": len(rmsd),
        "classification_counts": dict(classes),
        "rmsd_min_angstrom": min(rmsd) if rmsd else None,
        "rmsd_median_angstrom": float(np.median(rmsd)) if rmsd else None,
        "rmsd_95th_percentile_angstrom": float(np.percentile(rmsd, 95)) if rmsd else None,
        "rmsd_max_angstrom": max(rmsd) if rmsd else None,
        "caveat": "Direct-order full audit is decisive for exact coordinate reuse. Sequence mismatches require the separate graph-mapping fallback audit and are not classified as failures.",
    }
    destination.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary


def main():
    parser = argparse.ArgumentParser(description="Audit archived ORCA input geometries against PubChem3D.")
    parser.add_argument("project_root", type=Path)
    root = parser.parse_args().project_root.resolve()
    audit_dir = root / "initial_geometry_full_audit"
    sdf_dir = audit_dir / "pubchem_sdf_cache"
    audit_dir.mkdir(exist_ok=True)
    sdf_dir.mkdir(exist_ok=True)
    results_path = audit_dir / "initial_geometry_pubchem3d_full_results.csv"
    summary_path = audit_dir / "initial_geometry_pubchem3d_full_summary.json"
    existing, rows = load_existing(results_path)
    master = read_master(root / "all_results" / "orca_descriptors.csv")
    pending = [record for record in master if record["cid"] not in existing]
    print(f"Total={len(master)} completed={len(existing)} pending={len(pending)}")

    for index, record in enumerate(pending, 1):
        cid = record["cid"].strip()
        source = root / "out_all" / f"{cid}.out"
        sdf = sdf_dir / f"{cid}.sdf"
        row = {field: "" for field in FIELDS}
        row.update({
            "cid": cid, "orca_version": record["orca_version"], "atom_count": record["atom_count"],
            "heavy_atom_count": record["heavy_atom_count"], "charge": record["charge"],
            "multiplicity": record["multiplicity"], "source_out": str(source), "pubchem_sdf": str(sdf),
        })
        try:
            charge, multiplicity, initial = extract_input_geometry(source)
            if len(initial) != int(float(record["atom_count"])):
                raise ValueError("input atom count differs from master")
            status, error = download(cid, sdf)
            row["pubchem_3d_status"] = status
            row["error"] = error
            if status in ("downloaded", "cached"):
                pubchem = parse_sdf_coordinates(sdf)
                value, comparison_status = compare(initial, pubchem)
                row["comparison_status"] = comparison_status
                if value is not None:
                    row["heavy_atom_rmsd_angstrom"] = f"{value:.6f}"
                    row["classification"] = classify(value)
                else:
                    row["classification"] = "requires_graph_mapping"
            else:
                row["classification"] = "pubchem_3d_unavailable"
        except Exception as exc:
            row["classification"] = "processing_error"
            row["error"] = f"{type(exc).__name__}: {exc}"
        append_row(results_path, row)
        rows.append(row)
        if index % 25 == 0 or index == len(pending):
            summary = summarize(rows, summary_path)
            print(f"[{len(rows)}/{len(master)}] {dict(Counter(r['classification'] for r in rows))}")
        time.sleep(0.22)
    summary = summarize(rows, summary_path)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"Results: {results_path}")


if __name__ == "__main__":
    main()
