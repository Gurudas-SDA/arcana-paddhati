"""Which QA a push needs — from the diff against the base (Padomnieks 2026.10.23_1609, S msg 946 + Gurudas msg 952).

  «S teksta izmaiņas DIENĀ: būve + satura linteris (visa grāmata) + Playwright testi TIKAI mainītajām
   nodaļām/sadaļām (tālrunis, iPad, dators). Pilnā regresija dienā — nē. … Interfeisa (V) izmaiņas — vienmēr pilnā.»

classify(repo, base) -> dict:
  mode      "nodalas"  only book TEXT changed and every change maps to a section page that exists in
                       both versions → the day gate: lint (whole book) + s200 (changed sections × iPhone 14,
                       iPad, desktop) + the changed/added suites + the data-only rule suites;
            "full"     anything else (interface, build, harness, structure of the book, unknown file) →
                       the unchanged gate (pre-push: build + lint + run_all --fast; Actions full after push).
  reason    one line why
  sections  ["ru-iast:conclusion", "en:introduction", …]   (lang:id, en = data/book.json)
  suites    suite ids whose file changed or was added (run as in the fast gate)
  files     changed files
When in doubt → "full" (the safe side). The decision is printed by `python qa/lib/changed.py [BASE]`.
"""
import fnmatch
import json
import os
import re
import subprocess
import sys

# Files that are book TEXT (or its sources / its tests) — never the app's interface or build.
CONTENT = [
    "data/book.json", "data/book.*.json",
    "scripts/chapters/*", "scripts/moods/*", "scripts/parampara/*", "scripts/translate/*",
    "scripts/formats/*",                     # PDF / EPUB generator — not part of the app build
    "lib/transcripts.json", "public/transcripts/*",
    "qa/suites/*", "qa/evidence/*", "qa/snapshots/*", "qa/lint_content.py", "qa/likumi.json",
    "qa/known_failures.json", "qa/lint_config.json", "qa/tulkojumi_gaida.json",
    "*.md", "*/desktop.ini", "desktop.ini", "*/__pycache__/*", "*.pyc",
]
# qa/run_all.py counts as content only when nothing but its SUITES list changed (a suite registered).
RUN_ALL = "qa/run_all.py"
TRANSCRIPT_FILES = ("lib/transcripts.json", "public/transcripts/")


def git(repo, *args, check=True):
    r = subprocess.run(["git", "-c", "core.quotePath=false", "-C", repo, *args], capture_output=True, timeout=120)
    if check and r.returncode != 0:
        raise RuntimeError("git %s: %s" % (" ".join(args), r.stderr.decode("utf-8", "replace").strip()[:300]))
    return r.stdout.decode("utf-8", "replace")


def show(repo, rev, path):
    """File content at rev ('' = working tree); None if it does not exist there."""
    if rev == "":
        p = os.path.join(repo, path)
        return open(p, encoding="utf-8").read() if os.path.exists(p) else None
    r = subprocess.run(["git", "-C", repo, "show", "%s:%s" % (rev, path)], capture_output=True, timeout=120)
    return r.stdout.decode("utf-8") if r.returncode == 0 else None


def is_content(path):
    return any(fnmatch.fnmatchcase(path, pat) for pat in CONTENT)


def _suites_block(text):
    """(text without the SUITES = [...] list, the list text)."""
    m = re.search(r"^SUITES = \[\n", text, re.M)
    if not m:
        return text, ""
    end = text.find("\n]\n", m.end())
    if end < 0:
        return text, ""
    return text[:m.start()] + text[end + 3:], text[m.start():end + 3]


def suite_ids(block):
    return dict(re.findall(r'dict\(id="([^"]+)",\s*file="([^"]+)"', block))


def active_langs(repo, rev):
    """Languages the app builds (lib/languages.json without replacedBy); None = unknown."""
    txt = show(repo, rev, "lib/languages.json")
    if not txt:
        return None
    return [l["code"] for l in json.loads(txt) if not l.get("replacedBy")]


def book_path(lang):
    return "data/book.json" if lang == "en" else "data/book.%s.json" % lang


def lang_of(path):
    m = re.fullmatch(r"data/book(?:\.([a-z-]+))?\.json", path)
    return (m.group(1) or "en") if m else None


def section_diff(old, new):
    """(changed section ids, structure problem or None) between two versions of one book file."""
    o, n = json.loads(old), json.loads(new)
    for k in sorted(set(o) | set(n)):
        if k != "sections" and o.get(k) != n.get(k):
            return [], "grāmatas virsdaļa «%s» mainīta (vāks / daļas / satura rādītājs)" % k
    oi = [s["id"] for s in o.get("sections", [])]
    ni = [s["id"] for s in n.get("sections", [])]
    if oi != ni:
        return [], "sadaļu saraksts mainīts (pievienota / izņemta / pārvietota sadaļa: %s)" % (
            ", ".join(sorted(set(oi) ^ set(ni))) or "secība")
    os_ = {s["id"]: s for s in o["sections"]}
    return [s["id"] for s in n["sections"] if s != os_[s["id"]]], None


def classify(repo, base="origin/main", head="HEAD"):
    """head '' = the working tree (uncommitted changes count)."""
    mb = git(repo, "merge-base", base, head or "HEAD").strip()
    rng = [mb, head] if head else [mb]
    files = [f for f in git(repo, "diff", "--name-only", "--no-renames", *rng).splitlines() if f]
    out = dict(mode="full", reason="", sections=[], suites=[], files=files, base=mb[:10])
    if not files:
        out["reason"] = "nav izmaiņu pret %s — drošā puse: parastie vārti" % base
        return out
    other = [f for f in files if not is_content(f) and f != RUN_ALL]
    if other:
        out["reason"] = "interfeisa / būves faili mainīti: %s%s" % (", ".join(other[:6]), " …" if len(other) > 6 else "")
        return out
    suites = set()
    if RUN_ALL in files:
        a, b = show(repo, mb, RUN_ALL), show(repo, head, RUN_ALL)
        if a is None or b is None:
            out["reason"] = "qa/run_all.py pievienots / izņemts"
            return out
        (ra, la), (rb, lb) = _suites_block(a), _suites_block(b)
        if not la or not lb or ra != rb:
            out["reason"] = "qa/run_all.py mainīts ārpus SUITES saraksta (testu sistēma)"
            return out
        ia, ib = suite_ids(la), suite_ids(lb)
        for sid in ib:  # a registered or edited entry = that suite runs
            if sid not in ia or _entry(lb, sid) != _entry(la, sid):
                suites.add(sid)
        files_to_id = {v: k for k, v in ib.items()}
    else:
        files_to_id = {v: k for k, v in suite_ids(_suites_block(show(repo, head, RUN_ALL) or "")[1]).items()}
    for f in files:
        if f.startswith("qa/suites/") and show(repo, head, f) is not None:
            sid = files_to_id.get(f[3:])
            if sid:
                suites.add(sid)
    langs = active_langs(repo, head)
    secs = []
    for f in files:
        lang = lang_of(f)
        if not lang:
            continue
        a, b = show(repo, mb, f), show(repo, head, f)
        if a is None or b is None:
            out["reason"] = "grāmatas fails %s pievienots / izņemts" % f
            return out
        try:
            ids, problem = section_diff(a, b)
        except (ValueError, KeyError, TypeError) as e:
            out["reason"] = "%s: nevaru salīdzināt pa sadaļām (%s)" % (f, str(e)[:80])
            return out
        if problem:
            out["reason"] = "%s: %s" % (f, problem)
            return out
        if langs is not None and lang not in langs:
            continue  # a retired language: not built, nothing to open
        secs += ["%s:%s" % (lang, i) for i in ids]
    if any(f.startswith(TRANSCRIPT_FILES) for f in files):
        suites.add("s14")  # «Настроение» → transcript opens in the app
    out.update(mode="nodalas", sections=secs, suites=sorted(suites),
               reason="tikai grāmatas teksts: %d sadaļas×valodas, %d mainīti testi" % (len(secs), len(suites)))
    return out


def _entry(block, sid):
    """Text of one SUITES entry (from its dict( to the next entry / comment / end)."""
    i = block.find('dict(id="%s"' % sid)
    if i < 0:
        return None
    j = min([k for k in (block.find("\n    dict(id=", i + 1), block.find("\n    #", i + 1), block.find("\n]", i + 1)) if k > 0]
            or [len(block)])
    return block[i:j]


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    argv = sys.argv[1:]
    head = "HEAD"
    if "--head" in argv:  # another commit / branch instead of HEAD (dry runs)
        i = argv.index("--head")
        head = argv[i + 1]
        del argv[i:i + 2]
    if "--worktree" in argv:
        head = ""
    args = [a for a in argv if not a.startswith("--")]
    repo = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    repo = os.environ.get("QA_REPO") or repo
    r = classify(repo, args[0] if args else "origin/main", head)
    if "--json" in sys.argv:
        print(json.dumps(r, ensure_ascii=False))
    else:
        print("%s — %s" % (r["mode"], r["reason"]))
        for s in r["sections"]:
            print("  sadaļa " + s)
        for s in r["suites"]:
            print("  tests  " + s)
