"""L21 field around the figure (19.10.2026): Satkirti's rule 105 «фигура никогда не обрезается… вокруг есть поле…
в овальной рамке фигура полностью внутри» has no number; L21 requires a field ≥ 1.5 % of the oval width
(Lipikāras 19.10 tehniskais lēmums, Vraja msg 5143). Checked on temporary COPIES of the tree (never the real files):
  a) the real data → L21 passes (portrait 00 = Vraja's photo masked by code, clearance 2.0 %);
  b) one contour point of 00 at 1.0 % from the oval edge → L21 FAIL («too close»);
  c) one contour point of 00 outside the oval → L21 FAIL («OUTSIDE»);
  d) one contour point of 00 at 1.6 % → L21 still passes (the threshold is 1.5 %, not the old 5 %);
  e) portrait 00 WebP weight (Vraja Lila msg 5167, 19.10): q58 method 6, 736 px, recorded in portraits.json/check.json,
     the served WebP ≤ 125 KB (test: q58 = 119 KB, SSIM 0.919) and its file exists.
usage: python s46_l21_field.py
"""
import contextlib
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))
import qa  # noqa: E402

REPO = qa.REPO
LINT = os.path.join(REPO, "qa", "lint_content.py")
res = []


def chk(name, ok, ev=""):
    res.append(bool(ok))
    print(f"  [{'PASS' if ok else 'FAIL'}] data {name} {ev if not ok else ''}".rstrip(), flush=True)


def lint_l21(root):
    out = os.path.join(root, "lint.json")
    with contextlib.suppress(FileNotFoundError):
        os.remove(out)
    t0 = time.time() - 1
    p = subprocess.run([sys.executable, LINT, "--no-html", "--json", out], capture_output=True, text=True,
                       encoding="utf-8", errors="replace", cwd=REPO, env=dict(os.environ, QA_REPO=root))
    rr = json.load(open(out, encoding="utf-8")) if os.path.exists(out) and os.path.getmtime(out) >= t0 else None
    l21 = next((c for c in rr or [] if c["id"] == "L21"), None)
    return l21, (p.stdout or "") + (p.stderr or "")[-300:]


def copy_tree():
    tmp = tempfile.mkdtemp(prefix="s46_l21_")
    for d in ("data", "lib", "masters", os.path.join("public", "media"), os.path.join("scripts", "parampara")):
        shutil.copytree(os.path.join(REPO, d), os.path.join(tmp, d), ignore=shutil.ignore_patterns("desktop.ini", "__pycache__"))
    return tmp


def with_point(tmp, pt):
    f = os.path.join(tmp, "scripts", "parampara", "check.json")
    d = json.load(open(f, encoding="utf-8"))
    pg = next(p for p in d["pages"] if p["id"] == "00")
    cx, cy, cw, ch = pg["crop"]
    x = cx - cw / 2 + pt * cw          # on the horizontal axis, pt × oval width inside the left vertex (< 0 = outside)
    pg["hull"] = pg["hull"] + [[round(x, 2), cy]]
    json.dump(d, open(f, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


def case(name, pt, want_ok, want_text=None):
    tmp = copy_tree()
    try:
        if pt is not None:
            with_point(tmp, pt)
        l21, tail = lint_l21(tmp)
        ok = l21 is not None and l21["ok"] is want_ok and (want_text is None or want_text in tail)
        chk(name, ok, f"L21 {l21} | {tail[-400:]}")
        if ok and want_text:
            print("        " + next(l.strip() for l in tail.splitlines() if want_text in l)[:160], flush=True)
    finally:
        shutil.rmtree(tmp, onexc=lambda fn, q, e: (os.chmod(q, stat.S_IWRITE), fn(q)))


case("a real data → L21 passes (00 masked by code, field 2.0 %)", None, True)
case("b a contour point at 1.0 % of the oval width → L21 FAIL (too close)", 0.010, False, "too close")
case("c a contour point outside the oval → L21 FAIL (OUTSIDE)", -0.01, False, "OUTSIDE")
case("d a contour point at 1.6 % → L21 passes (threshold 1.5 %, not 5 %)", 0.016, True)

def webp_weight():
    man = json.load(open(os.path.join(REPO, "scripts", "parampara", "portraits.json"), encoding="utf-8"))["portraits"]["00"]
    pg = next(p for p in json.load(open(os.path.join(REPO, "scripts", "parampara", "check.json"), encoding="utf-8"))["pages"]
              if p["id"] == "00")
    rel = pg.get("photo_webp")
    f = os.path.join(REPO, "public", "media", rel) if rel else None
    size = os.path.getsize(f) if f and os.path.exists(f) else None
    ok = (man.get("webp_quality") == 58 and pg.get("webp_quality") == 58 and size is not None and size <= 125_000
          and pg.get("photo_size") == [736, 1000])
    chk("e 00 WebP q58 (Vraja msg 5167): recorded in portraits.json + check.json, ≤ 125 KB, 736x1000", ok,
        f"manifest q={man.get('webp_quality')} check q={pg.get('webp_quality')} file={rel} size={size} {pg.get('photo_size')}")
    if ok:
        print(f"        {rel}: {size:,} B", flush=True)


webp_weight()
print(f"s46: {sum(res)}/{len(res)} passed", flush=True)
sys.exit(0 if res and all(res) else 1)
