from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

UNITS = {
    "file_size_bytes": "byte", "molecular_mass_amu": "u",
    "final_electronic_energy_eh": "Eh", "zpe_eh": "Eh", "zpe_kcal_mol": "kcal mol-1",
    "thermal_vibrational_correction_eh": "Eh", "thermal_rotational_correction_eh": "Eh",
    "thermal_translational_correction_eh": "Eh", "total_thermal_correction_eh": "Eh",
    "total_thermal_energy_eh": "Eh", "enthalpy_correction_eh": "Eh", "total_enthalpy_eh": "Eh",
    "electronic_entropy_term_eh": "Eh", "vibrational_entropy_term_eh": "Eh",
    "rotational_entropy_term_eh": "Eh", "translational_entropy_term_eh": "Eh",
    "final_entropy_term_eh": "Eh", "final_entropy_term_kcal_mol": "kcal mol-1",
    "gibbs_correction_eh": "Eh", "final_gibbs_free_energy_eh": "Eh",
    "homo_eh": "Eh", "homo_ev": "eV", "lumo_eh": "Eh", "lumo_ev": "eV",
    "homo_lumo_gap_eh": "Eh", "homo_lumo_gap_ev": "eV",
    "dipole_x_au": "a.u.", "dipole_y_au": "a.u.", "dipole_z_au": "a.u.",
    "dipole_magnitude_au": "a.u.", "dipole_magnitude_debye": "D",
    "rot_const_a_cm1": "cm-1", "rot_const_b_cm1": "cm-1", "rot_const_c_cm1": "cm-1",
    "rot_const_a_mhz": "MHz", "rot_const_b_mhz": "MHz", "rot_const_c_mhz": "MHz",
    "lowest_frequency_cm1": "cm-1", "lowest_positive_frequency_cm1": "cm-1",
    "highest_frequency_cm1": "cm-1", "max_ir_intensity_km_mol": "km mol-1",
    "runtime_seconds": "s", "pubchem_MolecularWeight": "g mol-1",
    "pubchem_ExactMass": "Da", "pubchem_MonoisotopicMass": "Da", "pubchem_TPSA": "A2",
}

TYPE_OVERRIDES = {"cid": "string", "pubchem_CID": "string"}

DESCRIPTIONS = {
    "cid": "Primary record key; PubChem Compound identifier stored as text.",
    "source_file": "Archived ORCA output filename used for extraction.",
    "orca_version": "ORCA program version reported by the calculation.",
    "normal_termination": "1 when the ORCA normal-termination marker is present; otherwise 0.",
    "optimization_converged": "1 when the geometry-optimization convergence marker is present; otherwise 0.",
    "method_keywords": "ORCA simple-input keyword line preserved from the archived calculation.",
    "basis": "Parsed orbital basis-set label.", "charge": "Net molecular charge used in the calculation.",
    "multiplicity": "Spin multiplicity used in the calculation.",
    "molecular_formula": "Formula derived from the calculated atom list; formal charge is stored separately.",
    "electron_count": "Integrated ORCA electron count; small non-integer deviations reflect numerical precision.",
    "final_electronic_energy_eh": "Last final single-point electronic energy from the converged calculation.",
    "warning_count": "Total parsed ORCA warning occurrences; repeated messages are counted, not unique warning types.",
    "pubchem_CID": "CID returned by the frozen PubChem metadata snapshot.",
    "pubchem_SMILES": "PubChem SMILES from the frozen metadata snapshot.",
    "pubchem_ConnectivitySMILES": "PubChem connectivity SMILES used for connectivity-grouped splitting.",
    "pubchem_InChI": "PubChem International Chemical Identifier.",
    "pubchem_InChIKey": "PubChem full InChIKey used for exact-identity uniqueness checks.",
    "file_size_bytes": "Byte size of the archived source OUT file; an integrity/provenance field, not a molecular descriptor.",
    "atom_count": "Number of atoms, including hydrogen, in the calculated Cartesian atom list.",
    "heavy_atom_count": "Number of non-hydrogen atoms in the calculated Cartesian atom list.",
    "element_count": "Number of distinct chemical elements in the calculated atom list.",
    "molecular_mass_amu": "Molecular mass calculated from the ORCA atom list in unified atomic mass units; not the PubChem average molecular weight.",
    "zpe_eh": "Zero-point vibrational energy from the final harmonic-frequency analysis.",
    "zpe_kcal_mol": "Zero-point vibrational energy converted from hartree to kcal mol-1.",
    "thermal_vibrational_correction_eh": "Finite-temperature vibrational contribution to the thermal-energy correction at 298.15 K.",
    "thermal_rotational_correction_eh": "Rotational contribution to the thermal-energy correction at 298.15 K.",
    "thermal_translational_correction_eh": "Translational contribution to the thermal-energy correction at 298.15 K.",
    "total_thermal_correction_eh": "Sum of zero-point and finite-temperature thermal corrections used by ORCA.",
    "total_thermal_energy_eh": "Final electronic energy plus the total thermal-energy correction at 298.15 K.",
    "enthalpy_correction_eh": "Thermal enthalpy correction at 298.15 K and 1 atm.",
    "total_enthalpy_eh": "Final electronic energy plus the enthalpy correction at 298.15 K and 1 atm; do not rank across different stoichiometries as a stability score.",
    "electronic_entropy_term_eh": "Electronic contribution to T*S reported by ORCA at 298.15 K.",
    "vibrational_entropy_term_eh": "Vibrational contribution to T*S using ORCA QRRHO treatment with a 100 cm-1 reference frequency.",
    "rotational_entropy_term_eh": "Rotational contribution to T*S at 298.15 K and 1 atm.",
    "translational_entropy_term_eh": "Translational contribution to T*S at 298.15 K and 1 atm.",
    "final_entropy_term_eh": "Total T*S term reported by ORCA, expressed as energy in hartree rather than entropy per kelvin.",
    "final_entropy_term_kcal_mol": "Total T*S term converted to kcal mol-1; this is not an entropy value in cal mol-1 K-1.",
    "gibbs_correction_eh": "Thermal Gibbs free-energy correction at 298.15 K and 1 atm.",
    "final_gibbs_free_energy_eh": "Final electronic energy plus the Gibbs correction; a gas-phase within-protocol quantity not directly comparable across different stoichiometries.",
    "homo_eh": "Highest occupied Kohn-Sham orbital energy from the final orbital-energy block.",
    "homo_ev": "Highest occupied Kohn-Sham orbital energy converted to electronvolt.",
    "lumo_eh": "Lowest unoccupied Kohn-Sham orbital energy from the final orbital-energy block.",
    "lumo_ev": "Lowest unoccupied Kohn-Sham orbital energy converted to electronvolt.",
    "homo_lumo_gap_eh": "LUMO minus HOMO Kohn-Sham orbital-energy difference in hartree; not an experimental optical or quasiparticle gap.",
    "homo_lumo_gap_ev": "LUMO minus HOMO Kohn-Sham orbital-energy difference in eV; not an experimental optical or quasiparticle gap.",
    "dipole_x_au": "Cartesian x component of the gas-phase molecular dipole in atomic units; orientation dependent.",
    "dipole_y_au": "Cartesian y component of the gas-phase molecular dipole in atomic units; orientation dependent.",
    "dipole_z_au": "Cartesian z component of the gas-phase molecular dipole in atomic units; orientation dependent.",
    "dipole_magnitude_au": "Rotation-invariant magnitude of the gas-phase molecular dipole in atomic units.",
    "dipole_magnitude_debye": "Rotation-invariant magnitude of the gas-phase molecular dipole in debye; not a solution-phase measurement.",
    "rot_const_a_cm1": "Principal rotational constant A in reciprocal centimetres from the optimized geometry.",
    "rot_const_b_cm1": "Principal rotational constant B in reciprocal centimetres from the optimized geometry.",
    "rot_const_c_cm1": "Principal rotational constant C in reciprocal centimetres from the optimized geometry.",
    "rot_const_a_mhz": "Principal rotational constant A in MHz from the optimized geometry.",
    "rot_const_b_mhz": "Principal rotational constant B in MHz from the optimized geometry.",
    "rot_const_c_mhz": "Principal rotational constant C in MHz from the optimized geometry.",
    "frequency_count": "Number of parsed harmonic vibrational modes in the final frequency block.",
    "imaginary_frequency_count": "Number of parsed negative harmonic frequencies; use zero to construct the strict positive-curvature subset.",
    "lowest_frequency_cm1": "Lowest signed harmonic frequency; negative values denote retained imaginary modes.",
    "lowest_positive_frequency_cm1": "Smallest strictly positive harmonic frequency.",
    "highest_frequency_cm1": "Largest parsed harmonic vibrational frequency.",
    "ir_peak_count": "Number of parsed modes with an IR-intensity entry in the final spectrum block.",
    "max_ir_intensity_km_mol": "Maximum parsed harmonic IR intensity among the reported modes.",
    "runtime_seconds": "Elapsed wall-clock runtime reported by ORCA; depends on hardware, process count, system load and software version.",
    "pubchem_Title": "PubChem record title from the frozen metadata snapshot; optional and not used as the primary key.",
    "pubchem_IUPACName": "PubChem IUPAC name from the frozen metadata snapshot.",
    "pubchem_MolecularFormula": "Molecular formula returned by PubChem, including formal-charge notation when supplied.",
    "pubchem_MolecularWeight": "Average molecular weight returned by PubChem.",
    "pubchem_ExactMass": "Exact mass returned by PubChem.",
    "pubchem_MonoisotopicMass": "Monoisotopic mass returned by PubChem.",
    "pubchem_Charge": "Formal charge returned by PubChem and used for identity-consistency auditing.",
    "pubchem_XLogP": "PubChem XLogP annotation from the frozen snapshot; optional and not imputed.",
    "pubchem_TPSA": "PubChem topological polar surface area in square angstroms.",
    "pubchem_Complexity": "PubChem complexity score; use as a database annotation, not a quantum-chemical descriptor.",
    "pubchem_HBondDonorCount": "Hydrogen-bond donor count returned by PubChem.",
    "pubchem_HBondAcceptorCount": "Hydrogen-bond acceptor count returned by PubChem.",
    "pubchem_RotatableBondCount": "Rotatable-bond count returned by PubChem.",
    "pubchem_HeavyAtomCount": "Heavy-atom count returned by PubChem for identity and consistency checks.",
}

def infer_type(values: list[str]) -> str:
    values = [v for v in values if v != ""]
    if not values: return "string"
    try: [int(v) for v in values]; return "integer"
    except ValueError: pass
    try: [float(v) for v in values]; return "number"
    except ValueError: return "string"

def origin(field: str) -> str:
    if field.startswith("pubchem_"): return "PubChem frozen metadata snapshot"
    if field in {"cid", "source_file", "file_size_bytes"}: return "release assembly"
    if field in {"atom_count", "heavy_atom_count", "element_count", "molecular_formula"}:
        return "derived from ORCA Cartesian atom list"
    if field in {"homo_lumo_gap_eh", "homo_lumo_gap_ev", "dipole_magnitude_au"}:
        return "derived from parsed ORCA values"
    return "parsed from ORCA output"

def build(master: Path, csv_output: Path, json_output: Path) -> None:
    with master.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    fields = list(rows[0]); dictionary = []
    for position, field in enumerate(fields, 1):
        values = [(row.get(field) or "").strip() for row in rows]
        missing = sum(v == "" for v in values); field_type = TYPE_OVERRIDES.get(field, infer_type(values))
        dictionary.append({
            "position": position, "field": field, "type": field_type,
            "unit": UNITS.get(field, "dimensionless" if field_type != "string" else "not applicable"),
            "origin": origin(field), "required": not field.startswith("pubchem_") or missing == 0,
            "missing_count": missing,
            "missing_value_rule": "empty CSV cell; no imputation" if missing else "not missing in release 1.1.0-rc1",
            "description": DESCRIPTIONS.get(field, field.replace("pubchem_", "PubChem ").replace("_", " ").capitalize() + "."),
        })
    csv_output.parent.mkdir(parents=True, exist_ok=True)
    with csv_output.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(dictionary[0])); writer.writeheader(); writer.writerows(dictionary)
    schema = {"title": "TCM-QM master-table schema", "release_version": "1.1.0-rc1",
              "records": len(rows), "fields": len(fields),
              "missing_values": "Empty CSV cells denote unavailable optional metadata; values are not imputed.",
              "columns": dictionary}
    json_output.write_text(json.dumps(schema, ensure_ascii=False, indent=2), encoding="utf-8")

def main() -> None:
    parser = argparse.ArgumentParser(description="Generate the TCM-QM field dictionary and JSON schema.")
    parser.add_argument("master", type=Path); parser.add_argument("csv_output", type=Path); parser.add_argument("json_output", type=Path)
    args = parser.parse_args(); build(args.master, args.csv_output, args.json_output)

if __name__ == "__main__": main()
