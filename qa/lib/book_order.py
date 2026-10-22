"""The book's order from data/book.<lang>.json — a port of lib/book.ts tocLayout / readingOrder (V45).

layout(lang): every item of «Содержание» / «Лента» in order — sections and the parts' headings (ids).
pages(lang):  the pages «‹ Назад» / «Вперёд ›» step through — V45 (Vraja Lila msg 6178 / 1412, 22.10.2026):
              the sections only (no part headings), without a section that has no text of its own.
groups(lang): the section rows of «Содержание»: [(id, title, chapter ids)] — the Introduction, then each part.
"""
import json
import os

import qa


def book(lang):
    name = "book.json" if lang == "en" else f"book.{lang}.json"   # English = data/book.json
    return json.load(open(os.path.join(qa.DATA, name), encoding="utf-8"))


def _en():
    return book("en")


def layout(lang="ru-iast"):
    en = _en()
    ids = [s["id"] for s in en["sections"]]
    parts = en.get("parts") or []
    part_of = {sid: i for i, p in enumerate(parts) for sid in p["sections"]}
    out, emitted = [], 0
    for sid in ids:
        p = part_of.get(sid)
        if p is not None:
            while emitted <= p:
                out.append(("part", parts[emitted]["id"])); emitted += 1
        elif emitted > 0:
            while emitted < len(parts) and not parts[emitted]["sections"]:
                out.append(("part", parts[emitted]["id"])); emitted += 1
        out.append(("section", sid))
    while emitted < len(parts):
        out.append(("part", parts[emitted]["id"])); emitted += 1
    return out


def no_text(lang="ru-iast"):
    b = book(lang)
    return {s["id"] for s in b["sections"] if not s.get("content") and not s.get("subsections")}


def pages(lang="ru-iast"):
    skip = no_text(lang)
    return [i for k, i in layout(lang) if k == "section" and i not in skip]


def neighbours(lang, sid):
    """(prev, next) of a page; prev None = the cover; next None = none."""
    order = pages(lang)
    if sid is None:
        return None, order[0]
    if sid in order:
        i = order.index(sid)
        return (order[i - 1] if i else None), (order[i + 1] if i + 1 < len(order) else None)
    ids = [i for _, i in layout(lang)]
    at = ids.index(sid)
    before = [x for x in ids[:at] if x in order]
    after = [x for x in ids[at + 1:] if x in order]
    return (before[-1] if before else None), (after[0] if after else None)


def groups(lang="ru-iast"):
    b = book(lang)
    secs = {s["id"]: s for s in b["sections"]}
    parts = b.get("parts") or []
    in_part = {i for p in parts for i in p["sections"]}
    front = []
    for s in b["sections"]:
        if s["id"] in in_part:
            break
        front.append(s["id"])
    out = []
    if "introduction" in front:
        out.append(("introduction", secs["introduction"]["title"], front[front.index("introduction") + 1:]))
    out += [(p["id"], p["title"], list(p["sections"])) for p in parts]
    return out


def title(lang, sid):
    for s in book(lang)["sections"]:
        if s["id"] == sid:
            return s["title"]
    for p in book(lang).get("parts") or []:
        if p["id"] == sid:
            return p["title"]
    return sid
