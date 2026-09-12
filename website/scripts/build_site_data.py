#!/usr/bin/env python3
import csv
import json
import argparse
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

keep = {
    "cid": "cid",
    "pubchem_Title": "title",
    "molecular_formula": "formula",
    "pubchem_SMILES": "smiles",
    "pubchem_InChIKey": "inchiKey",
    "pubchem_MolecularWeight": "molecularWeight",
    "pubchem_ExactMass": "exactMass",
    "herb_count": "herbCount",
    "herb_names": "herbNames",
    "orca_version": "orcaVersion",
    "qc_status": "qcStatus",
    "review_reason": "reviewReason",
    "reviewed_warning_type": "warningType",
    "atom_count": "atomCount",
    "heavy_atom_count": "heavyAtomCount",
    "element_count": "elementCount",
    "electron_count": "electronCount",
    "charge": "charge",
    "multiplicity": "multiplicity",
    "molecular_mass_amu": "calculatedMassAmu",
    "normal_termination": "normalTermination",
    "optimization_converged": "optimizationConverged",
    "method_keywords": "methodKeywords",
    "basis": "basis",
    "final_electronic_energy_eh": "electronicEnergyEh",
    "zpe_eh": "zpeEh",
    "zpe_kcal_mol": "zpeKcalMol",
    "thermal_vibrational_correction_eh": "thermalVibrationalCorrectionEh",
    "thermal_rotational_correction_eh": "thermalRotationalCorrectionEh",
    "thermal_translational_correction_eh": "thermalTranslationalCorrectionEh",
    "total_thermal_correction_eh": "totalThermalCorrectionEh",
    "total_thermal_energy_eh": "totalThermalEnergyEh",
    "enthalpy_correction_eh": "enthalpyCorrectionEh",
    "total_enthalpy_eh": "enthalpyEh",
    "electronic_entropy_term_eh": "electronicEntropyTermEh",
    "vibrational_entropy_term_eh": "vibrationalEntropyTermEh",
    "rotational_entropy_term_eh": "rotationalEntropyTermEh",
    "translational_entropy_term_eh": "translationalEntropyTermEh",
    "final_entropy_term_eh": "finalEntropyTermEh",
    "final_entropy_term_kcal_mol": "finalEntropyTermKcalMol",
    "gibbs_correction_eh": "gibbsCorrectionEh",
    "final_gibbs_free_energy_eh": "gibbsEh",
    "homo_eh": "homoEh",
    "homo_ev": "homoEv",
    "lumo_eh": "lumoEh",
    "lumo_ev": "lumoEv",
    "homo_lumo_gap_eh": "gapEh",
    "homo_lumo_gap_ev": "gapEv",
    "dipole_x_au": "dipoleXAu",
    "dipole_y_au": "dipoleYAu",
    "dipole_z_au": "dipoleZAu",
    "dipole_magnitude_au": "dipoleMagnitudeAu",
    "dipole_magnitude_debye": "dipoleDebye",
    "rot_const_a_cm1": "rotConstACm1",
    "rot_const_b_cm1": "rotConstBCm1",
    "rot_const_c_cm1": "rotConstCCm1",
    "rot_const_a_mhz": "rotConstAMhz",
    "rot_const_b_mhz": "rotConstBMhz",
    "rot_const_c_mhz": "rotConstCMhz",
    "frequency_count": "frequencyCount",
    "imaginary_frequency_count": "imaginaryCount",
    "lowest_frequency_cm1": "lowestFrequencyCm1",
    "lowest_positive_frequency_cm1": "lowestPositiveFrequencyCm1",
    "highest_frequency_cm1": "highestFrequencyCm1",
    "ir_peak_count": "irPeakCount",
    "max_ir_intensity_km_mol": "maxIrIntensity",
    "runtime_seconds": "runtimeSeconds",
    "warning_count": "warningCount",
    "low_frequency_lt20_flag": "lowFrequencyLt20",
    "low_frequency_lt10_flag": "lowFrequencyLt10",
    "tiny_imaginary_frequency_flag": "tinyImaginaryFrequency",
    "high_warning_count_flag": "highWarningCount",
    "numerical_relations_pass": "numericalRelationsPass",
    "koopmans_ip_ev": "koopmansIpEv",
    "koopmans_ea_ev": "koopmansEaEv",
    "chemical_potential_ev": "chemicalPotentialEv",
    "electronegativity_ev": "electronegativityEv",
    "chemical_hardness_ev": "hardnessEv",
    "global_softness_ev_inv": "softnessEvInv",
    "electrophilicity_index_ev": "electrophilicityEv",
}

numeric = set(keep) - {
    "cid", "pubchem_Title", "molecular_formula", "pubchem_SMILES", "pubchem_InChIKey",
    "herb_names", "orca_version", "qc_status", "review_reason", "reviewed_warning_type",
    "method_keywords", "basis",
}

DERIVED = {'herb_count','herb_names','qc_status','review_reason','reviewed_warning_type',
           'low_frequency_lt20_flag','low_frequency_lt10_flag','tiny_imaginary_frequency_flag',
           'high_warning_count_flag','numerical_relations_pass','koopmans_ip_ev','koopmans_ea_ev',
           'chemical_potential_ev','electronegativity_ev','chemical_hardness_ev',
           'global_softness_ev_inv','electrophilicity_index_ev'}
EXTRA = {'pubchem_IUPACName':'iupacName','pubchem_XLogP':'xlogp','pubchem_TPSA':'tpsa',
         'pubchem_Complexity':'complexity','pubchem_HBondDonorCount':'hBondDonorCount',
         'pubchem_HBondAcceptorCount':'hBondAcceptorCount','pubchem_RotatableBondCount':'rotatableBondCount'}


def read_csv(path, required):
    with path.open(encoding='utf-8-sig', newline='') as handle:
        reader = csv.DictReader(handle)
        missing = set(required) - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f'{path}: missing columns {sorted(missing)}')
        rows = list(reader)
    if not rows:
        raise ValueError(f'{path}: empty input')
    return rows


def keyed(rows):
    result = {}
    for row in rows:
        cid = row['cid']
        if not cid.isdigit() or cid in result:
            raise ValueError(f'Invalid or duplicate CID: {cid}')
        result[cid] = row
    return result


def number(value, label, nullable=False):
    if value == '' and nullable:
        return None
    v = float(value)
    if not math.isfinite(v):
        raise ValueError(f'Non-finite {label}')
    return v


def build(source, provenance, closure):
    rows = read_csv(source, (set(keep)-DERIVED) | set(EXTRA))
    master = keyed(rows)
    pmap = keyed(read_csv(provenance, {'cid','herb_count','herb_names'}))
    if set(master) != set(pmap):
        raise ValueError('Master/provenance CID sets differ')
    # This flag is backed by the frozen audit, never assigned without evidence.
    checks = read_csv(closure, {'check','n_evaluable','n_pass','n_fail'})
    if len(checks) != 12 or len({r['check'] for r in checks}) != 12 or any(
        int(r['n_evaluable']) != len(rows) or int(r['n_pass']) != len(rows)
        or int(r['n_fail']) != 0 for r in checks
    ):
        raise ValueError('Expected 12 complete, passing frozen closure checks; re-audit before export')
    out = []
    for row in rows:
        cid = row['cid']
        for field in ['pubchem_SMILES','pubchem_InChIKey','molecular_formula']:
            if not row[field].strip():
                raise ValueError(f'{cid}: empty identity field {field}')
        item = {}
        for field, target in keep.items():
            if field in DERIVED:
                continue
            value = row[field]
            item[target] = number(value, field) if field in numeric else value
        for field, target in EXTRA.items():
            item[target] = row[field] if target == 'iupacName' else number(row[field], field, True)
        pr = pmap[cid]
        item['herbCount'] = int(pr['herb_count'])
        item['herbNames'] = pr['herb_names']
        if item['herbCount'] != len({n.strip() for n in pr['herb_names'].split('|') if n.strip()}):
            raise ValueError(f'{cid}: herb count/name mismatch')
        imag = item['imaginaryCount']
        item.update(qcStatus='review' if imag > 0 else 'pass',
                    reviewReason='微小负频率，建议复核' if imag > 0 else '',
                    warningType='tiny_imaginary_frequency' if imag > 0 else '',
                    lowFrequencyLt20=item['lowestPositiveFrequencyCm1'] < 20,
                    lowFrequencyLt10=item['lowestPositiveFrequencyCm1'] < 10,
                    tinyImaginaryFrequency=int(imag > 0),
                    highWarningCount=int(item['warningCount'] >= 10), numericalRelationsPass=1)
        h, l, gap = item['homoEv'], item['lumoEv'], item['gapEv']
        item.update(koopmansIpEv=-h, koopmansEaEv=-l, chemicalPotentialEv=(h+l)/2,
                    electronegativityEv=-(h+l)/2, hardnessEv=gap/2,
                    softnessEvInv=1/gap if gap else None,
                    electrophilicityEv=((h+l)/2)**2/gap if gap else None)
        out.append(item)
    return out


def main():
    tables = ROOT.parent / '02_数据发布包' / 'data_release' / 'tables'
    parser = argparse.ArgumentParser(description='Rebuild compounds from the frozen master and provenance, without an existing JSON.')
    parser.add_argument('--source', type=Path, default=tables/'tcm_qm_master.csv')
    parser.add_argument('--provenance', type=Path)
    parser.add_argument('--closure-summary', type=Path)
    parser.add_argument('--target', type=Path, default=ROOT/'app/data/compounds.json')
    args = parser.parse_args()
    out = build(args.source, args.provenance or args.source.parent/'cid_tcm_provenance_summary.csv',
                args.closure_summary or args.source.parent/'numerical_closure_summary.csv')
    args.target.parent.mkdir(parents=True, exist_ok=True)
    args.target.write_text(json.dumps(out, ensure_ascii=False, separators=(',', ':'), allow_nan=False), encoding='utf-8')
    print(f'wrote {len(out)} records to {args.target}')


if __name__ == '__main__':
    main()
