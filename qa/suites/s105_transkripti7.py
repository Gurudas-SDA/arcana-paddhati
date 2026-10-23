"""Satkirti msg 6417 (23.10.2026): «Убрать из книги, но сохрани у себя».
7 English lecture transcripts that no citation in data/book*.json points to (offline precache, 439 KB) leave the
book and are kept in the archive:
  a) these 7 files are not in public/transcripts/ and their ids are not in lib/transcripts.json;
  b) every remaining lib/transcripts.json entry exists as a file (and every file has an entry);
  c) the archive folder holds all 7 copies (checked only where the archive exists, i.e. on the server).
usage: python s105_transkripti7.py
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))
import qa  # noqa: E402

REPO = qa.REPO
GONE = {
    "19Mvvp80dlD44d6erl7MlL0HixM-_CSLp": "9906-en",
    "1I2fZQylHGSJmWlFQi8N2CzaXRNg6dcFR": "885-en",
    "1Igo0nPbdKJJjqhM4FRXD8P670v4kJSuH": "10192-en",
    "1JyWC3vBuBJrPBVrX3gMBkJVMBMg0GWtf": "9869-en",
    "1NLkR5jNzORd81hIVnWh_OT8-QJJNNcrb": "1941-en",
    "1_bHPh604BtUTXDR1hDyGAFDdx3h8Dnfp": "2640-en",
    "1doSjddDL03KpC2IZLD1GhNd_q4OI-NQF": "4380-en",
}
ARCHIVE = os.path.join(os.environ.get("QA_ARCHIVE_ROOT") or "/home/satkirti/03_Satkirti/Arcana-paddhati/archive",
                       "2026.10.23_Убранные из книги расшифровки лекций (7)")
TDIR = os.path.join(REPO, "public", "transcripts")
res = []


def chk(name, ok, ev=""):
    res.append(bool(ok))
    print(f"  [{'PASS' if ok else 'FAIL'}] data {name} {ev if not ok else ''}".rstrip(), flush=True)


with open(os.path.join(REPO, "lib", "transcripts.json"), encoding="utf8") as fh:
    idx = json.load(fh)
files = {f[:-5] for f in os.listdir(TDIR) if f.endswith(".html")}

still_files = sorted(n for n in GONE.values() if n in files)
chk("the 7 files are not in public/transcripts/", not still_files, still_files)
still_keys = sorted(k for k in GONE if k in idx)
chk("the 7 ids are not in lib/transcripts.json", not still_keys, still_keys)
missing = sorted(v for v in idx.values() if v not in files)
chk("every transcripts.json entry exists as a file", not missing, missing)
extra = sorted(files - set(idx.values()))
chk("every transcript file has a transcripts.json entry", not extra, extra)
if os.path.isdir(os.path.dirname(ARCHIVE)):
    absent = sorted(n for n in GONE.values() if not os.path.isfile(os.path.join(ARCHIVE, n + ".html")))
    chk("archive folder holds all 7 copies", not absent, absent)
else:
    print("  [SKIP] archive folder check: archive root absent (not the server)", flush=True)

sys.exit(0 if res and all(res) else 1)
