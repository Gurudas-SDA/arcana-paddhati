"""Cover without the raster Chaitanya Academy logo (V8, Vraja Lila msg 663/742, 20.10.2026).

The app draws the logo itself as a vector (components/CaLogo.tsx over the cover, components/HomePage.tsx), so the
app's cover WebP pair is encoded from this clean master (scripts/images_webp.py WEBP_SOURCE). The logo area
(x 272-602, y 1078-1188 of the 874 x 1240 cover; logo ink x 280-593, y 1085-1179) is filled with the cover's own
plain background (245, 238, 222 — uniform there, std 0). masters/media/cover/cover.jpg (original) and
public/media/cover/cover.jpg (PDF / EPUB cover, <img> fallback) keep their logo.

    python scripts/cover_clean_logo.py
"""
from pathlib import Path

from PIL import Image, ImageDraw

REPO = Path(__file__).resolve().parents[1]
SRC = REPO / "masters" / "media" / "cover" / "cover.jpg"
OUT = REPO / "masters" / "media" / "cover" / "cover-clean.png"
BOX = (272, 1078, 602, 1188)
BG = (245, 238, 222)

im = Image.open(SRC).convert("RGB")
ImageDraw.Draw(im).rectangle(BOX, fill=BG)
im.save(OUT, optimize=True)
print(OUT, im.size)
