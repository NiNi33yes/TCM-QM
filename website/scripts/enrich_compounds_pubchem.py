#!/usr/bin/env python3
"""Enrich app/data/compounds.json with PubChem molecular descriptors.

The website JSON already carries the computed DFT descriptors plus QC/Koopmans
indices. The frozen release master table additionally holds PubChem molecular
descriptors (XLogP, TPSA, complexity, H-bond donor/acceptor and rotatable-bond
counts, and the IUPAC name). This script merges those descriptors into
compounds.json by CID, preserving every existing field.

Idempotent: re-running overwrites only the added pubchem_* fields.
"""
import csv
import json
import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description="Merge PubChem descriptors into compounds.json by CID.")
parser.add_argument("--master", type=Path, default=ROOT.parent / "02_数据发布包" / "data_release" / "tables" / "tcm_qm_master.csv")
parser.add_argument("--target", type=Path, default=ROOT / "app" / "data" / "compounds.json")
args = parser.parse_args()
MASTER = args.master.resolve()
TARGET = args.target.resolve()

# source column -> target camelCase key. Additive only: never touches an existing field.
pubchem_fields = {
    "pubchem_IUPACName": "iupacName",
    "pubchem_XLogP": "xlogp",
    "pubchem_TPSA": "tpsa",
    "pubchem_Complexity": "complexity",
    "pubchem_HBondDonorCount": "hBondDonorCount",
    "pubchem_HBondAcceptorCount": "hBondAcceptorCount",
    "pubchem_RotatableBondCount": "rotatableBondCount",
}
ints = {"hBondDonorCount", "hBondAcceptorCount", "rotatableBondCount"}
floats = {"xlogp", "tpsa", "complexity"}


def normalize_cid(value: str) -> str:
    # master cid may surface as "19" or "19.0"; normalize to integer string.
    return str(int(float(value)))


with MASTER.open(encoding="utf-8-sig", newline="") as fh:
    by_cid = {normalize_cid(r["cid"]): r for r in csv.DictReader(fh)}

items = json.loads(TARGET.read_text(encoding="utf-8"))
missing = []
for item in items:
    cid = str(item["cid"])
    row = by_cid.get(cid)
    if row is None:
        missing.append(cid)
        continue
    for src, key in pubchem_fields.items():
        raw = row.get(src, "")
        if key in ints:
            item[key] = int(float(raw)) if raw != "" else None
        elif key in floats:
            try:
                item[key] = float(raw) if raw != "" else None
            except (TypeError, ValueError):
                item[key] = None
        else:
            item[key] = raw

TARGET.write_text(json.dumps(items, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

# quick report
def coverage(key):
    vals = [x.get(key) for x in items if x.get(key) not in (None, "")]
    return f"{key}: {len(vals)}/{len(items)} non-empty"

print(f"enriched {len(items)} records")
print(f"unmatched cid: {missing or 'NONE'}")
for key in pubchem_fields.values():
    print(" ", coverage(key))
