# -*- coding: utf-8 -*-
"""Front-matter chapter «Эмблема Гаудия-матха» -> data/book*.json; its mood quotes -> scripts/moods/moods.json.
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
          "as in Gauḍīya books: Gauḍīya Maṭha, maṭha, Śrīla Bhaktisiddhānta Sarasvatī Ṭhākura Prabhupāda, Śrīla Rūpa "
          "Gosvāmī, Vraja-svarūpa, Śrīmatī Rādhikā, Gaurī, Śrī Gaurāṅga Mahāprabhu, Nityānanda Prabhu, Lakṣmī-Nārāyaṇa, "
          "Vaikuṇṭha, Śrī Śrī Rādhā-Kṛṣṇa, Vṛndāvana, Pāñcarātra, Bhāgavatam, Śrīmad-Bhāgavatam, Bhāgavata-sandarbha, "
          "Śrīla Jīva Gosvāmī, Ṛg-veda, Gopāla-yantra, Gopāla-mantra, mahā-mantra, Bhagavān, siddhānta, arcana, ārati, "
          "dīpa, cāmara, mṛdaṅga, kartālas, Śukadeva Gosvāmī, Śrīla Prabhupāda, kṛṣṇa-prema, Kali-yuga, tilaka, "
          "rāgānugā-bhakti, vaidhī-bhakti, pāñcarātrika-dīkṣā, varṇāśrama-dharma, siddha-praṇālī, khichri, Jhūlana-yātrā, "
          "Chaitanya Academy (Latvia, Venice). «Гурудев» = «Gurudev» (our spiritual master Śrī Prem Prayojan Prabhu). "
          "«лекция № 7894 от 15.08.2024» → «lecture no. 7894, 15 August 2024»; «лекция № 1480 от 01.09.2016» → "
          "«lecture no. 1480, 1 September 2016»; «(там же; …)» → «(ibid.; …)»; «см. «Настроение Гурудева»» → «see "
          "“Gurudev's Mood”». Chapter title «Эмблема Гаудия-матха» → «The Emblem of the Gauḍīya Maṭha». Answer with "
          "JSON only.")

TITLES = {
    "7894": "Gaudiya Math logo - the Essence of Mahaprabhu’s Vichar-Dhara - 2024-08-15 - Sri Prem Prayojan",
    "1480": "Sri Prem Prayojan Prabhu: 01.09.2016 1 Nama Aparadha p. 1",
}


def moods():
    q = hc.Quotes(HERE, TITLES)
    P, E = q.piece, q.entry
    return [
        E("gaudiya-emblem",
          P("7894", "00:06:25", [("00:06:25", None, None, None, None),
                                 ("00:09:54", None, "logo of the Gauḍīya Maṭha.", None, "логотипа Гаудия-матха.")]),
          [P("7894", "01:58:18", [("01:58:18", "And so to in- embody", None, "Итак, чтобы воплотить", None)])]),
        E("emblem-gaudiya-matha",
          P("7894", "00:07:56", [("00:07:56", None, None, None, None)])),
        E("emblem-centre",
          P("7894", "00:12:58", [("00:12:58", None, None, None, None)]),
          [P("1480", "01:54:51", [("01:54:51", "You can see that", "mahā-mantra.", "Вы можете видеть", "маха-мантра.")])]),
        E("emblem-mahaprabhu-guru",
          P("7894", "00:14:27", [("00:14:27", None, None, None, None)])),
        E("emblem-vidhi-raga",
          P("7894", "00:15:21", [("00:15:21", None, None, None, None)]),
          [P("1480", "01:54:51", [("01:54:51", "So, in the logo", None, "Таким образом, на эмблеме", None)])]),
        E("emblem-arcanam-kirtanam",
          P("7894", "00:17:39", [("00:17:39", None, None, None, None)])),
        E("emblem-meaning",
          P("7894", "00:22:41", [("00:22:41", None, None, None, None)]),
          [P("1480", "01:56:47", [("01:56:47", "So, but Śrīla", "pure citta.", "Но Шрила", "сварупа бхакти.")])]),
        E("emblem-why",
          P("7894", "00:50:40", [("00:50:40", None, None, None, None)]),
          [P("7894", "01:59:25", [("01:59:25", None, None, None, None)])]),
    ]


if __name__ == "__main__":
    hc.main(HERE, SYSTEM, moods)
