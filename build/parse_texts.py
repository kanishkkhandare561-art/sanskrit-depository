"""Parse the further GRETIL Nyāya texts into the depository's common structure.

    python3 parse_texts.py            # writes parsed/<text-id>.json for every text below

Each output file looks like
    {"id": ..., "chapters": [{"id", "title", "group", "topic", "units": [
        {"id": ..., "segments": [{"t": kind, "x": text, ...}]}]}]}
Segment kinds:  s = root text (sūtra / section), with "id" and "n" (label)
                b = commentary paragraph, with "l" (layer key)
                p = running main text (for a text without a commentary)
                v = verse (lines separated by "\\n"), with "l" when part of a commentary
                h = heading inside a chapter;  c = colophon;  g = page reference of the printed edition
The display text is kept exactly as written in the source (no sandhi splitting); only
encoding debris, page markers and footnote numerals are removed.
"""
import json, os, re, sys, difflib

ROOT = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(ROOT, "source")
OUT = os.path.join(ROOT, "parsed")
os.makedirs(OUT, exist_ok=True)

L = "a-zāīūṛṝḷḹṅñṭḍṇśṣṃḥ"
LET = set("abcdefghijklmnopqrstuvwxyzāīūṛṝḷḹṅñṭḍṇśṣṃḥ")


def body(path, marker="\nText\n"):
    raw = open(path, encoding="utf-8").read().replace("\r", "")
    return raw[raw.index(marker) + len(marker):]


# ---------------------------------------------------------------- cleaning
def fix_quotes(s):
    """Tell apart avagraha (') and quotation marks in the converted texts."""
    out = []
    n = len(s)
    for i, ch in enumerate(s):
        if ch != "'":
            out.append(ch)
            continue
        if i + 1 < n and s[i + 1] == "'":          # '' already a closing quote
            out.append(ch)
            continue
        if i > 0 and s[i - 1] == "'":
            out.append(ch)
            continue
        prev = s[i - 1] if i else " "
        nxt = s[i + 1] if i + 1 < n else " "
        if prev in LET and nxt in LET:
            out.append(" '" if prev in "eo" else " ``")
        elif prev in LET:
            out.append("''")
        elif nxt in LET:
            j = i - 1
            while j >= 0 and s[j] == " ":
                j -= 1
            pw = s[j] if j >= 0 else " "
            out.append("'" if pw in "eo" else "``")
        else:
            out.append(" ")
    s = "".join(out)
    # straight double quotes: alternate open / close
    parts = s.split('"')
    if len(parts) > 1:
        s = parts[0]
        for k, p in enumerate(parts[1:]):
            s += (" ``" if k % 2 == 0 else "'' ") + p
    return s


def clean(s, keep_numbers=True):
    s = s.replace("‌", "").replace("‍", "").replace("\t", " ")
    s = re.sub(r"\[\s*(?:pṛ\.?\s*)?\d+\s*\]", " ", s)              # [377], [pṛ.1]
    s = re.sub(r"\(\s*\d+\s*/\s*\d+\s*\)", " ", s)                # ( 215 / 4)
    s = re.sub(r"#\s*([^#]{1,40}?)\s*#", r"(\1)", s)               # # 2/1/34 #
    s = re.sub(rf"(?<=[{L}])\d+", "", s)                           # footnote numerals glued to words
    s = re.sub(rf"(?<![\d/.\s-])\d+(?=[{L}])", "", s)
    s = re.sub(rf"(?:(?<=\s)|^)\d+(?=[{L}])", "", s)
    s = re.sub(r"(?<=\d)/(?=\d)", ".", s)                          # 2/1/34 -> 2.1.34
    s = re.sub(r"[`]{1,2}", "``", s)
    s = fix_quotes(s)
    s = re.sub(rf"(?<=[{L}])-\s*(?=[{L}])", "", s)                 # hyphenated compounds / line breaks
    s = re.sub(r"\s*-{2,}\s*", " --- ", s)
    s = re.sub(r"(?<=\s)-(?=\s)|(?<=\s)-(?=[{L}])|(?<=[{L}])-(?=\s)".format(L=L), " --- ", s)
    s = re.sub(r"\s*/\s*/\s*", " // ", s)
    s = re.sub(r"(?<!/)/(?!/)", " / ", s)
    s = re.sub(r"\.\s*(?=\d)", "", s) if not keep_numbers else s
    s = re.sub(r"\s+", " ", s).strip()
    s = re.sub(r"^(?:/|//|,)\s*", "", s)
    return s


def letters(s):
    return re.sub(rf"[^{L}]", "", s)


def is_junk(line):
    t = line.strip()
    return not t or re.fullmatch(r"[/\s.\-]*(dṛ)?[/\s.\-]*", t) is not None or t in ("oṃ", "śrīḥ", "// śrīḥ //", "/ śrīḥ/", "śrīḥ/")


# ---------------------------------------------------------------- analytic hints (Tarkasaṃgraha)
def hint_positions(cont, analytic):
    """Map the boundaries of the analytic (hyphen/space-separated) version onto the
    continuous text.  Returns {token_index: [("c"|"f", pos_in_token), ...]} where c = clean
    boundary before pos and f = boundary at a fused vowel at pos."""
    ctoks = [m for m in re.finditer(rf"'?[{L}]+", cont)]
    cstr = "".join(m.group(0).lstrip("'") for m in ctoks)
    cmap = []    # index in cstr -> (token idx, pos in token)
    for ti, m in enumerate(ctoks):
        w = m.group(0).lstrip("'")
        for k in range(len(w)):
            cmap.append((ti, k))
    apieces = re.findall(rf"[{L}]+|[-\s]+|.", analytic.replace("'", ""))
    astr, abound = "", []
    for p in apieces:
        if re.fullmatch(rf"[{L}]+", p):
            if astr:
                abound.append(len(astr))
            astr += p
    if not astr:
        return {}
    sm = difflib.SequenceMatcher(None, astr, cstr, autojunk=False)
    amap = {}
    fused = {}
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            for k in range(i2 - i1):
                amap[i1 + k] = j1 + k
        elif tag == "replace" or tag == "delete":
            for k in range(i1, i2):
                fused[k] = min(j1, len(cstr) - 1)
    hints = {}
    for b in abound:
        if b in amap and (b - 1) in amap and amap[b] == amap[b - 1] + 1:
            ci = amap[b]
            ti, pos = cmap[ci]
            if pos > 0:
                hints.setdefault(ti, []).append(("c", pos))
        else:
            ci = fused.get(b, fused.get(b - 1))
            if ci is None and b in amap:
                ci = amap[b] - 1
            if ci is not None and 0 <= ci < len(cmap):
                ti, pos = cmap[ci]
                if pos > 0:
                    hints.setdefault(ti, []).append(("f", pos))
    return hints


# ---------------------------------------------------------------- 1. Tarkasaṃgraha (mūla)
TS_CHAPTERS = [
    ("1", "pratyakṣaparicchedaḥ", "Pratyakṣa-pariccheda", 1, 43,
     "The seven categories, the nine substances and twenty-four qualities; cognition, causes, and perception"),
    ("2", "anumānaparicchedaḥ", "Anumāna-pariccheda", 44, 57,
     "Inference: pervasion, the five-membered argument, kinds of probans, and the pseudo-reasons"),
    ("3", "upamānaparicchedaḥ", "Upamāna-pariccheda", 58, 58,
     "Comparison: knowing what a word names through similarity"),
    ("4", "śabdaparicchedaḥ", "Śabda-pariccheda", 59, 63,
     "Verbal testimony: words, meaning, expectancy, compatibility and proximity"),
    ("5", "ayathārthānubhavādinirūpaṇam", "Erroneous cognition and the remaining categories", 64, 82,
     "Doubt, error and hypothetical reasoning; memory, pleasure, pain and the other qualities; motion, universals, particularity, inherence and absence"),
]


# keying errors in GRETIL's standard text of the Tarkasaṃgraha (also used for the root text of the Dīpikā edition)
TS_TYPO = [("ntyāḥ", "nityāḥ"), ("niyyaṃ", "nityaṃ"), ("saparśaḥ", "sparśaḥ"), ("daravatvam", "dravatvam"), ("kālakṛthaṃ", "kālakṛtaṃ"),
           ("kāla-kṛthaṃ", "kāla-kṛtaṃ"), ("śitasparśa", "śītasparśa"), ("śita-sparśa", "śīta-sparśa"), ("śitoṣṇ", "śītoṣṇ"),
           ("śita-uṣṇa", "śīta-uṣṇa"), ("pṛthagtvaṃ", "pṛthaktvaṃ"), ("snnikarṣa", "sannikarṣa"), ("brahmaṇo'yaṃ", "brāhmaṇo'yaṃ"),
           ("abhāvaparatyakṣe", "abhāvapratyakṣe"), ("bhṛtalam", "bhūtalam"), ("saparakārakaṃ", "saprakārakaṃ"),
           ("liṅgaparāmarṣaṃ", "liṅgaparāmarśa"), ("prayukte", "prayuṅkte"), ("pṛthivī tarebhyo", "pṛthivītarebhyo"),
           ("abhidhyatva", "abhidheyatva"), ("utpadyte", "utpadyate"), ("gosadṛṣaṃ", "gosadṛśaṃ"), ("go-sadṛṣaṃ", "go-sadṛśaṃ"),
           ("purṣo", "puruṣo"), ("sarveśām", "sarveṣām"), ("sarveśāṃ", "sarveṣāṃ"), ("prehare", "prahare"),
           ("sādhanavann iṣṭātyantābhāva", "sādhanavanniṣṭhātyantābhāva"), ("sādhanavann iṣṭa-atyanta", "sādhanavan-niṣṭha-atyanta"),
           ("sādhāraṇāvyapakatvam", "sādhanāvyāpakatvam"), ("sādhāraṇa-avyapakatvam", "sādhana-avyāpakatvam"),
           ("atrārdrendhasaṃyoga", "atrārdrendhanasaṃyoga"), ("ardra-indhasaṃyoga", "ārdra-indhana-saṃyoga"),
           ("tatrārdrendhnasaṃyoga", "tatrārdrendhanasaṃyoga"), ("ardra-indhna-saṃyoga", "ārdra-indhana-saṃyoga"),
           ("ardrendhanasaṃyoga", "ārdrendhanasaṃyoga"), ("ardra-indhana", "ārdra-indhana"),
           ("sādhyabhāvasādhakaṃ", "sādhyābhāvasādhakaṃ"), ("sādhya-bhāva-sādhakaṃ", "sādhya-abhāva-sādhakaṃ"), ("lingāt", "liṅgāt"),
           ("anvayadṛṣṭanto", "anvayadṛṣṭānto"), ("yatra śabdo nityaḥ kṛtakatvād", "yathā śabdo nityaḥ kṛtakatvād"),
           ("dvanyātmak", "dhvanyātmak"), ("dvany-ātmak", "dhvany-ātmak"), ("sādhyabhāva", "sādhyābhāva"),
           ("khagatarūpādeḥ", "svagatarūpādeḥ"), ("khagata-rūpādeḥ", "svagata-rūpādeḥ"), ("liṅgaparāmarśā'numānam", "liṅgaparāmarśo 'numānam"),
           ("liṅga-parāmarśā'numānam", "liṅga-parāmarśo 'numānam"), ("evāvatiṣṭate", "evāvatiṣṭhate"), ("eva avatiṣṭate", "eva avatiṣṭhate"),
           ("ayutasiddau", "ayutasiddhau"), ("bālāvyutpatti", "bālavyutpatti"), ("bālā-vyutpatti", "bāla-vyutpatti")]


def ts_fix(x):
    for a, b in TS_TYPO:
        x = x.replace(a, b)
    return x


def ts_chapter_of(n):
    for c in TS_CHAPTERS:
        if c[3] <= n <= c[4]:
            return c
    return TS_CHAPTERS[-1]


def parse_tarkasangraha():
    t = body(os.path.join(SRC, "tarkasangraha-gretil.txt"))
    blocks = [b for b in re.split(r"\n\s*\n", t) if b.strip()]
    pairs = []
    i = 0
    while i < len(blocks):
        b = blocks[i]
        m = re.search(r"\(?AnTs_(p?\d+)\)?\s*$", b.strip())
        if not m:
            i += 1
            continue
        cont = b.strip()[: m.start()].strip()
        ana = blocks[i + 1].strip() if i + 1 < len(blocks) else ""
        num = m.group(1)
        pairs.append((num, cont, ana))
        i += 2
    chapters = {}
    for num, cont, ana in pairs:
        n = 82 if num.startswith("p") else int(num)
        lines = [clean(ts_fix(x)) for x in cont.split("\n") if x.strip()]
        text = " \n ".join(lines) if n in (1, 82) else " ".join(lines)
        anat = ts_fix(" ".join(ana.split()))
        ch = ts_chapter_of(n)
        c = chapters.setdefault(ch[0], {"id": ch[0], "title": ch[2], "deva_title": ch[1], "topic": ch[5], "units": []})
        seg = {"t": "s", "id": str(n), "n": str(n) if n < 82 else "End", "x": text, "a": anat}
        if n == 82:
            seg["verse"] = 1
        if n == 1:
            seg["verse"] = 1
        c["units"].append({"id": str(n), "segments": [seg]})
    return {"id": "tarkasangraha", "chapters": [chapters[k] for k in sorted(chapters, key=int)]}


# ---------------------------------------------------------------- 2. Tarkasaṃgraha with Dīpikā, Prakāśikā, Bālapriyā, Prasāraṇā
LAYERS_DIPIKA = {"dīpikā": "dipika", "dipikā": "dipika", "prakāśikā": "prakasika", "pramāśikā": "prakasika", "prākāśikā": "prakasika",
                 "bālapriyā": "balapriya", "bālapiyā": "balapriya"}
TS_HEAD = ("tarkasaṅgrahaḥ", "tarkasaṃṅgrahaḥ", "tarkasaṃgrahaḥ")
PARICCHEDA = {"pratyakṣaparicchedaḥ", "anumānaparicchedaḥ", "upamānaparicchedaḥ", "śabdaparicchedaḥ"}


def syllables(line):
    t = letters(line.replace("ai", "e").replace("au", "o"))
    return len(re.findall(r"[aāiīuūṛṝḷḹeo]", t))


def verse_shape(grp):
    """True if 2 or 4 lines look like a verse: equal syllable counts per half / pāda, ending in //."""
    if len(grp) not in (2, 4):
        return False
    ends = [re.sub(rf"[^{L}/]+$", "", g).rstrip() for g in grp]
    if not re.search(r"//\s*$", re.sub(r"\d+", "", grp[-1]).replace(".", "").strip(" '`\"")) and not ends[-1].endswith("//"):
        return False
    cnt = [syllables(re.sub(r"[/\d.]+", "", g)) for g in grp]
    if len(grp) == 2:
        if not grp[0].rstrip(" '`\"").endswith("/"):
            return False
        return (abs(cnt[0] - cnt[1]) <= 1 and 14 <= cnt[0] <= 24) or (cnt[0] == cnt[1] and 24 < cnt[0] <= 34)
    if ends[0].endswith("/") or ends[2].endswith("/") or not ends[1].endswith("/"):
        return False
    return max(cnt) - min(cnt) <= 1 and 8 <= cnt[0] <= 21


def logical_lines(lines, headers=()):
    """Merge mid-sentence page breaks and two- or four-line verses in files where every line is a paragraph."""
    out = []
    i = 0
    ls = [x.strip() for x in lines]
    ls = [x for x in ls if x and not is_junk(x)]
    stop = set(headers)
    while i < len(ls):
        x = ls[i]
        hit = False
        for k in (2, 4):
            grp = ls[i:i + k]
            if len(grp) == k and not any(g in stop or g.startswith("AnTs_") or len(g) > 110 for g in grp) and verse_shape(grp):
                out.append(("v", grp))
                i += k
                hit = True
                break
        if hit:
            continue
        # paragraph continuing over a page break
        if len(x) >= 60 and not re.search(r"[/?:.!)'\"]\s*$", x) and not x.startswith("AnTs_"):
            nx = ls[i + 1] if i + 1 < len(ls) else ""
            heading_like = len(nx) < 48 and not re.search(r"[/?]", nx)
            colophon = x.startswith("iti ") and re.search(r"pariccheda|paricchada|samāpt", x)
            if nx and not nx.startswith("AnTs_") and nx not in stop and nx[:1] in LET and not heading_like and not colophon:
                ls[i + 1] = x + " " + ls[i + 1]
                i += 1
                continue
        out.append(("l", x))
        i += 1
    return out


def parse_dipika():
    raw = body(os.path.join(SRC, "tarkasangraha-dipika-gretil.txt"))
    lines = raw.split("\n")
    # main text: from the first "pratyakṣaparicchedaḥ" heading after the contents list
    start = next(i for i, x in enumerate(lines) if x.strip() == "śrīgurucaraṇāravindābhyāṃ namaḥ")
    pras = next(i for i, x in enumerate(lines) if x.strip().startswith("prakāśikāvyākhyā prasāraṇā"))
    hdr = set(LAYERS_DIPIKA) | set(TS_HEAD) | PARICCHEDA
    main = logical_lines(lines[start + 1: pras], hdr)
    appx = logical_lines(lines[pras + 1:], hdr)

    units = []
    cur = None
    layer = None
    pending_head = []
    uid = 0

    def new_unit(kind="u"):
        nonlocal cur, uid
        uid += 1
        cur = {"id": f"{kind}{uid}", "segments": []}
        units.append(cur)
        return cur

    last_root = None
    root_seen = {}
    colo_open = False
    for kind, x in main:
        if kind == "v":
            if cur is None:
                new_unit()
            vt = " \n ".join(clean(g) for g in x)
            cur["segments"].append({"t": "v", "x": vt, "l": layer or "mula"})
            colo_open = False
            continue
        s = x.strip()
        if s in TS_HEAD:
            new_unit()
            layer = "mula"
            last_root = None
            colo_open = False
            continue
        if s.startswith("dīpikā-prakāśikā-bālapriyā"):
            continue
        if s in LAYERS_DIPIKA:
            layer = LAYERS_DIPIKA[s]
            colo_open = False
            if cur is None:
                new_unit()
            continue
        m = re.match(r"AnTs_(\d+)(ab|cd|\[\d\])?\s+(.*)", s)
        if m:
            n = int(m.group(1))
            if cur is None or any(sg["t"] == "s" and sg["id"].split("-")[0] != str(n) for sg in cur["segments"]) or \
               any(sg["t"] in ("b",) for sg in cur["segments"]):
                if not (cur and not any(sg["t"] in ("s", "b", "v") for sg in cur["segments"])):
                    new_unit()
            k = root_seen.get(n, 0) + 1
            root_seen[n] = k
            anchor = str(n) if k == 1 else f"{n}-{k}"
            seg = {"t": "s", "id": anchor, "n": str(n), "x": clean(ts_fix(m.group(3)))}
            if m.group(2) == "cd" and cur["segments"] and cur["segments"][-1]["t"] == "s":
                cur["segments"][-1]["x"] += " \n " + seg["x"]
                cur["segments"][-1]["verse"] = 1
                root_seen[n] -= 1
            else:
                cur["segments"].append(seg)
                last_root = seg
            layer = "mula"
            colo_open = False
            continue
        if re.match(r"^(//\s*)?it\.?i\s", s) and len(s) < 120 and ("pariccheda" in s or "paricchada" in s or "samāpt" in s or s.endswith("vyākhyāyāṃ") or s.endswith("bālapriyāyāṃ")):
            if cur is None:
                new_unit()
            cur["segments"].append({"t": "c", "x": clean(s.replace("it.i", "iti"))})
            colo_open = not re.search(r"(pariccheda[ḥa]|paricchadaḥ|samāptaḥ?|samāptā)\s*/*\s*$", s)
            continue
        if colo_open and len(s) < 60:
            cur["segments"][-1]["x"] += " " + clean(s)
            colo_open = not re.search(r"(pariccheda[ḥa]|samāptaḥ?|samāptā)\s*/*\s*$", s)
            continue
        colo_open = False
        if s == "000":
            continue
        if s in PARICCHEDA or s == "bālapriyā samāptā":
            if s == "bālapriyā samāptā":
                cur["segments"].append({"t": "c", "x": clean(s)})
            continue
        if cur is None:
            new_unit()
        if re.match(r"^\d+\.\s", s):
            cur["segments"].append({"t": "b", "l": "notes", "x": clean(re.sub(r"^\d+\.\s*", "", s))})
            continue
        # editor's reprint of the root text right after an AnTs line: drop if it repeats it
        if layer == "mula" and last_root is not None:
            a, b = letters(last_root["x"]), letters(s)
            if difflib.SequenceMatcher(None, a, b, autojunk=False).ratio() > 0.55 or (len(b) < len(a) and b and b in a):
                continue
        if len(s) < 48 and not re.search(r"[/?]\s*$", s) and "/" not in s:
            if cur["segments"] and cur["segments"][-1]["t"] == "c":
                new_unit()
            cur["segments"].append({"t": "h", "x": clean(s)})
            continue
        cur["segments"].append({"t": "b", "l": layer if layer and layer != "mula" else "dipika", "x": clean(s)})

    # chapter assignment by the first root number of each unit
    starts = {1: 0, 44: 1, 58: 2, 59: 3, 64: 4}
    chs = [{"id": c[0], "title": c[2], "deva_title": c[1], "topic": c[5], "units": []} for c in TS_CHAPTERS]
    ci = 0
    for u in units:
        roots = [int(sg["n"]) for sg in u["segments"] if sg["t"] == "s"]
        if roots and roots[0] in starts:
            ci = starts[roots[0]]
        u["segments"] = [sg for sg in u["segments"] if sg.get("x")]
        if u["segments"]:
            chs[ci]["units"].append(u)

    # appendix: the Prasāraṇā
    PRAS = [("p1", "pratyakṣaparicchedaḥ", "Prasāraṇā on the Pratyakṣa-pariccheda"),
            ("p2", "anumānaparicchedaḥ", "Prasāraṇā on the Anumāna-pariccheda"),
            ("p3", "upamānaparicchedaḥ", "Prasāraṇā on the Upamāna-pariccheda"),
            ("p4", "śabdaparicchedaḥ", "Prasāraṇā on the Śabda-pariccheda")]
    pch = [{"id": a, "title": c, "deva_title": b, "topic": "Kṛṣṇatātācārya’s Prasāraṇā, a gloss on the Prakāśikā", "units": [], "appendix": 1} for a, b, c in PRAS]
    pi = 0
    cur = None
    started = set()
    for kind, x in appx:
        if kind == "v":
            if cur is None:
                cur = {"id": f"q{len(pch[pi]['units'])+1}", "segments": []}
                pch[pi]["units"].append(cur)
            cur["segments"].append({"t": "v", "l": "prasarana", "x": " \n ".join(clean(g) for g in x)})
            continue
        s = x.strip()
        if s in PARICCHEDA:
            idx = [p[1] for p in PRAS].index(s)
            if idx > pi or (idx == 0 and 0 not in started):
                pi = idx
                started.add(idx)
                cur = None
                continue
            continue
        if s.endswith("samāptaḥ") and len(s) < 40:
            continue
        if (re.match(r"^(//\s*)?iti\s", s) and len(s) < 120 and ("pariccheda" in s or "samāpt" in s or s.endswith("vyākhyāyāṃ"))) or s == "samāptaḥ":
            if cur is None:
                continue
            cur["segments"].append({"t": "c", "x": clean(s.strip("/ "))})
            continue
        if len(s) < 48 and "/" not in s:
            cur = {"id": f"q{pi+1}-{len(pch[pi]['units'])+1}", "segments": [{"t": "h", "x": clean(s)}]}
            pch[pi]["units"].append(cur)
            continue
        if cur is None:
            cur = {"id": f"q{pi+1}-{len(pch[pi]['units'])+1}", "segments": []}
            pch[pi]["units"].append(cur)
        cur["segments"].append({"t": "b", "l": "prasarana", "x": clean(s)})
    return {"id": "tarkasangraha-dipika", "chapters": chs + pch}


# ---------------------------------------------------------------- 3. Tattvacintāmaṇi, Śabdakhaṇḍa
TC_VADA = [
    ("śabdaprāmāṇyavāda", r"śabdāprāmāṇyavādaḥ", "Śabdaprāmāṇyavāda", "Whether words are a means of knowledge in their own right, not a form of inference"),
    ("ākāṅkṣāvāda", r"śabdākāṅkṣāvādapūrvapakṣaḥ", "Ākāṅkṣāvāda", "Syntactic expectancy between the words of a sentence"),
    ("yogyatāvāda", r"yogyatāvādaḥ", "Yogyatāvāda", "Semantic compatibility: the absence of anything that contradicts the sentence-meaning"),
    ("āsattivāda", r"āsattivādaparvapakṣaḥ", "Āsattivāda", "Proximity: words must be heard without interruption"),
    ("tātparyavāda", r"tātparyavādaḥ", "Tātparyavāda", "The speaker’s intention as a condition of verbal knowledge"),
    ("śabdānityatāvāda", r"śabdanityatāvādapūrvapakṣaḥ", "Śabdānityatāvāda", "Against the Mīmāṃsā doctrine that sound is eternal"),
    ("ucchanna-pracchannavāda", r"ucchanna-pracchannavādaḥ", "Ucchanna-pracchannavāda", "Lost and hidden Vedic branches, and the authority of smṛti"),
    ("vidhivāda", r"vidhivādapūrvapakṣaḥ", "Vidhivāda", "What an injunction (the optative suffix) means"),
    ("apūrvavāda", r"apūrvavādapūrvapakṣaḥ", "Apūrvavāda", "The unseen potency that links a ritual act to its later fruit"),
    ("kāryānvitaśaktivāda", r"kāryānvitaśaktivādapūrvapakṣaḥ", "Kāryānvitaśaktivāda", "Against the Prābhākara view that words denote only what is connected with something to be done"),
    ("jātiśaktivāda", r"jātiśaktivādaḥ", "Jātiśaktivāda", "Whether a word denotes the universal, the individual, or the individual as qualified by the universal"),
]


def parse_tc():
    t = body(os.path.join(SRC, "tattvacintamani-sabdakhanda-gretil.txt"))
    blocks = [b.strip() for b in re.split(r"\n\s*\n", t) if b.strip()]
    chapters = []
    cur_ch = None
    cur = None
    page = None
    for b in blocks:
        s = " ".join(x.strip() for x in b.split("\n"))
        m = re.match(r"\(Bibl\. Ind\. 98,\s*IV,?\s*(\d)?,?\s*p\.\s*(\d+)\)", s)
        if m:
            page = f"{m.group(1) or ''}{'.' if m.group(1) else ''}{m.group(2)}"
            page = m.group(2)
            if cur is not None:
                cur["segments"].append({"t": "g", "x": "p. " + page})
            else:
                pend = page
            continue
        hit = None
        for k, (cid, pat, title, topic) in enumerate(TC_VADA):
            if re.fullmatch(rf"(tattvacintāmaṇau\s+)?{pat}", s):
                hit = k
        if hit is not None:
            cid, pat, title, topic = TC_VADA[hit]
            cur_ch = {"id": str(hit + 1), "title": title, "deva_title": re.sub(r"^tattvacintāmaṇau\s+", "", s), "topic": topic, "units": []}
            chapters.append(cur_ch)
            cur = {"id": f"{hit+1}.1", "segments": [{"t": "h", "x": clean(s)}]}
            if page:
                cur["segments"].insert(0, {"t": "g", "x": "p. " + page})
            cur_ch["units"].append(cur)
            continue
        if cur_ch is None:
            continue
        if len(s) < 50 and re.search(r"(pūrvapakṣaḥ|siddhāntaḥ|parvapakṣaḥ)$", s):
            cur = {"id": f"{cur_ch['id']}.{len(cur_ch['units'])+1}", "segments": [{"t": "h", "x": clean(s)}]}
            cur_ch["units"].append(cur)
            continue
        if re.fullmatch(r"\d+", s):
            continue
        txt = clean(s)
        if txt:
            cur["segments"].append({"t": "p", "x": txt})
    return {"id": "tattvacintamani", "chapters": chapters}


# ---------------------------------------------------------------- 4. Nyāyasūtra with the Tātparyaṭīkā
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


def tt_paragraph(b):
    ls = [x.strip() for x in b.split("\n") if x.strip()]
    if verse_shape(ls):
        return "v", " \n ".join(clean(x) for x in ls)
    return "b", clean(" ".join(ls))


def parse_tt():
    t = body(os.path.join(SRC, "nyayasutra-tatparyatika-gretil.txt"))
    blocks = [b.strip() for b in re.split(r"\n\s*\n", t) if b.strip()]
    units = []
    cur = {"id": "intro", "segments": []}
    units.append(cur)
    SKIP = re.compile(r"^(vācaspatimiśraviracitāyāṃ nyāyavārttikatātparyaṭīkāyāṃ|nyāyavārttikatātparyaṭīkā|"
                      r"[a-zāīū]+(?:ādhyāyasya|asyādhyāyasya)\s*(?:prathamam|prathamāhnikam|ādyam|dvitīyam|dvitīyāhnikam|ādyamāhnikam)\s*(āhnikam)?\s*/*)$")
    for b in blocks:
        s1 = b.strip()
        if SKIP.match(s1):
            continue
        m = re.match(r"NyS_(\d),(\d)\.(\d+)\s*:\s*(.*)$", s1, re.S)
        if m:
            sid = f"{m.group(1)}.{m.group(2)}.{m.group(3)}"
            stext = re.sub(r"\s*/+\s*$", "", " ".join(m.group(4).split()))
            cur = {"id": sid, "segments": [{"t": "s", "id": sid, "n": sid, "x": clean(stext)}]}
            units.append(cur)
            continue
        if re.match(r"^iti\s.*(ṭīkāyāṃ|āhnikam|adhyāyaḥ)", s1) or re.match(r"^sūtrasamāptau", s1) or s1.startswith("samāptaścāyaṃ") or s1.startswith("śubhambhūyāt"):
            cur["segments"].append({"t": "c", "x": clean(" ".join(s1.split()))})
            continue
        if re.match(r"^\d+ adhyāye", s1):
            continue
        if len(s1) < 40 and "\n" not in s1 and re.search(r"(parīkṣā|prakaraṇam)\s*/?\s*$", s1):
            cur["segments"].append({"t": "h", "x": clean(s1)})
            continue
        k, x = tt_paragraph(s1)
        if x:
            seg = {"t": k, "x": x, "l": "tika"}
            cur["segments"].append(seg)
    chapters = {}
    for u in units:
        if u["id"] == "intro":
            cid = "1.1"
        else:
            cid = ".".join(u["id"].split(".")[:2])
        a, h = cid.split(".")
        ch = chapters.setdefault(cid, {"id": cid, "title": f"Adhyāya {ROMAN[int(a)]} · Āhnika {h}", "group": f"Adhyāya {ROMAN[int(a)]}",
                                       "short": f"Āhnika {h}", "topic": NS_TOPICS[cid], "units": []})
        ch["units"].append(u)
    # move a trailing colophon/heading that belongs to the next āhnika
    return {"id": "nyaya-tatparya", "chapters": [chapters[k] for k in sorted(chapters, key=lambda x: [int(y) for y in x.split(".")])]}


def stats(doc):
    for c in doc["chapters"]:
        n = sum(len(sg["x"]) for u in c["units"] for sg in u["segments"])
        print(f"  {c['id']:>4} {c['title'][:44]:44} units {len(c['units']):4}  chars {n:7}")


if __name__ == "__main__":
    which = sys.argv[1:] or ["tarkasangraha", "tarkasangraha-dipika", "tattvacintamani", "nyaya-tatparya"]
    fns = {"tarkasangraha": parse_tarkasangraha, "tarkasangraha-dipika": parse_dipika, "tattvacintamani": parse_tc, "nyaya-tatparya": parse_tt}
    for w in which:
        doc = fns[w]()
        json.dump(doc, open(os.path.join(OUT, w + ".json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print(w)
        stats(doc)
