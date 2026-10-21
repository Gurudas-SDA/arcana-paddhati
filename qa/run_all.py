"""Arcana-paddhati regresijas komplekts — viena komanda.

  python qa/run_all.py            pilnais: visi scenāriji, visas ierīces (~30–40 min)
  python qa/run_all.py --fast     ātrais (pre-push): galvenās ierīces, galvenie scenāriji (≤5 min)
  python qa/run_all.py --suites s07,s071 --devices pixel7,ipad-portrait
  python qa/run_all.py --list

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
    dict(id="s32", file="suites/s32_lang_pt_lt.py", title="A73: valodas pt + lt — /pt/ un /lt/ atveras, «Аа» valodu izvēlnē, pilns tulkojums, IAST = EN, nav angļu teikumu, UI atslēgas, offline",
         devices=["pixel7", "iphone14", "desktop"], fast=True, fast_devices=["pixel7", "desktop"]),
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
    dict(id="s51", file="suites/s51_search_field.py", title="Vraja 5316 p.3: meklēšanas lauks 16 px, placeholder #8B6508, fokuss pieskāriena laikā, .mobile-menu[data-open]",
         devices=["iphone14", "pixel7", "desktop"], fast=True, fast_devices=["iphone14", "pixel7"]),
    dict(id="s53", file="suites/s53_fonts_own_cut.py", title="Vraja 5316 p.4: sava fonta nogriezne (taisnais), Google Noto Serif netiek lejupielādēts, preload ≤ 80 KB",
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
    dict(id="s58", file="suites/s58_resume_arrow.py", title="Vraja 5430: «Продолжить чтение» — bultiņa › #8B6508 labajā apakšā, teksts nezem bultiņas, garie nosaukumi 2–3 rindās bez «…», vāks nelēkā",
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
    dict(id="s78", file="suites/s78_bg_dark_all_langs.py", title="V26b Vraja 5817: «Аа» fons «Тёмный» visās valodās nozīmē «tumšs», ne «nakts» (de/es/fr/hu/it/lt/lv/pt/uk + ru); visas V21 pārdēvētās atslēgas visās valodās, vietturi kā RU",
         devices=None, fast=True, server=False),
    dict(id="s75", file="suites/s75_aa_panel_v27.py", title="V27 Vraja 5769–5779: «Аа» panelis — «Язык» pirmā funkcija, logs nav apgriezts, kamēr ekrānā vieta, aiz tā aptumšojums melns 60 % (pieskāriens aizver), valodu sarakstam tie paši 60 % visos fonos (telefoni arī ainavā)",
         devices=["iphone14", "pixel7", "s23fe", "iphone-se", "ipad-portrait", "desktop"], fast=True, fast_devices=["iphone14", "pixel7"]),
    dict(id="s46", file="suites/s46_l21_field.py", title="L21 lauks ap figūru (noteikums 105): ≥ 1,5 % ovāla platuma — 1,0 % un ārpus krīt, 1,6 % iet (temp kopijas)",
         devices=None, fast=True, server=False),
    dict(id="s21", file="suites/s21_offline_deploy.py", title="OFFLINE pēc jauna deploy: vecais kešs strādā līdz jaunais pilns",
         devices=["pixel7", "desktop"], fast=False, server=False),
    dict(id="s45", file="suites/s45_scroll_option.py", title="A89: «Аа» «Страницы / Лента» — noklusējums lapas, režīms saglabājas pēc pārlādes, pārslēdzot vieta nezūd",
         devices=["iphone14", "ipad-portrait", "pixel7", "desktop"], fast=True, fast_devices=["iphone14", "pixel7"]),
    dict(id="s40", file="suites/s40_chapter_during_update.py", title="КСВ 15.10 iPad: grāmata saglabāta → jauns izlaidums, lēns tīkls → nodaļa ≤2 s, teksta labojums lejupielādē tikai mainīto",
         devices=["ipad-portrait", "iphone14"], fast=False, server=False),
]


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
    a = ap.parse_args()
    if a.list:
        for s in SUITES:
            print(f"{s['id']:6s} {'fast ' if s['fast'] else '     '} {s['title']}  [{', '.join(s['devices'] or ['—'])}]")
        return 0
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
        suites = [s for s in SUITES if s["id"] in want]
    elif a.fast:
        suites = [s for s in SUITES if s["fast"]]
    if a.suites_skip:
        suites = [s for s in suites if s["id"] not in a.suites_skip.split(",")]
    devf = a.devices.split(",") if a.devices else None
    jobs = jobs_for(suites, a.fast, devf, split=True)
    # longest first (better packing)
    weight = {"s23": 9, "s24": 9, "s071": 10, "s10": 10, "s11": 10, "s21": 10, "s07": 9, "s01": 8, "s20wk": 7, "s06": 6, "s03": 5, "s04": 5, "s05": 4}
    jobs.sort(key=lambda j: -weight.get(j[0]["id"], 2))
    srv = qa_server.Server().start()
    mode = "fast" if a.fast else "full"
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
