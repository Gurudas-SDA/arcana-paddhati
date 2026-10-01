"""Post-assembly fixes for data/book.<lang>.json (run after `tr.py assemble`).
Usage: python postfix.py [lang ...]   (default: all)

- LV terms chosen by Rājan 2026-09-30: "offering" = piedāvājums, "Their Lordships" = Viņu Augstības.
  Only noun forms are replaced; the verb "veltīt" also means "dedicate" in the text, so it is kept.
- HU: two English plurals on Sanskrit words in labels (HU_FIELDS).
- The "[name of your spiritual master]" placeholder inside an IAST mantra is localized.
- RU: one source verse contains English notes "(for one leaf)", which the transliterator garbled.
"""
import json
import pathlib
import re
import sys

DATA = pathlib.Path(__file__).resolve().parents[2] / "data"

LV_SUBS = [
    (r"\b([Vv])eltījum", lambda m: ("P" if m.group(1) == "V" else "p") + "iedāvājum"),
    (r"\b([Vv])eltīšan", lambda m: ("P" if m.group(1) == "V" else "p") + "iedāvāšan"),
    (r"\bViņu Dievišķīb", lambda m: "Viņu Augstīb"),
]

PLACEHOLDER = {
    "de": "[Name deines spirituellen Meisters]",
    "es": "[nombre de tu maestro espiritual]",
    "fr": "[nom de ton maître spirituel]",
    "it": "[nome del tuo maestro spirituale]",
    "uk": "[ім'я твого духовного вчителя]",
    "hu": "[lelki tanítómestered neve]",
}

# HU: whole-field fixes of English plurals left on Sanskrit words (exact field match only).
HU_FIELDS = {
    "Śālagrāma Śilās": "Śālagrāma-śilák",
    "aparādha-kṣamāpana-mantras": "aparādha-kṣamāpana-mantrák",
}

RU_LEAF = [
    ("(fор оне леаf)", "(за один лист)"),
    ("(fор северал\nлеавес)", "(за несколько\nлистьев)"),
    (") ор ета̄ни", ") или ета̄ни"),
]


def walk(node, fn):
    if isinstance(node, dict):
        return {k: (v if k in ("id", "type", "src", "layout", "page") else walk(v, fn)) for k, v in node.items()}
    if isinstance(node, list):
        return [walk(x, fn) for x in node]
    if isinstance(node, str):
        return fn(node)
    return node


def fix_lv(s):
    for pat, rep in LV_SUBS:
        s = re.sub(pat, rep, s)
    return s


def main():
    for lang in (sys.argv[1:] or ["lv", "de", "es", "fr", "it", "uk", "ru", "hu"]):
        path = DATA / f"book.{lang}.json"
        book = json.loads(path.read_text(encoding="utf-8"))
        fns = []
        if lang == "lv":
            fns.append(fix_lv)
        if lang in PLACEHOLDER:
            fns.append(lambda s, r=PLACEHOLDER[lang]: s.replace("[name of your spiritual master]", r))
        if lang == "hu":
            fns.append(lambda s: HU_FIELDS.get(s, s))
        if lang == "ru":
            def fix_ru(s):
                for a, b in RU_LEAF:
                    s = s.replace(a, b)
                return s
            fns.append(fix_ru)
        before = json.dumps(book, ensure_ascii=False)
        for fn in fns:
            book = walk(book, fn)
        after = json.dumps(book, ensure_ascii=False, indent=2)
        path.write_text(after + "\n", encoding="utf-8")
        print(f"[{lang}] changed: {before != json.dumps(book, ensure_ascii=False)}")


if __name__ == "__main__":
    main()
