# TCM-QM code

Parsing, reconstruction, provenance-audit and benchmark code for the TCM-QM quantum-chemical dataset (3,196 PubChem-indexed compounds, B3LYP-D3BJ/def2-TZVP, ORCA 6.0.1 / 6.1.1).

## Contents

- `parse_orca_out.py` - ORCA output parser (record-level fields, flags, versions).
- `build_master.py` - master-table assembly from parsed records.
- `verify_rebuild.py` - full-chain reconstruction verification (see REBUILD_PROTOCOL.md in the data release).
- `generate_data_dictionary.py` - field-level data dictionary and JSON schema generator.
- `build_figures.py` - Fig. 1-5 and Fig. 7.
- `build_fig6_r2_comparison.py` - Fig. 6 (machine-learning readiness).
- `build_ml_benchmark.py` / `scaffold_split_uncertainty.py` - leakage-controlled ML benchmark (RDKit descriptors, grouped-connectivity and Bemis-Murcko scaffold splits).
- `audit_all_initial_geometries_pubchem3d.py` / `analyze_full_initial_geometry_audit.py` - PubChem3D starting-geometry provenance audit.
- `select_orca_version_paired_sample.py` / `compare_orca_versions.py` / `rebuild_orca_input.py` - ORCA-version stratification and input reconstruction.
- `refresh_release_manifest.py` - SHA-256 release manifest generation.
- `select_conformer_sample.py` / `generate_conformers.py` / `compare_conformers.py` - conformer-sensitivity utilities.

## Environment

Python 3.9; dependencies in `environment.yml` (pandas, numpy, matplotlib, rdkit).

## License

MIT - see `LICENSE_MIT.txt`.
