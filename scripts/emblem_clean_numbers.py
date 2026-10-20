"""Remove burned-in numbers 1-9 from the Gaudiya emblem (only those pixels)."""
import sys
import numpy as np
from PIL import Image

src, dst = sys.argv[1], sys.argv[2]
a = np.array(Image.open(src).convert("RGB")).astype(float)
H, W, _ = a.shape
out = a.copy()
MAROON = np.array([110, 26, 46], float)

# "1": white glyph cut into the maroon field (rows 493-509, x 406-413) -> field colour
out[493:510, 406:414] = MAROON

sat = a.max(-1) - a.min(-1)
core = (sat < 25) & (a.max(-1) < 200)          # dark grey ink = the numbers only (checked: none elsewhere)
boxes = {"2": (623, 639, 491, 512), "3": (291, 307, 97, 118), "4": (641, 659, 337, 357),
         "5": (156, 172, 752, 773), "6": (824, 841, 751, 773), "7": (392, 408, 782, 802),
         "8": (581, 598, 806, 828), "9": (518, 535, 759, 781)}


def sample(img, x, y):
    x0, y0 = int(np.floor(x)), int(np.floor(y))
    fx, fy = x - x0, y - y0
    return (img[y0, x0] * (1 - fx) * (1 - fy) + img[y0, x0 + 1] * fx * (1 - fy)
            + img[y0 + 1, x0] * (1 - fx) * fy + img[y0 + 1, x0 + 1] * fx * fy)


masks = {}
for k, (x0, x1, y0, y1) in boxes.items():
    P = 3
    ys, xs = slice(y0 - P, y1 + P + 1), slice(x0 - P, x1 + P + 1)
    c = core[ys, xs]
    # dilate core by 2 px
    d = c.copy()
    for _ in range(2):
        e = d.copy()
        e[1:] |= d[:-1]; e[:-1] |= d[1:]; e[:, 1:] |= d[:, :-1]; e[:, :-1] |= d[:, 1:]
        d = e
    sub = a[ys, xs]
    pure_white = sub.min(-1) >= 250
    m = d & ~pure_white
    full = np.zeros((H, W), bool)
    full[ys, xs] = m
    masks[k] = full

for k, m in masks.items():
    x0, x1, y0, y1 = boxes[k]
    ring = np.zeros((H, W), bool)
    ring[y0 - 14:y1 + 15, x0 - 14:x1 + 15] = True
    ring &= ~m
    # choose the stroke direction that best explains the neighbourhood (straight frame lines)
    best = None
    for ang in np.arange(0, 180, 1.0):
        t = np.deg2rad(ang)
        dx, dy = np.cos(t), np.sin(t)
        err = 0.0
        n = 0
        ry, rx = np.nonzero(ring)
        for yy, xx in zip(ry[::3], rx[::3]):
            x2, y2 = xx + 3 * dx, yy + 3 * dy
            if 0 <= x2 < W - 1 and 0 <= y2 < H - 1 and not m[int(round(y2)), int(round(x2))]:
                err += np.abs(a[yy, xx] - sample(a, x2, y2)).sum()
                n += 1
        err /= max(n, 1)
        if best is None or err < best[0]:
            best = (err, dx, dy, ang)
    _, dx, dy, ang = best
    ys, xs = np.nonzero(m)
    for yy, xx in zip(ys, xs):
        vals, wts = [], []
        for s in (1, -1):
            for step in range(1, 40):
                x2, y2 = xx + s * step * dx, yy + s * step * dy
                if not (0 <= x2 < W - 1 and 0 <= y2 < H - 1):
                    break
                ix, iy = int(np.floor(x2)), int(np.floor(y2))
                if not (m[iy, ix] or m[iy, ix + 1] or m[iy + 1, ix] or m[iy + 1, ix + 1]):
                    vals.append(sample(a, x2, y2)); wts.append(1.0 / step)
                    break
        out[yy, xx] = np.average(vals, axis=0, weights=wts) if vals else 255
    print(k, "angle", ang, "px", int(m.sum()))

Image.fromarray(np.clip(np.round(out), 0, 255).astype(np.uint8)).save(dst, optimize=True)
diff = np.abs(out - a).sum(-1) > 0
print("changed px", int(diff.sum()))
