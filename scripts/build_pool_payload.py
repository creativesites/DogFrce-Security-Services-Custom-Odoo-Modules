#!/usr/bin/env python3
"""Map matched roster blocks to contract-site ids and emit the import payload.
Usage: python3 -I scripts/build_pool_payload.py matched.json payload.json
"""
import json
import sys

# block-title keyword -> production security.contract.site ids (reviewed by hand)
MAP = [
    ("AFRIKUUMBA", [34]), ("NANTU LIKWAFELA", [55]), ("NANTU WHK WEST", [56]),
    ("C C - HUB", [23]), ("MASIKHULENI", [57]), ("NAMIC NO.2", [53, 54]),
    ("PETROFUND", [30]), ("EROS HOUSE", [49]), ("WAKKA PRE", [33]), ("ADCON", [42]),
    ("BONSMARA", [47]), ("ATTA RENTAL", [40]), ("EYE CLINIC", [24]),
    ("MAGNOLIA", [39]), ("HOCHLAND S S", [8]), ("EFFORT INVESTMENT", [9]),
    ("CHINA SEVETH", [26]), ("SCRAP NORTHERN", [32]), ("KUNENE", [36]),
    ("AFRIDECA", [44]),
    ("DREAMLAND", [14]), ("CHINA CONSTRUCTION", [22]), ("ROBOT & NEW ROAD", [22]),
    ("MANDELA & UNDER", [22]),
]
OK = {"exact", "transposed", "token_subset", "initial_surname", "token_fuzzy", "fuzzy", "assisted"}


def cs_for(block):
    if block["sheet"] == "NAPWU" and "NAPWU" in block["titles"]:
        return [25]
    for key, ids in MAP:
        if any(key in t.upper() for t in block["titles"][:2]):
            return ids
    return None


blocks = json.load(open(sys.argv[1]))
out, skipped = {}, []
for b in blocks:
    ids = cs_for(b)
    if not ids:
        skipped.append({"sheet": b["sheet"], "titles": b["titles"][:2], "guards": len(b["guards"])})
        continue
    for cs in ids:
        d = out.setdefault(str(cs), {"emp": [], "unmatched": [], "titles": []})
        d["titles"].append(b["titles"][0])
        for m in b["matches"]:
            if m["tier"] in OK and m["emp_id"] not in d["emp"]:
                d["emp"].append(m["emp_id"])
            elif m["tier"] not in OK and m["raw"] not in d["unmatched"]:
                d["unmatched"].append(m["raw"])
json.dump({"sites": out, "skipped": skipped}, open(sys.argv[2], "w"), indent=1)
print(len(out), "contract sites;", sum(len(v["emp"]) for v in out.values()), "pool members")
for k, v in out.items():
    print(k, v["titles"], len(v["emp"]), "matched", len(v["unmatched"]), "unmatched")
print("SKIPPED", json.dumps(skipped))
