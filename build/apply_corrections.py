"""Apply corrections exported from the site's "My notes" page.

    python3 apply_corrections.py notes.json          # a file exported from My notes
    python3 apply_corrections.py --issue-body body.txt   # the body of a "Corrections" GitHub issue

Each corrected split goes into ../data/corrections.json (read by the site straight away, no rebuild
needed) and into overrides.json (so the next full rebuild keeps it). A note sent with a word is shown
in that word's popup.
"""
import json, os, re, sys

ROOT = os.path.dirname(os.path.abspath(__file__))
CORR = os.path.join(ROOT, "..", "data", "corrections.json")
OVER = os.path.join(ROOT, "overrides.json")
IAST = re.compile(r"^'?[a-zāīūṛṝḷḹṅñṭḍṇśṣṃḥ]+$")

V = {"a": "अ", "ā": "आ", "i": "इ", "ī": "ई", "u": "उ", "ū": "ऊ", "ṛ": "ऋ", "ṝ": "ॠ", "ḷ": "ऌ", "ḹ": "ॡ", "e": "ए", "ai": "ऐ", "o": "ओ", "au": "औ"}
M = {"a": "", "ā": "ा", "i": "ि", "ī": "ी", "u": "ु", "ū": "ू", "ṛ": "ृ", "ṝ": "ॄ", "ḷ": "ॢ", "ḹ": "ॣ", "e": "े", "ai": "ै", "o": "ो", "au": "ौ"}
C = {"kh": "ख", "gh": "घ", "ch": "छ", "jh": "झ", "ṭh": "ठ", "ḍh": "ढ", "th": "थ", "dh": "ध", "ph": "फ", "bh": "भ",
     "k": "क", "g": "ग", "ṅ": "ङ", "c": "च", "j": "ज", "ñ": "ञ", "ṭ": "ट", "ḍ": "ड", "ṇ": "ण", "t": "त", "d": "द", "n": "न",
     "p": "प", "b": "ब", "m": "म", "y": "य", "r": "र", "l": "ल", "v": "व", "ś": "श", "ṣ": "ष", "s": "स", "h": "ह"}
O = {"ṃ": "ं", "ḥ": "ः", "'": "ऽ"}


def deva(s):
    out, i = "", 0
    vk = sorted(V, key=len, reverse=True)
    ck = sorted(C, key=len, reverse=True)
    while i < len(s):
        c = next((k for k in ck if s.startswith(k, i)), None)
        if c:
            out += C[c]
            i += len(c)
            v = next((k for k in vk if s.startswith(k, i)), None)
            if v:
                out += M[v]
                i += len(v)
            else:
                out += "्"
            continue
        v = next((k for k in vk if s.startswith(k, i)), None)
        if v:
            out += V[v]
            i += len(v)
            continue
        out += O.get(s[i], s[i])
        i += 1
    return out


def load_payload(argv):
    if argv and argv[0] == "--issue-body":
        text = open(argv[1], encoding="utf-8").read()
        m = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, re.S)
        if not m:
            sys.exit("No JSON block found in the issue body.")
        return json.loads(m.group(1))
    return json.load(open(argv[0], encoding="utf-8"))


def main(argv):
    data = load_payload(argv)
    corr = json.load(open(CORR, encoding="utf-8")) if os.path.exists(CORR) else {}
    over = json.load(open(OVER, encoding="utf-8"))
    done = []
    for r in data.get("notes", [])[:500]:
        w = (r.get("w") or "").strip()
        if not IAST.match(w):
            continue
        text = re.sub(r"\s+", " ", str(r.get("text") or "")).strip()[:600]
        parts = []
        for p in r.get("split") or []:
            u, l = (p.get("u") or "").strip(), (p.get("l") or p.get("u") or "").strip()
            if IAST.match(u) and IAST.match(l):
                parts.append({"u": u.lstrip("'"), "l": l.lstrip("'")})
        if len(parts) != len(r.get("split") or []):
            parts = []          # something unreadable in the split: keep only the note
        ent = corr.get(w, {})
        if parts:
            ent["p"] = [{"u": p["u"], "l": p["l"], "g": "", "d": deva(p["u"]), "ld": deva(p["l"])} for p in parts]
            over[w] = {"p": [[p["u"], p["l"], ""] for p in parts]}
            if text:
                over[w]["n"] = text
        if text:
            ent["n"] = text
        if ent:
            corr[w] = ent
            done.append(w)
    json.dump(corr, open(CORR, "w", encoding="utf-8"), ensure_ascii=False, indent=1, sort_keys=True)
    json.dump(over, open(OVER, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"applied {len(done)}: " + ", ".join(done[:40]))


if __name__ == "__main__":
    main(sys.argv[1:])
