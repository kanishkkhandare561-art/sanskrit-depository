"""Parse the GRETIL Nyāyasūtra + Vātsyāyana-bhāṣya file into structured JSON (IAST)."""
import json, re, sys

SRC = sys.argv[1]
OUT = sys.argv[2]

raw = open(SRC, encoding="utf-8").read()
start = raw.index("% p.1 nyāyadarśanam")
lines = raw[start:].split("\n")

TYPO = {"grahaṇvat": "grahaṇavat", "śarīragunavaidharmyāt": "śarīraguṇavaidharmyāt", "aviṣeṣe vā": "aviśeṣe vā", "ekacchalaprasaṅaḥ": "ekacchalaprasaṅgaḥ", "yupagaj": "yugapaj", "yam arhtam": "yam artham", "dṛṣṭānataḥ": "dṛṣṭāntaḥ", "pratantrāsiddhaḥ": "paratantrāsiddhaḥ", "syyad": "syād", "budder": "buddher", "santattsabhivyakta": "santatyabhivyakta", "bhavanntīty": "bhavantīty", "bhūebyas": "bhūtebhyas", "vyavashtā": "vyavasthā", "upapadyte": "upapadyate", "nytyatva": "nityatva", "uapapadyete": "upapadyete", "sāmānysyā": "sāmānyasyā", "pratijñaiekadeśasya": "pratijñaikadeśasya", "tṛṭīya": "tṛtīya", "apratyauccāraṇaṃ": "apratyuccāraṇaṃ", " ṇupapannaṃ": " 'nupapannaṃ", " ṇupalambhāt": " 'nupalambhāt", " ṛtha": " 'rtha", "dhyvas": "dhyavas", 'pṛghag': 'pṛthag', 'uddśaḥ': 'uddeśaḥ', 'dharmao': 'dharmo', 'vvitaṇḍā': 'vitaṇḍā', 'ubyayam': 'ubhayam', "'samānajātīyebyaś": "'samānajātīyebhyaś", 'abādhibyo': 'abādibhyo', 'dṛṭṣṭāntaḥ': 'dṛṣṭāntaḥ', 'adhyvas': 'adhyavas', 'yathra': 'yatra', 'ekaddeśo': 'ekadeśo', 'avayavisadhbāvād': 'avayavisadbhāvād', 'ekavuddher': 'ekabuddher', 'putrakāmeṣṭiau': 'putrakāmeṣṭau', 'śabdao': 'śabdo', 'bhavgavataḥ': 'bhagavataḥ', 'daśakṭtvo': 'daśakṛtvo', 'cānupalabhder': 'cānupalabdher', 'pratikramānukramānupapatteeś': 'pratikramānukramānupapatteś', 'aprasṅgāt': 'aprasaṅgāt', 'pūrvagṛītam': 'pūrvagṛhītam', 'smaraṇāubandhāt': 'smaraṇānubandhāt', 'prakrtau': 'prakṛtau', 'prthivyāś': 'pṛthivyāś', 'copalabhir': 'copalabdhir', "dṛṣt'm": 'dṛṣṭam', 'dravyasyāviṣṭhmbhaḥ': 'dravyasyāviṣṭambhaḥ', 'bhavtitum': 'bhavitum', 'jñpayatīti': 'jñāpayatīti', 'avatiṣṭanta': 'avatiṣṭhanta', 'vinaṣthe': 'vinaṣṭe', 'jjānāvasthānād': 'jñānāvasthānād', 'utpatpannāpavargiṇī': 'utpannāpavargiṇī', 'utapannāpavargiṇī': 'utpannāpavargiṇī', 'pratyskṣe': 'pratyakṣe', 'arthagrhaṇaṃ': 'arthagrahaṇaṃ', 'viśiṣthadharmayogo': 'viśiṣṭadharmayogo', 'sāmrthyaṃ': 'sāmarthyaṃ', 'sannikarṣottpannaṃ': 'sannikarṣotpannaṃ', ' ṇusañcaya': " 'ṇusañcaya", ' ṇārabdhaś': " 'nārabdhaś", ' ṇta ': " 'nta ", 'ākaṅkṣā': 'ākāṅkṣā', 'dṛṣ.ārtha': 'dṛṣṭārtha', "so 'ya. ": "so 'yaṃ ", 'dṛṣṭādṛṣ.ārthatvāt': 'dṛṣṭādṛṣṭārthatvāt', 'pramaṇato': 'pramāṇato', "'rthoānarabhūtāḥ": "'rthāntarabhūtāḥ", 'vimarṣa': 'vimarśa', 'prayjyata': 'prayujyata', 'mṛdagavake': 'mṛdgavake', 'sāmārthyat': 'sāmarthyāt', 'sambhavait': 'sambhavati', 'kaṇṭakataikṣṇyādidarśanāt': 'kaṇṭakataikṣṇyādidarśanāt', 'atho khalv': 'atho khalv', 'nyāyābhāṣye': 'nyāyabhāṣye'}
ENC_FIX = {"śüE": "ś ", "asaśüEcā": "asaś cā", "@": "", "ü": ""}


def clean_line(line: str) -> str:
    line = line.rstrip()
    if line.startswith("%"):
        # "% <repeated fragment>] p.NNN new text"  or  "% p.NNN new text"
        body = line[1:]
        if "]" in body:
            body = body[body.rindex("]") + 1:]
        line = body
    # remove page markers and stray %
    line = re.sub(r"%\s*", " ", line)
    line = re.sub(r"\b[pP]\.\s*\d+(\(\d+\))?", " ", line)
    line = re.sub(r"(?<=\s)\.(?=[a-zāīūṛ])", "'", line)
    line = line.replace("dṛṣ.ārtha", "dṛṣṭārtha").replace("so 'ya. ", "so 'yaṃ ").replace("---]", "---")
    # editorial notes
    line = re.sub(r"\((corr|emend|following)[^)]*\)", "", line)
    line = re.sub(r"\(\d\*\)", "", line)
    line = line.replace("*", "")
    line = line.replace("asaśüEcā", "asaś cā").replace("doṣamithyājñānām uttarottarāpāye tadanantarāpāyād", "doṣamithyājñānānām uttarottarāpāye tadanantarāpāyād")
    for k, v in TYPO.items():
        line = line.replace(k, v)
    for k, v in ENC_FIX.items():
        line = line.replace(k, v)
    line = line.replace("---", " --- ")
    line = re.sub(r"\s+", " ", line).strip()
    return line


units = []  # list of dicts
cur = None
pending_intro = []  # text before first unit / between headers
UNIT_RE = re.compile(r"\*+\s*NySBh_(\d+),(\d+)\.([\d-]+)\s*\*+")
SUTRA_RE = re.compile(r"NyS_(\d+),(\d+)\.(\d+)\s*:\s*(.*?)\s*\|\|")

for line in lines:
    m = UNIT_RE.search(line)
    if m:
        cur = {"hdr": f"{m.group(1)},{m.group(2)}.{m.group(3)}", "segments": []}
        units.append(cur)
        rest = line[m.end():]
        if rest.strip():
            line = rest
        else:
            continue
    text = clean_line(line)
    if not text:
        continue
    if cur is None:
        pending_intro.append(text)
        continue
    # a line may contain a sūtra mid-way
    pos = 0
    for sm in SUTRA_RE.finditer(text):
        before = text[pos:sm.start()].strip()
        if before:
            cur["segments"].append({"t": "b", "x": before})
        sid = f"{sm.group(1)}.{sm.group(2)}.{sm.group(3)}"
        stext = sm.group(4).strip()
        # skip duplicate sūtra lines inside the same unit
        if not any(s["t"] == "s" and s["id"] == sid for s in cur["segments"]):
            cur["segments"].append({"t": "s", "id": sid, "x": stext})
        else:
            cur["dup"] = True
        pos = sm.end()
    after = text[pos:].strip()
    if after:
        if cur.get("dup") and any(after in s["x"] for s in cur["segments"] if s["t"] == "b"):
            continue
        cur.pop("dup", None)
        cur["segments"].append({"t": "b", "x": after})

# merge consecutive bhāṣya segments
for u in units:
    merged = []
    for s in u["segments"]:
        if merged and merged[-1]["t"] == "b" and s["t"] == "b":
            merged[-1]["x"] += " " + s["x"]
        else:
            merged.append(s)
    u["segments"] = merged
    u.pop("dup", None)

# Colophon detection: "iti ... āhnikam" / "adhyāyaḥ" sentences become separate segments
COLO = re.compile(r"(iti (?:śrī)?vātsyāyanīye[^/]*?(?:āhnikam|adhyāyaḥ)(?:\s*/+\s*\d*\s*/*)?(?:\s*samāpta[^/]*?adhyāyaḥ\s*/+\s*\d*\s*/*)?)")
for u in units:
    out = []
    for s in u["segments"]:
        if s["t"] != "b":
            out.append(s); continue
        parts = COLO.split(s["x"])
        for i, p in enumerate(parts):
            p = p.strip()
            if not p:
                continue
            if i % 2 == 1:
                out.append({"t": "c", "x": p})
            else:
                # strip leftover heading words like "dvitīyāhnikam" / "nyāyadarśanam atha ..."
                p2 = re.sub(r"^(nyāyadarśanam\s*)?(atha\s+)?([a-zāīū]+ādhyāyā?syā?\s+)?(ādyam|dvitīyam|prathamāhnikam|dvitīyāhnikam)\s*āhnikam\s*", "", p)
                p2 = re.sub(r"^(dvitīyāhnikam|tṛtīyo 'dhyāyaḥ prathamāhnikam/|nyāyadarśanam)\s*", "", p2).strip()
                if p2:
                    out.append({"t": "b", "x": p2})
        u["segments"] = out

# Group by adhyāya / āhnika using the sūtra ids
book = {}
for u in units:
    sids = [s["id"] for s in u["segments"] if s["t"] == "s"]
    if sids:
        a, h, _ = sids[0].split(".")
    else:
        a, rest = u["hdr"].split(",")
        h = rest.split(".")[0]
    u["id"] = sids[0] if sids else u["hdr"].replace(",", ".")
    u["sutras"] = sids
    book.setdefault(a, {}).setdefault(h, []).append(u)

json.dump({"intro": pending_intro, "book": book}, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
n_s = sum(len(u["sutras"]) for a in book.values() for h in a.values() for u in h)
print("units", len(units), "sutras", n_s)
for a in sorted(book):
    print(a, {h: len(book[a][h]) for h in sorted(book[a])})
