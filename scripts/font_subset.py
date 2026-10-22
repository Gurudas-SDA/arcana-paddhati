"""Our own cut of Noto Serif — upright AND italic (Vraja Lila msg 5316 p. 4, 20.10.2026; V49 msg 6363/6364, 23.10.2026).

Source: the full variable Noto Serif of Google Fonts (github.com/google/fonts, ofl/notoserif — the same files and
versions the Google Fonts API serves: upright 2.015, italic 2.013), downloaded once to scripts/.font-src/ (not in
git). Width fixed at 100 (as the API gives it); weights: upright 100–900 (as before), italic 400–700 (the weights the
book's italic uses: 400 Sanskrit / translations / sources, 500–700 bold Sanskrit words and headings; nothing in the
CSS is lighter than 400 or heavier than 700). No hinting (as the API files).

Keeps only the characters used by the book and the interface: data/*.json, public/transcripts, components/, lib/,
app/ + printable ASCII, Latin-1, the common punctuation, №, €, ™ — split by script as Google splits it:
  latin     Google «latin» range                 + the combining marks used
  latinext  Google «latin-ext» range             + the combining marks used
  cyrillic  Google «cyrillic» range + U+0400–052F + the combining marks used (V49: ӣ ӯ һ and the dot above U+0307
            of the Russian Sanskrit transliteration were outside the cut and pulled a full Google file)
The italic file of each script has exactly the characters of the upright one.
Writes app/fonts/arcana-serif-<script>[-italic].woff2 and prints each script's unicode-range for app/layout.tsx.
A new character in a text (e.g. a new language) -> run again: python scripts/font_subset.py
Needs fontTools (pip install fonttools brotli).
"""
import glob
import os
import subprocess
import sys
import urllib.request

from fontTools.ttLib import TTFont
from fontTools.varLib import instancer

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
SRC_DIR = os.path.join(ROOT, "scripts", ".font-src")
GH = "https://github.com/google/fonts/raw/main/ofl/notoserif/"
SOURCES = {  # style -> (file, sha256, wght range)
    "normal": ("NotoSerif[wdth,wght].ttf", "4d8e6761424656867019081a1a01336f3cb086982682698714054fc33f782713", (100, 900)),
    "italic": ("NotoSerif-Italic[wdth,wght].ttf", "e87acbc6c0efd0d9a20d6a8cbbda2b266c14be3a3a6f5af8ec9d7b2460570ad1", (400, 700)),
}


def rng(*parts):
    s = set()
    for p in parts:
        a, _, b = p.partition("-")
        s |= set(range(int(a, 16), int(b or a, 16) + 1))
    return s


# Google Fonts API unicode-range of each subset (css2?family=Noto+Serif, 23.10.2026)
GOOGLE = {
    "latin": rng("0000-00FF", "0131", "0152-0153", "02BB-02BC", "02C6", "02DA", "02DC", "0304", "0308", "0329",
                 "2000-206F", "20AC", "2122", "2191", "2193", "2212", "2215", "FEFF", "FFFD"),
    "latinext": rng("0100-02BA", "02BD-02C5", "02C7-02CC", "02CE-02D7", "02DD-02FF", "0304", "0308", "0329",
                    "1D00-1DBF", "1E00-1E9F", "1EF2-1EFF", "2020", "20A0-20AB", "20AD-20C4", "2113", "2C60-2C7F",
                    "A720-A7FF", "0020", "00A0"),
    "cyrillic": rng("0301", "0400-052F", "2116", "0020", "00A0"),
}
MARKS = rng("0300-036F")
# the OpenType features of the Google API files we cut before (V49: «*» would also keep every alternate glyph — +50 %)
FEATURES = "ccmp,locl,liga,frac,numr,dnom,pnum,tnum,kern,mark,mkmk"


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
    # general punctuation: the marks the cut has had since 20.10 (V49: not the whole U+2010–205E block — +5 KB unused)
    punct = {0x2002, 0x2009, 0x200B, 0x2013, 0x2014, 0x2018, 0x2019, 0x201A, 0x201C, 0x201D, 0x201E, 0x2022, 0x2026,
             0x2020, 0x2032, 0x2033, 0x2039, 0x203A, 0x2044}
    base = set(range(0x20, 0x7F)) | set(range(0xA0, 0x100)) | punct
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


def source(style):
    import hashlib
    name, sha, _ = SOURCES[style]
    path = os.path.join(SRC_DIR, name)
    if not os.path.exists(path):
        os.makedirs(SRC_DIR, exist_ok=True)
        url = GH + name.replace("[", "%5B").replace("]", "%5D")
        print(f"download {url}")
        urllib.request.urlretrieve(url, path)
    got = hashlib.sha256(open(path, "rb").read()).hexdigest()
    if got != sha:
        sys.exit(f"{path}: sha256 {got} != {sha} (another Noto Serif version — check before cutting)")
    return path


def main():
    cps = used_chars()
    marks = cps & MARKS
    for style, (name, _, (lo, hi)) in SOURCES.items():
        font = instancer.instantiateVariableFont(TTFont(source(style)), {"wdth": 100, "wght": (lo, hi)})
        tmp = os.path.join(SRC_DIR, f"_{style}.ttf")
        font.save(tmp)
        cmap = set(font.getBestCmap())
        for k, block in GOOGLE.items():
            sel = sorted((cps & (block | marks)) & cmap)
            suffix = "" if style == "normal" else "-italic"
            dst = os.path.join(ROOT, "app", "fonts", f"arcana-serif-{k}{suffix}.woff2")
            subprocess.run(["pyftsubset", tmp, "--unicodes=" + ",".join(f"U+{c:X}" for c in sel),
                            "--layout-features=" + FEATURES, "--no-hinting", "--flavor=woff2", "--output-file=" + dst], check=True)
            print(f"{style} {k} wght {lo}-{hi}: {len(sel)} chars, {os.path.getsize(dst)} B\n  unicode-range: {ranges(sel)}")
        os.remove(tmp)
    missing = sorted(c for c in cps if not any(c in TTFont(f).getBestCmap()
                                               for f in glob.glob(os.path.join(ROOT, "app", "fonts", "*.woff2"))))
    print("used, not in Noto Serif (drawn by the system font):", " ".join(f"U+{c:04X}" for c in missing) or "none")


if __name__ == "__main__":
    main()
