#!/usr/bin/env python3
"""Rebuild the original ORCA ``.inp`` input from the ``INPUT FILE`` section of
an archived ``.out`` file, for the paired version re-computation.

ORCA echoes the exact input it was given in an ``INPUT FILE`` block near the top
of every ``.out``. This script extracts the original ``!`` keyword line, the
``%pal``/``%maxcore`` control lines, the ``* xyz <charge> <mult>`` line and the
atom block (verbatim element tokens and coordinates), and writes a clean
``.inp`` that reproduces the released calculation. The reconstructed input is
the starting geometry for BOTH ORCA 6.0.1 and 6.1.1 in the paired run, so the
two versions are compared on the identical input.

Usage:
    # one file
    python code/rebuild_orca_input.py --out ARCHIVE/248_charge_fix.out --output-dir REBUILD/inp
    # a whole sample, selected from the paired-sample CSV
    python code/rebuild_orca_input.py --out-dir ARCHIVE/out_final_3196 \
        --sample audits/orca_version_paired_sample.csv --output-dir REBUILD/inp
    # override the parallel/memory lines for a specific cluster
    python code/rebuild_orca_input.py --out-dir ARCHIVE/out_final_3196 \
        --sample audits/orca_version_paired_sample.csv --output-dir REBUILD/inp \
        --nprocs 48 --maxcore 2000
"""
from __future__ import annotations

import argparse
import csv
import re
from pathlib import Path

INPUT_BANNER = re.compile(r"^\s*INPUT FILE\s*$", re.I | re.M)
END_INPUT = re.compile(r"\*{4,}\s*END OF INPUT\s*\*{4,}", re.I)
LINE_PREFIX = re.compile(r"^\|\s*\d+>\s?(.*)$")
FLOAT = r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[EeDd][-+]?\d+)?"
ATOM_LINE = re.compile(rf"^(\d+|[A-Za-z]{{1,2}})\s+({FLOAT})\s+({FLOAT})\s+({FLOAT})\s*$")


def extract_input(text: str) -> dict:
    """Return the reconstructed input pieces from an OUT text block."""
    banner = INPUT_BANNER.search(text)
    if not banner:
        raise RuntimeError("INPUT FILE banner not found")
    end = END_INPUT.search(text, banner.end())
    if not end:
        raise RuntimeError("END OF INPUT marker not found")
    block = text[banner.end():end.start()]

    keyword = None
    pal = None       # e.g. "nprocs 50 end"
    maxcore = None   # e.g. "1500"
    xyz = None       # (charge, multiplicity)
    atoms: list[str] = []
    name = None
    for raw in block.splitlines():
        m = LINE_PREFIX.match(raw)
        content = m.group(1).strip() if m else raw.strip()
        if not content:
            continue
        if content.startswith("NAME ="):
            name = content.split("=", 1)[1].strip()
        elif content.startswith("!"):
            keyword = content[1:].strip()
        elif content.startswith("%pal"):
            pal = content[len("%pal"):].strip()
        elif content.startswith("%maxcore"):
            maxcore = content[len("%maxcore"):].strip()
        elif content.startswith("* xyz"):
            parts = content.split()
            xyz = (parts[2], parts[3])
        elif content.startswith("*"):
            continue  # geometry terminator
        elif ATOM_LINE.match(content):
            atoms.append(content)
        # Any other line (banner separators, blank lines, NAME echo) is ignored.
    if keyword is None or xyz is None or not atoms:
        raise RuntimeError(f"incomplete INPUT FILE block: keyword={keyword!r} xyz={xyz!r} atoms={len(atoms)}")
    return {"name": name, "keyword": keyword, "pal": pal, "maxcore": maxcore,
            "charge": xyz[0], "multiplicity": xyz[1], "atoms": atoms}


def render(inp: dict, nprocs: str | None, maxcore: str | None) -> str:
    lines = [f"! {inp['keyword']}"]
    if nprocs is not None:
        lines.append(f"%pal nprocs {nprocs} end")
    elif inp["pal"]:
        lines.append(f"%pal {inp['pal']}")
    if maxcore is not None:
        lines.append(f"%maxcore {maxcore}")
    elif inp["maxcore"]:
        lines.append(f"%maxcore {inp['maxcore']}")
    lines.append(f"* xyz {inp['charge']} {inp['multiplicity']}")
    lines.extend(inp["atoms"])
    lines.append("*")
    return "\n".join(lines) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--out", type=Path, help="A single ORCA .out file")
    src.add_argument("--out-dir", type=Path, help="Directory of ORCA .out files")
    ap.add_argument("--sample", type=Path, default=None,
                    help="Optional paired-sample CSV; when given, only its CIDs are rebuilt")
    ap.add_argument("--output-dir", required=True, type=Path)
    ap.add_argument("--nprocs", type=str, default=None,
                    help="Override the %pal processor count (e.g. '48' -> '%pal nprocs 48 end'); omit to reproduce the original")
    ap.add_argument("--maxcore", type=str, default=None,
                    help="Override %maxcore (MB); omit to reproduce the original")
    args = ap.parse_args()

    files: list[Path]
    if args.out:
        files = [args.out]
    else:
        files = sorted(args.out_dir.glob("*.out"))

    # When a sample CSV is supplied, match files by their exact `source_file`
    # name so repair records (e.g. 248_charge_fix.out) are located by name, and
    # every output is named `<cid>.inp` for uniform downstream use.
    sample_map: dict[str, str] | None = None
    if args.sample:
        with args.sample.open(encoding="utf-8-sig", newline="") as fh:
            sample_map = {r["source_file"]: r["cid"] for r in csv.DictReader(fh)}
        files = [p for p in files if p.name in sample_map]

    args.output_dir.mkdir(parents=True, exist_ok=True)
    written = 0
    skipped = []
    for path in files:
        if sample_map is not None:
            cid = sample_map[path.name]
        else:
            m = re.search(r"(\d+)$", path.stem)
            cid = m.group(1) if m else path.stem
        text = path.read_text(encoding="utf-8", errors="replace")
        try:
            inp = extract_input(text)
            with (args.output_dir / f"{cid}.inp").open("w", encoding="utf-8", newline="\n") as fh:
                fh.write(render(inp, args.nprocs, args.maxcore))
            written += 1
        except RuntimeError as exc:
            skipped.append({"cid": cid, "source_file": path.name, "error": str(exc)})

    print(f"rebuilt {written} inputs -> {args.output_dir}")
    if skipped:
        print(f"skipped {len(skipped)}:")
        for s in skipped:
            print(f"  {s['source_file']}: {s['error']}")


if __name__ == "__main__":
    main()
