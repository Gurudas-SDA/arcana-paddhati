# -*- coding: utf-8 -*-
"""Put Vraja Lila's prepared photo into a parampara page (oval drawn by code, no baking) — one command.
1. python scripts/parampara/replace_photo.py NN "<path to the photo>"   (NN = 00…08; photo 736:1000, PNG/JPG/WebP)
2. Optional: --contour contour.json  (figure outline [[x, y], …] in photo px — needed for L21, margin 5 %).
3. The master is copied unchanged to masters/parampara/ (outside public/, never served); WebP q90 (≤ 2× the box, never upscaled) + fallback → public/.
4. portraits.json, check.json and lib/parampara-portraits.json are updated; the L21 verdict is printed (or «контур не проверен»).
5. Then: npm run build && python qa/lint_content.py → commit (the app switches the page by the manifest; no code change).

How Lipikāra switches a page (19.10.2026: the code mask is published, every page 00–08 still «baked»):
  a. Wait for BOTH: Vraja's final photo (736:1000) AND Satkirti's decision on the 5 % margin (question №12) —
     the 18.10 master of 00 has only 1.98 % clearance, so L21 fails for it until Satkirti decides.
  b. Worktree from origin/main; source wk-libs/env.sh; replace_photo.py NN "<photo>" [--contour c.json]
     (00 with the 18.10 master: replace_photo.py 00 masters/parampara/00-pancha-tattva-2e085029e773.png — keeps its contour).
  c. The script removes public/media/parampara/NN-<slug>.png/.webp (baked page), writes photo/NN-<slug>-<hash>.webp + fallback;
     check L21 verdict, npm run build, qa/run_all.py (no --no-verify), npm run formats (PDF/EPUB draw the frame), screenshots
     desktop+mobile vs. before; git merge --no-ff into main, push, Actions green, check the live page.
  d. Going back to baked: set "mode": "baked" in portraits.json, restore NN-<slug>.png/.webp + its check.json entry from git,
     set lib/parampara-portraits.json entry to {"mode": "baked", width, height}, delete photo/NN-<slug>-*.

Vraja Lila 18.10.2026 (group msg 4997–4999, 5004, 5006): «никаких „впеканий" — все фото я подготовлю вручную
(кадрирование), кодом будут вставляться в овал»; every photo 736:1000 with the same safe area; replacing a page
must be fast. Pipeline rules: his «2026.10.18_image-pipeline-agent-prompt.md». The 5 % rule of Satkirti 07.10
(«тело никогда не обрезается, с запасом 5 %») is checked unchanged; a photo without a contour is reported as
not verified (L21 then fails until a contour is traced — no exception without Satkirti's decision).
"""
import argparse
import hashlib
import importlib.util
import json
import shutil
import sys
from pathlib import Path

from PIL import Image

sys.stdout.reconfigure(encoding="utf-8")
HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
MASTERS = REPO / "masters" / "parampara"          # 19.10.2026 media layout: originals outside public/
ALLOWED = {".png", ".jpg", ".jpeg", ".webp"}


def load_render():
    spec = importlib.util.spec_from_file_location("render_parampara", HERE / "render_parampara.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main():
    ap = argparse.ArgumentParser(description="Replace a parampara portrait with a prepared 736:1000 photo (code mask).")
    ap.add_argument("nn", help="page 00…08")
    ap.add_argument("photo", type=Path, help="Vraja's prepared photo (736:1000)")
    ap.add_argument("--contour", type=Path, help="JSON [[x, y], …] — figure outline in photo px")
    a = ap.parse_args()
    nn = a.nn.zfill(2)
    if nn not in {f"{i:02d}" for i in range(9)}:
        raise SystemExit(f"page {a.nn}: expected 00…08")
    ext = a.photo.suffix.lower()
    if ext not in ALLOWED:
        raise SystemExit(f"{a.photo.name}: extension {ext} not in {sorted(ALLOWED)}")
    raw = a.photo.read_bytes()
    with Image.open(a.photo) as im:
        im.verify()
    with Image.open(a.photo) as im:
        w, h = im.size
    r = load_render()
    r.check_aspect(w, h)                                   # never distort / never crop: 736:1000 only
    sha = hashlib.sha256(raw).hexdigest()

    m = r.manifest()
    old = m["portraits"].get(nn, {})
    if a.contour:
        contour = json.loads(a.contour.read_text(encoding="utf-8"))
        assert all(len(p) == 2 for p in contour), "contour: [[x, y], …]"
        note = f"from {a.contour.name}"
    elif old.get("master_sha256") == sha and old.get("contour"):
        contour, note = old["contour"], old.get("contour_note")   # same photo: its contour still applies
    else:
        contour, note = None, None                         # a new photo: an old contour does not apply

    MASTERS.mkdir(parents=True, exist_ok=True)
    master = MASTERS / f"{r.page_name(nn)}-{sha[:12]}{'.jpg' if ext == '.jpeg' else ext}"
    same = a.photo.resolve() == master.resolve()           # the master already kept here (e.g. 00, prepared 18.10)
    for f in MASTERS.glob(f"{nn}-*"):
        if f != master:
            f.unlink()
    if not same:
        shutil.copyfile(a.photo, master)                   # unchanged bytes (pipeline rule 1)
    assert hashlib.sha256(master.read_bytes()).hexdigest() == sha
    src_name = old.get("source_name") if same and old.get("master_sha256") == sha else a.photo.name
    m["portraits"][nn] = {"mode": "mask", "master": str(master.relative_to(REPO)), "source_name": src_name,
                          "master_sha256": sha, "contour": contour, "contour_note": note}
    r.save_manifest(m)

    report = r.only([nn])
    pg = next(p for p in report["pages"] if p["id"] == nn)
    print(f"\n{nn}: {w}x{h} (aspect {w / h:.4f}) — inscribed oval = the whole photo box, uniform scale only")
    print(f"   app: {pg['photo_webp'] or '(no WebP)'} + fallback {pg['photo_fallback']}  size {pg['photo_size']}")
    if not contour:
        print(f"   L21: контур не проверен — no figure contour for this photo; L21 FAILS for {nn} until one is traced"
              f" (--contour), margin stays 5 %")
    elif pg["all_inside"] and pg["min_clearance"] >= r.MARGIN:
        print(f"   L21: OK — whole figure inside, min clearance {pg['min_clearance'] * 100:.1f} % ≥ 5 %")
    else:
        print(f"   L21: FAIL — min clearance {pg['min_clearance'] * 100:.1f} % < 5 %"
              f"{'' if pg['all_inside'] else ' (contour point OUTSIDE the oval)'}; needs Satkirti's decision or a new photo")
    print("   next: npm run build && python qa/lint_content.py, then commit")


if __name__ == "__main__":
    main()
