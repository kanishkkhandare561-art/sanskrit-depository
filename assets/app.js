/* Sanskrit Depository — reader for Sanskrit texts with tap-to-analyse words.
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
    library: null,
    texts: new Map(),        // tid -> promise of index
    glossaries: new Map(),   // tid -> promise of glossary
    glossary: null,          // glossary of the text being read
    gtid: null,
    chapters: new Map(),     // "tid/cid" -> promise of chapter
    pop: { anchor: null, entry: null, deva: "" },
    corrections: {},         // site-wide corrections committed to the repository (data/corrections.json)
  };

  /* ------------------------------------------------------------------ notes & corrections (kept in this browser) */
  const REPO = "kanishkkhandare561-art/sanskrit-depository";
  const notes = {
    all() { return store.get("sd-notes", {}); },
    get(w) { return this.all()[w] || null; },
    set(w, rec) { const a = this.all(); a[w] = rec; store.set("sd-notes", a); },
    del(w) { const a = this.all(); delete a[w]; store.set("sd-notes", a); },
  };
  const Lipi = window.SDLipi;
  // "विशेषाः + तु + अनन्ताः" or "viśeṣāḥ + tu (tu) + anantāḥ (ananta)" -> parts
  function parseSplit(text) {
    return text.split("+").map((x) => x.trim()).filter(Boolean).map((x) => {
      const m = x.match(/^(.*?)\s*\(([^)]*)\)\s*$/);
      const form = (m ? m[1] : x).trim();
      const lem = m ? m[2].trim() : "";
      const u = Lipi.isDeva(form) ? Lipi.toIast(form) : form.normalize("NFC");
      const l = lem ? (Lipi.isDeva(lem) ? Lipi.toIast(lem) : lem.normalize("NFC")) : "";
      return { u, l: l || guessLemma(u), d: Lipi.toDeva(u), ld: Lipi.toDeva(l || guessLemma(u)), g: "", mine: 1 };
    });
  }
  function splitText(parts) { return parts.map((p) => p.d).join(" + "); }
  // a dictionary form for a typed part, by trying the glossary with common endings removed
  function guessLemma(u) {
    const g = state.glossary || {};
    const cands = [u, u.replace(/ḥ$/, ""), u.replace(/(aḥ|am|aṃ|āt|asya|ena|eṇa|e|āya|au|āḥ|ān|āni|āṇi|aiḥ|ebhyaḥ|ānām|āṇām|eṣu)$/, "a"),
      u.replace(/(ā|ām|āṃ|ayā|āyai|āyāḥ|āyām|āḥ)$/, "ā"), u.replace(/(iḥ|im|iṃ|inā|eḥ|au|ayaḥ|īn)$/, "i"), u.replace(/(uḥ|um|uṃ|unā|oḥ|avaḥ)$/, "u"),
      u.replace(/(tvam|tvaṃ|tvāt|tvena|tve|tvasya)$/, "tva"), u.replace(/(tā|tām|tāṃ|tayā|tāyāḥ|tāyām)$/, "tā"), u.replace(/(t|d)$/, "t"), u.replace(/(t|d)$/, "d"), u + "n", u.replace(/a$/, "an"), u.replace(/o$/, "as"), u.replace(/(ā|ānam)$/, "an"), u.replace(/(aḥ|o)$/, "as")];
    return cands.find((c) => g[c]) || u;
  }
  // the analysis to show: the reader's own correction, then a site-wide correction, then the automatic one
  function effective(e) {
    const mine = notes.get(e.w);
    if (mine && mine.split && mine.split.length) return { ...e, p: mine.split, mine: 1, q: 0 };
    const c = state.corrections[e.w];
    if (c && c.p && c.p.length) return { ...e, p: c.p, corrected: 1, q: 0, cn: c.n || "" };
    if (c && c.n) return { ...e, cn: c.n };
    return e;
  }

  const view = $("#view");
  const pop = $("#pop");
  const popInner = $("#popInner");
  const scrim = $("#scrim");
  const brandSub = $("#brandSub");

  /* ------------------------------------------------------------------ data */
  async function getJSON(url) {
    const r = await fetch(url);
    if (!r.ok) throw new Error(`Could not load ${url} (${r.status})`);
    return r.json();
  }
  function loadText(tid) {
    if (!state.texts.has(tid)) state.texts.set(tid, getJSON(`data/${tid}/index.json`));
    return state.texts.get(tid);
  }
  function loadGlossary(tid) {
    if (!state.glossaries.has(tid)) state.glossaries.set(tid, getJSON(`data/${tid}/glossary.json`));
    return state.glossaries.get(tid);
  }
  function useGlossary(tid) {
    if (state.gtid === tid && state.glossary) return Promise.resolve(state.glossary);
    state.gtid = tid;
    state.glossary = null;
    return loadGlossary(tid).then((g) => { if (state.gtid === tid) state.glossary = g; return g; });
  }
  function loadChapter(tid, cid) {
    const k = `${tid}/${cid}`;
    if (!state.chapters.has(k)) state.chapters.set(k, getJSON(`data/${tid}/${cid}.json`));
    return state.chapters.get(k);
  }

  /* ------------------------------------------------------------------ settings */
  const settings = {
    fs: store.get("sd-fs", 1),
    iast: store.get("sd-iast", true),
    hidden: new Set(store.get("sd-hidden", store.get("sd-bh", true) ? [] : ["bhasya"])),
  };
  const layerStyle = document.createElement("style");
  document.head.appendChild(layerStyle);
  function applySettings() {
    document.documentElement.style.setProperty("--fs", settings.fs);
    view.classList.toggle("hide-iast", !settings.iast);
    layerStyle.textContent = [...settings.hidden].map((k) => `#view [data-l="${k}"]{display:none}`).join("\n");
  }
  $("#sizeUp").addEventListener("click", () => { settings.fs = Math.min(1.4, +(settings.fs + 0.08).toFixed(2)); store.set("sd-fs", settings.fs); applySettings(); });
  $("#sizeDown").addEventListener("click", () => { settings.fs = Math.max(0.8, +(settings.fs - 0.08).toFixed(2)); store.set("sd-fs", settings.fs); applySettings(); });
  $("#themeBtn").addEventListener("click", () => {
    const root = document.documentElement;
    const dark = root.dataset.theme ? root.dataset.theme === "dark" : matchMedia("(prefers-color-scheme: dark)").matches;
    root.dataset.theme = dark ? "light" : "dark";
    try { localStorage.setItem("sd-theme", root.dataset.theme); } catch (e) {}
  });

  /* ------------------------------------------------------------------ helpers */
  const ROMAN = ["", "I", "II", "III", "IV", "V"];
  const ADH_DEVA = { "Adhyāya I": "प्रथमोऽध्यायः", "Adhyāya II": "द्वितीयोऽध्यायः", "Adhyāya III": "तृतीयोऽध्यायः", "Adhyāya IV": "चतुर्थोऽध्यायः", "Adhyāya V": "पञ्चमोऽध्यायः" };
  const sec = (ix) => (ix.root === "section" ? "§" : "");
  function rangeText(ix, c) {
    if (!c.range) return "";
    const [a, b] = c.range;
    return sec(ix) + (a === b ? a : `${a}–${b}`);
  }
  // chapters grouped for the contents and the sidebar
  function groupsOf(ix) {
    const out = [];
    const byKey = new Map();
    for (const c of ix.chapters) {
      let key, label, dv;
      if (c.group) { key = c.group; label = c.group; dv = ADH_DEVA[c.group] || ""; }
      else if (c.appendix) { key = "appendix"; label = "Appendix · Prasāraṇā"; dv = "प्रसारणा"; }
      else { key = c.base || c.id; label = c.title; dv = c.dt || ""; }
      if (!byKey.has(key)) { const g = { key, label, dv, items: [] }; byKey.set(key, g); out.push(g); }
      byKey.get(key).items.push(c);
    }
    return out;
  }
  function entryLabel(c, g) {
    const part = c.part ? (c.part[1] > 1 ? ` · part ${c.part[0]}` : "") : "";
    if (c.short) return c.short + part;
    if (c.appendix) return c.title.replace(/^Prasāraṇā on the /, "") + part;
    if (g && g.items.length > 1) return `Part ${c.part ? c.part[0] : 1}`;
    return c.title;
  }
  function entrySmall(ix, c) {
    if (c.range) return rangeText(ix, c);
    if (c.part) {   // a page that only continues the commentary on the previous page's last sūtra
      const i = ix.chapters.indexOf(c);
      for (let j = i - 1; j >= 0 && (ix.chapters[j].base || ix.chapters[j].id) === c.base; j--) if (ix.chapters[j].range) return `${sec(ix)}${ix.chapters[j].range[1]} (cont.)`;
    }
    const pages = c.nav.filter((n) => n[0] === "g");
    if (pages.length) return `pp. ${pages[0][2].replace(/^p\.\s*/, "")}–${pages[pages.length - 1][2].replace(/^p\.\s*/, "")}`;
    return "";
  }
  const href = (tid, cid, anchor) => `#/${tid}/${cid}${anchor ? "/" + anchor : ""}`;

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

  function renderSidebar(ix, chapterId) {
    let h = "";
    if (!ix) {
      // library level: list the texts
      for (const d of state.library.darshanas) {
        h += `<div class="side-adh"><h3>${esc(d.name)}</h3>`;
        for (const tid of d.texts) {
          const t = state.library.texts[tid];
          if (!t) continue;
          h += `<a class="side-ahn side-text" href="#/${tid}"><span>${esc(t.short)}</span></a>`;
        }
        h += `</div>`;
      }
    } else {
      h += `<a class="side-back" href="#/">← All texts</a>`;
      h += `<a class="side-title${chapterId === "home" ? " on" : ""}" href="#/${ix.id}"><b>${esc(ix.short)}</b><span lang="sa">${esc(ix.deva)}</span></a>`;
      for (const g of groupsOf(ix)) {
        const solo = g.items.length === 1 && entryLabel(g.items[0], g) === g.label;
        h += solo ? `<div class="side-adh solo">` : `<div class="side-adh"><h3>${esc(g.label)}</h3>`;
        for (const c of g.items) {
          const on = c.id === chapterId;
          h += `<a class="side-ahn" href="${href(ix.id, c.id)}" ${on ? 'aria-current="page"' : ""}>${esc(entryLabel(c, g))}<small>${esc(entrySmall(ix, c))}</small></a>`;
          if (on && c.nav.length) {
            h += `<ol class="side-sutras">`;
            for (const n of c.nav) {
              const [kind, anchor, dv, , label] = n;
              if (kind === "s") h += `<li><a href="${href(ix.id, c.id, anchor)}" data-sid="${esc(anchor)}"><span>${esc(sec(ix) + label)}</span><span lang="sa">${esc(dv)}</span></a></li>`;
              else if (kind === "h") h += `<li class="nh"><a href="${href(ix.id, c.id, anchor)}" data-sid="${esc(anchor)}"><span></span><span lang="sa">${esc(dv)}</span></a></li>`;
              else h += `<li class="ng"><a href="${href(ix.id, c.id, anchor)}" data-sid="${esc(anchor)}"><span>${esc(dv)}</span><span></span></a></li>`;
            }
            h += `</ol>`;
          }
        }
        h += `</div>`;
      }
    }
    const nn = Object.keys(notes.all()).length;
    h += `<div class="side-adh"><a class="side-ahn" href="#/notes" ${chapterId === "notes" ? 'aria-current="page"' : ""}>My notes<small>${nn || ""}</small></a><a class="side-ahn" href="#/about" ${chapterId === "about" ? 'aria-current="page"' : ""}>About this depository</a></div>`;
    $("#sideInner").innerHTML = h;
    const on = $(".side-ahn[aria-current]", sidebar);
    if (on && chapterId !== "about") on.scrollIntoView({ block: "nearest" });
  }

  /* ------------------------------------------------------------------ text rendering */
  const NOSPACE_BEFORE = new Set([",", ";", "?", "!", ":", "”", "।", "॥", ")", "."]);
  function wordsHTML(tokens, lex) {
    let out = "";
    let prevOpen = true;
    tokens.forEach((t) => {
      if (typeof t === "string") {
        if (t === "\n") { out += "<br>"; prevOpen = true; return; }
        if (t === "“" || t === "(") { out += (prevOpen ? "" : " ") + t; prevOpen = true; return; }
        if (/^॥.*॥$/.test(t)) { out += " " + t; prevOpen = false; return; }
        out += (NOSPACE_BEFORE.has(t) || prevOpen ? "" : " ") + esc(t);
        prevOpen = false;
        return;
      }
      const [dv, k] = t;
      const e = lex[k];
      let cls = "w";
      if (e && (!e.p.length || e.q)) cls += " low";
      out += (prevOpen ? "" : " ") + `<span class="${cls}" data-k="${k}" tabindex="-1">${dv}</span>`;
      prevOpen = false;
    });
    return out.trim();
  }

  function renderChapter(ix, ch, meta) {
    const idx = ix.chapters.findIndex((c) => c.id === meta.id);
    const prev = ix.chapters[idx - 1];
    const next = ix.chapters[idx + 1];
    const layers = new Map((ix.layers || []).map((l) => [l.k, l]));
    const multi = layers.size > 1;
    const present = new Set();
    let hasRoot = false;
    for (const u of ch.units) for (const sg of u.segs) { if (sg.l && layers.has(sg.l)) present.add(sg.l); if (sg.t === "s") hasRoot = true; }
    const groups = groupsOf(ix);
    const g = groups.find((x) => x.items.includes(meta));
    const crumb = [ix.short, g && g.label !== meta.title ? g.label : "", entryLabel(meta, g) !== (g && g.label) ? entryLabel(meta, g) : ""].filter(Boolean).join(" · ");
    const rt = rangeText(ix, meta);
    let desc = rt ? `${ix.root === "sūtra" ? "Sūtras" : "Sections"} ${rt}. ` : "";
    desc += "Tap any word for its meaning; long words open with their sandhi split.";
    let h = `<header class="ch-head">
      <p class="crumb">${esc(crumb)}</p>
      <h1>${esc(meta.topic || meta.title)}</h1>
      <p>${esc(desc)}</p>
      <div class="ch-controls">
        ${hasRoot ? `<button class="chip-toggle" id="tIast" aria-pressed="${settings.iast}"><span class="dot"></span>Transliteration</button>` : ""}
        ${[...layers.values()].filter((l) => present.has(l.k)).map((l) => `<button class="chip-toggle" data-layer="${l.k}" aria-pressed="${!settings.hidden.has(l.k)}"><span class="dot"></span>${esc(layers.size === 1 ? "Commentary" : l.name)}</button>`).join("")}
      </div>
    </header>`;
    for (const u of ch.units) {
      h += `<section class="unit" id="u-${esc(u.id)}">`;
      let lastLayer = null;
      for (const sg of u.segs) {
        if (sg.t === "g") { h += `<p class="pg" id="g-${sg.id}">${esc(sg.x)}</p>`; continue; }
        if (sg.t === "k") { h += `<p class="cont">${sg.x ? esc(sec(ix) + sg.x) + " " : ""}continued</p>`; continue; }
        const words = wordsHTML(sg.w, ch.lex);
        const L = sg.l && layers.has(sg.l) ? sg.l : null;
        if ((sg.t === "b" || sg.t === "v") && L) {
          if (multi && L !== lastLayer) {
            const l = layers.get(L);
            h += `<p class="bh-label" data-l="${L}"><span lang="sa">${esc(l.deva)}</span> ${esc(l.name)}<small>${esc(l.by)}</small></p>`;
          }
          lastLayer = L;
          h += `<p class="bh${sg.t === "v" ? " verse" : ""}" data-l="${L}" data-words tabindex="0" lang="sa">${words}</p>`;
          continue;
        }
        if (sg.t === "s") {
          lastLayer = null;
          const long = sg.i.length > 180 ? " long" : "";
          h += `<div class="sutra" id="s-${esc(sg.id)}">
            <a class="sn" href="${href(ix.id, meta.id, sg.id)}" aria-label="${ix.root === "sūtra" ? "Sūtra" : "Section"} ${esc(sg.n)}">${esc(sec(ix) + sg.n)}</a>
            <p class="st${long}${sg.verse ? " verse" : ""}" data-words tabindex="0" lang="sa">${words}</p>
            <p class="tl" lang="sa-Latn">${esc(sg.i)}</p>
          </div>`;
        } else if (sg.t === "h") {
          lastLayer = null;
          h += `<h3 class="sec-h" id="h-${sg.id}" data-words tabindex="0" lang="sa">${words}</h3>`;
        } else if (sg.t === "c") {
          h += `<p class="colophon" data-words tabindex="0" lang="sa">${words}</p>`;
        } else {
          h += `<p class="bh main${sg.t === "v" ? " verse" : ""}" data-words tabindex="0" lang="sa">${words}</p>`;
        }
      }
      h += `</section>`;
    }
    h += `<nav class="pager" aria-label="Chapters">
      ${prev ? `<a href="${href(ix.id, prev.id)}"><small>Previous</small>${esc(pagerLabel(ix, prev))}</a>` : ""}
      ${next ? `<a class="next" href="${href(ix.id, next.id)}"><small>Next</small>${esc(pagerLabel(ix, next))}</a>` : ""}
    </nav>`;
    view.innerHTML = h;
    view.dataset.chapter = `${ix.id}/${meta.id}`;
    view.dataset.text = ix.id;
    const ti = $("#tIast");
    if (ti) ti.addEventListener("click", (ev) => { settings.iast = !settings.iast; store.set("sd-iast", settings.iast); ev.currentTarget.setAttribute("aria-pressed", settings.iast); applySettings(); });
    $$("[data-layer]", view).forEach((b) => b.addEventListener("click", (ev) => {
      const k = ev.currentTarget.dataset.layer;
      if (settings.hidden.has(k)) settings.hidden.delete(k); else settings.hidden.add(k);
      store.set("sd-hidden", [...settings.hidden]);
      ev.currentTarget.setAttribute("aria-pressed", !settings.hidden.has(k));
      applySettings();
    }));
    observeAnchors();
    markNoted(ch);
  }
  function markNoted(chIn) {
    const p = chIn ? Promise.resolve(chIn) : state.chapters.get(view.dataset.chapter);
    if (!p) return;
    p.then((ch) => {
      const mine = notes.all();
      $$(".w", view).forEach((w) => {
        const e = ch.lex[+w.dataset.k];
        if (!e) return;
        w.classList.toggle("noted", !!mine[e.w]);
        w.classList.toggle("fixed", !mine[e.w] && !!state.corrections[e.w]);
        if (state.corrections[e.w] || (mine[e.w] && mine[e.w].split && mine[e.w].split.length)) w.classList.remove("low");
      });
    });
  }
  function pagerLabel(ix, c) {
    const g = groupsOf(ix).find((x) => x.items.includes(c));
    const e = entryLabel(c, g);
    return g && g.label !== e && !c.short ? `${g.label} · ${e}` : c.title + (c.part && c.part[1] > 1 ? ` · part ${c.part[0]}` : "");
  }

  let anchorObserver = null;
  function observeAnchors() {
    if (anchorObserver) anchorObserver.disconnect();
    if (!("IntersectionObserver" in window)) return;
    anchorObserver = new IntersectionObserver((entries) => {
      for (const en of entries) {
        if (!en.isIntersecting) continue;
        const sid = en.target.id.slice(2);
        $$(".side-sutras a.on").forEach((a) => a.classList.remove("on"));
        const a = $(`.side-sutras a[data-sid="${CSS.escape(sid)}"]`);
        if (a) { a.classList.add("on"); a.scrollIntoView({ block: "nearest" }); }
      }
    }, { rootMargin: "-80px 0px -70% 0px" });
    $$(".sutra, .sec-h, .pg", view).forEach((s) => anchorObserver.observe(s));
  }

  /* ------------------------------------------------------------------ home */
  async function renderHome() {
    view.innerHTML = $("#tplHome").innerHTML;
    view.dataset.chapter = "home";
    view.dataset.text = "";
    brandSub.textContent = "Sanskrit texts you can read word by word";
    renderSidebar(null, "home");
    let lib = "";
    for (const d of state.library.darshanas) {
      lib += `<section class="darshana"><div class="darshana-head"><h2><span lang="sa">${esc(d.deva)}</span> ${esc(d.name)}</h2><p>${esc(d.blurb)}</p></div><ol class="texts">`;
      for (const tid of d.texts) {
        const t = state.library.texts[tid];
        if (!t) continue;
        const count = t.root === "sūtra" ? `${t.nroots} sūtras` : t.root === "section" ? `${t.nroots} sections` : `${t.nchapters} vādas`;
        lib += `<li><a class="text-card" href="#/${tid}">
          <span class="tc-deva" lang="sa">${esc(t.deva)}</span>
          <b>${esc(t.title)}</b>
          <span class="tc-by">${esc(t.author)}</span>
          <span class="tc-blurb">${esc(t.blurb)}</span>
          <i>${esc(count)}</i></a></li>`;
      }
      lib += `</ol></section>`;
    }
    $("#library").innerHTML = lib;

    await useGlossary("nyaya");
    const ch = await loadChapter("nyaya", "1.1");
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
      useGlossary("nyaya");
      const e = ch.lex[+b.dataset.k];
      $$("button.sel", box).forEach((x) => x.classList.remove("sel"));
      b.classList.add("sel");
      if (b.dataset.part !== undefined) {
        const i = +b.dataset.part, p = e.p[i];
        openPop(b, { w: p.u, p: [p] }, esc(p.d), { context: `Category ${i + 1} of the 16 in the opening compound. <a href="#/nyaya/1.1">Read the sūtra and commentary</a>` });
      } else {
        openPop(b, e, b.textContent);
      }
    });
  }

  /* ------------------------------------------------------------------ text home */
  function renderTextHome(ix) {
    renderSidebar(ix, "home");
    view.dataset.chapter = "text";
    view.dataset.text = ix.id;
    let toc = "";
    for (const g of groupsOf(ix)) {
      if (g.items.length === 1 && entryLabel(g.items[0], g) === g.label) {
        const c = g.items[0];
        const heads = c.nav.filter((n) => n[0] === "h").slice(0, 4).map((n) => n[2]).join(" · ");
        toc += `<li><div class="adh"><span lang="sa">${esc(g.dv || "")}</span><small>${esc(entrySmall(ix, c))}</small></div><div class="ahns">
          <a class="ahn" href="${href(ix.id, c.id)}"><b>${esc(c.title)}</b><span>${esc(c.topic || "")}${heads ? `<em lang="sa">${esc(heads)}</em>` : ""}</span></a></div></li>`;
        continue;
      }
      toc += `<li><div class="adh"><span lang="sa">${esc(g.dv)}</span><small>${esc(g.label)}</small></div><div class="ahns">`;
      for (const c of g.items) {
        const lab = entryLabel(c, g);
        const topic = c.part && c.part[0] > 1 ? "" : c.topic;
        const heads = c.nav.filter((n) => n[0] === "h").slice(0, 4).map((n) => n[2]).join(" · ");
        toc += `<a class="ahn" href="${href(ix.id, c.id)}"><b>${esc(lab === g.label ? (c.short || "Read") : lab)}</b><span>${esc(topic || "")}${heads ? `<em lang="sa">${esc(heads)}</em>` : ""}</span><i>${esc(entrySmall(ix, c))}</i></a>`;
      }
      toc += `</div></li>`;
    }
    const first = ix.chapters[0];
    view.innerHTML = `<section class="text-hero">
        <p class="hero-kicker">${esc(state.library.darshanas.find((d) => d.texts.includes(ix.id)).name)}</p>
        <p class="th-deva" lang="sa">${esc(ix.deva)}</p>
        <h1>${esc(ix.title)}</h1>
        <p class="th-by">${esc(ix.author)}</p>
        <p class="th-blurb">${esc(ix.blurb)}</p>
        ${ix.layers && ix.layers.length > 1 ? `<ul class="th-layers">${ix.layers.map((l) => `<li><span lang="sa">${esc(l.deva)}</span> <b>${esc(l.name)}</b> — ${esc(l.by)}</li>`).join("")}</ul>` : ""}
        ${ix.caution ? `<p class="caution">${esc(ix.caution)}</p>` : ""}
        <div class="hero-actions"><a class="btn primary" href="${href(ix.id, first.id)}">Start reading</a><a class="btn" href="#/about">How the word analysis works</a></div>
      </section>
      <section class="contents" aria-labelledby="contentsTitle">
        <h2 id="contentsTitle">Contents</h2>
        <ol class="toc">${toc}</ol>
        <p class="src-note"><b>Source.</b> ${esc(ix.source)}</p>
      </section>`;
  }

  /* ------------------------------------------------------------------ about */
  async function renderAbout() {
    brandSub.textContent = "Sanskrit texts you can read word by word";
    renderSidebar(null, "about");
    view.dataset.chapter = "about";
    view.dataset.text = "";
    const ids = state.library.darshanas.flatMap((d) => d.texts).filter((t) => state.library.texts[t]);
    const ixs = await Promise.all(ids.map(loadText));
    view.innerHTML = `<article class="prose">
      <h1>About this depository</h1>
      <p>The Sanskrit Depository is a reading room for Sanskrit texts. Each text is shown in Devanagari exactly as it is written, with sandhi intact; tap any word and a popup gives its sandhi split, its grammar and its English meaning.</p>

      <h2>Who made it</h2>
      <p>The Sanskrit Depository is made and maintained by <b>Kanishk Khandare</b>, an undergraduate law student at Maharashtra National Law University (MNLU), Nagpur. The site is his project to make the classical Sanskrit texts of the Nyāya school readable word by word, with every word open to its sandhi split, grammar and meaning, and to correct the analysis as he reads.</p>
      <p>If you find a wrong split or meaning, tap the word and use <b>Add a note or correct this split</b>, then send it from <a href="#/notes">My notes</a>.</p>

      <h2>The texts</h2>
      ${ixs.map((ix) => `<p><b>${esc(ix.title)}</b> <span class="dv">${esc(ix.deva)}</span>. ${esc(ix.source)}</p>`).join("")}
      <p>All the e-texts come from GRETIL (Göttingen Register of Electronic Texts in Indian Languages) and are distributed under the Creative Commons Attribution-NonCommercial-ShareAlike 4.0 licence. Page markers, footnote numerals and similar encoding debris were removed, and the romanised text was converted to Devanagari. Nothing was re-divided: where an e-text runs words together, as a Devanagari print does, so does the page here, and the split is shown only in the popup.</p>

      <h2>How a word is analysed</h2>
      <p>Each word is split by reversing the rules of sandhi: the program tries every possible division of the word, restores the sounds that sandhi merged (for example <code>ā</code> → <code>a + a</code>, <code>e</code> → <code>a + i</code>, a final <code>d</code> → <code>t</code>), and keeps the reading in which every piece is a real Sanskrit word. The last piece is identified grammatically (case, number, tense, person) using the Vidyut morphological lexicon. Meanings come first from glossaries written for Nyāya — one for the Nyāyasūtra and Bhāṣya, one for the technical vocabulary of the later texts — and otherwise from the Monier-Williams <i>Sanskrit–English Dictionary</i> (1899) as digitised by the Cologne Digital Sanskrit Dictionaries. For the Tarkasaṃgraha, the analysed (pada-pāṭha) version in the e-text guides where words and compound members divide.</p>
      <ul class="legend">
        <li><span class="ptag c">Nyāya glossary</span><span>Meaning written for these texts, giving the technical sense used in Nyāya (so <span class="dv">प्रमाण</span> is “means of valid knowledge”, not just “measure”, and <span class="dv">अवच्छेदक</span> is “delimitor”).</span></li>
        <li><span class="ptag mw">Monier-Williams</span><span>Meaning taken from the dictionary. The first senses are shown; the sense intended here may be a later one.</span></li>
        <li><span class="ptag q">Check this analysis</span><span>The split or the grammar is uncertain. Words like this are shown with a dotted underline in the text.</span></li>
        <li><span class="ptag c">Verified</span><span>The analysis was checked by hand.</span></li>
        <li><span class="ptag c">Corrected</span><span>A reader corrected the automatic split; the correction is now part of the site.</span></li>
        <li><span class="ptag me">Your correction</span><span>Your own split, saved in this browser. Words you have a note on carry a small dot.</span></li>
      </ul>
      <p>The analysis is automatic and will sometimes be wrong, especially in the commentaries and in the e-texts that were not proof-read. The sūtras of the Nyāyasūtra and the root text of the Tarkasaṃgraha have been reviewed. Where a form is ambiguous, the popup lists the other possible readings.</p>

      <h2>Keyboard</h2>
      <p>Press <b>Tab</b> to move to a paragraph, <b>Enter</b> to step into its words, <b>←</b> and <b>→</b> to move between words, <b>Enter</b> to open a word and <b>Esc</b> to close it.</p>

      <h2>Corrections and new texts</h2>
      <p>Corrections sent from <a href="#/notes">My notes</a> are added to <code>data/corrections.json</code>, which the site reads directly, and to <code>build/overrides.json</code>, so they survive the next rebuild. The analysis itself is generated by the scripts in the <code>build</code> folder of the repository. To correct a word by hand, add it to <code>build/overrides.json</code>; to improve a meaning, edit <code>build/curated.json</code> or <code>build/curated_navya.json</code>; then run the build again. The same pipeline prepares new texts for the depository.</p>
    </article>`;
  }

  /* ------------------------------------------------------------------ my notes */
  function notesPayload(list) {
    return { format: "sanskrit-depository-notes", version: 1, exported: new Date().toISOString(),
      notes: list.map((n) => ({ w: n.w, d: n.d, text: n.text || "", split: (n.split || []).map((p) => ({ u: p.u, l: p.l })), auto: n.auto || [], where: n.where || "" })) };
  }
  function download(name, text) {
    const a = document.createElement("a");
    a.href = URL.createObjectURL(new Blob([text], { type: "application/json" }));
    a.download = name;
    document.body.appendChild(a); a.click(); a.remove();
    setTimeout(() => URL.revokeObjectURL(a.href), 2000);
  }
  async function renderNotes() {
    brandSub.textContent = "My notes";
    renderSidebar(null, "notes");
    view.dataset.chapter = "notes";
    view.dataset.text = "";
    const all = Object.values(notes.all()).sort((a, b) => (b.t || 0) - (a.t || 0));
    const fixes = all.filter((n) => n.split && n.split.length);
    const rows = all.map((n) => `<li class="note-row">
        <div class="nr-word"><a href="${esc(n.where || "#/")}" lang="sa">${esc(n.d || Lipi.toDeva(n.w))}</a><span class="nr-iast">${esc(n.w)}</span></div>
        <div class="nr-body">
          ${n.split && n.split.length ? `<p><span class="ptag me">Your split</span> <span lang="sa">${esc(splitText(n.split))}</span></p>${n.auto && n.auto.length ? `<p class="nr-auto">Automatic: <span lang="sa">${esc(n.auto.map(Lipi.toDeva).join(" + "))}</span></p>` : ""}` : ""}
          ${n.text ? `<p>${esc(n.text)}</p>` : ""}
          <p class="nr-meta">${n.t ? new Date(n.t).toLocaleDateString() : ""} · <a href="${esc(n.where || "#/")}">Go to the word</a> · <button class="linkbtn" data-del="${esc(n.w)}">Delete</button></p>
        </div></li>`).join("");
    view.innerHTML = `<article class="prose notes-page">
      <h1>My notes</h1>
      <p>Tap any word in any text and choose <b>Add a note or correct this split</b>. You can write a note, and you can retype the sandhi split, parts joined by <code>+</code> — <span class="dv">विशेषाः + तु + अनन्ताः</span> — in Devanagari or IAST. Your split replaces the automatic one straight away, everywhere the word occurs, and the word is marked with a dot in the text.</p>
      <p>Notes are kept in this browser only. To keep them safe or move them to another device, export them. To correct the site for every reader, send your corrections to the repository: when the owner of the repository sends them, they are applied automatically within a minute or two.</p>
      <div class="note-btns big">
        <button class="btn primary" id="nSend" ${fixes.length || all.length ? "" : "disabled"}>Send corrections to the repository</button>
        <button class="btn" id="nExport" ${all.length ? "" : "disabled"}>Export notes</button>
        <label class="btn" for="nImport">Import notes</label><input type="file" id="nImport" accept="application/json,.json" hidden>
      </div>
      <p class="note-status" id="nStatus" role="status"></p>
      ${all.length ? `<h2>${all.length} ${all.length === 1 ? "word" : "words"}</h2><ol class="note-list">${rows}</ol>` : `<p class="empty-notes">No notes yet.</p>`}
    </article>`;
    const status = (m) => { $("#nStatus").textContent = m; };
    $$("[data-del]", view).forEach((b) => b.addEventListener("click", () => { notes.del(b.dataset.del); renderNotes(); }));
    const ex = $("#nExport");
    if (ex) ex.addEventListener("click", () => download(`sanskrit-depository-notes-${new Date().toISOString().slice(0, 10)}.json`, JSON.stringify(notesPayload(all), null, 1)));
    $("#nImport").addEventListener("change", async (ev) => {
      const f = ev.target.files[0];
      if (!f) return;
      try {
        const data = JSON.parse(await f.text());
        let n = 0;
        for (const r of data.notes || []) {
          if (!r.w) continue;
          const split = (r.split || []).map((p) => ({ u: p.u, l: p.l || p.u, d: Lipi.toDeva(p.u), ld: Lipi.toDeva(p.l || p.u), g: "", mine: 1 }));
          notes.set(r.w, { w: r.w, d: r.d || Lipi.toDeva(r.w), text: r.text || "", split, auto: r.auto || [], where: r.where || "", t: Date.now() });
          n++;
        }
        renderNotes();
        setTimeout(() => { const st = $("#nStatus"); if (st) st.textContent = `Imported ${n} ${n === 1 ? "note" : "notes"}.`; }, 0);
      } catch (e) { status("That file could not be read as exported notes."); }
    });
    const send = $("#nSend");
    if (send) send.addEventListener("click", async () => {
      const json = JSON.stringify(notesPayload(all));
      const title = `Corrections: ${all.length} ${all.length === 1 ? "word" : "words"}`;
      const body = "Sent from the My notes page of the Sanskrit Depository.\n\n```json\n" + json + "\n```\n";
      const url = `https://github.com/${REPO}/issues/new?title=${encodeURIComponent(title)}&labels=corrections&body=${encodeURIComponent(body)}`;
      if (url.length < 7500) { window.open(url, "_blank", "noopener"); status("A new GitHub issue has opened in another tab with your corrections filled in. Press Submit new issue there."); return; }
      try { await navigator.clipboard.writeText(body); } catch (e) { download("sanskrit-depository-corrections.json", json); }
      window.open(`https://github.com/${REPO}/issues/new?title=${encodeURIComponent(title)}&labels=corrections`, "_blank", "noopener");
      status("There are too many corrections to fit in a link, so they were copied to your clipboard (or downloaded). Paste them into the body of the GitHub issue that opened, then press Submit new issue.");
    });
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

  function renderPop(focusPart, editing) {
    const { deva } = state.pop;
    const auto = state.pop.entry;
    const e = state.pop.showAuto ? auto : effective(auto);
    const parts = e.p || [];
    let h = `<button class="pop-close" id="popClose" aria-label="Close"><svg viewBox="0 0 24 24"><path d="M6 6l12 12M18 6L6 18"/></svg></button>
      <p class="pw${deva.length > 22 ? " long" : ""}" id="popWord" lang="sa">${deva}</p>
      <p class="pw-iast" lang="sa-Latn">${esc(e.w)}</p>`;
    let tags = "";
    if (e.mine) tags += `<span class="ptag me">Your correction</span>`;
    else if (e.corrected) tags += `<span class="ptag c">Corrected</span>`;
    else if (e.v) tags += `<span class="ptag c">Verified</span>`;
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
    h += noteSection(auto, e, editing);
    const linkWord = parts.length === 1 ? parts[0].l : focusPart != null && parts[focusPart] ? parts[focusPart].l : parts.length ? null : e.w.replace(/^'/, "a");
    if (linkWord) h += `<div class="pfoot"><a href="https://www.wisdomlib.org/definition/${slug(linkWord)}" target="_blank" rel="noopener">Look up “${esc(linkWord)}” on Wisdomlib</a></div>`;
    else h += `<div class="pfoot"><span class="src">Tap a part to read its full entry.</span></div>`;
    popInner.innerHTML = h;
    $("#popClose").addEventListener("click", () => closePop(true));
    if (editing) { const t = $("#noteSplit", popInner); if (t) { t.focus(); t.setSelectionRange(t.value.length, t.value.length); } }
  }

  function noteSection(auto, e, editing) {
    const mine = notes.get(auto.w);
    let h = `<div class="psec notes-sec">`;
    if (e.cn) h += `<p class="note"><b>Note:</b> ${esc(e.cn)}</p>`;
    if (editing) {
      const cur = mine && mine.split && mine.split.length ? mine.split : (effective(auto).p || []);
      h += `<form class="note-form" id="noteForm">
        <label for="noteSplit">Sandhi split <small>parts joined by +, in Devanagari or IAST; add a dictionary form in brackets if you like: <span lang="sa">अनन्ताः (अनन्त)</span></small></label>
        <input id="noteSplit" lang="sa" autocomplete="off" spellcheck="false" value="${esc(cur.map((p) => p.d + (p.l && p.l !== p.u ? ` (${p.ld || Lipi.toDeva(p.l)})` : "")).join(" + "))}">
        <label for="noteText">Note</label>
        <textarea id="noteText" rows="3" placeholder="What is wrong, or anything you want to remember about this word">${esc(mine ? mine.text || "" : "")}</textarea>
        <div class="note-btns"><button class="btn primary sm" type="submit">Save</button><button class="btn sm" type="button" data-note-cancel>Cancel</button>${mine ? `<button class="btn sm danger" type="button" data-note-del>Delete</button>` : ""}</div>
        <p class="note-hint">Saved in this browser and applied at once. To correct the site for everyone, send it from <a href="#/notes">My notes</a>.</p>
      </form>`;
    } else if (mine) {
      h += `<div class="my-note"><h4>Your note</h4>${mine.text ? `<p>${esc(mine.text)}</p>` : ""}${mine.split && mine.split.length ? `<p class="my-split">Your split: <span lang="sa">${esc(splitText(mine.split))}</span></p>` : ""}
        <div class="note-btns"><button class="linkbtn" type="button" data-note-edit>Edit</button>${mine.split && mine.split.length ? `<button class="linkbtn" type="button" data-show-auto>${state.pop.showAuto ? "Show your split" : "Show the automatic split"}</button>` : ""}</div></div>`;
    } else {
      h += `<button class="linkbtn note-open" type="button" data-note-edit>✎ Add a note or correct this split</button>`;
    }
    return h + `</div>`;
  }

  popInner.addEventListener("submit", (ev) => {
    ev.preventDefault();
    const auto = state.pop.entry;
    const sp = $("#noteSplit", popInner).value.trim();
    const tx = $("#noteText", popInner).value.trim();
    const autoText = splitText(effective({ ...auto }).p || []);
    let split = sp ? parseSplit(sp) : [];
    const typed = split.map((p) => p.d).join(" + ");
    const old = notes.get(auto.w);
    // keep the split only if the reader changed it
    if (typed === autoText && !(old && old.split && old.split.length)) split = [];
    if (!tx && !split.length) { notes.del(auto.w); }
    else notes.set(auto.w, { w: auto.w, d: state.pop.deva.replace(/<[^>]+>/g, ""), text: tx, split, auto: (auto.p || []).map((p) => p.u), where: location.hash, t: Date.now() });
    state.pop.showAuto = false;
    renderPop(null);
    markNoted();
  });
  popInner.addEventListener("click", (ev) => {
    ev.stopPropagation();
    if (ev.target.closest("[data-note-edit]")) { renderPop(null, true); return; }
    if (ev.target.closest("[data-note-cancel]")) { renderPop(null); return; }
    if (ev.target.closest("[data-note-del]")) { notes.del(state.pop.entry.w); renderPop(null); markNoted(); return; }
    if (ev.target.closest("[data-show-auto]")) { state.pop.showAuto = !state.pop.showAuto; renderPop(null); return; }
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
    state.pop = { anchor, entry, deva, context: opts.context || "", showAuto: false };
    anchor.classList.add("sel");
    renderPop(opts.focusPart ?? null);
    pop.hidden = false;
    position();
    if (matchMedia("(max-width: 680px)").matches) scrim.hidden = false;
    if (!state.glossary) {
      const want = state.gtid;
      loadGlossary(want).then((g) => {
        if (state.gtid === want) state.glossary = g;
        if (state.pop.entry === entry) { const c = $(".part[aria-pressed='true']", popInner); renderPop(c ? +c.dataset.i : opts.focusPart ?? null); }
      });
    }
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

  function openWord(w, opts) {
    const key = view.dataset.chapter;
    const p = state.chapters.get(key);
    if (!p) return;
    useGlossary(view.dataset.text);
    p.then((ch) => openPop(w, ch.lex[+w.dataset.k], w.innerHTML, opts));
  }

  document.addEventListener("click", (ev) => {
    const w = ev.target.closest(".w");
    if (w && view.contains(w)) { openWord(w); return; }
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
    if (t.matches("input, textarea")) return;
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
        openWord(t, { keyboard: true });
      }
    }
  });

  /* ------------------------------------------------------------------ search */
  const search = $("#search");
  const results = $("#searchResults");
  const fold = (s) => s.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase().replace(/[^a-z0-9.ऀ-ॿ ]/g, "");
  let sel = -1;
  let searchSeq = 0;
  async function runSearch() {
    const q = search.value.trim();
    if (!q || !state.library) { results.hidden = true; return; }
    const seq = ++searchSeq;
    const cur = view.dataset.text;
    const ids = cur ? [cur, ...state.library.darshanas.flatMap((d) => d.texts).filter((t) => t !== cur)] : state.library.darshanas.flatMap((d) => d.texts);
    const ixs = await Promise.all(ids.filter((t) => state.library.texts[t]).map(loadText));
    if (seq !== searchSeq) return;
    const fq = fold(q);
    const isNum = /^§?\d+(\.\d*){0,2}$/.test(q);
    const qn = q.replace(/^§/, "");
    const hits = [];
    for (const ix of ixs) {
      for (const c of ix.chapters) {
        for (const n of c.nav) {
          if (n[0] === "g") continue;
          const [kind, anchor, dv, ia, label] = n;
          let ok;
          if (isNum) ok = kind === "s" && (label === qn || label.startsWith(qn.endsWith(".") ? qn : qn + "."));
          else ok = fold(ia).includes(fq) || dv.includes(q);
          if (ok && !(kind === "s" && hits.some((h) => h.ix === ix && h.label === label && h.kind === "s"))) hits.push({ ix, c, kind, anchor, dv, ia, label });
          if (hits.length >= 60) break;
        }
      }
    }
    sel = -1;
    const many = new Set(hits.map((h) => h.ix.id)).size > 1;
    results.innerHTML = hits.length
      ? hits.map((h) => `<a href="${href(h.ix.id, h.c.id, h.anchor)}" role="option"><span class="num">${h.kind === "s" ? esc(sec(h.ix) + h.label) : "—"}</span><span class="dv" lang="sa">${esc(h.dv)}</span><span class="tr">${many ? `<b>${esc(h.ix.short)}</b> · ` : ""}${esc(h.ia)}</span></a>`).join("")
      : `<div class="empty">Nothing matches “${esc(q)}”. Try a number such as 2.1.4, or part of a word in Devanagari or romanisation.</div>`;
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
  function notFound(msg) {
    view.innerHTML = `<p class="loading">${msg} <a href="#/">Go to the contents</a>.</p>`;
  }
  async function route() {
    closePop(false);
    setMenu(false);
    const h = decodeURIComponent(location.hash.replace(/^#\/?/, ""));
    applySettings();
    if (!h) { await renderHome(); window.scrollTo(0, 0); return; }
    if (h === "about") { await renderAbout(); window.scrollTo(0, 0); return; }
    if (h === "notes") { await renderNotes(); window.scrollTo(0, 0); return; }
    // links from before the depository held more than one text: #/1.1, #/1.1.4
    if (/^\d\.\d(?:[./]\d+)?$/.test(h)) { location.replace(`#/nyaya/${h.replace("/", ".")}`); return; }
    const [tid, x, y] = h.split("/");
    if (!state.library.texts[tid]) { notFound("That page doesn’t exist."); return; }
    const ix = await loadText(tid);
    brandSub.textContent = ix.title;
    useGlossary(tid);
    if (!x) { renderTextHome(ix); window.scrollTo(0, 0); $("#main").focus({ preventScroll: true }); return; }
    let meta = ix.chapters.find((c) => c.id === x);
    let anchor = y;
    if (!meta) {
      meta = ix.chapters.find((c) => c.nav.some((n) => n[1] === x));
      anchor = x;
      if (!meta) {   // a chapter that was split into parts: go to its first part
        meta = ix.chapters.find((c) => c.base === x);
        anchor = y;
      }
    }
    if (!meta) { notFound(`There is no “${esc(x)}” in ${esc(ix.short)}.`); return; }
    const key = `${tid}/${meta.id}`;
    if (view.dataset.chapter !== key) {
      view.innerHTML = `<p class="loading">Loading ${esc(meta.title)}…</p>`;
      renderSidebar(ix, meta.id);
      const ch = await loadChapter(tid, meta.id);
      renderChapter(ix, ch, meta);
      applySettings();
    } else {
      renderSidebar(ix, meta.id);
      observeAnchors();
    }
    if (anchor) {
      const el = document.getElementById(`s-${anchor}`) || document.getElementById(`h-${anchor}`) || document.getElementById(`g-${anchor}`) || document.getElementById(`u-${anchor}`);
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
      state.library = await getJSON("data/library.json");
      try { state.corrections = await getJSON("data/corrections.json"); } catch (e) { state.corrections = {}; }
    } catch (err) {
      view.innerHTML = `<div class="prose"><h1>The texts could not be loaded</h1><p>${esc(err.message)}.</p><p>If you opened <code>index.html</code> directly from your computer, the browser blocks the data files. Open the site through GitHub Pages, or run <code>python3 -m http.server</code> in this folder and visit <code>http://localhost:8000</code>.</p></div>`;
      return;
    }
    window.addEventListener("hashchange", route);
    route();
  }
  init();
})();
