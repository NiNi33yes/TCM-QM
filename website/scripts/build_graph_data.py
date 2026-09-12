"""Build compact, auditable herb-compound graph assets from the frozen release."""

from __future__ import annotations

import csv
import json
import argparse
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT.parent / "02_数据发布包" / "data_release" / "tables" / "tcm_source_provenance.csv"
OUTPUT = ROOT / "app" / "data"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=SOURCE)
    parser.add_argument('--output-dir', type=Path, default=OUTPUT)
    args = parser.parse_args()
    with args.source.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        required = {'cid','herb_id','herb_name','match_confidence','match_method',
                    'source_database','source_locator','source_snapshot'}
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f'Missing provenance columns: {sorted(missing)}')
        rows = list(reader)
    if not rows:
        raise ValueError('Empty provenance input')
    names = {}
    for row in rows:
        if not row['cid'].isdigit() or not row['herb_id'].strip() or not row['herb_name'].strip():
            raise ValueError('Invalid CID or empty herb identity')
        previous = names.setdefault(row['herb_id'], row['herb_name'])
        if previous != row['herb_name']:
            raise ValueError(f"Conflicting herb names for {row['herb_id']}")

    pair_rows: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        pair_rows[(row["herb_id"].strip(), row["cid"].strip())].append(row)
    counts = Counter(herb_id for herb_id, _ in pair_rows)
    herbs_by_id: dict[str, dict[str, object]] = {}
    edges: list[dict[str, str]] = []

    for (herb_id, cid), evidence_rows in pair_rows.items():
        row = evidence_rows[0]
        herbs_by_id.setdefault(
            herb_id,
            {
                "id": herb_id,
                "name": row["herb_name"].strip(),
                "edgeCount": counts[herb_id],
            },
        )
        edges.append(
            {
                "id": f"{herb_id}-{cid}",
                "herbId": herb_id,
                "cid": cid,
                "confidence": ", ".join(sorted({item["match_confidence"].strip() for item in evidence_rows})),
                "method": " | ".join(sorted({item["match_method"].strip() for item in evidence_rows})),
                "sourceDatabase": ", ".join(sorted({item["source_database"].strip() for item in evidence_rows})),
                "sourceLocator": " | ".join(item["source_locator"].strip() for item in evidence_rows),
                "sourceSnapshot": ", ".join(sorted({item["source_snapshot"].strip() for item in evidence_rows})),
                "evidenceCount": str(len(evidence_rows)),
            }
        )

    herbs = sorted(herbs_by_id.values(), key=lambda item: str(item["name"]))
    edges.sort(key=lambda item: (item["herbId"], int(item["cid"]), item["id"]))
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "herbs.json").write_text(
        json.dumps(herbs, ensure_ascii=False, separators=(",", ":")), encoding="utf-8"
    )
    (args.output_dir / "edges.json").write_text(
        json.dumps(edges, ensure_ascii=False, separators=(",", ":")), encoding="utf-8"
    )

    unique_cids = {edge["cid"] for edge in edges}
    print(
        json.dumps(
            {"herbs": len(herbs), "cids": len(unique_cids), "associationEdges": len(edges), "provenanceRecords": len(rows)},
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
