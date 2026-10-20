"""Per-object pixel masks for the numbered pictures (components/Hotspots.tsx).

Why: an ellipse-shaped highlight also darkens parts of neighbouring objects
where they sit close together. Rule: exactly ONE object (with its printed
number) darkens, never a piece of a neighbour.

What: for every number in data/hotspots.json this builds an alpha mask of
that object's own line pixels (+ its printed number), dilated ~2 px and
slightly feathered, and writes it to public/media/hotspots/<image-stem>/<NN>.png (19.10.2026 media layout)
(white, alpha = mask). Ink pixels that belong to anything else are cut out
of the mask again after dilation/feathering, so a neighbour can never darken.
The JSON entry of the number gets "mask": "<file name>".

How: dark pixels -> connected components. A component belongs to the object
when enough of it lies inside the object's region (the hotspot ellipse, or a
hand-tuned polygon in CONFIG when objects touch). Components that touch
several objects (e.g. the tray under 1-3) are split by those polygons; lines
that belong to no numbered object (the tray rim) are removed via "exclude".

A picture with a layered SVG master (CONFIG "svg"; the «16 предметов» schematic, V20c — Vraja Lila msg 5658)
takes none of the above: the SVG is rasterised with Chromium (Playwright) and mask N = exactly the pixels of
layer N (the object and its printed number, as Vraja grouped them); the book's PNG and the lit picture come
from the same rasterisation, so mask and picture match pixel for pixel (build_svg). After it, rerun
scripts/images_webp.py (the app's WebP of the new PNG).

Run:  python scripts/build_hotspot_masks.py [--only common/tilak.png] [--check out_dir]
Needs numpy, scipy, Pillow (+ Playwright Chromium for "svg"). Rerun after changing a picture or CONFIG.
The svgo copy of a layered SVG: npx svgo@4.1.0 --config scripts/svgo/paraphernalia.svgo.config.mjs
  -i masters/media/common/paraphernalia-layers-original.svg -o masters/media/common/paraphernalia-layers.svg
"""
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "hotspots.json"
IMAGES = ROOT / "public" / "media"          # data keys are paths under it, e.g. "common/tilak.png"
OUT = IMAGES / "hotspots"

INK = 235        # luminance below this = a drawn pixel (incl. anti-aliasing)
DILATE = 2       # px grown around the object's own pixels
FEATHER = 0.8    # gaussian sigma of the soft edge (px)

# Per image, per number (pixel coordinates of the natural-size picture):
#   clip:  polygon; only pixels inside it can belong to the object
#   grow:  scale of the hotspot ellipse used as region when there is no clip
# Per image: exclude = rings (ellipse outlines, band in px) that belong to
# no object; inert = polygons that are not tap targets at all.
_TILAK_ELL = {"clip_ellipse": 1.15}

CONFIG = {
    # Vraja Lila's schematic from her layered SVG (V20c, msg 5658, 21.10.2026: «разбил всё по слоям и по номерам»):
    # layer _x31_ … _x31_8 (Illustrator's code for the ids "1" … "18") = object N with its printed number. The book
    # picture, every mask and the lit picture are rasterised from that SVG (Chromium) — mask N = exactly layer N,
    # no pixel guessing (build_svg). Master: masters/media/common/paraphernalia-layers.svg (svgo; Vraja's file
    # unchanged next to it as paraphernalia-layers-original.svg).
    "common/paraphernalia.png": {
        "svg": "masters/media/common/paraphernalia-layers.svg",
        "ink": True,
        # The Deities (layer "Deities"): never a tap target (Vaishnava etiquette). build_svg checks that the polygon
        # holds all of the Deities and none of objects 1-18 (the notch over the incense 4 raised to y 660: its smoke
        # reaches y 674 in the SVG; the Deities end at y 584 there).
        "inert": [[(85, 10), (1185, 10), (1185, 722), (1100, 724), (1060, 750), (900, 762), (830, 760), (760, 747),
                   (712, 732), (712, 714), (560, 714), (560, 660), (415, 660), (415, 714), (85, 714)]],
    },
    # Emblem of the Gauḍīya Maṭha (Śrīla Bhaktisiddhānta Sarasvatī Ṭhākura): fields enclosed by the sector lines.
    # The three Deity fields are numbered list items 10-12 HERE ONLY — Satkirti's exception of 06.10.2026 to
    # «Deities are not tap targets» (10 Mahāprabhu, 11 Rādhā-Kṛṣṇa, 12 Lakṣmī-Nārāyaṇa); no "inert" any more.
    "common/gaudiya-emblem.png": {
        "label_r": 18,
        "label_clip": False,
        "items": {
            "1": {"clip": [(404, 500), (450, 413), (550, 413), (598, 500), (550, 588), (450, 588)]},
            "2": {"seeds": [(488, 342), (610, 419), (602, 560), (500, 626), (382, 560), (392, 432)], "close": 4},
            # the six opulences one by one (sub-points of 2; clockwise from the top): yaśaḥ, śrīḥ, jñānam,
            # vairāgyam, aiśvaryam, vīryam — each the inscription in its own point of the star
            "2.1": {"seeds": [(488, 342)], "close": 4},
            "2.2": {"seeds": [(610, 419)], "close": 4},
            "2.3": {"seeds": [(602, 560)], "close": 4},
            "2.4": {"seeds": [(500, 626)], "close": 4},
            "2.5": {"seeds": [(382, 560)], "close": 4},
            "2.6": {"seeds": [(392, 432)], "close": 4},
            "3": {"seeds": [(300, 120)], "close": 14},
            "4": {"seeds": [(640, 100)], "close": 14},
            "5": {"seeds": [(120, 640)], "close": 14, "cut": [[(0, 0), (1000, 0), (1000, 622), (0, 622)]]},  # not the legs of the Deities' throne
            "6": {"seeds": [(880, 640)], "close": 14, "cut": [[(0, 0), (1000, 0), (1000, 648), (0, 648)]]},  # not the Deities' lotus base
            "7": {"seeds": [(300, 760)], "close": 14},
            "8": {"seeds": [(700, 760)], "close": 14},
            "9": {"seeds": [(455, 900)], "close": 14},
            # the Deities: tight polygons inside their fields (the figures touch the sector lines)
            "10": {"clip": [(422, 25), (578, 25), (575, 110), (556, 160), (533, 212), (519, 262), (478, 262), (463, 212), (422, 120)]},
            "11": {"clip": [(735, 292), (925, 288), (935, 330), (962, 420), (962, 598), (905, 616), (740, 616),
                            (733, 560), (702, 440), (712, 380)],
                   # the band's horizontal lines where they show beside the drawing
                   "cut": [[(912, 380), (1000, 380), (1000, 414), (912, 414)], [(690, 380), (738, 380), (738, 414), (690, 414)],
                           [(890, 572), (1000, 572), (1000, 600), (890, 600)], [(690, 572), (742, 572), (742, 600), (690, 600)]]},
            "12": {"clip": [(58, 330), (120, 300), (165, 280), (200, 300), (258, 318), (298, 372), (316, 405), (318, 560), (310, 612),
                            (130, 612), (36, 560), (26, 430)],
                   "cut": [[(0, 396), (46, 396), (46, 414), (0, 414)], [(294, 394), (400, 394), (400, 416), (294, 416)],
                           [(0, 588), (128, 588), (128, 612), (0, 612)], [(300, 588), (400, 588), (400, 612), (300, 612)]]},
        },
    },
    "common/tilak.png": {
        "label_r": 11,
        # Plain digits (no circles) with a white halo: each digit is its own
        # ink component, so take only components lying mostly in the circle.
        "label_clip": False,
        "items": {
            "1": {"clip": [(186.5, 52), (201.5, 52), (201.5, 124), (186.5, 124)]}, "2": _TILAK_ELL, "3": _TILAK_ELL, "4": _TILAK_ELL,
            "5": _TILAK_ELL, "8": _TILAK_ELL, "11": _TILAK_ELL, "12": _TILAK_ELL,
            # marks drawn over the arm outline: tight polygons around the mark
            "6": {"clip": [(40, 334), (56, 334), (52, 362), (51, 378), (42, 386), (37, 372), (40, 352)]},
            "7": {"clip": [(58, 236), (78, 238), (70, 266), (66, 284), (52, 286), (52, 266)]},
            "9": {"clip": [(321, 324), (333, 322), (338, 346), (340, 374), (331, 376), (326, 356)]},
            "10": {"clip": [(308, 240), (318, 238), (330, 262), (333, 286), (326, 288), (318, 276), (312, 262)]},
            # the crown (Reader v7.8, Satkirti 07.10.2026): the śikhā on the back view's crown — no printed
            # number; lit by «tat prakṣālana-toyaṁ tu / vāsudevāya mūrdhani» and «oṁ vāsudevāya namaḥ»
            "13": {"clip": [(520, 41), (556, 41), (556, 105), (520, 105)]},
        },
    },
}


def poly_mask(shape, pts):
    """Pixels whose centre (integer x, y) lies inside the polygon (even-odd)."""
    yy, xx = np.mgrid[0:shape[0], 0:shape[1]].astype(float)
    inside = np.zeros(shape, bool)
    pts = [tuple(map(float, p)) for p in pts]
    for (x1, y1), (x2, y2) in zip(pts, pts[1:] + pts[:1]):
        if y1 == y2:
            continue
        cross = ((y1 <= yy) & (yy < y2)) | ((y2 <= yy) & (yy < y1))
        xi = x1 + (yy - y1) * (x2 - x1) / (y2 - y1)
        inside ^= cross & (xx < xi)
    return inside


def seed_region(ink, seeds, close):
    """Region of a field enclosed by drawn lines (the emblem's sectors): the white area around each seed,
    with everything drawn inside it (holes filled) and the bays of objects that touch the field's own
    outline closed (radius `close` px). The enclosing lines themselves stay outside."""
    white, _ = ndi.label(~ink)
    reg = np.zeros_like(ink)
    disk = np.hypot(*np.mgrid[-close:close + 1, -close:close + 1]) <= close
    for x, y in seeds:
        comp = white == white[int(y), int(x)]
        comp = ndi.binary_fill_holes(comp)
        comp = ndi.binary_closing(np.pad(comp, close), structure=disk)[close:-close, close:-close]
        reg |= ndi.binary_fill_holes(comp)
    return reg


def build(name, spec, cfg):
    W, H = spec["w"], spec["h"]
    a = np.asarray(Image.open(IMAGES / name).convert("RGBA")).astype(float) / 255
    rgb = a[..., :3] * a[..., 3:4] + (1 - a[..., 3:4])
    lum = (rgb @ [0.299, 0.587, 0.114]) * 255
    ink = lum < INK
    yy, xx = np.mgrid[0:H, 0:W]
    ring = np.zeros_like(ink)
    for r in cfg.get("exclude", []):
        d = np.sqrt(((xx - r["cx"]) / r["rx"]) ** 2 + ((yy - r["cy"]) / r["ry"]) ** 2)
        ring |= np.abs(d - 1) * min(r["rx"], r["ry"]) <= r["band"]
    work = ink & ~ring
    lab, _ = ndi.label(work, structure=np.ones((3, 3)))
    sizes = np.bincount(lab.ravel())

    own = {}
    for n, s in spec["spots"].items():
        ic = cfg.get("items", {}).get(n, {})
        cx, cy = s["x"] / 100 * W, s["y"] / 100 * H
        rx, ry = s["rx"] / 100 * W, s["ry"] / 100 * H
        clip = "clip" in ic or "clip_ellipse" in ic or "seeds" in ic
        if "seeds" in ic:
            region = seed_region(ink, ic["seeds"], ic.get("close", 12))
        elif "clip" in ic:
            region = poly_mask(ink.shape, ic["clip"])
        else:
            g = ic.get("clip_ellipse", ic.get("grow", 1.25))
            region = ((xx - cx) / (rx * g)) ** 2 + ((yy - cy) / (ry * g)) ** 2 <= 1
        def pick(reg, clipped):
            inside = np.bincount(lab[reg].ravel(), minlength=len(sizes))
            frac = inside / np.maximum(sizes, 1)
            keep = (frac >= ic.get("min_frac", 0.5)) | clipped & (inside > 0)
            keep[0] = False
            return keep[lab] & reg

        m = pick(region, clip)
        if "lx" in s:
            # The printed number: only components lying mostly inside its
            # circle, unless the label touches a line ("label_clip").
            lx, ly = s["lx"] / 100 * W, s["ly"] / 100 * H
            lr = ic.get("label_r", cfg.get("label_r", 12))
            circle = (xx - lx) ** 2 + (yy - ly) ** 2 <= lr * lr
            m |= pick(circle, cfg.get("label_clip", False))
        for cut in ic.get("cut", []):
            m &= ~poly_mask(ink.shape, cut)
        own[n] = m

    # Each ink pixel may belong to one object only — except a sub-point ("2.1") and its whole ("2"), which
    # share their pixels by design.
    def family(a, b):
        return a == b or a.startswith(b + ".") or b.startswith(a + ".")

    others = {n: np.logical_or.reduce([m2 for k, m2 in own.items() if not family(n, k)] or [np.zeros_like(ink)])
              for n in own}
    conflicts = {}
    for n, m in own.items():
        c = int((m & others[n]).sum())
        if c:
            conflicts[n] = c

    stem = Path(name).stem
    masks = {}
    for n, m in own.items():
        mine = ndi.binary_dilation(m, iterations=1) & ink & ~(others[n] & ~m)
        foreign = ink & ~mine
        grown = ndi.binary_dilation(m, iterations=DILATE).astype(float)
        soft = np.clip(ndi.gaussian_filter(grown, FEATHER) * 1.4, 0, 1)
        soft[foreign] = 0
        soft[mine] = 1
        masks[n] = soft
    return masks, own, conflicts, lum, stem


# --- V20c: masks straight from the layers of Vraja Lila's SVG (msg 5658, 21.10.2026) -------------------------------

def svg_layer_id(n):
    """Illustrator's id of layer "n": every digit d as _x3d_, the first digit escaped only ("1" -> _x31_,
    "10" -> _x31_0, "18" -> _x31_8)."""
    return f"_x3{n[0]}_{n[1:]}"


# A printed number's glyph on the rasterised layer: one connected piece (lines >= 50 % coverage) of the number font's
# size, 21-26 px high, 12-19 px wide (measured on Vraja's SVG 21.10.2026: 14-17 x 23-24 for all 18 numbers; nothing
# else in the 18 layers has that size). Used for the tap target's label position only — the mask is the whole layer.
GLYPH_H = (21, 26)
GLYPH_W = (12, 19)


def number_glyphs(cov):
    """Boxes (x0, y0, x1, y1) of the number glyphs in one layer's coverage."""
    lab, _ = ndi.label(cov >= 0.5, structure=np.ones((3, 3)))
    out = []
    for sl in ndi.find_objects(lab):
        h, w = sl[0].stop - sl[0].start, sl[1].stop - sl[1].start
        if GLYPH_H[0] <= h <= GLYPH_H[1] and GLYPH_W[0] <= w <= GLYPH_W[1]:
            out.append((sl[1].start, sl[0].start, sl[1].stop, sl[0].stop))
    return out


_SVG_SETUP = """([w, h]) => { const s = document.querySelector('svg'); s.setAttribute('width', w); s.setAttribute('height', h);
  s.style.display = 'block'; const bg = document.getElementById('background'); if (bg) bg.remove(); }"""
_SVG_SHOW = """(ids) => { for (const c of document.querySelector('svg').children)
  if (c.tagName !== 'defs' && c.tagName !== 'style') c.style.display = ids === null || ids.includes(c.id) ? '' : 'none'; }"""
def render_svg(svg_path, w, h, layers):
    """Rasterise the SVG with Chromium (Playwright) at w x h, 1 px = 1 SVG unit. Returns the whole picture on white
    (luminance), the coverage 0..1 of every layer id in `layers` and the objects-only picture (all but the last id)."""
    import io
    import re
    from playwright.sync_api import sync_playwright
    svg = re.sub(r"^\s*<\?xml[^>]*>", "", Path(svg_path).read_text(encoding="utf8"))

    def shot(pg):
        a = np.asarray(Image.open(io.BytesIO(pg.screenshot(omit_background=True))).convert("RGBA")).astype(float)
        cov = a[..., 3] / 255
        lum = a[..., :3] @ [0.299, 0.587, 0.114]
        return cov, lum * cov + 255 * (1 - cov)

    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": w, "height": h}, device_scale_factor=1)
        pg.set_content(f'<!doctype html><html><body style="margin:0;background:transparent">{svg}</body></html>')
        pg.evaluate(_SVG_SETUP, [w, h])
        pg.evaluate(_SVG_SHOW, None)
        _, whole = shot(pg)
        pg.evaluate(_SVG_SHOW, list(layers[:-1]))
        _, objects = shot(pg)
        cov = {}
        for lid in layers:
            pg.evaluate(_SVG_SHOW, [lid])
            cov[lid], _ = shot(pg)
        b.close()
    return whole, cov, objects


def build_svg(name, spec, cfg):
    """Picture, masks and lit picture from the SVG layers: mask N = every pixel layer N covers (its lines and its
    printed number), nothing else. The spot geometry (tap ellipse = the object's box, label = its number's box)
    comes from the same layer. Writes public/media/<name> (the book's PNG, also PDF / EPUB). Returns problems
    instead of guessing when a layer is missing or has no number."""
    W, H = spec["w"], spec["h"]
    nums = sorted(spec["spots"], key=lambda n: [int(x) for x in n.split(".")])
    ids = {n: svg_layer_id(n) for n in nums}
    whole, cov, objects = render_svg(ROOT / cfg["svg"], W, H, [ids[n] for n in nums] + ["Deities"])
    Image.fromarray(whole.round().astype(np.uint8), "L").save(IMAGES / name, optimize=True)
    problems = []
    own, masks = {}, {}
    yy, xx = np.mgrid[0:H, 0:W]
    for n in nums:
        c = cov[ids[n]]
        m = c > 0
        if not m.any():
            problems.append(f"layer {ids[n]} (object {n}) missing or empty")
            continue
        own[n] = m
        masks[n] = m.astype(float)
        g = number_glyphs(c)
        if len(g) != len(n):
            problems.append(f"layer {ids[n]}: {len(g)} number glyphs, expected {len(n)} (number {n})")
            continue
        g = np.array(g)
        x0, y0, x1, y1 = g[:, 0].min(), g[:, 1].min(), g[:, 2].max(), g[:, 3].max()
        sp = spec["spots"][n]
        sp["lx"], sp["ly"] = round((x0 + x1) / 2 / W * 100, 2), round((y0 + y1) / 2 / H * 100, 2)
        label = (xx >= x0 - 3) & (xx < x1 + 3) & (yy >= y0 - 3) & (yy < y1 + 3)
        ys, xs = np.where((c >= 0.5) & ~label)
        sp["x"], sp["y"] = round((xs.min() + xs.max() + 1) / 2 / W * 100, 2), round((ys.min() + ys.max() + 1) / 2 / H * 100, 2)
        sp["rx"], sp["ry"] = round((xs.max() + 1 - xs.min()) / 2 / W * 100, 2), round((ys.max() + 1 - ys.min()) / 2 / H * 100, 2)
    conflicts = {}
    for n, m in own.items():
        k = int(sum((m & m2).sum() for n2, m2 in own.items() if n2 != n))
        if k:
            conflicts[n] = k
    inert = np.logical_or.reduce([poly_mask((H, W), p) for p in cfg.get("inert", [])] or [np.zeros((H, W), bool)])
    deities = cov["Deities"] > 0
    if cfg.get("inert") and (deities & ~inert).any():
        problems.append(f"{int((deities & ~inert).sum())} px of the Deities outside the inert polygon")
    for n, m in own.items():
        if (m & inert).any():
            problems.append(f"object {n}: {int((m & inert).sum())} px inside the inert polygon")
    return masks, own, conflicts, objects, problems


def main():
    data = json.loads(DATA.read_text(encoding="utf8"))
    OUT.mkdir(parents=True, exist_ok=True)
    check = sys.argv[sys.argv.index("--check") + 1] if "--check" in sys.argv else None
    ok = True
    only = sys.argv[sys.argv.index("--only") + 1] if "--only" in sys.argv else None
    for name, spec in data.items():
        if only and name != only:
            continue
        cfg = CONFIG.get(name, {})
        if "svg" in cfg:
            masks, own, conflicts, lit, problems = build_svg(name, spec, cfg)
            stem = Path(name).stem
            if problems:
                ok = False
                print(f"{name}: " + "; ".join(problems))
        else:
            masks, own, conflicts, lum, stem = build(name, spec, cfg)
        if conflicts:
            ok = False
            print(f"{name}: pixels claimed by several objects: {conflicts}")
        for n, soft in masks.items():
            head, *sub = n.split(".")
            fn = f"{stem}/{int(head):02d}" + "".join(f"-{x}" for x in sub) + ".png"  # "2.1" -> <stem>/02-1.png
            (OUT / stem).mkdir(parents=True, exist_ok=True)
            alpha = Image.fromarray((soft * 255).round().astype(np.uint8), "L")
            img = Image.new("LA", alpha.size, 255)
            img.putalpha(alpha)
            img.save(OUT / fn, optimize=True)
            spec["spots"][n]["mask"] = fn
            print(f"{name} {n}: {int(own[n].sum())} px -> {fn}")
        if cfg.get("ink"):
            spec["ink"] = write_ink(stem, lit)
            print(f"{name}: ink -> {spec['ink']}")
        else:
            spec.pop("ink", None)
        inert = cfg.get("inert", [])
        if inert:
            spec["inert"] = [[[round(x / spec["w"] * 100, 2), round(y / spec["h"] * 100, 2)] for x, y in p] for p in inert]
        else:
            spec.pop("inert", None)
        if check:
            preview(name, spec, masks, check)
    DATA.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf8")
    if not ok:
        sys.exit(1)


def write_ink(stem, lit):
    """The lit picture baked in advance (Vraja Lila msg 5637/5638, 20.10.2026: on the iPhone the SVG filter left the
    inner lines of a lit object grey). V20c: the objects 1-18 exactly as Vraja drew them (her SVG layers, no Deities,
    no tray), on white — `lit` = luminance 0..255. Written as <stem>/ink-<hash>.webp (lossless) next to the masks;
    the app draws it through the mask without any filter."""
    import hashlib
    import io
    img = Image.fromarray(np.asarray(lit).round().astype(np.uint8), "L")
    buf = io.BytesIO()
    img.save(buf, "WEBP", lossless=True, method=6)
    h = hashlib.sha1(buf.getvalue()).hexdigest()[:8]
    for old in (OUT / stem).glob("ink-*.webp"):
        old.unlink()
    fn = f"{stem}/ink-{h}.webp"
    (OUT / fn).write_bytes(buf.getvalue())
    return fn


def preview(name, spec, masks, out_dir):
    """Simulated highlight (faded picture + inked object) per number."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    a = np.asarray(Image.open(IMAGES / name).convert("RGBA")).astype(float) / 255
    rgb = a[..., :3] * a[..., 3:4] + (1 - a[..., 3:4])
    grey = rgb @ [0.299, 0.587, 0.114]
    faded = 1 - (1 - grey) * 0.3
    inked = rgb ** 3.2
    for n, soft in masks.items():
        lit = faded[..., None] * (1 - soft[..., None] + soft[..., None] * inked)
        Image.fromarray((lit * 255).astype(np.uint8)).save(out / f"{Path(name).stem}-{n}.png")


if __name__ == "__main__":
    main()
