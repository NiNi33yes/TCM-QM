#!/usr/bin/env python3
"""Generate alternative starting conformers + ORCA inputs for the
conformational-sensitivity validation.

For each flexible molecule in the sample (``select_conformer_sample.py``), this
script embeds K diverse 3D conformers with RDKit ETKDGv3 and writes, per
conformer, both an ``.xyz`` archive file and an ``.inp`` ORCA input that reuses
the molecule's released ``!`` keyword line, charge and multiplicity. The only
thing that varies across conformers is the starting geometry, so a subsequent
ORCA run tests how the released descriptors respond to the choice of starting
conformer.

Usage:
    python code/generate_conformers.py \
        --sample audits/conformer_sensitivity_sample.csv \
        --output-dir audits/conformer_sensitivity \
        --n-confs 5
"""
from __future__ import annotations

import argparse
import csv
from pathlib import Path

from rdkit import Chem
from rdkit.Chem import AllChem


def write_xyz(path: Path, mol: Chem.Mol, conf_id: int, label: int) -> None:
    conf = mol.GetConformer(conf_id)
    atoms = mol.GetAtoms()
    lines = [str(mol.GetNumAtoms()), f"conformer {label}"]
    for atom in atoms:
        x, y, z = conf.GetAtomPosition(atom.GetIdx())
        lines.append(f"{atom.GetSymbol():<2s} {x:.6f} {y:.6f} {z:.6f}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_inp(path: Path, mol: Chem.Mol, conf_id: int, keywords: str,
              charge: str, multiplicity: str) -> None:
    conf = mol.GetConformer(conf_id)
    atoms = mol.GetAtoms()
    lines = [f"! {keywords.strip()}", f"* xyz {charge} {multiplicity}"]
    for atom in atoms:
        x, y, z = conf.GetAtomPosition(atom.GetIdx())
        lines.append(f"{atom.GetSymbol():<2s} {x:.6f} {y:.6f} {z:.6f}")
    lines.append("*")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--sample", required=True, type=Path)
    ap.add_argument("--output-dir", required=True, type=Path)
    ap.add_argument("--n-confs", type=int, default=5)
    ap.add_argument("--seed", type=int, default=20260829)
    args = ap.parse_args()

    with args.sample.open(encoding="utf-8-sig", newline="") as fh:
        sample = list(csv.DictReader(fh))

    xyz_dir = args.output_dir / "xyz"
    inp_dir = args.output_dir / "inp"
    xyz_dir.mkdir(parents=True, exist_ok=True)
    inp_dir.mkdir(parents=True, exist_ok=True)

    failed = []
    for r in sample:
        cid = r["cid"]
        smiles = r["pubchem_SMILES"]
        mol = Chem.MolFromSmiles(smiles)
        if mol is None:
            failed.append({"cid": cid, "error": "SMILES parse failed"})
            continue
        mol = Chem.AddHs(mol)
        params = AllChem.ETKDGv3()
        params.randomSeed = args.seed
        params.numThreads = 0
        conf_ids = AllChem.EmbedMultipleConfs(mol, numConfs=args.n_confs, params=params)
        if len(conf_ids) < args.n_confs:
            failed.append({"cid": cid, "error": f"only {len(conf_ids)}/{args.n_confs} conformers embedded"})
        for k, conf_id in enumerate(conf_ids, start=1):
            write_xyz(xyz_dir / f"{cid}_conf{k}.xyz", mol, conf_id, k)
            write_inp(inp_dir / f"{cid}_conf{k}.inp", mol, conf_id,
                      r["method_keywords"], r["charge"], r["multiplicity"])
        print(f"{cid}: {len(conf_ids)} conformers")

    print(f"wrote xyz + inp -> {args.output_dir}")
    if failed:
        print("failed:")
        for f in failed:
            print(f"  {f}")


if __name__ == "__main__":
    main()
