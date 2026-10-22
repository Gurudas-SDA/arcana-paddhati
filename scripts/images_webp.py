# -*- coding: utf-8 -*-
"""Book pictures -> WebP q58 (Vraja Lila msg 5338, 19.10.2026; same quality as the parampara portraits, msg 5167).

* The originals are copied unchanged to masters/media/<same path> (never served) and stay in public/media/ as the
  fallback (<picture>) and for the PDF / EPUB (build_formats.py keeps using the PNG / JPG).
* The WebP is encoded from the original at its own size (no crop, no resize), method 6, quality 58; alpha kept.
  Its name carries the first 8 hex of its sha1 (Vraja msg 5334: a new name per content, so neither the HTTP cache nor
  the service worker can show an old picture).
* lib/webp-images.json maps "<path under public/media/>" -> "<webp path under public/media/>"; the app looks it up
  (lib/webpImages.ts). The cover WebP pair (874 / 440 px) is encoded from masters/media/cover/cover-clean.png = cover.jpg
  without its raster logo (V8, Vraja Lila msg 742: the app draws the logo as a vector — scripts/cover_clean_logo.py).

    python scripts/images_webp.py
"""
import hashlib
import io
import json
import shutil
from pathlib import Path

from PIL import Image

REPO = Path(__file__).resolve().parents[1]
MEDIA = REPO / "public" / "media"
MASTERS = REPO / "masters" / "media"
MAP = REPO / "lib" / "webp-images.json"
Q = 58
# the pictures the app shows (ca-logo: PDF / EPUB only — left as it is)
PICTURES = ["common/gaudiya-emblem.png", "common/paraphernalia.png", "common/tilak.png"]
# The app's WebP is encoded from a different master where the app draws the numbers itself (Vraja Lila msg 5429/5432,
# 20.10.2026: emblem numbers 1-12, 2.1-2.6 = HTML tags over the picture). The PNG with the burned-in numbers stays in
# public/media/ (PDF / EPUB) and masters/media/ (history); the clean master = scripts/emblem_clean_numbers.py output.
WEBP_SOURCE = {"common/gaudiya-emblem.png": MASTERS / "common" / "gaudiya-emblem-clean.png"}


def encode(im, out_stem):
    buf = io.BytesIO()
    im.save(buf, "WEBP", quality=Q, method=6)
    data = buf.getvalue()
    rel = f"{out_stem}-{hashlib.sha1(data).hexdigest()[:8]}.webp"
    for old in (MEDIA / rel).parent.glob(f"{Path(out_stem).name}-????????.webp"):
        old.unlink()
    (MEDIA / rel).write_bytes(data)
    return rel


def keep_master(rel):
    # The master is the untouched original: copied once, never overwritten (20.10.2026: public/media/common/tilak.png
    # is cropped symmetrically FROM masters/ — Vraja Lila msg 5392 — and must not replace its original).
    dst = MASTERS / rel
    if dst.exists():
        return
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(MEDIA / rel, dst)


def main():
    out = {}
    for rel in PICTURES:
        keep_master(rel)
        with Image.open(WEBP_SOURCE.get(rel, MEDIA / rel)) as im:
            im.load()
            img = im.convert("RGBA") if im.mode in ("RGBA", "LA", "P") else im.convert("RGB")
        out[rel] = encode(img, rel[:-4])
    keep_master("cover/cover.jpg")
    with Image.open(MASTERS / "cover" / "cover-clean.png") as im:
        big = im.convert("RGB")
    old = json.loads(MAP.read_text(encoding="utf-8")) if MAP.exists() else {}
    with Image.open(MEDIA / old.get("cover/cover-440.webp", "cover/cover-440.webp")) as im:
        small_size = im.size                                  # the existing 440 px variant's size, unchanged
    out["cover/cover.webp"] = encode(big, "cover/cover")
    out["cover/cover-440.webp"] = encode(big.resize(small_size, Image.LANCZOS), "cover/cover-440")
    MAP.write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    for k, v in out.items():
        print(f"{k} -> {v}  {(MEDIA / v).stat().st_size:,} B")


if __name__ == "__main__":
    main()
