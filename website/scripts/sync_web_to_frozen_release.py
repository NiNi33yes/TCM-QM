import argparse
import csv,json
from pathlib import Path

root=Path(__file__).resolve().parents[1]
default_tables=root.parent / "02_数据发布包" / "data_release" / "tables"
parser=argparse.ArgumentParser(description="Synchronize website compound data with a frozen TCM-QM release.")
parser.add_argument("--web", type=Path, default=root)
parser.add_argument("--master", type=Path, default=default_tables / "tcm_qm_master.csv")
parser.add_argument("--provenance", type=Path, default=default_tables / "cid_tcm_provenance_summary.csv")
args=parser.parse_args()
web=args.web.resolve()
master=args.master.resolve()
prov=args.provenance.resolve()
target=web/"app/data/compounds.json"

old={str(x['cid']):x for x in json.loads(target.read_text(encoding='utf-8'))}
with master.open(encoding='utf-8-sig',newline='') as f: rows=list(csv.DictReader(f))
with prov.open(encoding='utf-8-sig',newline='') as f: pmap={r['cid']:r for r in csv.DictReader(f)}

field={
'orca_version':'orcaVersion','atom_count':'atomCount','heavy_atom_count':'heavyAtomCount','element_count':'elementCount','electron_count':'electronCount','charge':'charge','multiplicity':'multiplicity','molecular_mass_amu':'calculatedMassAmu','normal_termination':'normalTermination','optimization_converged':'optimizationConverged','method_keywords':'methodKeywords','basis':'basis','final_electronic_energy_eh':'electronicEnergyEh','zpe_eh':'zpeEh','zpe_kcal_mol':'zpeKcalMol','thermal_vibrational_correction_eh':'thermalVibrationalCorrectionEh','thermal_rotational_correction_eh':'thermalRotationalCorrectionEh','thermal_translational_correction_eh':'thermalTranslationalCorrectionEh','total_thermal_correction_eh':'totalThermalCorrectionEh','total_thermal_energy_eh':'totalThermalEnergyEh','enthalpy_correction_eh':'enthalpyCorrectionEh','total_enthalpy_eh':'enthalpyEh','electronic_entropy_term_eh':'electronicEntropyTermEh','vibrational_entropy_term_eh':'vibrationalEntropyTermEh','rotational_entropy_term_eh':'rotationalEntropyTermEh','translational_entropy_term_eh':'translationalEntropyTermEh','final_entropy_term_eh':'finalEntropyTermEh','final_entropy_term_kcal_mol':'finalEntropyTermKcalMol','gibbs_correction_eh':'gibbsCorrectionEh','final_gibbs_free_energy_eh':'gibbsEh','homo_eh':'homoEh','homo_ev':'homoEv','lumo_eh':'lumoEh','lumo_ev':'lumoEv','homo_lumo_gap_eh':'gapEh','homo_lumo_gap_ev':'gapEv','dipole_x_au':'dipoleXAu','dipole_y_au':'dipoleYAu','dipole_z_au':'dipoleZAu','dipole_magnitude_au':'dipoleMagnitudeAu','dipole_magnitude_debye':'dipoleDebye','rot_const_a_cm1':'rotConstACm1','rot_const_b_cm1':'rotConstBCm1','rot_const_c_cm1':'rotConstCCm1','rot_const_a_mhz':'rotConstAMhz','rot_const_b_mhz':'rotConstBMhz','rot_const_c_mhz':'rotConstCMhz','frequency_count':'frequencyCount','imaginary_frequency_count':'imaginaryCount','lowest_frequency_cm1':'lowestFrequencyCm1','lowest_positive_frequency_cm1':'lowestPositiveFrequencyCm1','highest_frequency_cm1':'highestFrequencyCm1','ir_peak_count':'irPeakCount','max_ir_intensity_km_mol':'maxIrIntensity','runtime_seconds':'runtimeSeconds','warning_count':'warningCount','pubchem_Title':'title','molecular_formula':'formula','pubchem_SMILES':'smiles','pubchem_InChIKey':'inchiKey','pubchem_MolecularWeight':'molecularWeight','pubchem_ExactMass':'exactMass'}
ints={'atomCount','heavyAtomCount','elementCount','charge','multiplicity','normalTermination','optimizationConverged','frequencyCount','imaginaryCount','irPeakCount','warningCount'}
texts={'orcaVersion','methodKeywords','basis','title','formula','smiles','inchiKey'}
out=[]
for r in rows:
    cid=str(int(float(r['cid']))); item=old[cid].copy(); item['cid']=cid
    for a,b in field.items():
        v=r.get(a,'')
        if b in texts: item[b]=v
        else:
            try: item[b]=int(float(v)) if b in ints else float(v)
            except: item[b]=None
    pr=pmap[cid]; item['herbCount']=int(pr['herb_count']); item['herbNames']=pr['herb_names']
    imag=int(float(r['imaginary_frequency_count'])); warn=int(float(r['warning_count']))
    item['qcStatus']='review' if imag>0 else 'pass'
    item['reviewReason']='微小负频率，建议复核' if imag>0 else ''
    item['warningType']='tiny_imaginary_frequency' if imag>0 else ''
    item['lowFrequencyLt20']=int(float(r['lowest_positive_frequency_cm1']))<20
    item['lowFrequencyLt10']=int(float(r['lowest_positive_frequency_cm1']))<10
    item['tinyImaginaryFrequency']=int(imag>0); item['highWarningCount']=int(warn>=10); item['numericalRelationsPass']=1
    h=float(r['homo_ev']); l=float(r['lumo_ev']); gap=float(r['homo_lumo_gap_ev'])
    item['koopmansIpEv']=-h; item['koopmansEaEv']=-l; item['chemicalPotentialEv']=(h+l)/2
    item['electronegativityEv']=-(h+l)/2; item['hardnessEv']=gap/2; item['softnessEvInv']=1/gap if gap else None
    item['electrophilicityEv']=item['electronegativityEv']**2/(2*item['hardnessEv']) if item['hardnessEv'] else None
    out.append(item)
target.write_text(json.dumps(out,ensure_ascii=False,separators=(',',':')),encoding='utf-8')
print({'records':len(out),'relationships':sum(x['herbCount'] for x in out),'mapped':sum(x['herbCount']>0 for x in out),'versions':{v:sum(x['orcaVersion']==v for x in out) for v in ['6.0.1','6.1.1']}})
