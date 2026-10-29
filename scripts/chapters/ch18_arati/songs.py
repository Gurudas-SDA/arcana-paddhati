# -*- coding: utf-8 -*-
"""A121 (Satkirti 26.10.2026, msg 6811–6818, 6824): the new songs of the part «Арати».

Texts: «2026.10.26_А121 Тексты для раздела «Арати» (черновик).md» (Липикара, 26.10.2026; Versebase = Śrī Gauḍīya
Gīti-guccha, kksongs.org, bhaktivinodainstitute.org, sanskritdocuments.org). Sources stay here, never in the book
(«Стандарты» 114).

RU «перевод» («Стандарты» 115): «Песенник гаудия-вайшнава», Воронеж 2015 (по «Шри Гаудия-гити-гуччхе»),
verbatim (dash « – » → « — », as in ch16/ch17), PDF pages: «Яшомати-нандана» 50–51, «Джая Радха-Мадхава» 51,
«Шри Ямуна-аштака» 287–290, «Джхула джхуле Радха-Дамодар» 416, «Радхе джхулана падхаро» 416–417.
  * NOT in the songbook: «Jaya Yaśodā-nandana» (Gītāvalī, Viṁśottara-śata-nām 6) — RU translated by Lipikāra from the
    English of bhaktivinodainstitute.org / kksongs.org (marked TR_OWN below).
  * «Джая Радха-Мадхава»: the songbook has «Радхе-Мадхаве» → «Радха-Мадхаве» («Стандарты» 8, lint L1).
EN «translation»: the source's English (draft), verbatim except: Yamunāṣṭakam 5 «she is expertly nourishes» → «she
expertly nourishes»; 4 «Yamunā-devī daughter» → «Yamunā-devī, daughter»; Jaya Rādhā-Mādhava = kksongs' two lines
joined, diacritics added (Kṛṣṇa, Rādhā, Vṛndāvana, Yaśodā, Yamunā).
IAST corrections against the draft: Yaśomatī-nandana 3 «rākhoŵālā» → «rākhowālā» (Institute, kksongs; ŵ = Versebase
typo); Rādhe jhūlana «ḓ» → «ḍ» (font glyph of the edition, as in jaya_dhvani.py ERRATA), «nahī͂» → «nahī̃».
Jaya Rādhā-Mādhava: ONLY the 1st verse (Gītāvalī/kksongs; Versebase's 2nd verse has no checked source — S/L 26.10).
Word-by-word (RU and EN): Lipikāra's, from the source texts and translations («Стандарты» 79).
"""

REFRAIN_RU = "māṁ — меня; punātu — пусть очистит; sarvadā — всегда; aravinda-bandhu-nandinī — дочь друга лотоса (Сурьи, бога Солнца)"
REFRAIN_EN = "māṁ — me; punātu — may she purify; sarvadā — always; aravinda-bandhu-nandinī — the daughter of the friend of the lotus (Sūrya, the sun-god)"
REFRAIN = "māṁ punātu sarvadāravinda-bandhu-nandinī"


def V(sk, wbw_ru, tr_ru, wbw_en, tr_en):
    return {"sanskrit": sk, "wbw_ru": wbw_ru, "tr_ru": tr_ru, "wbw_en": wbw_en, "tr_en": tr_en}


BVT = ("Шрила Бхактивинода Тхакур", "⟦Śrīla Bhaktivinoda Ṭhākura⟧")

SONGS = {
    # ---------------------------------------------------------------- Rāja-bhoga-ārati
    "song-yasomati-nandana": {
        "title": ("Яшомати-нандана", "Yaśomatī-nandana"), "author": BVT,
        "verses": [
            V("yaśomatī-nandana, vraja-vara-nāgara,\ngokula-rañjana kāna\ngopī-parāṇa-dhana, madana-manohara,\nkālīya-damana-vidhāna",
              "yaśomatī-nandana — сын Яшоды; vraja-vara-nāgara — лучший из возлюбленных Враджа; gokula-rañjana — услада Гокулы; kāna — Кана (ласковое имя Кришны); gopī-parāṇa-dhana — сокровище жизни гопи; madana-manohara — пленяющий ум даже Купидона (Мадану); kālīya-damana-vidhāna — покоритель змея Калии",
              "Кришна — любимый сын Яшоды и возлюбленный девушек Враджа-бхуми. Его ласково называют Кана. Он — услада жителей Гокулы и свет жизни гопи. Он — неисправимый вор, крадущий сердца всех живых существ, и он — покоритель змея Калии.",
              "yaśomatī-nandana — the son of Yaśodā; vraja-vara-nāgara — the best of lovers in Vraja; gokula-rañjana — the delight of Gokula; kāna — Kāna (an affectionate name of Kṛṣṇa); gopī-parāṇa-dhana — the wealth of the lives of the gopīs; madana-manohara — who steals the mind even of Cupid (Madana); kālīya-damana-vidhāna — who chastised the serpent Kāliya",
              "Lord Kṛṣṇa is the beloved son of Mother Yaśodā, the greatest lover in the land of Vraja, the delight of Gokula, He is intimately addressed as Kāna, and is the wealth of the lives of the gopīs. He steals the mind of even Cupid and punishes the Kāliya serpent."),
            V("amala harināma amiya-vilāsā\nvipina-purandara, navīna-nāgara-vara,\nvaṁśī-vadana, suvāsā",
              "amala — чистое; harināma — святое имя Хари; amiya-vilāsā — исполненное нектарных игр; vipina-purandara — владыка лесов (Враджа); navīna-nāgara-vara — лучший из юных возлюбленных; vaṁśī-vadana — с флейтой у уст; suvāsā — прекрасно одетый",
              "Чистые святые имена Кришны исполнены сладчайшего нектара его лил. Он — царь лесов Враджа и вечно юный влюбленный. Он одевается в великолепные наряды и всегда носит с собой флейту.",
              "amala — pure; harināma — the holy name of Hari; amiya-vilāsā — full of nectarean pastimes; vipina-purandara — the lord of the forests (of Vraja); navīna-nāgara-vara — the best of youthful lovers; vaṁśī-vadana — with the flute at His lips; suvāsā — beautifully dressed",
              "These pure holy names of Lord Hari are full of sweet nectarean pastimes. He is the monarch of the forests of Vṛndāvana, and the foremost of young paramours. He is always playing on a flute, and He is an excellent dresser."),
            V("vraja-jana-pālana, asura-kula-nāśana,\nnanda-godhana-rākhowālā\ngovinda, mādhava, navanīta-taskara,\nsundara nanda-gopālā",
              "vraja-jana-pālana — защитник жителей Враджа; asura-kula-nāśana — истребитель родов демонов; nanda-godhana-rākhowālā — пастух коров Нанды; govinda — Говинда (дарующий радость коровам); mādhava — Мадхава (супруг богини удачи); navanīta-taskara — воришка масла; sundara — прекрасный; nanda-gopālā — пастушок, сын Нанды",
              "Он защищает жителей Враджа, убивает демонов и пасет коров махараджи Нанды. Он — Говинда, дарующий наслаждение Земле, коровам, гопам, гопи и чувствам. Он — Мадхава, господин изначальной богини удачи Шримати Радхики, и воришка масла у жителей Враджа. Он — очаровательный пастушок, сын махараджи Нанды.",
              "vraja-jana-pālana — the protector of the people of Vraja; asura-kula-nāśana — the destroyer of the demon dynasties; nanda-godhana-rākhowālā — the keeper of Nanda’s cows; govinda — Govinda (who gives pleasure to the cows); mādhava — Mādhava (the husband of the goddess of fortune); navanīta-taskara — the butter thief; sundara — beautiful; nanda-gopālā — the cowherd boy of Nanda",
              "Kṛṣṇa is the protector of the inhabitants of Vraja, the destroyer of various demonic dynasties, the keeper and tender of Nanda Mahārāja’s cows, the giver of pleasure to the cows, the husband of the goddess of fortune, the butter thief, and the beautiful cowherd boy of Nanda Mahārāja."),
            V("yāmuna-taṭa-cara, gopī-vasana-hara,\nrāsa-rasika kṛpāmaya\nśrī rādhā-vallabha, vṛndāvana-naṭavara,\nbhakativinoda āśraya",
              "yāmuna-taṭa-cara — гуляющий по берегу Ямуны; gopī-vasana-hara — похищающий одежды гопи; rāsa-rasika — наслаждающийся танцем раса; kṛpāmaya — исполненный милости; śrī rādhā-vallabha — возлюбленный Шри Радхи; vṛndāvana-naṭavara — лучший танцор Вриндавана; bhakativinoda — Бхактивиноды; āśraya — прибежище",
              "Гуляя по берегу Ямуны, он крадет одежды у юных гопи. Он наслаждается танцем раса. Он — средоточие милости, возлюбленный Шримати Радхики и самый искусный танцор во всём Вриндаване. Он — единственное прибежище Бхактивиноды.",
              "yāmuna-taṭa-cara — who wanders on the bank of the Yamunā; gopī-vasana-hara — who steals the garments of the gopīs; rāsa-rasika — who relishes the rāsa dance; kṛpāmaya — full of mercy; śrī rādhā-vallabha — the beloved of Śrī Rādhā; vṛndāvana-naṭavara — the best dancer of Vṛndāvana; bhakativinoda — of Bhaktivinoda; āśraya — the shelter",
              "Kṛṣṇa wanders along the banks of the river Yamunā, He steals the garments of the young damsels of Vraja, and delights in the mellows of the rāsa dance. He is very merciful, the beloved of Śrīmatī Rādhārāṇī, the great dancer of Vṛndāvana, and the refuge of Bhaktivinoda."),
        ]},
    "song-jaya-yasoda-nandana": {
        "title": ("Джая Яшода-нандана", "Jaya Yaśodā-nandana"), "author": BVT, "TR_OWN": True,
        "verses": [
            V("jaya yaśodā-nandana kṛṣṇa gopāla govinda\njaya madana-mohana hare ananta mukunda",
              "jaya — слава; yaśodā-nandana — сыну Яшоды; kṛṣṇa — Кришне; gopāla — пастушку; govinda — Говинде (дарующему радость коровам); jaya — слава; madana-mohana — Мадана-мохану (очаровывающему Купидона); hare — Хари (устраняющему всё неблагоприятное); ananta — Безграничному; mukunda — Мукунде (дарующему освобождение)",
              "Слава Кришне, сыну матушки Яшоды, пастушку, дарующему радость коровам! Слава Хари, покорителю Купидона, устраняющему всё неблагоприятное, Безграничному, дарующему освобождение!",
              "jaya — all glories; yaśodā-nandana — to the son of Yaśodā; kṛṣṇa — to Kṛṣṇa; gopāla — the cowherd boy; govinda — Govinda (who gives pleasure to the cows); jaya — all glories; madana-mohana — to Madana-mohana (the enchanter of Cupid); hare — Hari (who takes away all inauspiciousness); ananta — the unlimited; mukunda — Mukunda (the giver of liberation)",
              "All glories to Kṛṣṇa, the son of Mother Yaśodā, the cowherd boy and giver of pleasure to the cows! All glories to the conqueror of Cupid, Lord Hari, who takes away all inauspiciousness, who is unlimited, and the awarder of liberation!"),
            V("jaya acyuta mādhava rām bṛndābana-candra\njaya muralī-vadana śyāma gopī-janānanda",
              "jaya — слава; acyuta — Непогрешимому; mādhava — Мадхаве (супругу богини удачи); rām — Раме (высшему наслаждающемуся); bṛndābana-candra — луне Вриндавана; jaya — слава; muralī-vadana — держащему флейту у уст; śyāma — Шьяме (цветом подобному тёмной дождевой туче); gopī-janānanda — блаженству гопи",
              "Слава Непогрешимому Господу, супругу богини удачи, высшему наслаждающемуся, луне Вриндавана! Слава Кришне, который всегда держит у уст флейту, цветом подобному тёмной дождевой туче, блаженству гопи!",
              "jaya — all glories; acyuta — to the infallible Lord; mādhava — Mādhava (the husband of the goddess of fortune); rām — Rāma (the supreme enjoyer); bṛndābana-candra — the moon of Vṛndāvana; jaya — all glories; muralī-vadana — to Him who holds the flute to His mouth; śyāma — Śyāma (whose colour is that of a dark rain cloud); gopī-janānanda — the bliss of the gopīs",
              "All glories to the infallible Lord, husband of the goddess of fortune, the supreme enjoyer, and the moon of Vṛndāvana! All glories to Kṛṣṇa, who always holds a flute to His mouth, who is the color of a dark blue rain cloud, and is the bliss of the gopīs!"),
        ]},
    "song-jaya-radha-madhava": {
        "title": ("Джая Радха-Мадхава", "Jaya Rādhā-Mādhava"), "author": BVT,
        "verses": [
            V("jaya rādhā-mādhava kuñja-bihārī\ngopī-jana-vallabha giri-vara-dhārī\nyaśodā-nandana, braja-jana-rañjana,\nyāmuna-tīra-vana-cārī",
              "jaya — слава; rādhā-mādhava — Радха-Мадхаве (Мадхаве, возлюбленному Радхи); kuñja-bihārī — наслаждающемуся играми в кунджах; gopī-jana-vallabha — возлюбленному гопи; giri-vara-dhārī — поднявшему лучший из холмов (Говардхан); yaśodā-nandana — сыну Яшоды; braja-jana-rañjana — радующему жителей Враджа; yāmuna-tīra-vana-cārī — гуляющему по лесам на берегу Ямуны",
              "Слава Шри Шри Радха-Мадхаве! Слава возлюбленному гопи! Он поднял холм Говардхан. Он — любимый сын Яшоды и радость жителей Враджа. Он гуляет по лесу вдоль берегов Ямуны и в уединенных кунджах наслаждается обществом прекрасных гопи.",
              "jaya — all glories; rādhā-mādhava — to Rādhā-Mādhava (Mādhava, the beloved of Rādhā); kuñja-bihārī — who enjoys pastimes in the groves; gopī-jana-vallabha — the beloved of the gopīs; giri-vara-dhārī — the holder of the best of hills (Govardhana); yaśodā-nandana — the son of Yaśodā; braja-jana-rañjana — the delight of the people of Vraja; yāmuna-tīra-vana-cārī — who wanders in the forests on the bank of the Yamunā",
              "Kṛṣṇa is the lover of Rādhā. He displays many amorous pastimes in the groves of Vṛndāvana, He is the lover of the cowherd maidens of Vraja, and the holder of the great hill named Govardhana. He is the beloved son of Mother Yaśodā, the delighter of the inhabitants of Vraja, and He wanders in the forests along the banks of the River Yamunā!"),
        ]},
    # ---------------------------------------------------------------- Yamunāṣṭaka
    "song-yamunastakam": {
        "title": ("Шри Ямунаштака", "Śrī Yamunāṣṭakam"), "author": ("Шрила Рупа Госвами", "⟦Śrīla Rūpa Gosvāmī⟧"),
        "verses": [
            V("bhrātur antakasya pattane ’bhipatti-hāriṇī\nprekṣayāti-pāpino ’pi pāpa-sindhu-tāriṇī\nnīra-mādhurībhir apy aśeṣa-citta-bandhinī\n" + REFRAIN,
              "bhrātur — брата; antakasya — Ямараджи (повелителя смерти); pattane — в обители; ’bhipatti-hāriṇī — избавляющая от попадания; prekṣayā — одним своим видом; ati-pāpinaḥ — величайших грешников; api — даже; pāpa-sindhu — из океана грехов; tāriṇī — спасающая; nīra-mādhurībhiḥ — сладостью вод; api — также; aśeṣa-citta — все сердца; bandhinī — пленяющая; " + REFRAIN_RU,
              "Пусть Ямуна-деви, дочь Сурьи, бога Солнца, очистит меня. Любого, кто касается её вод, она спасает от наказания в обители её брата Ямараджи. Увидев её, даже самые отъявленные грешники освобождаются от грехов. Её прекрасные воды пленяют сердце каждого.",
              "bhrātur — of her brother; antakasya — Yamarāja (the lord of death); pattane — in the city; ’bhipatti-hāriṇī — who prevents one from going; prekṣayā — by the sight (of her); ati-pāpinaḥ — the greatly wicked; api — even; pāpa-sindhu — from the ocean of sins; tāriṇī — who delivers; nīra-mādhurībhiḥ — by the sweetness of her waters; api — also; aśeṣa-citta — all hearts; bandhinī — who captivates; " + REFRAIN_EN,
              "Śrī Yamunā-devī prevents one from having to go to the city of her brother, Yamarāja (the lord of death). Simply seeing her delivers even the greatly wicked from an ocean of sins. Her sweet waters captivate everyone’s heart. May Yamunā-devī, daughter of the sun-god, Sūrya-deva [who, in this song, is called Aravinda-bandhu, friend of the lotus], always purify me."),
            V("hāri-vāri-dhārayābhimaṇḍitoru-khāṇḍavā\npuṇḍarīka-maṇḍalodyad-aṇḍajāli-tāṇḍavā\nsnāna-kāma-pāmarogra-pāpa-sampad-andhinī\n" + REFRAIN,
              "hāri — пленительным; vāri-dhārayā — потоком вод; abhimaṇḍita — украсившая; uru-khāṇḍavā — обширный лес Кхандава; puṇḍarīka-maṇḍala — на множестве белых лотосов; udyat — вспархивающих; aṇḍaja-āli — стай птиц; tāṇḍavā — (место) пляски; snāna-kāma — желающего омыться; pāmara — грешника; ugra-pāpa — тяжких грехов; sampat — богатство; andhinī — уничтожающая; " + REFRAIN_RU,
              "Своим потоком, радующим сердце, она украшает обширный лес Кхандава, владение Индры. На белых лотосах, цветущих по её берегам, непрестанно танцуют трясогузки и другие птицы. Одного только желания омыться в её кристально чистых водах достаточно, чтобы избавиться от самых страшных грехов. Пусть же Ямуна-деви, дочь Сурьи, очистит меня!",
              "hāri — charming; vāri-dhārayā — by the current of her waters; abhimaṇḍita — adorning; uru-khāṇḍavā — the vast Khāṇḍava forest; puṇḍarīka-maṇḍala — on the clusters of white lotuses; udyat — rising; aṇḍaja-āli — flocks of birds; tāṇḍavā — (where) dance; snāna-kāma — who desires to bathe; pāmara — of a sinner; ugra-pāpa — of heinous sins; sampat — the wealth; andhinī — who destroys; " + REFRAIN_EN,
              "She adorns Indra’s immense Khāṇḍava Forest with her enchanting current, and upon her blooming white lotuses, birds such as wagtails always dance. (What to speak of bathing,) simply desiring to bathe in her waters frees a sinner from his many heinous sins. May Yamunā-devī, daughter of Sūrya-deva, always purify me."),
            V("śīkarābhimṛṣṭa-jantu-durvipāka-mardinī\nnanda-nandanāntaraṅga-bhakti-pūra-vardhinī\ntīra-saṅgamābhilāṣi-maṅgalānubandhinī\n" + REFRAIN,
              "śīkara — каплей (её воды); abhimṛṣṭa — окроплённых; jantu — живых существ; durvipāka — тяжкие последствия (грехов); mardinī — сокрушающая; nanda-nandana — к сыну Нанды; antaraṅga-bhakti — сокровенной преданности; pūra — поток; vardhinī — усиливающая; tīra-saṅgama — жить на (её) берегах; abhilāṣi — желающим; maṅgala — благо; anubandhinī — дарующая; " + REFRAIN_RU,
              "Достаточно окропить себя лишь каплей её воды, чтобы искупить вину за самое тяжкое преступление. Она усиливает в сердце рагануга-бхакт поток любви к Шри Нанда-нандане и дарует благословения каждому, кто хочет жить на её берегах. Пусть же Ямуна-деви, дочь Сурьи, очистит меня!",
              "śīkara — by a drop (of her water); abhimṛṣṭa — touched; jantu — of living beings; durvipāka — the grievous results (of sins); mardinī — who crushes; nanda-nandana — for the son of Nanda; antaraṅga-bhakti — of intimate devotion; pūra — the current; vardhinī — who increases; tīra-saṅgama — to reside on (her) banks; abhilāṣi — to those who desire; maṅgala — auspiciousness; anubandhinī — who bestows; " + REFRAIN_EN,
              "Touching but a single drop of her water nullifies a person’s most heinous of crimes. She increases the current of rāgānuga-bhakti for Śrī Nanda-nandana and brings auspiciousness to anyone who simply desires to reside on her banks. May Yamunā-devī, daughter of Sūrya-deva, always purify me."),
            V("dvīpa-cakravāla-juṣṭa-sapta-sindhu-bhedinī\nśrī-mukunda-nirmitoru-divya-keli-vedinī\nkānti-kandalībhir indranīla-vṛnda-nindinī\n" + REFRAIN,
              "dvīpa-cakravāla — кругом островов (материков); juṣṭa — почитаемые; sapta-sindhu — семь океанов; bhedinī — пересекающая (не смешиваясь с ними); śrī-mukunda — Шри Мукундой; nirmita — совершаемые; uru — великие; divya-keli — божественные игры; vedinī — знающая; kānti-kandalībhiḥ — сиянием (своих вод); indranīla-vṛnda — множество сапфиров; nindinī — посрамляющая; " + REFRAIN_RU,
              "Ямуна-деви столь могущественна, что в отличие от всех остальных рек никогда не смешивается с океанскими водами, несмотря на то что она пересекает семь гигантских островов и впадает в семь океанов, окружающих эти острова. Она постоянно созерцает удивительные сокровенные лилы Шри Кришны и помогает этим лилам проявиться в сердцах тех, кто находит у нее прибежище. Её темные искрящиеся воды прекраснее драгоценных сапфиров. Пусть же Ямуна-деви, дочь Сурьи, очистит меня!",
              "dvīpa-cakravāla — by the circle of continents; juṣṭa — worshipped; sapta-sindhu — the seven oceans; bhedinī — who passes through (without merging); śrī-mukunda — by Śrī Mukunda; nirmita — performed; uru — great; divya-keli — divine pastimes; vedinī — who knows; kānti-kandalībhiḥ — by the luster (of her waters); indranīla-vṛnda — a host of sapphires; nindinī — who censures; " + REFRAIN_EN,
              "She encircles the seven oceans, which are worshipped by the continents of the Earth. (In other words, she never merges into the seven oceans, as do ordinary rivers.) She is thoroughly acquainted with the divine play of Śrī Mukunda (and thus she makes those pastimes arise in the hearts of those who take shelter of her). The luster of her waters censures a host of blue sapphires. May Yamunā-devī, daughter of Sūrya-deva, always purify me."),
            V("māthureṇa maṇḍalena cāruṇābhimaṇḍitā\nprema-naddha-vaiṣṇavādhva-vardhanāya paṇḍitā\nūrmi-dor-vilāsa-padmanābha-pāda-vandinī\n" + REFRAIN,
              "māthureṇa maṇḍalena — Матхура-мандалой; cāruṇā — прекрасной; abhimaṇḍitā — украшенная; prema-naddha — проникнутого премой; vaiṣṇava-adhva — пути вайшнавов; vardhanāya — в развитии; paṇḍitā — искусная; ūrmi-doḥ — руками-волнами; vilāsa — играя; padmanābha-pāda — стопам Падманабхи (Кришны); vandinī — поклоняющаяся; " + REFRAIN_RU,
              "Украшенная прекрасной Матхура-мандалой, Ямуна-деви пробуждает рагануга-бхакти в сердцах искренних вайшнавов, которые омываются в её водах. Своими нежными волнами, словно руками, она совершает поклонение лотосным стопам Шри Кришны. Пусть же Ямуна-деви, дочь Сурьи, очистит меня!",
              "māthureṇa maṇḍalena — by the land of Mathurā; cāruṇā — enchanting; abhimaṇḍitā — adorned; prema-naddha — saturated with love; vaiṣṇava-adhva — the path of the Vaiṣṇavas; vardhanāya — in nourishing; paṇḍitā — expert; ūrmi-doḥ — with the arms of her waves; vilāsa — playfully; padmanābha-pāda — the feet of Padmanābha (Kṛṣṇa); vandinī — who worships; " + REFRAIN_EN,
              "She is ornamented by the enchanting land of Mathurā-maṇḍala, and she expertly nourishes the Vaiṣṇava path that is saturated with love, the sampradāya of rāgānuga-bhakti. (In other words, she manifests rāgānugā-bhakti in the heart of Vaiṣṇavas who bathe in her waters.) With the playful arms of her waves, she worships Padmanābha Śrī Kṛṣṇa’s lotus feet. May Yamunā-devī, daughter of Sūrya-deva, always purify me."),
            V("ramya-tīra-rambhamāṇa-go-kadamba-bhūṣitā\ndivya-gandha-bhāk-kadamba-puṣpa-rāji-rūṣitā\nnanda-sūnu-bhakta-saṅgha-saṅgamābhinandinī\n" + REFRAIN,
              "ramya-tīra — (на) прекрасных берегах; rambhamāṇa — мычащими; go-kadamba — стадами коров; bhūṣitā — украшенная; divya-gandha-bhāk — источающих божественный аромат; kadamba-puṣpa-rāji — рядами цветущих кадамб; rūṣitā — благоухающая; nanda-sūnu — сына Нанды; bhakta-saṅgha — собрания преданных; saṅgama — встречей; abhinandinī — радующаяся; " + REFRAIN_RU,
              "Живописные берега Ямуны-деви украшены цветущими кадамбовыми деревьями, источающими райское благоухание, и стадами радостно мычащих коров. Видя у своих вод преданных сына махаражи Нанды, она чувствует безмерное счастье. Пусть же Ямуна-деви, дочь Сурьи, очистит меня!",
              "ramya-tīra — (on) her charming banks; rambhamāṇa — mooing; go-kadamba — by herds of cows; bhūṣitā — adorned; divya-gandha-bhāk — bearing celestial fragrance; kadamba-puṣpa-rāji — by rows of kadamba flowers; rūṣitā — perfumed; nanda-sūnu — of the son of Nanda; bhakta-saṅgha — of the assembly of devotees; saṅgama — by the gathering; abhinandinī — who rejoices; " + REFRAIN_EN,
              "Her charming banks are adorned by herds of loudly mooing cows and are perfumed by celestial fragrances emanating from the flowers of rows of kadamba trees. She is overjoyed by the gathering of Śrī Nanda-lāla’s bhaktas [on those banks]. May Yamunā-devī, daughter of Sūrya-deva, always purify me."),
            V("phulla-pakṣa-mallikākṣa-haṁsa-lakṣa-kūjitā\nbhakti-viddha-deva-siddha-kinnarāli-pūjitā\ntīra-gandhavāha-gandha-janma-bandha-randhinī\n" + REFRAIN,
              "phulla-pakṣa — с раскрытыми крыльями; mallikākṣa-haṁsa — лебедей маллика-кша; lakṣa — сотнями тысяч; kūjitā — оглашаемая; bhakti-viddha — пронзёнными преданностью; deva-siddha-kinnara — полубогами, сиддхами и киннарами; āli — сонмами; pūjitā — почитаемая; tīra-gandhavāha — ветерка с (её) берегов; gandha — ароматом; janma-bandha — узы рождений; randhinī — разрывающая; " + REFRAIN_RU,
              "Над её водами раздаются голоса сотен тысяч лебедей, чьи круглые глаза напоминают распустившиеся цветы маллика. Ей выражают почтение полубоги, сиддхи, киннары и люди, полностью посвятившие себя служению Шри Хари. Любой, кого коснется её приятный ветерок, непременно освободится из круговорота рождений и смертей. Пусть же Ямуна-деви, дочь Сурьи, очистит меня!",
              "phulla-pakṣa — with wings spread wide; mallikākṣa-haṁsa — of mallikākṣa swans; lakṣa — by hundreds of thousands; kūjitā — filled with the sounds; bhakti-viddha — pierced by devotion; deva-siddha-kinnara — by devas, siddhas and kinnaras; āli — by hosts; pūjitā — worshipped; tīra-gandhavāha — of the breeze from (her) banks; gandha — by the fragrance; janma-bandha — the bondage of birth; randhinī — who destroys; " + REFRAIN_EN,
              "She is filled with the sounds of hundreds of thousands of sweetly warbling mallikākṣa swans, whose wings are spread wide. She is worshiped by the devas, siddhas, kinnaras, and human beings whose hearts are dedicated to the service of Śrī Hari. The slightest touch of breezes from her banks eradicates the bondage of rebirth. May Yamunā-devī, daughter of Sūrya-deva, always purify me."),
            V("cid-vilāsa-vāri-pūra-bhūr-bhuvaḥ-svar-āpinī\nkīrtitāpi durmadoru-pāpa-marma-tāpinī\nballavendra-nandanāṅgarāga-bhaṅga-gandhinī\n" + REFRAIN,
              "cid-vilāsa — духовным знанием; vāri-pūra — потоком вод; bhūr-bhuvaḥ-svaḥ — (миры) Бхух, Бхувах и Свах; āpinī — наполняющая; kīrtitā — воспетая; api — даже; durmada — неистовых; uru-pāpa — великих грехов; marma — корни; tāpinī — сжигающая; ballavendra-nandana — сына царя пастухов (Кришны); aṅgarāga — благовонными умащениями с тела; bhaṅga — (смытыми) волнами; gandhinī — благоухающая; " + REFRAIN_RU,
              "Неся свои воды через три мира (Бхух, Бхувах и Свах), она дарует их обитателям духовное знание. Тот, кто воспевает её в молитвах, сжигает дотла последствия самых тяжких грехов. Её воды благоухают сандалом с тела Шри Кришны. Пусть же Ямуна-деви, дочь Сурьи, очистит меня!",
              "cid-vilāsa — with transcendental knowledge; vāri-pūra — by the current of her waters; bhūr-bhuvaḥ-svaḥ — (the worlds) Bhūḥ, Bhuvaḥ and Svaḥ; āpinī — who fills; kīrtitā — glorified; api — even; durmada — wild; uru-pāpa — of great sins; marma — the roots; tāpinī — who burns; ballavendra-nandana — of the son of the king of cowherds (Kṛṣṇa); aṅgarāga — by the unguents of the body; bhaṅga — (washed off) by the waves; gandhinī — fragrant; " + REFRAIN_EN,
              "Her currents fill the three worlds—Bhuḥ, Bhuvaḥ, and Svaḥ—with transcendental knowledge (cid-vilāsa). Just uttering her glories burns the greatest deeply rooted sins to ashes. She is supremely fragrant, due to unguents [such as sandal paste and kuṅkuma] coming from the body of Ballavendra-nandana Kṛṣṇa. May Yamunā-devī, daughter of Sūrya-deva, always purify me."),
            V("tuṣṭa-buddhir aṣṭakena nirmalormi-ceṣṭitāṁ\ntvām anena bhānu-putri sarva-deva-veṣṭitām\nyaḥ stavīti vardhayasva sarva-pāpa-mocane\nbhakti-pūram asya devi puṇḍarīka-locane",
              "tuṣṭa-buddhir — с умиротворённым умом; aṣṭakena anena — этой аштакой; nirmala-ūrmi — чистыми волнами; ceṣṭitām — действующую; tvām — тебя; bhānu-putri — о дочь Солнца; sarva-deva — всеми полубогами; veṣṭitām — окружённую; yaḥ — тот, кто; stavīti — прославляет; vardhayasva — умножь; sarva-pāpa-mocane — к освобождающему от всех грехов; bhakti-pūram — поток преданности; asya — его; devi — о богиня; puṇḍarīka-locane — к лотосоокому (Кришне)",
              "О Сурья-путри! О Деви! О Ямуна! Твои воды могут очистить каждого. Тебе поклоняются все полубоги. Пусть же в сердце того, кто в спокойном состоянии ума повторяет эту молитву, расцветет любовь к лотосоокому Шри Кришне!",
              "tuṣṭa-buddhir — with satisfied intelligence; aṣṭakena anena — with this aṣṭaka; nirmala-ūrmi — by pure waves; ceṣṭitām — acting; tvām — you; bhānu-putri — O daughter of the sun; sarva-deva — by all the demigods; veṣṭitām — surrounded; yaḥ — one who; stavīti — praises; vardhayasva — please increase; sarva-pāpa-mocane — for Him who liberates from all sins; bhakti-pūram — the current of devotion; asya — of that person; devi — O goddess; puṇḍarīka-locane — for the lotus-eyed (Kṛṣṇa)",
              "O Sūryaputri! O Devī! O Yamunā, whose powerful waves are purifying and who is surrounded by all the demigods! For those persons of satisfied intelligence who recite this prayer, please increase their current of bhakti for the lotus-eyed Śrī Kṛṣṇa, who liberates people from all their sins. This is my supplication at your feet."),
        ]},
    # ---------------------------------------------------------------- Jhūlana-yātrā
    "song-jhula-jhule": {
        "title": ("Джхула джхуле Радха-Дамодара", "Jhūlā jhūle Rādhā-Dāmodara"),
        "author": ("Традиционный киртан Враджи", "A traditional kīrtana of Vraja"),
        "verses": [
            V("jhūlā jhūle rādhā-dāmodara vṛndāvana mẽ\nkaisī chāī hariyālī ālī kuñjana mẽ",
              "jhūlā — на качелях; jhūle — качаются; rādhā-dāmodara — Радха и Дамодара; vṛndāvana mẽ — во Вриндаване; kaisī — как (пышно); chāī — раскинулась; hariyālī — зелень; ālī — о подруга; kuñjana mẽ — в кунджах",
              "Радха и Дамодара качаются на качелях во Вриндаване. О подруга, посмотри, как расцвела кунджа!",
              "jhūlā — on the swing; jhūle — swing; rādhā-dāmodara — Rādhā and Dāmodara; vṛndāvana mẽ — in Vṛndāvana; kaisī — how (lush); chāī — has spread; hariyālī — the greenery; ālī — O friend; kuñjana mẽ — in the bowers",
              "Rādhā and Dāmodara are swinging back and forth on a swing in Vṛndāvana. O friend, how lush is the greenery in the forest bowers."),
            V("ita nanda ko dulāro, uta bhānu kī dulārī\njorī lāge ati pyārī basi nainana mẽ",
              "ita — с одной стороны; nanda ko — Нанды; dulāro — любимый сын; uta — с другой стороны; bhānu kī — Вришабхану; dulārī — любимая дочь; jorī — пара; lāge — кажется; ati — очень; pyārī — прекрасной; basi — пребывает; nainana mẽ — в глазах",
              "С одной стороны любимый сын Нанды, а с другой — дорогая дочь махараджи Вришабхану. Оба они так прекрасны! Пусть мой взор всегда будет устремлен на них!",
              "ita — on one side; nanda ko — of Nanda; dulāro — the dear son; uta — on the other side; bhānu kī — of Vṛṣabhānu; dulārī — the dear daughter; jorī — the pair; lāge — appears; ati — very; pyārī — charming; basi — dwells; nainana mẽ — in the eyes",
              "On one side is the dear son of Nanda, on the other side is the dear daughter of Vṛṣabhānu Mahārāja. They appear so charming together. I keep Them within my sight."),
            V("jamunā ke kūla, pahira suraṅga dukūla\ntaise khila rahe phūla in kadamana mẽ",
              "jamunā ke — Ямуны; kūla — на берегу; pahira — надев; suraṅga — яркие; dukūla — одежды; taise — так же; khila rahe — распустились; phūla — цветы; in — на этих; kadamana mẽ — деревьях кадамба",
              "Они гуляют по берегу Ямуны, одетые в чудесные яркие одежды. О подруга, посмотри, как благоухают цветы кадамба!",
              "jamunā ke — of the Yamunā; kūla — on the bank; pahira — wearing; suraṅga — colourful; dukūla — garments; taise — so too; khila rahe — are blossoming; phūla — the flowers; in — on these; kadamana mẽ — kadamba trees",
              "On the bank of the Yamunā, They wear beautiful, colorful garments. Oh, how the flowers are blossoming on these kadamba trees!"),
            V("gaura śyāma raṅga, ghana dāminī ke saṅga\nbhai akhiyā̃ apaṅga chavi bharī mana mẽ",
              "gaura — золотистый; śyāma — тёмный; raṅga — цвет (тел); ghana — грозовая туча; dāminī ke saṅga — вместе с молнией; bhai — стали; akhiyā̃ — глаза; apaṅga — немигающими; chavi — этот образ; bharī — наполнил; mana mẽ — ум",
              "Золотистая Радхика рядом со смуглоликим Кришной напоминает молнию на фоне темного грозового облака. О глаза, не закрывайтесь ни на миг, пусть эта картина навечно останется в моём уме!",
              "gaura — golden; śyāma — dark; raṅga — complexions; ghana — a dark cloud; dāminī ke saṅga — with lightning; bhai — have become; akhiyā̃ — the eyes; apaṅga — unblinking; chavi — this sight; bharī — has filled; mana mẽ — the mind",
              "Their [respective] golden and dark complexions resemble lightning on a dark cloud. This sight fills my mind, and my eyes do not close."),
            V("rādhe mukha aura, naina śyāma ke cakora\nbraja-gopin prema ḍora lagī caraṇana mẽ",
              "rādhe mukha — лица Радхи; aura — к; naina — глаза; śyāma ke — Шьямы; cakora — (подобные) птицам чакора; braja-gopin — враджа-гопи; prema — премы; ḍora — верёвка; lagī — привязана; caraṇana mẽ — к стопам",
              "Лицо Радхики словно луна, а глаза Кришны, как две птицы чакоры (очарованные луной), устремлены на нее. Враджа-гопи веревкой премы связывают вместе лотосные стопы Радхи и Кришны.",
              "rādhe mukha — Rādhā’s face; aura — towards; naina — the eyes; śyāma ke — of Śyāma; cakora — (like) cakora birds; braja-gopin — of the gopīs of Vraja; prema — of prema; ḍora — the rope; lagī — is bound; caraṇana mẽ — to the feet",
              "Rādhā’s face is like the moon and Kṛṣṇa’s eyes, which are like those of a cakora bird, look toward Her. The vraja-gopīs’ prema is a rope binding Rādhā and Kṛṣṇa’s lotus feet."),
        ]},
    "song-radhe-jhulana-padharo": {
        "title": ("Радхе джхулана падхаро", "Rādhe jhūlana padhāro"),
        "author": ("Традиционный киртан Враджи", "A traditional kīrtana of Vraja"),
        "verses": [
            V("rādhe jhūlana padhāro jhuka āye badarā\njhuka āye badarā, ghira āye badarā",
              "rādhe — о Радха; jhūlana — на качели; padhāro — приди; jhuka āye — низко нависли; badarā — тучи; ghira āye — сгустились",
              "Подруги говорят Радхе: «Пойдем покачаемся! Посмотри, набежали дождевые облака. Скоро хлынет дождь. Если ты сейчас же не пойдешь, ты всё пропустишь и потом будешь жалеть об этом. Всё небо в облаках!»",
              "rādhe — O Rādhā; jhūlana — to the swing; padhāro — please come; jhuka āye — have hung low; badarā — the clouds; ghira āye — have gathered",
              "“O Rādhā, go and sit on the swing. Low rain clouds have come and filled the sky."),
            V("aiso māna nahī̃ kīje, haṭha choḍo rī alī\ntum to parama sayānī vṛṣabhānu kī lalī",
              "aiso — такую; māna — обиду (ману); nahī̃ kīje — не держи; haṭha — упрямство; choḍo — оставь; rī alī — о подруга; tum to — ты ведь; parama — весьма; sayānī — разумная; vṛṣabhānu kī — Вришабхану; lalī — дочь",
              "«Перестань сердиться, о сакхи. Не упрямься, ведь ты так разумна, ты же дочь махараджи Вришабхану».",
              "aiso — such; māna — sulkiness (māna); nahī̃ kīje — do not keep; haṭha — stubbornness; choḍo — give up; rī alī — O friend; tum to — You are indeed; parama — highly; sayānī — intelligent; vṛṣabhānu kī — of Vṛṣabhānu; lalī — the daughter",
              "“Give up Your sulky mood, O friend. Don’t be stubborn like this. You are the dear, highly intelligent daughter of King Vṛṣabhānu."),
            V("sājo solah śriṅgāra ḍāro nainana kajarā\npaharo pañca-raṅga sāḍī oḍho śyāma cadarā",
              "sājo — укрась себя; solah — шестнадцатью; śriṅgāra — украшениями; ḍāro — нанеси; nainana — на глаза; kajarā — каджал; paharo — надень; pañca-raṅga — пятицветное; sāḍī — сари; oḍho — накинь; śyāma — тёмную; cadarā — накидку",
              "«Укрась себя шестнадцатью видами украшений, подведи глаза кадджалом. Надень пятицветное сари и тонкую темную накидку».",
              "sājo — decorate Yourself; solah — with sixteen; śriṅgāra — ornaments; ḍāro — apply; nainana — to the eyes; kajarā — kajjal; paharo — put on; pañca-raṅga — five-coloured; sāḍī — sārī; oḍho — cover Yourself; śyāma — dark; cadarā — a veil",
              "“Decorate Yourself with sixteen kinds of ornaments and line your eyes with kajjal. Don your five-colored sārī and cover yourself with a thin, dark veil."),
            V("tero rasika pritama, maga johata khaḍo\nrādhe jahā̃ paga dhāro śyāma nainā dharo",
              "tero — твой; rasika — исполненный вкуса (расы); pritama — возлюбленный; maga — дорогу; johata — высматривая; khaḍo — стоит; rādhe — о Радха; jahā̃ — куда; paga — стопы; dhāro — ставишь; śyāma — Шьям; nainā — глаза; dharo — устремляет",
              "«Твой возлюбленный ждет тебя на тропинке. Сложив молитвенно руки, Шьям готов упасть к твоим ногам».",
              "tero — Your; rasika — playful; pritama — beloved; maga — the path; johata — watching; khaḍo — stands; rādhe — O Rādhā; jahā̃ — wherever; paga — feet; dhāro — You place; śyāma — Śyāma; nainā — eyes; dharo — fixes",
              "“Your playful beloved is waiting for You on the path. O Rādhā, wherever You place Your feet, Śyāma’s eyes follow.”"),
            V("ḍārī reśama ḍorī jāpai jhūle rādhā gorī\njākī baiyā̃ gorī gorī pahare hāthana gajarā",
              "ḍārī — привязаны; reśama — шёлковые; ḍorī — верёвки; jāpai — на которых; jhūle — качается; rādhā — Радха; gorī — золотистая; jākī — чьи; baiyā̃ — руки; gorī gorī — золотистые; pahare — носят; hāthana — на руках; gajarā — браслеты",
              "Шелковые веревки уже завязаны там, где златокожая Радха будет качаться на качелях. На её золотистых руках сверкают изумрудные браслеты.",
              "ḍārī — are hung; reśama — silken; ḍorī — ropes; jāpai — upon which; jhūle — swings; rādhā — Rādhā; gorī — fair; jākī — whose; baiyā̃ — arms; gorī gorī — golden; pahare — wear; hāthana — on the hands; gajarā — floral bracelets",
              "Silken ropes are hung, upon which fair Rādhā is swinging. Her golden arms are decorated with floral bracelets."),
        ]},
}

# the part «Арати» (Satkirti msg 6811–6818): chapter id -> (RU title, EN title, [song ids] for new chapters)
PART = {"id": "arati", "title": ("Арати", "Ārati")}
CHAPTERS = [
    ("mangala-arati-songs", "Мангала-арати", "Maṅgala-ārati", None),
    ("raja-bhoga-arati", "Раджа-бхога-арати", "Rāja-bhoga-ārati",
     ["song-yasomati-nandana", "song-jaya-yasoda-nandana", "song-jaya-radha-madhava"]),
    ("gaura-arati-songs", "Гаура-арати", "Gaura-ārati", None),
    ("kartika-bhajans", "Картика", "Kārtika", None),               # S: «Пиши картика. Без дамодара»
    ("jhulana-yatra-bhajans", "Джхулана-ятра", "Jhūlana-yātrā", ["song-jhula-jhule", "song-radhe-jhulana-padharo"]),
    ("yamunastaka", "Ямунаштака", "Yamunāṣṭaka", ["song-yamunastakam"]),   # A127 msg 6961: after «Джхулана-ятра», the chapter IS the bhajan (FLAT). S: «Ямунаштаку вынеси отдельно»
]
# A127 (msg 6961): chapters that ARE one bhajan — no subsection, the song content and numbering sit in the chapter.
FLAT = {"yamunastaka"}
FESTIVALS = ("festivals-vows", "Праздники и обеты", "Festivals and Vows")   # «песни арати» moved out
