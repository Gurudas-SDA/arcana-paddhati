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

Run:  python scripts/build_hotspot_masks.py [--only common/tilak.png] [--check out_dir]
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
IMAGES = ROOT / "public" / "media"          # data keys are paths under it, e.g. "common/tilak.png"
OUT = IMAGES / "hotspots"

INK = 235        # luminance below this = a drawn pixel (incl. anti-aliasing)
DILATE = 2       # px grown around the object's own pixels
FEATHER = 0.8    # gaussian sigma of the soft edge (px)
DARK = 128       # luminance below this = a black stroke (printed numbers), not a grey rim

# Per image, per number (pixel coordinates of the natural-size picture):
#   clip:  polygon; only pixels inside it can belong to the object
#   grow:  scale of the hotspot ellipse used as region when there is no clip
# Per image: exclude = rings (ellipse outlines, band in px) that belong to
# no object; inert = polygons that are not tap targets at all.
_TILAK_ELL = {"clip_ellipse": 1.15}

CONFIG = {
    # Vraja Lila's schematic (20.10.2026 msg 736/738; 1254 x 1254, three Deities + objects 1-18).
    "common/paraphernalia.png": {
        "label_r": 18,   # printed numbers ~30 x 24 px: both digits of "10"-"18" lie inside the circle
        "solid": 5,      # whole object and number incl. lines crossing them (solidify; Vraja Lila msg 5617-5620)
        "ink": True,     # lit picture baked in advance (write_ink; Vraja Lila msg 5637/5638)
        # Rim of the big tray under 1-3 (outer double line + inner grey ring): belongs to no numbered object.
        "exclude": [{"cx": 488.5, "cy": 993, "rx": 139.5, "ry": 77, "band": 6},
                    {"cx": 490, "cy": 994, "rx": 123, "ry": 59, "band": 3}],
        # The Deities: never a tap target (Vaishnava etiquette).
        "inert": [[(85, 10), (1185, 10), (1185, 722), (1100, 724), (1060, 750), (900, 762), (830, 760), (760, 747),
                   (712, 732), (712, 714), (560, 714), (560, 680), (415, 680), (415, 714), (85, 714)]],
        "items": {
            # cup with its spoon (the spoon's top end lies right of the bell's saucer)
            "1": {"clip": [(406, 982), (460, 980), (471, 960), (476, 950), (485, 950), (485, 1053), (406, 1053)]},
            # shell on its stand (both feet; the printed 2 sits right of the stand)
            "2": {"clip": [(488, 920), (597, 920), (597, 965), (584, 968), (584, 1027), (488, 1027)]},
            # bell on its saucer (stops before the spoon and the incense holder)
            "3": {"clip": [(420, 848), (455, 848), (455, 915), (464, 935), (470, 950), (471, 960), (460, 980), (406, 980),
                           (406, 930), (420, 915)]},
            "4": {"clip": [(456, 676), (522, 676), (522, 877), (456, 877)]},
            "5": {"clip": [(335, 800), (426, 800), (426, 850), (418, 872), (412, 888), (335, 888)]},
            "6": {"clip": [(581, 734), (706, 734), (706, 862), (581, 862)]},
            "7": {"clip": [(610, 904), (701, 904), (701, 961), (610, 961)]},
            "8": {"clip": [(703, 873), (883, 873), (883, 983), (703, 983)]},
            "9": {"clip": [(620, 1020), (708, 1020), (708, 1077), (620, 1077)]},
            "10": {"clip": [(712, 1009), (853, 1009), (853, 1100), (712, 1100)]},
            "11": {"clip": [(897, 867), (1231, 867), (1231, 1127), (897, 1127)]},
            "12": {"clip": [(15, 877), (341, 877), (341, 1140), (15, 1140)]},
            "13": {"clip": [(195, 746), (297, 746), (297, 863), (195, 863)]},
            # flower plate + garland (the Tulasī bowl 15 sits at its upper left)
            "14": {"clip": [(576, 1098), (830, 1098), (830, 1212), (543, 1212), (543, 1142), (556, 1134), (576, 1112)]},
            "15": {"clip": [(488, 1082), (574, 1082), (574, 1110), (552, 1134), (540, 1141), (488, 1141)]},
            "16": {"clip": [(436, 1142), (502, 1142), (502, 1190), (436, 1190)]},
            "17": {"clip": [(302, 751), (438, 751), (438, 796), (302, 796)]},
            "18": {"clip": [(72, 751), (193, 751), (193, 831), (72, 831)]},
        },
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


def solidify(ink, core, ring, region, k):
    """The whole object, not just its pieces (Vraja Lila msg 5617-5620, 20.10.2026: «не выделены целиком на
    пересечении серых линий, а также цифры»). Where the tray's rims cross an object, the "exclude" bands cut
    the object's own outline too, and the highlight showed gaps. Put the rim pixels of the object's region
    back, find what that outline encloses (its inside), and take every drawn pixel within k px of the inside:
    the object's own lines under the crossing and the stretch of rim that runs over the object. Rim that only
    touches the outline from outside stays out (it borders no inside of the object)."""
    if not core.any():
        return core
    outline = core | (ink & ring & region)
    inside = ndi.binary_fill_holes(outline) & ~outline
    inside = ndi.binary_opening(inside)          # no 1-px slivers between two touching lines
    # only the object's own insides: mostly bounded by its own lines (not a sliver between two rim lines)
    lab, n = ndi.label(inside)
    if n:
        rim = ndi.binary_dilation(inside, iterations=2) & ink & ~inside
        idx = np.arange(1, n + 1)
        near_lab = ndi.grey_dilation(lab, size=5)
        own_b = ndi.sum(rim & core, near_lab, idx)
        all_b = ndi.sum(rim, near_lab, idx)
        good = np.zeros(n + 1, bool)
        good[1:] = own_b >= 0.5 * np.maximum(all_b, 1)
        inside = good[lab]
    near = ndi.binary_dilation(inside, iterations=k)
    return core | (ink & region & near)


def solid_label(ink, core, region, dark):
    """A printed number in full (Vraja Lila msg 5617-5620, 5637 «ты обрезал цифру»): every drawn pixel of the
    number's box — the box of its black strokes, 2 px wider for the serifs — and the black pixels inside the
    convex hull of its strokes. The serifs are thin and grey (anti-aliased), and where a tray rim runs along
    a serif (the foot of «1») only the box keeps the serif whole; the bit of rim inside the box goes with it."""
    if core.sum() < 3:
        return core
    ys, xs = np.where(dark & region & ndi.binary_dilation(core, iterations=3))   # its black strokes, also under a rim
    if len(ys):
        box = np.zeros_like(core)
        box[max(ys.min() - 1, 0):ys.max() + 2, max(xs.min() - 2, 0):xs.max() + 3] = True
        strokes = dark & region & ndi.binary_dilation(core, iterations=3)
        core = core | (ink & region & box & ndi.binary_dilation(strokes, iterations=3))   # serif = next to a stroke
    from scipy.spatial import ConvexHull
    pts = np.argwhere(core)[:, ::-1].astype(float)
    hull = ConvexHull(pts)
    poly = [tuple(pts[v]) for v in hull.vertices]
    hullm = ndi.binary_dilation(poly_mask(ink.shape, poly) | core, iterations=1)
    return core | (ink & dark & region & hullm)


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

        solid_k = ic.get("solid", cfg.get("solid", 0))
        m = pick(region, clip)
        if solid_k:
            m = solidify(ink, m, ring, region, solid_k)
        if "lx" in s:
            # The printed number: only components lying mostly inside its
            # circle, unless the label touches a line ("label_clip").
            lx, ly = s["lx"] / 100 * W, s["ly"] / 100 * H
            lr = ic.get("label_r", cfg.get("label_r", 12))
            circle = (xx - lx) ** 2 + (yy - ly) ** 2 <= lr * lr
            lab_m = pick(circle, cfg.get("label_clip", False))
            if solid_k:
                lab_m = solid_label(ink, lab_m, (xx - lx) ** 2 + (yy - ly) ** 2 <= (lr + 6) ** 2, lum < DARK)
            m |= lab_m
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
    only = sys.argv[sys.argv.index("--only") + 1] if "--only" in sys.argv else None
    for name, spec in data.items():
        if only and name != only:
            continue
        cfg = CONFIG.get(name, {})
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
            spec["ink"] = write_ink(name, stem, masks)
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


INK_WHITE = 0.94   # luminance at/above this = paper (white) in the lit picture
INK_POWER = 4.5    # darkening curve of the lit picture (stronger than the SVG filter's gamma 3.2: grey inner lines dark too)


def write_ink(name, stem, masks):
    """The lit picture baked in advance (Vraja Lila msg 5637/5638, 20.10.2026: on the iPhone the inner lines of a
    lit object — the shell's spiral, the spoon — stayed grey; the SVG gamma filter on the zoomed picture is not
    reliable there). Every drawn line, grey ones too, pushed towards black; paper stays white; outside all
    masks plain white (smaller file). Written as <stem>/ink-<hash>.webp next to the masks; the app draws it
    through the mask without any filter."""
    import hashlib
    a = np.asarray(Image.open(IMAGES / name).convert("RGBA")).astype(float) / 255
    rgb = a[..., :3] * a[..., 3:4] + (1 - a[..., 3:4])
    t = np.clip(rgb / INK_WHITE, 0, 1) ** INK_POWER
    any_mask = np.logical_or.reduce([m > 0 for m in masks.values()])
    any_mask = ndi.binary_dilation(any_mask, iterations=2)
    t[~any_mask] = 1
    img = Image.fromarray((t * 255).round().astype(np.uint8), "RGB").convert("L")
    buf = __import__("io").BytesIO()
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
