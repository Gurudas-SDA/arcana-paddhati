"""S msg 6787/6793/6803: «По середине строки над стихом жирную» (A120, 26.10.2026: «Шри Дамодараштака» — номера стихов;
6803 «Годится. Переделай» — утверждён вариант 2: номер над стихом, по центру, жирный).

Data-driven: a subsection with `"numbered": true` (data/book*.json) shows the running number 1, 2, … of its `verse` blocks
above each verse. Today only «Шри Дамодараштака» (kartika-bhajans → song-damodarastakam, 8 verses) has the flag.
  a) data: every data/book*.json that has song-damodarastakam has `"numbered": true` on it; no other subsection is flagged
     (S has not asked for others yet — new ones get the flag only after S says so);
  b) app (en, ru-iast): in song-damodarastakam there is exactly one `.verse-num` above each of the 8 verses, texts 1…8 in order,
     each directly before its Sanskrit block;
  c) the number is centred on the verse column, bold (font-weight >= 700), larger than the verse line
     (≈1.15× — # tehniskais slieksnis Lipikāra, nav S noteikums: ratio 1.05…1.30), a small gap to the IAST
     (# tehniskais slieksnis Lipikāra, nav S noteikums: 0…24 px) and does not overlap it;
  d) nothing else changes: the other subsections of the chapter (song-nanda-nandanastakam, song-radha-…) have no `.verse-num`,
     and a chapter with verses elsewhere (gaura-arati-songs) has none either.
usage: python s112_numbered_verses_a120.py <base-url>
"""
import glob
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))
import qa  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402

BASE = sys.argv[1].rstrip("/") if len(sys.argv) > 1 else None
DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data")
SID, SUB, N = "kartika-bhajans", "song-damodarastakam", 8
FLAGGED = {(SID, SUB)}  # subsections S asked to number
results = []


def check(device, name, ok, info=""):
    results.append(bool(ok))
    print(f"  [{'PASS' if ok else 'FAIL'}] {device} {name} {'' if ok else info}".rstrip(), flush=True)


# ---------------- a) data ----------------
files = sorted(glob.glob(os.path.join(DATA, "book*.json")))
for f in files:
    n = os.path.basename(f)
    book = json.load(open(f, encoding="utf-8"))
    flagged = {(s["id"], sub["id"]) for s in book["sections"] for sub in s.get("subsections", []) if sub.get("numbered")}
    has = any(s["id"] == SID and any(sub["id"] == SUB for sub in s.get("subsections", [])) for s in book["sections"])
    if has:
        check("data", f"{n}: {SUB} numbered", (SID, SUB) in flagged, sorted(flagged))
    check("data", f"{n}: no other subsection numbered", flagged <= FLAGGED, sorted(flagged - FLAGGED))

if BASE is None:
    print(f"{sum(results)}/{len(results)} passed")
    sys.exit(0 if results and all(results) else 1)

# ---------------- b–d) app ----------------
MEASURE_JS = """(sub) => {
  const s = document.getElementById(sub);
  if (!s) return null;
  const nums = [...s.querySelectorAll('.verse-num')];
  const verses = [...s.querySelectorAll('.verse-text')];
  return {verses: verses.length, nums: nums.map(e => {
    const cs = getComputedStyle(e);
    const sa = e.nextElementSibling;
    const r = e.getBoundingClientRect();
    const range = document.createRange(); range.selectNodeContents(e);
    const t = range.getBoundingClientRect();
    const sr = sa ? sa.getBoundingClientRect() : null;
    const line = sa ? sa.querySelector('p') : null;
    return {text: e.textContent.trim(), weight: parseInt(cs.fontWeight, 10), size: parseFloat(cs.fontSize),
            align: cs.textAlign, nextIsVerse: !!(sa && sa.classList.contains('verse-text')),
            saSize: sa ? parseFloat(getComputedStyle(sa).fontSize) : 0,
            textCx: t.left + t.width / 2, colCx: sr ? sr.left + sr.width / 2 : -1,
            gap: sr ? sr.top - r.bottom : -1, visible: r.height > 0 && t.width > 0};
  })};
}"""
OTHER_JS = """(sel) => [...document.querySelectorAll(sel)].map(s => [s.id, s.querySelectorAll('.verse-num').length])"""

with sync_playwright() as p:
    for device, engine, options in qa.devices(["iphone14", "pixel7", "desktop"]):
        browser = getattr(p, engine).launch()
        context = browser.new_context(service_workers="block", **options)
        page = context.new_page()
        for lang in ("", "ru-iast/"):
            tag = f"{device} {lang or 'en/'}"
            page.goto(f"{BASE}/{lang}{SID}/", wait_until="load")
            page.wait_for_selector(f"#{SUB} .verse-text", state="attached", timeout=15000)
            m = page.evaluate(MEASURE_JS, SUB)
            nums = m["nums"] if m else []
            check(tag, f"{SUB}: {N} verses, {N} numbers", m and m["verses"] == N and len(nums) == N, m and (m["verses"], len(nums)))
            check(tag, "numbers 1…8 in order", [x["text"] for x in nums] == [str(i) for i in range(1, N + 1)],
                  [x["text"] for x in nums])
            check(tag, "each number directly above its verse", nums and all(x["nextIsVerse"] and x["visible"] for x in nums), nums[:1])
            check(tag, "centred (text-align center, ±2 px of the verse column)",
                  nums and all(x["align"] == "center" and abs(x["textCx"] - x["colCx"]) <= 2 for x in nums), nums[:1])
            check(tag, "bold (font-weight >= 700)", nums and all(x["weight"] >= 700 for x in nums), nums[:1])
            check(tag, "≈1.15× the verse line (1.05…1.30)",
                  nums and all(x["saSize"] and 1.05 <= x["size"] / x["saSize"] <= 1.30 for x in nums), nums[:1])
            check(tag, "small gap to the IAST (0…24 px), no overlap", nums and all(0 <= x["gap"] <= 24 for x in nums),
                  [round(x["gap"], 1) for x in nums])
            others = page.evaluate(OTHER_JS, f"#{SID} section[data-subsection], section[data-subsection]")
            check(tag, "other subsections unnumbered", all(c == 0 for i, c in others if i != SUB), others)
        page.goto(f"{BASE}/gaura-arati-songs/", wait_until="load")
        page.wait_for_selector(".sanskrit", state="attached", timeout=15000)
        cnt = page.evaluate("() => [document.querySelectorAll('.sanskrit').length, document.querySelectorAll('.verse-num').length]")
        check(f"{device} en/", "gaura-arati-songs (not flagged, has verses): no numbers", cnt[0] > 0 and cnt[1] == 0, cnt)
        context.close()
        browser.close()

print(f"{sum(results)}/{len(results)} passed")
sys.exit(0 if results and all(results) else 1)
