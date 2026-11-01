"""token_guard — V61 solis 6 (Vraja Lila: «Автоматическая проверка перед выпуском: сначала предупреждает о новых значениях не из токенов,
позже — останавливает»; plāns apstiprināts 30.10 msg 1920, 31.10 msg 7164). Tagad TIKAI BRĪDINĀJUMS (exit 0); `--strict` → exit 1.

Skatās UI kodu (app/globals.css, components/**/*.tsx, app/**/*.tsx) un salīdzina «cietās» vērtības ar bāzes sarakstu
qa/token_guard_baseline.json (esošās vērtības; šodien brīdinājumu nav). Ķer:
  - krāsas #hex, rgb()/rgba()/hsl()/hsla();
  - Tailwind arbitrary klases ar px/rem/em vai krāsu: p-[13px], rounded-[10px], gap-[7px], text-[#abc123] (bez var(...));
  - CSS/inline deklarācijas padding/margin/gap/border-radius/color/background(-color)/border-color/top/left/... ar skaitli+vienību vai
    krāsu, ja vērtībā nav var(--…).
Neķer: 0, auto, %, vh/vw, calc bez px/krāsas, vērtības no var(--…), komentārus; design-system/tokens.css, qa/, node_modules, out, .next netiek skenēti.
Bāze: (fails, vērtība) pāri — rindu numuri nav svarīgi, tāpēc rindu nobīde neradīs brīdinājumu.
Lietošana: python qa/token_guard.py [--strict] [--root DIR] [--update-baseline]
"""
import argparse
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_ROOT = os.path.normpath(os.path.join(HERE, ".."))
BASELINE = os.path.join(HERE, "token_guard_baseline.json")
SKIP_DIRS = {"node_modules", "out", ".next", "qa", ".git", "design-system"}

HEX = re.compile(r"#[0-9a-fA-F]{3,8}\b")
FUNC = re.compile(r"\b(?:rgba?|hsla?)\([^)]*\)", re.I)
UNIT = re.compile(r"(?<![\w.-])-?\d*\.?\d+(?:px|rem|em)\b")
TW = re.compile(r"[\w:!-]+-\[[^\]\s]+\]")
PROPS = (r"padding|margin|gap|row-gap|column-gap|border-radius|border-width|color|background|background-color|border|border-color|"
         r"outline|top|right|bottom|left|width|height|min-width|min-height|max-width|max-height|font-size|line-height|"
         r"padding-(?:top|right|bottom|left|inline|block)|margin-(?:top|right|bottom|left|inline|block)|box-shadow")
DECL = re.compile(r"(?<![\w-])(" + PROPS + r")\s*:\s*([^;{}]+?)\s*(?=;|\}|$)")


def strip_comments(text):
    text = re.sub(r"/\*.*?\*/", lambda m: "\n" * m.group(0).count("\n"), text, flags=re.S)
    return "\n".join(re.sub(r"(^|\s)//.*$", r"\1", ln) for ln in text.split("\n"))


def hard(v):
    """True ja vērtība satur cietu krāsu vai px/rem/em skaitli un nav no tokena."""
    if "var(" in v:
        return False
    return bool(HEX.search(v) or FUNC.search(v) or UNIT.search(v))


def scan_text(text):
    """-> [(rinda, vērtība)]"""
    out = []
    for n, line in enumerate(strip_comments(text).split("\n"), 1):
        taken = []
        for m in DECL.finditer(line):
            prop, val = m.group(1), m.group(2).strip().strip("\"'`,")
            if hard(val):
                out.append((n, f"{prop}:{val}"))
                taken.append(m.group(2))
        rest = line
        for t in taken:
            rest = rest.replace(t, " ")
        for m in TW.finditer(rest):
            if hard(m.group(0)):
                out.append((n, m.group(0)))
        rest = TW.sub(lambda m: " " if hard(m.group(0)) else m.group(0), rest)
        for rx in (FUNC, HEX):
            for m in rx.finditer(rest):
                out.append((n, m.group(0)))
            rest = rx.sub(" ", rest)
    return out


def files(root):
    res = []
    if os.path.isfile(os.path.join(root, "app", "globals.css")):
        res.append("app/globals.css")
    for d in ("components", "app"):
        for dp, dn, fs in os.walk(os.path.join(root, d)):
            dn[:] = sorted(x for x in dn if x not in SKIP_DIRS)
            for f in sorted(fs):
                if f.endswith(".tsx"):
                    res.append(os.path.relpath(os.path.join(dp, f), root).replace(os.sep, "/"))
    return res


def collect(root):
    found = []
    for rel in files(root):
        with open(os.path.join(root, rel), encoding="utf-8") as fh:
            for n, v in scan_text(fh.read()):
                found.append((rel, n, v))
    return found


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--strict", action="store_true")
    ap.add_argument("--root", default=DEFAULT_ROOT)
    ap.add_argument("--baseline", default=BASELINE)
    ap.add_argument("--update-baseline", action="store_true")
    a = ap.parse_args(argv)
    found = collect(a.root)
    if a.update_baseline:
        data = {}
        for rel, _, v in found:
            data.setdefault(rel, set()).add(v)
        with open(a.baseline, "w", encoding="utf-8") as fh:
            json.dump({"_": "token_guard baseline (V61 s6): esošās cietās vērtības; jaunas = brīdinājums",
                       "values": {k: sorted(x) for k, x in sorted(data.items())}}, fh, ensure_ascii=False, indent=1)
            fh.write("\n")
        print(f"token_guard: bāze atjaunota, {sum(len(x) for x in data.values())} vērtības")
        return 0
    with open(a.baseline, encoding="utf-8") as fh:
        base = {k: set(v) for k, v in json.load(fh)["values"].items()}
    new = [(r, n, v) for r, n, v in found if v not in base.get(r, set())]
    for r, n, v in new:
        print(f"BRĪDINĀJUMS token_guard: {r}:{n} {v} — nav no tokeniem (V61 6. solis)")
    print(f"token_guard: {len(found)} cietas vērtības, {len(new)} jaunas ārpus bāzes")
    return 1 if (new and a.strict) else 0


if __name__ == "__main__":
    sys.exit(main())
