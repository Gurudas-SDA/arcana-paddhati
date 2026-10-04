# Chapter 13 — «Чатурмасья и Пурушоттама-маса» (Part IV «Праздники и обеты»)

Hand-written chapter: the Russian text is the master (written from Gurudev's lectures, Hari-bhakti-vilāsa and the
Russian edition of Arcana-dīpikā), English is translated from it. It is **not** produced by `scripts/translate/tr.py`
and is locked there (`scripts/translate/locked_sections.json`), so `tr.py assemble` keeps the RU / RU-IAST copies
unchanged. Section id: `caturmasya-purusottama-masa`.

## Files

| File | What |
|---|---|
| `chapter_ru.py` | RU master text (Sanskrit inside `⟦…⟧` and verse `sanskrit` in IAST; build converts to Cyrillic for `book.ru.json`) |
| `en_cache.json` | EN translation, string by string (`src` = RU string, `en` = translation). Model cx/gpt-6.1-sol; the 8942 sentence in 13.4 was added by hand |
| `i18n_cache.json` | Part title + "translation in preparation" note for the other languages |
| `build.py` | `translate` (AnyModel, only changed strings) / `apply` (writes `data/book*.json`, `data/ui.*.json`) |
| `am.py` | AnyModel client for `build.py translate` (keys from `~/.credentials/ca_pipeline/config.ini`) |
| `moods_ch13.py` | the chapter's «Настроение Гурудева» entries in `scripts/moods/moods.json` (verbatim EN + Academy RU transcript) |
| `sources.json` | lecture meta for the quotes (date, transcript and audio links) |
| `calendar/gen_calendar.py` | GCal calculation for Riga → `calendar/table_Riga.json` (the table in 13.6) |
| `calendar/validate.py` | check against the Chaitanya Academy calendar (`calendar/ppp_calendar_snapshot.json`) |

Gitignored, regenerable: `calendar/out/` (GCal text per year + parsed days), `transcripts/` (`moods_ch13.py fetch`).

## Edit the text and rebuild

```
cd scripts/chapters/ch13_caturmasya
# edit chapter_ru.py
python build.py translate         # EN for the changed strings only (needs AnyModel keys)
python build.py apply             # idempotent: unchanged sources = no diff in data/
python moods_ch13.py              # only if the quotes changed (needs transcripts/: python moods_ch13.py fetch)
python ../../moods/apply_moods.py # always after apply (puts the mood blocks back)
npm run build
```

## Calendar (13.6 «Памятка с датами»)

```
pip install git+https://github.com/gopa810/gaurabda-calendar@92c36b5   # gaurabda 0.8.4 (GCal 11, Gopalapriya das)
cd calendar
python gen_calendar.py Riga 2026 2046     # ~6 s per year; writes out/ and table_Riga.json
python validate.py                        # exit 0 = all checks match
cd .. && python build.py apply
```

Rule used ("pūrṇimā system", as in our line): the vow begins on Guru-pūrṇimā and each next month on the next
pūrṇimā; the end is Kārttika-pūrṇimā. Location: the library's own entry for Riga, Latvia (the Academy's calendar
is made for Riga). Puruṣottama-māsa = GCal's adhika-māsa (new moon to new moon).

Validation (2026-10-04, `validate.py` against the Academy calendar `ppp_calendar.json`, Sep 2026 – Nov 2027,
https://gurudas-sda.github.io/ca-link-finder/data-static/ppp_calendar.json):

- Cāturmāsya dates (month starts + end): 8 of 8 match
- Ekādaśī fasting days: 31 of 31 match, no extra GCal days
- Viśvarūpa-mahotsava falls on the start of the 3rd month in all 21 years (2026–2046)
- Puruṣottama-māsa 2026 = 17 May – 15 Jun (the commonly published adhika-māsa dates)

Re-running the generator from scratch reproduces `table_Riga.json` exactly.
