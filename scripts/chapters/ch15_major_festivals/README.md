# Chapter 15 — «Великие праздники» (Part IV «Праздники и обеты»)

Hand-written chapter, section id `major-festivals`. RU master `chapter_ru.py`, EN = `en_cache.json` (AnyModel cx/gpt-6.1-sol;
quotations with an English original and Gurudev's exact words are set by hand: `EN_FIX` / edited cache entries).
Locked in `scripts/translate/locked_sections.json` (tr.py keeps RU / RU-IAST). Other languages show the English
chapter with the "translation in preparation" note.

Sources: Gurudev's lectures; dates: the Chaitanya Academy calendar for Riga (ppp_calendar.json) and GCal 11 for Riga before Sep 2026 (as in ch.13). Table: festival dates 2026/2027 (`TABLES["dates"]`).

Builder: `../hand_chapter.py` (shared by chapters 14 and 15).

```
python build.py translate          # EN for changed RU strings only
python build.py apply              # data/book*.json, idempotent
python build.py fetch              # transcripts/ (gitignored) from sources.json
python build.py moods              # this chapter's entries in scripts/moods/moods.json
python ../../moods/apply_moods.py  # always after apply / moods
npm run build && npm run formats
```
