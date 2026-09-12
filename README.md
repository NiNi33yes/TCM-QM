# TCM-QM code

Version 1.1.2 contains the parsing, reconstruction, provenance-audit, validation, figure-generation and machine-learning utilities used for the provenance-corrected TCM-QM data release, together with the complete TCM-QM Atlas website source. Version 1.1.2 does not change the molecular dataset.

The corresponding data release contains 3,196 PubChem-indexed molecular records calculated at the B3LYP-D3BJ/def2-TZVP level with ORCA 6.0.1 or 6.1.1. The code is licensed under the MIT License. ORCA binaries and third-party datasets are not redistributed by this repository.

## Environment

Create the pinned Python 3.11 environment:

```bash
conda env create -f environment.yml
conda activate tcm-qm-release
```

The environment includes NumPy, pandas, SciPy, scikit-learn, statsmodels, matplotlib, RDKit, NetworkX and openpyxl. ORCA is required only for new quantum-chemical calculations, not for inspecting the frozen release or rerunning table-level audits.

## Main commands

```bash
python parse_orca_out.py RAW_OUT_DIRECTORY PARSED_OUTPUT_DIRECTORY

python generate_data_dictionary.py DATA_RELEASE/tables/tcm_qm_master.csv rebuilt/data_dictionary.csv rebuilt/schema.json

python build_ml_benchmark.py DATA_RELEASE/tables/tcm_qm_master.csv rebuilt/machine_learning
python -m unittest test_build_ml_benchmark.py

python build_figures_v1_1.py DATA_RELEASE rebuilt/figures --vector-output-dir rebuilt/figures_vector
```

See `REPRODUCIBILITY.md` and `REBUILD_PROTOCOL.md` for inputs, boundaries and reconstruction checks.

## Web application

The complete source of the public TCM-QM Atlas is provided in `website/`. It includes the searchable compound catalogue, molecular detail pages, 2D and 3D structure viewers, the evidence-aware herb–compound graph, download surfaces, data-generation scripts and regression tests.

The web application requires Node.js 22.13.0 or newer:

```bash
cd website
npm install
npm run lint
npm test
```

The bundled website data correspond to the provenance-corrected `v1.1.0-rc1` candidate data freeze: 3,196 compounds, 495 herb entities, 16,918 unique herb–CID edges and 16,930 accepted source-evidence rows. Herb–compound edges represent documented TCMSP source associations and must not be interpreted as evidence of efficacy, abundance, exposure or target engagement.

## Code map

- `parse_orca_out.py` extracts released ORCA fields and calculation flags.
- `build_master.py` assembles the CID-indexed master table from parsed calculations and a frozen PubChem table.
- `build_finalization_audit.py` reconstructs selection decisions from supplied source ledgers.
- `verify_rebuild.py` compares reconstructed output with the frozen release.
- `generate_data_dictionary.py` builds the field dictionary and JSON schema.
- `audit_all_initial_geometries_pubchem3d.py` and `analyze_full_initial_geometry_audit.py` implement the PubChem3D starting-geometry audit.
- `build_ionization_state_audit.py` classifies internally charge-separated SMILES representations.
- `integrate_nist_cccbdb_validation.py` rebuilds the NIST CCCBDB dipole-validation artifacts from deposited audit inputs.
- `build_ml_benchmark.py`, `scaffold_split_uncertainty.py` and `build_fig6_r2_comparison.py` implement the reuse benchmark.
- `select_conformer_sample.py`, `generate_conformers.py` and `compare_conformers.py` support conformer-sensitivity analysis.
- `select_orca_version_paired_sample.py`, `rebuild_orca_input.py` and `compare_orca_versions.py` support a paired ORCA-version study; the released dataset does not claim that this study was completed.
- `build_figures_v1_1.py` rebuilds the current data-driven manuscript figures.
- `refresh_release_manifest.py` creates SHA-256 payload manifests.
- `website/` contains the complete TCM-QM Atlas source, static molecular structures, machine-readable downloads and website-specific tests.

`build_corrected_freeze_v5.py` is retained only as provenance for the historical recovery of 154 XYZ files. It is not the supported release-building entry point. `build_fig6_r2_comparison.py` summarizes the deposited run-level machine-learning results and is used by the current figure workflow; it is not a superseded copy of `build_figures_v1_1.py`.

## Reproducibility boundary

Exact reconstruction requires the inputs named in `REBUILD_PROTOCOL.md`, including archived ORCA outputs, frozen PubChem metadata and the source ledgers used for selection and provenance adjudication. The data release records which upstream artifacts are deposited and which remain unavailable. A successful checksum comparison establishes file identity; it does not establish experimental accuracy, conformer completeness or interchangeability between ORCA versions.

## Versioning

- `v1.0.0` corresponds to the initial public code archive.
- `v1.1.0` corresponds to the provenance-corrected data-processing and validation code described here.
- `v1.1.1` corrects Figure 1 so that connected stages all use calculation-record counts (6,948 to 4,012 to 3,196); it makes no change to the released molecular records or provenance edges.
- `v1.1.2` adds the complete, tested TCM-QM Atlas website source and its static research-data surfaces; it makes no change to the released molecular records or provenance edges.

Use the immutable tagged release or its archived software DOI in reproducible work rather than the moving `main` branch.
