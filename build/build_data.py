"""Tokenise the parsed text, analyse every word, write site data files."""
import json, re, os, sys, collections
from vidyut.lipi import transliterate, Scheme
from morph import Analyzer, iast, slp, VOWELS

ROOT = os.path.dirname(os.path.abspath(__file__))
SITE = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "..")
DATA = os.path.join(SITE, "data")
os.makedirs(DATA, exist_ok=True)

parsed = json.load(open(os.path.join(ROOT, "parsed.json"), encoding="utf-8"))
curated_iast = json.load(open(os.path.join(ROOT, "curated.json"), encoding="utf-8"))
overrides = json.load(open(os.path.join(ROOT, "overrides.json"), encoding="utf-8"))
curated = {}
for k, v in curated_iast.items():
    if k.startswith("_") or k.endswith("_") or not v or "_" in k:
        continue
    curated[slp(k)] = v
mw = json.load(open(os.path.join(ROOT, "mw_index.json"), encoding="utf-8"))
A = Analyzer(os.path.join(ROOT, "vdata"), os.path.join(ROOT, "mw_index.json"), curated)


def deva(s):
    return transliterate(s, Scheme.Iast, Scheme.Devanagari)


def deva_slp(s):
    return transliterate(s, Scheme.Slp1, Scheme.Devanagari)


LET = "a-zA-Zāīūṛṝḷḹṅñṭḍṇśṣṃḥ"
TOK = re.compile(rf"(//\s*\d+\s*//|//|/|---|``|''|[,;?!:]|'?[{LET}]+|\d+|\S)")


def tokenize(text):
    toks = TOK.findall(text)
    out = []
    for t in toks:
        if re.fullmatch(rf"'?[{LET}]+", t):
            out.append(("w", t))
        else:
            out.append(("p", t))
    return out


PUNCT = {"/": "।", "//": "॥", "---": "—", "``": "“", "''": "”"}


def punct(t):
    m = re.fullmatch(r"//\s*(\d+)\s*//", t)
    if m:
        return "॥" + transliterate(m.group(1), Scheme.Iast, Scheme.Devanagari) + "॥"
    return PUNCT.get(t, t)


def nxt_class(nx):
    if not nx:
        return ""
    if nx in ("n", "m"):
        return nx
    if nx in VOWELS:
        return "a"
    return ""


# ------------------------------------------------------------------ glosses
def mw_gloss(lem):
    e = mw.get(lem) or mw.get(A.alias.get(lem, "")) 
    if not e and lem.endswith("i") and lem[:-1] in mw:   # causative stem in -i
        e = mw.get(lem[:-1])
    if not e and lem + "A" in mw:   # desiderative stem -> desiderative noun
        e = mw.get(lem + "A")
    if not e:
        return None
    g = e[0]
    if g.startswith("cl.") or re.match(r"^(\w+ )?cl\. ?\d", g):
        m = re.search(r"\bto [a-z]", g)
        g = ("√ (verb) " + g[m.start():]) if m else g
    g = re.sub(r"\s*;\s*;", ";", g)
    g = g.replace(" ,", ",").strip()
    if len(g) > 300:
        g = g[:300].rsplit(" ", 1)[0] + " …"
    return g


GLOSS = {}   # lemma SLP1 -> {"i": iast, "m": meaning, "s": source, "x": mw-only extra}


def gloss_for(lem):
    if lem in GLOSS:
        return
    ent = {"i": iast(lem)}
    c = curated.get(lem)
    mg = mw_gloss(lem)
    if c:
        ent["m"] = c if isinstance(c, str) else c.get("m")
        if isinstance(c, dict) and c.get("n"):
            ent["n"] = c["n"]
        ent["s"] = "c"
        if mg:
            ent["mw"] = mg
    elif mg:
        ent["m"] = mg
        ent["s"] = "mw"
    mk = lem if lem in mw else A.alias.get(lem)
    if mk and "—" in mw[mk][1]:
        parts = [p.replace("/", "") for p in mw[mk][1].split("—") if p]
        if len(parts) > 1:
            ent["c"] = [iast(p) for p in parts]  # dictionary compound structure
    GLOSS[lem] = ent


# ------------------------------------------------------------------ analysis
ANALYSES = {}
fail = collections.Counter()
lemma_freq = collections.Counter()


def analyse(tok, nxt):
    key = tok + "|" + nxt
    if key in ANALYSES:
        return key
    raw = tok
    iast_tok = tok
    s = slp(iast_tok)
    lead_av = False
    if s.startswith("'"):
        s = "a" + s[1:]
        lead_av = True
    ov = overrides.get(iast_tok)
    entry = {"w": iast_tok}
    if ov:
        parts = []
        for p in ov["p"]:
            parts.append({"u": p[0], "l": p[1], "g": p[2] if len(p) > 2 else ""})
            gloss_for(slp(p[1]))
            lemma_freq[slp(p[1])] += 1
        for p_ in parts:
            p_["d"] = deva(p_["u"]); p_["ld"] = deva(p_["l"])
        entry["p"] = parts
        entry["v"] = 1
        if ov.get("n"):
            entry["n"] = ov["n"]
        ANALYSES[key] = entry
        return key
    r = A.split(s, nxt)
    if not r:
        fail[iast_tok] += 1
        entry["p"] = []
        ANALYSES[key] = entry
        return key
    cost, segs = r
    parts = []
    for sg in segs:
        u = sg["u"]
        if sg["final"]:
            lem, lab, kind, sc = sg["an"][0]
            alts = []
            for a in sg["an"][1:3]:
                alts.append([iast(a[0]), a[1]])
            for (uc, a) in sg.get("alts", ()):
                alts.append([iast(a[0]), a[1] + f" (reading {iast(uc)})"])
            p = {"u": iast(u), "l": iast(lem), "g": lab}
            if alts:
                p["a"] = alts[:3]
            gloss_for(lem)
            for a in sg["an"][1:3]:
                gloss_for(a[0])
            lemma_freq[lem] += 1
        else:
            if u in A.stems:
                p = {"u": iast(u), "l": iast(u), "g": "compound member (stem)"}
                gloss_for(u)
                lemma_freq[u] += 1
            elif A.participle(u):
                rt, plab = A.participle(u)
                p = {"u": iast(u), "l": iast(u), "g": "compound member — " + plab + " (√" + iast(rt) + ")", "r": iast(rt)}
                gloss_for(rt)
            elif A.abstract(u):
                base = u[:-3] if u.endswith("tva") else u[:-2]
                p = {"u": iast(u), "l": iast(u), "g": "compound member — abstract noun (‘-ness’) from " + iast(base), "r": iast(base)}
                gloss_for(base)
            else:
                an = A.pada(u)
                lem, lab, kind, sc = an[0]
                p = {"u": iast(u), "l": iast(lem), "g": lab}
                gloss_for(lem)
                lemma_freq[lem] += 1
        parts.append(p)
    for p_ in parts:
        p_["d"] = deva(p_["u"])
        p_["ld"] = deva(p_["l"])
    entry["p"] = parts
    if cost / max(1, len(parts)) > 1.6:
        entry["q"] = 1  # low confidence
    ANALYSES[key] = entry
    return key


def process_text(text):
    toks = tokenize(text)
    out = []
    for i, (kind, t) in enumerate(toks):
        if kind == "p":
            out.append(punct(t))
            continue
        nx = ""
        if i + 1 < len(toks) and toks[i + 1][0] == "w":
            nt = slp(toks[i + 1][1])
            nx = "a" if nt.startswith("'") else nt[0]
        key = analyse(t, nxt_class(nx))
        out.append([deva(t), key])
    return out


TOPICS = {"1.1": "The sixteen categories enumerated and defined: means of knowledge, objects of knowledge, doubt, the five-membered argument",
          "1.2": "Kinds of debate, the five pseudo-reasons, quibble, futile rejoinder and points of defeat",
          "2.1": "Doubt examined; the means of knowledge defended — perception, inference, comparison and testimony",
          "2.2": "Other proposed means of knowledge; the impermanence of sound; what a word means",
          "3.1": "The self, the body, the senses and their objects",
          "3.2": "Cognition, the mind, and how a body comes to be",
          "4.1": "Faults, rebirth, fruit, pain and liberation; rival doctrines on causation",
          "4.2": "Knowledge of truth; wholes and parts; idealism refuted; the practice of yoga",
          "5.1": "The twenty-four futile rejoinders (jāti)",
          "5.2": "The twenty-two points of defeat (nigrahasthāna)"}
TITLES = {"1": "Adhyāya I", "2": "Adhyāya II", "3": "Adhyāya III", "4": "Adhyāya IV", "5": "Adhyāya V"}
AHN = {"1": "Āhnika 1", "2": "Āhnika 2"}

index = {"text": {"id": "nyaya", "title": "Nyāyasūtra with Vātsyāyana’s Nyāyabhāṣya", "deva": deva("nyāyasūtram vātsyāyanabhāṣyasahitam")},
         "chapters": []}

for a in sorted(parsed["book"], key=int):
    for h in sorted(parsed["book"][a], key=int):
        units = parsed["book"][a][h]
        ANALYSES_LOCAL_KEYS = set()
        out_units = []
        for u in units:
            segs = []
            for sgm in u["segments"]:
                toks = process_text(sgm["x"])
                for t in toks:
                    if isinstance(t, list):
                        ANALYSES_LOCAL_KEYS.add(t[1])
                d = {"t": sgm["t"], "w": toks}
                if sgm["t"] == "s":
                    d["id"] = sgm["id"]
                    d["i"] = sgm["x"]
                segs.append(d)
            out_units.append({"id": u["id"], "sutras": u["sutras"], "segs": segs})
        # compact keys
        keys = sorted(ANALYSES_LOCAL_KEYS)
        kid = {k: i for i, k in enumerate(keys)}
        for ou in out_units:
            for sg in ou["segs"]:
                sg["w"] = [[t[0], kid[t[1]]] if isinstance(t, list) else t for t in sg["w"]]
        lex = [ANALYSES[k] for k in keys]
        cid = f"{a}.{h}"
        json.dump({"id": cid, "units": out_units, "lex": lex}, open(os.path.join(DATA, f"nyaya-{cid}.json"), "w", encoding="utf-8"),
                  ensure_ascii=False, separators=(",", ":"))
        first = [s for u in units for s in u["segments"] if s["t"] == "s"]
        index["chapters"].append({"id": cid, "adhyaya": int(a), "ahnika": int(h), "title": f"{TITLES[a]} · {AHN[h]}",
                                  "nsutras": len(first), "topic": TOPICS[f"{a}.{h}"],
                                  "sutras": [[s["id"], deva(s["x"]), s["x"]] for s in first]})

# glosses keyed by IAST lemma
gl = {}
for lem, ent in GLOSS.items():
    gl[ent["i"]] = {k: v for k, v in ent.items() if k != "i"}
json.dump(gl, open(os.path.join(DATA, "glossary.json"), "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
json.dump(index, open(os.path.join(DATA, "index.json"), "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))

# report
nw = len(ANALYSES)
nfail = sum(1 for e in ANALYSES.values() if not e["p"])
nq = sum(1 for e in ANALYSES.values() if e.get("q"))
nogloss = [l for l, e in GLOSS.items() if "m" not in e]
print(f"unique word-keys {nw}, unanalysed {nfail}, low-confidence {nq}, lemmas {len(GLOSS)}, lemmas without gloss {len(nogloss)}")
json.dump({"fail": fail.most_common(400), "freq": [(iast(l), c, GLOSS.get(l, {}).get('s')) for l, c in lemma_freq.most_common(1500)],
           "nogloss": [iast(x) for x in nogloss]},
          open(os.path.join(ROOT, "report.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=0)
