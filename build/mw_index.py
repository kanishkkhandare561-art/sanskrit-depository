"""Build headword -> short English gloss index from Monier-Williams (csl-orig mw.txt, SLP1)."""
import re, json, sys
from vidyut.lipi import transliterate, Scheme

SRC, OUT = sys.argv[1], sys.argv[2]

def slp_to_iast(s):
    return transliterate(s, Scheme.Slp1, Scheme.Iast)

TAG_DROP = re.compile(r"<(ls|info|pc|lang|gk|etym|hom|lbinfo)[^>]*>.*?</\1>|<(info|lbinfo|ls)[^>]*/>", re.S)

def clean(body):
    body = TAG_DROP.sub("", body)
    body = re.sub(r"<ls[^>]*>[^<]*</ls>", "", body)
    body = re.sub(r"<s>(.*?)</s>", lambda m: slp_to_iast(m.group(1).replace("—", "-")), body)
    body = re.sub(r"<s1[^>]*>(.*?)</s1>", r"\1", body)
    body = re.sub(r"<[^>]+>", "", body)
    body = re.sub(r"\{[^}]*\}", "", body)
    body = re.sub(r"\[Page[^\]]*\]", "", body)
    body = body.replace("¦", "").replace("—", "-")
    body = re.sub(r"\(\s*[,;]?\s*\)", "", body)
    body = re.sub(r"\s+([,;.])", r"\1", body)
    body = re.sub(r"([,;])\1+", r"\1", body)
    body = re.sub(r"\s+", " ", body).strip(" ,;")
    return body

entries = {}   # k1 -> {"k2":..., "lex":..., "senses":[...]}
cur = None
for block in open(SRC, encoding="utf-8").read().split("<LEND>"):
    m = re.search(r"<L>([\d.]+)<pc>[^<]*<k1>([^<]+)<k2>([^<]+)(?:<h>\d+)?<e>(\w+)", block)
    if not m:
        continue
    k1, k2, e = m.group(2), m.group(3), m.group(4)
    body = block[m.end():]
    lex = re.findall(r"<lex>([^<]+)</lex>", body)
    text = clean(body)
    if not text:
        continue
    ent = entries.setdefault(k1, {"k2": k2, "lex": [], "senses": [], "n": 0})
    if lex and not ent["lex"]:
        ent["lex"] = [l.strip() for l in lex[:2]]
    # keep a few senses, prefer the earliest
    if ent["n"] < 6 and len(" ; ".join(ent["senses"])) < 380:
        ent["senses"].append(text)
        ent["n"] += 1

out = {}
for k1, ent in entries.items():
    g = "; ".join(ent["senses"])
    # drop the leading repeated headword in the gloss (e.g. "pramāṇa n. measure")
    g = re.sub(r"^[^\s]*?[a-zāīūṛṝḷṅñṭḍṇśṣṃḥ\-]+\s+(?=(m|f|n|mfn|ind|cl)\.)", "", g)
    if len(g) > 420:
        g = g[:420].rsplit(" ", 1)[0] + " …"
    out[k1] = [g, ent["k2"]]

json.dump(out, open(OUT, "w", encoding="utf-8"), ensure_ascii=False)
print("headwords", len(out))
for k in ["pramARa", "tattvajYAna", "jYAna", "nyAya", "hetvABAsa", "cala", "Cala", "vAda", "jalpa", "vitaRqA", "anumAna", "ca", "BU", "a"]:
    print(k, out.get(k))
