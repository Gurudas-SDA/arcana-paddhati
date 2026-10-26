"""Arcana-paddhati regresijas komplekts — viena komanda.

  python qa/run_all.py            pilnais: visi scenāriji, visas ierīces (~30–40 min)
  python qa/run_all.py --fast     ātrais (pre-push): galvenās ierīces, galvenie scenāriji (≤5 min)
  python qa/run_all.py --suites s07,s071 --devices pixel7,ipad-portrait
  python qa/run_all.py --list
  python qa/run_all.py --changed-from origin/main   pre-push / qa_run.py nodalas: only book TEXT changed →
                                  lint + s200 (changed sections × iPhone 14, iPad, desktop) + changed/added suites +
                                  data-only rule suites; anything else → exactly --fast (qa/lib/changed.py)

Palaiž lokālu statisku serveri no out/ (brīvs ports, NE 8899) zem /arcana-paddhati,
katru scenāriju (qa/suites/*.py) kā atsevišķu procesu (paralēli, pa ierīcēm),
apkopo [PASS]/[FAIL] rindas, saista kļūdas ar Satkirti likumiem (qa/likumi.json),
raksta qa/.results/last.json un logus qa/.results/<scenārijs>-<ierīces>.log.
Izejas kods 1 = kaut viena pārbaude krita (vai scenārijs avarēja).
Procesus aptur TIKAI pēc paša palaistā PID (kill_tree) — nekad pēc nosaukuma (python.exe).
Pārslodzes gadījumā: --jobs 3.
"""
import argparse
import concurrent.futures as cf
import json
import os
import re
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "lib"))
import qa  # noqa: E402
import server as qa_server  # noqa: E402

RESULTS = os.path.join(HERE, ".results")
LINE = re.compile(r"^\s*\[(PASS|FAIL|SKIP|WARN|INFO)\]\s+(\S+)\s+(.*)$")
TOC_MODE_SUITES = {"s01", "s03", "s04", "s05", "s23", "s24", "s25", "s30", "s071", "s35"}

# name, file, devices (full run; None = the suite has no devices), in fast run?, extra env (fast), extra env (full)
SUITES = [
    dict(id="lint", file="lint_content.py", title="satura linteris (data/ + out/)", devices=None, fast=True, server=False),
    dict(id="s00", file="suites/s00_one_russian.py", title="viens «Русский» (ru → ru-iast)", devices=["iphone14", "pixel7", "desktop"], fast=True),
    dict(id="s01", file="suites/s01_reader_mode.py", title="lasīšanas režīms (Apple Books izvēlne, Аа, meklēšana, «Назад»)",
         devices=["iphone14", "pixel7", "ipad-portrait", "ipad-landscape", "ipad-mini", "ipad-pro", "desktop"], fast=True,
         env_fast={"LANGS": "ru-iast"}),
    dict(id="s02", file="suites/s02_columns_fonts.py", title="teksts pilnā platumā, burtu izmērs, «Аа» saglabājas",
         devices=["iphone14", "pixel7", "ipad-portrait", "ipad-landscape", "desktop"], fast=True),
    dict(id="s03", file="suites/s03_cover_back_steps.py", title="vāks: pieskāriens rāda izvēlni; «Назад» soli pa solim; pogas malās",
         devices=["pixel7", "iphone14", "ipad-portrait", "ipad-landscape", "ipad-mini", "ipad-pro", "desktop"], fast=True),
    dict(id="s04", file="suites/s04_contents_expand.py", title="«Содержание»: nodaļa ar apakšnodaļām izveras; «Назад» uz to pašu vietu",
         devices=["pixel7", "iphone14", "ipad-portrait", "ipad-landscape", "ipad-mini", "ipad-pro", "desktop"], fast=True),
    dict(id="s05", file="suites/s05_two_tap_mood_offline_ui.py", title="divi pieskārieni, «Настроение» logs, numuri rindā, bez tulkošanas, bez ārējiem",
         devices=["iphone14", "pixel7", "ipad-portrait", "ipad-landscape", "ipad-mini", "ipad-pro", "desktop"], fast=True),
    dict(id="s06", file="suites/s06_next_chapter.py", title="«Вперёд ›» katras nodaļas beigās",
         devices=["iphone14", "iphone-se", "pixel7", "ipad-portrait", "ipad-landscape", "desktop"], fast=True),
    dict(id="s07", file="suites/s07_path_intro_pictures.py", title="ceļa izgaismojums, «Вперёд», «Введение» grupa, attēls↔saraksts, vāks, «пословно» visiem",
         devices=["pixel7", "s23fe", "iphone14", "ipad-portrait", "ipad-landscape", "desktop", "mac-safari"], fast=True),
    dict(id="s071", file="suites/s071_reader_v71.py", title="Reader v7.1 (Satkirti 06.10, 1–19)",
         devices=["pixel7", "s23fe", "iphone14", "ipad-portrait", "ipad-landscape", "desktop", "mac-safari"], fast=True),
    dict(id="s10", file="suites/s10_rules_verifier.py", title="neatkarīgais verificētājs pa likumiem §1–§9",
         devices=["pixel7", "s23fe", "iphone14", "ipad-portrait", "ipad-landscape", "ipad-mini", "desktop", "mac-safari"], fast=False),
    dict(id="s11", file="suites/s11_headings_after_jump.py", title="apakšnodaļas virsraksts augšā pēc pārejas no «Содержание»",
         devices=["pixel7", "s23fe", "iphone14", "ipad-portrait", "ipad-landscape"], fast=False),
    dict(id="s12", file="suites/s12_back_to_search.py", title="«Назад» uz meklēšanu ar vaicājumu un atvērto rezultātu redzamu",
         devices=["pixel7", "iphone14", "desktop", "mac-safari"], fast=True),
    dict(id="s13", file="suites/s13_cards_no_overflow.py", title="teksts un tabulu kartītes neiziet pa labi ārā (visas nodaļas, «Аа» ×1 un ×1.35)",
         devices=["s23fe", "pixel7", "iphone-se", "iphone14"], fast=True),
    dict(id="s14", file="suites/s14_mood_transcript.py", title="«Настроение»: tap «транскрипт» atver transkriptu lietotnē (arī offline)",
         devices=["pixel7", "s23fe", "iphone14", "iphone-se"], fast=True),
    dict(id="s22", file="suites/s22_parampara_songs.py", title="Reader v7.4: parampara (8 lapas, paraksti, bez apgriešanas) + ārati dziesmas",
         devices=["pixel7", "iphone14", "s23fe", "iphone-se", "ipad-portrait", "ipad-landscape", "ipad-mini", "desktop", "mac-safari"], fast=True),
    dict(id="s23", file="suites/s23_ksv_0710_taps_back.py", title="КСВ 07.10: portrets=lapa, «Обложка»=home, «Назад»=tie paši soļi, divi pieskārieni (telefons+planšete+dators)",
         devices=["pixel7", "iphone14", "ipad-portrait", "ipad-landscape", "desktop", "mac-safari"], fast=True,
         fast_devices=["pixel7", "iphone14", "ipad-portrait", "desktop"]),
    dict(id="s24", file="suites/s24_two_tap_all_rows.py", title="v7.6.1: divi pieskārieni KATRAI lapas rindai (nodaļa bez apakšnodaļām, apakšnodaļa) + «Назад» (dators visas, telefons/iPad ≥30)",
         devices=["desktop", "pixel7", "iphone14", "ipad-portrait", "ipad-landscape", "mac-safari"], fast=True,
         fast_devices=["desktop", "pixel7", "iphone14", "ipad-portrait"]),
    dict(id="s25", file="suites/s25_contents_reload_history.py", title="v7.6.1: «Содержание» pēc pārlādes, pārlāde vēstures vidū, dziļā saite, ātri dubultpieskārieni",
         devices=["pixel7", "iphone14", "ipad-portrait", "ipad-landscape", "desktop", "mac-safari"], fast=True,
         fast_devices=["pixel7", "iphone14", "ipad-portrait", "desktop"]),
    dict(id="s26", file="suites/s26_ksv_0710_evening.py", title="v7.8 КСВ 07.10 vakars: «Аа» slēdži+valoda, nekustīgā «Обложка», pilna platuma rindas, autoritināšana, tilakas rindas+galvvidus, īsās mantras bez «пословно», meklēšanas izgaismojums, parampara bez rombiem",
         devices=["pixel7", "iphone14", "ipad-portrait", "ipad-landscape", "desktop", "mac-safari"], fast=True,
         fast_devices=["pixel7", "iphone14", "ipad-portrait"]),
    dict(id="s27", file="suites/s27_night_sync_safety.py", title="v7.8.3: nakts sinhronizācija nedzēš tulkotu sadaļu bez i18n ieraksta; atomiski faili",
         devices=None, fast=True, server=False),
    dict(id="s28", file="suites/s28_a68_night_0910.py", title="A68 nakts 09.10: sanskrits tikai sanskrits (RU-IAST = EN), avotu rakstība, HU cache pādya-pātra, night_sync exit≠0 pie FAIL",
         devices=None, fast=True, server=False),
    dict(id="s29", file="suites/s29_tulasi_patram_0910.py", title="nakts 09.10: 12-пушпа «tulasī-patram» (lapa), ne «pātram» (trauks) — avots p055; visas grāmatas, RU kirilica, 16 upacāra",
         devices=None, fast=True, server=False),
    dict(id="s30", file="suites/s30_a65_toc_loading.py", title="A65 КСВ 07.10: «Содержание» 2. pieskāriens — uzreiz ielādes josla + «загружается…», atkārtots pieskāriens nesabojā, vecā lapa nemirgo",
         devices=["pixel7", "iphone14", "ipad-portrait", "desktop", "mac-safari"], fast=True,
         fast_devices=["pixel7", "iphone14", "desktop"]),
    # s32: pt + lt removed from the book (S 23.10 Padomnieks 934–941) — not run while they are retired.
    dict(id="s32", file="suites/s32_lang_pt_lt.py", title="A73: valodas pt + lt — /pt/ un /lt/ atveras, «Аа» valodu izvēlnē, pilns tulkojums, IAST = EN, nav angļu teikumu, UI atslēgas, offline",
         devices=["pixel7", "iphone14", "desktop"], fast=True, fast_devices=["pixel7", "desktop"],
         skip="S 23.10 Padomnieks 934–941: valoda izņemta (pt, lt)"),
    dict(id="s33", file="suites/s33_toc_one_tap.py", title="TOC: chapter top, action-only Back, cover/search; one-tap default",
         devices=["s23fe", "iphone14", "pixel7", "desktop", "mac-safari"], fast=False),
    # s34 off: continuous reading is not used (Satkirti 14.10.2026 msg 3480); re-enable with CONTINUOUS_BOOK.
    # dict(id="s34", file="suites/s34_continuous_book.py", title="Continuous book: cover scroll, deep links, reload, Back/Forward and offline",
    #      devices=["s23fe", "iphone14", "pixel7", "desktop", "mac-safari"], fast=False),
    dict(id="s35", file="suites/s35_history_burst.py", title="History writes under fast tapping: app writes <= actions, no WebKit quota error, Back/Forward retrace (17 and 40 actions, Back burst)",
         devices=["pixel7", "iphone14", "ipad-portrait", "desktop"], fast=True, fast_devices=["pixel7", "iphone14"]),
    dict(id="s37", file="suites/s37_reading_place.py", title="Contents reading place: closing, subsection marks and opened chapter visibility",
         devices=["iphone14", "pixel7"], fast=True),
    dict(id="s38", file="suites/s38_cover_load.py", title="КСВ 14.10: vāks interaktīvs ≤3 s (Chromium emulācija, CPU 4×) + lejupielādētie MB",
         devices=["ipad-portrait", "iphone14", "pixel7"], fast=True, fast_devices=["ipad-portrait"]),
    dict(id="s39", file="suites/s39_images_loaded.py", title="КСВ 14.10: visi attēli ielādējas pēc ielādes, ritināšanas un pārlādes",
         devices=["ipad-portrait", "iphone14", "pixel7"], fast=False),
    dict(id="s20",file="suites/s20_offline.py", title="OFFLINE: Chromium (Android) — visas nodaļas, navigācija, transkripti", args=["chromium"],
         devices=None, fast=True, timeout_fast=200),
    dict(id="s20wk", file="suites/s20_offline.py", title="OFFLINE: WebKit (iPhone/iPad) — serveris izslēgts", args=["webkit"],
         devices=None, fast=False),
    dict(id="s49", file="suites/s49_offline_save_card.py", title="Vraja 5318: «Видимая загрузка» — bloks uz vāka (stāvokļi 1–4), bez lēciena, skaits = «Содержание» rinda",
         devices=["iphone14", "pixel7", "desktop"], fast=True, fast_devices=["iphone14", "pixel7"]),
    dict(id="s50", file="suites/s50_sw_updates.py", title="Vraja 5316 p.2: SW — jaunā versija pārņem arī nepilnu; tiešsaistē tīkls pirmais; updateViaCache none, update(), viena pārlāde",
         devices=["pixel7", "desktop"], fast=True, fast_devices=["pixel7"]),
    dict(id="s51", file="suites/s51_search_field.py", title="Vraja 5316 p.3: meklēšanas lauks 16 px, placeholder --ap-gold #965700 (V33), fokuss pieskāriena laikā, .mobile-menu[data-open]",
         devices=["iphone14", "pixel7", "desktop"], fast=True, fast_devices=["iphone14", "pixel7"]),
    dict(id="s53", file="suites/s53_fonts_own_cut.py", title="Vraja 5316 p.4: sava fonta nogriezne (taisnais + V49 īsts kursīvs), Google Noto Serif netiek lejupielādēts, preload ≤ 130 KB",
         devices=["pixel7", "iphone14", "desktop"], fast=True, fast_devices=["pixel7", "iphone14"]),
    dict(id="s59", file="suites/s59_emblem_numbers.py", title="Vraja 5429/5432: emblēmas numuri 1–12, 2.1–2.6 — #6E1A2E, balta 60 % pill + blur 3,5 px, HTML slānis bez mix-blend; 8/10/11 jaunās vietas; attēlā nav iededzinātu ciparu",
         devices=["iphone14", "ipad-portrait", "desktop"], fast=True, fast_devices=["iphone14"]),
    dict(id="s52", file="suites/s52_reading_place.py", title="Vraja 5316 p.5–7: lasīšanas vieta (klusi, liveLang), «Продолжить» uz vāka bez lēciena, cilne «Закладки»",
         devices=["iphone14", "pixel7", "desktop"], fast=True, fast_devices=["iphone14", "pixel7"]),
    dict(id="s54", file="suites/s54_bookmark_button.py", title="Vraja 5380: grāmatzīmes poga (variants A) augšējā joslā — tosts «Закладка поставлена · Отменить», 10.1 otrs pieskāriens noņem, 10.2 bez vēstures soļa, offline, 12 valodas 320–390 px",
         devices=["iphone14", "pixel7", "desktop"], fast=True, fast_devices=["iphone14", "pixel7"]),
    dict(id="s57", file="suites/s57_vraja_1020.py", title="Vraja 20.10 (5391–5402): «Настроение» aizveras ar pieskārienu fonam (kā ✕, Esc), numurēti attēli centrā, divkolonnu sarakstu joslas + līnija pirms grupas, «Next chapter» kolonnā",
         devices=["iphone14", "pixel7", "desktop"], fast=True, fast_devices=["iphone14", "pixel7"]),
    dict(id="s56", file="suites/s56_lang_menu.py", title="Vraja 5418 (variants Nr. 1): valodas izvēlne grāmatas stilā — listbox, ≥44 px, ✓, Esc/ārpuse aizver, izvēle maina valodu, Тёмный/Бежевый kontrasts, mazs horizontāls ekrāns ritinās",
         devices=["iphone14", "pixel7", "desktop"], fast=True, fast_devices=["iphone14", "pixel7"]),
    dict(id="s58", file="suites/s58_resume_arrow.py", title="Vraja 5430: «Продолжить чтение» — bultiņa › --ap-gold #965700 (V33) labajā apakšā, teksts nezem bultiņas, garie nosaukumi 2–3 rindās bez «…», vāks nelēkā",
         devices=["iphone14", "ipad-portrait", "pixel7"], fast=True, fast_devices=["iphone14", "pixel7"]),
    dict(id="s55", file="suites/s55_bookmark_lit.py", title="Vraja 5436: cilnē «Закладки» lasāmās vietas grāmatzīme izcelta tāpat kā «Содержание» (9.2), jaunākā no vairākām, pieritināta redzamā (9.12)",
         devices=["iphone14", "pixel7", "desktop"], fast=True, fast_devices=["iphone14", "pixel7"]),
    dict(id="s60", file="suites/s60_bookmark_remove_icon.py", title="Vraja 5439/5440: cilnē «Закладки» ikona labajā pusē noņem grāmatzīmi (2а) — rinda bāla līdz tosta beigām, «Отменить» atjauno, rinda pati joprojām ved uz vietu",
         devices=["iphone14", "pixel7", "desktop"], fast=True, fast_devices=["iphone14", "pixel7"]),
    dict(id="s61", file="suites/s61_paraphernalia_schema.py", title="V13 Vraja 736/738: «16 предметов» → Vraja shēma (oriģināls masters/ nemainīts, WebP 1254×1254 bez kropļojuma, 1:1 kaste no datiem, 18 objektu pieskārieni → rinda) + V20 Vraja 5617–5620: maskas veselas arī pelēko līniju krustojumos, cipari pilni; V20b 5637/5638: cipari ar serifiem, iepriekš sagatavots izgaismotais attēls (visas iekšējās līnijas tumšas); V20c 5658: maska N = Vraja SVG slānis N (līnijas + cipars, IoU ≥ 0.99), attēls un izgaismojums rasterizēti no tā paša SVG",
         devices=["iphone14", "pixel7", "desktop"], fast=True, fast_devices=["iphone14", "pixel7"]),
    dict(id="s62", file="suites/s62_ca_logo_vector.py", title="V8 Vraja 742: Chaitanya Academy logotips uz vāka — Vraja SVG inline (viewBox 257,42:83,23, bez kropļojuma), vecā logotipa vietā, WebP bez rastra logotipa, lasāms arī «Тёмный», vāks nelēkā",
         devices=["iphone14", "pixel7", "ipad-portrait", "desktop"], fast=True, fast_devices=["iphone14", "pixel7"]),
    dict(id="s63", file="suites/s63_splash.py", title="Vraja 20.10 (ДА 5520, kods 762): starta ekrāns — balts slānis, CA zīme 200 px centrā, aiziet 450 ms ease-out pēc hidratācijas, reduced motion statiska, drošība 4 s bez JS; iOS startup attēli visiem izmēriem; manifest #ffffff",
         devices=["iphone14", "ipad-portrait", "desktop"], fast=True, fast_devices=["iphone14", "desktop"]),
    dict(id="s64", file="suites/s64_cover_cards_width.py", title="Vraja 20.10 (ДА 5520): kartītes zem vāka («Продолжить», «Сохраняется») tieši vāka platumā — malas sakrīt ±1 px (iPhone SE/14, iPad portrets/ainava, dators)",
         devices=["iphone-se", "iphone14", "ipad-portrait", "ipad-landscape", "desktop"], fast=True, fast_devices=["iphone14", "desktop"]),
    dict(id="s65", file="suites/s65_menu_slide.py", title="Vraja 20.10 (ДА 5520, 5521): «Содержание» izbīdās/iebīdās ar augšējās joslas easing un ilgumu, izvēlētā rinda #F5E6C8, A65 kārtība, «Аа» panelis aizveras plūstoši; reduced motion — bez animācijas",
         devices=["iphone14", "pixel7", "desktop"], fast=True, fast_devices=["iphone14", "pixel7"]),
    dict(id="s66", file="suites/s66_bottom_bar_still.py", title="Vraja 20.10 (pēc V16): apakšējā josla nemirgo, kad «Содержание» izbīdās/iebīdās — vieta, redzamība, nav zem aptumšojuma, «Назад»/«Вперёд» nemainās (iPhone, Android, dators)",
         devices=["iphone14", "pixel7", "desktop"], fast=True, fast_devices=["iphone14", "pixel7"]),
    dict(id="s67", file="suites/s67_menu_never_halfway.py", title="Vraja 20.10 (msg 5605): «Содержание» nekad nepaliek pusceļā — aizvērts izbīdoties, atvērts iebīdoties, ātri pieskārieni, ekrāna pagriešana; beigās pilnībā ārā vai prom, apakšējā josla virs aptumšojuma",
         devices=["iphone14", "pixel7", "desktop"], fast=True, fast_devices=["iphone14", "pixel7"]),
    dict(id="s68", file="suites/s68_dim_close_x.py", title="Vraja V18 (5603/5606/5610): aptumšojums melns 60 % bez izpludinājuma («Настроение», instalēšanas logs, «Содержание»), apakšējā josla neaptumšota; ✕ augšējās rindas līmenī (telefons/desktop ≥1024 px, «Аа» panelis)",
         devices=["iphone14", "pixel7", "desktop"], fast=True, fast_devices=["iphone14", "desktop"]),
    dict(id="s69", file="suites/s69_chapter_nav.py", title="V17 Vraja 796/5639/5784: navigācija pa nodaļām (virsraksts pēc pārejas pilnībā zem augšējās joslas) — apakšā «‹ Назад»/«Вперёд ›» = iepr./nāk. nodaļa satura secībā (Pages un Scroll), pirmajā/pēdējā nav, bez «где мы / %» rindas, bez «Next chapter» bloka, nodaļas beigās joslas 1×, augšup aiziet",
         devices=["pixel7", "iphone14", "iphone-se", "ipad-portrait", "desktop"], fast=True, fast_devices=["iphone14", "pixel7"]),
    dict(id="s70", file="suites/s70_en_theme_label.py", title="Vraja 5780: EN tumšais fons «Dark» (RU «Тёмный»), nekur EN saskarnē «Night»",
         devices=None, fast=True, server=False),
    dict(id="s71", file="suites/s71_bookmark_name.py", title="V34 Satkirti 5866 + Vraja 5869/5872: grāmatzīmes nosaukuma logs (vidū, aptumšojums 60 % bez izpludinājuma, ✕, noklusējums = apakšnodaļas nosaukums, Enter/Отмена/Esc), zīmulītis pa kreisi no dzēšanas, pārdēvētai tikai nosaukums 1 rindā ar «…», precīza vieta (bloks) atveras zem augšējās joslas un iezīmējas — «Страницы» un «Лента»",
         devices=["iphone14", "pixel7", "desktop"], fast=True, fast_devices=["iphone14", "pixel7"]),
    dict(id="s78", file="suites/s78_bg_dark_all_langs.py", title="V26b Vraja 5817: «Аа» fons «Тёмный» visās valodās nozīmē «tumšs», ne «nakts» (de/es/fr/hu/it/lt/lv/pt/uk + ru); visas V21 pārdēvētās atslēgas visās valodās, vietturi kā RU",
         devices=None, fast=True, server=False),
    dict(id="s75", file="suites/s75_aa_panel_v27.py", title="V27 Vraja 5769–5779: «Аа» panelis — «Язык» pirmā funkcija, logs nav apgriezts, kamēr ekrānā vieta, aiz tā aptumšojums melns 60 % (pieskāriens aizver), valodu sarakstam tie paši 60 % visos fonos (telefoni arī ainavā)",
         devices=["iphone14", "pixel7", "s23fe", "iphone-se", "ipad-portrait", "desktop"], fast=True, fast_devices=["iphone14", "pixel7"]),
    dict(id="s76", file="suites/s76_item_peek_v28.py", title="V28 Vraja 5782: «16 предметов» peldošais attēla lodziņš vienmēr pilnībā ekrānā, ✕ virspusē un nospiežams (iPhone 14, Pixel 7, iPad, desktop; portrets/ainava; joslas rādītas/slēptas; lodziņš augšā/apakšā)",
         devices=["iphone14", "pixel7", "ipad-portrait", "ipad-landscape", "desktop"], fast=True, fast_devices=["iphone14", "pixel7"]),
    dict(id="s77", file="suites/s77_resume_fade_v29.py", title="V29 Vraja 5783: «Продолжить» — mērķa lapa bez lēciena (vieta nekustas, kamēr lapa redzama), parādās ar īsu fade (CSS 200 ms, mērīts 100–450 ms); reduced motion — uzreiz, bez animācijas",
         devices=["iphone14", "pixel7", "desktop"], fast=True, fast_devices=["iphone14", "pixel7"]),
    dict(id="s101", file="suites/s101_front_um8_jaya.py", title="Satkirti 22.10 msg 6137/6139, 6151–6155: grāmata sākas ar «Упадеша-сара» (Upadeśāmṛta 8, BBT tulkojums + пословный no vedabase, «Настроение Гурудева» 5 citāti № 7717, 812, 554, 137, 447) → «Гуру-парампара» → «Джая-дхвани» (msg 6177/6180: 34 saucieni burtiski no «Gīti-guccha» 2016, 2. = mūsu guru vārds, needs_satkirti) → «Мангалачарана»; Ievadā panta vairs nav (ŚB 11.3.48 neatgriezts); 9 valodās tulkojums vai EN līdz nakts izlaidumam; emblēma nemainīta (msg 6038)",
         devices=None, fast=True, server=False),
    dict(id="s88", file="suites/s88_conclusion.py", title="Satkirti 21.10 msg 6065 + Idea №2 (msg 5692): «Заключение» — pēdējā sadaļa ārpus daļām, bez numura; dienas cikls no pamodināšanas līdz noguldīšanai; katram Gurudeva citātam avots (№, datums, laiks, saite); ru-iast bez kirilicas ar diakritiku",
         devices=None, fast=True, server=False),
    dict(id="s104", file="suites/s104_tulk_gaida.py", title="Gurudas 23.10 msg 868: tulkojuma trūkums neaptur izlaidumu — qa/tulkojumi_gaida.json pāri EN līdz tulkojumam; L27/L31 pieņem EN TIKAI šiem pāriem, citur stingri (mākslīgas kļūdas krīt); L38 saraksts aktuāls (tehniskais slieksnis Lipikāra, nav S noteikums)",
         devices=None, fast=True, server=False),
    dict(id="s100", file="suites/s100_ashtakala.py", title="Satkirti 22.10 msg 6141/6151 + 6169/6504 (pants tan-nāma-rūpa TIKAI 10. apakšnodaļas beigās, ne «Заключения» sākumā, visās 12 grāmatās): «Заключение» 11. apakšnodaļa «Аштакалия-лила» — tabula 8 rindas diennakts secībā (laiks no–līdz, IAST nosaukums, kas notiek — viena rinda), laiki 24 h bez spraugām no 3:36; beigās avots tikai Bhajana-rahasya + Gurudevs + Nārāyaṇa Mahārāja (bez noapaļoto laiku rindkopas); 10. apakšnodaļas beigās UM 8 pants vēlreiz pilnībā",
         devices=None, fast=True, server=False),
    dict(id="s82", file="suites/s82_one_block_highlight_v36.py", title="V36 Vraja 5962: atzīmēta saraksta rinda = VIENS bloks (numurs + teksts vienā taisnstūrī ar noapaļotiem stūriem) — 16 priekšmeti (11) асана), tilaka saraksts",
         devices=["iphone14", "desktop"], fast=True),
    dict(id="s84", file="suites/s84_bookmark_keyboard_v38.py", title="V38 Vraja 1315–1317: grāmatzīmes logs («Новая закладка»/«Переименовать») virs iPhone tastatūras (visualViewport) — «Отмена»/«Подтвердить» redzamas un nospiežamas (iPhone 13/14, SE), lauks iOS neizskatās pēc kontakta (AutoFill)",
         devices=["iphone14", "iphone-se", "desktop"], fast=True, fast_devices=["iphone14", "iphone-se"]),
    dict(id="s86", file="suites/s86_menu_full_height_v35.py", title="V35 Vraja 1226/1319: «Содержание» pilnā augstumā, apakšējā josla plūstoši aizbrauc lejā (vāks, nodaļa, Lente), aptumšojums līdz apakšai, aizverot josla atgriežas",
         devices=["iphone14", "pixel7", "desktop"], fast=True, fast_devices=["iphone14", "pixel7"]),
    # V45 (Vraja Lila msg 6178–6191 / nodots 1412, 22.10.2026) replaces s83 (V37 name → section page), s85 (V38b only the
    # top bar on the cover) and s91 (V39 «В этом разделе»): those rules are cancelled by Vraja Lila.
    dict(id="s97", file="suites/s97_section_row_one_button_v45.py", title="V45 Vraja 6178/6191 (nodots 1412): sadaļas rinda «Содержании» = VIENA poga (pieskāriens jebkur izvērš/sakļauj, nekur neved, lasīšanas vieta nemainās, ▸ tikai ikona); sadaļu lapu un «В этом разделе» nav; Назад/Вперёд — nodaļa→nodaļa pa «Содержание» secību; viena izceltā rinda, «… · N %»; vākā apakšējā josla tikai ar «Вперёд ›» → lapa pēc vāka, tur «‹ Назад» (vāks) un «Вперёд ›»; «Лента» secība = «Содержание» — Lapas un Lente × iPhone 14 / dators",
         devices=["iphone14", "desktop"], fast=True, fast_devices=["iphone14"]),
    dict(id="s87", file="suites/s87_section_row_one_highlight_v38c.py", title="V38c Vraja 1321/1322: izceltā sadaļa izvēlnē — VIENS vienlaidu fons visai rindai (nosaukums + bultiņa ▸), arī pieskāriena izgaismojumā",
         devices=["iphone14", "pixel7", "desktop"], fast=True, fast_devices=["iphone14", "pixel7"]),
    dict(id="s89", file="suites/s89_pill_master_v40.py", title="V40 Vraja 6091–6094/6103: pārslēdzēja poga = viens master elements (design-system/Pill): fiksēts izmērs atvērta/aizvērta, mainās tikai krāsa/fons, bultiņa griežas vienmērīgi ap centru (panta čipi, «Настроение Гурудева»)",
         devices=["iphone14", "pixel7", "desktop"], fast=True, fast_devices=["iphone14", "pixel7"]),
    dict(id="s81", file="suites/s81_wcag_v33.py", title="V33 Vraja 5865/5900–5907 (variants B): WCAG 2.1 AA — viens akcenta tonis --ap-gold #965700 / tumšajā #E3A03C, kontrasti (teksts 4.5, ikonas/rāmji/fokuss 3) visos fonos, ikona = vārds, josla «Установить» balts teksts, ✕ zonas 44×44, fokuss «Содержание» ar tastatūru",
         devices=["iphone14", "pixel7", "desktop"], fast=True, fast_devices=["iphone14", "desktop"]),
    dict(id="s105", file="suites/s105_transkripti7.py", title="Satkirti msg 6417 (23.10) «Убрать из книги, но сохрани у себя»: 7 расшифровок-сирот ārā no public/transcripts/ un lib/transcripts.json, atlikušie ieraksti = faili, kopijas arhīvā",
         devices=None, fast=True, server=False),
    dict(id="s99", file="suites/s99_one_gold_v47.py", title="V47 Vraja (nodots 22.10 22:31) «цвета варианта B не везде»: VIENS zelts — josla «Saving to your phone», ❀ starp pantiem un visi rotājumi = tokens --ap-gold (variants B) baltajā/sēpijas/nakts tēmā; vecais zelts (#D4A843/#B8860B/#8B6508/#E8B04A) nekur — computed visiem elementiem (vāks, Maṅgalācaraṇa, Парампара, Распорядок, stāvokļu zondes, transkripts) + ielādētais CSS + avoti",
         devices=["iphone14", "pixel7", "desktop"], fast=True, fast_devices=["iphone14", "desktop"]),
    dict(id="s102", file="suites/s102_true_italic_v49.py", title="V49 Vraja 6363/6364 «big да»: Noto Serif ĪSTS kursīvs savā nogriezumā — kursīvos elementos (IAST pants, avots, RU sanskrits) ielādēts mūsu italic woff2, katra zīme no ielādētas italic sejas (Chromium: platformas fonts = Noto Serif Italic, ne sintētisks), Google Noto Serif netiek lejupielādēts; offline precache bez 8 Google rezerves failiem; kursīvā nogriezumā tās pašas zīmes, kas taisnajā, un visas grāmatas zīmes (fontTools)",
         devices=["iphone14", "pixel7", "desktop"], fast=True, fast_devices=["iphone14", "desktop"]),
    dict(id="s103", file="suites/s103_legacy_cleanup_v50.py", title="V50 Vraja 6368/6369/6370 «почисти»: legacy tīrīšana — 2 neizmantotie attēli (conch-shankha, frame-red-cartouche) ārā no public/ (oriģināli archive/), neviens cits attēls neaiztikts; offline precache bez PNG/JPG kopijām attēliem, kurus lapas rāda WebP, un bez nenosauktiem attēliem (faili paliek public/); lapas tos neielādē, offline visi attēli no keša; dead code (INLINE_SA_*, htmlLangFor, .book-cover, --ds-radius-band, lieki export)",
         devices=["desktop", "iphone14"], fast=True, fast_devices=["desktop", "iphone14"]),
    dict(id="s98", file="suites/s98_hint_above_bottom_bar_v46.py", title="V46 Vraja 6321 «Tap empty space to show the menu» zem apakšējā paneļa: vienreizējais padoms VISĀ augstumā virs apakšējā paneļa (panelis ārā un paslēpts, katrā paneļa kustības kadrā), «Страницы» + «Лента», en «Maṅgalācaraṇa» + ru-iast; kustībā necaurspīdīgs («Solid while moving»)",
         devices=["iphone14", "pixel7", "desktop"], fast=True, fast_devices=["iphone14", "pixel7"]),
    dict(id="s96", file="suites/s96_bars_opaque_while_moving_v44.py", title="V44 Vraja 22.10 «фон панели полупрозрачный при выезде — сквозь Back/Forward просвечивает текст»: augšējā/apakšējā josla un «Содержание» katrā kustības kadrā NECAURSPĪDĪGAS (tikai transform, bez opacity), en «Maṅgalācaraṇa» + ru-iast",
         devices=["iphone14", "pixel7", "desktop"], fast=True, fast_devices=["iphone14", "pixel7"]),
    dict(id="s95", file="suites/s95_bookmark_autofill_v43.py", title="V43 Vraja 22.10 «autofill пока вижу»: grāmatzīmes lauks iOS neizskatās pēc kontakta — name/id bez domuzīmes un kontakta vārda (name=search), bez placeholder, autocomplete off, etiķete/virsraksts ar U+200D starp burtiem (lasāms teksts nemainīts); TIKAI atribūti — īstā iPhone pārbaude Vrajam",
         devices=["iphone14", "desktop"], fast=True, fast_devices=["iphone14"]),
    dict(id="s93", file="suites/s93_one_focus_frame_v43.py", title="V43 Vraja 22.10 «двойные рамки всё ещё там (на поиске тоже)»: fokusā VIENA rāmja līnija visur (border+ring / border+outline nav), lauki (grāmatzīme, meklēšana) — viena zelta 2 px līnija; fokusa krāsa = --ap-gold (design-system --ds-focus)",
         devices=["iphone14", "desktop"], fast=True, fast_devices=["iphone14", "desktop"]),
    dict(id="s94", file="suites/s94_panels_close_smooth_v43.py", title="V43 Vraja 22.10 «задвигаются обратно дёргано и мерцают»: joslas slēpjas ar to pašu transition kā parādās, viena virziena kustība; «Содержание» aizveras ar savu ap-menu-out (forwards, ease, 220 ms) un pazūd tikai PĒC animācijas beigām; apakšējā josla atgriežas vienreiz",
         devices=["iphone14", "pixel7", "desktop"], fast=True, fast_devices=["iphone14", "pixel7"]),
    dict(id="s46", file="suites/s46_l21_field.py", title="L21 lauks ap figūru (noteikums 105): ≥ 1,5 % ovāla platuma — 1,0 % un ārpus krīt, 1,6 % iet (temp kopijas)",
         devices=None, fast=True, server=False),
    dict(id="s108", file="suites/s108_a110_spelling_four_words.py", title="A110 Satkirti msg 6501/6502: rakstība viśrāma, vyajana, puṣpāṇi, nityānandāya visās valodās (Method of Worship 2); vecās formas nav, jaunās ir; viśramya nemainīts",
         devices=None, fast=True, server=False),
    dict(id="s107", file="suites/s107_edge_bars_stay_v55.py", title="V55 Vraja 1728/1730 «ВАЖНО»: nodaļas SĀKUMĀ un BEIGĀS (ritinot līdz malai) abas joslas izbrauc un PALIEK — 10× sākums un beigas, «Страницы» un «Лента», pirksts + inerce (garš metiens >1,5 s) + iPhone rubber-band",
         devices=["iphone14", "pixel7"], fast=False),
    dict(id="s21", file="suites/s21_offline_deploy.py", title="OFFLINE pēc jauna deploy: vecais kešs strādā līdz jaunais pilns",
         devices=["pixel7", "desktop"], fast=False, server=False),
    dict(id="s45", file="suites/s45_scroll_option.py", title="A89: «Аа» «Страницы / Лента» — noklusējums lapas, režīms saglabājas pēc pārlādes, pārslēdzot vieta nezūd",
         devices=["iphone14", "ipad-portrait", "pixel7", "desktop"], fast=True, fast_devices=["iphone14", "pixel7"]),
    dict(id="s40", file="suites/s40_chapter_during_update.py", title="КСВ 15.10 iPad: grāmata saglabāta → jauns izlaidums, lēns tīkls → nodaļa ≤2 s, teksta labojums lejupielādē tikai mainīto",
         devices=["ipad-portrait", "iphone14"], fast=False, server=False),
    dict(id="s92", file="suites/s92_update_reaches_open_book.py", title="КСВ 22.10 iPad (S msg 6133 «не вижу Заключение»): saglabāta grāmata + jauns izlaidums, lēns tīkls (pirmais baits 4 s) → 2. reload / atvērta no jauna / atgriezta no fona rāda jauno versiju (≤60 s), negaidot visu lejupielādi",
         devices=["ipad-portrait"], fast=False, server=False),
    dict(id="s109", file="suites/s109_two_languages.py", title="S 23.10 Padomnieks 934–941 «Оставляю два языка: английский и русский… оставить версию с IAST»: valodu izvēlnē tikai English + Русский (ru-iast); /ru/… → /ru-iast/…, /de/ /lv/ /uk/… → angliski (hash saglabāts), saglabātā izņemtā valoda → en/ru-iast; izņemtās valodas nav būvētas (nav meklēšanas indeksa, nav offline), dati saglabāti",
         devices=["iphone14", "pixel7", "desktop"], fast=True, fast_devices=["iphone14", "desktop"]),
    dict(id="s110", file="suites/s110_splash_logo_smaller_v53.py", title="V53 Vraja Lila msg 6433: заставка — красное лого на мобильной на 15 % меньше (200 → 170 px), по центру, neapgriezts, animācija nesalauzta; planšete/dators nemainīti (200 px)",
         devices=["iphone14", "pixel7", "ipad-portrait", "desktop"], fast=True, fast_devices=["iphone14", "pixel7"]),
    dict(id="s111", file="suites/s111_night_tokens_v54.py", title="V54 Враджа Лила msg 1714 (DS V1.1 §7): ночью --ds-row-lit = --ap-band-toc; карточка «Saving to your phone» — только токены",
         devices=["iphone14", "desktop"], fast=True, fast_devices=["iphone14", "desktop"]),
    dict(id="s112", file="suites/s112_numbered_verses_a120.py", title="A120 S msg 6787/6793/6803 «По середине строки над стихом жирную»: apakšnodaļā ar \"numbered\": true (Шри Дамодараштака) virs katra panta numurs 1…8 — centrā, trekns, ≈1,15×; A121 msg 6826: visas dziesmas ar ≥3 pantiem numurētas, ar 1–2 — ne (en, ru-iast)",
         devices=["iphone14", "pixel7", "desktop"], fast=True, fast_devices=["iphone14", "pixel7"]),
    dict(id="s113", file="suites/s113_arati_part_a121.py", title="A121 S msg 6811/6812/6817/6818/6824 + 6826 + 6828: раздел «Арати» (Мангала-арати, Раджа-бхога-арати, Гаура-арати, Картика, Ямунаштака, Джхулана-ятра); dziesmas ≥3 panti numurētas, 1–2 ne; «Джая-дхвани» bez перевода/пословно",
         devices=["iphone14", "desktop"], fast=True, fast_devices=["iphone14"]),
]


# Day release of book TEXT (Padomnieks 2026.10.23_1609, S msg 946 + Gurudas msg 952) — chosen only by
# --changed-from (or --suites s200 + QA_SECTIONS); never part of the full / fast lists.
NODALAS_SUITE = dict(id="s200", file="suites/s200_changed_sections.py",
                     title="S dienas izlaidums: mainītās sadaļas atveras, virsraksti/apakšnodaļas/teksts = dati, nekas neiziet ārā, attēli, bez kļūdām (iPhone 14, iPad, dators)",
                     devices=["iphone14", "ipad-portrait", "desktop"], fast=False,
                     fast_devices=["iphone14", "ipad-portrait", "desktop"])


def changed_plan(base):
    """(suite ids or None, why) for --changed-from: None = the unchanged --fast gate."""
    import changed  # qa/lib/changed.py
    r = changed.classify(qa.REPO, base)
    if r["mode"] != "nodalas":
        return None, r
    ids = ["lint"] + (["s200"] if r["sections"] else []) + r["suites"]
    # the Satkirti rule checks on the data (no browser) — cheap, so every day release keeps them
    ids += [s["id"] for s in SUITES if s["devices"] is None and not s.get("server", True) and s["fast"] and s["id"] != "lint"]
    seen = set()
    return [x for x in ids if not (x in seen or seen.add(x))], r


def load_rules():
    p = os.path.join(HERE, "likumi.json")
    return json.load(open(p, encoding="utf-8"))["rules"] if os.path.exists(p) else []


def matches(ref, suite, name):
    s, _, prefix = ref.partition(":")
    return s == suite and name.startswith(prefix)


def jobs_for(suites, mode_fast, dev_filter, split):
    jobs = []
    for s in suites:
        devs = s["devices"]
        if devs is not None:
            devs = [d for d in devs if (dev_filter is None or d in dev_filter)]
            if mode_fast and dev_filter is None:
                # fast_devices: a suite may run on more than the two phones in the pre-push run
                # (v7.5, КСВ 07.10: the Contents rules on phone + tablet + computer every push)
                devs = [d for d in devs if d in s.get("fast_devices", qa.FAST_DEVICES)]
            if not devs:
                continue
            groups = [[d] for d in devs] if split else [devs]
        else:
            groups = [None]
        for i, g in enumerate(groups):
            # One Contents mode (Satkirti 13.10.2026): the two-tap mode was
            # removed from the app, so nothing is run against it any more.
            for toc_mode in (("default",) if s["id"] in TOC_MODE_SUITES else (None,)):
                jobs.append(({**s, "toc_mode": toc_mode}, g, i == 0))
    return jobs


def kill_tree(pid):
    """Stop ONE process this run started, with its children, BY PID.
    Never by image name (taskkill /IM python.exe / Stop-Process -Name python* would stop
    other sessions' work on this computer — incident 06.10 21:28)."""
    if os.name == "nt":
        subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    else:
        try:
            os.kill(pid, 9)
        except OSError:
            pass


def run_job(job, base, mode_fast, timeout):
    s, devs, first = job
    env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1")
    env.pop("ONLY", None)
    if s.get("toc_mode"):
        env["QA_TOC_MODE"] = s["toc_mode"]
    else:
        env.pop("QA_TOC_MODE", None)
    if devs:
        env["QA_DEVICES"] = ",".join(devs)
    if mode_fast:
        env["QA_FAST"] = "1"
        env.update(s.get("env_fast", {}))
    if not first:
        env["QA_DATA_CHECKS"] = "0"  # data-only checks (s07) once per run
    cmd = [sys.executable, "-u", os.path.join(HERE, s["file"])]
    if s.get("server", True):
        cmd.append(base)
    cmd += s.get("args", [])
    tag = s["id"] + ("-" + "+".join(devs) if devs else "")
    if s.get("toc_mode"):
        tag += "-" + s["toc_mode"]
    log = os.path.join(RESULTS, tag + ".log")
    t0 = time.time()
    p = subprocess.Popen(cmd, env=env, cwd=qa.REPO, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    try:
        raw, _ = p.communicate(timeout=timeout)
        out, rc = raw.decode("utf-8", "replace"), p.returncode
    except subprocess.TimeoutExpired:
        kill_tree(p.pid)  # ONLY our own job (its PID + its children = its browsers), never by process name
        raw, _ = p.communicate()
        out = (raw or b"").decode("utf-8", "replace") + f"\n  [FAIL] {tag} TIMEOUT after {timeout}s\n"
        rc = -9
    open(log, "w", encoding="utf-8").write(out)
    checks = []
    for line in out.splitlines():
        m = LINE.match(line)
        if m:
            checks.append(dict(suite=s["id"], dev=m.group(2), status=m.group(1), name=m.group(3).strip()))
    kp = os.path.join(HERE, "known_failures.json")
    known = json.load(open(kp, encoding="utf-8"))["known"] if os.path.exists(kp) else []
    for c in checks:
        if c["status"] == "FAIL":
            k = next((k for k in known if matches(k["test"], c["suite"], c["name"])), None)
            if k:
                c["status"], c["known"] = "KNOWN", k["reason"]
    counted = [c for c in checks if c["status"] in ("PASS", "FAIL", "KNOWN")]
    if not counted:
        checks.append(dict(suite=s["id"], dev=tag, status="FAIL", name=f"suite produced no checks (rc={rc}), see {os.path.relpath(log, qa.REPO)}"))
    elif rc != 0 and not any(c["status"] == "FAIL" for c in checks):
        checks.append(dict(suite=s["id"], dev=tag, status="FAIL", name=f"suite crashed (rc={rc}), see {os.path.relpath(log, qa.REPO)}"))
    return dict(suite=s["id"], devices=devs, toc_mode=s.get("toc_mode"), rc=rc, secs=round(time.time() - t0, 1), log=os.path.relpath(log, qa.REPO), checks=checks)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--fast", action="store_true", help="pre-push: pixel7 + iphone14, galvenie scenāriji")
    ap.add_argument("--suites", help="komatiem: lint,s07,s071 …")
    ap.add_argument("--suites-skip", help="komatiem: scenāriji, ko izlaist (pre-push: lint jau palaists)")
    ap.add_argument("--devices", help="komatiem: pixel7,iphone14,ipad-portrait …")
    ap.add_argument("--jobs", type=int, default=max(2, min(6, (os.cpu_count() or 4) - 2)))
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--changed-from", metavar="REF", help="nodaļu režīms, ja pret REF mainīts tikai grāmatas teksts; citādi = --fast")
    a = ap.parse_args()
    if a.list:
        for s in SUITES + [NODALAS_SUITE]:
            print(f"{s['id']:6s} {'fast ' if s['fast'] else '     '} {s['title']}  [{', '.join(s['devices'] or ['—'])}]")
        return 0
    label = None
    if a.changed_from:
        try:
            ids, plan = changed_plan(a.changed_from)
        except Exception as e:  # cannot tell what changed → the safe side
            ids, plan = None, dict(reason=f"diff pret {a.changed_from} nav nolasāms ({str(e)[:120]})", sections=[])
        a.fast = True
        if ids is None:
            print(f"QA režīms: pilnie vārti (--fast) — {plan['reason']}", flush=True)
        else:
            label = "nodalas"
            a.suites = ",".join(ids)
            if a.suites_skip:  # pre-push runs lint itself first
                ids = [x for x in ids if x not in a.suites_skip.split(",")]
            os.environ["QA_SECTIONS"] = ",".join(plan["sections"])
            NODALAS_SUITE["timeout_fast"] = 120 + 20 * len(plan["sections"])
            print(f"QA režīms: NODAĻAS — {plan['reason']}; sadaļas: {', '.join(plan['sections']) or '—'}; testi: {', '.join(ids)}", flush=True)
    os.makedirs(RESULTS, exist_ok=True)
    for f in os.listdir(RESULTS):
        # only the suite logs of the previous run (not build.log / push.log of the hook)
        if f.endswith(".log") and (f.split("-")[0].split(".")[0] in {s["id"] for s in SUITES}):
            os.remove(os.path.join(RESULTS, f))
    if not os.path.exists(os.path.join(qa.OUT, "precache-manifest.json")):
        print("out/ nav uzbūvēts — vispirms: npm run build")
        return 2
    stale, which = qa.out_is_stale()
    if stale:
        print(f"BRĪDINĀJUMS: out/ ir vecāks par avotu ({os.path.relpath(which, qa.REPO)}) — testē VECO būvējumu. Palaid: npm run build")
    suites = SUITES
    if a.suites:
        want = a.suites.split(",")
        suites = [s for s in SUITES + [NODALAS_SUITE] if s["id"] in want]
    elif a.fast:
        suites = [s for s in SUITES if s["fast"]]
    if a.suites_skip:
        suites = [s for s in suites if s["id"] not in a.suites_skip.split(",")]
    # A suite with "skip" (a reason) is not run — e.g. it checks only languages removed from the book
    # (S 23.10 Padomnieks 934–941); kept in the list, so it comes back by deleting "skip".
    for s in [s for s in suites if s.get("skip")]:
        print(f"  SKIP {s['id']}: {s['skip']}", flush=True)
    suites = [s for s in suites if not s.get("skip")]
    devf = a.devices.split(",") if a.devices else None
    jobs = jobs_for(suites, a.fast, devf, split=True)
    # longest first (better packing)
    weight = {"s23": 9, "s24": 9, "s071": 10, "s10": 10, "s11": 10, "s21": 10, "s07": 9, "s01": 8, "s20wk": 7, "s06": 6, "s03": 5, "s04": 5, "s05": 4}
    jobs.sort(key=lambda j: -weight.get(j[0]["id"], 2))
    srv = qa_server.Server().start()
    mode = label or ("fast" if a.fast else "full")
    print(f"QA {mode}: {len(jobs)} darbi, {a.jobs} paralēli, serveris {srv.base} (out/)", flush=True)
    t0 = time.time()
    results = []
    flaky = []
    timeout = 280 if a.fast else 2400
    try:
        with cf.ThreadPoolExecutor(max_workers=a.jobs) as ex:
            futs = {ex.submit(run_job, j, srv.base, a.fast, j[0].get("timeout_fast", timeout) if a.fast else timeout): j for j in jobs}
            for f in cf.as_completed(futs):
                r = f.result()
                results.append(r)
                n_ok = sum(1 for c in r["checks"] if c["status"] == "PASS")
                n_bad = sum(1 for c in r["checks"] if c["status"] == "FAIL")
                print(f"  {'OK  ' if not n_bad else 'FAIL'} {r['suite']:6s} {','.join(r['devices'] or ['-']):28s} {n_ok:4d} pass {n_bad:3d} fail  {r['secs']:6.0f}s", flush=True)
        # one retry of every failed browser job: a real regression fails twice,
        # a timing hiccup under parallel load passes on its own (reported FLAKY)
        retry = [r for r in results if r["suite"] != "lint" and any(c["status"] == "FAIL" for c in r["checks"])]
        if retry:
            print(f"  atkārtoju {len(retry)} kritušos darbus vienu reizi …", flush=True)
            by_key = {(j[0]["id"], tuple(j[1] or []), j[0].get("toc_mode")): j for j in jobs}
            with cf.ThreadPoolExecutor(max_workers=min(a.jobs, len(retry))) as ex:
                futs = {ex.submit(run_job, by_key[(r["suite"], tuple(r["devices"] or []), r.get("toc_mode"))], srv.base, a.fast,
                                  timeout * 2 if a.fast else timeout): r for r in retry}
                for f in cf.as_completed(futs):
                    old, new = futs[f], f.result()
                    n_bad = sum(1 for c in new["checks"] if c["status"] == "FAIL")
                    if not n_bad:
                        flaky.extend(f"{c['suite']} {c['dev']} {c['name'][:160]}" for c in old["checks"] if c["status"] == "FAIL")
                        results[results.index(old)] = new
                    else:
                        new["retried"] = True
                        results[results.index(old)] = new
                    print(f"  {'OK  ' if not n_bad else 'FAIL'} {new['suite']:6s} {','.join(new['devices'] or ['-']):28s} (atkārtoti) {n_bad:3d} fail", flush=True)
    finally:
        srv.stop()
    checks = [c for r in results for c in r["checks"]]
    known_hits = [c for c in checks if c["status"] == "KNOWN"]
    fails = [c for c in checks if c["status"] == "FAIL"]
    passes = [c for c in checks if c["status"] == "PASS"]
    skipped = [c for c in checks if c["status"] == "SKIP"]
    rules = load_rules()
    broken = []
    for r in rules:
        hit = [c for c in fails if any(matches(t, c["suite"], c["name"]) for t in r.get("tests", []))]
        if hit:
            broken.append((r, hit))
    dur = time.time() - t0
    json.dump(dict(mode=mode, finished=time.strftime("%Y-%m-%d %H:%M:%S"), seconds=round(dur), jobs=results,
                   passed=len(passes), failed=len(fails), skipped=len(skipped), known=len(known_hits), flaky=flaky), open(os.path.join(RESULTS, "last.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"\nQA {mode}: {len(passes)} pass, {len(fails)} fail, {len(skipped)} skip, {dur / 60:.1f} min")
    for c in skipped:
        print(f"  SKIP {c['suite']} {c['dev']} {c['name']}")
    if known_hits:
        print(f"KNOWN (zināmas, eskalētas kļūdas no qa/known_failures.json — {len(known_hits)}):")
        for c in known_hits[:10]:
            print(f"  ! {c['suite']} {c['dev']} {c['name'][:120]}")
    if flaky:
        print(f"FLAKY (krita, atkārtojumā izgāja — {len(flaky)}):")
        for x in flaky[:10]:
            print("  ~ " + x)
    for c in fails[:40]:
        print(f"  FAIL {c['suite']} {c['dev']} {c['name'][:220]}")
    if len(fails) > 40:
        print(f"  … +{len(fails) - 40} (qa/.results/last.json)")
    if broken:
        print("\nPārkāptie Satkirti likumi:")
        for r, hit in broken:
            print(f"  {r['id']} {r['text'][:110]}  ({len(hit)} fail)")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
