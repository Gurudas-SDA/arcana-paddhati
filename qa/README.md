# QA vārti — Arcana-paddhati

**Kāpēc:** neviena jau zināma Satkirti piezīme vai likums nedrīkst atkārtoti nonākt live. Katrs likums no
«Правила интерфейса книг.md» un «Стандарты книги и работы.md» ir reģistrēts `qa/likumi.json` un, kur iespējams,
tam ir automātisks tests. Pirms katra `git push` vārti palaiž būvējumu, satura linteri un ātro regresiju — ja kaut
kas krīt, push netiek izpildīts.

## Komandas

| Ko | Komanda |
|---|---|
| Ieslēgt vārtus (vienreiz pēc klonēšanas) | `npm run qa:install-hooks` (= `git config core.hooksPath qa/hooks`) |
| Ātrā regresija (pre-push, ≤5 min) | `npm run qa:fast` (= `python qa/run_all.py --fast`) |
| Pilnā regresija (~30–40 min, visas ierīces) | `npm run qa` (= `python qa/run_all.py`) |
| Satura linteris | `npm run qa:lint` (= `python qa/lint_content.py`) |
| Pārklājums (likumi ar testu / bez) | `npm run qa:coverage` (= `python qa/coverage.py`) |
| Daļa | `python qa/run_all.py --suites s07,s071 --devices pixel7,ipad-portrait`; saraksts: `--list` |

`run_all.py` pats palaiž lokālu statisku serveri no `out/` (brīvs ports, nekad 8899) zem `/arcana-paddhati` un to
aptur. Rezultāti: `qa/.results/last.json`, logi `qa/.results/<scenārijs>-<ierīce>.log` (git ignorē).
Prasības: Python 3 + `pip install playwright pillow` + `python -m playwright install chromium webkit`.

Ierīces (`qa/lib/qa.py`): pixel7, s23fe (360×780), iphone14, iphone-se, ipad-portrait, ipad-landscape, ipad-mini,
ipad-pro, desktop (Windows Chromium), mac-safari (WebKit). Ātrais režīms: pixel7 + iphone14 (abi dzinēji).
Kritis darbs tiek automātiski atkārtots vienu reizi; ja atkārtojumā iziet — atskaitē «FLAKY» (nebloķē, bet jāskatās).

## Procesu apturēšana — TIKAI pēc PID

`run_all.py` aptur tikai to, ko pats palaida: serveris ir tā paša procesa pavediens (`srv.stop()`), scenārijs, kas
pārsniedz laiku, tiek apturēts ar `taskkill /PID <tā PID> /T /F` (kopā ar SAVIEM pārlūkiem); `s20_offline.py webkit`
savu serveri aptur ar `Popen.kill()`. **NEKAD** `taskkill /IM python.exe`, `Stop-Process -Name python*`, `pkill python`
u.tml. — tie aptur arī citu sesiju darbu šajā datorā (incidents 06.10 21:28). Pārslodzes gadījumā — mazāk paralēlu
darbu: `python qa/run_all.py --fast --jobs 3`.

## Kas notiek pie `git push` (qa/hooks/pre-push)

1. Push drīkst sūtīt tikai izņemto HEAD, un darba kokam jābūt tīram (citādi testētu ne to, kas tiek sūtīts).
2. Ja `out/` vecāks par avotu → `npm run build`.
3. `python qa/lint_content.py` — datu likumi (L1–L23).
4. `python qa/run_all.py --fast` — pārlūka regresija.

Jebkura kļūda → **push bloķēts** ar skaidru ziņu, kurš tests un kurš Satkirti likums krita.

**`git push --no-verify` (vārtu apiešana) ir AIZLIEGTA** bez Satkirti vai Gurudas tiešas ziņas konkrētajam push.
Ja vārti kļūdaini bloķē — labo testu (ar pamatojumu commit ziņā), nevis apej vārtus.

## Kā jauna Satkirti piezīme kļūst par testu (veidne)

Katru reizi, kad Satkirti dod interfeisa/satura piezīmi (vai КСВ atrod kļūdu):

1. **Likums.** Ieraksti to RU dokumentā («Правила интерфейса книг.md» vai «Стандарты книги и работы.md») — tā prasa §9.
2. **Reģistrs.** Pievieno ierakstu `qa/likumi.json`:
   ```json
   {"id": "UI-9.10", "doc": "UI", "section": "§9", "text": "<rinda no dokumenta, burtiski>",
    "tests": ["s0XX:<pārbaudes nosaukuma sākums>"]}
   ```
   Ja tests nav iespējams: `"tests": [], "nav_testa": "<kāpēc>"` — tas parādīsies `coverage.py` sarakstā.
3. **Tests.** Izvēlies vietu:
   - *datu/teksta likums* (rakstība, locījumi, katram pantam X) → jauna pārbaude `qa/lint_content.py`
     (`c = Check("L21", "<īss apraksts>")` … `c.hit(fails, ceļš, fragments)` … `c.report(args.max)`);
   - *uzvedība lietotnē* → jauns scenārijs `qa/suites/sNN_<īss_nosaukums>.py` (paraugs: `s12_back_to_search.py`)
     un rinda `SUITES` sarakstā `qa/run_all.py` (`fast=True`, ja piezīme ir svarīga katram push).
   Scenārija līgums: arguments = bāzes URL; ierīces no `qa.devices([...])` (filtrs `QA_DEVICES`); katra pārbaude drukā
   `  [PASS] <ierīce> <nosaukums>` vai `  [FAIL] <ierīce> <nosaukums> <pierādījums>`.
4. **Visai grāmatai.** Tests pārbauda principu visā grāmatā (visas nodaļas / visus attēlus), ne tikai atrasto vietu (КСВ likums).
5. **Pierādi, ka tests ķer.** Uz brīdi atjauno kļūdu → tests krīt; atgriez labojumu → tests iziet. Tikai tad commit.
6. **Commit** kopā ar labojumu: `[Arcana-paddhati] <labojums> + test (Satkirti DD.MM)`.

## Izņēmumi un momentuzņēmumi

- Lintera izņēmumi: `qa/lint_config.json` → `exceptions` (`check`, `file`, `match`, **`reason`**, `since`, **`by`**).
  Izņēmums nebloķē, bet parādās kā `[WARN]`. Jaunu izņēmumu drīkst pievienot tikai ar Satkirti vai Gurudas ziņu;
  zināmo trūkumu izņēmumus dzēš, tiklīdz trūkums novērsts.
- Galvenie Gurudeva citāti: `qa/snapshots/main_quotes.json` (L14). Mainīt/izņemt galveno citātu drīkst TIKAI pēc Satkirti
  tieša lūguma; tad `python qa/lint_content.py --update-quote-snapshot` un commit ziņā norāde uz lūgumu. Pievienot drīkst brīvi.

## Faili

| Fails | Kas |
|---|---|
| `run_all.py` | viena komanda: serveris + visi scenāriji paralēli + atskaite |
| `suites/s00…s21` | uzvedības scenāriji (pārnesti no Reader v2–v7.1 testiem un neatkarīgā verificētāja) |
| `lint_content.py`, `lint_config.json` | satura linteris + izņēmumi |
| `likumi.json`, `coverage.py` | Satkirti likumu reģistrs → testi; pārklājuma atskaite |
| `hooks/pre-push` | git vārti |
| `lib/qa.py`, `lib/server.py` | ierīču profili, ceļi, `out/` svaigums; lokālais serveris |
| `snapshots/main_quotes.json` | galveno citātu momentuzņēmums (L14) |
