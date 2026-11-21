// Compiles a validated storyboard + measured page facts into an absolute timeline.
// Authors never write times; every beat's choreography is fixed here.
import { STAGE } from "./stage.mjs";
import { LIMITS } from "./validate.mjs";
import { LEAD, TAIL } from "./audio.mjs";

const ENTER = 1.8;
const EXIT = 1.6;
const PAD = 10;

const clamp = (x, a, b) => Math.min(b, Math.max(a, x));
const esc = (s) => String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");

// Escape, apply **bold** (captions/tails) and fill {{binds}} with escaped values.
export function richText(text, values, { bold = true } = {}) {
  if (text == null) return null;
  let s = esc(text);
  if (bold) s = s.replace(/\*\*([^*]+)\*\*/g, "<b>$1</b>");
  return s.replace(/\{\{\s*([a-zA-Z]\w*)\s*\}\}/g, (_, n) => {
    if (values[n] == null) throw new Error(`Unresolved bind {{${n}}}`);
    return esc(values[n]);
  });
}
export function plainText(text, values) {
  if (text == null) return null;
  return String(text).replace(/\*/g, "").replace(/\{\{\s*([a-zA-Z]\w*)\s*\}\}/g, (_, n) => values[n]);
}

// Title words; *italic* spans become accent italics, one span per word.
function titleWords(title) {
  const words = [];
  let italic = false;
  for (const raw of title.trim().split(/\s+/)) {
    let w = raw;
    const opens = w.startsWith("*");
    if (opens) { italic = true; w = w.slice(1); }
    const closes = w.endsWith("*");
    if (closes) w = w.slice(0, -1);
    words.push({ html: italic ? `<em>${esc(w)}</em>` : esc(w) });
    if (closes) italic = false;
  }
  return words;
}

function statValue(text) {
  const m = /^(\D*?)(-?\d[\d,]*(?:\.\d+)?)(.*)$/.exec(text);
  if (!m) return { text, num: null, prefix: "", suffix: "", decimals: 0, grouping: false };
  const decimals = (m[2].split(".")[1] || "").length;
  return { text, num: parseFloat(m[2].replace(/,/g, "")), prefix: m[1], suffix: m[3], decimals, grouping: m[2].includes(",") };
}

const toWin = (r) => ({ x: r.x, y: r.y + STAGE.titlebar, w: r.w, h: r.h });
const padRect = (r, p = PAD) => ({ x: r.x - p, y: r.y - p, w: r.w + 2 * p, h: r.h + 2 * p });
const center = (r) => [r.x + r.w / 2, r.y + r.h / 2];
const worldOf = ([wx, wy]) => [STAGE.winX + wx, STAGE.winY + wy];
const union = (a, b) => {
  const x = Math.min(a.x, b.x), y = Math.min(a.y, b.y);
  return { x, y, w: Math.max(a.x + a.w, b.x + b.w) - x, h: Math.max(a.y + a.h, b.y + b.h) - y };
};
// Largest zoom that keeps rect inside the safe frame above the caption band.
const fitZoom = (r, cap) => clamp(Math.min(cap, 1760 / (r.w + 100), 760 / (r.h + 110)), 1, cap);

// voice: optional { [unitKey]: seconds of recorded speech }. Units stretch to fit their line.
// beats: optional music beat times; scene/beat ends snap forward onto a beat when one is within 0.5s.
export function compile(story, prep, voice = {}, beats = null) {
  const S = STAGE;
  const TL = {
    constants: { winX: S.winX, winY: S.winY, anchorX: S.anchorX, anchorY: S.anchorY, cursorTip: S.cursorTip },
    kinetic: [], windowSpans: [], shots: [{ at: 0, dur: 0, z: 1, f: [S.anchorX, S.anchorY] }],
    spots: [], captions: [], cursor: { keys: [], vis: [], clicks: [], live: [] }, menus: [], lifts: [],
  };
  const legibility = []; // {label, minPx, keyPx, kind}: on-screen text size after zoom/lift, in 1080p pixels
  const beatStats = { snapped: 0, total: 0 };
  const snap = (start, sec) => {
    if (!beats?.length) return sec;
    beatStats.total++;
    const end = start + sec;
    const nb = beats.find((b) => b >= end - 0.02);
    if (nb != null && nb - end <= 0.5) { beatStats.snapped++; return nb - start; }
    return sec;
  };
  const actions = [];
  const checks = []; // {t, rect(window), label} — targets that must be fully on screen
  const cues = []; // {key, at} — where each narration line starts
  const fitVoice = (key, kind, sec, tail, start) => {
    const d = voice[key];
    if (d == null) return sec;
    cues.push({ key, at: start + LEAD[kind], dur: d });
    return Math.max(sec, LEAD[kind] + d + tail);
  };
  let t = 0;
  let capN = 0;
  const caption = (html, start, end) => { if (html) TL.captions.push({ id: `cap-${capN++}`, html, start, end }); };
  const shot = (at, dur, z, f, ease) => TL.shots.push({ at, dur, z, f, ease });
  let lastFocus = null; // where the camera last framed something, for the zoom-through exit
  let fullZ = 1, fullF = [S.anchorX, S.anchorY];
  const full = (at, dur) => shot(at, dur, fullZ, fullF);
  const fit = (r, cap) => Math.max(fullZ, fitZoom(r, Math.max(cap, fullZ)));

  story.scenes.forEach((scene, i) => {
    const p = prep.scenes[i];
    if (scene.type !== "app") {
      const sec = snap(t, fitVoice(`s${i}`, scene.type, scene.seconds ?? LIMITS[scene.type].def, TAIL.kinetic, t));
      const v = p.values;
      const k = { id: `k-${i}`, type: scene.type, start: t, end: t + sec };
      if (scene.type === "title") {
        Object.assign(k, { eyebrow: richText(scene.eyebrow ?? "", v, { bold: false }), words: titleWords(scene.title), reveal: scene.reveal ?? "mask", layout: scene.layout ?? "center", subtitle: richText(scene.subtitle, v, { bold: false }) });
      } else if (scene.type === "stat") {
        Object.assign(k, {
          lead: richText(scene.lead, v), layout: scene.layout ?? (scene.value2 ? "versus" : "center"),
          values: [scene.value, scene.value2].filter(Boolean).map((x) => statValue(plainText(x, v))),
          labels: (scene.labels || []).map((l) => richText(l, v, { bold: false })),
          tail: richText(scene.tail, v), source: richText(scene.source, v, { bold: false }),
        });
      } else if (scene.type === "quote") {
        Object.assign(k, {
          text: esc(plainText(scene.text, v)), attribution: richText(scene.attribution, v, { bold: false }),
          source: richText(scene.source, v, { bold: false }),
        });
      } else {
        Object.assign(k, {
          eyebrow: richText(scene.eyebrow, v, { bold: false }),
          title: esc(scene.title ?? "Aequitas").replace(/\*([^*]+)\*/g, "<em>$1</em>"),
          subtitle: richText(scene.subtitle ?? "Public transport equity briefings against official deprivation indices.", v, { bold: false }),
          url: esc(scene.url ?? S.host), source: richText(scene.source, v, { bold: false }),
        });
      }
      TL.kinetic.push(k);
      t += sec;
      return;
    }

    // ---------------------------------------------------------- app scene
    const start = t;
    const frame = scene.frame ?? "window";
    if (frame === "bleed") {
      // The app page itself fills the frame: cover 1920x1080 and centre the page, chrome off-screen.
      // Overscan 0.5% so no edge seam shows; pin the page top to the frame top (crop the bottom, keep the header).
      fullZ = Math.max(S.width / S.appWidth, S.height / S.appHeight) * 1.005;
      fullF = [S.winX + S.appWidth / 2, S.winY + S.titlebar + S.anchorY / fullZ];
    } else { fullZ = 1; fullF = [S.anchorX, S.anchorY]; }
    TL.windowSpans.push({ enterStart: start, enterEnd: start + ENTER, exitStart: 0, exitEnd: 0, urlPath: scene.path.split("?")[0], exit: scene.exit ?? "drop", frame });
    actions.push({ t: start, kind: "navigate", path: scene.path, expect: p.initial });
    full(start, 0);
    t = start + ENTER - 0.2;

    scene.beats.forEach((b, j) => {
      const m = p.beats[j];
      const b0 = t;
      const key = `s${i}b${j}`;
      if (b.do === "wide") {
        const sec = snap(b0, fitVoice(key, "wide", b.seconds ?? LIMITS.wide.def, TAIL.beat, b0));
        full(b0, Math.min(1.4, sec * 0.4));
        lastFocus = null;
        caption(m.caption, b0 + 0.3, b0 + sec - 0.1);
        t += sec;
      } else if (b.do === "focus") {
        const sec = snap(b0, fitVoice(key, "focus", b.seconds ?? LIMITS.focus.def, TAIL.beat, b0));
        const r = padRect(toWin(m.rect));
        const z = b.zoom ? Math.max(fullZ, Math.min(b.zoom, fitZoom(r, 2.4))) : fit(r, 1.9);
        const move = Math.min(1.6, sec * 0.4);
        shot(b0, move, z, worldOf(center(r)));
        shot(b0 + move, sec - move, z * 1.04, worldOf(center(r))); // slow creep-in during the hold
        lastFocus = { z: z * 1.04, f: worldOf(center(r)) };
        TL.shots.at(-1).drift = true;
        if (m.font) legibility.push({ label: `scenes[${i}].beats[${j}] focus`, minPx: m.font.min * z, keyPx: m.font.max * z, kind: "focus", visual: m.font.visual > 0.45 });
        checks.push({ t: b0 + sec - 0.05, rect: r, label: `scenes[${i}].beats[${j}] focus target (end of hold)` });
        TL.spots.push({ start: b0 + 0.55, end: b0 + sec - 0.05, rect: r, ring: !!b.highlight });
        caption(m.caption, b0 + 0.35, b0 + sec - 0.1);
        checks.push({ t: b0 + move + 0.05, rect: r, label: `scenes[${i}].beats[${j}] focus target` });
        if (m.hover?.length) {
          const pts = m.hover.map((pt) => [pt[0], pt[1] + S.titlebar]);
          const appear = b0 + 1.3;
          TL.cursor.keys.push({ at: appear, dur: 0, p: [pts[0][0] + 160, pts[0][1] + 140] });
          TL.cursor.vis.push({ start: appear, end: b0 + sec - 0.25 });
          // Real pointer follows the drawn cursor so chart tooltips track it frame by frame.
          TL.cursor.live.push({ start: appear + 0.15, end: b0 + sec - 0.3 });
          pts.forEach((pt, n) => {
            const at = appear + 0.2 + n * 1.7;
            TL.cursor.keys.push({ at, dur: 0.8, p: pt });
            checks.push({ t: at + 0.82, rect: { x: pt[0] - 2, y: pt[1] - 2, w: 4, h: 4 }, label: `scenes[${i}].beats[${j}].hover[${n}]` });
          });
          actions.push({ t: b0 + sec - 0.2, kind: "unhover" });
        }
        t += sec;
      } else if (b.do === "select") {
        const sec = snap(b0, fitVoice(key, "select", LIMITS.select.def, TAIL.beat, b0)); // extra time = hold after the menu closes
        const ctrl = toWin(m.control);
        const items = m.options.map((o) => esc(o.label));
        const mw = Math.max(ctrl.w, 190);
        const menuRect = { x: ctrl.x, y: ctrl.y + ctrl.h + 6, w: mw, h: 12 + 34 * items.length };
        const region = padRect(union(ctrl, menuRect), 24);
        shot(b0, 1.3, fit(region, 1.9), worldOf(center(region)));
        lastFocus = { z: fit(region, 1.9), f: worldOf(center(region)) };
        checks.push({ t: b0 + 1.35, rect: region, label: `scenes[${i}].beats[${j}] select control + menu` });
        const ctrlPt = [ctrl.x + Math.min(ctrl.w * 0.35, 60), ctrl.y + ctrl.h * 0.6];
        const itemPt = [menuRect.x + 46, menuRect.y + 6 + 34 * m.targetIndex + 19];
        TL.cursor.keys.push({ at: b0 + 0.3, dur: 0, p: [ctrlPt[0] + 240, ctrlPt[1] + 250] });
        TL.cursor.keys.push({ at: b0 + 0.45, dur: 0.95, p: ctrlPt });
        TL.cursor.keys.push({ at: b0 + 1.85, dur: 0.55, p: itemPt });
        TL.cursor.vis.push({ start: b0 + 0.3, end: b0 + 3.3 });
        TL.cursor.clicks.push(b0 + 1.5, b0 + 2.55);
        TL.menus.push({ id: `menu-${i}-${j}`, open: b0 + 1.6, close: b0 + 2.65, rect: menuRect, items, current: m.currentIndex, hot: m.targetIndex, hotFrom: b0 + 2.35 });
        actions.push({ t: b0 + 2.75, kind: "select", control: b.control, value: m.targetValue, expect: m.after });
        caption(m.caption, b0 + 0.3, b0 + sec - 0.1);
        t += sec;
      } else if (b.do === "lift" || b.do === "compare") {
        // The real card (cropped from the page at 2x) rises out of the window, which falls back and blurs.
        const sec = snap(b0, fitVoice(key, b.do, b.seconds ?? LIMITS[b.do].def, TAIL.beat, b0));
        const src = toWin(m.rect);
        const sides = b.do === "lift" ? [{ img: m.img, label: null, rect: m.rect }] : m.sides;
        const n = sides.length;
        const gap = 64, labelH = sides[0].label ? 56 : 0;
        const W = Math.max(...sides.map((sd) => sd.rect.w)), H = Math.max(...sides.map((sd) => sd.rect.h));
        // Side by side for tall cards, stacked rows for wide ones: whichever shows the card bigger.
        const sRow = Math.min(2.6, (1640 - gap * (n - 1)) / n / W, (n === 1 ? 600 : 560) / H);
        const sCol = Math.min(2.6, 1500 / W, (860 - (n - 1) * 44 - n * labelH) / n / H);
        const stacked = n > 1 && sCol > sRow * 1.15;
        const s1 = stacked ? sCol : sRow;
        let items;
        if (stacked) {
          const total = n * (H * s1 + labelH) + (n - 1) * 44;
          let y = 480 - total / 2;
          items = sides.map((sd, k) => {
            const cyk = y + labelH + (H * s1) / 2;
            y += labelH + H * s1 + 44;
            return { img: sd.img, label: sd.label ? esc(sd.label) : null, w: sd.rect.w, h: sd.rect.h, to: { cx: S.width / 2, cy: cyk, s: s1 }, delay: k * 0.14 };
          });
        } else {
          const widths = sides.map((sd) => sd.rect.w * s1);
          let x = S.width / 2 - (widths.reduce((a, c) => a + c, 0) + gap * (n - 1)) / 2;
          const cy = n === 1 ? 470 : 500;
          items = sides.map((sd, k) => {
            const it = { img: sd.img, label: sd.label ? esc(sd.label) : null, w: sd.rect.w, h: sd.rect.h, to: { cx: x + widths[k] / 2, cy, s: s1 }, delay: k * 0.12 };
            x += widths[k] + gap;
            return it;
          });
        }
        for (const it of items) {
          const top = it.to.cy - (it.h * s1) / 2 - (it.label ? 56 : 0);
          const bottom = it.to.cy + (it.h * s1) / 2;
          if (top < 30 || bottom > 930) checks.push({ t: -1, abs: true, label: `scenes[${i}].beats[${j}] ${b.do} layout (top ${top | 0}, bottom ${bottom | 0})` });
        }
        full(b0, 0.9);
        lastFocus = null;
        TL.lifts.push({ id: `lift-${i}-${j}`, start: b0, end: b0 + sec, rect: src, radius: Math.max(8, m.font?.radius || 12), items });
        caption(m.caption, b0 + 0.55, b0 + sec - 0.1);
        if (m.font) legibility.push({ label: `scenes[${i}].beats[${j}] ${b.do}`, minPx: m.font.min * s1, keyPx: m.font.max * s1, kind: b.do });
        t += sec;
      } else if (b.do === "click") {
        const sec = snap(b0, fitVoice(key, "click", LIMITS.click.def, TAIL.beat, b0));
        const r = toWin(m.rect);
        const region = padRect(r, 40);
        shot(b0, 1.3, fit(region, 1.7), worldOf(center(region)));
        lastFocus = { z: fit(region, 1.7), f: worldOf(center(region)) };
        checks.push({ t: b0 + 1.35, rect: region, label: `scenes[${i}].beats[${j}] click target` });
        const pt = center(r);
        TL.cursor.keys.push({ at: b0 + 0.3, dur: 0, p: [pt[0] + 240, pt[1] + 250] });
        TL.cursor.keys.push({ at: b0 + 0.45, dur: 0.95, p: pt });
        TL.cursor.vis.push({ start: b0 + 0.3, end: b0 + 2.7 });
        TL.cursor.clicks.push(b0 + 1.5);
        actions.push({ t: b0 + 1.55, kind: "click", target: b.target, expect: m.after });
        caption(m.caption, b0 + 0.3, b0 + sec - 0.1);
        t += sec;
      }
    });

    const span = TL.windowSpans.at(-1);
    if (span.exit === "zoom") {
      // Zoom-through: the camera accelerates into the last framed point while the page dissolves.
      shot(t, EXIT, (lastFocus?.z ?? 1) * 2.6, lastFocus?.f ?? [S.anchorX, S.anchorY], "in");
      span.exitStart = t + 0.45;
      span.exitEnd = t + EXIT;
    } else full(t, 0.9);
    span.exitStart = span.exit === "zoom" ? t + 0.45 : t + 0.6;
    span.exitEnd = t + EXIT;
    // Let a following title/stat/outro fade in while the window leaves, so no empty frames.
    const next = story.scenes[i + 1];
    t += next && next.type !== "app" ? EXIT - 0.6 : EXIT;
  });

  return { TL, actions: actions.sort((a, b) => a.t - b.t), checks, cues, legibility, beatStats, duration: Math.round(t * 1000) / 1000 };
}
