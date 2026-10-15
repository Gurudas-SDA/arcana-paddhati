# -*- coding: utf-8 -*-
"""Readable Markdown of the chapter from data/book.ru-iast.json (for reviewers and the PDF preview).
    python to_md.py <out.md>"""
import json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
BOOK = os.path.join(HERE, "..", "..", "..", "data", "book.ru-iast.json")
SID = "mangala-arati-procedure"


def inl(s):
    return re.sub(r"⟦([^⟦⟧]*)⟧", r"*\1*", s)


def blocks(bs, out):
    for b in bs:
        t = b["type"]
        if t == "mood":
            out.append("> **Настроение Гурудева.** " + b["translation"].replace("\n", " "))
            s = b["source"]
            out.append(f"> — Шри Према Прайоджана Прабху, «{s['title']}», {s['date']}, № {s['nr']}, {s['timecode']}")
            for m in b.get("more", []):
                out.append("> ")
                out.append("> " + m["translation"].replace("\n", " "))
                ms = m["source"]
                out.append(f"> — «{ms['title']}», {ms['date']}, № {ms['nr']}, {ms['timecode']}")
            out.append("")
        elif t == "text":
            out += [inl(b["content"]), ""]
        elif t == "instruction":
            out += ["- " + inl(b["content"]), ""]
        elif t == "subtitle":
            out += ["#### " + inl(b["content"]), ""]
        elif t == "bullet-list":
            out += ["- " + inl(x) for x in b["content"].split("\n")] + [""]
        elif t == "verse":
            out += ["    " + line for line in b["sanskrit"].split("\n")]
            out.append("")
            if b.get("translation"):
                out += ["«" + b["translation"] + "»", ""]
            if b.get("wbw"):
                out += ["Пословно: " + b["wbw"], ""]
        elif t == "paired-list":
            nums = b.get("numbers") or [""] * len(b["items"])
            out += ["| № | | |", "|---|---|---|"]
            for n, it in zip(nums, b["items"]):
                out.append(f"| {n} | {inl(it['label'])} | {inl(it['value'])} |")
            out.append("")
            w = [it for it in b["items"] if it.get("wbw")]
            if w:
                out += ["Пословно: " + " · ".join(it["wbw"] for it in w), ""]


def main(path):
    sec = next(s for s in json.load(open(BOOK, encoding="utf-8"))["sections"] if s["id"] == SID)
    out = [f"# {sec['title']}", "", f"*{sec['subtitle']}*", ""]
    blocks(sec["content"], out)
    for i, sub in enumerate(sec["subsections"], 1):
        out += [f"## {i}. {sub['title']}", ""]
        blocks(sub["content"], out)
    open(path, "w", encoding="utf-8").write("\n".join(out) + "\n")
    print("wrote", path)


if __name__ == "__main__":
    main(sys.argv[1])
