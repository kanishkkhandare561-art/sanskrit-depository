/* Minimal IAST ⇄ Devanagari conversion for the notes and corrections readers type in. */
(() => {
  "use strict";
  const V = { a: "अ", "ā": "आ", i: "इ", "ī": "ई", u: "उ", "ū": "ऊ", "ṛ": "ऋ", "ṝ": "ॠ", "ḷ": "ऌ", "ḹ": "ॡ", e: "ए", ai: "ऐ", o: "ओ", au: "औ" };
  const M = { a: "", "ā": "ा", i: "ि", "ī": "ी", u: "ु", "ū": "ू", "ṛ": "ृ", "ṝ": "ॄ", "ḷ": "ॢ", "ḹ": "ॣ", e: "े", ai: "ै", o: "ो", au: "ौ" };
  const C = {
    kh: "ख", gh: "घ", ch: "छ", jh: "झ", "ṭh": "ठ", "ḍh": "ढ", th: "थ", dh: "ध", ph: "फ", bh: "भ",
    k: "क", g: "ग", "ṅ": "ङ", c: "च", j: "ज", "ñ": "ञ", "ṭ": "ट", "ḍ": "ड", "ṇ": "ण", t: "त", d: "द", n: "न",
    p: "प", b: "ब", m: "म", y: "य", r: "र", l: "ल", v: "व", "ś": "श", "ṣ": "ष", s: "स", h: "ह",
  };
  const OTHER = { "ṃ": "ं", "ṁ": "ं", "ḥ": "ः", "'": "ऽ", "’": "ऽ" };
  const VK = Object.keys(V).sort((a, b) => b.length - a.length);
  const CK = Object.keys(C).sort((a, b) => b.length - a.length);
  const at = (s, i, keys) => keys.find((k) => s.startsWith(k, i));

  function toDeva(src) {
    const s = src.normalize("NFC").toLowerCase();
    let out = "";
    let i = 0;
    while (i < s.length) {
      const c = at(s, i, CK);
      if (c) {
        out += C[c];
        i += c.length;
        const v = at(s, i, VK);
        if (v) { out += M[v]; i += v.length; } else out += "्";
        continue;
      }
      const v = at(s, i, VK);
      if (v) { out += V[v]; i += v.length; continue; }
      out += OTHER[s[i]] !== undefined ? OTHER[s[i]] : s[i];
      i += 1;
    }
    return out;
  }

  const RV = {}, RM = {}, RC = {}, RO = { "ं": "ṃ", "ः": "ḥ", "ऽ": "'", "ँ": "m̐", "।": "/", "॥": "//" };
  for (const [k, d] of Object.entries(V)) RV[d] = k;
  for (const [k, d] of Object.entries(M)) if (d) RM[d] = k;
  for (const [k, d] of Object.entries(C)) RC[d] = k;
  function toIast(src) {
    let out = "";
    const s = src.normalize("NFC").replace(/़/g, "");
    for (let i = 0; i < s.length; i++) {
      const ch = s[i];
      if (RC[ch]) {
        out += RC[ch];
        const nx = s[i + 1];
        if (nx === "्") { i++; }
        else if (RM[nx]) { out += RM[nx]; i++; }
        else out += "a";
      } else if (RV[ch]) out += RV[ch];
      else if (RO[ch] !== undefined) out += RO[ch];
      else out += ch;
    }
    return out;
  }
  const isDeva = (s) => /[ऀ-ॿ]/.test(s);
  window.SDLipi = { toDeva, toIast, isDeva };
})();
