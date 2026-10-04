# -*- coding: utf-8 -*-
"""Front-matter chapter «Эмблема Гаудия-матха» -> data/book*.json (no mood blocks: see moods()).
  python build.py translate | apply | fetch      (see ../hand_chapter.py)
After apply: python ../../moods/apply_moods.py (keeps the other chapters' mood blocks), then npm run build.
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
          "rāgānugā-bhakti, vaidhī-bhakti, pāñcarātrika-dīkṣā, varṇāśrama-dharma, siddha-praṇālī, khichri, "
          "Hari-bhakti-vilāsa, Rāga-vartma-candrikā, Śrīla Viśvanātha Cakravartī Ṭhākura, Madhvācārya, Nimbāditya, "
          "Rāmānujācārya, Viṣṇusvāmī, Brahma-sampradāya, Śrī-sampradāya, Rudra-sampradāya, Lakṣmī-Nṛsiṁha, Padma Purāṇa, "
          "Dvārakā, Rukmiṇī, Vasudeva, Devakī, Nanda, Yaśodā, Vraja, smārta-brāhmaṇas, smaraṇa, kuñja, hari-kathā, "
          "lakh, maṅgala-ārati, Prabhupāda-padāṣṭaka, Gauḍīya-darśana, agauḍīya. «Гурудев» = «Gurudev» (our spiritual "
          "master Śrī Prem Prayojan Prabhu). Literary book prose in the third person, as in the Russian. Chapter title "
          "«Эмблема Гаудия-матха» → «The Emblem of the Gauḍīya Maṭha». Answer with JSON only.")


def moods():
    """No mood blocks in the intro chapters (Satkirti, 2026-10-04): the chapter itself conveys Gurudev's thought, and
    one source line with links opens it (chapter_ru.py SOURCES). `python build.py moods` therefore adds nothing; the
    chapter's former entries were removed from scripts/moods/moods.json."""
    return []


if __name__ == "__main__":
    hc.main(HERE, SYSTEM, moods)
