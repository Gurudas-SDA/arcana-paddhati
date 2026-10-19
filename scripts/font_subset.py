"""Our own cut of Noto Serif (upright, variable 100–900) — Vraja Lila msg 5316 p. 4, 20.10.2026.

Takes the three Google subsets next/font downloads at build (latin, latin-ext, cyrillic; out/_next/static/media,
recognised by their character maps) and keeps only the characters used by the book and the interface:
data/*.json, public/transcripts, components/, lib/, app/ + printable ASCII, Latin-1, general punctuation, №, €, ™.
Writes app/fonts/arcana-serif-<latin|latinext|cyrillic>.woff2 and prints each file's unicode-range for
app/layout.tsx (localFont declarations). Anything outside the cut is still drawn by the full Noto Serif.
A new character in a text (e.g. a new language) -> run again: python scripts/font_subset.py
Needs fontTools (pip install fonttools brotli).
"""
import glob
import os
import subprocess
import sys

from fontTools.ttLib import TTFont

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
MEDIA = os.path.join(ROOT, "out", "_next", "static", "media")
# a code point each Google subset has and the others have not
MARKERS = {"latin": 0x41, "latinext": 0x101, "cyrillic": 0x416}


def used_chars():
    used = set()
    pats = ["data/*.json", "public/transcripts/**/*", "components/*.tsx", "lib/*.ts", "lib/*.json", "app/**/*.tsx"]
    for pat in pats:
        for f in glob.glob(os.path.join(ROOT, pat), recursive=True):
            if os.path.isfile(f):
                try:
                    used |= {ord(c) for c in open(f, encoding="utf-8").read()}
                except UnicodeDecodeError:
                    pass
    base = set(range(0x20, 0x7F)) | set(range(0xA0, 0x100)) | set(range(0x2010, 0x2028)) | set(range(0x2030, 0x205F))
    return base | {0x2116, 0x20AC, 0x2122} | {c for c in used if c >= 0x20}


def ranges(cps):
    out, s, p = [], None, None
    for c in cps:
        if s is None:
            s = p = c
        elif c == p + 1:
            p = c
        else:
            out.append((s, p))
            s = p = c
    out.append((s, p))
    return ",".join(f"U+{a:X}" if a == b else f"U+{a:X}-{b:X}" for a, b in out)


def main():
    cps = used_chars()
    found = {}
    for f in glob.glob(os.path.join(MEDIA, "*.woff2")):
        cmap = set(TTFont(f).getBestCmap())
        for k, m in MARKERS.items():
            if m in cmap and (k != "latin" or 0x101 not in cmap) and (k != "latinext" or 0x41 not in cmap):
                found.setdefault(k, (f, cmap))
    for k in MARKERS:
        if k not in found:
            sys.exit(f"Google subset {k} not found in {MEDIA} (run npm run build first)")
        src, cmap = found[k]
        sel = sorted(cmap & cps)
        dst = os.path.join(ROOT, "app", "fonts", f"arcana-serif-{k}.woff2")
        subprocess.run(["pyftsubset", src, "--unicodes=" + ",".join(f"U+{c:X}" for c in sel), "--layout-features=*",
                        "--flavor=woff2", "--output-file=" + dst], check=True)
        print(f"{k}: {len(sel)} chars, {os.path.getsize(dst)} B (from {os.path.getsize(src)} B)\n  unicode-range: {ranges(sel)}")


if __name__ == "__main__":
    main()
