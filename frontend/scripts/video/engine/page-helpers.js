/* Injected into every app frame (init script). Gives the renderer one shared,
 * deterministic way to locate cards/controls, read bound numbers, and act.
 * Also freezes CSS transitions and hides scrollbars so captures are clean. */
(() => {
  if (window.__vq) return;
  const FREEZE_CSS =
    "*,*::before,*::after{transition:none!important;animation:none!important;caret-color:transparent!important}" +
    "html{scrollbar-width:none!important}::-webkit-scrollbar{display:none!important}";
  const addFreeze = () => {
    if (document.getElementById("__vq-freeze") || !document.head) return;
    const s = document.createElement("style");
    s.id = "__vq-freeze";
    s.textContent = FREEZE_CSS;
    document.head.appendChild(s);
  };
  document.addEventListener("DOMContentLoaded", addFreeze);
  new MutationObserver(addFreeze).observe(document, { childList: true, subtree: true });

  const norm = (s) => (s || "").replace(/\s+/g, " ").trim().toLowerCase();
  const visible = (el) => {
    const r = el.getBoundingClientRect();
    const cs = getComputedStyle(el);
    return r.width > 0 && r.height > 0 && cs.visibility !== "hidden" && cs.display !== "none";
  };
  const box = (el) => {
    const r = el.getBoundingClientRect();
    return { x: r.x, y: r.y, w: r.width, h: r.height };
  };
  const union = (rs) => {
    const x1 = Math.min(...rs.map((r) => r.x)), y1 = Math.min(...rs.map((r) => r.y));
    const x2 = Math.max(...rs.map((r) => r.x + r.w)), y2 = Math.max(...rs.map((r) => r.y + r.h));
    return { x: x1, y: y1, w: x2 - x1, h: y2 - y1 };
  };
  const area = (el) => { const r = el.getBoundingClientRect(); return r.width * r.height; };
  const HEADING = "h1,h2,h3,h4,h5,h6,[role=heading]";
  const CLICKABLE = "button,a,[role=tab],[role=button],[role=link],summary,label";

  // Element whose visible text equals `text` (case/space-insensitive). Prefers headings, then smallest.
  function byText(text) {
    const want = norm(text);
    const all = [...document.body.querySelectorAll("*")].filter(
      (el) => !["SCRIPT", "STYLE", "SVG", "OPTION", "SELECT"].includes(el.tagName.toUpperCase()) && visible(el) && norm(el.innerText) === want,
    );
    if (!all.length) return null;
    all.sort((a, b) => (b.matches(HEADING) ? 1 : 0) - (a.matches(HEADING) ? 1 : 0) || area(a) - area(b));
    return all[0];
  }

  // Nearest framed ancestor (border, shadow or background) around a heading.
  function card(text) {
    const h = byText(text);
    if (!h) return null;
    const hr = h.getBoundingClientRect();
    let e = h;
    for (let i = 0; i < 12 && e.parentElement && e.parentElement !== document.body; i++) {
      e = e.parentElement;
      const cs = getComputedStyle(e);
      const r = e.getBoundingClientRect();
      const bg = cs.backgroundColor;
      const framed =
        parseFloat(cs.borderTopWidth) > 0 || parseFloat(cs.borderLeftWidth) > 0 || cs.boxShadow !== "none" ||
        (bg !== "rgba(0, 0, 0, 0)" && bg !== "transparent");
      if (framed && r.height > hr.height * 1.6 && r.height < window.innerHeight * 0.95 && r.width >= hr.width) return e;
    }
    return null;
  }

  function control(label) {
    const want = norm(label);
    for (const el of document.querySelectorAll("select,input,[role=combobox]")) {
      if (norm(el.getAttribute("aria-label")) === want) return el;
      if (el.id) {
        const l = document.querySelector(`label[for="${CSS.escape(el.id)}"]`);
        if (l && norm(l.innerText) === want) return el;
      }
      const wrap = el.closest("label");
      if (wrap && norm(wrap.innerText).startsWith(want)) return el;
    }
    return null;
  }

  // Locator forms: "css selector" | {card} | {cards:[...]} | {text} | {control}
  function findAll(loc) {
    if (typeof loc === "string") {
      const el = document.querySelector(loc);
      return el && visible(el) ? [el] : [];
    }
    if (loc && loc.card) { const c = card(loc.card); return c ? [c] : []; }
    if (loc && loc.cards) {
      const cs = loc.cards.map(card);
      return cs.every(Boolean) ? cs : [];
    }
    if (loc && loc.text) { const e = byText(loc.text); return e ? [e] : []; }
    if (loc && loc.control) { const e = control(loc.control); return e ? [e] : []; }
    return [];
  }
  const describe = (loc) => (typeof loc === "string" ? loc : JSON.stringify(loc));

  function rect(loc) {
    const els = findAll(loc);
    if (!els.length) return { error: `Not found on page: ${describe(loc)}` };
    return { rect: union(els.map(box)) };
  }

  const PICKS = {
    percent: /[-−]?\d[\d,]*(?:\.\d+)?\s?%/g,
    count: /(?<![\d.,£€$])\d{1,3}(?:,\d{3})+(?![\d.%])|(?<![\d.,£€$])\d+(?![\d.,%])/g,
    number: /[£€$]?[-−]?\d[\d,]*(?:\.\d+)?(?:\s?%|[kmb]n?\b)?/gi,
  };

  // Bind spec: {from: locator, line?: 1-based, pick: percent|count|number|text, nth?: 1-based}
  function bind(spec) {
    const els = findAll(spec.from);
    if (!els.length) return { error: `Bind source not found: ${describe(spec.from)}` };
    const text = els.map((e) => e.innerText).join("\n");
    const lines = text.split("\n").map((s) => s.trim()).filter(Boolean);
    let src = text.replace(/\s+/g, " ").trim();
    if (spec.line) {
      if (!lines[spec.line - 1]) return { error: `Line ${spec.line} missing. Lines: ${JSON.stringify(lines.slice(0, 12))}` };
      src = lines[spec.line - 1];
    }
    if (spec.pick === "text") return { value: src, context: src };
    const re = PICKS[spec.pick];
    const found = src.match(re) || [];
    const nth = spec.nth || 1;
    if (!found[nth - 1]) return { error: `No ${spec.pick} #${nth} in "${src.slice(0, 120)}"` };
    return { value: found[nth - 1].replace("−", "-").trim(), context: src.slice(0, 160) };
  }

  function options(loc) {
    const [el] = findAll(loc);
    if (!el || el.tagName !== "SELECT") return { error: `Not a <select>: ${describe(loc)}` };
    return {
      options: [...el.options].map((o) => ({ value: o.value, label: o.textContent.trim() })),
      selected: el.selectedIndex,
    };
  }

  function select(loc, value) {
    const [el] = findAll(loc);
    if (!el || el.tagName !== "SELECT") return { error: `Not a <select>: ${describe(loc)}` };
    const setter = Object.getOwnPropertyDescriptor(HTMLSelectElement.prototype, "value").set;
    setter.call(el, value);
    el.dispatchEvent(new Event("input", { bubbles: true }));
    el.dispatchEvent(new Event("change", { bubbles: true }));
    // Controlled selects re-render asynchronously; callers confirm via options() after settling.
    return { ok: true };
  }

  function click(loc) {
    const [el] = findAll(loc);
    if (!el) return { error: `Not found: ${describe(loc)}` };
    const target = el.closest(CLICKABLE) || el;
    target.click();
    return { ok: true };
  }

  // Bars inside a region, for hover tokens bar:tallest / bar:shortest.
  function bars(regionLoc) {
    const [region] = findAll(regionLoc);
    const scope = region || document;
    return [...scope.querySelectorAll('g[aria-label="bar"] rect, g[aria-label="bar"] path, .recharts-bar-rectangle path, .recharts-rectangle, rect.bar, [data-bar]')]
      .map(box)
      .filter((r) => r.w > 2 && r.h > 2);
  }

  function hoverPoint(token, regionLoc) {
    if (token === "bar:tallest" || token === "bar:shortest") {
      const bs = bars(regionLoc);
      if (!bs.length) return { error: `No chart bars inside ${describe(regionLoc)}` };
      bs.sort((a, b) => b.h - a.h);
      const r = token === "bar:tallest" ? bs[0] : bs[bs.length - 1];
      return { point: [r.x + r.w / 2, r.y + Math.min(r.h / 2, 40)] };
    }
    const res = rect(token);
    if (res.error) return res;
    return { point: [res.rect.x + res.rect.w / 2, res.rect.y + res.rect.h / 2] };
  }

  // Changes while text, data or chart geometry (incl. JS-driven chart animation) changes.
  function signature() {
    let t = document.body ? document.body.innerText : "";
    const shapes = document.querySelectorAll("svg path, svg rect, svg circle, svg line");
    for (let i = 0; i < Math.min(shapes.length, 3000); i++) {
      const e = shapes[i];
      t += (e.getAttribute("d") || "") + (e.getAttribute("height") || "") + (e.getAttribute("width") || "") + (e.getAttribute("transform") || "");
    }
    t += String(document.querySelectorAll("[aria-busy=true], .animate-pulse, [data-loading=true]").length);
    // Network activity (map tiles, lazy images) keeps the page "unsettled" until it stops.
    t += String(performance.getEntriesByType("resource").length);
    t += String([...document.images].filter((im) => im.complete).length);
    let h = 0;
    for (let i = 0; i < t.length; i++) h = (h * 31 + t.charCodeAt(i)) | 0;
    return `${t.length}:${h}:${shapes.length}`;
  }

  // Page map for storyboard authors (used by --inspect).
  function inspect() {
    const out = { url: location.pathname + location.search, controls: [], cards: [], headings: [], clickables: [] };
    for (const el of document.querySelectorAll("select")) {
      if (!visible(el)) continue;
      const label = el.getAttribute("aria-label") || (el.id && document.querySelector(`label[for="${CSS.escape(el.id)}"]`)?.innerText) || "";
      out.controls.push({ control: label.trim(), selected: el.value, options: [...el.options].map((o) => `${o.value} = ${o.textContent.trim()}`), rect: box(el) });
    }
    const seen = new Set();
    for (const h of document.querySelectorAll(HEADING)) {
      if (!visible(h)) continue;
      const text = h.innerText.replace(/\s+/g, " ").trim();
      if (!text || seen.has(text)) continue;
      seen.add(text);
      const r = box(h);
      if (r.y > window.innerHeight) { out.headings.push({ text, belowFold: true }); continue; }
      out.headings.push({ text });
      const c = card(text);
      if (!c) continue;
      const lines = c.innerText.split("\n").map((s) => s.trim()).filter(Boolean);
      const numericLines = lines
        .map((l, i) => ({ line: i + 1, text: l }))
        .filter((x) => /\d/.test(x.text))
        .slice(0, 6);
      out.cards.push({ card: text, rect: box(c), numericLines });
    }
    out.footers = [];
    for (const f of document.querySelectorAll("footer, [role=contentinfo]")) {
      if (!visible(f)) continue;
      const cls = [...f.classList].find((c) => /^[a-z][\w-]*$/i.test(c));
      const first = f.querySelector(":scope > span, :scope > p");
      const sel = cls ? `.${cls}${first ? " > " + first.tagName.toLowerCase() : ""}` : "footer";
      out.footers.push({ selector: sel, text: (first || f).innerText.replace(/\s+/g, " ").trim() });
    }
    // Metric tiles whose label is not a heading: framed, short, label line + number line.
    for (const el of document.querySelectorAll("div,section,article,li")) {
      if (!visible(el)) continue;
      const r = el.getBoundingClientRect();
      if (r.height > 220 || r.height < 40 || r.width < 80 || r.y > window.innerHeight) continue;
      const cs = getComputedStyle(el);
      const framed = parseFloat(cs.borderTopWidth) > 0 || cs.boxShadow !== "none";
      if (!framed) continue;
      const lines = el.innerText.split("\n").map((x) => x.trim()).filter(Boolean);
      if (lines.length < 2 || lines.length > 5 || /\d/.test(lines[0]) || !lines.some((l) => /\d/.test(l))) continue;
      const label = lines[0];
      if (seen.has(label) || card(label) !== el) continue;
      seen.add(label);
      out.cards.push({ card: label, rect: box(el), numericLines: lines.map((l, i) => ({ line: i + 1, text: l })).filter((x) => /\d/.test(x.text)).slice(0, 4), tile: true });
    }
    for (const el of document.querySelectorAll("[role=tab],button,a")) {
      if (!visible(el) || el.getBoundingClientRect().width < 8 || el.getBoundingClientRect().height < 8) continue;
      const text = el.innerText.replace(/\s+/g, " ").trim();
      if (!text || text.length > 40) continue;
      const r = box(el);
      if (r.y > window.innerHeight) continue;
      out.clickables.push({ text, role: el.getAttribute("role") || el.tagName.toLowerCase() });
    }
    return out;
  }

  // Font sizes of visible text inside a target (for legibility QA) and its corner radius.
  function metrics(loc) {
    const els = findAll(loc);
    if (!els.length) return { error: `Not found on page: ${describe(loc)}` };
    const sizes = [];
    for (const root of els) {
      const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
      for (let n = walker.nextNode(); n; n = walker.nextNode()) {
        if (!n.textContent.trim()) continue;
        const el = n.parentElement;
        if (!el || !visible(el)) continue;
        const cs = getComputedStyle(el);
        if (Number(cs.opacity) < 0.5) continue;
        sizes.push([parseFloat(cs.fontSize), n.textContent.trim().length]);
      }
      for (const t of root.querySelectorAll("svg text")) {
        if (visible(t)) sizes.push([parseFloat(getComputedStyle(t).fontSize) || 10, t.textContent.trim().length]);
      }
    }
    const radius = parseFloat(getComputedStyle(els[0]).borderTopLeftRadius) || 0;
    // "min" = size at the 15th percentile of characters, so a few footnote/attribution words
    // do not decide legibility but a card of small text does. "tiny" = true minimum.
    sizes.sort((a, b) => a[0] - b[0]);
    const total = sizes.reduce((s, x) => s + x[1], 0);
    let acc = 0, p15 = sizes.length ? sizes[0][0] : 0;
    for (const [fs, n] of sizes) { acc += n; if (acc >= total * 0.15) { p15 = fs; break; } }
    // Share of the target covered by its largest map/chart surface (canvas or svg).
    const tr = els[0].getBoundingClientRect();
    let visualArea = 0;
    for (const v of els[0].querySelectorAll("canvas, svg")) {
      const vr = v.getBoundingClientRect();
      visualArea = Math.max(visualArea, vr.width * vr.height);
    }
    const visual = visualArea / Math.max(1, tr.width * tr.height);
    return { min: p15, tiny: sizes.length ? sizes[0][0] : 0, max: sizes.length ? sizes.at(-1)[0] : 0, radius, visual };
  }

  window.__vq = { rect, bind, options, select, click, hoverPoint, signature, inspect, metrics };
})();
