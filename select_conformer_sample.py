#!/usr/bin/env python3
"""Select the flexible molecules for the conformational-sensitivity validation.

Pre-submission checklist item 4 (first half). The released dataset stores one
DFT-optimized geometry per CID, obtained from a single starting geometry. This
script selects a small set of the most flexible (high rotatable-bond-count),
neutral molecules so that the sensitivity of the released descriptors to the
choice of starting conformer can be tested directly: several alternative
starting conformers of each molecule are re-optimized, and the spread of the
resulting descriptors is reported.

Selection is deterministic: neutral (charge 0) molecules with heavy-atom count
in [10, 32] (flexible enough to matter, small enough for a cheap re-run), ranked
by ``pubchem_RotatableBondCount`` descending (ties broken by smaller heavy-atom
count), taking the top N.

Usage:
    python code/select_conformer_sample.py \
        --master 02_数据冻结最新版_v5/tables/tcm_qm_master.csv \
        --output 02_数据冻结最新版_v5/audits/conformer_sensitivity_sample.csv \
        --n 15
"""
from __future__ import annotations

import argparse
import csv
from pathlib import Path


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--master", required=True, type=Path)
    ap.add_argument("--output", required=True, type=Path)
    ap.add_argument("--n", type=int, default=15, help="Number of flexible molecules (10-20)")
    ap.add_argument("--min-ha", type=int, default=10)
    ap.add_argument("--max-ha", type=int, default=32)
    args = ap.parse_args()

    with args.master.open(encoding="utf-8-sig", newline="") as fh:
        rows = list(csv.DictReader(fh))

    candidates = []
    for r in rows:
        if r.get("charge") != "0":
            continue
        try:
            rotb = int(float(r["pubchem_RotatableBondCount"]))
            ha = int(r["heavy_atom_count"])
        except (KeyError, ValueError, TypeError):
            continue
        if args.min_ha <= ha <= args.max_ha:
            candidates.append((rotb, -ha, r))

    # rotb desc, then smaller heavy-atom count first (stable tie-break).
    candidates.sort(key=lambda t: (-t[0], t[1]))
    picked = [r for _rotb, _neg_ha, r in candidates[: args.n]]

    args.output.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["cid", "source_file", "orca_version", "charge", "multiplicity",
                  "molecular_formula", "heavy_atom_count", "pubchem_RotatableBondCount",
                  "pubchem_SMILES", "method_keywords"]
    with args.output.open("w", encoding="utf-8-sig", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fieldnames, lineterminator="\r\n")
        w.writeheader()
        for r in picked:
            w.writerow({k: r.get(k, "") for k in fieldnames})

    print(f"selected {len(picked)} flexible molecules -> {args.output}")
    for r in picked:
        print(f"  {r['cid']}  rotb={r['pubchem_RotatableBondCount']}  HA={r['heavy_atom_count']}")


if __name__ == "__main__":
    main()
