#!/usr/bin/env python3
"""Rebuild the release payload SHA-256 manifest without touching payloads."""

from __future__ import annotations

import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST_DIR = ROOT / "manifests"
MANIFEST = MANIFEST_DIR / "files_sha256.csv"
SIDECAR = MANIFEST_DIR / "files_sha256.csv.sha256"
SUMMARY = MANIFEST_DIR / "release_summary.json"


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def main() -> None:
    paths = sorted(
        path
        for path in ROOT.rglob("*")
        if path.is_file()
        and "manifests" not in path.relative_to(ROOT).parts
        and "__pycache__" not in path.relative_to(ROOT).parts
        and not path.name.endswith(".tar.gz")
        and not path.name.endswith(".tar.gz.sha256")
    )
    rows = [
        {
            "relative_path": path.relative_to(ROOT).as_posix(),
            "size_bytes": path.stat().st_size,
            "sha256": digest(path),
        }
        for path in paths
    ]

    MANIFEST_DIR.mkdir(parents=True, exist_ok=True)
    temporary = MANIFEST.with_suffix(".csv.tmp")
    with temporary.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["relative_path", "size_bytes", "sha256"],
        )
        writer.writeheader()
        writer.writerows(rows)
    temporary.replace(MANIFEST)

    manifest_hash = digest(MANIFEST)
    SIDECAR.write_text(f"{manifest_hash}  files_sha256.csv\n", encoding="ascii")

    release_summary = {
        "release_name": "TCM-QM",
        "release_version": "1.0.0",
        "frozen_at": datetime.now(timezone.utc).isoformat(),
        "payload_file_count": len(rows),
        "payload_size_bytes": sum(row["size_bytes"] for row in rows),
        "manifest_scope": "all files except files inside manifests/",
        "hash_algorithm": "SHA-256",
    }
    SUMMARY.write_text(
        json.dumps(release_summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(release_summary, ensure_ascii=False, indent=2))
    print(f"manifest_sha256={manifest_hash}")


if __name__ == "__main__":
    main()
