// Research + variety. Every video starts from a study of real reference videos; its creative choices
// must be traceable to that study, and it must look different from the videos made before it.
// Techniques the engine cannot do yet go on a wishlist, which is how the engine grows.
import fs from "node:fs";
import path from "node:path";

// Technique vocabulary: id → [what it is, how to get it in a storyboard]. Automatic ones need no choice.
export const TECHNIQUES = {
  "warm-paper": ["Warm off-white editorial stage", '"theme": "paper"'],
  "dark-stage": ["Dark premium stage, light type", '"theme": "ink"'],
  "colour-field": ["Full-bleed brand-colour stage", '"theme": "field"'],
  "grid-stage": ["Cool technical stage with fine grid", '"theme": "grid"'],
  "mask-title": ["Title words slide up from behind a mask", 'title "reveal": "mask"'],
  "focus-title": ["Title words come into focus from blur/depth", 'title "reveal": "focus"'],
  "rise-title": ["Title words rise and un-blur", 'title "reveal": "rise"'],
  "centred-title": ["Centred title lockup", 'title "layout": "center"'],
  "editorial-title": ["Left-aligned editorial title with a rule line", 'title "layout": "left"'],
  "stacked-title": ["Giant words stacked one per line", 'title "layout": "stack"'],
  "big-number": ["One huge number, centred", 'stat "layout": "center"'],
  "split-number": ["Huge number on one side, context on the other", 'stat "layout": "split"'],
  "versus-numbers": ["Two numbers face off side by side", 'stat "layout": "versus" + value2 + labels'],
  "pull-quote": ["A sentence set large as a quote", 'scene "type": "quote"'],
  "browser-window": ["Product shown in a browser window", 'app "frame": "window"'],
  "full-bleed-ui": ["Product UI fills the whole frame", 'app "frame": "bleed"'],
  "3d-tilted-ui": ["Product UI at a 3D angle that flattens on push-in", 'app "frame": "tilt"'],
  "cold-open": ["Opens directly on the product, no title card", "first scene is an app scene"],
  "card-lift": ["One UI element lifts out of the page", 'beat "do": "lift"'],
  "side-by-side": ["Same element in two states, side by side", 'beat "do": "compare"'],
  "spotlight": ["Dims everything except one element", 'focus "highlight": true'],
  "cursor-demo": ["A cursor operates the real UI", 'beat "do": "select" / "click"'],
  "chart-hover": ["Cursor hovers a chart and tooltips appear", 'focus "hover"'],
  "camera-push": ["Camera pushes into a region of the UI", 'beat "do": "focus"'],
  "zoom-through": ["Camera accelerates through the UI into the next scene", 'app "exit": "zoom"'],
  "voiceover": ["Narration", '"say" lines + user voice'],
  "beat-sync": ["Cuts land on the music beat", "automatic with music"],
  "motion-blur": ["Real motion blur", "automatic"],
  "spring-motion": ["Springy, slightly overshooting movement", "automatic"],
  "highlight-marker": ["Highlighter drawn under key words", "automatic on **bold**"],
  "sound-design": ["UI clicks, whooshes, pops", "automatic"],
  "captions": ["On-screen captions", "automatic"],
};
const AUTOMATIC = new Set(["beat-sync", "motion-blur", "spring-motion", "highlight-marker", "sound-design", "captions"]);

// Techniques a storyboard uses (automatic ones excluded).
export function techniquesOf(story) {
  const t = new Set();
  t.add({ paper: "warm-paper", ink: "dark-stage", field: "colour-field", grid: "grid-stage" }[story.theme ?? "paper"]);
  if (story.scenes[0]?.type === "app") t.add("cold-open");
  for (const s of story.scenes) {
    if (s.type === "title") {
      t.add({ mask: "mask-title", focus: "focus-title", rise: "rise-title" }[s.reveal ?? "mask"]);
      t.add({ center: "centred-title", left: "editorial-title", stack: "stacked-title" }[s.layout ?? "center"]);
    }
    if (s.type === "stat") t.add({ center: "big-number", split: "split-number", versus: "versus-numbers" }[s.layout ?? (s.value2 ? "versus" : "center")]);
    if (s.type === "quote") t.add("pull-quote");
    if (s.type === "app") {
      t.add({ window: "browser-window", bleed: "full-bleed-ui", tilt: "3d-tilted-ui" }[s.frame ?? "window"]);
      if (s.exit === "zoom") t.add("zoom-through");
      for (const b of s.beats || []) {
        if (b.do === "lift") t.add("card-lift");
        if (b.do === "compare") t.add("side-by-side");
        if (b.do === "select" || b.do === "click") t.add("cursor-demo");
        if (b.do === "focus") { t.add("camera-push"); if (b.highlight) t.add("spotlight"); if (b.hover) t.add("chart-hover"); }
      }
    }
    if (s.say || (s.beats || []).some((b) => b.say)) t.add("voiceover");
  }
  return t;
}

// Fingerprint: the dimensions a viewer notices first.
export function fingerprint(story) {
  const by = (type) => story.scenes.filter((s) => s.type === type);
  return {
    look: story.theme ?? "paper",
    title: by("title").map((s) => `${s.layout ?? "center"}/${s.reveal ?? "mask"}`).join(",") || "none",
    stat: by("stat").map((s) => s.layout ?? (s.value2 ? "versus" : "center")).join(",") || "none",
    frame: by("app").map((s) => s.frame ?? "window").join(",") || "none",
    opening: story.scenes[0]?.type ?? "none",
    scenes: story.scenes.map((s) => s.type).join(">"),
    shots: by("app").flatMap((s) => (s.beats || []).map((b) => b.do)).join(">"),
    exit: by("app").map((s) => s.exit ?? "drop").join(","),
  };
}

// The n stories made most recently BEFORE this one (by file time), so re-checking an old story
// never compares it with videos made after it.
export function previousStories(storyFile, id, n = 3) {
  const dir = path.dirname(storyFile);
  const selfTime = fs.existsSync(storyFile) ? fs.statSync(storyFile).mtimeMs : Date.now();
  return fs.readdirSync(dir)
    .filter((f) => f.endsWith(".json"))
    .map((f) => path.join(dir, f))
    .filter((f) => path.resolve(f) !== path.resolve(storyFile))
    .map((f) => { try { return { file: f, mtime: fs.statSync(f).mtimeMs, story: JSON.parse(fs.readFileSync(f, "utf8")) }; } catch { return null; } })
    .filter((x) => x && x.story.id && x.story.id !== id && Array.isArray(x.story.scenes) && x.mtime < selfTime)
    .sort((a, b) => b.mtime - a.mtime)
    .slice(0, n);
}

// Each new video must differ from each of the last 3 in at least 4 of the 8 fingerprint dimensions,
// and at least 2 of those must be what a viewer notices first: look, title, stat, frame, opening.
const VISUAL = ["look", "title", "stat", "frame", "opening"];
export function varietyErrors(story, prev, minDiff = 4, minVisual = 2) {
  const errors = [];
  const mine = fingerprint(story);
  for (const p of prev) {
    const theirs = fingerprint(p.story);
    const same = Object.keys(mine).filter((k) => mine[k] === theirs[k]);
    const diff = Object.keys(mine).length - same.length;
    const visualDiff = VISUAL.filter((k) => mine[k] !== theirs[k]).length;
    if (diff < minDiff || visualDiff < minVisual) {
      errors.push(`Too similar to "${p.story.id}": differs in ${diff} of 8 ways (needs ${minDiff}) and ${visualDiff} visible ways (needs ${minVisual} of ${VISUAL.join("/")}). ` +
        `Same: ${same.map((k) => `${k}=${mine[k]}`).join("; ")}. Change the look, title layout, stat layout, framing or opening.`);
    }
  }
  return errors;
}

async function reachable(url) {
  const yt = /(?:youtube\.com|youtu\.be)\//i.test(url), vimeo = /vimeo\.com\//i.test(url);
  const probe = yt ? `https://www.youtube.com/oembed?format=json&url=${encodeURIComponent(url)}`
    : vimeo ? `https://vimeo.com/api/oembed.json?url=${encodeURIComponent(url)}` : url;
  try {
    const r = await fetch(probe, { method: "GET", redirect: "follow", signal: AbortSignal.timeout(12000), headers: { "user-agent": "Mozilla/5.0 (aequitas-video-research-check)" } });
    if (r.status === 401 || r.status === 403) return { ok: true, note: `HTTP ${r.status} (exists but restricted)` };
    return { ok: r.ok, note: `HTTP ${r.status}` };
  } catch (e) {
    return { ok: false, note: e.name === "TimeoutError" ? "timeout" : e.message };
  }
}

// Validates research/<id>.json. Returns { errors, warnings, wishlist, references }.
export async function validateResearch(file, story, { checkLinks = true } = {}) {
  const errors = [], warnings = [];
  if (!fs.existsSync(file)) return { errors: [`Research file not found: ${file}. Do the research step first.`], warnings, wishlist: [] };
  let r;
  try { r = JSON.parse(fs.readFileSync(file, "utf8")); } catch (e) { return { errors: [`Research file is not valid JSON: ${e.message}`], warnings, wishlist: [] }; }
  const allowed = ["story", "date", "brief", "references", "decisions", "wishlist"];
  for (const k of Object.keys(r)) if (!allowed.includes(k)) errors.push(`research: unknown key "${k}"`);
  if (r.story !== story.id) errors.push(`research.story must be "${story.id}"`);
  if (typeof r.brief !== "string" || r.brief.split(/\s+/).length < 6) errors.push("research.brief: one sentence saying what this video must make the viewer understand");
  const refs = Array.isArray(r.references) ? r.references : [];
  if (refs.length < 10) errors.push(`research.references: ${refs.length} found; study at least 10 reference videos`);
  const urls = new Set(), brands = new Set();
  const seen = new Set();
  refs.forEach((ref, i) => {
    const w = `research.references[${i}]`;
    for (const k of Object.keys(ref || {})) if (!["title", "brand", "url", "length", "observed", "techniques", "borrow"].includes(k)) errors.push(`${w}: unknown key "${k}"`);
    if (!/^https?:\/\//.test(ref?.url || "")) errors.push(`${w}.url: full https link to the video`);
    else if (urls.has(ref.url)) errors.push(`${w}.url: duplicate`);
    else urls.add(ref.url);
    if (!ref?.brand) errors.push(`${w}.brand: the company that made it`);
    else brands.add(String(ref.brand).toLowerCase().trim());
    if (!ref?.title) errors.push(`${w}.title required`);
    const obs = Array.isArray(ref?.observed) ? ref.observed : [];
    if (obs.length < 2) errors.push(`${w}.observed: at least 2 timestamped observations, e.g. "0:12 the card lifts out of the UI while the page blurs"`);
    obs.forEach((o, k) => {
      if (!/^\d{1,2}:\d{2}\s+\S/.test(String(o)) || String(o).split(/\s+/).length < 7) errors.push(`${w}.observed[${k}]: start with a timestamp (m:ss) and describe what happens in 6+ words`);
    });
    const tech = Array.isArray(ref?.techniques) ? ref.techniques : [];
    if (!tech.length) errors.push(`${w}.techniques: list technique ids from the vocabulary (render.mjs techniques)`);
    for (const t of tech) {
      if (!TECHNIQUES[t]) errors.push(`${w}.techniques: "${t}" is not in the vocabulary. Use a listed id, or put it in research.wishlist if the engine cannot do it.`);
      else seen.add(t);
    }
    if (!ref?.borrow || String(ref.borrow).split(/\s+/).length < 5) errors.push(`${w}.borrow: what you take from this video for this one (5+ words)`);
  });
  // Fresh eyes every time: at least 5 references not cited in any earlier video's research.
  const dir = path.dirname(file);
  const earlier = new Set();
  for (const f of fs.existsSync(dir) ? fs.readdirSync(dir).filter((x) => x.endsWith(".json")) : []) {
    if (path.resolve(path.join(dir, f)) === path.resolve(file)) continue;
    try { for (const ref of JSON.parse(fs.readFileSync(path.join(dir, f), "utf8")).references || []) earlier.add(ref.url); } catch { /* skip */ }
  }
  const fresh = [...urls].filter((u) => !earlier.has(u)).length;
  if (refs.length && fresh < 5) errors.push(`research.references: only ${fresh} new reference(s); at least 5 must not appear in earlier videos' research. Find new videos.`);
  if (brands.size < 4) errors.push(`research.references: only ${brands.size} brand(s); use at least 4 different companies so the style is not copied from one source`);
  const used = [...techniquesOf(story)].filter((t) => !AUTOMATIC.has(t));
  const unbacked = used.filter((t) => !seen.has(t));
  if (unbacked.length) errors.push(`Story uses techniques no reference shows: ${unbacked.join(", ")}. Either cite a reference that uses them or change the story.`);
  const d = r.decisions || {};
  if (!d.why || String(d.why).split(/\s+/).length < 12) errors.push("research.decisions.why: explain in 12+ words why these choices fit this finding");
  const wishlist = Array.isArray(r.wishlist) ? r.wishlist : [];
  wishlist.forEach((wi, i) => {
    if (!wi?.technique || !wi?.seen_in) errors.push(`research.wishlist[${i}]: {"technique": "...", "seen_in": "<reference url>", "why": "..."}`);
  });
  if (checkLinks && refs.length) {
    const results = await Promise.all(refs.map((ref) => (ref?.url ? reachable(ref.url) : Promise.resolve({ ok: false, note: "no url" }))));
    results.forEach((res, i) => {
      if (!res.ok) errors.push(`research.references[${i}].url does not resolve (${res.note}): ${refs[i]?.url}. Only cite videos you actually opened.`);
    });
  }
  return { errors, warnings, wishlist, references: refs.length, brands: brands.size };
}

export function collectWishlist(researchDir) {
  if (!fs.existsSync(researchDir)) return [];
  const items = [];
  for (const f of fs.readdirSync(researchDir).filter((x) => x.endsWith(".json"))) {
    try {
      const r = JSON.parse(fs.readFileSync(path.join(researchDir, f), "utf8"));
      for (const w of r.wishlist || []) items.push({ ...w, story: r.story });
    } catch { /* skip unreadable */ }
  }
  return items;
}
