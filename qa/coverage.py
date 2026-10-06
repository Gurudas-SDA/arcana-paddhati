"""Pārklājums: Satkirti likumi (qa/likumi.json) → testi.

  python qa/coverage.py            kopsavilkums + saraksts «nav testa»
  python qa/coverage.py --all      katrs likums ar saviem testiem
  python qa/coverage.py --strict   kļūda (exit 1), ja kāda atsauce pēdējā PILNAJĀ palaidienā nesakrita ne ar vienu pārbaudi

Ja ir qa/.results/last.json (pēdējais run_all.py), katram likumam rāda arī statusu:
PASS (visas saistītās pārbaudes izgāja), FAIL, «nav palaists» (piem. --fast neskar).
"""
import argparse
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from run_all import SUITES, matches  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--strict", action="store_true")
    a = ap.parse_args()
    reg = json.load(open(os.path.join(HERE, "likumi.json"), encoding="utf-8"))
    rules = reg["rules"]
    suite_ids = {s["id"] for s in SUITES}
    lint_src = open(os.path.join(HERE, "lint_content.py"), encoding="utf-8").read()
    lint_ids = set(re.findall(r'Check\("(L\d+)"', lint_src))
    last_p = os.path.join(HERE, ".results", "last.json")
    last = json.load(open(last_p, encoding="utf-8")) if os.path.exists(last_p) else None
    checks = [c for j in (last or {}).get("jobs", []) for c in j["checks"] if c["status"] in ("PASS", "FAIL", "KNOWN")]

    bad_refs, unmatched = [], []
    with_t, without, partial = [], [], []
    status = {}
    for r in rules:
        refs = r.get("tests", [])
        for t in refs:
            s, _, pre = t.partition(":")
            if s == "lint":
                if pre not in lint_ids:
                    bad_refs.append((r["id"], t))
            elif s not in suite_ids:
                bad_refs.append((r["id"], t))
        if refs:
            with_t.append(r)
            if r.get("daleji"):
                partial.append(r)
        else:
            without.append(r)
        if last and refs:
            hit = [c for c in checks if any(matches(t, c["suite"], c["name"]) for t in refs)]
            for t in refs:
                if not any(matches(t, c["suite"], c["name"]) for c in checks):
                    unmatched.append((r["id"], t))
            sts = {c["status"] for c in hit}
            status[r["id"]] = ("FAIL" if "FAIL" in sts else "KNOWN" if "KNOWN" in sts else "PASS") if hit else "nav palaists"

    n = len(rules)
    print(f"Satkirti likumi: {n}  (UI {sum(1 for r in rules if r['doc'] == 'UI')}, standarti {sum(1 for r in rules if r['doc'] == 'STD')})")
    print(f"  ar testu:   {len(with_t)}  ({len(with_t) * 100 // n}%), no tiem daļēji: {len(partial)}")
    print(f"  bez testa:  {len(without)}")
    if last:
        c = {k: sum(1 for v in status.values() if v == k) for k in ("PASS", "FAIL", "KNOWN", "nav palaists")}
        print(f"  pēdējais palaidiens ({last['mode']}, {last['finished']}): PASS {c['PASS']}, FAIL {c['FAIL']}, KNOWN {c['KNOWN']}, nav palaists {c['nav palaists']}")
    print("\nNAV TESTA:")
    for r in without:
        print(f"  {r['id']:8s} {r['text'][:90]}{'…' if len(r['text']) > 90 else ''}\n           ↳ {r.get('nav_testa', '?')}")
    print("\nDAĻĒJI (tests ir, bet neaptver visu rindu):")
    for r in partial:
        print(f"  {r['id']:8s} ↳ {r['daleji']}")
    if a.all:
        print("\nVISI:")
        for r in rules:
            st = status.get(r["id"], "")
            print(f"  {r['id']:8s} {st:13s} {r['text'][:80]}")
            for t in r.get("tests", []):
                print(f"           - {t}")
    if bad_refs:
        print("\nKĻŪDA: atsauces uz neesošu scenāriju / lint pārbaudi:")
        for x in bad_refs:
            print("  ", *x)
    if last and unmatched:
        print(f"\nAtsauces, kas pēdējā palaidienā ({last['mode']}) nesakrita ne ar vienu pārbaudi: {len(unmatched)}"
              + (" (ātrajā režīmā tas ir normāli — daļa scenāriju/ierīču netiek palaista)" if last["mode"] == "fast" else ""))
        for x in unmatched[:60]:
            print("  ", *x)
    if bad_refs or (a.strict and last and last["mode"] == "full" and unmatched):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
