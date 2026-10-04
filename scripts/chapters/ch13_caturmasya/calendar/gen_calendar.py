# -*- coding: utf-8 -*-
"""Cāturmāsya / Puruṣottama-māsa date table for chapter 13, computed with GCal (gaurabda library).

  python gen_calendar.py [city] [year_from] [year_to]      (default: Riga 2026 2046)

1. GCal plain-text calendar per year -> out/<city>_<year>.txt   (gitignored, regenerable)
2. parsed days {iso: {tithi, note, masa, ev[]}}  -> out/<city>.json  (used by validate.py)
3. table rows -> table_<city>.json  (committed; read by ../build.py)

Library: https://github.com/gopa810/gaurabda-calendar (v0.8.4, commit 92c36b5), GCal 11 engine by Gopalapriya das.
Install:  pip install git+https://github.com/gopa810/gaurabda-calendar@92c36b5
     or:  git clone it and set GAURABDA_PATH=<clone dir>.
Location: gcal.FindLocation(city="Riga") from the library's own city list (Riga, Latvia).
"""
import datetime, io, json, os, re, sys, time

sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")
MON = {m: i + 1 for i, m in enumerate("Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split())}


def gcal_text(city, y0, y1):
    if os.environ.get("GAURABDA_PATH"):
        sys.path.insert(0, os.environ["GAURABDA_PATH"])
    import gaurabda as gcal
    loc = gcal.FindLocation(city=city)
    print(loc)
    os.makedirs(OUT, exist_ok=True)
    for y in range(y0, y1 + 1):
        p = os.path.join(OUT, f"{city}_{y}.txt")
        if os.path.exists(p):
            continue
        t = time.time()
        tc = gcal.TCalendar()
        tc.CalculateCalendar(loc, gcal.GCGregorianDate(text=f"1 jan {y}"), 366 if y % 4 == 0 else 365)
        s = io.StringIO()
        tc.write(s, format="plain")
        open(p, "w", encoding="utf-8").write(s.getvalue())
        print(y, round(time.time() - t, 1), "s", flush=True)


def parse(city, y0, y1):
    days, masa = {}, None
    for y in range(y0, y1 + 1):
        cur = None
        for line in open(os.path.join(OUT, f"{city}_{y}.txt"), encoding="utf-8"):
            m = re.match(r"^\s+(\S.*?) Masa, Gaurabda (\d+)", line)
            if m:
                masa = m.group(1)
                continue
            m = re.match(r"^\s{0,2}(\d{1,2}) (\w{3}) (\d{4}) \w\w  (\S+)(?: \(([^)]*)\))?", line)
            if m:
                d = datetime.date(int(m.group(3)), MON[m.group(2)], int(m.group(1)))
                cur = days.setdefault(d.isoformat(), {"tithi": m.group(4), "note": m.group(5), "masa": masa, "ev": []})
                continue
            if cur is not None and line.startswith("                 ") and line.strip():
                cur["ev"].append(line.strip())
    return days


def table(g, y0, y1):
    D = sorted(g)

    def find(pat, y, months=None):
        return [d for d in D if d.startswith(str(y)) and (months is None or d[5:7] in months)
                and any(re.search(pat, e) for e in g[d]["ev"])]
    rows = []
    for y in range(y0, y1 + 1):
        r = {"year": y}
        for k, n in (("m1", "First"), ("m2", "Second"), ("m3", "Third"), ("m4", "Fourth")):
            r[k] = find(f"{n} month of Caturmasya begins", y)
        last = find("Last day of the fourth Caturmasya", y)
        r["last4"] = last
        if last:
            nx = (datetime.date.fromisoformat(last[0]) + datetime.timedelta(1)).isoformat()
            r["end"] = nx
            r["end_tithi"] = g[nx]["tithi"]
        r["guru"] = find(r"Guru \(Vyasa\) Purnima", y)
        r["sayana"] = find("Fasting for Sayana Ekadasi", y)
        r["utthana"] = find("Fasting for Utthana Ekadasi", y)
        adh = [d for d in D if d.startswith(str(y)) and g[d]["masa"] and "adhika" in g[d]["masa"].lower()]
        r["adhika"] = [adh[0], adh[-1], len(adh)] if adh else None
        b0 = find("First day of Bhisma Pancaka", y, ("10", "11", "12"))
        b1 = find("Last day of Bhisma Pancaka", y, ("10", "11", "12"))
        assert len(b0) == 1 and len(b1) == 1, (y, b0, b1)
        r["bhisma"] = [b0[0], b1[0]]
        rows.append(r)
    return rows


if __name__ == "__main__":
    city = sys.argv[1] if len(sys.argv) > 1 else "Riga"
    y0 = int(sys.argv[2]) if len(sys.argv) > 2 else 2026
    y1 = int(sys.argv[3]) if len(sys.argv) > 3 else 2046
    # one extra year: the parse keeps the running māsa name across year boundaries
    gcal_text(city, y0, y1 + 1)
    days = parse(city, y0, y1 + 1)
    json.dump(days, open(os.path.join(OUT, f"{city}.json"), "w", encoding="utf-8"), ensure_ascii=False)
    rows = table(days, y0, y1)
    with open(os.path.join(HERE, f"table_{city}.json"), "w", encoding="utf-8", newline="\n") as f:
        json.dump(rows, f, indent=1)
        f.write("\n")
    print("table:", len(rows), "years ->", f"table_{city}.json")
