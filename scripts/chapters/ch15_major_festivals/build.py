# -*- coding: utf-8 -*-
"""Part IV, chapter 15 «Великие праздники» -> data/book*.json; its mood quotes -> scripts/moods/moods.json.
  python build.py translate | apply | moods | fetch      (see ../hand_chapter.py)
After apply / moods: python ../../moods/apply_moods.py, then npm run build.
The section is locked in scripts/translate/locked_sections.json, so tr.py assemble keeps it as written here."""
import os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import hand_chapter as hc  # noqa: E402

SYSTEM = ("You translate a chapter of a Gauḍīya Vaiṣṇava Deity-worship manual from Russian into English for the book "
          "'Arcana-paddhati — The Process of Deity Worship'. Rules: faithful, plain, natural book English; do not add or "
          "omit content. Keep every ⟦…⟧ span exactly as it is. Sanskrit names and terms in English with IAST diacritics, "
          "as in Gauḍīya books: Vyāsa-pūjā, Guru-pūjā, Guru-pūrṇimā, Vyāsa-pūrṇimā, Āṣāḍha, vyāsāsana, guru-paramparā, "
          "guru-varga, pañcaka, sapta-pañcakam, pūjā-pañcaka, Kṛṣṇa-pañcaka, Vyāsa-pañcaka, ācārya-pañcaka, "
          "Sanakādi-pañcaka, guru-pañcaka, upāsya-pañcaka, tattva-pañcaka, Pañca-tattva, kalaśa, kuṅkuma, svastika, "
          "upacāra, pūjārī, puṣpāñjali, parikramā, ārati, bhoga, mahā-prasāda, hari-kathā, Śrīvāsa-aṅgana, Māyāpura, "
          "Govardhana Maṭha, Purī, Puṣkara, Dvārakā, Śrī Gauḍīya-patrikā, Śrī Bhāgavata-patrikā, Śrī Caitanya-bhāgavata, "
          "Śrīmad-Bhāgavatam, Gauḍīya Vedānta Samiti, Śaṅkarācārya, Īśvara Purīpāda, Śrīla Vyāsadeva, Śrī Kṛṣṇa "
          "Dvaipāyana Vedavyāsa, Śrīla Bhaktisiddhānta Sarasvatī Ṭhākura Prabhupāda, Śrīla Bhaktivinoda Ṭhākura, Śrīla "
          "Bhakti Prajñāna Keśava Gosvāmī Mahārāja, Śrīla Bhaktivedānta Nārāyaṇa Gosvāmī Mahārāja, Śrīla A. C. "
          "Bhaktivedānta Svāmī Prabhupāda, Sumantu, Aṅgirā, Atharva Veda. «Гурудев» = «Gurudev» (our spiritual master "
          "Śrī Prem Prayojan Prabhu). Festivals and names: Janmāṣṭamī, Nandotsava, Rādhāṣṭamī, Jhūlana-yātrā, "
          "Naukā-vilāsa, Candana-yātrā, Narendra-sarovara, Rādhā-Madana-mohana, Śrī Śrī Rādhā-Gopīnātha, Mānasī-gaṅgā, "
          "Kusuma-sarovara, Rādhā-kuṇḍa, Ghanaśyāma, mādanākhya-mahābhāva, sakhī, Malhāra and Dhanaśrī rāgas, Vraja-bhāṣā, "
          "cāmara, caraṇāmṛta, abhiṣeka, Ekādaśī prasāda, Pavitropanī Ekādaśī, Śrāvaṇa, Bhādra, Śrīdhara, Hṛṣīkeśa, "
          "Baladeva-pūrṇimā, Rakṣā-bandhana, tirobhāva-tithi, viraha-mahotsava, adhivāsa, Keśavajī Gauḍīya Maṭha, Mathurā, "
          "Nanda-bhavana, Uddhava, Akṣaya-tṛtīyā, rūpānuga. Chapter titles: «Маха-абхишека» → «Maha Abhiseka»; "
          "«Чатурмасья и Пурушоттама-маса» → «Cāturmāsya and Puruṣottama-māsa»; «Шри Гуру-пуджа и Вьяса-пуджа» → "
          "«Śrī Guru-pūjā and Vyāsa-pūjā»; «Великие праздники» → «Major Festivals». Book titles plainly, no quotation marks: «Ачарья Кешари Кешава Госвами. Его жизнь "
          "и учение», М., 2004 → «Ācārya Kesarī Keśava Gosvāmī: His Life and Teachings, Russian edition, Moscow, 2004»; "
          "«англ. изд.» → «English edition (GVP, 2013)» the first time, then «English edition». «лекция № 9643 от "
          "06.07.2025» → «lecture no. 9643, 6 July 2025» (same pattern for all lectures); «с. 105» → «p. 105». Chapter "
          "titles of this book: «Арчана Шри Гуру» → «Arcana of Śrī Guru»; «Храмовый стандарт» → «Temple Standard»; "
          "«Главное поклонение с шестнадцатью упачарами» → «The Main Worship with Sixteen Items». The translation "
          "«Sumantu Muni Aṅgirā» stays in English as is. Russian dates like «6 февраля 2027 г.» → «6 February 2027». "
          "Answer with JSON only.")

TITLES = {
    "9739": "2026.03.02_Gaura-katha part 2",
    "10080": "Shree Krishna Janmashtami 2012 part1, Ticino 2012",
    "2329": "Sri Prem Prayojan - 2017-09-06 - Why does Chaitanya Mahaprabhu come to this world",
    "6027": "Disappearance day of Srila Rupa Gosvami part 1 - 2021-08-19 - Sri Prem Prayojan",
    "123": "Sri Nityananda Prabhus causeless mercy - Sri Prem Prayojan Prabhu, Switzerland, 05.08.2014",
    "7894": "Gaudiya Math logo - the Essence of Mahaprabhu’s Vichar-Dhara - 2024-08-15 - Sri Prem Prayojan",
    "6556": "Guru Purnima, Vyasa Puja - 2022-07-13 - Sri Prem Prayojan",
    "1472": "2016.08.25 Sri Janmashtami",
    "2276": "Sri Prem Prayojan - 2017-08-15 - Sri Krishna Janmashtami",
    "6623": "Nandotsava - 2022-08-20 - Sri Prem Prayojan",
    "10075": "Jhulan Yatra, Dole 2012",
    "1468": "Rupanuaga, Palya dasi & Jhulan-Yatra, Sri Prem Prayojan Prabhu in Ananda-Dham, 14.08.2016",
    "10322": "2026.08.02_Rādhā-Kṛṣṇa-naukā-vihāra-līlā_Boat Festival",
    "7972": "Sri Radhastami part 2 - 2024-09-11 - Sri Prem Prayojan",
}


def moods():
    q = hc.Quotes(HERE, TITLES)
    P, E = q.piece, q.entry
    return [
        E("major-festivals",
          P("9739", "00:48:21", [("00:48:21", "But you should know", None, "Но вы должны знать", None)]),
          [P("10080", "00:51:16", [("00:51:16", "Kṛṣṇa's telling Uddhava", None, "Кришна говорит Уддхаве", None)])]),
        E("rupa-gosvami-festival",
          P("2329", "00:07:50", [("00:07:50", None, None, None, None)]),
          [P("6027", "00:04:20", [("00:04:20", None, None, None, None)]),
           P("123", "00:02:50", [("00:02:50", None, "lotus feet of Śrī Kṛṣṇa.", None, "лотосным стопам Шри Кришны.")]),
           P("7894", "00:04:56", [("00:04:56", "By the causeless", None, "По беспричинной", None)],
             fix_ru={"Радхи-Кришны's": "Радхи-Кришны"})]),
        E("guru-purnima-festival",
          P("6556", "00:04:34", [("00:04:34", "By the causeless", None, "По беспричинной", None)])),
        E("janmastami-nandotsava",
          P("1472", "00:05:26", [("00:05:26", None, None, None, None)]),
          [P("2276", "00:04:38", [("00:04:38", None, None, None, None)]),
           P("6623", "00:10:57", [("00:10:57", None, None, None, None)])]),
        E("jhulana-yatra",
          P("10075", "00:00:56", [("00:00:56", None, None, None, None)]),
          # 1468: the line at 01:05:10, the verse Gurudev quotes (CC Ādi 4.180, left out), and its explanation
          [P("1468", "01:05:10", [({"en": "01:05:10", "ru": "01:05:08"}, None, None, None, None),
                                  (None, None, None, None, None),
                                  (("#", 225), None, None, None, None)])]),
        E("nauka-vilasa",
          P("10322", "00:50:04", [("00:50:04", None, None, None, None), ("01:43:47", None, None, None, None)]),
          [P("10322", "00:50:42", [("00:50:42", None, None, None, None)])]),
        E("radhastami-festival",
          P("7972", "00:05:05", [("00:05:05", "Today, we are celebrating", None, "Сегодня мы празднуем", None)])),
    ]


if __name__ == "__main__":
    hc.main(HERE, SYSTEM, moods)
