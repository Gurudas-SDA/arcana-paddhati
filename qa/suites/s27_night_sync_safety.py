"""Reader v7.8.3 (Codex review of e8d33aa..bb066eb) — night sync never loses a translation, never half-writes a file.
  1  i18n_sections.put: no i18n.json record for a section the book already has → the localized section is KEPT
     (status «missing …», a MISSING warning), never deleted (the app would fall back to English); a book without
     the section stays without it (English fallback); a record present → the section is put in its place
  2  apply_sections: the same through the CLI path (the book file on disk keeps the section; mood blocks kept)
  3  write_atomic: temp file + os.replace — a failing write leaves the old file whole and no temp file behind;
     i18n_sections.apply_sections and night_sync.save / run_moods write through it (no plain open(…, "w"))
 v7.8.4 (Codex review): a locked target (PermissionError on os.replace, Windows / OneDrive) is retried with a short
     backoff; still locked → AtomicWriteError with a clear message, the old file whole, no temp file left
No browser, no server: python s27_night_sync_safety.py"""
import contextlib
import io
import json
import os
import re
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(HERE, "..", ".."))
TR = os.path.join(REPO, "scripts", "translate")
sys.path.insert(0, TR)
import i18n_sections as I  # noqa: E402

res = []


def chk(name, ok, info=""):
    res.append(bool(ok))
    print(f"  [{'PASS' if ok else 'FAIL'}] data {name} {'' if ok else info}", flush=True)


def sec(sid, title, sub=None):
    s = {"id": sid, "title": title, "content": [{"type": "text", "content": title + " text"}]}
    if sub:
        s["subsections"] = [{"id": sub, "title": title + " sub", "content": [{"type": "text", "content": "x"}]}]
    return s


tmp = tempfile.mkdtemp(prefix="qa-s27-")
try:
    en = {"sections": [sec("a", "A"), sec("b", "B"), sec("c", "C")]}
    en_ids = [s["id"] for s in en["sections"]]
    gen = os.path.join(tmp, "gen")
    os.makedirs(gen)

    # ---------- 1: put() without a record keeps the localized section ----------
    book = {"sections": [sec("a", "A-lv"), sec("b", "B-lv"), sec("c", "C-lv")]}
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        st = I.put(book, "lv", "b", gen, en["sections"][1], en_ids)   # no i18n.json at all
    ids = [s["id"] for s in book["sections"]]
    chk("1 no i18n.json record → existing localized section kept (not deleted), reported MISSING",
        ids == ["a", "b", "c"] and book["sections"][1]["title"] == "B-lv" and st.startswith("missing")
        and "MISSING lv/b" in out.getvalue(), (ids, st, out.getvalue()[:120]))
    json.dump({"b": {"de": {"en_hash": "x", "model": "m", "date": "d", "section": sec("b", "B-de")}}},
              open(os.path.join(gen, "i18n.json"), "w", encoding="utf-8"))
    with contextlib.redirect_stdout(io.StringIO()):
        st = I.put(book, "lv", "b", gen, en["sections"][1], en_ids)   # record only for another language
    chk("1 record for another language only → lv section still kept",
        [s["id"] for s in book["sections"]] == ["a", "b", "c"] and st.startswith("missing"), st)
    book2 = {"sections": [sec("a", "A-lv"), sec("c", "C-lv")]}
    with contextlib.redirect_stdout(io.StringIO()):
        st = I.put(book2, "lv", "b", gen, en["sections"][1], en_ids)
    chk("1 book without the section and no record → stays without it (English fallback)",
        [s["id"] for s in book2["sections"]] == ["a", "c"] and st.startswith("none"), st)
    with contextlib.redirect_stdout(io.StringIO()):
        st = I.put(book2, "de", "b", gen, en["sections"][1], en_ids)
    chk("1 record present → the translated section put in the English order",
        [s["id"] for s in book2["sections"]] == ["a", "b", "c"] and book2["sections"][1]["title"] == "B-de", st)

    # ---------- 2: apply_sections (CLI path) on files ----------
    data = os.path.join(tmp, "data")
    os.makedirs(data)
    json.dump(en, open(os.path.join(data, "book.json"), "w", encoding="utf-8"))
    for lang in I.OTHER:
        b = {"sections": [sec("a", "A-" + lang), sec("b", "B-" + lang, sub="b1"), sec("c", "C-" + lang)]}
        b["sections"][1]["subsections"][0]["content"].insert(0, {"type": "mood", "quote": "q"})
        open(os.path.join(data, f"book.{lang}.json"), "w", encoding="utf-8", newline="").write(
            json.dumps(b, ensure_ascii=False, indent=2) + "\n")
    os.remove(os.path.join(gen, "i18n.json"))
    with contextlib.redirect_stdout(io.StringIO()):
        rep = I.apply_sections(["b"], {"b": gen}, data)
    bad = []
    for lang in I.OTHER:
        p = os.path.join(data, f"book.{lang}.json")
        raw = open(p, encoding="utf-8", newline="").read()
        b = json.loads(raw)
        s = next((x for x in b["sections"] if x["id"] == "b"), None)
        if not s or s["title"] != "B-" + lang or not raw.endswith("\n") or rep[lang]["b"][:7] != "missing":
            bad.append(lang)
        elif s["subsections"][0]["content"][0].get("type") != "mood":
            bad.append(lang + " mood")
    chk("2 apply_sections without records: every book file keeps its localized section (+ its mood blocks)", not bad, bad)

    # ---------- 3: atomic writes ----------
    p = os.path.join(tmp, "f.json")
    open(p, "w", encoding="utf-8").write('{"old": 1}\n')

    err = None
    try:
        I.write_atomic(p, None)   # f.write(None) raises after the temp file was opened
    except Exception as e:  # noqa: BLE001
        err = e
    left = [f for f in os.listdir(tmp) if f.startswith(".tmp-")]
    chk("3 write_atomic: a failing write leaves the old file whole and no temp file",
        err is not None and open(p, encoding="utf-8").read() == '{"old": 1}\n' and not left, (err, left))
    I.write_atomic(p, '{"new": 2}\n', newline="\n")
    chk("3 write_atomic: a good write replaces the file", open(p, encoding="utf-8", newline="").read() == '{"new": 2}\n')
    # v7.8.4: os.replace locked (PermissionError) twice → retried and saved; always locked → a clear error
    real_replace, real_sleep = I.os.replace, I.time.sleep
    calls = {"n": 0}

    def locked(times):
        def rep(a, b):
            calls["n"] += 1
            if calls["n"] <= times:
                raise PermissionError(13, "Access is denied (qa: simulated OneDrive lock)", b)
            return real_replace(a, b)
        return rep

    try:
        I.time.sleep = lambda s: None
        I.os.replace = locked(2)
        I.write_atomic(p, '{"retry": 3}\n', newline="\n")
        ok1 = calls["n"] == 3 and open(p, encoding="utf-8").read() == '{"retry": 3}\n'
        calls["n"] = 0
        I.os.replace = locked(10 ** 6)
        err = None
        try:
            I.write_atomic(p, '{"lost": 4}\n', newline="\n")
        except Exception as e:  # noqa: BLE001
            err = e
    finally:
        I.os.replace, I.time.sleep = real_replace, real_sleep
    left = [f for f in os.listdir(tmp) if f.startswith(".tmp-")]
    chk("3 write_atomic: a locked file (PermissionError on os.replace) is retried and then saved", ok1, calls)
    chk("3 write_atomic: still locked after the retries → AtomicWriteError naming the file, old file whole, no temp",
        isinstance(err, I.AtomicWriteError) and isinstance(err, OSError) and "could not replace" in str(err)
        and calls["n"] == I.REPLACE_TRIES and open(p, encoding="utf-8").read() == '{"retry": 3}\n' and not left,
        (repr(err)[:200], calls, left))
    plain = re.compile(r"(?<![\w.])open\([^)]*[\"']w[\"']")   # builtin open(..., 'w'), not os.fdopen
    srcs = {}
    for f in ("i18n_sections.py", "night_sync.py"):
        t = open(os.path.join(TR, f), encoding="utf-8").read()
        srcs[f] = [ln.strip() for ln in t.splitlines() if plain.search(ln) and "night_sync.log" not in ln and "LOG" not in ln]
    ns = open(os.path.join(TR, "night_sync.py"), encoding="utf-8").read()
    chk("3 i18n_sections / night_sync write book, i18n.json and moods.json only through write_atomic",
        not any(srcs.values()) and ns.count("write_atomic(") >= 2, srcs)

    # ---------- 4 (live verifier 08.10): formats version = build date; «Arghya-pātra» spelled with gh ----------
    import datetime
    import glob
    import importlib.util
    spec = importlib.util.spec_from_file_location("build_formats", os.path.join(REPO, "scripts", "formats", "build_formats.py"))
    bf = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(bf)
    chk("4 PDF / EPUB «Версия от» = the build date (not the last data commit)",
        bf.content_version() == datetime.date.today().isoformat(), bf.content_version())
    argya = [os.path.basename(f) for f in glob.glob(os.path.join(REPO, "data", "book*.json"))
             if re.search(r"⟦[Aa]rgya-", open(f, encoding="utf-8").read())]
    chk("4 «Arghya-pātra» (never «Argya-pātra») in every book", not argya, argya)
    # v7.8.4 (live verifier 08.10): ch3 unnumbered row — DE / FR «Padya-pātra», ES «padya-pātra» lacked the long ā
    padya = [os.path.basename(f) for f in glob.glob(os.path.join(REPO, "data", "book*.json"))
             if re.search(r"⟦[Pp]adya-", open(f, encoding="utf-8").read())]
    chk("4 «Pādya-pātra» (never «Padya-pātra») in every book", not padya, padya)
finally:
    shutil.rmtree(tmp, ignore_errors=True)

print(f"s27: {sum(res)}/{len(res)} passed", flush=True)
sys.exit(0 if res and all(res) else 1)
