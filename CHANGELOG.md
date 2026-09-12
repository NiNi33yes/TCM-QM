# Changelog

All notable changes to the public TCM-QM processing and validation code are documented here.

## v1.1.1 — 2026-09-12

### Corrected

- Corrected Figure 1 to use calculation-record counts consistently across its connected selection stages: 6,948 candidate records, 4,012 quality-qualified records and 3,196 released records.
- Corrected the quality-adjudication reduction to 2,936 records and the qualified-record deduplication reduction to 816 records. The 6,106 normalized unique CIDs remain a separately reported identity count and are no longer subtracted from a calculation-record count.

### Scope

- No molecular record, quantum-chemical value, XYZ structure, TCMSP provenance record or herb–CID edge was changed.
- Version 1.1.1 updates code and documentation only; the v1.1.0 tag remains available as historical provenance.

## v1.1.0 — 2026-09-10

This code release accompanies the provenance-corrected TCM-QM data release v1.1.0.

### Added

- Full-library PubChem3D starting-geometry audit and summary analysis.
- Record-level ionization-state audit for internally charge-separated SMILES.
- NIST CCCBDB dipole-validation integration.
- Conformer-sensitivity sampling, generation and comparison utilities.
- Scaffold-split uncertainty analysis for the machine-learning reuse benchmark.
- ORCA-version paired-study selection, input reconstruction and comparison utilities.
- Current manuscript figure generator with explicit input and output paths.
- Reconstruction, reproducibility and validation protocols.

### Changed

- Updated all public processing scripts to the versions deposited with data release v1.1.0.
- Standardized the documented runtime on Python 3.11 and pinned the release environment.
- Clarified the reproducibility boundary between executable processing code, archived ORCA outputs, frozen upstream metadata and adjudicated provenance ledgers.
- Updated documentation to distinguish the moving `main` branch from immutable version tags.

### Removed

- Superseded v1.0.0 figure scripts that no longer reproduce the current manuscript figures.

### Data-release facts represented by v1.1.0

- 3,196 unique PubChem CIDs.
- 16,930 accepted TCMSP evidence rows and 16,918 deduplicated CID–herb edges.
- 382 legacy-only relations excluded from the primary graph by the frozen adjudication policy.
- Nine CIDs retaining multiple TCMSP MOL_ID source records.

The accepted edge set is defined by the deposited v1.1.0 tables and adjudication ledgers. This software release does not redistribute TCMSP or PubChem source snapshots and must not be interpreted as independently relicensing those third-party records.

## v1.0.0

Initial public release of the TCM-QM processing code.
