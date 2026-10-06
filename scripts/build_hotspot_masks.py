"""Per-object pixel masks for the numbered pictures (components/Hotspots.tsx).

Why: an ellipse-shaped highlight also darkens parts of neighbouring objects
where they sit close together. Rule: exactly ONE object (with its printed
number) darkens, never a piece of a neighbour.

What: for every number in data/hotspots.json this builds an alpha mask of
that object's own line pixels (+ its printed number), dilated ~2 px and
slightly feathered, and writes it to public/images/hotspots/<image>-<NN>.png
(white, alpha = mask). Ink pixels that belong to anything else are cut out
of the mask again after dilation/feathering, so a neighbour can never darken.
The JSON entry of the number gets "mask": "<file name>".

How: dark pixels -> connected components. A component belongs to the object
when enough of it lies inside the object's region (the hotspot ellipse, or a
hand-tuned polygon in CONFIG when objects touch). Components that touch
several objects (e.g. the tray under 1-3) are split by those polygons; lines
that belong to no numbered object (the tray rim) are removed via "exclude".

Run:  python scripts/build_hotspot_masks.py [--check out_dir]
Needs numpy, scipy, Pillow. Rerun after changing a picture or CONFIG.
"""
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "hotspots.json"
IMAGES = ROOT / "public" / "images"
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
    "Parafernalia.png": {
        # Rim of the big tray under 1-3: belongs to no numbered object.
        "exclude": [{"cx": 276, "cy": 307.5, "rx": 69.5, "ry": 38.5, "band": 3.5}],
        # The Deities: never a tap target (Vaishnava etiquette).
        "inert": [[(236, 14), (476, 14), (476, 182), (360, 182), (330, 176), (236, 176)]],
        "items": {
            # cup with its spoon (the spoon crosses the bell's saucer)
            "1": {"clip": [(234, 301.5), (266, 301.5), (266.5, 287), (274.4, 287), (274, 301.5),
                           (276, 301.5), (276, 344), (234, 344)]},
            "2": {"clip": [(273, 271), (333, 271), (335, 300), (331, 324), (273, 324)]},
            # bell on its saucer (stops at the spoon and at the incense holder)
            "3": {"clip": [(242.6, 234), (257.6, 234), (258.5, 243.5), (261.5, 246.5), (261.5, 262), (266, 276), (266.5, 287),
                           (264, 301), (240, 301), (230, 296), (230, 279), (241, 268), (242.6, 262)]},
            "4": {"clip": [(262, 176), (288, 176), (292, 222), (300, 238), (302, 258),
                           (286, 258), (261.6, 252), (261.6, 246.6), (258.6, 243.6),
                           (257.7, 234), (257.7, 222)]},
            "5": {"clip": [(196, 222), (242, 222), (242.5, 247), (238, 260), (196, 260)]},
            "11": {"clip": [(480, 240), (652, 240), (652, 378), (480, 378)]},
            "12": {"clip": [(40, 250), (200, 250), (200, 378), (40, 378)]},
            "14": {"clip": [(282, 377), (296, 375.5), (322, 375), (348, 377), (360, 418), (282, 418)]},
            "15": {"clip": [(274, 352), (322, 352), (322, 374), (296, 374.5), (274, 376)]},
        },
    },
    # Emblem of the Gauḍīya Maṭha (Śrīla Bhaktisiddhānta Sarasvatī Ṭhākura): fields enclosed by the sector lines.
    # The three Deity fields are numbered list items 10-12 HERE ONLY — Satkirti's exception of 06.10.2026 to
    # «Deities are not tap targets» (10 Mahāprabhu, 11 Rādhā-Kṛṣṇa, 12 Lakṣmī-Nārāyaṇa); no "inert" any more.
    "Gaudiya_emblem.png": {
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
    "Tilak.png": {
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


def main():
    data = json.loads(DATA.read_text(encoding="utf8"))
    OUT.mkdir(parents=True, exist_ok=True)
    check = sys.argv[sys.argv.index("--check") + 1] if "--check" in sys.argv else None
    ok = True
    for name, spec in data.items():
        cfg = CONFIG.get(name, {})
        masks, own, conflicts, lum, stem = build(name, spec, cfg)
        if conflicts:
            ok = False
            print(f"{name}: pixels claimed by several objects: {conflicts}")
        for n, soft in masks.items():
            head, *sub = n.split(".")
            fn = f"{stem}-{int(head):02d}" + "".join(f"-{x}" for x in sub) + ".png"  # "2.1" -> <stem>-02-1.png
            alpha = Image.fromarray((soft * 255).round().astype(np.uint8), "L")
            img = Image.new("LA", alpha.size, 255)
            img.putalpha(alpha)
            img.save(OUT / fn, optimize=True)
            spec["spots"][n]["mask"] = fn
            print(f"{name} {n}: {int(own[n].sum())} px -> {fn}")
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
