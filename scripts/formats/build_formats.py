#!/usr/bin/env python3
"""Build the PRINT (A5 PDF) and E-BOOK (EPUB 3) editions of the book.

The app (Next.js, `npm run build`) is the first format; this script produces
the other two from the same data files (data/book[.<lang>].json, ui.<lang>.json,
public/cover.jpg, public/images/*).

    python scripts/formats/build_formats.py                  # ru + en, all formats
    python scripts/formats/build_formats.py --lang ru,en,lv  # any language with data
    python scripts/formats/build_formats.py --formats print  # only the PDF

Output (default): ../Арчана-паддхати — книга/ next to the repo, with
  1 Приложение/  link to the app + readme
  2 Для печати/  <name> — print.pdf
  3 EPUB/        <name>.epub  (EPUB 3: cover, contents page, nav; Kindle takes
                 EPUB via Send to Kindle - no AZW3 is produced any more)

Numbering: chapters are numbered 1, 2, 3, ... and their subsections 2.1, 2.2, ...,
computed here from the section order (same rule as the app, lib/book.ts
sectionNumbers): every section is numbered, front matter included
(Introduction 1, Mangalacarana 2, then Part I from 3); only the appendix and
the verse index (generated here, not book sections) stay unnumbered.
Parts (book.json "parts": Part I Temple worship, II Home worship, III ...) are
a level above the chapters, numbered I, II, III: a part page before the part's
first chapter (an empty part = page with "in preparation"), and a level in the
contents, PDF outline and EPUB nav.

PRINT: HTML + CSS paged media rendered by headless Chrome (--headless=new, no
window), twice: pass 1 finds the page of every section and verse through the
PDF's named destinations (TOC, verse index and appendix entries link to them), pass 2
writes the page numbers into the TOC, the index and the appendix.

Mood blocks ("Gurudev's mood"): the chosen quote is printed in the block; the
other candidate quotes (`more`, shown after it in the app's mood overlay) go to an appendix
chapter "Gurudev's words — all quotes", grouped by block with a page reference
(PDF) or link (EPUB) to the block. Running headers, page numbers and PDF
bookmarks are then added with PyMuPDF.

Requires: Chrome or Edge, Python packages PyMuPDF (fitz) and fontTools,
Noto Serif TTF (Windows ships it).
"""
from __future__ import annotations

import argparse
import datetime as dt
import html
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unicodedata
import uuid
import zipfile
from pathlib import Path

import fitz  # PyMuPDF

REPO = Path(__file__).resolve().parents[2]
DATA = REPO / "data"
PUBLIC = REPO / "public"
DEFAULT_OUT = REPO.parent / "Арчана-паддхати — книга"
APP_URL = "https://gurudas-sda.github.io/arcana-paddhati/"

FONT_FILES = {
    "regular": "NotoSerif-Regular.ttf",
    "bold": "NotoSerif-Bold.ttf",
    "italic": "NotoSerif-Italic.ttf",
    "bolditalic": "NotoSerif-BoldItalic.ttf",
}
FONT_DIRS = [
    Path(os.environ.get("NOTO_FONT_DIR", "")),
    Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts",
    Path.home() / "AppData/Local/Microsoft/Windows/Fonts",
    Path("/usr/share/fonts/truetype/noto"),
    Path("/usr/share/fonts/noto"),
    Path.home() / "Library/Fonts",
]
CHROME_CANDIDATES = [
    os.environ.get("CHROME_PATH", ""),
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    "/usr/bin/google-chrome", "/usr/bin/chromium",
]

# Per-language strings of the editions. A language without an entry uses the
# English strings (labels found in data/ui.<lang>.json still win) and the file
# name "Arcana Paddhati (<CODE>)".
LANG_STRINGS = {
    "en": {
        "name": "Arcana Paddhati (EN)",
        "print_suffix": " — print",
        "short_title": "Arcana Paddhati",
        "toc": "Contents",
        "index": "Index of verses",
        "index_note": "First lines of the verses in alphabetical order (IAST), with the page, word-by-word meanings and translation.",
        "index_note_epub": "First lines of the verses in alphabetical order (IAST), with links to their places, word-by-word meanings and translation.",
        "version": "Version of",
        "app": "The book as an app (with search):",
        "cover": "Cover",
        "pages": "p.",
        "appendix": "Gurudev's words — all quotes",
        "appendix_note": "For each “Gurudev's mood” block: the other quotes of Gurudev on the same theme (the block itself has the chosen one). Verbatim from the lecture transcripts, with translation and source.",
        "appendix_block": "block on",
    },
    "ru": {
        "name": "Арчана-паддхати (рус.)",
        "print_suffix": " — для печати",
        "short_title": "Арчана-паддхати",
        "toc": "Содержание",
        "index": "Указатель шлок",
        "index_note": "Первые строки шлок в алфавитном порядке, с номером страницы, пословным и литературным переводом.",
        "index_note_epub": "Первые строки шлок в алфавитном порядке, со ссылками на место в книге, пословным и литературным переводом.",
        "version": "Версия от",
        "app": "Книга в виде приложения (с поиском):",
        "cover": "Обложка",
        "pages": "с.",
        "appendix": "Цитаты Гурудева — все варианты",
        "appendix_note": "Для каждого блока «Настроение Гурудева» — остальные цитаты Гурудева на ту же тему (в самом блоке напечатана выбранная). Дословно из транскриптов лекций, с переводом и источником.",
        "appendix_block": "блок на",
    },
}

# IAST alphabet (Sanskrit order); digraphs are single letters.
IAST_ORDER = [
    "a", "ā", "i", "ī", "u", "ū", "ṛ", "ṝ", "ḷ", "ḹ", "e", "ai", "o", "au", "ṁ", "ṃ", "ḥ",
    "k", "kh", "g", "gh", "ṅ", "c", "ch", "j", "jh", "ñ", "ṭ", "ṭh", "ḍ", "ḍh", "ṇ",
    "t", "th", "d", "dh", "n", "p", "ph", "b", "bh", "m", "y", "r", "l", "v", "ś", "ṣ", "s", "h",
]
IAST_RANK = {t: i + 1 for i, t in enumerate(IAST_ORDER)}
RU_ALPHABET = "абвгдеёжзийклмнопрстуфхцчшщъыьэюя"
RU_RANK = {c: i + 1 for i, c in enumerate(RU_ALPHABET)}


# ---------------------------------------------------------------- helpers

def find_file(candidates):
    for c in candidates:
        if c and Path(c).is_file():
            return Path(c)
    return None


def find_fonts():
    fonts = {}
    for key, name in FONT_FILES.items():
        for d in FONT_DIRS:
            if str(d) and (d / name).is_file():
                fonts[key] = d / name
                break
        else:
            sys.exit(f"Font {name} not found (set NOTO_FONT_DIR)")
    return fonts


def esc(text: str) -> str:
    return html.escape(text or "", quote=True)


def inline(text: str) -> str:
    """Running text -> HTML; ⟦…⟧ runs become bold Sanskrit spans."""
    out = esc(text)
    return re.sub(r"⟦([^⟦⟧]*)⟧", r'<b class="sa">\1</b>', out)


def strip_inline(text: str) -> str:
    return re.sub(r"[⟦⟧]", "", text or "")


def is_cyrillic(text: str) -> bool:
    return bool(re.search(r"[Ѐ-ӿ]", text or ""))


def sa_lang(text: str) -> str:
    return "sa-Cyrl" if is_cyrillic(text) else "sa-Latn"


def lines_br(text: str, fn=inline) -> str:
    return "<br/>".join(fn(line) for line in (text or "").split("\n"))


def parse_wbw(wbw: str):
    pairs = []
    for part in (wbw or "").split(";"):
        part = part.strip()
        if not part:
            continue
        m = re.match(r"^(.*?)\s+[—–-]\s+(.*)$", part)
        pairs.append((m.group(1).strip(), m.group(2).strip()) if m else (part, ""))
    return pairs


def wbw_html(wbw: str) -> str:
    out = []
    for word, meaning in parse_wbw(wbw):
        w = f'<span class="w">{esc(word)}</span>'
        out.append(f"{w} — {inline(meaning)}" if meaning else w)
    return "; ".join(out)


def sort_key(first_line: str):
    """Alphabetical key: IAST order for Latin, Russian alphabet for Cyrillic."""
    s = unicodedata.normalize("NFC", first_line.lower())
    s = re.sub(r"^[^\wЀ-ӿ]+", "", s)  # leading quotes, brackets
    s = s.replace("-", "").replace("'", "").replace("’", "").replace("‘", "")
    key = []
    if is_cyrillic(s):
        for ch in s:
            if ch not in "йё":
                ch = "".join(c for c in unicodedata.normalize("NFD", ch) if not unicodedata.combining(c))
            for c in ch:
                if c == " ":
                    key.append(0)
                elif c in RU_RANK:
                    key.append(RU_RANK[c])
                elif c.isalpha():
                    key.append(100 + ord(c))
        return key
    s = s.replace("ṃ", "ṁ")
    i = 0
    while i < len(s):
        two, one = s[i:i + 2], s[i]
        if two in IAST_RANK:
            key.append(IAST_RANK[two])
            i += 2
            continue
        if one == " ":
            key.append(0)
        elif one in IAST_RANK:
            key.append(IAST_RANK[one])
        elif one.isalpha():
            base = "".join(c for c in unicodedata.normalize("NFD", one) if not unicodedata.combining(c))
            key.append(IAST_RANK.get(base, 1000 + ord(one)))
        i += 1
    return key


def to_roman(n: int) -> str:
    out = ""
    for v, sym in ((1000, "M"), (900, "CM"), (500, "D"), (400, "CD"), (100, "C"), (90, "XC"),
                   (50, "L"), (40, "XL"), (10, "X"), (9, "IX"), (5, "V"), (4, "IV"), (1, "I")):
        while n >= v:
            out += sym
            n -= v
    return out


def toc_layout(section_ids, parts):
    """Reading order [("part", pi) | ("sec", si)] - same rule as lib/book.ts tocLayout():
    each part's page just before its first chapter, empty parts after the previous part."""
    part_of = {sid: pi for pi, prt in enumerate(parts) for sid in prt.get("sections", [])}
    out, emitted = [], 0
    for si, sid in enumerate(section_ids):
        pi = part_of.get(sid)
        if pi is not None:
            while emitted <= pi:
                out.append(("part", emitted))
                emitted += 1
        elif emitted > 0:
            while emitted < len(parts) and not parts[emitted].get("sections"):
                out.append(("part", emitted))
                emitted += 1
        out.append(("sec", si))
    while emitted < len(parts):
        out.append(("part", emitted))
        emitted += 1
    return out


# ---------------------------------------------------------------- data

class Edition:
    def __init__(self, lang: str):
        self.lang = lang
        f = DATA / ("book.json" if lang == "en" else f"book.{lang}.json")
        if not f.is_file():
            sys.exit(f"No data file for language '{lang}': {f}")
        self.book = json.loads(f.read_text(encoding="utf-8"))
        ui = json.loads((DATA / "ui.en.json").read_text(encoding="utf-8"))
        uf = DATA / f"ui.{lang}.json"
        if uf.is_file():
            ui.update(json.loads(uf.read_text(encoding="utf-8")))
        self.ui = ui
        langs = json.loads((REPO / "lib/languages.json").read_text(encoding="utf-8"))
        self.html_lang = next((l["htmlLang"] for l in langs if l["code"] == lang), lang)
        s = dict(LANG_STRINGS["en"])
        s["name"] = f"Arcana Paddhati ({lang.upper()})"
        s["toc"] = ui.get("sidebar.contents", s["toc"])
        s.update(LANG_STRINGS.get(lang, {}))
        self.s = s
        self.version = content_version()
        # Parts (I, II, III): structure from the English book, titles from this language.
        en_parts = json.loads((DATA / "book.json").read_text(encoding="utf-8")).get("parts", [])
        own = {prt["id"]: prt for prt in self.book.get("parts", [])}
        self.parts = [dict(prt, title=own.get(prt["id"], prt)["title"]) for prt in en_parts]
        self.layout = toc_layout([sec["id"] for sec in self.book["sections"]], self.parts)
        part_by_sid = {sid: pi for pi, prt in enumerate(self.parts) for sid in prt["sections"]}
        self.part_of = {si: part_by_sid.get(sec["id"]) for si, sec in enumerate(self.book["sections"])}
        # Chapter numbers: every section in order, front matter included: 1, 2, 3, ...
        self.nums = list(range(1, len(self.book["sections"]) + 1))
        # Number every verse once (same ids in PDF and EPUB) and collect the index.
        self.verse_ids = {}
        n = 0
        for si, sec in enumerate(self.book["sections"]):
            for blk in self.all_blocks(sec):
                if blk.get("type") == "verse":
                    n += 1
                    self.verse_ids[id(blk)] = (f"v{n}", si)
        self.index = self.build_index()
        # Mood blocks: anchor id per block; those with other quotes go to the appendix.
        self.mood_ids = {}
        self.appendix = []  # (mood id, section index, subsection index or None, block)
        n = 0
        for si, sec in enumerate(self.book["sections"]):
            nodes = [(sec, None)] + [(sub, sj) for sj, sub in enumerate(sec.get("subsections", []))]
            for node, sj in nodes:
                for blk in node.get("content", []):
                    if blk.get("type") == "mood":
                        n += 1
                        self.mood_ids[id(blk)] = f"m{n}"
                        if blk.get("more"):
                            self.appendix.append((f"m{n}", si, sj, blk))

    def num(self, si, sj=None):
        """'2' for chapter si, '2.1' for its subsection sj."""
        n = self.nums[si]
        if n is None:
            return None
        return str(n) if sj is None else f"{n}.{sj + 1}"

    def _title(self, si, sj):
        sec = self.book["sections"][si]
        return sec["title"] if sj is None else sec["subsections"][sj]["title"]

    def label(self, si, sj=None) -> str:
        """Plain-text title with its number: '2. Title' / '2.1. Title'."""
        n = self.num(si, sj)
        return f"{n}. {self._title(si, sj)}" if n else self._title(si, sj)

    def label_html(self, si, sj=None) -> str:
        """Title with its number as a muted span: <span class="num">2.</span> Title."""
        n = self.num(si, sj)
        return (f'<span class="num">{n}.</span> ' if n else "") + esc(self._title(si, sj))

    def full_title(self) -> str:
        """'Арчана-паддхати — Процесс поклонения Божеству' (name — subtitle)."""
        b = self.book
        return f'{b["title"]} — {b["subtitle"]}' if b.get("subtitle") else b["title"]

    def part_label(self, pi) -> str:
        """'Part I' / 'Часть I' (ui part.label)."""
        return self.ui.get("part.label", "Part {n}").replace("{n}", to_roman(pi + 1))

    def part_title(self, pi) -> str:
        """Plain 'I. Temple worship' for contents / outline / nav."""
        return f"{to_roman(pi + 1)}. {self.parts[pi]['title']}"

    def part_title_html(self, pi) -> str:
        return f'<span class="num">{to_roman(pi + 1)}.</span> {esc(self.parts[pi]["title"])}'

    def part_html(self, pi) -> str:
        """Part page: label, title, and 'in preparation' while the part is empty."""
        empty = "" if self.parts[pi]["sections"] else f'<p class="pe">{esc(self.ui.get("part.empty", ""))}</p>'
        return (f'<section class="part" id="p{pi}"><p class="pl">{esc(self.part_label(pi))}</p>'
                f'<h1>{esc(self.parts[pi]["title"])}</h1>{empty}</section>')

    @staticmethod
    def all_blocks(sec):
        yield from sec.get("content", [])
        for sub in sec.get("subsections", []):
            yield from sub.get("content", [])

    def build_index(self):
        """Verse index: verses with translation/word-by-word, or of 2+ lines
        (one-line procedural mantras are left out). Same first line = one entry."""
        entries = {}
        for sec in self.book["sections"]:
            for blk in self.all_blocks(sec):
                if blk.get("type") != "verse" or not blk.get("sanskrit"):
                    continue
                sk = strip_inline(blk["sanskrit"]).strip()
                lines = [l for l in sk.split("\n") if l.strip()]
                if not (blk.get("translation") or blk.get("wbw") or len(lines) >= 2):
                    continue
                first = lines[0].strip()
                norm = re.sub(r"\s+", " ", first.lower()).strip(" ,.;|।॥")
                e = entries.setdefault(norm, {"first": first, "ids": [], "wbw": "", "translation": "", "key": sort_key(first)})
                e["ids"].append(self.verse_ids[id(blk)])
                e["wbw"] = e["wbw"] or blk.get("wbw", "")
                e["translation"] = e["translation"] or blk.get("translation", "")
        return sorted(entries.values(), key=lambda e: (e["key"], e["first"]))

    # ------------------------------------------------------------ blocks

    def blocks_html(self, items, epub=False) -> str:
        return "\n".join(self.block_html(it, epub) for it in items)

    def block_html(self, it, epub) -> str:
        t = it.get("type")
        if t == "verse":
            return self.verse_html(it)
        if t == "subtitle":
            return f'<h3>{inline(it.get("content", ""))}</h3>'
        if t == "instruction":
            return f'<p class="instr">{inline(it.get("content", ""))}</p>'
        if t == "list":
            rows = [l for l in (it.get("content") or "").split("\n") if l.strip()]
            nums = it.get("numbers")
            lis = []
            for i, line in enumerate(rows):
                lab = (f"{nums[i]})" if nums[i] else "–") if nums and i < len(nums) else f"{i + 1})"
                lis.append(f'<li><span class="n">{esc(lab)}</span> <span class="t">{inline(line)}</span></li>')
            return '<ol class="list">' + "".join(lis) + "</ol>"
        if t == "bullet-list":
            rows = [l for l in (it.get("content") or "").split("\n") if l.strip()]
            return '<ul class="bl">' + "".join(f"<li>{inline(r)}</li>" for r in rows) + "</ul>"
        if t == "paired-list":
            if it.get("layout") == "vertical":
                out = []
                for p in it.get("items", []):
                    out.append(
                        f'<div class="pv"><p class="pv-l" lang="{sa_lang(p["label"])}">{esc(strip_inline(p["label"]))}</p>'
                        f'<p class="pv-v">{inline(p["value"])}</p></div>')
                return '<div class="pvl">' + "".join(out) + "</div>"
            nums = it.get("numbers")  # optional number per row (e.g. the illustration's numbers)
            rows = ""
            for i, p in enumerate(it.get("items", [])):
                num = ""
                if nums:
                    lab = f"{nums[i]})" if i < len(nums) and nums[i] else "–"
                    num = f'<td class="pn">{esc(lab)}</td>'
                rows += f'<tr>{num}<td class="pl">{inline(p["label"])}</td><td>{inline(p["value"])}</td></tr>'
            return f'<table class="pairs"><tbody>{rows}</tbody></table>'
        if t == "table":
            head = "".join(f"<th>{inline(h)}</th>" for h in it.get("header", []))
            body = ""
            for r in it.get("rows", []):
                cells = r.get("cells", [])
                tds = "".join((f"<th>{inline(c)}</th>" if i == 0 else f"<td>{inline(c)}</td>") for i, c in enumerate(cells))
                cls = ' class="hl"' if r.get("highlight") else ""
                body += f"<tr{cls}>{tds}</tr>"
            return f'<table class="dt"><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>'
        if t == "mood":
            return self.mood_html(it, epub)
        if t == "sources":  # source line of an intro chapter: one line per lecture + its transcript / audio links
            links = it.get("links") or []
            rows = []
            for i, line in enumerate((it.get("content") or "").split("\n")):
                l = links[i] if i < len(links) else None
                rows.append(inline(line) + "".join(
                    f' · <a href="{esc(l[k])}">{esc(self.ui[lab])}</a>'
                    for k, lab in (("transcript_url", "mood.transcript"), ("audio_url", "mood.audio")) if l and l.get(k)))
            return '<p class="srcnote">' + "<br/>".join(rows) + "</p>"
        if t == "image":
            return (f'<div class="img"><img src="images/{esc(it.get("src", ""))}" alt="{esc(it.get("alt", ""))}"/></div>')
        content = it.get("content", "")
        return f"<p>{lines_br(content)}</p>"

    def verse_html(self, it) -> str:
        vid, _ = self.verse_ids[id(it)]
        sk = it.get("sanskrit", "")
        stanzas = "".join(f"<p>{lines_br(st, lambda l: esc(strip_inline(l)))}</p>" for st in sk.split("\n\n"))
        tr, wbw = it.get("translation"), it.get("wbw")
        cls = "verse" if (tr or wbw or "\n" in sk) else "verse mantra"
        out = [f'<div class="{cls}" id="{vid}"><div class="sk" lang="{sa_lang(sk)}">{stanzas}</div>']
        if wbw:
            out.append(f'<p class="wbw">{wbw_html(wbw)}</p>')
        if tr:
            out.append(f'<p class="tr">{lines_br(tr)}</p>')
        out.append("</div>")
        return "".join(out)

    def mood_html(self, it, epub) -> str:
        mid = self.mood_ids.get(id(it))
        attr = f' id="{mid}"' if mid else ""
        return f'<div class="mood"{attr}>{self.quote_html(it, epub)}</div>'

    def quote_html(self, it, epub) -> str:
        """Gurudev's words (EN), translation, source line (+ links in EPUB)."""
        ui = self.ui
        def paras(text, cls):
            return "".join(f'<p class="{cls}{" gap" if p.strip() == "[…]" else ""}">{esc(p)}</p>'
                           for p in (text or "").split("\n\n"))
        out = [f'<p class="ml">{esc(ui["mood.words"])}</p>',
               f'<div lang="en">{paras(it.get("quote", ""), "mq")}</div>']
        if it.get("translation"):
            note = f' <span class="mn">({esc(ui["mood.machine"])})</span>' if it.get("translation_note") == "machine" else ""
            out.append(f'<p class="ml ml2">{esc(ui["mood.translation"])}{note}</p>{paras(it["translation"], "mt")}')
        src = it.get("source")
        if src:
            line = " · ".join(x for x in [src.get("title"), src.get("date"),
                                          f'№ {src["nr"]}' if src.get("nr") else "", src.get("timecode"), src.get("note")] if x)
            links = ""
            if epub:
                for key, lab in (("transcript_url", "mood.transcript"), ("audio_url", "mood.audio")):
                    if src.get(key):
                        links += f' · <a href="{esc(src[key])}">{esc(ui[lab])}</a>'
            out.append(f'<p class="ms"><span lang="{esc(src.get("lang") or "en")}">{esc(line)}</span>{links}</p>')
        return "".join(out)

    def appendix_html(self, ref) -> str:
        """Appendix chapter: the other quotes of every mood block. `ref(mood_id, si)`
        returns the HTML of the reference to the block (page number or link)."""
        s = self.s
        out = [f'<section class="ap" id="ap"><h1>{esc(s["appendix"])}</h1><p class="note">{esc(s["appendix_note"])}</p>']
        for mid, si, sj, blk in self.appendix:
            title = self.label_html(si, sj)
            ctx = f"{self.label_html(si)} · " if sj is not None else ""
            out.append(f'<div class="ap-block"><h2>{title}</h2>'
                       f'<p class="ap-ref">{ctx}{esc(s["appendix_block"])} {ref(mid, si)}</p>')
            for alt in blk["more"]:
                out.append(f'<div class="mood ap-q">{self.quote_html(alt, epub=True)}</div>')
            out.append("</div>")
        out.append("</section>")
        return "\n".join(out)

    def section_html(self, si, sec, epub=False) -> str:
        out = [f'<section class="chap" id="s{si}"><h1>{self.label_html(si)}</h1>']
        if sec.get("subtitle"):
            out.append(f'<p class="sub">{esc(sec["subtitle"])}</p>')
        out.append(self.blocks_html(sec.get("content", []), epub))
        for sj, sub in enumerate(sec.get("subsections", [])):
            out.append(f'<section class="subsec" id="s{si}-{sj}"><h2>{self.label_html(si, sj)}</h2>')
            out.append(self.blocks_html(sub.get("content", []), epub))
            out.append("</section>")
        out.append("</section>")
        return "\n".join(out)


def content_version() -> str:
    try:
        r = subprocess.run(["git", "log", "-1", "--format=%cs", "--", "data"], cwd=REPO,
                           capture_output=True, text=True, timeout=30)
        if r.stdout.strip():
            return r.stdout.strip()
    except Exception:
        pass
    return dt.date.today().isoformat()


# ---------------------------------------------------------------- shared CSS

BASE_CSS = """
body { font-family: 'Noto Serif', serif; color: #1a1a1a; }
h1, h2, h3 { font-weight: 700; color: #2C1810; }
b.sa { font-weight: 700; font-style: normal; }
.verse .sk, .pv-l { font-weight: 700; }
.verse .sk p { margin: 0 0 0.4em 0; }
.wbw .w { font-weight: 700; font-style: italic; }
.tr { font-style: italic; }
.mood { border-left: 2.5pt solid #B8860B; background: #FBF4E6; }
.mood .ml { font-size: 0.72em; font-weight: 700; letter-spacing: 0.08em; text-transform: uppercase; color: #8B6508; margin: 0 0 0.3em 0; }
.mood .ml2 { margin-top: 0.7em; padding-top: 0.5em; border-top: 0.5pt solid #E3CFA8; }
.mood .mn { font-weight: 400; text-transform: none; letter-spacing: 0; }
.mood .mq { color: #2C1810; margin: 0 0 0.4em 0; }
.mood .mt { font-style: italic; margin: 0 0 0.4em 0; }
.mood .gap { color: #8B6508; }
.mood .ms { font-size: 0.78em; color: #5C3D2E; border-top: 0.5pt solid #E3CFA8; padding-top: 0.35em; margin: 0.6em 0 0 0; }
.srcnote { font-size: 0.85em; font-style: italic; color: #5C3D2E; }
.srcnote a { color: #8B6508; font-style: normal; }
.img { text-align: center; }
.img img { max-width: 100%; }
table.pairs { border-collapse: collapse; }
table.pairs td { vertical-align: top; padding: 0.1em 0; }
table.pairs td.pl { padding-right: 1.2em; }
table.pairs td.pn { padding-right: 0.5em; text-align: right; color: #5C3D2E; }
table.dt { border-collapse: collapse; width: 100%; font-size: 0.78em; line-height: 1.25; margin: 0.8em 0; }
table.dt th, table.dt td { text-align: left; vertical-align: top; padding: 0.25em 0.3em; border-bottom: 1px solid #E8DCC8; }
table.dt thead th { font-weight: 600; color: #5C3D2E; border-bottom: 1.5px solid #D4A843; vertical-align: bottom; }
table.dt tr.hl { background: #FBF0D9; }
table.dt tr.hl td:last-child { font-weight: 600; color: #8B6508; }
table.dt tr { break-inside: avoid; page-break-inside: avoid; }
ol.list, ul.bl { list-style: none; padding: 0; }
ol.list li { padding-left: 2.6em; text-indent: -2.6em; }
ol.list .n { display: inline-block; width: 2.2em; text-align: right; text-indent: 0; color: #5C3D2E; }
ul.bl li { padding-left: 1.2em; text-indent: -1.2em; }
ul.bl li::before { content: "– "; color: #B8860B; }
.instr { padding-left: 1.1em; text-indent: -1.1em; }
.instr::before { content: "•\\00a0\\00a0"; color: #5C3D2E; }
.pv-v { margin: 0 0 0.6em 2em; font-style: italic; }
.pv-l { margin: 0; }
.sub { font-style: italic; color: #555; }
.ix-entry .ix-first { font-weight: 700; }
.ap .note { font-style: italic; color: #555; }
.ap-ref { font-size: 0.85em; color: #5C3D2E; font-style: italic; }
.ap-ref a { color: #8B6508; }
.ms a { color: #8B6508; }
.num { color: #9C7A4E; }
.part { text-align: center; }
.part .pl { color: #9C7A4E; letter-spacing: 0.14em; text-transform: uppercase; }
.part .pe { font-style: italic; color: #5C3D2E; }
"""


def font_face_css(urls: dict) -> str:
    spec = {"regular": (400, "normal"), "bold": (700, "normal"),
            "italic": (400, "italic"), "bolditalic": (700, "italic")}
    return "\n".join(
        f"@font-face {{ font-family: 'Noto Serif'; font-weight: {w}; font-style: {s}; src: url('{urls[k]}'); }}"
        for k, (w, s) in spec.items())


# ---------------------------------------------------------------- PRINT

PRINT_CSS = """
@page { size: 148mm 210mm; }
@page :right { margin: 19mm 15mm 19mm 21mm; }
@page :left { margin: 19mm 21mm 19mm 15mm; }
@page cover { margin: 0; }
html { font-size: 10pt; }
body { margin: 0; line-height: 1.42; hyphens: auto; text-align: justify; orphans: 2; widows: 2; }
p { margin: 0 0 0.45em 0; }
.coverpage { page: cover; break-after: page; width: 148mm; height: 210mm; overflow: hidden; }
.coverpage img { width: 148mm; height: 210mm; object-fit: cover; display: block; }
.blank { break-after: page; height: 1px; }
.titlepage { break-after: page; text-align: center; padding-top: 38mm; }
.titlepage .t1 { font-size: 24pt; font-weight: 700; color: #2C1810; line-height: 1.2; margin-bottom: 6mm; }
.titlepage .t2 { font-size: 13pt; font-style: italic; color: #5C3D2E; }
.titlepage .orn { color: #B8860B; font-size: 14pt; margin: 9mm 0; }
.titlepage img { width: 22mm; margin-top: 40mm; }
.imprint { break-after: page; padding-top: 140mm; font-size: 8.5pt; color: #5C3D2E; text-align: left; }
.toc { break-after: page; }
.toc h1, .ix h1 { font-size: 16pt; text-align: center; margin: 0 0 6mm 0; }
.toc ol { list-style: none; margin: 0; padding: 0; }
.toc li { display: flex; align-items: flex-end; text-align: left; }
.toc li.l1 { font-weight: 700; margin-top: 2.2mm; }
.toc li.l2 { padding-left: 5mm; font-size: 9pt; }
.toc li .tt { flex: 0 1 auto; }
.toc li .dots { flex: 1 0 4mm; border-bottom: 0.6pt dotted #999; margin: 0 1.5mm 0.8mm 1.5mm; }
.toc li a { color: inherit; text-decoration: none; }
.toc li .pg { flex: 0 0 auto; min-width: 7mm; text-align: right; font-variant-numeric: tabular-nums; }
.chap { break-before: page; }
.chap > h1 { font-size: 17pt; line-height: 1.2; margin: 6mm 0 2mm 0; text-align: left; }
.chap > .sub { margin-bottom: 4mm; }
.chap > h1 + * { margin-top: 5mm; }
h2 { font-size: 12.5pt; line-height: 1.25; margin: 6mm 0 2.5mm 0; text-align: left; break-after: avoid; }
h3 { font-size: 10.5pt; margin: 4mm 0 1.5mm 0; text-align: left; break-after: avoid; }
.subsec { border-top: 0.5pt solid #E8DCC8; margin-top: 5mm; }
.verse { margin: 2.5mm 0 3mm 0; text-align: left; }
.verse .sk { break-inside: avoid; break-after: avoid; }
.verse .sk { font-size: 10pt; line-height: 1.5; padding-left: 5mm; }
.verse.mantra { margin: 1.5mm 0; }
.verse.mantra .sk { padding-left: 8mm; }
.wbw { font-size: 8.8pt; line-height: 1.42; padding-left: 4mm; border-left: 0.6pt solid #D4B26A; margin: 1.5mm 0 1.5mm 1mm; text-align: left; }
.tr { padding-left: 4mm; border-left: 0.6pt solid #999; margin: 1.5mm 0 0 1mm; text-align: left; }
.mood { padding: 2.5mm 3.5mm; margin: 3mm 0; font-size: 9.3pt; break-inside: avoid; text-align: left; }
.img { margin: 3mm 0; break-inside: avoid; }
.img img { max-height: 95mm; }
.pairs { margin: 2mm 0; text-align: left; }
ol.list, ul.bl { margin: 2mm 0; text-align: left; }
h1 + .verse, h2 + .verse, h3 + .verse { break-before: avoid; }
.part { break-before: page; break-after: page; padding-top: 55mm; }
.part .pl { font-size: 10pt; margin: 0 0 4mm 0; }
.part h1 { font-size: 20pt; line-height: 1.25; margin: 0 0 10mm 0; text-align: center; }
.part .pe { font-size: 10.5pt; text-align: center; }
.toc li.l0 { font-weight: 700; margin-top: 4.5mm; text-transform: uppercase; letter-spacing: 0.06em; font-size: 9pt; color: #5C3D2E; }
.ix { break-before: page; }
.ix .note { font-size: 8.5pt; font-style: italic; color: #555; text-align: center; margin-bottom: 5mm; }
.ix-entry { margin: 0 0 3mm 0; text-align: left; break-inside: avoid; font-size: 9pt; }
.ix-entry .ix-head { display: flex; align-items: baseline; }
.ix-entry .ix-first { flex: 0 1 auto; }
.ix-entry .dots { flex: 1 0 4mm; border-bottom: 0.6pt dotted #999; margin: 0 1.5mm 0.8mm 1.5mm; }
.ix-entry .pg { flex: 0 0 auto; text-align: right; }
.ix-entry .pg a { color: inherit; text-decoration: none; }
.ix-entry .wbw { font-size: 8.3pt; margin: 0.8mm 0 0.8mm 1mm; }
.ix-entry .tr { font-size: 8.6pt; margin: 0.8mm 0 0 1mm; }
.ap { break-before: page; }
.ap > h1 { font-size: 16pt; text-align: center; margin: 0 0 4mm 0; }
.ap > .note { font-size: 8.5pt; text-align: center; margin-bottom: 5mm; }
.ap-block { margin: 0 0 4mm 0; }
.ap-block > h2 { border-top: 0.5pt solid #E8DCC8; padding-top: 2mm; margin-top: 5mm; }
.ap-ref { margin: 0 0 2mm 0; text-align: left; }
.mood.ap-q { break-inside: auto; }
.ap-block > h2, .ap-ref, .mood .ml, .mood .ml2 { break-after: avoid; }
.ms a { text-decoration: none; }
"""


def print_html(ed: Edition, fonts_url: dict, toc_pages=None, verse_pages=None, mood_pages=None) -> str:
    s, b = ed.s, ed.book
    pg = (lambda key: str(toc_pages.get(key, ""))) if toc_pages else (lambda key: "000")
    parts = [f'<div class="coverpage"><img src="cover.jpg" alt="{esc(s["cover"])}"/></div>',
             '<div class="blank"></div>',
             f'<div class="titlepage"><div class="t1">{esc(b["title"])}</div>'
             f'<div class="orn">❦</div>' + (f'<div class="t2">{esc(b["subtitle"])}</div>' if b.get("subtitle") else "") +
             f'<img src="images/CA_logo.png" alt=""/></div>',
             f'<div class="imprint">' + (f'<p>{esc(b["subtitle"])}</p>' if b.get("subtitle") else "") +
             f'<p>{esc(s["version"])} {ed.version}</p>'
             f'<p>{esc(s["app"])}<br/>{esc(APP_URL)}</p></div>']
    toc = [f'<div class="toc"><h1>{esc(s["toc"])}</h1><ol>']
    for kind, si in ed.layout:
        if kind == "part":
            toc.append(f'<li class="l0"><span class="tt">{ed.part_title_html(si)}</span><span class="dots"></span>'
                       f'<a class="pg" href="#p{si}">{pg(f"p{si}")}</a></li>')
            continue
        sec = b["sections"][si]
        toc.append(f'<li class="l1"><span class="tt">{ed.label_html(si)}</span><span class="dots"></span>'
                   f'<a class="pg" href="#s{si}">{pg(f"s{si}")}</a></li>')
        for sj, sub in enumerate(sec.get("subsections", [])):
            toc.append(f'<li class="l2"><span class="tt">{ed.label_html(si, sj)}</span><span class="dots"></span>'
                       f'<a class="pg" href="#s{si}-{sj}">{pg(f"s{si}-{sj}")}</a></li>')
    if ed.appendix:
        toc.append(f'<li class="l1"><span class="tt">{esc(s["appendix"])}</span><span class="dots"></span>'
                   f'<a class="pg" href="#ap">{pg("ap")}</a></li>')
    toc.append(f'<li class="l1"><span class="tt">{esc(s["index"])}</span><span class="dots"></span>'
               f'<a class="pg" href="#ix">{pg("ix")}</a></li></ol></div>')
    parts.append("".join(toc))
    for kind, si in ed.layout:
        parts.append(ed.part_html(si) if kind == "part" else ed.section_html(si, b["sections"][si]))
    if ed.appendix:
        mp = (lambda mid: str(mood_pages.get(mid, ""))) if mood_pages else (lambda mid: "000")
        parts.append(ed.appendix_html(lambda mid, si: f'{esc(s["pages"])}\u00a0<a href="#{mid}">{mp(mid)}</a>'))
    ix = [f'<div class="ix" id="ix"><h1>{esc(s["index"])}</h1><p class="note">{esc(s["index_note"])}</p>']
    for e in ed.index:
        if verse_pages:
            seen, links = set(), []
            for vid, _ in e["ids"]:
                p = verse_pages.get(vid)
                if p and p not in seen:
                    seen.add(p)
                    links.append(f'<a href="#{vid}">{p}</a>')
            nums = ", ".join(links)
        else:
            nums = ", ".join(f'<a href="#{vid}">000</a>' for vid, _ in e["ids"])
        ix.append(f'<div class="ix-entry"><div class="ix-head"><span class="ix-first" lang="{sa_lang(e["first"])}">'
                  f'{esc(e["first"])}</span><span class="dots"></span><span class="pg">{nums}</span></div>')
        if e["wbw"]:
            ix.append(f'<p class="wbw">{wbw_html(e["wbw"])}</p>')
        if e["translation"]:
            ix.append(f'<p class="tr">{lines_br(e["translation"])}</p>')
        ix.append("</div>")
    ix.append("</div>")
    parts.append("".join(ix))
    css = font_face_css(fonts_url) + BASE_CSS + PRINT_CSS
    return (f'<!DOCTYPE html><html lang="{ed.html_lang}"><head><meta charset="utf-8"/>'
            f'<title>{esc(b["title"])}</title><style>{css}</style></head><body>\n'
            + "\n".join(parts) + "\n</body></html>")


def chrome_pdf(chrome: Path, html_file: Path, pdf_file: Path, profile: Path):
    if pdf_file.exists():
        pdf_file.unlink()
    cmd = [str(chrome), "--headless=new", "--disable-gpu", "--no-first-run", "--no-default-browser-check",
           "--disable-extensions", f"--user-data-dir={profile}", "--no-pdf-header-footer",
           "--run-all-compositor-stages-before-draw", "--virtual-time-budget=20000",
           f"--print-to-pdf={pdf_file}", html_file.resolve().as_uri()]
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    subprocess.run(cmd, check=True, capture_output=True, timeout=600, creationflags=flags)
    if not pdf_file.is_file():
        sys.exit(f"Chrome did not write {pdf_file}")


def dest_pages(doc):
    """1-based page of every link target (Chrome writes named destinations)."""
    return {name: d["page"] + 1 for name, d in doc.resolve_names().items() if d.get("page", -1) >= 0}


def build_print(ed: Edition, fonts: dict, chrome: Path, work: Path, out_pdf: Path):
    work.mkdir(parents=True, exist_ok=True)
    shutil.copy(PUBLIC / "cover.jpg", work / "cover.jpg")
    shutil.copytree(PUBLIC / "images", work / "images", dirs_exist_ok=True,
                    ignore=shutil.ignore_patterns("desktop.ini"))
    furl = {k: Path(v).resolve().as_uri() for k, v in fonts.items()}
    profile = work / "chrome-profile"
    html1, pdf1 = work / "pass1.html", work / "pass1.pdf"
    html1.write_text(print_html(ed, furl), encoding="utf-8")
    chrome_pdf(chrome, html1, pdf1, profile)

    d1 = fitz.open(pdf1)
    toc_keys = []
    for si, sec in enumerate(ed.book["sections"]):
        toc_keys.append(f"s{si}")
        toc_keys += [f"s{si}-{sj}" for sj in range(len(sec.get("subsections", [])))]
    toc_keys += [f"p{pi}" for pi in range(len(ed.parts))]
    if ed.appendix:
        toc_keys.append("ap")
    toc_keys.append("ix")
    mood_keys = [mid for mid, *_ in ed.appendix]
    names = dest_pages(d1)
    missing = [k for k in toc_keys if k not in names]
    missing += [vid for e in ed.index for vid, _ in e["ids"] if vid not in names]
    missing += [mid for mid in mood_keys if mid not in names]
    if missing:
        sys.exit(f"pass 1: no PDF destination for {missing[:10]}")
    toc_pages = {k: names[k] for k in toc_keys}
    verse_pages = {vid: names[vid] for e in ed.index for vid, _ in e["ids"]}
    mood_pages = {mid: names[mid] for mid in mood_keys}
    n1 = len(d1)
    d1.close()

    html2, pdf2 = work / "pass2.html", work / "pass2.pdf"
    html2.write_text(print_html(ed, furl, toc_pages, verse_pages, mood_pages), encoding="utf-8")
    chrome_pdf(chrome, html2, pdf2, profile)
    doc = fitz.open(pdf2)
    # Check pass 2 kept the layout of pass 1 (section starts).
    # (a verse listed twice on one page is linked once, so it has no destination)
    names2 = dest_pages(doc)
    check = {k: names2.get(k) for k in toc_keys}
    ref_pages = {**verse_pages, **mood_pages}
    if check != toc_pages or any(v in names2 and names2[v] != p for v, p in ref_pages.items()):
        diff = {k: (toc_pages[k], check.get(k)) for k in toc_pages if toc_pages[k] != check.get(k)}
        diff.update({v: (p, names2.get(v)) for v, p in ref_pages.items() if v in names2 and names2[v] != p})
        sys.exit(f"pass 2 layout differs from pass 1: {diff}")

    # Running headers, page numbers, bookmarks.
    sections = ed.book["sections"]
    starts = sorted((toc_pages[f"s{si}"], ed.label(si)) for si in range(len(sections)))
    first_toc_page = 5
    ix_page = toc_pages["ix"]
    ap_page = toc_pages.get("ap", ix_page)
    f_it = fitz.Font(fontfile=str(fonts["italic"]))
    f_rg = fitz.Font(fontfile=str(fonts["regular"]))
    col = (0.36, 0.24, 0.18)
    mm = 72 / 25.4
    start_set = ({p for p, _ in starts} | {ix_page, ap_page, first_toc_page}
                 | {toc_pages[f"p{pi}"] for pi in range(len(ed.parts))})
    for pno in range(len(doc)):
        num = pno + 1
        if num < first_toc_page:
            continue
        page = doc[pno]
        page.wrap_contents()  # Chrome leaves its content transform active
        w = page.rect.width
        right = num % 2 == 1
        left_m, right_m = (21 * mm, 15 * mm) if right else (15 * mm, 21 * mm)
        cx = left_m + (w - left_m - right_m) / 2
        tw = fitz.TextWriter(page.rect)
        if num not in start_set:
            if num >= ix_page:
                head = ed.s["index"]
            elif num >= ap_page:
                head = ed.s["appendix"]
            elif num < starts[0][0]:
                head = ed.s["toc"]
            else:
                head = [t for p, t in starts if p <= num][-1]
            size = 7.8
            maxw = w - left_m - right_m
            while f_it.text_length(head, fontsize=size) > maxw and size > 6:
                size -= 0.2
            if f_it.text_length(head, fontsize=size) > maxw:
                while f_it.text_length(head + "…", fontsize=size) > maxw:
                    head = head[:-1]
                head = head.rstrip() + "…"
            hw = f_it.text_length(head, fontsize=size)
            tw.append((cx - hw / 2, 12.5 * mm), head, font=f_it, fontsize=size)
            page.draw_line((left_m, 14.2 * mm), (w - right_m, 14.2 * mm), color=(0.85, 0.78, 0.66), width=0.4)
        label = str(num)
        lw = f_rg.text_length(label, fontsize=8.5)
        tw.append((cx - lw / 2, page.rect.height - 10 * mm), label, font=f_rg, fontsize=8.5)
        tw.write_text(page, color=col)
    toc = [[1, ed.s["cover"], 1], [1, ed.s["toc"], first_toc_page]]
    for kind, si in ed.layout:
        if kind == "part":
            toc.append([1, ed.part_title(si), toc_pages[f"p{si}"]])
            continue
        lvl = 2 if ed.part_of[si] is not None else 1
        toc.append([lvl, ed.label(si), toc_pages[f"s{si}"]])
        for sj, sub in enumerate(sections[si].get("subsections", [])):
            toc.append([lvl + 1, ed.label(si, sj), toc_pages[f"s{si}-{sj}"]])
    if ed.appendix:
        toc.append([1, ed.s["appendix"], ap_page])
    toc.append([1, ed.s["index"], ix_page])
    doc.set_toc(toc)
    doc.set_metadata({"title": ed.full_title(), "author": "Chaitanya Academy",
                      "subject": ed.book.get("subtitle") or ed.book["title"], "creator": "build_formats.py", "producer": "Chrome + PyMuPDF"})
    doc.subset_fonts()
    out_pdf.parent.mkdir(parents=True, exist_ok=True)
    tmp = work / "final.pdf"
    doc.save(tmp, garbage=4, deflate=True)
    doc.close()
    shutil.copy(tmp, out_pdf)
    return {"pages": n1, "toc_pages": toc_pages, "mood_pages": mood_pages}


# ---------------------------------------------------------------- EPUB

EPUB_CSS = """
body { margin: 0 3%; line-height: 1.45; }
p { margin: 0 0 0.5em 0; }
h1 { font-size: 1.5em; margin: 0.6em 0 0.4em 0; line-height: 1.2; }
h2 { font-size: 1.2em; margin: 1.4em 0 0.5em 0; line-height: 1.25; page-break-after: avoid; }
h3 { font-size: 1.05em; margin: 1em 0 0.4em 0; page-break-after: avoid; }
.verse { margin: 0.8em 0 1em 0; }
.verse .sk { padding-left: 1em; line-height: 1.55; }
.verse.mantra { margin: 0.4em 0; }
.verse.mantra .sk { padding-left: 2em; }
.wbw { font-size: 0.9em; padding-left: 0.8em; border-left: 1px solid #D4B26A; margin: 0.4em 0 0.4em 0.2em; }
.tr { padding-left: 0.8em; border-left: 1px solid #999; margin: 0.4em 0 0 0.2em; }
.mood { padding: 0.6em 0.9em; margin: 0.9em 0; font-size: 0.93em; }
.img { margin: 0.8em 0; }
.pairs { margin: 0.5em 0; }
ol.list, ul.bl { margin: 0.5em 0; }
.cover { text-align: center; margin: 0; padding: 0; }
.cover img { max-width: 100%; max-height: 100%; }
.title { text-align: center; margin-top: 20%; }
.title .t1 { font-size: 1.8em; font-weight: 700; color: #2C1810; }
.title .t2 { font-style: italic; color: #5C3D2E; margin-top: 1em; }
.title .orn { color: #B8860B; font-size: 1.4em; margin: 0.8em 0; }
.title .imp { font-size: 0.8em; color: #5C3D2E; margin-top: 3em; }
.title img { width: 25%; margin-top: 2em; }
nav ol { list-style: none; padding-left: 0; }
nav ol ol { padding-left: 1.2em; }
.ix .note { font-size: 0.85em; font-style: italic; color: #555; }
.ix-entry { margin: 0 0 1em 0; }
.ix-entry .refs { font-size: 0.85em; }
.ap-block > h2 { border-top: 1px solid #E8DCC8; padding-top: 0.5em; }
.ap-ref { margin: 0 0 0.6em 0; }
.part { margin-top: 30%; }
.part .pl { font-size: 0.9em; margin: 0 0 0.6em 0; }
.part h1 { font-size: 1.7em; margin: 0 0 1.5em 0; }
"""


def xhtml(lang: str, title: str, body: str, extra_ns: str = "") -> str:
    return ('<?xml version="1.0" encoding="utf-8"?>\n<!DOCTYPE html>\n'
            f'<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops"{extra_ns} '
            f'lang="{lang}" xml:lang="{lang}"><head><meta charset="utf-8"/><title>{esc(title)}</title>'
            '<link rel="stylesheet" type="text/css" href="style.css"/></head>'
            f"<body>{body}</body></html>")


def subset_font(src: Path, dst: Path, text: str):
    from fontTools import subset
    opts = subset.Options()
    opts.layout_features = ["*"]
    opts.name_IDs = ["*"]
    opts.notdef_outline = True
    font = subset.load_font(str(src), opts)
    sub = subset.Subsetter(opts)
    sub.populate(text=text)
    sub.subset(font)
    subset.save_font(font, str(dst), opts)


def build_epub(ed: Edition, fonts: dict, out_epub: Path, work: Path):
    b, s, L = ed.book, ed.s, ed.html_lang
    files = {}  # name -> str/bytes
    sec_files = []
    for si, sec in enumerate(b["sections"]):
        name = f"sec{si:02d}.xhtml"
        sec_files.append(name)
        files[name] = xhtml(L, ed.label(si), ed.section_html(si, sec, epub=True))
    # verse index
    vfile = {vid: sec_files[si] for (vid, si) in ed.verse_ids.values()}
    ix = [f'<section class="ix" id="ix"><h1>{esc(s["index"])}</h1><p class="note">{esc(s["index_note_epub"])}</p>']
    for e in ed.index:
        seen, refs = set(), []
        for vid, si in e["ids"]:
            if si in seen:
                continue
            seen.add(si)
            refs.append(f'<a href="{vfile[vid]}#{vid}">{ed.label_html(si)}</a>')
        ix.append(f'<div class="ix-entry"><p class="ix-first" lang="{sa_lang(e["first"])}">{esc(e["first"])}</p>'
                  f'<p class="refs">→ {" · ".join(refs)}</p>')
        if e["wbw"]:
            ix.append(f'<p class="wbw">{wbw_html(e["wbw"])}</p>')
        if e["translation"]:
            ix.append(f'<p class="tr">{lines_br(e["translation"])}</p>')
        ix.append("</div>")
    ix.append("</section>")
    files["index.xhtml"] = xhtml(L, s["index"], "".join(ix))
    if ed.appendix:
        files["appendix.xhtml"] = xhtml(L, s["appendix"], ed.appendix_html(
            lambda mid, si: f'<a href="{sec_files[si]}#{mid}">→ {ed.label_html(si)}</a>'))
    part_files = []
    for pi in range(len(ed.parts)):
        part_files.append(f"part{pi + 1}.xhtml")
        files[part_files[-1]] = xhtml(L, ed.part_title(pi), ed.part_html(pi))
    files["cover.xhtml"] = xhtml(L, s["cover"], f'<div class="cover"><img src="cover.jpg" alt="{esc(s["cover"])}"/></div>')
    files["title.xhtml"] = xhtml(L, b["title"],
        f'<div class="title"><p class="t1">{esc(b["title"])}</p><p class="orn">❦</p>'
        + (f'<p class="t2">{esc(b["subtitle"])}</p>' if b.get("subtitle") else "") +
        f'<p class="imp">{esc(s["version"])} {ed.version}<br/>{esc(s["app"])}<br/><a href="{APP_URL}">{APP_URL}</a></p>'
        f'<img src="images/CA_logo.png" alt=""/></div>')
    # nav
    # contents tree: (label, href, children) - front matter, parts > chapters > subsections
    tree, cur = [(b["title"], "title.xhtml", [])], None
    for kind, si in ed.layout:
        if kind == "part":
            cur = (ed.part_title(si), part_files[si], [])
            tree.append(cur)
            continue
        f = sec_files[si]
        node = (ed.label(si), f, [(ed.label(si, sj), f"{f}#s{si}-{sj}", [])
                                  for sj in range(len(b["sections"][si].get("subsections", [])))])
        if ed.part_of[si] is not None and cur is not None:
            cur[2].append(node)
        else:
            cur = None
            tree.append(node)
    if ed.appendix:
        tree.append((s["appendix"], "appendix.xhtml", []))
    tree.append((s["index"], "index.xhtml", []))

    def nav_li(node):
        label, href, kids = node
        sub = ("<ol>" + "".join(nav_li(k) for k in kids) + "</ol>") if kids else ""
        return f'<li><a href="{href}">{esc(label)}</a>{sub}</li>'

    order = 0

    def ncx_point(node):
        nonlocal order
        order += 1
        label, href, kids = node
        me = (f'<navPoint id="np{order}" playOrder="{order}"><navLabel><text>{esc(label)}</text></navLabel>'
              f'<content src="{href}"/>')
        return me + "".join(ncx_point(k) for k in kids) + "</navPoint>"

    nav = [f'<nav epub:type="toc" id="toc"><h1>{esc(s["toc"])}</h1><ol>' + "".join(nav_li(n) for n in tree) + "</ol></nav>"]
    ncx_points = [ncx_point(n) for n in tree]
    nav.append(f'<nav epub:type="landmarks" hidden=""><ol><li><a epub:type="cover" href="cover.xhtml">{esc(s["cover"])}</a></li>'
               f'<li><a epub:type="toc" href="nav.xhtml">{esc(s["toc"])}</a></li>'
               f'<li><a epub:type="bodymatter" href="{sec_files[0]}">{esc(b["sections"][0]["title"])}</a></li>'
               f'<li><a epub:type="index" href="index.xhtml">{esc(s["index"])}</a></li></ol></nav>')
    files["nav.xhtml"] = xhtml(L, s["toc"], "".join(nav))
    book_id = "urn:uuid:" + str(uuid.uuid5(uuid.NAMESPACE_URL, f"{APP_URL}#{ed.lang}"))
    ncx = ('<?xml version="1.0" encoding="utf-8"?>\n<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1">'
           f'<head><meta name="dtb:uid" content="{book_id}"/><meta name="dtb:depth" content="3"/></head>'
           f'<docTitle><text>{esc(b["title"])}</text></docTitle><navMap>{"".join(ncx_points)}</navMap></ncx>')
    files["toc.ncx"] = ncx
    # fonts: subset to the characters of the book
    alltext = "".join(v for v in files.values() if isinstance(v, str)) + "0123456789–—…·→❦"
    alltext = html.unescape(re.sub(r"<[^>]+>", " ", alltext))
    fdir = work / "fonts"
    fdir.mkdir(parents=True, exist_ok=True)
    font_names = {}
    for k, p in fonts.items():
        dst = fdir / p.name
        subset_font(p, dst, alltext)
        font_names[k] = f"fonts/{p.name}"
        files[font_names[k]] = dst.read_bytes()
    files["style.css"] = font_face_css(font_names) + BASE_CSS + EPUB_CSS
    files["cover.jpg"] = (PUBLIC / "cover.jpg").read_bytes()
    used_imgs = set(re.findall(r'src="images/([^"]+)"', "".join(v for v in files.values() if isinstance(v, str))))
    for img in sorted(used_imgs):
        files[f"images/{img}"] = (PUBLIC / "images" / img).read_bytes()
    # manifest + spine
    mt = {".xhtml": "application/xhtml+xml", ".css": "text/css", ".jpg": "image/jpeg", ".png": "image/png",
          ".ttf": "font/ttf", ".ncx": "application/x-dtbncx+xml"}
    manifest = []
    for i, name in enumerate(sorted(files)):
        props = []
        if name == "nav.xhtml":
            props.append("nav")
        if name == "cover.jpg":
            props.append("cover-image")
        pid = {"cover.jpg": "cover-img", "toc.ncx": "ncx", "nav.xhtml": "nav"}.get(name, f"i{i}")
        pr = f' properties="{" ".join(props)}"' if props else ""
        manifest.append(f'<item id="{pid}" href="{esc(name)}" media-type="{mt[Path(name).suffix]}"{pr}/>')
    ids = {name: m.split('id="')[1].split('"')[0] for name, m in zip(sorted(files), manifest)}
    body = [part_files[i] if kind == "part" else sec_files[i] for kind, i in ed.layout]
    spine = (["cover.xhtml", "title.xhtml", "nav.xhtml"] + body
             + (["appendix.xhtml"] if ed.appendix else []) + ["index.xhtml"])
    spine_xml = "".join(f'<itemref idref="{ids[n]}"/>' for n in spine)
    now = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    opf = ('<?xml version="1.0" encoding="utf-8"?>\n'
           '<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="bookid" '
           f'xml:lang="{L}"><metadata xmlns:dc="http://purl.org/dc/elements/1.1/">'
           f'<dc:identifier id="bookid">{book_id}</dc:identifier>'
           f'<dc:title>{esc(ed.full_title())}</dc:title>'
           f'<dc:language>{L}</dc:language><dc:creator>Chaitanya Academy</dc:creator>'
           f'<dc:description>{esc(b.get("subtitle") or b["title"])}</dc:description><dc:date>{ed.version}</dc:date>'
           f'<meta property="dcterms:modified">{now}</meta><meta name="cover" content="cover-img"/></metadata>'
           f'<manifest>{"".join(manifest)}</manifest><spine toc="ncx">{spine_xml}</spine>'
           '<guide><reference type="cover" title="Cover" href="cover.xhtml"/>'
           '<reference type="toc" title="Contents" href="nav.xhtml"/></guide></package>')
    container = ('<?xml version="1.0" encoding="utf-8"?>\n<container version="1.0" '
                 'xmlns="urn:oasis:names:tc:opendocument:xmlns:container"><rootfiles>'
                 '<rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>'
                 '</rootfiles></container>')
    out_epub.parent.mkdir(parents=True, exist_ok=True)
    tmp = work / "book.epub"
    with zipfile.ZipFile(tmp, "w") as z:
        z.writestr(zipfile.ZipInfo("mimetype"), "application/epub+zip", compress_type=zipfile.ZIP_STORED)
        z.writestr("META-INF/container.xml", container, compress_type=zipfile.ZIP_DEFLATED)
        z.writestr("OEBPS/content.opf", opf, compress_type=zipfile.ZIP_DEFLATED)
        for name, data in sorted(files.items()):
            z.writestr(f"OEBPS/{name}", data, compress_type=zipfile.ZIP_DEFLATED)
    shutil.copy(tmp, out_epub)
    return tmp


# ---------------------------------------------------------------- app folder

def write_app_folder(out: Path):
    d = out / "1 Приложение"
    d.mkdir(parents=True, exist_ok=True)
    (d / "Ссылка на приложение.url").write_text(f"[InternetShortcut]\r\nURL={APP_URL}\r\n", encoding="utf-8")
    (d / "Прочти меня.txt").write_text(
        "Приложение «Арчана-паддхати» (вся книга на 10 языках, с поиском) открывается по ссылке "
        f"{APP_URL} — его можно установить на телефон или компьютер (кнопка «Установить» / «Добавить на главный экран»).\r\n",
        encoding="utf-8-sig")


# ---------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--lang", default="ru,en", help="comma-separated language codes (en = data/book.json)")
    ap.add_argument("--formats", default="print,epub", help="print (PDF) and/or epub - the only formats produced")
    ap.add_argument("--out", default=str(DEFAULT_OUT), help="output folder (default: %(default)s)")
    ap.add_argument("--work", default="", help="keep intermediate files here (default: temp dir)")
    args = ap.parse_args()
    langs = [l.strip() for l in args.lang.split(",") if l.strip()]
    formats = {f.strip() for f in args.formats.split(",") if f.strip()}
    out = Path(args.out)
    fonts = find_fonts()
    chrome = find_file(CHROME_CANDIDATES) if "print" in formats else None
    if "print" in formats and not chrome:
        sys.exit("Chrome/Edge not found (set CHROME_PATH)")
    unknown = formats - {"print", "epub"}
    if unknown:
        sys.exit(f"Unknown format(s) {sorted(unknown)}: only print (PDF) and epub are produced")
    work_root = Path(args.work) if args.work else Path(tempfile.mkdtemp(prefix="arcana-formats-"))
    write_app_folder(out)
    for lang in langs:
        ed = Edition(lang)
        work = work_root / lang
        work.mkdir(parents=True, exist_ok=True)
        name = ed.s["name"]
        if "print" in formats:
            pdf = out / "2 Для печати" / f'{name}{ed.s["print_suffix"]}.pdf'
            info = build_print(ed, fonts, chrome, work / "print", pdf)
            ap = f", appendix p. {info['toc_pages']['ap']} ({len(ed.appendix)} blocks)" if "ap" in info["toc_pages"] else ""
            print(f"[{lang}] PDF  {pdf}  ({info['pages']} pages{ap})")
        if "epub" in formats:
            epub = out / "3 EPUB" / f"{name}.epub"
            build_epub(ed, fonts, epub, work / "epub")
            print(f"[{lang}] EPUB {epub}")
    if not args.work:
        shutil.rmtree(work_root, ignore_errors=True)


if __name__ == "__main__":
    main()
