"""token_guard — V61 solis 7 (s6 → s7). Vraja Lila lēmums (msg 7207, 01.11):
«по поводу новых токенов и системы — лучше автоматом подгоняй под имеющуюся и если будет просьба сделать исключение и она обоснованна — то окей».
Agrāk (s6; msg 1920, 30.10; msg 7164, 31.10): «Автоматическая проверка перед выпуском: сначала предупреждает о новых значениях не из токенов,
позже — останавливает». Tagad PĒC NOKLUSĒJUMA BLOĶĒ (exit 1, ja ir jaunas cietas vērtības ārpus bāzes un izņēmumiem); `--warn` = vecais
tikai-brīdinājums (exit 0). Katrai jaunajai vērtībai paziņojumā tiek IETEIKTS tuvākais esošais tokens (krāsai — tuvākais krāsas tokens no
design-system/tokens.css pēc RGB attāluma; px izmēram — tuvākais no --space-* / --radius-* skalas, piem. «13px → var(--space-12)»);
`--fix` (V61 s8, Vraja Lila msg 7250 «автоматически на ближайший токен», 7251 «до и после») pats aizstāj JAUNU cietu vērtību ar tuvākā tokena var(--…)
(tā pati īpašību grupa: krāsa → krāsas tokens, atstarpe → --space-*, rādiuss → rādiusa tokens); bāze un izņēmumi netiek aiztikti; ja grupā tokena nav /
vērtība nav nosakāma (hsl, alfa, width/top/font-size, 0, negatīva, krāsa .tsx teksta literālī) — atstāj un bloķē kā līdz šim. `--report FILE` raksta Markdown «до / после».
Izņēmumi: qa/token_guard_exceptions.json — saraksts [{"value","file","reason","who"}] (who = msg Nr.); vērtība, kas ir izņēmumos, nav kļūda.
Ieraksts bez reason vai who (vai value/file) ir nederīgs → token_guard kļūda (exit 1; arī ar --warn).

Skatās UI kodu (app/globals.css, components/**/*.tsx, app/**/*.tsx) un salīdzina «cietās» vērtības ar bāzes sarakstu
qa/token_guard_baseline.json (esošās vērtības; šodien brīdinājumu nav). Ķer:
  - krāsas #hex, rgb()/rgba()/hsl()/hsla();
  - Tailwind arbitrary klases ar px/rem/em vai krāsu: p-[13px], rounded-[10px], gap-[7px], text-[#abc123] (bez var(...));
  - CSS/inline deklarācijas padding/margin/gap/border-radius/color/background(-color)/border-color/top/left/... ar skaitli+vienību vai
    krāsu, ja vērtībā nav var(--…).
Neķer: 0, auto, %, vh/vw, calc bez px/krāsas, vērtības no var(--…), komentārus; design-system/tokens.css, qa/, node_modules, out, .next netiek skenēti.
Bāze: (fails, vērtība) pāri — rindu numuri nav svarīgi, tāpēc rindu nobīde neradīs brīdinājumu.
Lietošana: python qa/token_guard.py [--warn] [--fix [--report FILE]] [--root DIR] [--update-baseline] [--exceptions FILE]
"""
import argparse
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_ROOT = os.path.normpath(os.path.join(HERE, ".."))
BASELINE = os.path.join(HERE, "token_guard_baseline.json")
EXCEPTIONS = os.path.join(HERE, "token_guard_exceptions.json")
SKIP_DIRS ={"node_modules", "out", ".next", "qa", ".git", "design-system"}

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


# ---------- ieteikumi: tuvākais esošais tokens ----------
def _tokens_css(root):
    p = os.path.join(root, "design-system", "tokens.css")
    if not os.path.isfile(p):
        p = os.path.join(DEFAULT_ROOT, "design-system", "tokens.css")
    with open(p, encoding="utf-8") as fh:
        return strip_comments(fh.read())


def _rgb(h):
    h = h.lstrip("#")
    if len(h) in (3, 4):
        h = "".join(c * 2 for c in h[:3])
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def load_scales(root):
    css = _tokens_css(root)
    colors, spaces, radii = [], [], []
    seen_names = set()
    for name, val in re.findall(r"(--[\w-]+)\s*:\s*([^;]+);", css):
        val = val.strip()
        if name in seen_names:  # tikai pirmā definīcija (:root, dienas vērtība); tēmu pārdefinējumi (sēpija/nakts) neskaitās
            continue
        seen_names.add(name)
        if re.fullmatch(r"#[0-9a-fA-F]{6}|#[0-9a-fA-F]{3}", val):
            colors.append((name, _rgb(val)))
        m = re.fullmatch(r"(\d+(?:\.\d+)?)px", val)
        if m and float(m.group(1)) < 1000:
            if name.startswith("--space-"):
                spaces.append((name, float(m.group(1))))
            elif "radius" in name:
                radii.append((name, float(m.group(1))))
    return colors, spaces, radii


def _num_px(tok):
    m = re.fullmatch(r"(-?\d*\.?\d+)(px|rem|em)", tok)
    if not m:
        return None
    return float(m.group(1)) * (16 if m.group(2) in ("rem", "em") else 1)


def _nearest_colour(c, colors):
    return min(colors, key=lambda x: sum((a - b) ** 2 for a, b in zip(c, x[1])))[0]


def suggest(v, scales):
    """vērtība (kā atrasta) -> ieteikuma teksts («13px → var(--space-12)») vai ''"""
    colors, spaces, radii = scales
    parts, seen = [], set()
    for m in HEX.finditer(v):
        t = m.group(0)
        if t in seen or len(t) not in (4, 5, 7, 9) or not colors:
            continue
        seen.add(t)
        parts.append(f"{t} → var({_nearest_colour(_rgb(t), colors)})")
    for m in FUNC.finditer(v):
        nums = re.findall(r"\d+", m.group(0))
        if m.group(0).lower().startswith("rgb") and len(nums) >= 3 and colors:
            c = tuple(int(x) for x in nums[:3])
            parts.append(f"{m.group(0)} → var({_nearest_colour(c, colors)})")
    scale = radii if "radius" in v.lower() else spaces
    for m in UNIT.finditer(re.sub(r"#[0-9a-fA-F]+", " ", v)):
        t = m.group(0)
        px = _num_px(t)
        if px is None or not scale or t in seen:
            continue
        seen.add(t)
        name = min(scale, key=lambda x: (abs(x[1] - px), x[1]))[0]
        parts.append(f"{t} → var({name})")
    return "; ".join(parts)


# ---------- --fix: automātiska aizstāšana ar tuvāko tokenu ----------
COLOR_PROPS = {"color", "background", "background-color", "border-color", "outline"}
SPACE_PROPS = {"padding", "margin", "gap", "row-gap", "column-gap"} | {f"{a}-{b}" for a in ("padding", "margin")
               for b in ("top", "right", "bottom", "left", "inline", "block")}
RADIUS_PROPS = {"border-radius"}
ANY = re.compile(FUNC.pattern + "|" + HEX.pattern + "|" + UNIT.pattern, re.I)
TW_SPACE = re.compile(r"^((?:[\w!-]+:)*)(?:p|px|py|pt|pr|pb|pl|ps|pe|m|mx|my|mt|mr|mb|ml|ms|me|gap|gap-x|gap-y|space-x|space-y)-\[([^\]]+)\]$")
TW_RADIUS = re.compile(r"^((?:[\w!-]+:)*)rounded(?:-(?:t|b|l|r|s|e|tl|tr|bl|br|ss|se|es|ee))?-\[([^\]]+)\]$")
TW_COLOR = re.compile(r"^((?:[\w!-]+:)*)(?:text|bg|border|border-[xytblrse]|fill|stroke|outline|ring|from|to|via|divide|accent|caret|decoration|placeholder)-\[([^\]]+)\]$")
NOT_COLOUR_CTX = re.compile(r"(href|id|htmlFor|hash|location|url)\s*[=:(]?\s*[\"'(]?\s*$", re.I)


def token_values(root):
    out = {}
    for n, v in re.findall(r"(--[\w-]+)\s*:\s*([^;]+);", _tokens_css(root)):
        out.setdefault(n, v.strip())
    return out


def fix_string(s, kind, scales, tv):
    """s — vērtības teksts; kind = 'color' | 'space' | 'radius' | None -> (jaunais teksts, [(vecais, tokens, tokena vērtība, starpība)]) vai None."""
    colors, spaces, radii = scales
    changes = []
    bad = []

    def sub(m):
        t = m.group(0)
        if t[0] == "#" or t.lower().startswith(("rgb", "hsl")):
            if kind != "color" or not colors:
                bad.append(t)
                return t
            if t[0] == "#":
                if len(t) not in (4, 7):
                    bad.append(t)
                    return t
                c = _rgb(t)
            else:
                nums = re.findall(r"\d+(?:\.\d+)?", t)
                if not t.lower().startswith("rgb") or len(nums) < 3 or (len(nums) == 4 and float(nums[3]) != 1) or len(nums) > 4 \
                        or any(float(x) > 255 for x in nums[:3]):
                    bad.append(t)
                    return t
                c = tuple(int(float(x)) for x in nums[:3])
            name = _nearest_colour(c, colors)
            tc = dict(colors)[name]
            big = max(abs(a - b) for a, b in zip(c, tc)) >= 16  # tehniskais slieksnis Lipikāra, nav S/V noteikums
            changes.append((t, name, tv.get(name, ""), "ΔRGB %d" % round(sum((a - b) ** 2 for a, b in zip(c, tc)) ** 0.5), big))
            return f"var({name})"
        scale = {"space": spaces, "radius": radii}.get(kind)
        px = None if t.startswith("-") else _num_px(t)
        if not scale or not px:
            bad.append(t)
            return t
        name, npx = min(scale, key=lambda x: (abs(x[1] - px), x[1]))
        d = npx - px
        big = abs(d) >= 4 or abs(d) / px >= 0.2  # tehniskais slieksnis Lipikāra, nav S/V noteikums
        changes.append((t, name, tv.get(name, ""), ("%+g" % d).replace("-", "−") + "px", big))
        return f"var({name})"

    out = ANY.sub(sub, s)
    if bad or not changes:
        return None
    return out, changes


def tw_kind(cls):
    for rx, kind in ((TW_SPACE, "space"), (TW_RADIUS, "radius"), (TW_COLOR, "color")):
        m = rx.match(cls)
        if m:
            return kind, m
    return None, None


def selector_for(rel, text, n):
    """CSS — selektors tuvākajā rindā ar «{» (uz augšu); .tsx — komponenta fails (+ rinda)."""
    if not rel.endswith(".css"):
        return f"{os.path.basename(rel)} (komponents, rinda {n})"
    lines = text.split("\n")
    for i in range(n - 1, -1, -1):
        if "{" in lines[i]:
            sel = lines[i].split("{")[0].strip()
            if sel:
                return sel
            if i > 0 and lines[i - 1].strip():
                return lines[i - 1].strip().rstrip(",")
    return ""


def fix_file(rel, text, items, scales, tv):
    """items = [(rel, n, v)] -> (jaunais teksts, [(n, īpašība, vecais, tokens, vērtība, starpība)], [neizlabotie items])"""
    lines = text.split("\n")
    orig = text
    done, left = [], []
    is_css = rel.endswith(".css")
    for _, n, v in items:
        O = lines[n - 1]
        ok = False
        mp = re.match(r"^([a-z-]+):(.*)$", v, re.S)
        if mp and mp.group(1) in (COLOR_PROPS | SPACE_PROPS | RADIUS_PROPS | {"border", "outline"} | set(re.findall(r"[a-z-]+", PROPS))):
            prop, val = mp.group(1), mp.group(2)
            kind = "color" if prop in COLOR_PROPS else "space" if prop in SPACE_PROPS else "radius" if prop in RADIUS_PROPS else None
            for m in DECL.finditer(O):
                if m.group(1) == prop and m.group(2).strip().strip("\"'`,") == val:
                    r = fix_string(m.group(2), kind, scales, tv)
                    if r:
                        lines[n - 1] = O[:m.start(2)] + r[0] + O[m.end(2):]
                        done += [(n, prop, *c, selector_for(rel, orig, n)) for c in r[1]]
                        ok = True
                    break
        elif re.search(r"-\[", v):
            kind, m = tw_kind(v)
            if kind:
                inner = m.group(2)
                r = fix_string(inner, kind, scales, tv)
                if r and v in O:
                    new_in = f"color:{r[0]}" if kind == "color" else r[0]
                    new = v.replace("[" + inner + "]", "[" + new_in + "]", 1)
                    lines[n - 1] = O.replace(v, new, 1)
                    done += [(n, v.split("-[")[0] + "-[…]", *c, selector_for(rel, orig, n)) for c in r[1]]
                    ok = True
        elif is_css and v in O and not NOT_COLOUR_CTX.search(O[:O.find(v)]):
            r = fix_string(v, "color", scales, tv)
            if r:
                lines[n - 1] = O.replace(v, r[0], 1)
                done += [(n, "color", *c, selector_for(rel, orig, n)) for c in r[1]]
                ok = True
        if not ok:
            left.append((rel, n, v))
    return "\n".join(lines), done, left


def write_report(path, changes):
    import datetime
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(f"# token_guard — замены до и после ({datetime.date.today():%Y.%m.%d})\n\n"
                 "Новые «жёсткие» значения автоматически заменены ближайшим токеном (Враджа Лила, msg 7250/7251).\n\n"
                 "Метка «заметно»: отступ/размер/радиус — разница ≥ 4px или ≥ 20 %; цвет — любой канал ≥ 16 из 255; остальное — «мелко».\n\n"
                 "| Файл:строка | Свойство | до | после | разница | заметность | селектор |\n|---|---|---|---|---|---|---|\n")
        for rel, n, prop, old, tok, val, d, big, sel in changes:
            fh.write(f"| {rel}:{n} | {prop} | {old} | var({tok}) = {val} | {d} | {'заметно' if big else 'мелко'} | "
                     f"{sel.replace('|', '/') if big else ''} |\n")


def load_exceptions(path):
    """-> (set((file, value)), [kļūdas])"""
    if not os.path.isfile(path):
        return set(), []
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    items = data.get("exceptions", []) if isinstance(data, dict) else data
    ok, errs = set(), []
    for i, e in enumerate(items):
        miss = [k for k in ("value", "file", "reason", "who") if not (isinstance(e, dict) and str(e.get(k, "")).strip())]
        if miss:
            errs.append(f"izņēmums #{i + 1} nederīgs — trūkst: {', '.join(miss)}")
        else:
            ok.add((e["file"], e["value"]))
    return ok, errs


def is_excepted(exc, rel, v):
    bare = v.split(":", 1)[1] if re.match(r"^[a-z-]+:", v) else v
    return any(f in (rel, "*") and x in (v, bare) for f, x in exc)


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
    ap.add_argument("--warn", action="store_true", help="tikai brīdinājums (exit 0)")
    ap.add_argument("--strict", action="store_true", help="(vecais karogs; tagad noklusējums)")
    ap.add_argument("--root", default=DEFAULT_ROOT)
    ap.add_argument("--baseline", default=BASELINE)
    ap.add_argument("--exceptions", default=EXCEPTIONS)
    ap.add_argument("--update-baseline", action="store_true")
    ap.add_argument("--fix", action="store_true", help="aizstāt jaunās vērtības ar tuvāko tokenu")
    ap.add_argument("--report", default="", help="--fix: Markdown «до / после» fails")
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
    exc, errs = load_exceptions(a.exceptions)
    for e in errs:
        print(f"KĻŪDA token_guard: {os.path.basename(a.exceptions)}: {e}")
    new = [(r, n, v) for r, n, v in found if v not in base.get(r, set()) and not is_excepted(exc, r, v)]
    scales = load_scales(a.root)
    if a.fix and new:
        tv = token_values(a.root)
        allch, left = [], []
        for rel in sorted({r for r, _, _ in new}):
            fp = os.path.join(a.root, rel)
            with open(fp, encoding="utf-8") as fh:
                text = fh.read()
            t2, done, lf = fix_file(rel, text, [x for x in new if x[0] == rel], scales, tv)
            if done:
                with open(fp, "w", encoding="utf-8") as fh:
                    fh.write(t2)
            allch += [(rel, *d) for d in done]
            left += lf
        for rel, n, prop, old, tok, val, d, big, sel in allch:
            print(f"token_guard --fix: {rel}:{n} {old} → var({tok}) (vērtība {val}; {prop}; {d}; {'заметно' if big else 'мелко'})")
        nz = sum(1 for c in allch if c[7])
        print(f"token_guard --fix: aizstātas {len(allch)} vērtības, atstātas {len(left)}")
        if nz:
            print(f"TOKEN_FIX ZAMETNO: {nz}")
        if a.report and allch:
            write_report(a.report, allch)
        new = left
    label = "BRĪDINĀJUMS" if a.warn else "KĻŪDA"
    for r, n, v in new:
        s = suggest(v, scales)
        print(f"{label} token_guard: {r}:{n} {v} — nav no tokeniem" + (f"; ieteikums: {s}" if s else "")
              + " (vai izņēmums ar reason+who: qa/token_guard_exceptions.json)")
    print(f"token_guard: {len(found)} cietas vērtības, {len(new)} jaunas ārpus bāzes un izņēmumiem")
    if errs:
        return 1
    return 1 if (new and not a.warn) else 0


if __name__ == "__main__":
    sys.exit(main())
