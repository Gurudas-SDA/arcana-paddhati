# -*- coding: utf-8 -*-
"""Part IV, chapter 14 «Шри Гуру-пуджа и Вьяса-пуджа» -> data/book*.json; its mood quotes -> scripts/moods/moods.json.
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
          "Śrī Prem Prayojan Prabhu). Book titles plainly, no quotation marks: «Ачарья Кешари Кешава Госвами. Его жизнь "
          "и учение», М., 2004 → «Ācārya Kesarī Keśava Gosvāmī: His Life and Teachings, Russian edition, Moscow, 2004»; "
          "«англ. изд.» → «English edition (GVP, 2013)» the first time, then «English edition». «лекция № 9643 от "
          "06.07.2025» → «lecture no. 9643, 6 July 2025» (same pattern for all lectures); «с. 105» → «p. 105». Chapter "
          "titles of this book: «Арчана Шри Гуру» → «Arcana of Śrī Guru»; «Храмовый стандарт» → «Temple Standard»; "
          "«Главное поклонение с шестнадцатью упачарами» → «The Main Worship with Sixteen Items». The translation "
          "«Sumantu Muni Aṅgirā» stays in English as is. Russian dates like «6 февраля 2027 г.» → «6 February 2027». "
          "Answer with JSON only.")

TITLES = {
    "10011": "2026.04.12_Vyasa Puja lecture",
    "5168": "Sri Prema Prayojana Prabhu Vyasa Puja 18042020",
    "378": "2007.07.29-1_Vyasapuja",
    "7247": "2023.07.03 Sri Raya Ramananda Samvada part 08",
    "5836": "SAT SAMPRADAYA SAD GURU SAT SISYA - 2021-05-07 - Sri Prem Prayojan",
    "3295": "Sri Prem Prayojan - 2018-07-27 - Guru-Purnima",
    "5984": "Appearance Day of Srila Vyasadeva part 1 - 2021-07-24 - Sri Prem Prayojan",
}


def moods():
    q = hc.Quotes(HERE, TITLES)
    P, E = q.piece, q.entry
    return [
        E("vyasa-puja-meaning",
          # 10011 has no timecodes in the transcript: the opening paragraph after the invocation
          P("10011", "", [(("#", 18), None, None, None, None)]),
          [P("5168", "00:04:46", [("00:04:46", "So, the tradition is", "manifest transcendental knowledge.",
                                   "Итак, традиция такова", "проявить трансцендентное знание.")]),
           P("378", "00:19:45", [("00:19:45", None, "down to his own guru.", None, "вплоть до своего гуру.")])]),
        E("sapta-pancakam",
          P("7247", "00:43:46", [("00:43:46", None, None, None, None), ("00:47:19", None, None, None, None)]),
          [P("5168", "00:11:48", [("00:11:48", "The worship of the Vyāsa-pūjā", None, "Поклонение в честь Вьяса-пуджи", None),
                                  ("00:14:09", None, None, None, None)]),
           P("5836", "00:13:47", [("00:13:47", None, None, None, None),
                                  (("#", 61), "So, and then upāsya-pañcaka.", None, "Итак, далее — упасья-панчака.", None)],
             fix_ru={"Ангирa": "Ангира"})]),
        E("vyasa-puja-order",
          P("3295", "00:26:31", [("00:26:31", "This is a very ancient ceremony", "partake in this ceremony.",
                                  "Это очень древняя церемония", None)]),
          [P("5984", "00:31:18", [("00:31:18", None, None, None, None)])]),
    ]


if __name__ == "__main__":
    hc.main(HERE, SYSTEM, moods)
