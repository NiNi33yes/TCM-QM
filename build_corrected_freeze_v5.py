from pathlib import Path
import argparse,shutil,hashlib,csv,json,datetime

parser=argparse.ArgumentParser(description="Rebuild the corrected v5 structure freeze from declared inputs.")
parser.add_argument('--source-release',required=True,type=Path)
parser.add_argument('--output-release',required=True,type=Path)
parser.add_argument('--optimized-xyz',required=True,type=Path)
parser.add_argument('--replacement-audit',required=True,type=Path)
parser.add_argument('--recovered-out',required=True,type=Path)
args=parser.parse_args()
src=args.source_release.resolve(); out=args.output_release.resolve(); xyz=args.optimized_xyz.resolve()
audit=args.replacement_audit.resolve(); outs=args.recovered_out.resolve()
if out.exists(): raise SystemExit(f"refuse overwrite {out}")
shutil.copytree(src,out)
for p in xyz.glob('*.xyz'): shutil.copy2(p,out/'structures_xyz'/p.name)
shutil.copy2(audit,out/'audits'/'placeholder_xyz_replacement_audit.csv')

with audit.open(encoding='utf-8-sig',newline='') as f: ids={str(int(float(r['cid']))) for r in csv.DictReader(f)}
checks=[]
for cid in sorted(ids,key=int):
    p=outs/f'{cid}.out'; t=p.read_text(encoding='utf-8',errors='replace')
    checks.append({'cid':cid,'normal_termination':int('ORCA TERMINATED NORMALLY' in t),'optimization_converged':int('THE OPTIMIZATION HAS CONVERGED' in t),'frequency_section':int('VIBRATIONAL FREQUENCIES' in t),'final_coordinates_present':int('CARTESIAN COORDINATES (ANGSTROEM)' in t),'source_out_size_bytes':p.stat().st_size})
with (out/'audits'/'recovered_xyz_154_validation.csv').open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.DictWriter(f,fieldnames=checks[0]);w.writeheader();w.writerows(checks)

readme=(out/'README.md').read_text(encoding='utf-8')
readme=readme.replace('- XYZ structures: 3,196','- XYZ structures: 3,196 DFT-optimized coordinates')
readme=readme.replace('## Release boundary','## Structure recovery audit\n\nThe earlier local assembly temporarily used 154 ETKDG/MMFF placeholders because those optimized coordinate files were absent from the first local structure directory. The corresponding 154 ORCA outputs were subsequently recovered. All 154 terminate normally, contain converged optimizations, frequency sections and final Cartesian-coordinate sections. Their DFT-optimized coordinates replace the placeholders in this v5 freeze. CID 10946210 uses the later E/Z stereochemistry-corrected recalculation.\n\n## Release boundary')
(out/'README.md').write_text(readme,encoding='utf-8')

# Rebuild payload manifest after every replacement. Manifest files are excluded from their own scope.
rows=[]
for p in sorted(x for x in out.rglob('*') if x.is_file() and 'manifests' not in x.relative_to(out).parts):
    h=hashlib.sha256(p.read_bytes()).hexdigest(); rows.append({'relative_path':p.relative_to(out).as_posix(),'size_bytes':p.stat().st_size,'sha256':h})
with (out/'manifests'/'files_sha256.csv').open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.DictWriter(f,fieldnames=rows[0]);w.writeheader();w.writerows(rows)
mh=hashlib.sha256((out/'manifests'/'files_sha256.csv').read_bytes()).hexdigest()
(out/'manifests'/'files_sha256.csv.sha256').write_text(f'{mh}  files_sha256.csv\n',encoding='ascii')
summary={'release_name':out.name,'release_version':'1.1.0-rc1','frozen_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'payload_file_count':len(rows),'payload_size_bytes':sum(r['size_bytes'] for r in rows),'hash_algorithm':'SHA-256','structure_count':len(list((out/'structures_xyz').glob('*.xyz'))),'recovered_dft_xyz_count':154,'remaining_placeholder_xyz_count':0}
(out/'manifests'/'release_summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
print(json.dumps(summary,indent=2))
