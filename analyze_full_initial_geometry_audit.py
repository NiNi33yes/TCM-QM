#!/usr/bin/env python3
"""Summarize the full TCM-QM ORCA-input versus PubChem3D audit.

Run after downloading initial_geometry_pubchem3d_full_results.csv.  The script
does not modify the source CSV and writes all derived files to a new directory.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from statistics import median


def number(value: str | None) -> float | None:
    try:
        result = float(value or "")
        return result if math.isfinite(result) else None
    except (TypeError, ValueError):
        return None


def first_present(row: dict[str, str], names: tuple[str, ...]) -> str:
    for name in names:
        if row.get(name, "").strip():
            return row[name].strip()
    return ""


def rmsd_of(row: dict[str, str]) -> float | None:
    return number(first_present(row, (
        "rmsd_angstrom", "heavy_atom_rmsd_angstrom", "direct_order_rmsd_angstrom",
        "rmsd", "kabsch_rmsd_angstrom",
    )))


def classification_of(row: dict[str, str], rmsd: float | None) -> str:
    existing = first_present(row, ("classification", "comparison_class", "status"))
    if existing:
        return existing
    if rmsd is None:
        return "not_comparable"
    if rmsd <= 0.02:
        return "coordinate_identity_consistent"
    if rmsd <= 0.20:
        return "same_geometry_with_minor_relaxation"
    if rmsd <= 0.75:
        return "same_or_similar_conformer"
    return "different_conformer_or_source"


def percentile(values: list[float], q: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    pos = (len(ordered) - 1) * q
    lo, hi = math.floor(pos), math.ceil(pos)
    if lo == hi:
        return ordered[lo]
    return ordered[lo] * (hi - pos) + ordered[hi] * (pos - lo)


def write_csv(path: Path, rows: list[dict], fields: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("results_csv", type=Path)
    parser.add_argument("output_directory", type=Path)
    args = parser.parse_args()

    with args.results_csv.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        raise SystemExit("No audit records found")

    output = args.output_directory
    output.mkdir(parents=True, exist_ok=True)
    classes = Counter()
    version_classes: dict[str, Counter] = defaultdict(Counter)
    comparable: list[tuple[dict[str, str], float]] = []
    review_rows: list[dict[str, str | float]] = []

    for row in rows:
        rmsd = rmsd_of(row)
        cls = classification_of(row, rmsd)
        classes[cls] += 1
        version = first_present(row, ("orca_version", "version")) or "unknown"
        version_classes[version][cls] += 1
        if rmsd is not None:
            comparable.append((row, rmsd))
        if cls in {
            "requires_graph_mapping", "different_conformer_or_source",
            "pubchem_3d_unavailable", "processing_error", "not_comparable",
        } or (rmsd is not None and rmsd > 0.20):
            review_rows.append({
                "cid": first_present(row, ("cid", "CID")),
                "orca_version": version,
                "rmsd_angstrom": "" if rmsd is None else f"{rmsd:.6f}",
                "classification": cls,
                "source_file": first_present(row, ("source_file", "source_out")),
                "error_or_note": first_present(row, ("error", "note", "message")),
            })

    values = [value for _, value in comparable]
    exact = sum(value <= 1e-6 for value in values)
    summary = {
        "records": len(rows),
        "unique_cids": len({first_present(r, ("cid", "CID")) for r in rows}),
        "comparable_records": len(values),
        "exact_to_1e_6_angstrom": exact,
        "rmsd_median_angstrom": percentile(values, 0.5),
        "rmsd_p95_angstrom": percentile(values, 0.95),
        "rmsd_p99_angstrom": percentile(values, 0.99),
        "rmsd_max_angstrom": max(values) if values else None,
        "classification_counts": dict(sorted(classes.items())),
        "records_requiring_review": len(review_rows),
        "orca_version_classification": {
            version: dict(sorted(counts.items()))
            for version, counts in sorted(version_classes.items())
        },
        "interpretation_rule": {
            "coordinate_identity_consistent": "RMSD <= 0.02 A",
            "same_geometry_with_minor_relaxation": "0.02 < RMSD <= 0.20 A",
            "same_or_similar_conformer": "0.20 < RMSD <= 0.75 A",
            "different_conformer_or_source": "RMSD > 0.75 A",
            "requires_graph_mapping": "Direct atom order is not comparable; graph mapping is required before inference",
        },
    }
    (output / "full_initial_geometry_audit_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    write_csv(output / "full_initial_geometry_review_queue.csv", review_rows, [
        "cid", "orca_version", "rmsd_angstrom", "classification", "source_file", "error_or_note",
    ])

    class_rows = []
    for cls, count in sorted(classes.items()):
        class_rows.append({
            "classification": cls,
            "count": count,
            "percentage": f"{100 * count / len(rows):.4f}",
        })
    write_csv(output / "full_initial_geometry_classification.csv", class_rows,
              ["classification", "count", "percentage"])

    figure_status = "not_generated"
    try:
        import matplotlib.pyplot as plt

        fig, axes = plt.subplots(1, 2, figsize=(11.5, 4.3), constrained_layout=True)
        plot_values = [min(v, 1.5) for v in values]
        axes[0].hist(plot_values, bins=50, color="#176B5B", edgecolor="white", linewidth=0.35)
        axes[0].axvline(0.02, color="#D29B38", linestyle="--", linewidth=1.2)
        axes[0].axvline(0.20, color="#B44C43", linestyle="--", linewidth=1.2)
        axes[0].set_xlabel("Aligned RMSD (Å; values >1.5 clipped for display)")
        axes[0].set_ylabel("Molecule count")
        axes[0].set_title("a  Starting-coordinate agreement")

        labels = [key.replace("_", "\n") for key, _ in classes.most_common()]
        counts = [value for _, value in classes.most_common()]
        axes[1].bar(range(len(counts)), counts, color="#426B8A")
        axes[1].set_xticks(range(len(labels)), labels, rotation=25, ha="right", fontsize=8)
        axes[1].set_ylabel("Molecule count")
        axes[1].set_title("b  Audit classification")
        for i, count in enumerate(counts):
            axes[1].text(i, count, str(count), ha="center", va="bottom", fontsize=8)
        fig.savefig(output / "Fig_initial_geometry_full_audit.png", dpi=300, facecolor="white")
        fig.savefig(output / "Fig_initial_geometry_full_audit.pdf", facecolor="white")
        plt.close(fig)
        figure_status = "generated"
    except Exception as exc:  # figure is optional; tables remain authoritative
        (output / "figure_generation_error.txt").write_text(str(exc) + "\n", encoding="utf-8")

    print(json.dumps({**summary, "figure_status": figure_status}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
