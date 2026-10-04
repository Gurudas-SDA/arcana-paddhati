# -*- coding: utf-8 -*-
"""Front-matter chapter «Виграха-таттва» -> data/book*.json; its mood quotes -> scripts/moods/moods.json.
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
          "as in Gauḍīya books: vigraha, arcā-vigraha, sac-cid-ānanda-vigraha, Paramātmā, avatāra, dīkṣā, mantra, darśana, "
          "hari-kathā, aṅga, bhakti, rāgānugā-sādhana, Vraja, vraja-gopīs, Śrī Gopāla, Śrīnāthajī, Vajranābha, Śrīla "
          "Mādhavendra Purī, Śrīla Rūpa Gosvāmī, Śrīla Jīva Gosvāmī, Rādhā-Dāmodara, Sevā-kuñja, Vṛndāvana, Sākṣī-gopāla, "
          "Padma Purāṇa, Vedānta-sūtra, Kūrma Purāṇa, Bhagavad-gītā, Brahma-saṁhitā, Śrī Caitanya-caritāmṛta (Ādi, Madhya, "
          "Antya), Bhakti-rasāmṛta-sindhu, Lalita-mādhava, Śikṣāṣṭaka, Śrīla Haridāsa Ṭhākura, Śrīla Sanātana Gosvāmī, "
          "Śrīla Viśvanātha Cakravartī Ṭhākura, prārabdha-karma, kaustubha, cintāmaṇi, Nārāyaṇa, Śrīmatī Rādhārāṇī, "
          "Rādhikā, Arjuna, Paurṇamāsī, Yogamāyā, Yamunā, Gaṅgā, Sarasvatī, Triveṇī, Goloka Vṛndāvana, Jagannātha Purī, "
          "Gadādhara Paṇḍita, Gambhīrā, Svarūpa Dāmodara, Rāya Rāmānanda, Lalitā, Viśākhā, Yameśvara-ṭoṭā, "
          "kṣetra-sannyāsa, Ṭoṭā-gopīnātha, Śrīmad-Bhāgavatam, Puruṣottama-māsa, Durham (North Carolina, USA). "
          "«Гурудев» = «Gurudev» (our spiritual master Śrī Prem Prayojan Prabhu); «Шрила Бхактиведанта Нараяна Госвами "
          "Махарадж» = «Śrīla Bhaktivedānta Nārāyaṇa Gosvāmī Mahārāja». «лекция № 10183» → «lecture no. 10183»; «см. "
          "«Настроение Гурудева»» → «see “Gurudev's Mood”». Chapter title «Виграха-таттва» → «Vigraha-tattva». Verse "
          "translations: plain prose, keep the source reference in parentheses. Answer with JSON only.")

TITLES = {"10183": "2026.05.23_Vigraha tattva, Durham NC"}


def moods():
    q = hc.Quotes(HERE, TITLES)
    P, E = q.piece, q.entry
    w = lambda ts: P("10183", ts, [(ts, None, None, None, None)])
    return [
        E("vigraha-tattva", w("00:11:03")),
        E("vigraha-not-idol", w("00:15:42"), [w("00:17:49")]),
        E("vigraha-sac-cid-ananda", w("00:21:20"), [w("00:25:01")]),
        E("vigraha-fourth-form", w("00:31:13"), [w("00:34:13")]),
        E("vigraha-service-for-all", w("00:34:14")),
        E("vigraha-three-senses", w("00:46:21")),
        E("vigraha-diksa", w("00:58:09"), [w("01:02:14")]),
        E("vigraha-not-symbol", w("01:09:21")),
        E("vigraha-four-madhuris", w("01:25:01")),
        E("vigraha-darsana-greed", w("01:44:01"), [w("01:31:45")]),
        E("vigraha-tota-gopinatha", P("10183", "01:48:58", [("01:48:58", None, None, None, None),
                                                           (("#", 517), None, None, None, None)])),
    ]


if __name__ == "__main__":
    hc.main(HERE, SYSTEM, moods)
