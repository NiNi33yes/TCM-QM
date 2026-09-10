import csv
import hashlib
import json
from collections import Counter
from pathlib import Path

from rdkit import Chem


ROOT = Path(__file__).resolve().parents[1]
MASTER = ROOT / "tables" / "tcm_qm_master_with_tcmsp.csv"
OUTPUT = ROOT / "tables" / "ionization_state_audit.csv"
SUPPLEMENT = ROOT / "Supplementary_Table_S5_ionization_state.csv"
SUMMARY = ROOT / "audits" / "ionization_state_audit_summary.json"


def nitro_charge_atom_indices(mol):
    """Return charged atom indices belonging to canonical nitro resonance groups."""
    indices = set()
    nitro = Chem.MolFromSmarts("[N+](=O)[O-]")
    for match in mol.GetSubstructMatches(nitro):
        for idx in match:
            if mol.GetAtomWithIdx(idx).GetFormalCharge() != 0:
                indices.add(idx)
    return indices


with MASTER.open(encoding="utf-8-sig", newline="") as handle:
    rows = list(csv.DictReader(handle))

output_rows = []
counts = Counter()

for row in rows:
    cid = row["cid"].strip()
    smiles = row["pubchem_SMILES"].strip()
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        raise ValueError(f"RDKit could not parse PubChem SMILES for CID {cid}: {smiles}")

    charged = [atom for atom in mol.GetAtoms() if atom.GetFormalCharge() != 0]
    positive = [atom for atom in charged if atom.GetFormalCharge() > 0]
    negative = [atom for atom in charged if atom.GetFormalCharge() < 0]
    molecular_net_charge = sum(atom.GetFormalCharge() for atom in mol.GetAtoms())
    calculation_charge = int(round(float(row["charge"])))
    pubchem_net_charge = int(round(float(row["pubchem_Charge"])))
    charge_separated = bool(positive and negative)
    nitro_indices = nitro_charge_atom_indices(mol)
    charged_indices = {atom.GetIdx() for atom in charged}

    if not charged:
        representation_class = "no_formally_charged_atoms"
        review_flag = 0
        note = "No formally charged atoms in the canonical PubChem SMILES."
    elif molecular_net_charge != 0:
        representation_class = "net_charged_species"
        review_flag = 0
        note = "Net-charged species; calculation and PubChem net charges should be interpreted together."
    elif charged_indices and charged_indices <= nitro_indices:
        representation_class = "charge_separated_nitro_resonance_representation"
        review_flag = 0
        note = "Internal formal charges arise only from canonical nitro-group resonance notation."
    else:
        representation_class = "charge_separated_microspecies_requires_attention"
        review_flag = 1
        note = (
            "Net-neutral structure contains both positive and negative formal charges outside an "
            "exclusively nitro-resonance representation; treat it as a specified charge-separated "
            "microspecies, not as an unspecified neutral tautomer or protomer."
        )

    if molecular_net_charge != calculation_charge or molecular_net_charge != pubchem_net_charge:
        raise ValueError(
            f"Net-charge inconsistency for CID {cid}: RDKit={molecular_net_charge}, "
            f"calculation={calculation_charge}, PubChem={pubchem_net_charge}"
        )

    counts[representation_class] += 1
    output_rows.append(
        {
            "cid": cid,
            "pubchem_title": row["pubchem_Title"],
            "pubchem_smiles": smiles,
            "calculation_net_charge": calculation_charge,
            "pubchem_net_charge": pubchem_net_charge,
            "charged_atom_count": len(charged),
            "positive_formal_charge_atom_count": len(positive),
            "negative_formal_charge_atom_count": len(negative),
            "charge_separated_flag": int(charge_separated),
            "charge_representation_class": representation_class,
            "microspecies_review_flag": review_flag,
            "dipole_magnitude_debye": row["dipole_magnitude_debye"],
            "dipole_gt_5_debye_flag": int(float(row["dipole_magnitude_debye"]) > 5.0),
            "interpretation_note": note,
        }
    )

fieldnames = list(output_rows[0])
with OUTPUT.open("w", encoding="utf-8-sig", newline="") as handle:
    writer = csv.DictWriter(handle, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(output_rows)

charge_separated_rows = [row for row in output_rows if int(row["charge_separated_flag"]) == 1]
with SUPPLEMENT.open("w", encoding="utf-8-sig", newline="") as handle:
    writer = csv.DictWriter(handle, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(charge_separated_rows)

summary = {
    "records_audited": len(output_rows),
    "calculation_pubchem_rdkit_net_charge_mismatches": 0,
    "representation_class_counts": dict(sorted(counts.items())),
    "net_neutral_internal_formal_charge_records": len(charge_separated_rows),
    "nitro_resonance_only_records": sum(
        row["charge_representation_class"]
        == "charge_separated_nitro_resonance_representation"
        for row in charge_separated_rows
    ),
    "other_charge_separated_microspecies_records": sum(
        int(row["microspecies_review_flag"]) for row in output_rows
    ),
    "interpretation": (
        "Internal formal-charge separation is a molecular representation and microspecies "
        "attribute. It is not, by itself, evidence of a quantum-chemical calculation error."
    ),
    "table": OUTPUT.relative_to(ROOT).as_posix(),
    "table_sha256": hashlib.sha256(OUTPUT.read_bytes()).hexdigest(),
    "supplementary_table": SUPPLEMENT.relative_to(ROOT).as_posix(),
    "supplementary_table_sha256": hashlib.sha256(SUPPLEMENT.read_bytes()).hexdigest(),
}
SUMMARY.parent.mkdir(parents=True, exist_ok=True)
SUMMARY.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

print(f"records={len(output_rows)}")
for key, value in sorted(counts.items()):
    print(f"{key}={value}")
print(f"microspecies_review={sum(int(r['microspecies_review_flag']) for r in output_rows)}")
print(f"output={OUTPUT}")
print(f"supplementary_records={len(charge_separated_rows)}")
print(f"supplement={SUPPLEMENT}")
print(f"summary={SUMMARY}")
