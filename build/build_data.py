"""Tokenise every parsed text, analyse every word, and write the site's data files.

    python3 build_data.py                 # every text
    python3 build_data.py nyaya tarkasangraha   # only these (library.json is always rewritten)

Inputs:  parsed.json (Nyāyasūtra + Bhāṣya, from parse_text.py) and parsed/<id>.json (from parse_texts.py)
Outputs: ../data/library.json, ../data/<id>/index.json, ../data/<id>/<chapter>.json, ../data/<id>/glossary.json
"""
import json, re, os, sys, collections, difflib, math
from vidyut.lipi import transliterate, Scheme
from morph import Analyzer, iast, slp, VOWELS
from texts_meta import LIBRARY, TEXTS

ROOT = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(ROOT, "..")
DATA = os.path.join(SITE, "data")
os.makedirs(DATA, exist_ok=True)

curated_iast = json.load(open(os.path.join(ROOT, "curated.json"), encoding="utf-8"))
overrides = json.load(open(os.path.join(ROOT, "overrides.json"), encoding="utf-8"))
navya_iast = json.load(open(os.path.join(ROOT, "curated_navya.json"), encoding="utf-8"))


def _load(d):
    out = {}
    for k, v in d.items():
        if k.startswith("_") or k.endswith("_") or not v or "_" in k:
            continue
        out[slp(k)] = v
    return out


curated = _load(curated_iast)       # Nyāyasūtra-Bhāṣya senses
navya = _load(navya_iast)           # senses for the later texts
stems_curated = dict(navya)
stems_curated.update(curated)
mw = json.load(open(os.path.join(ROOT, "mw_index.json"), encoding="utf-8"))
A = Analyzer(os.path.join(ROOT, "vdata"), os.path.join(ROOT, "mw_index.json"), stems_curated)


def deva(s):
    return transliterate(s, Scheme.Iast, Scheme.Devanagari)


LET = "a-zA-Zāīūṛṝḷḹṅñṭḍṇśṣṃḥ"
TOK = re.compile(rf"(//\s*\d+\s*//|//|/|---|``|''|[,;?!:]|'?[{LET}]+|\d+|\n|\S)")


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


GLOSS = {}   # lemma SLP1 -> {"i": iast, "m": meaning, "s": source, ...}


def gloss_for(lem):
    if lem in GLOSS:
        return
    ent = {"i": iast(lem)}
    c = curated.get(lem) or navya.get(lem)
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


def analyse(tok, nxt, hints=None):
    hs = ",".join(f"{k}{p}" for k, p in sorted(hints)) if hints else ""
    key = tok + "|" + nxt + ("|" + hs if hs else "")
    if key in ANALYSES:
        return key
    iast_tok = tok
    s = slp(iast_tok)
    if s.startswith("'"):
        s = "a" + s[1:]
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
    r = A.split(s, nxt, frozenset(hints) if hints else None)
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


# ------------------------------------------------------------------ analytic hints
def hint_map(cont, analytic):
    """Boundaries of an analytic (hyphenated, pada-separated) version mapped onto the words of the
    continuous text: {word index: {("c"|"f", position in the word's SLP1 form)}}."""
    ctoks = [t for k, t in tokenize(cont) if k == "w"]
    cs = [slp(t[1:] if t.startswith("'") else t) for t in ctoks]
    off = [t.startswith("'") for t in ctoks]
    cstr = "".join(cs)
    cmap = [(ti, k) for ti, w in enumerate(cs) for k in range(len(w))]
    pieces = [slp(p) for p in re.findall(rf"[{LET}]+", analytic.replace("'", ""))]
    astr, ab = "", []
    for p in pieces:
        if astr:
            ab.append(len(astr))
        astr += p
    if not astr or not cstr:
        return {}
    sm = difflib.SequenceMatcher(None, astr, cstr, autojunk=False)
    amap, fused = {}, {}
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            for k in range(i2 - i1):
                amap[i1 + k] = j1 + k
        elif tag in ("replace", "delete"):
            for k in range(i1, i2):
                fused[k] = min(j1, len(cstr) - 1)
    out = {}
    for b in ab:
        if b in amap and (b - 1) in amap and amap[b] == amap[b - 1] + 1:
            ti, pos = cmap[amap[b]]
            kind = "c"
        else:
            ci = fused.get(b, fused.get(b - 1))
            if ci is None:
                continue
            ti, pos = cmap[ci]
            kind = "f"
        if pos > 0:
            out.setdefault(ti, set()).add((kind, pos + (1 if off[ti] else 0)))
    return out


def process_text(text, analytic=None):
    toks = tokenize(text)
    hm = hint_map(text, analytic) if analytic else {}
    out = []
    wi = -1
    for i, (kind, t) in enumerate(toks):
        if kind == "p":
            out.append(punct(t))
            continue
        wi += 1
        nx = ""
        if i + 1 < len(toks) and toks[i + 1][0] == "w":
            nt = slp(toks[i + 1][1])
            nx = "a" if nt.startswith("'") else nt[0]
        key = analyse(t, nxt_class(nx), hm.get(wi))
        out.append([t, key])
    return join_words(out)


CONS_END = set("kgṅcjñṭḍṇtdnpbmyrlvśṣsh")


def join_words(out):
    """Write the text as a Devanagari print would: a word ending in a consonant runs on into the next
    word (viśeṣās tv anantā → विशेषास्त्वनन्ता), and an avagraha joins the word before it.
    The joined form is one clickable word whose popup lists the parts of all its words."""
    res = []
    i = 0
    while i < len(out):
        t = out[i]
        if not isinstance(t, list):
            res.append(t)
            i += 1
            continue
        group = [t]
        while i + 1 < len(out) and isinstance(out[i + 1], list) and (group[-1][0][-1] in CONS_END or out[i + 1][0].startswith("'")):
            group.append(out[i + 1])
            i += 1
        i += 1
        if len(group) == 1:
            res.append([deva(t[0]), t[1]])
            continue
        word = "".join(g[0] for g in group)
        key = "+".join(g[1] for g in group)
        if key not in ANALYSES and word in overrides:     # a correction made to the joined word
            ov = overrides[word]
            parts = [{"u": q[0], "l": q[1], "g": q[2] if len(q) > 2 else "", "d": deva(q[0]), "ld": deva(q[1])} for q in ov["p"]]
            for q in ov["p"]:
                gloss_for(slp(q[1]))
            ANALYSES[key] = {"w": word, "p": parts, "v": 1, **({"n": ov["n"]} if ov.get("n") else {})}
        if key not in ANALYSES:
            es = [ANALYSES[g[1]] for g in group]
            e = {"w": word, "p": [p for x in es for p in x["p"]]}
            if any(not x["p"] for x in es) or any(x.get("q") for x in es):
                e["q"] = 1
            if all(x.get("v") for x in es):
                e["v"] = 1
            ANALYSES[key] = e
        res.append([deva(word), key])
    return res


def nav_deva(x):
    s = join_plain(plain(x))
    s = re.sub(r"\s*//\s*", " ॥ ", s)
    s = re.sub(r"\s*/\s*", " । ", s).replace("---", "—").replace("``", "“").replace("''", "”")
    return deva(s.strip())


def join_plain(s):
    """The same joining for plain strings (sidebar and search labels)."""
    s = re.sub(rf"(?<=[{''.join(CONS_END)}]) (?=[{LET}'])", "", s)
    return re.sub(r" (?=')", "", s)


# ------------------------------------------------------------------ texts
NS_TOPICS = {"1.1": "The sixteen categories enumerated and defined: means of knowledge, objects of knowledge, doubt, the five-membered argument",
             "1.2": "Kinds of debate, the five pseudo-reasons, quibble, futile rejoinder and points of defeat",
             "2.1": "Doubt examined; the means of knowledge defended — perception, inference, comparison and testimony",
             "2.2": "Other proposed means of knowledge; the impermanence of sound; what a word means",
             "3.1": "The self, the body, the senses and their objects",
             "3.2": "Cognition, the mind, and how a body comes to be",
             "4.1": "Faults, rebirth, fruit, pain and liberation; rival doctrines on causation",
             "4.2": "Knowledge of truth; wholes and parts; idealism refuted; the practice of yoga",
             "5.1": "The twenty-four futile rejoinders (jāti)",
             "5.2": "The twenty-two points of defeat (nigrahasthāna)"}
ROMAN = ["", "I", "II", "III", "IV", "V"]


def load_nyaya():
    parsed = json.load(open(os.path.join(ROOT, "parsed.json"), encoding="utf-8"))
    chapters = []
    for a in sorted(parsed["book"], key=int):
        for h in sorted(parsed["book"][a], key=int):
            units = []
            for u in parsed["book"][a][h]:
                segs = []
                for sg in u["segments"]:
                    if sg["t"] == "s":
                        segs.append({"t": "s", "id": sg["id"], "n": sg["id"], "x": sg["x"]})
                    elif sg["t"] == "b":
                        segs.append({"t": "b", "l": "bhasya", "x": sg["x"]})
                    else:
                        segs.append({"t": sg["t"], "x": sg["x"]})
                units.append({"id": u["id"], "segments": segs})
            cid = f"{a}.{h}"
            chapters.append({"id": cid, "title": f"Adhyāya {ROMAN[int(a)]} · Āhnika {h}", "group": f"Adhyāya {ROMAN[int(a)]}",
                             "short": f"Āhnika {h}", "topic": NS_TOPICS[cid], "units": units})
    return {"id": "nyaya", "chapters": chapters}


def load(tid):
    if tid == "nyaya":
        return load_nyaya()
    return json.load(open(os.path.join(ROOT, "parsed", tid + ".json"), encoding="utf-8"))


def seg_chars(u):
    return sum(len(sg["x"]) for sg in u["segments"])


def split_chapters(doc, limit=90000, target=60000):
    """Long chapters become several pages, cut between units (or between paragraphs of a very long unit)."""
    out = []
    for ch in doc["chapters"]:
        total = sum(seg_chars(u) for u in ch["units"])
        if total <= limit:
            out.append(ch)
            continue
        n = math.ceil(total / target)
        size = total / n
        # break over-long units into continuation pieces
        units = []
        for u in ch["units"]:
            if seg_chars(u) <= size * 1.35:
                units.append(u)
                continue
            piece, acc, k = [], 0, 0
            label = next((sg.get("n") for sg in u["segments"] if sg["t"] == "s"), None)
            for sg in u["segments"]:
                if acc >= size and sg["t"] in ("b", "p", "v"):
                    units.append({"id": u["id"] if k == 0 else f"{u['id']}~{k + 1}", "segments": piece})
                    k += 1
                    piece = [{"t": "k", "x": label or "", "of": u["id"]}]
                    acc = 0
                piece.append(sg)
                acc += len(sg["x"])
            units.append({"id": u["id"] if k == 0 else f"{u['id']}~{k + 1}", "segments": piece})
        parts, cur, acc = [], [], 0
        for u in units:
            c = seg_chars(u)
            if cur and acc + c / 2 > size and len(parts) < n - 1:
                parts.append(cur)
                cur, acc = [], 0
            cur.append(u)
            acc += c
        if cur:
            parts.append(cur)
        for k, us in enumerate(parts, 1):
            p = dict(ch)
            p["id"] = f"{ch['id']}-{k}"
            p["part"] = [k, len(parts)]
            p["base"] = ch["id"]
            p["units"] = us
            out.append(p)
    doc["chapters"] = out
    return doc


def plain(s):
    return re.sub(r"\s+", " ", s.replace("\n", " ")).strip()


def build_text(tid):
    meta = TEXTS[tid]
    doc = split_chapters(load(tid))
    analytic = {}
    if meta.get("analytic_from"):
        src = load(meta["analytic_from"])
        for ch in src["chapters"]:
            for u in ch["units"]:
                for sg in u["segments"]:
                    if sg["t"] == "s" and sg.get("a"):
                        analytic[sg["id"]] = (sg["x"], sg["a"])
    tdir = os.path.join(DATA, tid)
    os.makedirs(tdir, exist_ok=True)
    for f in os.listdir(tdir):
        if f.endswith(".json"):
            os.remove(os.path.join(tdir, f))
    index = {k: v for k, v in meta.items() if k not in ("analytic_from",)}
    index["id"] = tid
    index["chapters"] = []
    lemmas = set()
    for ch in doc["chapters"]:
        keys = set()
        out_units = []
        nav = []
        hn = gn = 0
        for u in ch["units"]:
            segs = []
            for sg in u["segments"]:
                a = sg.get("a")
                if sg["t"] == "s" and not a and analytic:
                    base = sg["id"].split("-")[0]
                    if base in analytic:
                        cx, ca = analytic[base]
                        if re.sub(r"[^a-zāīūṛṝḷḹṅñṭḍṇśṣṃḥ]", "", cx) == re.sub(r"[^a-zāīūṛṝḷḹṅñṭḍṇśṣṃḥ]", "", sg["x"]):
                            a = ca
                if sg["t"] in ("g", "k"):
                    d = {"t": sg["t"], "x": sg["x"]}
                    if sg["t"] == "g":
                        gn += 1
                        d["id"] = f"g{gn}"
                        nav.append(["g", d["id"], sg["x"], ""])
                    else:
                        d["of"] = sg.get("of", "")
                    segs.append(d)
                    continue
                toks = process_text(sg["x"], a)
                for t in toks:
                    if isinstance(t, list):
                        keys.add(t[1])
                d = {"t": sg["t"], "w": toks}
                if sg.get("l"):
                    d["l"] = sg["l"]
                if sg["t"] == "s":
                    d["id"] = sg["id"]
                    d["n"] = sg.get("n", sg["id"])
                    d["i"] = re.sub(r"\s*\n\s*", " ", sg["x"])
                    if sg.get("verse"):
                        d["verse"] = 1
                    nav.append(["s", sg["id"], nav_deva(sg["x"]), plain(sg["x"]), sg.get("n", sg["id"])])
                elif sg["t"] == "h":
                    hn += 1
                    d["id"] = f"h{hn}"
                    nav.append(["h", d["id"], nav_deva(sg["x"]), plain(sg["x"])])
                segs.append(d)
            out_units.append({"id": u["id"], "segs": segs})
        ks = sorted(keys)
        kid = {k: i for i, k in enumerate(ks)}
        for ou in out_units:
            for sg in ou["segs"]:
                if "w" in sg:
                    sg["w"] = [[t[0], kid[t[1]]] if isinstance(t, list) else t for t in sg["w"]]
        lex = [ANALYSES[k] for k in ks]
        for e in lex:
            for p in e["p"]:
                lemmas.add(p["l"])
                if p.get("r"):
                    lemmas.add(p["r"])
                for al in p.get("a", ()):
                    lemmas.add(al[0])
        json.dump({"id": ch["id"], "units": out_units, "lex": lex}, open(os.path.join(tdir, f"{ch['id']}.json"), "w", encoding="utf-8"),
                  ensure_ascii=False, separators=(",", ":"))
        roots = [n for n in nav if n[0] == "s"]
        cm = {"id": ch["id"], "title": ch["title"], "topic": ch.get("topic", "")}
        for k in ("group", "short", "deva_title", "part", "base", "appendix"):
            if ch.get(k):
                cm[k] = ch[k]
        if ch.get("deva_title"):
            cm["dt"] = deva(ch["deva_title"])
        if roots:
            cm["range"] = [roots[0][4], roots[-1][4]]
        cm["nroots"] = len({r[4] for r in roots})
        cm["nav"] = nav
        index["chapters"].append(cm)
    gl = {}
    for lem, ent in GLOSS.items():
        if ent["i"] in lemmas:
            e = {k: v for k, v in ent.items() if k != "i"}
            if tid != "nyaya" and lem in navya:
                nv = navya[lem]
                if e.get("s") == "mw":
                    e["mw"] = e.get("m")
                e["m"] = nv if isinstance(nv, str) else nv.get("m")
                e.pop("n", None)
                if isinstance(nv, dict) and nv.get("n"):
                    e["n"] = nv["n"]
                e["s"] = "c"
            gl[ent["i"]] = e
    json.dump(gl, open(os.path.join(tdir, "glossary.json"), "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    json.dump(index, open(os.path.join(tdir, "index.json"), "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    nroot = len({n[4] for c in index["chapters"] for n in c["nav"] if n[0] == "s"})
    print(f"{tid}: {len(index['chapters'])} pages, {nroot} root units, glossary {len(gl)}")
    return index


def write_library(built):
    lib = json.loads(json.dumps(LIBRARY))
    for tid, meta in TEXTS.items():
        f = os.path.join(DATA, tid, "index.json")
        if not os.path.exists(f):
            continue
        ix = json.load(open(f, encoding="utf-8"))
        base = {}
        for c in ix["chapters"]:
            base.setdefault(c.get("base", c["id"]), c)
        lib["texts"][tid] = {k: meta[k] for k in ("title", "deva", "author", "short", "blurb", "root") if k in meta}
        lib["texts"][tid]["nchapters"] = len(base)
        lib["texts"][tid]["npages"] = len(ix["chapters"])
        lib["texts"][tid]["nroots"] = len({n[4] for c in ix["chapters"] for n in c["nav"] if n[0] == "s"})
        lib["texts"][tid]["first"] = ix["chapters"][0]["id"]
    json.dump(lib, open(os.path.join(DATA, "library.json"), "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))


if __name__ == "__main__":
    which = sys.argv[1:] or list(TEXTS)
    built = []
    for t in which:
        built.append(build_text(t))
        # keep memory bounded across texts (the analyser caches grow large)
        for f in (A.pada, A.final_pada, A.kosha_get, A.participle, A.obscurity):
            f.cache_clear()
    write_library(built)
    nw = len(ANALYSES)
    nfail = sum(1 for e in ANALYSES.values() if not e["p"])
    nq = sum(1 for e in ANALYSES.values() if e.get("q"))
    nogloss = [l for l, e in GLOSS.items() if "m" not in e]
    print(f"unique word-keys {nw}, unanalysed {nfail}, low-confidence {nq}, lemmas {len(GLOSS)}, lemmas without gloss {len(nogloss)}")
    json.dump({"fail": fail.most_common(800), "freq": [(iast(l), c, GLOSS.get(l, {}).get('s')) for l, c in lemma_freq.most_common(3000)],
               "nogloss": [iast(x) for x in nogloss]},
              open(os.path.join(ROOT, "report.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=0)
