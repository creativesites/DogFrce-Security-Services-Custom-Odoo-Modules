#!/usr/bin/env python3
"""Match parsed roster guard names to hr.employee rows (offline, read-only).

Usage: python3 -I scripts/match_roster_guards.py blocks.json emps.psv out.json
emps.psv is `id|name|employee_code` as exported from psql.
"""
import difflib
import json
import re
import sys


def norm(s):
    return re.sub(r"[^a-z ]", " ", s.lower().replace("(ns)", " ")).split()


def load_emps(path):
    out = []
    for line in open(path).read().splitlines()[1:]:
        p = line.split("|")
        if len(p) >= 2 and p[0].isdigit():
            out.append({"id": int(p[0]), "name": p[1], "code": p[2] if len(p) > 2 else "", "t": norm(p[1])})
    return out


def match(name, emps):
    t = norm(name)
    if not t:
        return None, "empty", 0, []
    ts = set(t)
    def pick(cands, tier, conf):
        if len(cands) == 1:
            return cands[0], tier, conf, []
        if len(cands) > 1:
            return None, "ambiguous", 0, [c["name"] for c in cands]
        return False
    for tier, conf, fn in (
        ("exact", 100, lambda e: e["t"] == t),
        ("transposed", 95, lambda e: set(e["t"]) == ts and len(e["t"]) == len(t)),
        ("token_subset", 90, lambda e: len(ts) >= 2 and ts <= set(e["t"])),
        ("initial_surname", 85, lambda e: len(t) == 2 and any(
            len(x) == 1 and any(y[0] == x for y in e["t"]) for x in t)
            and any(len(x) > 1 and x in e["t"] for x in t)),
    ):
        r = pick([e for e in emps if fn(e)], tier, conf)
        if r:
            return r
    def tok_fuzzy(e):
        pool = list(e["t"])
        for x in t:
            best = max(pool, key=lambda y: difflib.SequenceMatcher(None, x, y).ratio(), default=None)
            if best is None or difflib.SequenceMatcher(None, x, best).ratio() < 0.80:
                return False
            pool.remove(best)
        return len(t) >= 2
    r = pick([e for e in emps if tok_fuzzy(e)], "token_fuzzy", 82)
    if r:
        return r
    scored = sorted(((difflib.SequenceMatcher(None, " ".join(sorted(t)), " ".join(sorted(e["t"]))).ratio(), e)
                     for e in emps), key=lambda x: -x[0])
    if scored and scored[0][0] >= 0.80 and (len(scored) < 2 or scored[0][0] - scored[1][0] >= 0.05):
        return scored[0][1], "fuzzy", int(scored[0][0] * 100), []
    return None, "unmatched", 0, [e["name"] for s, e in scored[:2]]


if __name__ == "__main__":
    blocks = json.load(open(sys.argv[1]))
    emps = load_emps(sys.argv[2])
    stats = {}
    for b in blocks:
        b["matches"] = []
        for g in b["guards"]:
            e, tier, conf, alts = match(g, emps)
            stats[tier] = stats.get(tier, 0) + 1
            b["matches"].append({"raw": g, "emp_id": e["id"] if e else None,
                                 "emp_name": e["name"] if e else None, "tier": tier,
                                 "conf": conf, "alts": alts})
    json.dump(blocks, open(sys.argv[3], "w"), indent=1)
    print(stats)
    for b in blocks:
        for m in b["matches"]:
            if m["tier"] in ("ambiguous", "unmatched"):
                print(b["sheet"], "|", m["raw"], "|", m["tier"], m["alts"])
