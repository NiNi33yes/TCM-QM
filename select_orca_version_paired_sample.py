#!/usr/bin/env python3
"""Deterministically select the paired ORCA-version re-computation sample.

This implements pre-submission checklist item 3: a paired re-computation of the
SAME molecule in both ORCA 6.0.1 and 6.1.1, so the software-version effect can
be isolated from the between-batch composition confound that limits the released
composition-adjusted sensitivity analysis (see ``audits/orca_version_analysis_summary.json``,
whose caveat explicitly flags that version assignment was not randomized).

Sampling rationale
------------------
The sample is stratified so that any version-induced difference is most likely
to surface, while remaining small enough (30-50) for a server-side re-run:

1. **Fixed repair block** — CIDs 248, 5571, 10946210 (the two formal-charge
   repairs and the one E/Z stereochemical repair). 248 and 5571 are the only
   +1 charged records, so both charge states are guaranteed present.
2. **Rare/heavy elements** — molecules containing I, F, Si are included in
   full (their molecule counts are 2/2/3); Br is capped at its full 7; P, Cl
   and S are capped at a quota. Rare elements exercise def2 basis and ECP
   handling, where a minor version change is most likely to matter.
3. **CHNO bulk** — the remaining quota is filled from molecules whose only
   heavy elements are C/N/O, stratified by heavy-atom-count tercile and the
   original ORCA-version batch, so the sample spans the dataset size range and
   both source batches.

Selection is fully deterministic (fixed seed) and de-duplicated.

Usage:
    python code/select_orca_version_paired_sample.py \
        --master 02_数据冻结最新版_v5/tables/tcm_qm_master.csv \
        --output 02_数据冻结最新版_v5/audits/orca_version_paired_sample.csv \
        --n 40
"""
from __future__ import annotations

import argparse
import csv
import random
import re
from pathlib import Path

# CIDs whose identity/stereochemistry was repaired before freeze. Two of these
# (248, 5571) are the dataset's only +1 charged molecules.
FIXED_REPAIR_CIDS = ["248", "5571", "10946210"]

# Non-CHNO elements, in descending priority (rarest first). Quota = max number
# of *additional* molecules containing that element to select (some molecules
# carry several of these elements, so the final count is de-duplicated).
RARE_ELEMENT_QUOTA = {
    "I": 2,   # 2 molecules total  -> all
    "F": 2,   # 2 molecules total  -> all
    "Si": 3,  # 3 molecules total  -> all
    "Br": 7,  # 7 molecules total  -> all
    "P": 4,   # 10 molecules total -> 4
    "Cl": 4,  # 27 molecules total -> 4
    "S": 5,   # 81 molecules total -> 5
}

FORMULA_TOKEN = re.compile(r"([A-Z][a-z]?)(\d*)")


def parse_heavy_elements(formula: str) -> set[str]:
    """Return the set of non-H elements in a molecular formula string."""
    return {sym for sym, _n in FORMULA_TOKEN.findall(formula) if sym != "H"}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--master", required=True, type=Path)
    ap.add_argument("--output", required=True, type=Path)
    ap.add_argument("--n", type=int, default=40,
                    help="Total sample size (default 40, within the 30-50 checklist range)")
    ap.add_argument("--seed", type=int, default=20260829)
    args = ap.parse_args()

    with args.master.open(encoding="utf-8-sig", newline="") as fh:
        rows = list(csv.DictReader(fh))
    by_cid = {r["cid"]: r for r in rows}
    cids = sorted(by_cid, key=int)

    def record(cid: str, stratum: str, note: str) -> dict:
        r = by_cid[cid]
        els = parse_heavy_elements(r["molecular_formula"])
        return {
            "cid": cid, "source_file": r["source_file"], "orca_version": r["orca_version"],
            "charge": r["charge"], "multiplicity": r["multiplicity"],
            "molecular_formula": r["molecular_formula"],
            "heavy_atom_count": r["heavy_atom_count"], "elements": "+".join(sorted(els)),
            "stratum": stratum, "note": note,
        }

    selected: dict[str, dict] = {}
    missing = [c for c in FIXED_REPAIR_CIDS if c not in by_cid]
    if missing:
        raise RuntimeError(f"Fixed repair CIDs missing from master: {missing}")
    for cid in FIXED_REPAIR_CIDS:
        note = "repair block; +1 charged" if cid in ("248", "5571") else "repair block; E/Z stereochemical"
        selected[cid] = record(cid, "repair", note)

    # Rare/heavy-element coverage (in priority order, de-duplicated).
    heavy_el_by_cid = {cid: parse_heavy_elements(by_cid[cid]["molecular_formula"]) for cid in cids}
    for el, quota in RARE_ELEMENT_QUOTA.items():
        got = 0
        for cid in cids:
            if got >= quota:
                break
            if cid in selected or el not in heavy_el_by_cid[cid]:
                continue
            selected[cid] = record(cid, "rare_element", f"contains {el}")
            got += 1

    # CHNO bulk: fill the remaining quota from molecules with only C/N/O heavy
    # atoms, stratified by heavy-atom-count tercile and original version batch.
    chno_pool = [cid for cid in cids if cid not in selected and heavy_el_by_cid[cid] <= {"C", "N", "O"}]
    chno_hats = sorted(int(by_cid[c]["heavy_atom_count"]) for c in chno_pool)
    if chno_hats:
        lo = chno_hats[len(chno_hats) // 3]
        hi = chno_hats[2 * len(chno_hats) // 3]
    else:
        lo = hi = 0

    def tercile(cid: str) -> str:
        h = int(by_cid[cid]["heavy_atom_count"])
        return "small" if h <= lo else ("large" if h >= hi else "medium")

    strata: dict[str, list[str]] = {}
    for cid in chno_pool:
        key = (tercile(cid), by_cid[cid]["orca_version"])
        strata.setdefault(key, []).append(cid)

    # Deterministic interleaving within each stratum.
    rng = random.Random(args.seed)
    for key in strata:
        rng.shuffle(strata[key])

    remaining = args.n - len(selected)
    # Round-robin across strata so every (tercile, version) cell is represented.
    cell_keys = sorted(strata, key=lambda k: (k[0], k[1]))
    idx = {k: 0 for k in cell_keys}
    added = 0
    round_i = 0
    while added < remaining and any(idx[k] < len(strata[k]) for k in cell_keys):
        progressed = False
        for k in cell_keys:
            if added >= remaining:
                break
            if idx[k] < len(strata[k]):
                cid = strata[k][idx[k]]
                idx[k] += 1
                if cid not in selected:
                    selected[cid] = record(cid, "chno", f"CHNO {k[0]} / {k[1]}")
                    added += 1
                    progressed = True
        if not progressed:
            break
        round_i += 1

    out = [selected[cid] for cid in sorted(selected, key=int)]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["cid", "source_file", "orca_version", "charge", "multiplicity",
                  "molecular_formula", "heavy_atom_count", "elements", "stratum", "note"]
    with args.output.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames, lineterminator="\r\n")
        writer.writeheader()
        writer.writerows(out)

    print(f"selected {len(out)}/{args.n} CIDs -> {args.output}")
    from collections import Counter
    print("stratum counts:", dict(Counter(r["stratum"] for r in out)))
    print("elements covered:", sorted({e for r in out for e in r["elements"].split("+")}))
    print("version batch:", dict(Counter(r["orca_version"] for r in out)))


if __name__ == "__main__":
    main()
