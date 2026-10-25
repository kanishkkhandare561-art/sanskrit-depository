"""Titles, authors, commentary layers and sources of the texts in the depository."""

LIBRARY = {
    "darshanas": [
        {"id": "nyaya", "name": "Nyāya darśana", "deva": "न्यायदर्शनम्",
         "blurb": "The school of logic and epistemology: the sūtras of Gautama, their classical commentaries, "
                  "the ‘new’ Nyāya of Gaṅgeśa, and the Nyāya-Vaiśeṣika primer that students still begin with.",
         "texts": ["nyaya", "nyaya-tatparya", "tattvacintamani", "tarkasangraha", "tarkasangraha-dipika"]},
    ],
    "texts": {},
}

GRETIL_LICENCE = "Creative Commons Attribution-NonCommercial-ShareAlike 4.0"

TEXTS = {
    "nyaya": {
        "title": "Nyāyasūtra with Vātsyāyana’s Nyāyabhāṣya",
        "short": "Nyāyasūtra · Bhāṣya",
        "deva": "न्यायसूत्रम् वात्स्यायनभाष्यसहितम्",
        "author": "Gautama (Akṣapāda), with the commentary of Vātsyāyana (Pakṣilasvāmin)",
        "blurb": "The root text of the school, 528 sūtras in five adhyāyas, with the oldest surviving commentary.",
        "root": "sūtra",
        "layers": [{"k": "bhasya", "name": "Nyāyabhāṣya", "deva": "न्यायभाष्यम्", "by": "Vātsyāyana"}],
        "groups": "adhyaya",
        "source": "GRETIL e-text (input by the Indology Student Team, University of Tokyo), based on the edition of Taranatha "
                  "Nyaya-Tarkatirtha, Calcutta Sanskrit Series 18 & 19 (Calcutta, 1936–1944). About eighty keying errors were corrected.",
        "hero": "1.1.1",
    },
    "nyaya-tatparya": {
        "title": "Nyāyasūtra with Vācaspati Miśra’s Tātparyaṭīkā",
        "short": "Nyāyasūtra · Tātparyaṭīkā",
        "deva": "न्यायवार्त्तिकतात्पर्यटीका",
        "author": "Vācaspati Miśra (10th century), on Uddyotakara’s Nyāyavārttika",
        "blurb": "Vācaspati’s ‘commentary on the purport’ of the Vārttika, the great defence of Nyāya against the Buddhist logicians, "
                 "set out under each sūtra of Gautama.",
        "root": "sūtra",
        "layers": [{"k": "tika", "name": "Tātparyaṭīkā", "deva": "तात्पर्यटीका", "by": "Vācaspati Miśra"}],
        "groups": "adhyaya",
        "source": "GRETIL e-text, input by members of the SANSKNET project and checked against the edition of Anantalal Thakur "
                  "(New Delhi, 1996). The e-text was converted from a Devanagari encoding, so many word boundaries are not marked "
                  "by spaces, and it has not been fully proof-read. Page and line references to the Vārttika were removed.",
        "caution": "This e-text has not been fully proof-read, and many words run together as they would in a Devanagari print. "
                   "Expect more misprints, and more uncertain analyses, than in the Bhāṣya.",
    },
    "tattvacintamani": {
        "title": "Tattvacintāmaṇi of Gaṅgeśa · Śabdakhaṇḍa",
        "short": "Tattvacintāmaṇi · Śabda",
        "deva": "तत्त्वचिन्तामणौ शब्दखण्डः",
        "author": "Gaṅgeśa Upādhyāya (14th century)",
        "blurb": "The founding work of Navya-Nyāya. This book on verbal testimony runs from the defence of śabda as a "
                 "means of knowledge to the debate over what words denote.",
        "root": "vāda",
        "layers": [],
        "groups": None,
        "source": "GRETIL e-text, input by members of the SANSKNET project; it corresponds to the Bibliotheca Indica edition "
                  "(no. 98), part IV vol. 1 to part IV vol. 2, p. 599 line 2, and stops partway through the Jātiśaktivāda. "
                  "The page numbers of that edition are shown in the margin.",
        "caution": "This e-text has not been proof-read, and many words run together as they would in a Devanagari print.",
    },
    "tarkasangraha": {
        "title": "Tarkasaṃgraha of Annaṃbhaṭṭa",
        "short": "Tarkasaṃgraha",
        "deva": "तर्कसंग्रहः",
        "author": "Annaṃbhaṭṭa (17th century)",
        "blurb": "The classic primer of Nyāya-Vaiśeṣika: the seven categories and the four means of knowledge in 81 short sections.",
        "root": "section",
        "layers": [],
        "groups": None,
        "source": "GRETIL e-text input by Takuya Ono. The e-text also gives an analysed (pada-pāṭha) version of every section; "
                  "it is not shown, but the word analysis uses it to decide where words and compound members divide.",
    },
    "tarkasangraha-dipika": {
        "title": "Tarkasaṃgraha with the Dīpikā, Prakāśikā and Bālapriyā",
        "short": "Tarkasaṃgraha · Dīpikā",
        "deva": "तर्कसंग्रहः दीपिकाप्रकाशिकाबालप्रियासहितः",
        "author": "Annaṃbhaṭṭa’s own Dīpikā, Nīlakaṇṭha Bhaṭṭa’s Prakāśikā, and N. S. Rāmānuja Tātācārya’s Bālapriyā",
        "blurb": "The Tarkasaṃgraha with its author’s own commentary and two layers of sub-commentary, "
                 "followed by Kṛṣṇa Tātācārya’s Prasāraṇā on the Prakāśikā.",
        "root": "section",
        "layers": [
            {"k": "dipika", "name": "Dīpikā", "deva": "दीपिका", "by": "Annaṃbhaṭṭa"},
            {"k": "prakasika", "name": "Prakāśikā", "deva": "प्रकाशिका", "by": "Nīlakaṇṭha Bhaṭṭa, on the Dīpikā"},
            {"k": "balapriya", "name": "Bālapriyā", "deva": "बालप्रिया", "by": "N. S. Rāmānuja Tātācārya, on the Prakāśikā"},
            {"k": "notes", "name": "Notes", "deva": "टिप्पणी", "by": "Footnotes of the printed edition"},
            {"k": "prasarana", "name": "Prasāraṇā", "deva": "प्रसारणा", "by": "Kṛṣṇa Tātācārya, on the Prakāśikā"},
        ],
        "groups": None,
        "analytic_from": "tarkasangraha",
        "source": "GRETIL e-text, input by members of the SANSKNET project, of the edition with the Bālapriyā and Prasāraṇā "
                  "(Madras, 1980; preface by N. Veezhinathan, which is not reproduced here). The root text in each section is GRETIL’s "
                  "standard text of the Tarkasaṃgraha; where the edition reprints the same words, the repetition is left out.",
        "caution": "This e-text has not been proof-read, and many words run together as they would in a Devanagari print. "
                   "Expect misprints, and more uncertain analyses, especially in the Navya-Nyāya sub-commentaries.",
    },
}
