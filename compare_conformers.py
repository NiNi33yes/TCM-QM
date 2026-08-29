#!/usr/bin/env python3
"""Analyze conformational sensitivity from multi-conformer ORCA outputs.

After each flexible molecule has been re-optimized from K alternative starting
conformers (see ``generate_conformers.py`` / ``CONFORMER_SENSITIVITY_PROTOCOL.md``),
this script parses every ``<cid>_conf<k>.out`` with the same field extraction as
the release and reports, per molecule, how much the optimized descriptors spread
across conformers. A molecule whose conformers all re-optimize to the same
minimum (near-zero energy spread) is insensitive to the starting geometry;
a large spread flags a genuine multi-minimum case for which the single released
geometry is a limitation rather than a representative value.

Usage:
    python code/compare_conformers.py \
        --out-dir audits/conformer_sensitivity/out \
        --sample audits/conformer_sensitivity_sample.csv \
        --output-dir audits/conformer_sensitivity/result
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from parse_orca_out import parse_file  # noqa: E402

HARTREE_TO_KCAL = 627.509474

# Descriptors reported per molecule, with the unit used for the spread.
SPREAD_FIELDS = {
    "final_electronic_energy_eh": ("kcal/mol", HARTREE_TO_KCAL),
    "final_gibbs_free_energy_eh": ("kcal/mol", HARTREE_TO_KCAL),
    "dipole_magnitude_debye": ("Debye", 1.0),
    "homo_lumo_gap_ev": ("eV", 1.0),
    "lowest_positive_frequency_cm1": ("cm-1", 1.0),
}


def cid_conf_of(path: Path):
    m = re.match(r"^(\d+)_conf(\d+)\.out$", path.name)
    if m:
        return m.group(1), int(m.group(2))
    m = re.match(r"^(\d+)\.out$", path.name)
    return (m.group(1), 0) if m else (path.stem, 0)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out-dir", required=True, type=Path)
    ap.add_argument("--sample", type=Path, default=None)
    ap.add_argument("--output-dir", required=True, type=Path)
    ap.add_argument("--energy-thresholds", type=str, default="0.1,2.0",
                    help="kcal/mol thresholds for single_minimum / near_degenerate / multi_minimum")
    args = ap.parse_args()
    t1, t2 = [float(x) for x in args.energy_thresholds.split(",")]

    with args.sample.open(encoding="utf-8-sig", newline="") as fh:
        wanted = {r["cid"] for r in csv.DictReader(fh)} if args.sample else None

    by_cid = defaultdict(list)
    for path in sorted(args.out_dir.glob("*.out")):
        cid, conf = cid_conf_of(path)
        if wanted is not None and cid not in wanted:
            continue
        by_cid[cid].append((conf, path))

    rows = []
    for cid in sorted(by_cid, key=int):
        parsed = []
        for conf, path in sorted(by_cid[cid]):
            r = parse_file(path)
            r["conf"] = conf
            parsed.append(r)
        row = {
            "cid": cid, "n_conformers": len(parsed),
            "all_terminated": int(all(p.get("normal_termination") == 1 for p in parsed)),
            "all_converged": int(all(p.get("optimization_converged") == 1 for p in parsed)),
        }
        for field, (_unit, scale) in SPREAD_FIELDS.items():
            vals = []
            for p in parsed:
                try:
                    v = float(p.get(field))
                except (TypeError, ValueError):
                    v = None
                if v is not None:
                    vals.append(v * scale)
            if vals:
                row[f"{field}_min"] = min(vals)
                row[f"{field}_max"] = max(vals)
                row[f"{field}_range"] = max(vals) - min(vals)
                row[f"{field}_std"] = (sum((v - sum(vals) / len(vals)) ** 2 for v in vals) / len(vals)) ** 0.5
            else:
                for suffix in ("min", "max", "range", "std"):
                    row[f"{field}_{suffix}"] = ""
        erange = row.get("final_electronic_energy_eh_range")
        if erange == "":
            row["sensitivity_class"] = "undetermined"
        elif erange < t1:
            row["sensitivity_class"] = "single_minimum"
        elif erange < t2:
            row["sensitivity_class"] = "near_degenerate"
        else:
            row["sensitivity_class"] = "multi_minimum"
        rows.append(row)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    fieldnames = ["cid", "n_conformers", "all_terminated", "all_converged"] + [
        f"{f}_{s}" for f in SPREAD_FIELDS for s in ("min", "max", "range", "std")
    ] + ["sensitivity_class"]
    with (args.output_dir / "conformer_sensitivity_results.csv").open("w", encoding="utf-8-sig", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fieldnames, lineterminator="\r\n")
        w.writeheader()
        w.writerows(rows)

    from collections import Counter
    classes = Counter(r["sensitivity_class"] for r in rows)
    energy_ranges = [r["final_electronic_energy_eh_range"] for r in rows
                     if r.get("final_electronic_energy_eh_range") not in ("", None)]
    summary = {
        "molecules": len(rows),
        "thresholds_kcal_mol": {"single_minimum": f"< {t1}", "near_degenerate": f"[{t1}, {t2})", "multi_minimum": f">= {t2}"},
        "sensitivity_class_counts": dict(classes),
        "max_energy_range_kcal_mol": max(energy_ranges) if energy_ranges else None,
        "not_all_terminated": [r["cid"] for r in rows if not r["all_terminated"]],
        "not_all_converged": [r["cid"] for r in rows if not r["all_converged"]],
    }
    (args.output_dir / "conformer_sensitivity_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    for r in rows:
        print(f"  {r['cid']}: {r['sensitivity_class']} (ΔE={r.get('final_electronic_energy_eh_range')} kcal/mol)")


if __name__ == "__main__":
    main()
