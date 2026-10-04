# -*- coding: utf-8 -*-
"""Check the GCal (Riga) table against the Chaitanya Academy calendar.

  python validate.py [ppp_calendar.json]     (default: ppp_calendar_snapshot.json, saved 2026-10-04 from
                                              https://gurudas-sda.github.io/ca-link-finder/data-static/ppp_calendar.json)
Needs out/Riga.json from gen_calendar.py. Exit code 1 on any mismatch.
"""
import json, os, re, sys

sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
ca = json.load(open(sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "ppp_calendar_snapshot.json"), encoding="utf-8"))
g = json.load(open(os.path.join(HERE, "out", "Riga.json"), encoding="utf-8"))
rows = json.load(open(os.path.join(HERE, "table_Riga.json"), encoding="utf-8"))
bad = 0

# 1. Cāturmāsya dates: CA 'vrata' events vs the table
ours = set()
for r in rows:
    ours |= {r["m1"][0], r["m2"][0], r["m3"][0], r["m4"][0], r["end"]}
cad = sorted({d for e in ca["events"] if e["kind"] == "vrata" and "caturmasya" in e["slug"] for d in e["dates"]})
miss = [d for d in cad if d not in ours]
print("caturmasya: CA dates %d, matched %d, CA-only %s" % (len(cad), len(cad) - len(miss), miss))
bad += len(miss)

# 2. Ekādaśī fasting days in the CA range
cfast = {d for e in ca["events"] if e["kind"] == "ekadasi" for d in e["dates"]}
lo, hi = min(cfast), max(cfast)
gfast = {d for d, v in g.items() if lo <= d <= hi and any(e.startswith("Fasting for") and "Ekadasi" in e for e in v["ev"])}
print("ekadasi %s..%s: CA %d, matched %d, CA-only %s, GCal-only %s" % (
    lo, hi, len(cfast), len(cfast & gfast), sorted(cfast - gfast), sorted(gfast - cfast)))
bad += len(cfast ^ gfast)

# 3. Viśvarūpa-mahotsava = start of the 3rd month, every year
vm = [r["year"] for r in rows if not any(re.search("Visvarupa", e) for e in g[r["m3"][0]]["ev"])]
print("visvarupa-mahotsava on 3rd-month start: %d/%d years%s" % (len(rows) - len(vm), len(rows), (" — differs: %s" % vm) if vm else ""))
bad += len(vm)

print("OK" if not bad else "MISMATCHES: %d" % bad)
sys.exit(1 if bad else 0)
