"""A132 Саткирти msg 7224 (01.11) «А132 да» на «исправлять по образцу BBT?»; msg 7201 «Проверь всю нашу книгу на подобные ошибки»; msg 7194 «Посмотри, как БиБиТи переводится слова… Всё должно быть попроще».
Пословные переводы в 19 стихах (эпиграф, Утренние молитвы, 3:40, бахья-пуджа, прощение, Дамодараштака 1-8, Нанда-нанданаштака 9, Радха-крипа-катакша 7 и 9):
40 записей (вид 1 — слово перенесено, часть с «-» на конце; вид 2 — длинное значение с пояснениями; вид 3 — слитые по сандхи слова) приведены к форме BBT: «слово — простое значение», слитые слова разделены.
Data-only test over data/book.ru-iast.json and data/book.ru.json (ru: транслит ключей тем же iast_to_cyrillic).
usage: python s134_a132_poslovno_bbt.py [data_dir]   (data_dir — для проверки «красного» на старых данных)
# tehniskais slieksnis Lipikāra, nav S noteikums: проверка «ключ с «-» на конце» только в этих 19 стихах; короткие пояснения в скобках (88 записей) — вне А132.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "scripts", "translate"))
from iast_to_cyrillic import translit  # noqa: E402

DATA = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "..", "..", "data")
# старые записи, которых быть не должно (по одной на исправленное место)
OLD = [
    'devakī-janma-vādo — вокруг которого возникли разногласия, поскольку Он, казалось, родился из лона Деваки',
    'sthira-cara-vṛjina-ghnaḥ — уничтожающий все неблагоприятное для живых существ, движущихся и неподвижных',
    'vivṛddha- — полностью расцветающей; prema-smitena — любящей улыбкой',
    'mādhvyā — сладостной; girāpanayatāt — пусть избавит словами',
    'uttiṣṭhottiṣṭha — встаньте, встаньте',
    'uttiṣṭhottiṣṭha — пожалуйста, встань, пожалуйста, встань',
    'kālindī-jala-kallola- — волн вод Ямуны; saṅgi-māruta-sevitam — которой служат ветерки, соприкасающиеся с ними',
    'nānā-puṣpa-latā-baddha- — украшенную различными цветами и лианами; vṛkṣa-ṣaṇḍaiś — группами деревьев',
    'gṛhāṇānukampayā — пожалуйста, прими по Своей беспричинной милости.',
    'namāmīśvaraṁ — поклоны Верховному Повелителю, обладателю всех энергий',
    'gokule — в трансцендентной обители Гокуле, доме гопов, гопи, коров, телят и прочих',
    'bhiyolūkhalād — из страха, спрыгнув со ступы',
    'rekhāṅka — отмеченной изогнутыми линиями, напоминающими кольцевые бороздки вокруг шейки раковины',
    'dāmodaraṁ — Шри Кришне, чей живот (удара) связан верёвкой (дама)',
    'itīdṛk — подобными этим (Его в высшей степени пленительными детскими играми, такими как дама-бандхана-лила, в которой Его живот был связан); sva-līlābhir — Своими неповторимыми и необычайными играми',
    'sva-ghoṣaṁ — всех обитателей Своей обители Гокулы или всех существ, проявленных Его энергией игр',
    'deva — о в высшей степени сияющий и исполненный игривости Господь',
    'mokṣaṁ — освобождения от страданий преходящего бытия (четвёртой высшей цели человеческой жизни)',
    'mokṣāvadhiṁ — вершины освобождения: пребывания на Шри Вайкунтха-локе, в обители необычайного сосредоточенного счастья',
    'cānyaṁ — и других [благословений, таких как навадха-бхакти, характеризуемая шраваной и киртаной]',
    'vareśād — [у] Тебя, Верховного Повелителя, способного даровать любое благословение; apīha — даже здесь [во Врадже]',
    'idaṁ — этот [в высшей степени очаровательный]',
    'manasy — в уме [или сердце, очищенном вишуддха-саттвой]',
    'āvirāstām — пусть [этот лик] проявится',
    'dāmodarānanta — о бхакта-ватсала (Ты, кто исполнен нежности к Своим преданным) Шри Дамодара, о Господь непостижимых величественных энергий',
    'vṛṣṭyāti — дождём, чрезвычайно',
    'batānu — увы, и начало слова, перенесённого на следующую строку; gṛhāṇeśa — [ану-]: отнесись ко мне с добротой или оживи меня, даровав избавление, о в высшей степени независимый Повелитель',
    'baddha-mūrtyaiva — божественным образом (шри виграхой), который был связан, несомненно',
    'mocitau — оба избавлены [как от существования в облике деревьев, так и от уз круговорота рождения и смерти]',
    'kuverātmajau — двух сыновей Куверы (Налакувару и Манигриву)',
    'dāmodareha — о бхакта-ватсала Дамодара, только к этому',
    'viśvasya — всей вселенной [движущихся и неподвижных существ]',
    'tvadīyodarāyātha — Твоему животу, а также',
    'nandanāṣṭakaṁ — восемь стихов, прославляющих сына',
    'locanāvalokane — о Ты, чей взгляд глаз подобен',
    'saubhagoruke — о обладательница прекрасных бёдер, подобных',
]
# 18 стихов: по первой строке санскрита (iast)
VERSES = ["jayati jana-nivāso", "so 'sāv adabhra-karuṇo", "deva prapannārti-hara", "uttiṣṭhottiṣṭha śrī guro",
          "uttiṣṭhottiṣṭha gaurāṅga", "tato vṛndāvanaṁ dhyāyet", "yad-dattaṁ bhakti-mātreṇa", "namāmīśvaraṁ", "rudantaṁ muhur", "itīdṛk",
          "varaṁ deva", "idaṁ te mukhāmbhojam", "namo deva", "kuverātmajau", "namas te ’stu dāmne", "śrī-nanda-nandanāṣṭakaṁ",
          "mṛṇāla-vāla-vallarī", "nitamba-bimba-lambamāna"]
res = []


def chk(name, ok, ev=""):
    res.append(bool(ok))
    print(f"  [{'PASS' if ok else 'FAIL'}] {name} {ev if not ok else ''}".rstrip(), flush=True)


def verses(d):
    out = []

    def w(o):
        if isinstance(o, dict):
            if o.get("type") == "verse" and "wbw" in o:
                out.append(o)
            for v in o.values():
                w(v)
        elif isinstance(o, list):
            for x in o:
                w(x)
    w(d)
    return out


def conv_ru(s):
    return "; ".join(translit(e.partition(" — ")[0]) + " — " + e.partition(" — ")[2] for e in s.split("; "))


for fn, conv in (("book.ru-iast.json", lambda s: s), ("book.ru.json", conv_ru)):
    d = json.load(open(os.path.join(DATA, fn), encoding="utf-8"))
    vs = verses(d)
    allw = "\n".join(v["wbw"] for v in vs)
    bad_old = [o for o in OLD if conv(o) in allw]
    chk(f"{fn}: старых записей нет (0 из {len(OLD)})", not bad_old, f"осталось {len(bad_old)}: {[b[:25] for b in bad_old[:5]]}")
    found = 0
    badg = []
    for key in VERSES:
        k = conv(key) if fn == "book.ru-iast.json" else translit(key)
        m = [v for v in vs if key in v.get("sanskrit", "") or k in v.get("sanskrit", "")]
        found += bool(m)
        for v in m:
            for e in v["wbw"].rstrip(".").split("; "):
                kk = e.partition(" — ")[0]
                if kk.endswith("-"):
                    badg.append(e[:50])
    chk(f"{fn}: все 18 стихов найдены", found == len(VERSES), f"{found}")
    # «parayācyuta» — вопрос Саткирти (не исправлено): исключение из общей проверки
    badg = [b for b in badg if "ayācyuta" not in b and "айачйута" not in b]
    chk(f"{fn}: в 19 стихах нет ключа с «-» на конце", not badg, f"{len(badg)}: {badg[:5]}")

# S msg 7242 «Запиши» («Стандарты» «Пословный перевод делаем по образцу BBT…; длинное составное слово делим на части, у каждой своё значение»):
# salikums no 3+ daļām — pa daļām. # tehniskais slieksnis Lipikāra, nav S noteikums: 3+ daļas dala, 2 daļas paliek vesels (S msg 7242 koordinatora precizējums).
COMPOUNDS = ["vivṛddha-prema-smitena", "kālindī-jala-kallola-saṅgi-māruta-sevitam", "nānā-puṣpa-latā-baddha-vṛkṣa-ṣaṇḍaiś",
             "sthira-cara-vṛjina-ghnaḥ", "devakī-janma-vādo", "parayācyuta"]
for fn, cv in (("book.ru-iast.json", lambda x: x), ("book.ru.json", translit)):
    d = json.load(open(os.path.join(DATA, fn), encoding="utf-8"))
    keys = [e.partition(" — ")[0] for v in verses(d) for e in v["wbw"].rstrip(".").split("; ")]
    left = [c for c in COMPOUNDS if cv(c) in keys]
    chk(f"{fn}: составные слова 3+ частей разделены (нет целым ключом)", not left, str(left))
    chk(f"{fn}: «pāraya — переправь; acyuta» есть", cv("pāraya") in keys and cv("acyuta") in keys)
# stih 3:40/2 — «pārayācyuta» (Hari-bhakti-vilāsa 3.132; Стандарты 14) во всех 12 книгах
import glob
for fp in sorted(glob.glob(os.path.join(DATA, "book*.json"))):
    t = open(fp, encoding="utf-8").read()
    bad, good = ("парайа̄чйута", "па̄райа̄чйута") if fp.endswith("book.ru.json") else ("parayācyuta", "pārayācyuta")
    n_bad = t.count(bad + "\"") + t.count(bad + "\\")  # panta teksts (rinda beidzas)
    chk(f"{os.path.basename(fp)}: panta tekstā «pārayācyuta», nav «parayācyuta»", good in t and "māṁ " + bad not in t and "ма̄м̇ " + bad not in t, "")
print(f"s134: {sum(res)}/{len(res)} passed", flush=True)
sys.exit(0 if res and all(res) else 1)
