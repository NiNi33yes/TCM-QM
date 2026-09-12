# Reproducibility guide

This release candidate separates scripts that can be rerun from the frozen tables from
historical assembly scripts that require source ledgers or raw ORCA outputs.

## Environment

Create the declared environment with `conda env create -f environment.yml`. ORCA itself
is not redistributed. Re-parsing requires access to the archived `.out` files and a
licensed/local ORCA installation is required only for new quantum-chemical calculations.

## Commands using frozen or externally supplied inputs

```text
python generate_data_dictionary.py tables/tcm_qm_master.csv tables/data_dictionary.csv tables/schema.json
python parse_orca_out.py RAW_OUT_DIRECTORY PARSED_OUTPUT_DIRECTORY
python build_ml_benchmark.py tables/tcm_qm_master.csv machine_learning_rebuilt
python -m unittest test_build_ml_benchmark.py
python audit_all_initial_geometries_pubchem3d.py PROJECT_ROOT
python build_figures_v1_1.py DATA_RELEASE rebuilt/figures --vector-output-dir rebuilt/figures_vector
```

`build_finalization_audit.py --help` lists all required source ledgers and paths. It no
longer contains machine-specific `D:\` defaults. The historical v5 correction script is
retained as provenance for the 154 recovered XYZ replacements; it is not the supported
entry point for a new release.

The Figure 1 generator asserts both released selection identities before plotting:
6,948 - 4,012 = 2,936 quality exclusions and 4,012 - 3,196 = 816 qualified-record
deduplications. The 6,106 normalized unique CIDs are reported separately because a
unique-CID count cannot be subtracted from a calculation-record count.

## Reproducibility boundary

The current package supports inspection of the frozen tables and rerunning the included
dictionary, ML and audit logic when their declared inputs are supplied. It does not embed
every upstream candidate-selection input. A complete 3,196-file OUT archive has been
assembled and checksum-verified with SHA-256 digest
`c24933581aa93112b64ebbe33768b8cd6c5bcd8ac509c5079bece87097ff08bf`;
repository deposition remains pending. The published 6,948-row decision ledger supports
verification of selection arithmetic and final membership, but the earlier process that
created the candidate inventory is outside the recoverable archive. A clean end-to-end
rebuild from the deposited OUT archive to the published master hash has not yet been
recorded and must not be claimed as completed until the rebuild evidence is available.
