"""PDF / EPUB cover with the Chaitanya Academy logo as Vraja Lila's vector (night release 21.10.2026; V8, msg 663/742).

The app draws the logo over the clean cover (masters/media/cover/cover-clean.png + components/CaLogo.tsx, placed by
app/globals.css .home-cover-logo: left 33.72 %, top 87.54 %, width 32.56 %, proportion 257.42 : 83.23, lettering
#110f0f). The printed book and the EPUB use one raster cover, so this script draws the same picture once, at twice the
cover's size (1748 x 2480, the vector stays sharp in print), with Chromium (Playwright), and writes
masters/media/cover/cover-print.jpg. scripts/formats/build_formats.py takes it when present (else public cover.jpg).

    python scripts/formats/cover_print.py
"""
import base64
import re
from pathlib import Path

from playwright.sync_api import sync_playwright

REPO = Path(__file__).resolve().parents[2]
CLEAN = REPO / "masters" / "media" / "cover" / "cover-clean.png"
SVG = REPO / "public" / "media" / "common" / "ca-logo.svg"
OUT = REPO / "masters" / "media" / "cover" / "cover-print.jpg"
W, H, SCALE = 874, 1240, 2


def main():
    svg = SVG.read_text(encoding="utf-8")
    svg = re.sub(r"<\?xml[^>]*\?>", "", svg)
    png = base64.b64encode(CLEAN.read_bytes()).decode()
    html = f"""<!doctype html><html><head><meta charset="utf-8"><style>
html,body{{margin:0;padding:0;background:#fff}}
.box{{position:relative;width:{W}px;height:{H}px;line-height:0}}
.box img{{width:{W}px;height:{H}px;display:block}}
.logo{{position:absolute;left:33.72%;top:87.54%;width:32.56%;aspect-ratio:257.42361/83.22854;color:#110f0f}}
.logo svg{{width:100%;height:100%;display:block}}
</style></head><body><div class="box"><img src="data:image/png;base64,{png}"/><div class="logo">{svg}</div></div></body></html>"""
    with sync_playwright() as p:
        b = p.chromium.launch(args=["--no-sandbox"])
        pg = b.new_page(viewport={"width": W, "height": H}, device_scale_factor=SCALE)
        pg.set_content(html)
        pg.wait_for_load_state("networkidle")
        pg.locator(".box").screenshot(path=str(OUT), type="jpeg", quality=92)
        b.close()
    print(OUT)


if __name__ == "__main__":
    main()
