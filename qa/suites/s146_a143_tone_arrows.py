"""A143 (Саткирти msg 7447–7450, 04.11.2026), «Арати», стрелки у куплетов, которые поются на другой тон.
Саткирти (burtiski): «отметить стрелками куплеты, которые поются на другой тон. 1) «Мангала шри гуру-гаура» (Arati daļa, maṅgala-ārati bhajani): куплеты 2, 4, 6, 8 — стрелка вверх (на тон выше); 5, 7, 9 — стрелка горизонтально (другой тон). 2) «Вибхавари-шеша»: куплеты 3, 5, 7 — стрелка вверх. 3) «Джая Радха, Джая Кришна, Джая Вриндаван», 5-й куплет: вместо «jaya paurṇamāsī, jaya ābhīra-nāgarī» писать «jaya jaya paurṇamāsī, ābhīra-nāgarī». Пришли скриншоты, как это будет выглядеть.»
Проверка:
  a) данные (en, ru-iast): у song-mangala-arati куплеты 2,4,6,8 tone=up; 5,7,9 tone=shift; остальные без tone;
     у song-vibhavari-sesa куплеты 3,5,7 tone=up; других песен с tone нет;
  b) данные (все языки): куплет 5 песни song-vraja-dhama-mahimamrta — вторая строка санскрита ровно «jaya jaya paurṇamāsī, ābhīra-nāgarī»
     (ru.json — то же в кириллице); пословный перевод ru-iast/ru: «jaya — слава» дважды перед «paurṇamāsī»; en: «jaya jaya paurṇamāsī»;
  c) приложение (с <base-url>): на странице «Мангала-арати» у «Мангала-арати» ровно 7 меток (↑ ×4, → ×3) на номерах 2,4,6,8 / 5,7,9,
     у «Вибхавари-шеша» ровно 3 метки ↑ на 3,5,7; у каждой есть aria-label; подпись видна только у первой метки каждого вида;
     номер остаётся по центру (метка не сдвигает его).
usage: python s146_a143_tone_arrows.py [<base-url>]
"""
import glob
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))
import qa  # noqa: E402

BASE = sys.argv[1].rstrip("/") if len(sys.argv) > 1 else None
DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data")
results = []
UP, SHIFT = "up", "shift"
EXPECT = {"song-mangala-arati": {2: UP, 4: UP, 6: UP, 8: UP, 5: SHIFT, 7: SHIFT, 9: SHIFT},
          "song-vibhavari-sesa": {3: UP, 5: UP, 7: UP}}


def check(where, name, ok, info=""):
    results.append(bool(ok))
    print(f"  [{'PASS' if ok else 'FAIL'}] {where} {name} {'' if ok else info}".rstrip(), flush=True)


def songs(b):
    for s in b["sections"]:
        for sub in s.get("subsections") or []:
            if str(sub.get("id", "")).startswith("song-"):
                yield sub


for fn in ("book.json", "book.ru-iast.json"):
    b = json.load(open(os.path.join(DATA, fn), encoding="utf-8"))
    got_all = {}
    for sub in songs(b):
        vs = [x for x in sub["content"] if x.get("type") == "verse" and x.get("sanskrit")]
        got_all[sub["id"]] = {i + 1: v["tone"] for i, v in enumerate(vs) if v.get("tone")}
    for sid, exp in EXPECT.items():
        check(fn, f"a {sid}: tone по куплетам {exp}", got_all.get(sid) == exp, got_all.get(sid))
    others = {k: v for k, v in got_all.items() if v and k not in EXPECT}
    check(fn, "a других песен с tone нет", not others, others)

for f in sorted(glob.glob(os.path.join(DATA, "book*.json"))):
    fn = os.path.basename(f)
    b = json.load(open(f, encoding="utf-8"))
    sub = next((x for x in songs(b) if x["id"] == "song-vraja-dhama-mahimamrta"), None)
    vs = [x for x in (sub or {"content": []})["content"] if x.get("type") == "verse"]
    v5 = vs[4] if len(vs) >= 5 else {}
    lines = v5.get("sanskrit", "").split("\n")
    want = "джайа джайа паурн̣ама̄сӣ, а̄бхӣра-на̄гарӣ" if fn == "book.ru.json" else "jaya jaya paurṇamāsī, ābhīra-nāgarī"
    check(fn, "b куплет 5: вторая строка «jaya jaya paurṇamāsī, ābhīra-nāgarī»", len(lines) == 2 and lines[1] == want, lines)
    wbw = v5.get("wbw", "")
    if fn == "book.ru-iast.json":
        check(fn, "b пословный: «jaya — слава; jaya — слава; paurṇamāsī»", "jaya — слава; jaya — слава; paurṇamāsī — " in wbw and "; jaya — слава; ābhīra" not in wbw, wbw)
    if fn == "book.ru.json":
        check(fn, "b пословный (кириллица): «джайа — слава; джайа — слава; паурн̣ама̄сӣ»", "джайа — слава; джайа — слава; паурн̣ама̄сӣ — " in wbw, wbw)
    if fn == "book.json":
        check(fn, "b пословный EN: «jaya jaya paurṇamāsī — glories, all glories»", "jaya jaya paurṇamāsī — glories, all glories" in wbw and "; jaya ābhīra" not in wbw, wbw)

if BASE is None:
    print(f"{sum(results)}/{len(results)} passed")
    sys.exit(0 if results and all(results) else 1)

from playwright.sync_api import sync_playwright  # noqa: E402

JS = """(id) => {
  const sec = document.getElementById(id);
  if (!sec) return null;
  return [...sec.querySelectorAll('.verse-num')].map(n => {
    const t = n.querySelector('.verse-tone'), nn = n.querySelector('.verse-num-n');
    const r = nn.getBoundingClientRect(), p = n.getBoundingClientRect();
    return {num: parseInt(nn.firstChild.textContent, 10), tone: t ? t.getAttribute('data-tone') : null,
            aria: t ? t.getAttribute('aria-label') : null, note: !!(t && t.querySelector('.verse-tone-note')),
            off: Math.round(Math.abs((r.left + r.width / 2) - (p.left + p.width / 2)))};
  });
}"""
SHOTS = os.environ.get("A143_SHOTS")
with sync_playwright() as p:
    for device, engine, options in qa.devices(["iphone14", "desktop"]):
        browser = getattr(p, engine).launch()
        context = browser.new_context(service_workers="block", **options)
        page = context.new_page()
        page.goto(f"{BASE}/ru-iast/mangala-arati-songs/", wait_until="load")
        page.wait_for_selector("#song-mangala-arati .verse-num", state="attached", timeout=20000)
        for sid, exp, label in (("song-mangala-arati", EXPECT["song-mangala-arati"], "Мангала-арати"),
                                ("song-vibhavari-sesa", EXPECT["song-vibhavari-sesa"], "Вибхавари-шеша")):
            got = page.evaluate(JS, sid) or []
            tag = f"{device} {label}"
            marks = {g["num"]: g["tone"] for g in got if g["tone"]}
            check(tag, "c метки на нужных номерах", marks == exp, marks)
            check(tag, "c у каждой метки подпись для чтения с экрана (aria-label)", all(g["aria"] for g in got if g["tone"]), got)
            kinds = [g["tone"] for g in got if g["note"]]
            check(tag, "c слова метки только у первой метки «вверх» (стрелка «другой тон» — без слов)", kinds == (["up"] if "up" in exp.values() else []), kinds)
            # S msg 7465 (04.11.2026), burtiski: «Все хорошо, только убери правописание "другой тон"»
            vis = page.evaluate("(id) => document.getElementById(id).innerText.includes('другой тон')", sid)
            check(tag, "c S 7465: «убери правописание \"другой тон\"» — надписи «другой тон» на странице нет", not vis, vis)
            check(tag, "c номер остаётся по центру (сдвиг ≤ 2 px)", all(g["off"] <= 2 for g in got), [g["off"] for g in got])
        if SHOTS:
            for sid, name in (("song-mangala-arati", "Мангала-арати"), ("song-vibhavari-sesa", "Вибхавари-шеша")):
                el = page.locator(f"#{sid}")
                el.scroll_into_view_if_needed()
                el.screenshot(path=os.path.join(SHOTS, f"{sid}-{device}.png"))
            # point 3: verse 5 of «Враджа-дхама-махимамрита» (the verse block with its number)
            v5 = page.locator("#song-vraja-dhama-mahimamrta .verse-text").nth(4)
            v5.scroll_into_view_if_needed()
            v5.locator("xpath=..").screenshot(path=os.path.join(SHOTS, f"song-vraja-dhama-v5-{device}.png"))
        context.close()
        browser.close()

print(f"{sum(results)}/{len(results)} passed")
sys.exit(0 if results and all(results) else 1)
