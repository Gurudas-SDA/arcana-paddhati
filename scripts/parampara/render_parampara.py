# -*- coding: utf-8 -*-
"""Parampara portraits (Reader v7.4): one guru per page, oval frame «вариант A».

Satkirti 07.10.2026 13:07: «Парампару — овальную рамку, всех — включай в книгу.»
Rule 07.10.2026 12:34–12:36 (Стандарты книги, «Начало книги»): the body of a guru /
vaiṣṇava is NEVER cut — head, hands, knees, feet fully inside the frame with a
margin; only the background may be cropped; with an oval, the figure's contour
is fully inside.

How it is ensured (same method as the approved draft parampara_varianty.py):
  * every source has a hand-traced contour of the figure (HULL, source px:
    top of the head, ears, shoulders, elbows, hands, knees, feet, lowest cloth);
  * the smallest oval (aspect 0.735, like variant A) is searched such that every
    contour point lies inside it with a clearance >= 5 % of the oval width;
  * where that oval reaches beyond the painting, the background is extended
    (smooth push-pull fill from the painting's own edge colours, blurred) — the
    figure itself is never touched, never scaled unevenly, never masked;
  * Gurudev (no. 8): his 2025 portrait with exactly the crop of the approved
    variant A (fit_crop() of the draft script, imported from the draft folder).

Sources (not in git): ../Арчана-паддхати — книга/Черновики/2026-10-07 …/_исходники/парампара/
  1–7: «The Victory of Pure Love» (2020), p. 11 crops, 391×508 — the better of the two
       books (Haven of Love has the same paintings at 300×390); no. 7 of the book
       (Gour Govinda Svāmī) is not in our parampara (Satkirti 06.10).

Output (in git):
  public/images/parampara/01.png … 08.png   RGBA: photo in the oval + gold double line +
                                              small rhombi top/bottom; transparent outside
  scripts/parampara/check.json              crop, oval and the contour check of every page
                                              (re-verified by qa/lint_content.py L21)

    python scripts/parampara/render_parampara.py
"""
import importlib.util
import json
import math
import sys
from pathlib import Path

import numpy as np
import shapely
from PIL import Image, ImageDraw, ImageFilter
from shapely.geometry import Polygon

sys.stdout.reconfigure(encoding="utf-8")
REPO = Path(__file__).resolve().parents[2]
DRAFT = REPO.parent / "Арчана-паддхати — книга" / "Черновики" / "2026-10-07 Песни арати, парампара, прамана" / "_исходники"
SRC = DRAFT / "парампара"
OUT = REPO / "public" / "images" / "parampara"
CHECK = Path(__file__).resolve().parent / "check.json"

ASPECT = 0.735          # oval width / height (variant A)
MARGIN = 0.05           # min clearance of the contour: 5 % of the oval width
WIN_W = 600             # oval width in the output image, px (sources are ~430 px across the oval)
SS = 3                  # supersampling of the frame lines
GOLD_D = (139, 101, 8, 255)
GOLD = (212, 168, 67, 255)
WHITE = (255, 255, 255, 255)

# The painting inside the gold frame of the book crop (391×508): frame ~8 px, corner radius ~22 px.
INSET = 9
INSET_B = 10
CORNER_R = 22

# id, file, contour of the figure (source px). Traced on a 25 px grid, generously outside
# the figure (hair, ears, garland, cloth, fingers, toes). Objects (seat, mat, danda, book)
# are not the body and may be cut by the oval.
GURUS = [
    ("01", "1 Jagannatha dasa Babaji — VictoryOfPureLove_p11.jpeg",
     [(240, 38), (212, 52), (277, 52), (84, 112), (86, 142), (128, 182), (143, 240), (133, 300), (148, 400),
      (160, 472), (186, 478), (232, 472), (264, 464), (302, 400), (320, 290), (307, 200), (292, 128)]),
    ("02", "2 Bhaktivinoda Thakura — VictoryOfPureLove_p11.jpeg",
     [(185, 18), (143, 40), (227, 40), (58, 170), (312, 165), (38, 290), (334, 290), (20, 372), (23, 392),
      (48, 412), (53, 467), (130, 480), (250, 457), (350, 457), (330, 400)]),
    ("03", "3 Gaura-kisora dasa Babaji — VictoryOfPureLove_p11.jpeg",
     [(190, 86), (146, 108), (237, 108), (98, 195), (287, 195), (26, 334), (15, 366), (30, 405), (118, 417),
      (175, 467), (215, 467), (292, 417), (381, 362), (378, 392), (346, 316)]),   # knees: x 24 … 372 (v7.4.1)
    ("04", "4 Bhaktisiddhanta Sarasvati — VictoryOfPureLove_p11.jpeg",
     [(195, 23), (153, 48), (237, 48), (113, 160), (292, 155), (98, 300), (314, 300), (38, 395), (31, 410),
      (53, 447), (108, 480), (240, 482), (364, 472), (347, 420),
      # v7.5 (independent check 07.10): the seat mat is part of the figure («body rule includes the seat»):
      # its back-left corner, front-left corner, front edge and right end — all inside the oval with the margin
      (50, 408), (16, 496), (120, 497), (250, 497), (372, 496), (380, 478)]),
    ("05", "5 Bhakti Prajnana Kesava Gosvami — VictoryOfPureLove_p11.jpeg",
     [(183, 53), (140, 85), (224, 85), (73, 200), (284, 190), (48, 330), (297, 340), (33, 370), (31, 410),
      (73, 474), (150, 477), (250, 457), (374, 395), (368, 442)]),
    ("06", "6 Bhaktivedanta Svami — VictoryOfPureLove_p11.jpeg",
     [(190, 46), (143, 80), (240, 90), (108, 200), (302, 180), (93, 340), (INSET, 378), (INSET, 422), (58, 442),
      (150, 464), (250, 464), (322, 454), (391 - INSET, 422), (391 - INSET, 373), (357, 330)]),
    ("07", "8 Bhaktivedanta Narayana Gosvami — VictoryOfPureLove_p11.jpeg",
     [(225, 55), (188, 85), (264, 80), (148, 170), (327, 160), (78, 330), (40, 395), (43, 432), (78, 467),
      (200, 474), (300, 452), (344, 468), (352, 420), (364, 320)]),
]
GURUDEV = ("08", "Sri Prem Prayojan Prabhu portrait 2025, long gareland B.jpg")

# Satkirti 07.10 13:35 / 13:41: Śrī Pañca-tattva page first; portraits from the internet where an
# acceptable one exists (body rule!), else the book crops above. Details and URLs:
# «Источники изображений v7.4.md» in the draft folder.
LIB_GD = REPO.parent / "Библиотека" / "Книги Гурудева" / "Gaudiya Darsana (фото, 06.10)" / "05.jpg"
EXTRA = {
    # id: (source path, usable rectangle (l, t, r, b, corner r) or None = whole picture, contour, preprocessing)
    # v7.4.1 (independent check 07.10): the v7.4 contours of 00 and 03 were traced too tight — the raised
    # fingertips (00) and the knees / lap cloth at the photo's sides (03) touched the oval. Re-traced
    # generously; the background outside the usable picture now fades softly into a light neutral tone
    # (STYLE below) instead of being stretched.
    "00": (LIB_GD, (360, 284, 700, 712, 0),   # Satkirti's phone photo of «Gauḍīya-darśana» p. 05 (fallback:
           # no suitable Pañca-tattva painting found online); the rectangle leaves out most of the printed
           # carved frame (its remaining scrolls lie outside the figures and fade out)
           [(445, 306), (490, 308), (530, 298), (556, 298), (585, 300), (645, 286), (664, 296),   # fingertips
            (398, 394), (368, 420), (366, 500), (366, 600), (370, 660),                          # Advaita, left
            (382, 714), (440, 716), (520, 694), (600, 704), (690, 710),                          # lotus bases
            (697, 640), (697, 520), (696, 420), (688, 378)], "photo"),                       # Śrīvāsa, right
    # 03: the v7.4 Wikimedia photo (Gaurakisora dasa Babaji ca.1900, PD) is itself truncated — the lap
    # cloth / knees run out of the picture at both sides — so v7.4.1 goes back to the book painting
    # (GURUS «03» above: the whole seated figure incl. both knees and hands is inside the painting).
    # 06: the book painting (both books) cuts Śrīla Prabhupāda's right knee at the painting's edge; v7.4.1 uses
    # the only free full-figure photo found: Wikimedia Commons «AC Bhaktivedanta Swami Prabhupada.jpg»
    # (Paris, 22.07.1972, Vanimedia, CC BY-SA 4.0 — attribution required), standing, 475 × 699.
    "06": (SRC / "internet — AC Bhaktivedanta Swami Prabhupada 1972 Paris (Wikimedia Commons, CC BY-SA 4.0).jpg", None,
           [(237, 52), (198, 88), (280, 88), (190, 160), (310, 150), (130, 200), (128, 300), (130, 460),
            (138, 560), (140, 620), (160, 680), (265, 660), (310, 684), (330, 640), (352, 612),
            (378, 560), (400, 470), (400, 380), (392, 250), (345, 160)], None),                          # walking stick = object
}

# Background outside the usable picture (v7.4.1): fade into a light neutral tone over FADE_OUT × oval width;
# the photo 00 also fades its own border inwards (FADE_IN) — only outside the figure's contour (+ PROTECT).
# Book paintings and the 06 photo keep their colours but end in a soft, heavily blurred tone of their own edge.
STYLE = {"00": {"tone": "neutral", "fade_out": 0.05, "fade_in": 0.05, "vignette": 0.10},
         "06": {"tone": "soft", "fade_out": 0.06, "fade_in": 0.0},
         # v7.5: below the painting's bottom edge (04: under the mat; 07: under the cloth) the replicated
         # edge rows showed as streaks — a short ramp into the calm blurred tone instead
         "04": {"tone": "soft", "fade_out": 0.02, "fade_in": 0.06},
         "07": {"tone": "soft", "fade_out": 0.02, "fade_in": 0.06}}
STYLE_PAINTING = {"tone": "soft", "fade_out": 0.05, "fade_in": 0.0}
PROTECT = 0.025     # contour buffer (× oval width) never touched by the inward fade


def oval(w, h, n=720):
    t = np.linspace(0, 2 * math.pi, n, endpoint=False)
    return Polygon(np.c_[w / 2 + w / 2 * np.cos(t), h / 2 + h / 2 * np.sin(t)])


def clearance(hull, x0, y0, cw):
    """(all inside, min distance of a contour point to the oval edge / oval width) — exact (shapely)."""
    poly = oval(cw, cw / ASPECT)
    px, py = hull[:, 0] - x0, hull[:, 1] - y0
    inside = shapely.contains_xy(poly, px, py)
    dist = shapely.distance(poly.exterior, shapely.points(px, py))
    return bool(inside.all()), float(dist.min() / cw)


_T = np.linspace(0, 2 * math.pi, 1440, endpoint=False)


def _fast(hull, cx, cy, cw):
    """Same test, vectorised (search only; the result is re-checked exactly)."""
    a, b = cw / 2, cw / ASPECT / 2
    q = ((hull[:, 0] - cx) / a) ** 2 + ((hull[:, 1] - cy) / b) ** 2
    if (q >= 1).any():
        return False, 0.0
    ex, ey = cx + a * np.cos(_T), cy + b * np.sin(_T)
    d = np.hypot(hull[:, 0, None] - ex[None], hull[:, 1, None] - ey[None]).min()
    return True, float(d / cw)


def fit(hull):
    """Smallest oval (then the most centred) that holds the whole contour with MARGIN."""
    bx0, by0 = hull.min(0)
    bx1, by1 = hull.max(0)
    mx, my = (bx0 + bx1) / 2, (by0 + by1) / 2
    st = max(2.0, (bx1 - bx0) / 180)
    for cw in np.arange(max(bx1 - bx0, (by1 - by0) * ASPECT), 3 * (bx1 - bx0), st):
        ch = cw / ASPECT
        best = None
        for cx in np.arange(mx - 15 * st, mx + 15.5 * st, st):
            for cy in np.arange(my - 30 * st, my + 30.5 * st, st):
                ok, cl = _fast(hull, cx, cy, cw)
                if ok and cl >= MARGIN + 0.002 and (best is None or cl > best[0]):
                    best = (cl, cx, cy)
        if best:
            ok, cl = clearance(hull, best[1] - cw / 2, best[2] - ch / 2, cw)
            if ok and cl >= MARGIN:
                return float(best[1]), float(best[2]), float(cw), float(ch)
    raise SystemExit("contour does not fit")




def book_frame(w, h):
    """The painting inside the gold frame of a book crop: (left, top, right, bottom, corner radius)."""
    return INSET, INSET, w - 1 - INSET, h - 1 - INSET_B, CORNER_R


def nearest_valid(xx, yy, w, h, valid):
    """Nearest point of the usable picture (rectangle, optionally rounded corners) for every pixel."""
    lx, ty, rx, by, r = valid
    px = np.clip(xx, lx, rx).astype(float)
    py = np.clip(yy, ty, by).astype(float)
    corners = ((lx + r, ty + r), (rx - r, ty + r), (lx + r, by - r), (rx - r, by - r)) if r else ()
    for cx, cy in corners:
        sel = ((px < cx) if cx < w / 2 else (px > cx)) & ((py < cy) if cy < h / 2 else (py > cy))
        dx, dy = px[sel] - cx, py[sel] - cy
        n = np.maximum(np.hypot(dx, dy), 1e-9)
        k = np.minimum(1.0, (r - 1) / n)
        px[sel], py[sel] = cx + dx * k, cy + dy * k
    return px, py


def _smooth(t):
    t = np.clip(t, 0, 1)
    return t * t * (3 - 2 * t)


def soft_background(out, a, xx, yy, px, py, dist, mask, valid, crop, hull, style):
    """v7.4.1: instead of a long stretched (streaky) extension, the extension ends in a calm tone:
    'neutral' — a light grey matching the photo's light background (photos 00, 03);
    'soft'    — the painting's own edge colours, very heavily blurred (book paintings).
    Photos also fade their own border inwards (fade_in), but never within the figure's contour + PROTECT."""
    from scipy.ndimage import distance_transform_edt
    cw = crop[2]
    lx, ty, rx, by, _ = valid
    if style["tone"] == "neutral":
        band = a[ty:by + 1, lx:rx + 1]
        edge = np.concatenate([band[:8].reshape(-1, 3), band[-8:].reshape(-1, 3),
                               band[:, :8].reshape(-1, 3), band[:, -8:].reshape(-1, 3)])
        lum = edge.mean(1)
        light = edge[lum >= np.percentile(lum, 70)]          # the light background, not the dark floor/curtain
        tone = np.full(3, float(np.median(light.mean(1))))   # neutral grey of that brightness
        tone_img = np.broadcast_to(tone, out.shape)
    else:
        sig = 0.12 * cw
        tone_img = np.asarray(Image.fromarray(np.clip(out, 0, 255).astype(np.uint8))
                              .filter(ImageFilter.GaussianBlur(sig)), float)
    t = _smooth(dist / (style["fade_out"] * cw))[..., None]
    res = out * (1 - t) + tone_img * t
    if style.get("fade_in"):
        din = np.minimum.reduce([xx - lx, rx - xx, yy - ty, by - yy]).astype(float)
        w = _smooth(din / (style["fade_in"] * cw))
        # the figure: convex hull of the contour, buffered; soft ramp just outside it
        hp = shapely.MultiPoint([tuple(p) for p in hull]).convex_hull.buffer(PROTECT * cw)
        prot = Image.new("L", (xx.shape[1], xx.shape[0]), 0)
        x0, y0 = xx[0, 0], yy[0, 0]
        ImageDraw.Draw(prot).polygon([(x - x0, y - y0) for x, y in hp.exterior.coords], fill=255)
        inside = np.asarray(prot) > 0
        dout = distance_transform_edt(~inside)
        keep = np.clip(1 - dout / (0.02 * cw), 0, 1)
        if style.get("vignette"):     # background farther from the figure fades out too (soft vignette)
            w = np.minimum(w, _smooth(1 - dout / (style["vignette"] * cw)))
        w = np.maximum(w, keep)
        # outside the picture the extension continues with the weight of its nearest picture point
        iy = np.clip(np.rint(py).astype(int) - y0, 0, w.shape[0] - 1)
        ix = np.clip(np.rint(px).astype(int) - x0, 0, w.shape[1] - 1)
        w_out = w[iy, ix] * (1 - t[..., 0])
        w = np.where(mask, w, w_out)[..., None]
        res = out * w + tone_img * (1 - w)
    return res


def extended_crop(src, crop, valid, hull=None, style=None):
    """Crop (cx, cy, cw, ch) of the painting; where it reaches beyond the painting the
    background is extended from the painting's own edge colours, blurred more with the
    distance from the painting (the painting — and the figure in it — stays untouched)."""
    cx, cy, cw, ch = crop
    a = np.asarray(src, float)
    h, w = a.shape[:2]
    x0, y0 = int(math.floor(cx - cw / 2)) - 4, int(math.floor(cy - ch / 2)) - 4
    x1, y1 = int(math.ceil(cx + cw / 2)) + 4, int(math.ceil(cy + ch / 2)) + 4
    yy, xx = np.mgrid[y0:y1, x0:x1]
    px, py = nearest_valid(xx, yy, w, h, valid)
    dist = np.hypot(xx - px, yy - py)
    mask = dist < 0.5
    rep = a[np.rint(py).astype(int), np.rint(px).astype(int)]
    canvas = rep.copy()
    base = Image.fromarray(np.clip(rep, 0, 255).astype(np.uint8))
    levels = [(0, None), (6, 3), (20, 9), (45, 22), (90, 45)]   # (distance px, blur sigma)
    blurred = [rep] + [np.asarray(base.filter(ImageFilter.GaussianBlur(s)), float) for _, s in levels[1:]]
    out = blurred[-1].copy()
    for i in range(len(levels) - 1, 0, -1):
        d0, d1 = levels[i - 1][0], levels[i][0]
        t = np.clip((dist - d0) / (d1 - d0), 0, 1)[..., None]
        seg = blurred[i - 1] * (1 - t) + blurred[i] * t
        sel = dist < d1
        out[sel] = seg[sel]
    out[mask] = canvas[mask]
    if style:
        out = soft_background(out, a, xx, yy, px, py, dist, mask, valid, crop, hull, style)
    im = Image.fromarray(np.clip(out, 0, 255).astype(np.uint8))
    # exact crop box inside the padded canvas
    bx = (cx - cw / 2) - x0
    by = (cy - ch / 2) - y0
    return im, (bx, by, bx + cw, by + ch), float((~mask).mean())


def outline(d, poly, g, width, color):
    p = poly.buffer(g, join_style="mitre", mitre_limit=10) if g else poly
    pts = list(p.exterior.coords)
    d.line(pts + [pts[1]], fill=color, width=width, joint="curve")


def rhombus(d, x, y, r, fill=None, outline_c=None, width=1):
    pts = [(x, y - r), (x + r, y), (x, y + r), (x - r, y)]
    d.polygon(pts, fill=fill)
    if outline_c:
        d.line(pts + [pts[0]], fill=outline_c, width=width, joint="curve")


def render_page(photo, box):
    """Photo (PIL RGB) → RGBA: oval window WIN_W wide, variant-A double gold line, rhombi."""
    k = WIN_W / 1190.0                    # variant A was drawn for a 1190 px oval
    ww, wh = WIN_W * SS, round(WIN_W / ASPECT) * SS
    g1, g2 = 14 * k * SS, 24 * k * SS
    r_out = 11 * k * SS
    pad = int(math.ceil(g2 + r_out + 3 * SS))
    W, H = ww + 2 * pad, wh + 2 * pad
    ph = photo.resize((ww, wh), Image.LANCZOS, box=box)
    page = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    poly = oval(ww, wh)
    mask = Image.new("L", (ww, wh), 0)
    ImageDraw.Draw(mask).polygon(list(poly.exterior.coords), fill=255)
    page.paste(ph.convert("RGBA"), (pad, pad), mask)
    d = ImageDraw.Draw(page)
    from shapely import affinity
    shifted = affinity.translate(poly, pad, pad)
    outline(d, shifted, g1, max(SS, round(4.5 * k * SS)), GOLD_D)
    outline(d, shifted, g2, max(SS, round(2.2 * k * SS)), GOLD)
    for y in (pad - g2, pad + wh + g2):
        rhombus(d, W / 2, y, r_out, fill=WHITE, outline_c=GOLD_D, width=max(SS, round(2 * k * SS)))
        rhombus(d, W / 2, y, 4 * k * SS, fill=GOLD_D)
    out = page.resize((W // SS, H // SS), Image.LANCZOS)
    return out, pad / SS


def gurudev_crop():
    spec = importlib.util.spec_from_file_location("parampara_varianty", DRAFT / "parampara_varianty.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    src = m.load_source()
    crop = m.fit_crop(m.shape_oval, ASPECT, src.size, False)   # = variant A (approved 07.10)
    rep = m.verify(m.shape_oval, crop)
    return src, crop, rep, [list(p) for p in m.HULL]


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    report = {"aspect": ASPECT, "margin": MARGIN, "pages": []}
    jobs = [(gid, SRC / fname, None, hull, None) for gid, fname, hull in GURUS if gid not in EXTRA]
    jobs += [(gid, path, valid, hull, prep) for gid, (path, valid, hull, prep) in EXTRA.items()]
    for gid, path, valid, hull, prep in sorted(jobs):
        fname = path.name if path.parent == SRC else str(path.relative_to(REPO.parent))
        src = Image.open(path).convert("RGB")
        if prep == "photo":   # phone photo of a printed page: even out glare and contrast
            from PIL import ImageOps
            src = ImageOps.autocontrast(src, cutoff=1)
        valid = valid or ((0, 0, src.size[0] - 1, src.size[1] - 1, 0) if path.parent != SRC or gid in EXTRA else None)
        valid = valid or book_frame(*src.size)
        H = np.array(hull, float)
        crop = fit(H)
        im, box, ext = extended_crop(src, crop, valid, hull, STYLE.get(gid, STYLE_PAINTING))
        ok, cl = clearance(H, crop[0] - crop[2] / 2, crop[1] - crop[3] / 2, crop[2])
        page, pad = render_page(im, box)
        page.save(OUT / f"{gid}.png", optimize=True)
        report["pages"].append({"id": gid, "source": fname, "source_size": list(src.size),
                                "crop": [round(v, 2) for v in crop], "hull": [list(p) for p in hull],
                                "all_inside": ok, "min_clearance": round(cl, 4),
                                "extended_background_share": round(ext, 3),
                                "image": f"parampara/{gid}.png", "image_size": list(page.size), "oval_pad": round(pad, 2)})
        print(f"{gid} crop {tuple(round(v) for v in crop)} inside={ok} clearance={cl:.3f} ext={ext:.2f} -> {page.size}")
    src, crop, rep, hull = gurudev_crop()
    cx, cy, cw, ch = crop
    page, pad = render_page(src, (cx - cw / 2, cy - ch / 2, cx + cw / 2, cy + ch / 2))
    page.save(OUT / f"{GURUDEV[0]}.png", optimize=True)
    ok, cl = clearance(np.array(hull, float), cx - cw / 2, cy - ch / 2, cw)
    report["pages"].append({"id": GURUDEV[0], "source": GURUDEV[1] + " (+ mirrored 700 px of the cloth below, as in variant A)",
                            "source_size": [src.size[0], src.size[1]], "crop": [round(float(v), 2) for v in crop],
                            "hull": hull, "all_inside": ok, "min_clearance": round(cl, 4),
                            "variant_a_verify": {k: (v if isinstance(v, (bool, int, float)) else str(v)) for k, v in rep.items()},
                            "image": f"parampara/{GURUDEV[0]}.png", "image_size": list(page.size), "oval_pad": round(pad, 2)})
    print(f"{GURUDEV[0]} crop {tuple(round(v) for v in crop)} inside={ok} clearance={cl:.3f} -> {page.size}")
    CHECK.write_text(json.dumps(report, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
