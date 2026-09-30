# -*- coding: utf-8 -*-
"""IAST -> Ukrainian vedabase.io/uk diacritic Cyrillic scheme (derived from BG 2.7, 4.34, 9.26 pages)."""
import unicodedata
MAC, DOT, ACU, DOTA, TIL = "\u0304", "\u0323", "\u0301", "\u0307", "\u0303"
T = {"kh": "кх", "gh": "ґг", "ch": "чх", "jh": "джх", "ṭh": "т"+DOT+"х", "ḍh": "д"+DOT+"г",
     "th": "тх", "dh": "дг", "ph": "пх", "bh": "бг", "ai": "аі", "au": "ау",
     "a": "а", "ā": "а"+MAC, "i": "і", "ī": "\u0131"+MAC, "u": "у", "ū": "у"+MAC,
     "ṛ": "р"+DOT, "ṝ": "р"+DOT+MAC, "ḷ": "л"+DOT, "e": "е", "o": "о",
     "ṁ": "м"+DOTA, "ṃ": "м"+DOTA, "ḥ": "х"+DOT,
     "k": "к", "g": "ґ", "ṅ": "н"+DOTA, "c": "ч", "j": "дж", "ñ": "н"+TIL,
     "ṭ": "т"+DOT, "ḍ": "д"+DOT, "ṇ": "н"+DOT, "t": "т", "d": "д", "n": "н",
     "p": "п", "b": "б", "m": "м", "y": "й", "r": "р", "l": "л", "v": "в", "w": "в",
     "ś": "ш"+ACU, "ṣ": "ш", "s": "с", "h": "х"}
def translit_uk(s):
    s = unicodedata.normalize("NFC", s); low = s.lower(); out = []; i = 0
    while i < len(s):
        for L in (2, 1):
            k = low[i:i+L]
            if len(k) == L and k in T:
                r = T[k]
                if s[i] != low[i]:
                    r = r[:1].upper() + r[1:]
                out.append(r); i += L; break
        else:
            out.append(s[i]); i += 1
    return unicodedata.normalize("NFC", "".join(out))
if __name__ == "__main__":
    import sys; sys.stdout.reconfigure(encoding="utf-8")
    for w in ["Bhagavad-gītā", "Kṛṣṇa", "brāhmaṇa", "Bṛhad-āraṇyaka", "praṇipātena", "jñānaṁ", "tattva-darśinaḥ", "upadekṣyanti", "sevayā"]:
        print(w, translit_uk(w))
