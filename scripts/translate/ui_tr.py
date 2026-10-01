"""Translate data/ui.en.json -> data/ui.<lang>.json via AnyModel (one key, sequential).

Usage (from this folder):  python ui_tr.py [lang ...]   (default: all LANGS)
ru-iast gets a copy of ru (UI texts are identical; only verse script differs).
"""
import json
import os
import re
import shutil
import sys

import tr

DATA = os.path.join(tr.PROJ, "data")
LANGS = ["ru", "lv", "de", "fr", "es", "it", "uk", "hu"]
NAMES = {"ru": "Russian", "lv": "Latvian", "de": "German", "fr": "French",
         "es": "Spanish", "it": "Italian", "uk": "Ukrainian", "hu": "Hungarian"}
PH = re.compile(r"\{[a-zA-Z]+\}")


def prompt(lang):
    return (
        f"Translate the UI strings of a website (a Vaishnava Deity-worship temple manual) "
        f"from English into {NAMES[lang]}. Return a JSON object with exactly the same keys. "
        "Rules: keep every {placeholder} exactly as is; keep the product name 'Arcana Paddhati' "
        "unchanged; keep the brand name 'Chrome'; use the standard labels that iOS/Android show "
        f"in {NAMES[lang]} for 'Share', 'Add to Home Screen', 'Add', 'Open in Browser'; keep "
        "quotation marks where the English has them; short, natural UI wording. "
        "Key 'language.fallbackSuffix' stays '(EN)'."
    )


def main():
    src = json.load(open(os.path.join(DATA, "ui.en.json"), encoding="utf-8"))
    try:
        for lang in (sys.argv[1:] or LANGS):
            text, fin, _, secs = tr.call([
                {"role": "system", "content": prompt(lang)},
                {"role": "user", "content": json.dumps(src, ensure_ascii=False, indent=1)},
            ], max_tokens=8000)
            out = json.loads(text[text.find("{"):text.rfind("}") + 1])
            bad = [k for k in src if k not in out or sorted(PH.findall(src[k])) != sorted(PH.findall(out[k]))]
            extra = [k for k in out if k not in src]
            if bad or extra:
                tr.log(f"UI {lang}: FAIL keys/placeholders bad={bad} extra={extra}")
                continue
            path = os.path.join(DATA, f"ui.{lang}.json")
            with open(path, "w", encoding="utf-8") as f:
                json.dump({k: out[k] for k in src}, f, ensure_ascii=False, indent=2)
                f.write("\n")
            tr.log(f"UI {lang}: OK {secs:.0f}s fin={fin}")
        if "ru" in (sys.argv[1:] or LANGS) and os.path.exists(os.path.join(DATA, "ui.ru.json")):
            shutil.copyfile(os.path.join(DATA, "ui.ru.json"), os.path.join(DATA, "ui.ru-iast.json"))
            tr.log("UI ru-iast: copied from ru")
    finally:
        if tr._key_index is not None:
            tr.release_key()


if __name__ == "__main__":
    main()
