/* Sanskrit Depository — reader for the Nyāyasūtra with Vātsyāyana's Bhāṣya.
   Plain JavaScript, no build step: works as-is on GitHub Pages. */
(() => {
  "use strict";

  const $ = (s, el = document) => el.querySelector(s);
  const $$ = (s, el = document) => Array.from(el.querySelectorAll(s));
  const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  const store = {
    get(k, d) { try { const v = localStorage.getItem(k); return v === null ? d : JSON.parse(v); } catch (e) { return d; } },
    set(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch (e) {} },
  };

  const state = {
    index: null,
    glossary: null,
    glossaryPromise: null,
    chapters: new Map(),
    current: null,          // current chapter id
    pop: { anchor: null, entry: null, deva: "" },
  };

  const view = $("#view");
  const pop = $("#pop");
  const popInner = $("#popInner");
  const scrim = $("#scrim");

  /* ------------------------------------------------------------------ data */
  async function getJSON(url) {
    const r = await fetch(url);
    if (!r.ok) throw new Error(`Could not load ${url} (${r.status})`);
    return r.json();
  }
  function loadGlossary() {
    if (!state.glossaryPromise) {
      state.glossaryPromise = getJSON("data/glossary.json").then((g) => (state.glossary = g));
    }
    return state.glossaryPromise;
  }
  async function loadChapter(id) {
    if (!state.chapters.has(id)) state.chapters.set(id, getJSON(`data/nyaya-${id}.json`));
    return state.chapters.get(id);
  }

  /* ------------------------------------------------------------------ settings */
  const settings = {
    fs: store.get("sd-fs", 1),
    iast: store.get("sd-iast", true),
    bh: store.get("sd-bh", true),
  };
  function applySettings() {
    document.documentElement.style.setProperty("--fs", settings.fs);
    view.classList.toggle("hide-iast", !settings.iast);
    view.classList.toggle("hide-bh", !settings.bh);
  }
  $("#sizeUp").addEventListener("click", () => { settings.fs = Math.min(1.4, +(settings.fs + 0.08).toFixed(2)); store.set("sd-fs", settings.fs); applySettings(); });
  $("#sizeDown").addEventListener("click", () => { settings.fs = Math.max(0.8, +(settings.fs - 0.08).toFixed(2)); store.set("sd-fs", settings.fs); applySettings(); });
  $("#themeBtn").addEventListener("click", () => {
    const root = document.documentElement;
    const dark = root.dataset.theme ? root.dataset.theme === "dark" : matchMedia("(prefers-color-scheme: dark)").matches;
    root.dataset.theme = dark ? "light" : "dark";
    try { localStorage.setItem("sd-theme", root.dataset.theme); } catch (e) {}
  });

  /* ------------------------------------------------------------------ sidebar */
  const sidebar = $("#sidebar");
  const menuBtn = $("#menuBtn");
  function setMenu(open) {
    sidebar.classList.toggle("open", open);
    menuBtn.setAttribute("aria-expanded", String(open));
    scrim.hidden = !open && pop.hidden;
  }
  menuBtn.addEventListener("click", () => setMenu(!sidebar.classList.contains("open")));
  scrim.addEventListener("click", () => { setMenu(false); closePop(); });

  const ROMAN = ["", "I", "II", "III", "IV", "V"];
  function renderSidebar(chapterId, chapter) {
    const byAdh = {};
    for (const c of state.index.chapters) (byAdh[c.adhyaya] ||= []).push(c);
    let h = "";
    for (const a of Object.keys(byAdh)) {
      h += `<div class="side-adh"><h3>Adhyāya ${ROMAN[a]}</h3>`;
      for (const c of byAdh[a]) {
        const on = c.id === chapterId;
        h += `<a class="side-ahn" href="#/${c.id}" ${on ? 'aria-current="page"' : ""}>Āhnika ${c.ahnika}<small>${c.nsutras} sūtras</small></a>`;
        if (on) {
          h += `<ol class="side-sutras">`;
          for (const [sid, dv] of c.sutras) {
            h += `<li><a href="#/${sid}" data-sid="${sid}"><span>${sid}</span><span>${esc(dv)}</span></a></li>`;
          }
          h += `</ol>`;
        }
      }
      h += `</div>`;
    }
    h += `<div class="side-adh"><a class="side-ahn" href="#/about" ${chapterId === "about" ? 'aria-current="page"' : ""}>About this edition</a></div>`;
    $("#sideInner").innerHTML = h;
    const on = $(".side-ahn[aria-current]", sidebar);
    if (on && chapterId !== "about") on.scrollIntoView({ block: "nearest" });
  }

  /* ------------------------------------------------------------------ text rendering */
  const NOSPACE_BEFORE = new Set([",", ";", "?", "!", ":", "”", "।", "॥"]);
  function wordsHTML(tokens, lex) {
    let out = "";
    let prevOpen = false;
    tokens.forEach((t, i) => {
      if (typeof t === "string") {
        if (t === "“") { out += (i ? " " : "") + t; prevOpen = true; return; }
        if (/^॥.*॥$/.test(t)) { out += " " + t; return; }
        out += (NOSPACE_BEFORE.has(t) ? "" : " ") + t;
        return;
      }
      const [dv, k] = t;
      const e = lex[k];
      let cls = "w";
      if (e && (!e.p.length || e.q)) cls += " low";
      out += (i && !prevOpen ? " " : "") + `<span class="${cls}" data-k="${k}" tabindex="-1">${dv}</span>`;
      prevOpen = false;
    });
    return out.trim();
  }

  function renderChapter(ch, meta) {
    const idx = state.index.chapters.findIndex((c) => c.id === meta.id);
    const prev = state.index.chapters[idx - 1];
    const next = state.index.chapters[idx + 1];
    let h = `<header class="ch-head">
      <p class="crumb">Adhyāya ${ROMAN[meta.adhyaya]}, Āhnika ${meta.ahnika}</p>
      <h1>${esc(meta.topic)}</h1>
      <p>Sūtras ${meta.sutras[0][0]}–${meta.sutras[meta.sutras.length - 1][0]}. Tap any word for its meaning; long words open with their sandhi split.</p>
      <div class="ch-controls">
        <button class="chip-toggle" id="tIast" aria-pressed="${settings.iast}"><span class="dot"></span>Transliteration</button>
        <button class="chip-toggle" id="tBh" aria-pressed="${settings.bh}"><span class="dot"></span>Commentary</button>
      </div>
    </header>`;
    for (const u of ch.units) {
      h += `<section class="unit" id="u-${u.id}">`;
      for (const sg of u.segs) {
        const words = wordsHTML(sg.w, ch.lex);
        if (sg.t === "s") {
          h += `<div class="sutra" id="s-${sg.id}">
            <a class="sn" href="#/${sg.id}" aria-label="Sūtra ${sg.id}">${sg.id}</a>
            <p class="st" data-words tabindex="0" lang="sa">${words}</p>
            <p class="tl" lang="sa-Latn">${esc(sg.i)}</p>
          </div>`;
        } else if (sg.t === "c") {
          h += `<p class="colophon" data-words tabindex="0" lang="sa">${words}</p>`;
        } else {
          h += `<p class="bh" data-words tabindex="0" lang="sa">${words}</p>`;
        }
      }
      h += `</section>`;
    }
    h += `<nav class="pager" aria-label="Āhnikas">
      ${prev ? `<a href="#/${prev.id}"><small>Previous</small>${prev.title}</a>` : ""}
      ${next ? `<a class="next" href="#/${next.id}"><small>Next</small>${next.title}</a>` : ""}
    </nav>`;
    view.innerHTML = h;
    view.dataset.chapter = meta.id;
    $("#tIast").addEventListener("click", (ev) => { settings.iast = !settings.iast; store.set("sd-iast", settings.iast); ev.currentTarget.setAttribute("aria-pressed", settings.iast); applySettings(); });
    $("#tBh").addEventListener("click", (ev) => { settings.bh = !settings.bh; store.set("sd-bh", settings.bh); ev.currentTarget.setAttribute("aria-pressed", settings.bh); applySettings(); });
    observeSutras();
  }

  let sutraObserver = null;
  function observeSutras() {
    if (sutraObserver) sutraObserver.disconnect();
    if (!("IntersectionObserver" in window)) return;
    sutraObserver = new IntersectionObserver((entries) => {
      for (const en of entries) {
        if (!en.isIntersecting) continue;
        const sid = en.target.id.slice(2);
        $$(".side-sutras a.on").forEach((a) => a.classList.remove("on"));
        const a = $(`.side-sutras a[data-sid="${CSS.escape(sid)}"]`);
        if (a) { a.classList.add("on"); a.scrollIntoView({ block: "nearest" }); }
      }
    }, { rootMargin: "-80px 0px -70% 0px" });
    $$(".sutra", view).forEach((s) => sutraObserver.observe(s));
  }

  /* ------------------------------------------------------------------ home */
  async function renderHome() {
    view.innerHTML = $("#tplHome").innerHTML;
    view.dataset.chapter = "home";
    renderSidebar("home");
    let toc = "";
    const byAdh = {};
    for (const c of state.index.chapters) (byAdh[c.adhyaya] ||= []).push(c);
    const ADH_DEVA = ["", "प्रथमोऽध्यायः", "द्वितीयोऽध्यायः", "तृतीयोऽध्यायः", "चतुर्थोऽध्यायः", "पञ्चमोऽध्यायः"];
    for (const a of Object.keys(byAdh)) {
      toc += `<li><div class="adh">${ADH_DEVA[a]}<small>Adhyāya ${ROMAN[a]}</small></div><div class="ahns">`;
      for (const c of byAdh[a]) {
        toc += `<a class="ahn" href="#/${c.id}"><b>Āhnika ${c.ahnika}</b><span>${esc(c.topic)}</span><i>${c.sutras[0][0]}–${c.sutras[c.sutras.length - 1][0]}</i></a>`;
      }
      toc += `</div></li>`;
    }
    $("#toc").innerHTML = toc;

    const ch = await loadChapter("1.1");
    const s1 = ch.units[0].segs.find((s) => s.t === "s");
    const box = $("#heroSutra");
    if (!box) return;
    let h = "";
    s1.w.forEach((t, i) => {
      if (typeof t === "string") return;
      const e = ch.lex[t[1]];
      if (i === 0 && e.p.length > 1) {
        e.p.forEach((p, j) => {
          h += `<span class="hero-member"><span class="n">${j + 1}</span><button type="button" data-k="${t[1]}" data-part="${j}" aria-label="${esc(p.u)}">${esc(p.d)}</button></span>`;
        });
      } else {
        h += `<span class="hero-rest"><button type="button" class="w-hero" data-k="${t[1]}">${t[0]}</button></span>`;
      }
    });
    box.innerHTML = h;
    box.addEventListener("click", (ev) => {
      const b = ev.target.closest("button");
      if (!b) return;
      const e = ch.lex[+b.dataset.k];
      $$("button.sel", box).forEach((x) => x.classList.remove("sel"));
      b.classList.add("sel");
      if (b.dataset.part !== undefined) {
        const i = +b.dataset.part, p = e.p[i];
        openPop(b, { w: p.u, p: [p] }, esc(p.d), { context: `Category ${i + 1} of the 16 in the opening compound. <a href="#/1.1">Read the sūtra and commentary</a>` });
      } else {
        openPop(b, e, b.textContent);
      }
    });
  }

  /* ------------------------------------------------------------------ about */
  function renderAbout() {
    renderSidebar("about");
    view.dataset.chapter = "about";
    view.innerHTML = `<article class="prose">
      <h1>About this edition</h1>
      <p>This is a reading edition of the <b>Nyāyasūtra</b> of Gautama (Akṣapāda), the root text of the Nyāya school of Indian logic and epistemology, with the complete <b>Nyāyabhāṣya</b> of Vātsyāyana (Pakṣilasvāmin). Every Sanskrit word on the site can be tapped to see how it is built and what it means.</p>

      <h2>The text</h2>
      <p>The Sanskrit comes from the GRETIL e-text (input by the Indology Student Team, University of Tokyo), based on the edition of Taranatha Nyaya-Tarkatirtha, <i>Calcutta Sanskrit Series</i> 18 &amp; 19 (Calcutta, 1936–1944). Page markers and editorial notes were removed, the text was converted from romanisation to Devanagari, and around eighty obvious keying errors were corrected (for example <span class="dv">पृघग्</span> → <span class="dv">पृथग्</span>). It is distributed under the Creative Commons Attribution-NonCommercial-ShareAlike 4.0 licence.</p>

      <h2>How a word is analysed</h2>
      <p>Each word is split by reversing the rules of sandhi: the program tries every possible division of the word, restores the sounds that sandhi merged (for example <code>ā</code> → <code>a + a</code>, <code>e</code> → <code>a + i</code>, a final <code>d</code> → <code>t</code>), and keeps the reading in which every piece is a real Sanskrit word. The last piece is identified grammatically (case, number, tense, person) using the Vidyut morphological lexicon. Meanings come first from a glossary written for Nyāya, and otherwise from the Monier-Williams <i>Sanskrit–English Dictionary</i> (1899) as digitised by the Cologne Digital Sanskrit Dictionaries.</p>
      <ul class="legend">
        <li><span class="ptag c">Nyāya glossary</span><span>Meaning written for this text, giving the technical sense used in Nyāya (so <span class="dv">प्रमाण</span> is “means of valid knowledge”, not just “measure”).</span></li>
        <li><span class="ptag mw">Monier-Williams</span><span>Meaning taken from the dictionary. The first senses are shown; the sense intended here may be a later one.</span></li>
        <li><span class="ptag q">Check this analysis</span><span>The split or the grammar is uncertain. Words like this are shown with a dotted underline in the text.</span></li>
      </ul>
      <p>The analysis is automatic and will sometimes be wrong, especially in the commentary. The sūtras themselves have been reviewed. Where a form is ambiguous (for example a final <span class="dv">-आन्</span> before a nasal may be an accusative plural or an ablative singular), the popup lists the other possible readings.</p>

      <h2>Keyboard</h2>
      <p>Press <b>Tab</b> to move to a paragraph, <b>Enter</b> to step into its words, <b>←</b> and <b>→</b> to move between words, <b>Enter</b> to open a word and <b>Esc</b> to close it.</p>

      <h2>Corrections and new texts</h2>
      <p>The analysis is generated by the scripts in the <code>build</code> folder of the repository. To correct a word, add it to <code>build/overrides.json</code>; to improve a meaning, edit <code>build/curated.json</code>; then run the build again. The same pipeline can prepare other texts for the depository.</p>
    </article>`;
  }

  /* ------------------------------------------------------------------ popup */
  const shorten = (s, n = 120) => (s && s.length > n ? s.slice(0, n).replace(/\s+\S*$/, "") + " …" : s || "");
  const slug = (s) => s.normalize("NFD").replace(/[̀-ͯ]/g, "").replace(/[^a-zA-Z]/g, "").toLowerCase();

  function glossFor(p) {
    const g = state.glossary || {};
    return g[p.l] || (p.r && g[p.r]) || null;
  }

  function lemmaCard(p, showHead = true) {
    const g = glossFor(p);
    let gram = p.g === "compound member (stem)" ? "compound member (stem form)" : p.g;
    let h = `<div class="lemma">`;
    if (showHead && p.l !== p.u) h += `<div class="lemma-head"><span class="gram-k">Dictionary form</span><span class="ld" lang="sa">${esc(p.ld || p.l)}</span><span class="li">${esc(p.l)}</span></div>`;
    else if (showHead) h += `<div class="lemma-head"><span class="ld" lang="sa">${esc(p.ld || p.l)}</span><span class="li">${esc(p.l)}</span></div>`;
    if (gram) h += `<p class="gram">${esc(gram)}</p>`;
    if (!state.glossary) {
      h += `<p class="mean">Loading the dictionary…</p>`;
    } else if (g && g.m) {
      h += `<p class="mean">${esc(g.m)}</p>`;
      if (g.n) h += `<p class="note">${esc(g.n)}</p>`;
      if (g.c && g.c.length > 1) h += `<p class="dict-split">Dictionary analysis: <span>${esc(g.c.join(" + "))}</span></p>`;
      if (g.s === "c" && g.mw) h += `<details class="mwx"><summary>Monier-Williams</summary><p>${esc(g.mw)}</p></details>`;
    } else {
      h += `<p class="mean">No dictionary meaning was found for this form. Try the dictionary links below.</p>`;
    }
    if (p.a && p.a.length) {
      h += `<div class="alts">Other possible readings:<ul>${p.a.map(([l, gr]) => `<li><span lang="sa-Latn">${esc(l)}</span>: ${esc(gr)}</li>`).join("")}</ul></div>`;
    }
    h += `</div>`;
    return h;
  }

  function sourceTag(p) {
    const g = glossFor(p);
    if (!g || !g.m) return "";
    return g.s === "c" ? `<span class="ptag c">Nyāya glossary</span>` : `<span class="ptag mw">Monier-Williams</span>`;
  }

  function renderPop(focusPart) {
    const { entry: e, deva } = state.pop;
    const parts = e.p || [];
    let h = `<button class="pop-close" id="popClose" aria-label="Close"><svg viewBox="0 0 24 24"><path d="M6 6l12 12M18 6L6 18"/></svg></button>
      <p class="pw${deva.length > 22 ? " long" : ""}" id="popWord" lang="sa">${deva}</p>
      <p class="pw-iast" lang="sa-Latn">${esc(e.w)}</p>`;
    let tags = "";
    if (e.v) tags += `<span class="ptag c">Verified</span>`;
    if (!parts.length) tags += `<span class="ptag q">Not analysed</span>`;
    else if (e.q) tags += `<span class="ptag q">Check this analysis</span>`;
    if (parts.length === 1) tags += sourceTag(parts[0]);
    if (tags) h += `<div>${tags}</div>`;

    if (parts.length > 1) {
      h += `<div class="psec"><h4>Sandhi split</h4><div class="split" role="group" aria-label="Parts of the word">`;
      parts.forEach((p, i) => {
        if (i) h += `<span class="plus" aria-hidden="true">+</span>`;
        h += `<button class="part" data-i="${i}" aria-pressed="${focusPart === i}" lang="sa" title="${esc(p.u)}">${esc(p.d)}</button>`;
      });
      h += `</div></div>`;
      if (focusPart === null || focusPart === undefined) {
        h += `<div class="psec"><h4>Meaning of each part</h4><ul class="parts-list">`;
        parts.forEach((p, i) => {
          const g = glossFor(p);
          const m = g && g.m ? shorten(g.m, 110) : state.glossary ? p.g : "…";
          h += `<li><button data-i="${i}"><span class="pd" lang="sa">${esc(p.d)}</span><span class="pm">${esc(m)}</span></button></li>`;
        });
        h += `</ul></div>`;
      } else {
        const p = parts[focusPart];
        h += `<div class="psec"><button class="back" data-back>← All parts</button>${sourceTag(p) ? `<div style="margin:-4px 0 8px">${sourceTag(p)}</div>` : ""}${lemmaCard(p)}</div>`;
      }
    } else if (parts.length === 1) {
      const p = parts[0];
      h += `<div class="psec">${lemmaCard(p, p.l !== e.w.replace(/^'/, "a") && p.l !== p.u || p.u !== e.w.replace(/^'/, "a"))}</div>`;
      if (state.pop.context) h += `<p class="ctx">${state.pop.context}</p>`;
    } else {
      h += `<p class="mean" style="margin-top:14px">This form could not be analysed automatically — it may contain a misprint in the source, or be a rare form.</p>`;
    }
    const linkWord = parts.length === 1 ? parts[0].l : focusPart != null && parts[focusPart] ? parts[focusPart].l : parts.length ? null : e.w.replace(/^'/, "a");
    if (linkWord) h += `<div class="pfoot"><a href="https://www.wisdomlib.org/definition/${slug(linkWord)}" target="_blank" rel="noopener">Look up “${esc(linkWord)}” on Wisdomlib</a></div>`;
    else h += `<div class="pfoot"><span class="src">Tap a part to read its full entry.</span></div>`;
    popInner.innerHTML = h;
    $("#popClose").addEventListener("click", () => closePop(true));
  }

  popInner.addEventListener("click", (ev) => {
    ev.stopPropagation();
    const b = ev.target.closest("button[data-i]");
    if (b) {
      const i = +b.dataset.i;
      const cur = $(".part[aria-pressed='true']", popInner);
      renderPop(cur && +cur.dataset.i === i ? null : i);
      const nb = $(`.part[data-i="${i}"]`, popInner);
      if (nb) nb.focus();
      return;
    }
    if (ev.target.closest("[data-back]")) {
      renderPop(null);
      const first = $(".part", popInner);
      if (first) first.focus();
    }
  });

  function openPop(anchor, entry, deva, opts = {}) {
    if (state.pop.anchor && state.pop.anchor !== anchor) state.pop.anchor.classList.remove("sel");
    state.pop = { anchor, entry, deva, context: opts.context || "" };
    anchor.classList.add("sel");
    renderPop(opts.focusPart ?? null);
    pop.hidden = false;
    position();
    if (matchMedia("(max-width: 680px)").matches) scrim.hidden = false;
    if (!state.glossary) loadGlossary().then(() => { if (state.pop.entry === entry) { const c = $(".part[aria-pressed='true']", popInner); renderPop(c ? +c.dataset.i : opts.focusPart ?? null); } });
    if (opts.keyboard) { const f = $(".part", popInner) || $("#popClose"); f && f.focus(); }
  }

  function position() {
    const a = state.pop.anchor;
    if (!a || pop.hidden) return;
    if (matchMedia("(max-width: 680px)").matches) return; // bottom sheet via CSS
    const r = a.getBoundingClientRect();
    const pw = pop.offsetWidth, ph = pop.offsetHeight;
    const vw = document.documentElement.clientWidth, vh = window.innerHeight;
    let left = Math.min(Math.max(12, r.left + r.width / 2 - 40), vw - pw - 12);
    const below = r.bottom + 12 + ph < vh || r.top < ph + 80;
    const top = below ? r.bottom + 12 : r.top - ph - 12;
    pop.classList.toggle("above", !below);
    pop.style.left = left + window.scrollX + "px";
    pop.style.top = top + window.scrollY + "px";
    const arrowX = Math.min(Math.max(16, r.left + r.width / 2 - left - 7), pw - 30);
    $("#popArrow").style.left = arrowX + "px";
  }

  function closePop(returnFocus) {
    if (pop.hidden) return;
    pop.hidden = true;
    if (!sidebar.classList.contains("open")) scrim.hidden = true;
    const a = state.pop.anchor;
    if (a) { a.classList.remove("sel"); if (returnFocus) a.focus(); }
    state.pop.anchor = null;
  }

  document.addEventListener("click", (ev) => {
    const w = ev.target.closest(".w");
    if (w && view.contains(w)) {
      const chId = view.dataset.chapter;
      state.chapters.get(chId).then((ch) => openPop(w, ch.lex[+w.dataset.k], w.innerHTML));
      return;
    }
    if (!pop.hidden && !pop.contains(ev.target) && !ev.target.closest("#heroSutra")) closePop(false);
  });
  window.addEventListener("resize", () => position());

  // keyboard: paragraph → words → popup
  document.addEventListener("keydown", (ev) => {
    if (ev.key === "Escape") {
      if (!pop.hidden) { closePop(true); ev.preventDefault(); return; }
      if (sidebar.classList.contains("open")) setMenu(false);
      const w = document.activeElement && document.activeElement.closest && document.activeElement.closest(".w");
      if (w) w.closest("[data-words]").focus();
      return;
    }
    const t = document.activeElement;
    if (!t || !view.contains(t)) return;
    if (t.matches("[data-words]") && (ev.key === "Enter" || ev.key === " ")) {
      const f = $(".w", t); if (f) { f.focus(); ev.preventDefault(); }
    } else if (t.classList.contains("w")) {
      if (ev.key === "ArrowRight" || ev.key === "ArrowLeft") {
        const ws = $$(".w", t.closest("[data-words]"));
        const i = ws.indexOf(t) + (ev.key === "ArrowRight" ? 1 : -1);
        if (ws[i]) ws[i].focus();
        ev.preventDefault();
      } else if (ev.key === "Enter" || ev.key === " ") {
        ev.preventDefault();
        state.chapters.get(view.dataset.chapter).then((ch) => openPop(t, ch.lex[+t.dataset.k], t.innerHTML, { keyboard: true }));
      }
    }
  });

  /* ------------------------------------------------------------------ search */
  const search = $("#search");
  const results = $("#searchResults");
  const fold = (s) => s.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase().replace(/[^a-z0-9.ऀ-ॿ ]/g, "");
  let sel = -1;
  function runSearch() {
    const q = search.value.trim();
    if (!q || !state.index) { results.hidden = true; return; }
    const fq = fold(q);
    const isNum = /^\d+(\.\d*){0,2}$/.test(q);
    const hits = [];
    for (const c of state.index.chapters) {
      for (const [sid, dv, ia] of c.sutras) {
        if (isNum ? sid === q || sid.startsWith(q.endsWith(".") ? q : q + ".") || sid === q : fold(ia).includes(fq) || dv.includes(q)) hits.push([sid, dv, ia]);
        if (hits.length >= 40) break;
      }
    }
    sel = -1;
    results.innerHTML = hits.length
      ? hits.map(([sid, dv, ia]) => `<a href="#/${sid}" role="option"><span class="num">${sid}</span><span class="dv" lang="sa">${esc(dv)}</span><span class="tr">${esc(ia)}</span></a>`).join("")
      : `<div class="empty">No sūtra matches “${esc(q)}”. Try a number such as 2.1.4, or part of a word in Devanagari or romanisation.</div>`;
    results.hidden = false;
  }
  search.addEventListener("input", runSearch);
  search.addEventListener("focus", runSearch);
  search.addEventListener("keydown", (ev) => {
    const items = $$("a", results);
    if (ev.key === "ArrowDown" || ev.key === "ArrowUp") {
      ev.preventDefault();
      sel = Math.max(0, Math.min(items.length - 1, sel + (ev.key === "ArrowDown" ? 1 : -1)));
      items.forEach((a, i) => a.setAttribute("aria-selected", i === sel));
      items[sel] && items[sel].scrollIntoView({ block: "nearest" });
    } else if (ev.key === "Enter") {
      const a = items[sel >= 0 ? sel : 0];
      if (a) { location.hash = a.getAttribute("href"); results.hidden = true; search.blur(); }
    } else if (ev.key === "Escape") { results.hidden = true; search.blur(); }
  });
  document.addEventListener("click", (ev) => { if (!ev.target.closest(".search")) results.hidden = true; });
  results.addEventListener("click", () => { results.hidden = true; search.value = ""; });

  /* ------------------------------------------------------------------ router */
  async function route() {
    closePop(false);
    setMenu(false);
    const h = location.hash.replace(/^#\/?/, "");
    applySettings();
    if (!h) { await renderHome(); window.scrollTo(0, 0); return; }
    if (h === "about") { renderAbout(); window.scrollTo(0, 0); return; }
    const m = h.match(/^(\d)\.(\d)(?:[./](\d+))?$/);
    if (!m) { view.innerHTML = `<p class="loading">That page doesn’t exist. <a href="#/">Go to the contents</a>.</p>`; return; }
    const cid = `${m[1]}.${m[2]}`;
    const meta = state.index.chapters.find((c) => c.id === cid);
    if (!meta) { view.innerHTML = `<p class="loading">There is no Āhnika ${esc(cid)}. <a href="#/">Go to the contents</a>.</p>`; return; }
    if (view.dataset.chapter !== cid) {
      view.innerHTML = `<p class="loading">Loading ${esc(meta.title)}…</p>`;
      renderSidebar(cid);
      const ch = await loadChapter(cid);
      renderChapter(ch, meta);
      applySettings();
    } else {
      renderSidebar(cid);
      observeSutras();
    }
    if (m[3]) {
      const el = document.getElementById(`s-${cid}.${m[3]}`);
      if (el) {
        el.scrollIntoView({ block: "start" });
        el.classList.remove("flash"); void el.offsetWidth; el.classList.add("flash");
      }
    } else {
      window.scrollTo(0, 0);
    }
    $("#main").focus({ preventScroll: true });
  }

  async function init() {
    try {
      state.index = await getJSON("data/index.json");
    } catch (err) {
      view.innerHTML = `<div class="prose"><h1>The text could not be loaded</h1><p>${esc(err.message)}.</p><p>If you opened <code>index.html</code> directly from your computer, the browser blocks the data files. Open the site through GitHub Pages, or run <code>python3 -m http.server</code> in this folder and visit <code>http://localhost:8000</code>.</p></div>`;
      return;
    }
    loadGlossary();
    window.addEventListener("hashchange", route);
    route();
  }
  init();
})();
