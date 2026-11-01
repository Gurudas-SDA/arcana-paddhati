# -*- coding: utf-8 -*-
"""A131 (Satkirti msg 7226, 01.11.2026): new subsection «Медитация на Шри Дамодару (дамодара-дхьяна)» in the chapter
«Картика» (kartika-bhajans), right after «Шри Дамодараштака». Idempotent. Adds it to kartika_bhajany.json (the source of
build.py) and to data/book.json (en), book.ru-iast.json, book.ru.json (Cyrillic mirror via iast_to_cyrillic.translit).
Other languages: not touched (night release translates; until then the English fallback).

Source: Satkirti's photo (verse + glosses), Gurudeva's explanation in CA lecture 5652 (22.11.2020); the text of the verse
lines 1-3 is not found in CA nor in Versebase — written by the photo and Sanskrit rules (see the A131 source note).
"""
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
CH = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(CH, "..", "..", ".."))
sys.path.insert(0, os.path.join(REPO, "scripts", "translate"))
from iast_to_cyrillic import translit  # noqa: E402
from build import wbw_cyr  # noqa: E402

SUB = "song-damodara-dhyana"
AFTER = "song-damodarastakam"

VERSE = ("aṅga-śyāmalima-chaṭābhir abhito mandī-kṛtendīvaraṁ\n"
         "jāḍyaṁ jāguḍa-rociṣāṁ vidadhataṁ paṭṭāmbarasya śriyā\n"
         "vṛndāraṇya-vilāsinaṁ hṛdi lasad-dāmābhir āmodaraṁ\n"
         "rādhā-skandha-niveśitojjvala-bhujaṁ dhyāyema dāmodaram")

RU = {
    "title": "Медитация на Шри Дамодару (дамодара-дхьяна)",
    "author": "Шрила Рупа Госвами, «Става-мала» (по словам Гурудева, лекция CA 5652, 22.11.2020)",
    "wbw": ("aṅga-śyāmalima-chaṭābhir — сиянием тёмного цвета Его тела; abhito — повсюду; "
            "mandī-kṛtendīvaraṁ — затмевающего голубые лотосы; jāḍyaṁ — тусклость; jāguḍa-rociṣāṁ — сияния кункумы; "
            "vidadhataṁ — наводящего; paṭṭāmbarasya śriyā — блеском шёлкового одеяния; "
            "vṛndāraṇya-vilāsinaṁ — наслаждающегося играми в лесу Вриндавана; hṛdi — на груди; "
            "lasad-dāmābhir — сверкающими гирляндами; āmodaraṁ — благоухающего; "
            "rādhā-skandha-niveśitojjvala-bhujaṁ — Чья сияющая рука покоится на плече Радхи; "
            "dhyāyema — будем медитировать; dāmodaram — на Дамодару"),
    "translation": ("Будем медитировать на Шри Дамодару. Сияние Его тёмного тела повсюду затмевает голубые лотосы, "
                    "блеск Его шёлкового одеяния затмевает сияние кункумы. Он наслаждается играми в лесу Вриндавана, "
                    "Его грудь благоухает сверкающими гирляндами, а Его сияющая рука покоится на плече Радхи."),
}
EN = {
    "title": "Meditation on Śrī Dāmodara (Dāmodara-dhyāna)",
    "author": "Śrīla Rūpa Gosvāmī, Stava-mālā (as told by Gurudeva, CA lecture 5652, 22.11.2020)",
    "wbw": ("aṅga-śyāmalima-chaṭābhir — by the luster of the dark color of His body; abhito — everywhere; "
            "mandī-kṛtendīvaraṁ — eclipsing the blue lotuses; jāḍyaṁ — dullness; jāguḍa-rociṣāṁ — of the glow of kuṅkuma; "
            "vidadhataṁ — bringing; paṭṭāmbarasya śriyā — by the splendor of His silk garment; "
            "vṛndāraṇya-vilāsinaṁ — enjoying pastimes in Vṛndāvana forest; hṛdi — on the chest; "
            "lasad-dāmābhir — with shining garlands; āmodaraṁ — fragrant; "
            "rādhā-skandha-niveśitojjvala-bhujaṁ — whose splendid arm rests on Rādhā's shoulder; "
            "dhyāyema — let us meditate; dāmodaram — on Dāmodara"),
    "translation": ("Let us meditate on Śrī Dāmodara. The luster of His dark body eclipses the blue lotuses everywhere, "
                    "the splendor of His silk garment dims the glow of kuṅkuma. He enjoys pastimes in Vṛndāvana forest, "
                    "His chest is fragrant with shining garlands, and His splendid arm rests on Rādhā's shoulder."),
}


def make(t, cyr=False):
    tr = translit if cyr else (lambda x: x)
    return {
        "id": SUB,
        "title": t["title"],
        "content": [
            {"type": "text", "content": t["author"]},
            {"type": "verse", "sanskrit": tr(VERSE), "wbw": wbw_cyr(t["wbw"]) if cyr else t["wbw"],
             "translation": t["translation"]},
        ],
    }


def put_into(sec):
    subs = sec["subsections"]
    subs[:] = [s for s in subs if s["id"] != SUB]
    at = [s["id"] for s in subs].index(AFTER) + 1
    subs.insert(at, None)
    return subs, at


def write_json(path, obj, nl_end):
    open(path, "w", encoding="utf-8", newline="").write(json.dumps(obj, ensure_ascii=False, indent=2) + ("\n" if nl_end else ""))


def main():
    p = os.path.join(CH, "kartika_bhajany.json")
    raw = open(p, encoding="utf-8", newline="").read()
    d = json.loads(raw)
    for key, t in (("en", EN), ("ru-iast", RU)):
        subs, at = put_into(d[key])
        subs[at] = make(t)
    write_json(p, d, raw.endswith("\n"))
    for fn, t, cyr in (("book.json", EN, False), ("book.ru-iast.json", RU, False), ("book.ru.json", RU, True)):
        path = os.path.join(REPO, "data", fn)
        raw = open(path, encoding="utf-8", newline="").read()
        book = json.loads(raw)
        sec = next(s for s in book["sections"] if s["id"] == "kartika-bhajans")
        subs, at = put_into(sec)
        subs[at] = make(t, cyr)
        write_json(path, book, raw.endswith("\n"))
        print("wrote", fn)


if __name__ == "__main__":
    main()
