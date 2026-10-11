#!/usr/bin/env python3
"""Parse the DogForce manual roster workbook into site blocks (read-only).

Usage: python3 -I scripts/ingest_excel_roster.py <roster.xlsx> [out.json]
"""
import json
import re
import sys

import openpyxl

SHIFT_CODES = {"NS", "DS", "OFF", "STBY", "L", "SHPRT", "MGNS", "MGDS", "NTN"}


def _s(v):
    return re.sub(r"\s+", " ", str(v)).strip() if v is not None else ""


def parse_workbook(path):
    wb = openpyxl.load_workbook(path, data_only=True)
    blocks = []
    for ws in wb:
        rows = [[_s(c) for c in r] for r in ws.iter_rows(values_only=True)]
        cur = None
        pending_titles = []
        for i, r in enumerate(rows):
            a = r[0].upper() if r else ""
            if a.startswith("NAMES OF GUARD"):
                cur = {"sheet": ws.title.strip(), "header_row": i + 1, "needed": None,
                       "allocated": None, "service": "", "titles": list(pending_titles),
                       "guards": []}
                # look back up to 4 rows for needed/allocated/service/site name
                for j in range(max(0, i - 5), i):
                    b = rows[j]
                    k = b[0].upper()
                    if k.startswith("NUMBER OF GUARD") and b[1].isdigit():
                        cur["needed"] = int(b[1])
                    elif k.startswith("OFFICERS ALLOCATED") and b[1].isdigit():
                        cur["allocated"] = int(b[1])
                    elif k.startswith("TYPE OF SERVICE"):
                        cur["service"] = b[1]
                    elif k.startswith("SITE NAME"):
                        cur["titles"] += [x for x in b[1:] if x]
                    # floating titles in other cells of the block header rows
                    if j >= i - 5:
                        for x in b[2:]:
                            if x and not x.isdigit() and x.upper() not in SHIFT_CODES \
                                    and len(x) > 3 and not k.startswith("NAMES"):
                                cur["titles"].append(x)
                blocks.append(cur)
                pending_titles = []
                continue
            if cur is None:
                continue
            if a.startswith(("TYPE OF SERVICE", "NUMBER OF GUARD", "OFFICERS ALLOC", "SITE NAME")):
                cur = None
                continue
            name = r[0]
            if not name or name.upper() == "X" or name.upper() in SHIFT_CODES:
                continue
            cur["guards"].append(name)
    return blocks


if __name__ == "__main__":
    blocks = parse_workbook(sys.argv[1])
    out = sys.argv[2] if len(sys.argv) > 2 else None
    print(len(blocks), "blocks;", sum(len(b["guards"]) for b in blocks), "guard rows")
    for b in blocks:
        print(b["sheet"], "|", b["titles"][:3], "|", b["service"], "| need", b["needed"],
              "alloc", b["allocated"], "| guards", len(b["guards"]))
    if out:
        json.dump(blocks, open(out, "w"), indent=1)
