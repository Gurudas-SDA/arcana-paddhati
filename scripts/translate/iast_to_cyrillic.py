# -*- coding: utf-8 -*-
"""Deterministic IAST -> academic Cyrillic transliterator (Russian Gaudiya style).

Usage: python iast_to_cyrillic.py "text"   or   echo text | python iast_to_cyrillic.py
"""
import sys
import unicodedata

MAC = "\u0304"   # combining macron
DOT = "\u0323"   # combining dot below
ACU = "\u0301"   # combining acute
DOTA = "\u0307"  # combining dot above
TIL = "\u0303"   # combining tilde

# Longest keys first is enforced in translit(); all keys are lowercase NFC.
TABLE = {
    # aspirated / digraph consonants
    "kh": "кх", "gh": "гх", "ch": "чх", "jh": "джх",
    "ṭh": "т" + DOT + "х", "ḍh": "д" + DOT + "х",
    "th": "тх", "dh": "дх", "ph": "пх", "bh": "бх",
    # diphthongs
    "ai": "аи", "au": "ау",
    # vowels
    "a": "а", "ā": "а" + MAC, "i": "и", "ī": "ӣ", "u": "у", "ū": "ӯ",
    "ṛ": "р" + DOT, "ṝ": "р" + DOT + MAC, "ḷ": "л" + DOT, "ḹ": "л" + DOT + MAC,
    "e": "е", "o": "о",
    # anusvara / visarga
    "ṁ": "м" + DOTA, "ṃ": "м" + DOTA, "ḥ": "х" + DOT,
    # consonants
    "k": "к", "g": "г", "ṅ": "н" + DOTA,
    "c": "ч", "j": "дж", "ñ": "н" + TIL,
    "ṭ": "т" + DOT, "ḍ": "д" + DOT, "ṇ": "н" + DOT,
    "t": "т", "d": "д", "n": "н",
    "p": "п", "b": "б", "m": "м",
    "y": "й", "r": "р", "l": "л", "v": "в", "w": "в",
    "ś": "ш" + ACU, "ṣ": "ш" + DOT, "s": "с", "h": "х",
}
_MAXLEN = max(len(k) for k in TABLE)


def _cap(s):
    return s[:1].upper() + s[1:]


def translit(s: str) -> str:
    s = unicodedata.normalize("NFC", s)
    low = s.lower()
    out = []
    i = 0
    n = len(s)
    while i < n:
        for L in range(_MAXLEN, 0, -1):
            key = low[i:i + L]
            if len(key) == L and key in TABLE:
                rep = TABLE[key]
                if s[i] != low[i]:  # source char uppercase
                    # whole token uppercase (e.g. "KH") -> full upper, else first letter only
                    rep = rep.upper() if s[i:i + L].isupper() and L > 1 else _cap(rep)
                out.append(rep)
                i += L
                break
        else:
            out.append(s[i])  # punctuation, digits, spaces, newlines, hyphens, apostrophes
            i += 1
    return unicodedata.normalize("NFC", "".join(out))


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    text = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else sys.stdin.read()
    sys.stdout.write(translit(text) + ("\n" if len(sys.argv) > 1 else ""))
