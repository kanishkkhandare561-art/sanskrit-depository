"""Morphology + sandhi-splitting engine (SLP1 internally)."""
import json, functools, re
from vidyut.kosha import Kosha
from vidyut.lipi import transliterate, Scheme

VOWELS = set("aAiIuUfFxXeEoO")

# ---------------------------------------------------------------- nominal endings
# (ending, stem-final, label).  label uses short English grammar abbreviations.
def _a_stem():
    out = []
    for end, lab in [("aH", "nom. sg. m."), ("am", "acc. sg. m. / nom.-acc. sg. n."), ("ena", "instr. sg."), ("eRa", "instr. sg."),
                     ("Aya", "dat. sg."), ("At", "abl. sg."), ("asya", "gen. sg."), ("e", "loc. sg."), ("O", "nom.-acc. du."),
                     ("AByAm", "instr.-dat.-abl. du."), ("ayoH", "gen.-loc. du."), ("AH", "nom. pl. m."), ("An", "acc. pl. m."),
                     ("Ani", "nom.-acc. pl. n."), ("ARi", "nom.-acc. pl. n."), ("EH", "instr. pl."), ("eByaH", "dat.-abl. pl."),
                     ("AnAm", "gen. pl."), ("ARAm", "gen. pl."), ("ezu", "loc. pl.")]:
        out.append((end, "a", lab))
    return out

def _A_stem():
    return [(e, "A", l) for e, l in [("A", "nom. sg. f."), ("Am", "acc. sg. f."), ("ayA", "instr. sg. f."), ("AyE", "dat. sg. f."),
            ("AyAH", "abl.-gen. sg. f."), ("AyAm", "loc. sg. f."), ("e", "nom.-acc. du. f."), ("AByAm", "instr.-dat.-abl. du."),
            ("ayoH", "gen.-loc. du."), ("AH", "nom.-acc. pl. f."), ("ABiH", "instr. pl. f."), ("AByaH", "dat.-abl. pl. f."),
            ("AnAm", "gen. pl. f."), ("ARAm", "gen. pl. f."), ("Asu", "loc. pl. f.")]]

def _i_stem():
    return [(e, "i", l) for e, l in [("iH", "nom. sg."), ("im", "acc. sg."), ("inA", "instr. sg. m./n."), ("iRA", "instr. sg. m./n."),
            ("yA", "instr. sg. f."), ("aye", "dat. sg. m."), ("yE", "dat. sg. f."), ("eH", "abl.-gen. sg."), ("yAH", "abl.-gen. sg. f."),
            ("O", "loc. sg."), ("yAm", "loc. sg. f."), ("I", "nom.-acc. du."), ("iByAm", "instr.-dat.-abl. du."), ("yoH", "gen.-loc. du."),
            ("ayaH", "nom. pl."), ("In", "acc. pl. m."), ("IH", "acc. pl. f."), ("Ini", "nom.-acc. pl. n."), ("iBiH", "instr. pl."),
            ("iByaH", "dat.-abl. pl."), ("InAm", "gen. pl."), ("IRAm", "gen. pl."), ("izu", "loc. pl."), ("i", "nom.-acc. sg. n.")]]

def _I_stem():
    return [(e, "I", l) for e, l in [("I", "nom. sg. f."), ("Im", "acc. sg. f."), ("yA", "instr. sg. f."), ("yE", "dat. sg. f."),
            ("yAH", "abl.-gen. sg. f."), ("yAm", "loc. sg. f."), ("yO", "nom.-acc. du. f."), ("yaH", "nom. pl. f."), ("IH", "acc. pl. f."),
            ("IBiH", "instr. pl. f."), ("IByaH", "dat.-abl. pl. f."), ("InAm", "gen. pl. f."), ("IRAm", "gen. pl. f."), ("Izu", "loc. pl. f.")]]

def _u_stem():
    return [(e, "u", l) for e, l in [("uH", "nom. sg."), ("um", "acc. sg."), ("unA", "instr. sg."), ("uRA", "instr. sg."), ("ave", "dat. sg."),
            ("oH", "abl.-gen. sg."), ("O", "loc. sg."), ("U", "nom.-acc. du."), ("avaH", "nom. pl."), ("Un", "acc. pl. m."),
            ("uBiH", "instr. pl."), ("uByaH", "dat.-abl. pl."), ("UnAm", "gen. pl."), ("URAm", "gen. pl."), ("uzu", "loc. pl."),
            ("u", "nom.-acc. sg. n."), ("Uni", "nom.-acc. pl. n.")]]

def _f_stem():
    return [(e, "f", l) for e, l in [("A", "nom. sg."), ("Aram", "acc. sg."), ("aram", "acc. sg."), ("rA", "instr. sg."), ("re", "dat. sg."),
            ("uH", "abl.-gen. sg."), ("ari", "loc. sg."), ("ArO", "nom.-acc. du."), ("arO", "nom.-acc. du."), ("AraH", "nom. pl."),
            ("araH", "nom. pl."), ("Fn", "acc. pl."), ("fBiH", "instr. pl."), ("fByaH", "dat.-abl. pl."), ("FRAm", "gen. pl."), ("fzu", "loc. pl.")]]

def _cons():
    out = []
    # -at / -ant (participles, -vat, -mat)
    for e, l in [("an", "nom. sg. m."), ("An", "nom. sg. m."), ("antam", "acc. sg. m."), ("Antam", "acc. sg. m."), ("atA", "instr. sg."),
                 ("ate", "dat. sg."), ("ataH", "abl.-gen. sg. / acc. pl."), ("ati", "loc. sg."), ("antO", "nom.-acc. du."),
                 ("antaH", "nom. pl. m."), ("AntaH", "nom. pl. m."), ("atI", "nom. sg. f."), ("adBiH", "instr. pl."), ("adByaH", "dat.-abl. pl."),
                 ("atAm", "gen. pl."), ("atsu", "loc. pl."), ("at", "nom.-acc. sg. n."), ("anti", "nom.-acc. pl. n."), ("ati", "loc. sg.")]:
        out.append((e, "at", l))
    # -in
    for e, l in [("I", "nom. sg. m."), ("inam", "acc. sg. m."), ("iRam", "acc. sg. m."), ("inA", "instr. sg."), ("iRA", "instr. sg."),
                 ("ine", "dat. sg."), ("iRe", "dat. sg."), ("inaH", "abl.-gen. sg. / nom.-acc. pl."), ("iRaH", "abl.-gen. sg. / nom.-acc. pl."),
                 ("ini", "loc. sg."), ("iRi", "loc. sg."), ("inO", "nom.-acc. du."), ("iRO", "nom.-acc. du."), ("iBiH", "instr. pl."),
                 ("iByaH", "dat.-abl. pl."), ("inAm", "gen. pl."), ("iRAm", "gen. pl."), ("izu", "loc. pl."), ("i", "nom.-acc. sg. n."),
                 ("Ini", "nom.-acc. pl. n."), ("IRi", "nom.-acc. pl. n.")]:
        out.append((e, "in", l))
    # -an (Atman, karman, nAman)
    for e, l in [("A", "nom. sg. m."), ("Anam", "acc. sg. m."), ("ARam", "acc. sg. m."), ("anA", "instr. sg."), ("nA", "instr. sg."), ("aRA", "instr. sg."), ("RA", "instr. sg."),
                 ("ane", "dat. sg."), ("ne", "dat. sg."), ("aRe", "dat. sg."), ("Re", "dat. sg."), ("anaH", "abl.-gen. sg."), ("naH", "abl.-gen. sg."),
                 ("aRaH", "abl.-gen. sg."), ("RaH", "abl.-gen. sg."), ("ani", "loc. sg."), ("aRi", "loc. sg."), ("AnO", "nom.-acc. du."),
                 ("ARO", "nom.-acc. du."), ("AnaH", "nom. pl."), ("ARaH", "nom. pl."), ("a", "nom.-acc. sg. n."), ("Ani", "nom.-acc. pl. n."),
                 ("ARi", "nom.-acc. pl. n."), ("aBiH", "instr. pl."), ("aByaH", "dat.-abl. pl."), ("anAm", "gen. pl."), ("nAm", "gen. pl."),
                 ("aRAm", "gen. pl."), ("asu", "loc. pl.")]:
        out.append((e, "an", l))
    # -as / -is / -us neuters
    for st in ("as", "is", "us"):
        v = st[0]
        for e, l in [(v + "H", "nom.-acc. sg. n."), (v + "sA", "instr. sg."), (v + "zA", "instr. sg."), (v + "se", "dat. sg."), (v + "ze", "dat. sg."),
                     (v + "saH", "abl.-gen. sg."), (v + "zaH", "abl.-gen. sg."), (v + "si", "loc. sg."), (v + "zi", "loc. sg."),
                     ({"a": "AMsi", "i": "IMzi", "u": "UMzi"}[v], "nom.-acc. pl."), (v + "sAm", "gen. pl."), (v + "zAm", "gen. pl.")]:
            out.append((e, st, l))
        out += [(v + "soH", st, "gen.-loc. du."), (v + "zoH", st, "gen.-loc. du."), (v + "sI", st, "nom.-acc. du."), (v + "zI", st, "nom.-acc. du.")]
    out += [("oBiH", "as", "instr. pl."), ("oByaH", "as", "dat.-abl. pl."), ("A", "as", "nom. sg. m./f.")]
    return out

def _generic_cons():
    return [(e, "", l) for e, l in [("A", "instr. sg."), ("e", "dat. sg."), ("aH", "abl.-gen. sg. / nom.-acc. pl."), ("i", "loc. sg."),
            ("O", "nom.-acc. du."), ("am", "acc. sg."), ("Am", "gen. pl."), ("su", "loc. pl."), ("zu", "loc. pl."), ("BiH", "instr. pl."),
            ("ByaH", "dat.-abl. pl.")]]

ENDINGS = _generic_cons() + _a_stem() + _A_stem() + _i_stem() + _I_stem() + _u_stem() + _f_stem() + _cons()
ENDINGS.sort(key=lambda x: -len(x[0]))

PARTICLES = {
    "ca", "na", "iti", "eva", "tu", "api", "vA", "hi", "iva", "aTa", "Kalu", "ataH", "yataH", "tataH", "tatra", "yatra", "tadA", "yadA",
    "kadA", "punaH", "tAvat", "yAvat", "tathA", "taTA", "yaTA", "evam", "iha", "atra", "sma", "nu", "cet", "yadi", "kaTam", "kva",
    "saha", "vinA", "antareRa", "prAk", "Urdhvam", "aho", "BoH", "aNga", "hanta", "adDA", "tarhi", "kevalam", "paScAt", "yugapat",
    "sadA", "kadAcit", "kvacit", "kaScit", "kiYcit", "alam", "ekadA", "anyatra", "sarvatra", "anyaTA", "itarathA", "itaraTA", "sarvaTA",
    "nAnA", "pfTak", "BUyaH", "muhuH", "satatam", "sadyaH", "tUzRIm", "svayam", "svataH", "parataH", "kutaH", "kasmAt", "tasmAt",
    "yasmAt", "ataS", "ubhayaTA", "uBayaTA", "dvidhA", "tridhA", "bahuDA", "katham", "kim", "idAnIm", "adya", "purA", "pUrvam",
    "anantaram", "samam", "yatas", "tatas", "tad", "yad", "etad", "Iti", "om", "ati", "arTAt", "kaTaYcana", "kaTaYcit", "eva",
    "nanu", "atyantam", "mA", "cit", "cid", "cana", "Bhoh", "punar", "antar", "prAtar", "bahiH", "bahis", "Bahis", "ced", "aho", "vai", "ha", "u", "iti", "yadvat", "tadvat", "yaTAkramam", "kramaSaH", "ekaikaSaH",
}

FIXED = {
    **{p_ + "smin": (p_l, "pronoun: loc. sg. m./n.", "pron", 3.0) for p_, p_l in [("eka", "eka"), ("ta", "tad"), ("ya", "yad"), ("a", "idam"),
        ("eta", "etad"), ("ka", "kim"), ("anya", "anya"), ("sarva", "sarva"), ("aneka", "aneka"), ("uBaya", "uBaya"), ("anyatara", "anyatara"),
        ("ekatara", "ekatara"), ("itara", "itara"), ("para", "para"), ("pUrva", "pUrva"), ("amuz", "adas")]},
    "te": ("tad", "pronoun: nom. pl. m. (also ‘to you / your’ = yuṣmad)", "pron", 3.0),
    "tvam": ("yuzmad", "pronoun: you (nom. sg.)", "pron", 3.0),
    "catuzwvam": ("catuzwva", "nom.-acc. sg. n. — ‘fourfoldness’ (abstract noun from catur, ‘four’)", "nom", 3.0),
    "gOH": ("go", "nom. sg. — ‘cow’", "nom", 3.0), "gAm": ("go", "acc. sg.", "nom", 3.0), "gavA": ("go", "instr. sg.", "nom", 3.0),
    "goH": ("go", "abl.-gen. sg.", "nom", 3.0), "gavi": ("go", "loc. sg.", "nom", 3.0), "gAvaH": ("go", "nom. pl.", "nom", 3.0),
    "gavAm": ("go", "gen. pl.", "nom", 3.0),
    "tEH": ("tad", "pronoun: instr. pl. m./n.", "pron", 3.0), "eBiH": ("idam", "pronoun: instr. pl.", "pron", 3.0),
    "eByaH": ("idam", "pronoun: dat.-abl. pl.", "pron", 3.0), "eBir": ("idam", "pronoun: instr. pl.", "pron", 3.0),
    "trIRi": ("tri", "nom.-acc. pl. n. — ‘three’", "nom", 3.0), "staH": ("as", "verb: present, 3rd pers. du., active", "tin", 3.0),
    "BUH": ("BU", "nom. sg. f. — ‘earth; being’", "nom", 2.0),
    "sa": ("tad", "pronoun: nom. sg. m. (saḥ before a consonant)", "pron", 3.0),
    "saH": ("tad", "pronoun: nom. sg. m.", "pron", 3.0),
    "eza": ("etad", "pronoun: nom. sg. m. (eṣaḥ)", "pron", 3.0),
    "ezaH": ("etad", "pronoun: nom. sg. m.", "pron", 3.0),
    "ayam": ("idam", "pronoun: nom. sg. m.", "pron", 3.0),
    "iyam": ("idam", "pronoun: nom. sg. f.", "pron", 3.0),
    "idam": ("idam", "pronoun: nom.-acc. sg. n.", "pron", 3.0),
    "tat": ("tad", "pronoun: nom.-acc. sg. n.", "pron", 3.0),
    "yat": ("yad", "pronoun: nom.-acc. sg. n. / conj. ‘that, because’", "pron", 3.0),
    "etat": ("etad", "pronoun: nom.-acc. sg. n.", "pron", 3.0),
    "ahaM": ("asmad", "pronoun: I (nom. sg.)", "pron", 3.0), "aham": ("asmad", "pronoun: I (nom. sg.)", "pron", 3.0),
    "Bavati": ("BU", "verb: present, 3rd pers. sg., active", "tin", 3.0),
    "Bavanti": ("BU", "verb: present, 3rd pers. pl., active", "tin", 3.0),
    "asti": ("as", "verb: present, 3rd pers. sg., active", "tin", 3.0),
    "santi": ("as", "verb: present, 3rd pers. pl., active", "tin", 3.0),
    "Bavet": ("BU", "verb: optative, 3rd pers. sg., active", "tin", 3.0),
    "syAt": ("as", "verb: optative, 3rd pers. sg., active", "tin", 3.0),
    "syAtAm": ("as", "verb: optative, 3rd pers. du., active", "tin", 3.0),
    "syuH": ("as", "verb: optative, 3rd pers. pl., active", "tin", 3.0),
    "ucyate": ("vac", "verb: present, 3rd pers. sg., passive", "tin", 3.0),
    "ucyete": ("vac", "verb: present, 3rd pers. du., passive", "tin", 3.0),
    "ucyante": ("vac", "verb: present, 3rd pers. pl., passive", "tin", 3.0),
    "Aha": ("Ah", "verb: perfect, 3rd pers. sg. — ‘(he) says’", "tin", 3.0),
    "BavatA": ("Bavat", "pronoun: instr. sg. — ‘by you (honorific)’", "pron", 3.0),
    "BavAn": ("Bavat", "pronoun: nom. sg. m. — ‘you (honorific)’", "pron", 3.0),
    "kasmAt": ("kim", "pronoun: abl. sg. — ‘why? from what?’", "pron", 3.0),
}
STEM_BLOCK = {"avi", "Iti", "nABi", "nAti", "Ati", "adaya", "SrayaH", "mantf", "asi", "nAsty", "nAsti", "nAstika_", "ceti", "tenEva", "ityAdi_", "na", "Ra", "ta", "Ta", "da", "ma"}
COMMON_ROOTS = {"vac", "as", "BU", "kf", "jYA", "dfS", "gam", "i", "sTA", "laB", "grah", "vid", "man", "sad", "pad", "budh",
                "Buj", "yuj", "Sru", "smf", "dA", "DA", "nI", "han", "vft", "ji", "sic", "kzip", "upapad", "pratipad", "sidh",
                "pravft", "nivft", "upalaB", "anumA", "pramA", "aByupagam", "pratizidh", "Ah", "vad", "cint", "IkS", "arh"}
UPASARGA = {"pra", "parA", "apa", "sam", "anu", "ava", "nis", "nir", "dus", "dur", "vi", "A", "ni", "aDi", "api", "ati", "su", "ut", "ud",
            "aBi", "prati", "pari", "upa", "saM", "niH", "duH"}
UPASARGA_FULL = {"pra", "parA", "apa", "sam", "anu", "ava", "nis", "nir", "niH", "dus", "dur", "vi", "A", "ni", "aDi", "api", "ati", "su",
                 "ut", "ud", "aBi", "prati", "pari", "upa", "aBivi", "pravi", "saMpra", "sampra", "aByupa", "upA", "samA", "vyA", "pratyA",
                 "aBisam", "aBisaM", "anuvi", "pratyaBi", "samud", "samut", "aByA", "upasaM", "upasam", "vipari", "anvA", "paryA"}
SUFFIX_OK = {"tva", "tA", "vat", "mAtra", "ja", "sTa", "kAra", "kAri", "kfta", "Adi", "ka", "maya", "tara", "tama", "vid", "jYa", "ga"}
FREQ_PARTICLES = {"na", "ca", "iti", "eva", "tu", "api", "vA", "hi", "iva", "punar", "punaH"}
PRONOUN_STEMS = {"tad", "yad", "idam", "etad", "kim", "adas", "asmad", "yuzmad", "sarva", "anya", "eka", "para", "itara", "Bavat",
                 "ubhaya", "uBaya", "katara", "yatara", "anyatara", "ekatara", "kaScid", "pUrva", "apara", "dakziRa", "uttara", "sva", "ekatama"}

LAKARA = {"Lat": "present", "Lit": "perfect", "Lut": "periphrastic future", "Lrt": "future", "Lot": "imperative", "Lan": "imperfect",
          "VidhiLin": "optative", "AshirLin": "benedictive", "Lun": "aorist", "Lrn": "conditional", "Let": "subjunctive"}
PURUSHA = {"Prathama": "3rd", "Madhyama": "2nd", "Uttama": "1st"}
VACANA = {"Eka": "sg.", "Dvi": "du.", "Bahu": "pl."}
VIBH = {"Prathama": "nom.", "Dvitiya": "acc.", "Trtiya": "instr.", "Caturthi": "dat.", "Panchami": "abl.", "Sasthi": "gen.",
        "Saptami": "loc.", "Sambodhana": "voc."}
LINGA = {"Pum": "m.", "Stri": "f.", "Napumsaka": "n."}
PRAYOGA = {"Kartari": "active", "Karmani": "passive", "Bhave": "impersonal"}

FUSE = {"A": [("a", "a"), ("a", "A"), ("A", "a"), ("A", "A")],
        "I": [("i", "i"), ("i", "I"), ("I", "i"), ("I", "I")],
        "U": [("u", "u"), ("u", "U"), ("U", "u"), ("U", "U")],
        "e": [("a", "i"), ("a", "I"), ("A", "i"), ("A", "I")],
        "o": [("a", "u"), ("a", "U"), ("A", "u"), ("A", "U")],
        "E": [("a", "e"), ("A", "e"), ("a", "E"), ("A", "E")],
        "O": [("a", "o"), ("A", "o"), ("a", "O"), ("A", "O")]}
# last surface consonant of left member -> underlying finals
CONS_BACK = {"d": ["t"], "g": ["k"], "b": ["p"], "q": ["w"], "j": ["t", "c"], "c": ["t"], "l": ["t"], "n": ["t", "n"],
             "M": ["m", "n"], "o": ["as"], "r": ["s", "H"], "S": ["s", "H", "t"], "z": ["s", "H"], "s": ["s", "H"], "H": ["s", "H"],
             "Y": ["n", "t"], "N": ["N", "k"], "R": ["n", "R"], "w": ["w", "t"]}
# word-final external sandhi -> underlying finals
FINAL_BACK = {"o": ["aH"], "r": ["H"], "s": ["H"], "S": ["H"], "z": ["H"], "d": ["t"], "g": ["k"], "b": ["p"], "q": ["w"],
              "c": ["t"], "j": ["t"], "l": ["t"], "n": ["t", "m"], "M": ["m"], "y": ["i", "I"], "v": ["u", "U"],
              "Y": ["t", "n"], "N": ["N", "k"], "R": ["n"]}

SHORT_OK = {"a", "an", "su", "dus", "nis", "sa", "ca", "na", "tu", "hi", "vA", "iti", "api", "eva", "iva", "sva", "sat", "asat",
            "Bu", "go", "tat", "yat", "kim", "nO", "dvi", "tri", "jYa", "pra"}


HIATUS = [("aA", "A"), ("aa", "A"), ("Aa", "A"), ("AA", "A"), ("ai", "e"), ("aI", "e"), ("au", "o"), ("aU", "o"), ("Ai", "e"),
          ("ii", "I"), ("iI", "I"), ("Ii", "I"), ("uu", "U"), ("ia", "ya"), ("iA", "yA"), ("iu", "yu"), ("iU", "yU"), ("ie", "ye"),
          ("io", "yo"), ("ua", "va"), ("uA", "vA"), ("ui", "vi"), ("uI", "vI"), ("ue", "ve"), ("af", "ar"), ("Af", "Ar"), ("ae", "e"), ("ao", "o")]

def join_hiatus(t):
    for _ in range(3):
        for a, b in HIATUS:
            t = t.replace(a, b)
    return t


class Analyzer:
    def __init__(self, vdata, mw_path, curated):
        self.kosha = Kosha(vdata + "/kosha")
        mw = json.load(open(mw_path, encoding="utf-8"))
        self.mw = mw
        self.mwset = {k for k in mw if len(k) > 1 or k in ("a",)}
        self.curated = curated  # SLP1 stem -> meaning (also counts as a valid stem)
        # nasal aliases: MW writes saMkalpa, texts often write saNkalpa / sankalpa / sambandha
        self.alias = {}
        HOMO = {"k": "N", "K": "N", "g": "N", "G": "N", "c": "Y", "C": "Y", "j": "Y", "J": "Y", "w": "R", "W": "R", "q": "R", "Q": "R",
                "t": "n", "T": "n", "d": "n", "D": "n", "n": "n", "p": "m", "P": "m", "b": "m", "B": "m", "m": "m"}
        for k in mw:
            if "M" in k:
                a = re.sub(r"M(?=([kKgGcCjJwWqQtTdDnpPbBm]))", lambda m_: HOMO[m_.group(1)], k)
                if a != k and a not in mw:
                    self.alias[a] = k
        self.stems = (self.mwset | set(curated) | set(self.alias)) - STEM_BLOCK

    # ------------------------------------------------------------ word level
    @functools.lru_cache(maxsize=None)
    def kosha_get(self, w):
        try:
            return self.kosha.get(w)
        except Exception:
            return []

    @functools.lru_cache(maxsize=None)
    def pada(self, w):
        """Analyse an inflected word w (underlying form). Return list of (lemma, label, kind, score)."""
        res = []
        if w in PARTICLES:
            return ((w, "indeclinable", "avy", 3.0),)
        if w in FIXED:
            return (FIXED[w],)
        ks = self.kosha_get(w)
        tin = []
        en = lambda x: repr(x).split(".")[-1] if x is not None else ""
        for e in ks:
            r = repr(e)
            if r.startswith("PadaEntry.Tinanta"):
                d = e.dhatu_entry
                root = join_hiatus(d.clean_text)
                lab = f"{LAKARA.get(en(e.lakara), 'verb')}, {PURUSHA.get(en(e.purusha),'')} pers. {VACANA.get(en(e.vacana),'')}, {PRAYOGA.get(en(e.prayoga),'')}"
                sc = 2.2 + (0.3 if root in COMMON_ROOTS else 0)
                san = [repr(x).split(".")[-1] for x in (getattr(d.dhatu, "sanadi", None) or [])]
                if "San" in san:
                    lab = "desiderative, " + lab
                if "Ric" in san:
                    lab = "causative, " + lab
                tin.append((root, "verb: " + lab, "tin", sc))
            elif r.startswith("PadaEntry.Subanta"):
                pe = e.pratipadika_entry
                rp = repr(pe)
                if rp.startswith("PratipadikaEntry.Basic"):
                    t = pe.pratipadika.text
                    if t in PRONOUN_STEMS:
                        lab = f"{VIBH.get(en(e.vibhakti),'')} {VACANA.get(en(e.vacana),'')} {LINGA.get(en(e.linga),'')}"
                        res.append((t, "pronoun: " + lab, "pron", 2.6))
                    elif getattr(pe.pratipadika, "is_avyaya", False) and t == w and t in self.stems:
                        res.append((t, "indeclinable", "avy", 1.4))
                elif rp.startswith("PratipadikaEntry.Krdanta"):
                    krt = en(pe.krt)
                    root = join_hiatus(pe.dhatu_entry.clean_text)
                    pref = getattr(pe.dhatu_entry.dhatu, "prefixes", None) or []
                    kind = None
                    if krt == "ktvA":
                        kind = "gerund (absolutive): having …"
                    elif krt in ("lyap",) or (krt == "kyap" and pref and w.endswith("ya")):
                        kind = "gerund (absolutive): having …"
                    elif krt == "tumun":
                        kind = "infinitive: to …"
                    if kind:
                        res.append((root, kind, "kr", 2.7))
        # nominal endings with MW-validated stems
        nom = []
        for end, sf, lab in ENDINGS:
            if w.endswith(end) and len(w) > len(end):
                stem = w[: -len(end)] + sf
                if sf == "" and (stem[-1] in VOWELS or stem[-1] in "HM"):
                    continue
                if stem not in self.stems and sf == "a" and self.abstract(stem):
                    nom.append((stem, lab + " — abstract noun in -tva (‘-ness’)", "nom", 2.0))
                    continue
                if stem not in self.stems and sf == "A" and self.abstract(stem):
                    nom.append((stem, lab + " — abstract noun in -tā (‘-ness’)", "nom", 2.0))
                    continue
                if stem not in self.stems and sf in ("A", "I") and len(stem) > 4:
                    masc = stem[:-1] + "a"
                    if stem.endswith("ikA") and (stem[:-3] + "aka") in self.stems:
                        masc = stem[:-3] + "aka"
                    if masc in self.stems:
                        nom.append((masc, lab + " (feminine form)", "nom", 1.75))
                        continue
                if stem not in self.stems and sf == "a" and self.participle(stem):
                    rt, plab = self.participle(stem)
                    nom.append((stem, lab + " — " + plab + " (√" + rt + ")", "nom", 2.1))
                    continue
                if stem in self.stems:
                    sc = 1.5 + min(len(stem), 12) * 0.03 + (0.15 if sf == "a" else 0) + (0.1 if sf in ("i", "A", "u", "I") else 0) - (0.1 if sf in ("in", "at", "an") else 0)
                    if stem in self.curated:
                        sc += 0.2
                    nom.append((stem, lab, "nom", sc))
        # stem itself (compound-final without ending is rare, used for voc./stem forms)
        if w in self.stems and not nom and not res and not tin:
            res.append((w, "stem form", "stem", 0.6))
        # verbs: prefer finite reading unless a good a-/ā-stem noun exists
        good_nom = [n for n in nom if n[0].endswith(("a", "A", "i", "I", "u")) and len(n[0]) > 3]
        if any(t[0] in COMMON_ROOTS for t in tin):
            good_nom = []
            res = [r for r in res if r[2] not in ("avy", "pron")]
            nom = [n for n in nom if len(n[0]) > 6 and n[0].endswith("a")]
        if tin and not good_nom:
            for t in tin:
                res.append((t[0], t[1], t[2], t[3] + 0.6))
        else:
            res += [(t[0], t[1], t[2], 1.0) for t in tin[:2]]
        # adverbs in -tas
        if w.endswith("taH") and (w[:-1] + "s") not in self.stems and w[:-3] in self.stems and len(w) > 6:
            res.append((w[:-1] + "s", "indeclinable (adverb in -taḥ: ‘from / by reason of / as regards’)", "avy", 2.5))
        if w.endswith("taH") and (w[:-1] + "s") in self.stems:
            res.append((w[:-1] + "s", "indeclinable (adverb in -taḥ: ‘from / as regards’)", "avy", 2.5))
            nom = [x for x in nom if not x[0].endswith("tas")]
        res += nom
        if not res and not nom and not tin:
            for end, rep, lab in (("AmaH", "anti", "1st pers. pl."), ("Ami", "ati", "1st pers. sg."), ("AvaH", "anti", "1st pers. du."),
                                  ("asi", "ati", "2nd pers. sg."), ("aTa", "anti", "2nd pers. pl."), ("Amahe", "ante", "1st pers. pl. (middle)"),
                                  ("e", "ate", "1st pers. sg. (middle)")):
                if w.endswith(end) and len(w) > len(end) + 2:
                    for e in self.kosha_get(w[: -len(end)] + rep):
                        if repr(e).startswith("PadaEntry.Tinanta"):
                            res.append((join_hiatus(e.dhatu_entry.clean_text), f"verb: {LAKARA.get(en(e.lakara), 'present')}, {lab}", "tin", 2.4))
                            break
                    if res:
                        break
        if not res and not nom and not tin:
            for pf in sorted(UPASARGA_FULL, key=len, reverse=True):
                if w.startswith(pf) and len(w) > len(pf) + 3:
                    rest = w[len(pf):]
                    for e in self.kosha_get(rest):
                        if repr(e).startswith("PadaEntry.Tinanta"):
                            root = join_hiatus(pf + e.dhatu_entry.clean_text)
                            lab = f"{LAKARA.get(en(e.lakara), 'verb')}, {PURUSHA.get(en(e.purusha),'')} pers. {VACANA.get(en(e.vacana),'')}, {PRAYOGA.get(en(e.prayoga),'')}"
                            res.append((root, "verb: " + lab, "tin", 2.3))
                            break
                    if res:
                        break
        # group readings of the same lemma+kind, keep best score
        groups = {}
        for r in sorted(res, key=lambda x: -x[3]):
            g = groups.setdefault((r[0], r[2]), [r[0], [], r[2], r[3]])
            lab = r[1].replace("pronoun: ", "")
            if lab not in g[1]:
                g[1].append(lab)
        out = []
        for (lem, kind), g in groups.items():
            labs = g[1]
            lab = " | ".join(labs[:3])
            if kind == "pron":
                lab = "pronoun: " + lab
            out.append((lem, lab, kind, g[3]))
        out.sort(key=lambda x: -x[3])
        return tuple(out[:4])

    @functools.lru_cache(maxsize=None)
    def final_pada(self, w, nxt=""):
        """Try word w with external-sandhi final restorations; nxt = first SLP1 letter of the next word."""
        if w.endswith("nn") and len(w) > 3:
            w = w[:-1]
        cands = [] if (w and w[-1] in "dgbqjclrsSzyvMY") else [(w, 0.0)]
        if w and w[-1] in FINAL_BACK:
            for rep in FINAL_BACK[w[-1]]:
                pen = 0.05
                if w[-1] == "n" and rep == "t" and nxt in ("n", "m"):
                    pen = -0.4
                if w[-1] == "n" and rep == "t" and nxt not in ("n", "m"):
                    continue
                cands.append((w[:-1] + rep, pen))
        if nxt and nxt in VOWELS and w.endswith("a") and w not in PARTICLES:
            cands = [(c, pen + 0.5) for c, pen in cands]
            cands += [(w + "H", 0.05), (w[:-1] + "e", 0.1)]
        if w.endswith("A"):
            cands.append((w + "H", 0.35))
        if w.endswith("a"):
            cands += [(w + "H", 0.2), (w[:-1] + "e", 0.3)]
        if w.endswith("Ms") or w.endswith("MS"):
            cands.append((w[:-2] + "n", 0.05))
        if w.endswith("Ay"):
            cands.append((w[:-2] + "E", 0.2))
        if w.endswith("Av"):
            cands.append((w[:-2] + "O", 0.0))
        if w.endswith("y") and len(w) > 1 and w[-2] == "a":
            cands.append((w[:-1] + "e", 0.2))
        found = []
        for c, pen in cands:
            a = self.pada(c)
            if a:
                found.append((a[0][3] - pen, c, a))
        if not found:
            return None
        found.sort(key=lambda x: -x[0])
        best = found[0]
        # keep alternative readings that come from a different underlying form
        alts = tuple((c, an[0]) for sc, c, an in found[1:3] if c != best[1])
        return (best[0], best[1], best[2], alts)

    @functools.lru_cache(maxsize=None)
    def participle(self, stem):
        """Recognise middle/passive present participle stems in -mAna/-mARa/-Ana. Return (root, label) or None."""
        for suf in ("mAna", "mARa"):
            if stem.endswith(suf) and len(stem) > 5:
                base = stem[:-4]
                for e in self.kosha_get(base + "te"):
                    if repr(e).startswith("PadaEntry.Tinanta"):
                        pr = repr(e.prayoga).split(".")[-1]
                        return join_hiatus(e.dhatu_entry.clean_text), "present participle, " + ("passive" if pr == "Karmani" else "middle") + ": ‘being …-ed / …-ing’"
        if stem.endswith("Ana") and len(stem) > 4:
            for e in self.kosha_get(stem[:-3] + "e"):
                if repr(e).startswith("PadaEntry.Tinanta"):
                    return join_hiatus(e.dhatu_entry.clean_text), "participle in -āna: ‘…-ing / being …-ed’"
        return None

    def is_stem(self, u):
        return u in self.stems or self.participle(u) is not None or self.abstract(u)

    def abstract(self, u):
        return (u.endswith("tva") and len(u) > 5 and (u[:-3] in self.stems or (u[:-3] + "n") in self.stems)) or (u.endswith("tA") and len(u) > 4 and u[:-2] in self.stems and u[:-2][-1] in VOWELS)

    # ------------------------------------------------------------ compound / sandhi splitting
    def split(self, token, nxt=""):
        token = re.sub(r"r([kgcjwqtdpbmnyv])\1", r"r\1", token)
        token = re.sub(r"rtT", "rT", token)
        if token.endswith("nn") and len(token) > 3:
            token = token[:-1]
        best = self._split(token, nxt)
        for alt in self.initial_variants(token):
            r = self._split(alt, nxt)
            if r and (not best or r[0] + 0.05 < best[0]):
                best = r
        return best

    def initial_variants(self, t):
        out = []
        if t.startswith("cC"):
            out += ["S" + t[2:], "C" + t[2:]]
        elif t.startswith("C"):
            out.append("S" + t[1:])
        return out

    def _split(self, token, nxt=""):
        S = token
        n = len(S)
        INF = 1e9
        # dp[(pos, prefix)] = (cost, back)
        from heapq import heappush, heappop
        best = {}
        heap = [(0.0, 0, "", None)]
        final_best = None
        while heap:
            cost, p, pre, back = heappop(heap)
            key = (p, pre)
            if key in best:
                continue
            best[key] = (cost, back)
            if final_best and cost >= final_best[0]:
                break
            # end segment
            for j in range(p + 1, min(n, p + 40) + 1):
                surf = S[p:j]
                if j == n:
                    u = pre + surf
                    fp = self.final_pada(u, nxt)
                    if fp:
                        c = cost + self.seg_cost(fp[1], final=True, score=fp[0]) + self.obscurity(fp[2][0][0]) * (1 if fp[2][0][2] == "nom" else 0)
                        if final_best is None or c < final_best[0]:
                            final_best = (c, key, fp[1], fp[2], fp[3])
                    continue
                for left, np_, npre, tc in self.junctions(S, p, j, pre):
                    if self.is_stem(left):
                        c = cost + self.seg_cost(left) + tc
                    else:
                        pp = self.pada(left) if len(left) > 1 else None
                        if not pp:
                            continue
                        c = cost + self.seg_cost(left, nonfinal_pada=True, score=pp[0][3], kind=pp[0][2]) + tc
                    nk = (np_, npre)
                    if nk not in best:
                        heappush(heap, (c, np_, npre, (key, left, S[p:j])))
        if not final_best:
            return None
        c, key, ufinal, analyses, alts = final_best
        segs = [{"u": ufinal, "an": analyses, "alts": alts, "final": True}]
        while key != (0, ""):
            cost, back = best[key]
            pkey, left, s = back
            segs.append({"u": left, "an": None, "final": False})
            key = pkey
        segs.reverse()
        return c, segs

    def junctions(self, S, p, j, pre):
        n = len(S)
        base = pre + S[p:j]
        out = [(base, j, "", 0.0)]
        if base[-1] in "ai":
            out.append((base + "n", j, "", 0.02))
        c = S[j]
        if c in FUSE and j > p:
            for k, (lv, rv) in enumerate(FUSE[c]):
                out.append((pre + S[p:j] + lv, j + 1, rv, 0.03 + 0.005 * k))
        if S[j:j + 2] == "ar" and j + 2 < n:
            for lv in ("a", "A"):
                out.append((pre + S[p:j] + lv, j + 2, "f", 0.05))
        if c in "yvr" and j + 1 < n and S[j + 1] in VOWELS and j > p:
            for k, lv in enumerate({"y": ("i", "I"), "v": ("u", "U"), "r": ("f",)}[c]):
                out.append((pre + S[p:j] + lv, j + 1, "", 0.15 + 0.01 * k))
        last = S[j - 1]
        if j - 1 >= p and last in CONS_BACK:
            for orig in CONS_BACK[last]:
                out.append((pre + S[p:j - 1] + orig, j, "", 0.04))
        if last == "c" and c == "C" and j - 1 >= p:
            out.append((pre + S[p:j - 1] + "t", j + 1, "S", 0.04))
        if c == "c" and j + 1 < n and S[j + 1] == "C":
            out.append((base, j + 1, "", 0.02))
        return out

    @functools.lru_cache(maxsize=None)
    def obscurity(self, u):
        if u in self.curated:
            return -0.15
        e = self.mw.get(u) or self.mw.get(self.alias.get(u, ""))
        if not e:
            return 0.1
        g = e[0]
        if len(g) < 40 or g.startswith(("N. of", "see ", "= ", "w.r. for", "v.l. for", "ifc.", "mfn. ifc.")) or "w.r." in g[:30]:
            return 0.2
        return 0.0

    def seg_cost(self, u, final=False, nonfinal_pada=False, score=1.0, kind=""):
        c = 1.0
        L = len(u)
        if u in FREQ_PARTICLES and not final:
            c -= 0.15
        if u in UPASARGA:
            c += 0.6
        if L <= 2 and u not in SHORT_OK:
            c += 1.4
        elif L == 3 and u not in SHORT_OK and u not in SUFFIX_OK:
            c += 0.35
        if not nonfinal_pada:
            c += self.obscurity(u)
        if u in ("a", "an"):
            c += 0.25
        if not final and not nonfinal_pada:
            g = (self.mw.get(u) or self.mw.get(self.alias.get(u, ""), ["", ""]))[0]
            if u not in self.curated and (g.startswith("cl.") or re.match(r"^[^\s]*√", g) or "cl. " in g[:25]):
                c += 0.5
            if len(u) > 2 and u[-1] not in VOWELS and u[-2] not in VOWELS and u[-1] not in "HM":
                c += 0.4
        if nonfinal_pada:
            c += 0.05 if u in PARTICLES else (0.2 if kind in ("tin", "pron") else 0.7)
        if final:
            c += max(0.0, 2.0 - score) * 0.3
        return c


def iast(s):
    return transliterate(s, Scheme.Slp1, Scheme.Iast)

def slp(s):
    return transliterate(s, Scheme.Iast, Scheme.Slp1)
