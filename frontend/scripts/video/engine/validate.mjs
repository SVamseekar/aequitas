// Storyboard lint. Runs before any browser work. Every rule here exists because a
// weaker authoring model got it wrong at least once in principle: typos in keys,
// invented numbers, overclaiming copy, cross-country comparisons, bad timing.

export const LIMITS = {
  title: { def: 4.2, min: 3.5, max: 6 },
  stat: { def: 4.6, min: 4, max: 6.5 },
  outro: { def: 4.6, min: 3.8, max: 7 },
  quote: { def: 5, min: 4, max: 8 },
  focus: { def: 4, min: 2.8, max: 7 },
  wide: { def: 3, min: 2.4, max: 5 },
  select: { def: 3.6, min: 3.6, max: 3.6 },
  lift: { def: 3.8, min: 3, max: 7 },
  compare: { def: 4.8, min: 4, max: 7 },
  click: { def: 3, min: 3, max: 3 },
  total: { min: 15, max: 75 },
  captionChars: 86,
  sayWords: 32,
  voiceMaxSeconds: 12,
  titleChars: 48,
  subtitleChars: 110,
  statLeadChars: 90,
  statTailChars: 100,
};

const COUNTRIES = {
  england: ["england", "english"],
  ireland: ["ireland", "irish"],
  netherlands: ["netherlands", "dutch"],
  france: ["france", "french"],
};
const FOREIGN_SCOPE = ["uk", "united kingdom", "britain", "british", "europe", "european", "eu"];

// Copy that overclaims, paraphrases numbers, or implies causation. Rephrase instead.
const BANNED = [
  ["isolat*", "says more than the data: the data counts scheduled departures, not isolation"],
  ["strand*", "overclaim"], ["cut off", "overclaim"], ["lifeline", "overclaim"], ["abandon*", "overclaim"],
  ["no transport", "data covers scheduled bus/rail departures only"], ["all bus connectivity", "overclaim"],
  ["caus*", "no causal claims"], ["because", "no causal claims"], ["prove*", "no 'prove' claims"], ["due to", "no causal claims"],
  ["estimat*", "no estimates"], ["approx*", "no approximations"], ["roughly", "no approximations"], ["~", "no approximations"],
  ["half", "number words are paraphrases; bind the real value"], ["third", "number word"], ["quarter", "number word"],
  ["majority", "number word"], ["doubl*", "number word"], ["tripl*", "number word"], ["times more", "number word"],
  ["dozen", "number word"], ["hundred", "number word"], ["thousand", "number word"], ["million", "number word"], ["billion", "number word"],
  ["one in", "number word"], ["two", "number word"], ["three", "number word"], ["four", "number word"], ["five", "number word"],
  ["six", "number word"], ["seven", "number word"], ["eight", "number word"], ["nine", "number word"], ["ten", "number word"],
  ["travel time", "travel times only if the page shows them; bind the value instead of naming it in copy"],
  ["benefit-cost", "never in copy"], ["bcr", "never in copy"],
];

const TEXT_FIELDS = {
  title: ["eyebrow", "title", "subtitle"],
  stat: ["lead", "value", "value2", "tail", "source"],
  outro: ["eyebrow", "title", "subtitle", "url", "source"],
  quote: ["text", "attribution", "source"],
};
export const LOOKS = {
  theme: ["paper", "ink", "field", "grid"],
  titleLayout: ["center", "left", "stack"],
  statLayout: ["center", "split", "versus"],
  frame: ["window", "bleed", "tilt"],
  reveal: ["mask", "focus", "rise"],
  exit: ["drop", "zoom"],
};
const SCENE_KEYS = {
  title: ["type", "eyebrow", "title", "subtitle", "say", "reveal", "layout", "seconds"],
  stat: ["type", "layout", "lead", "value", "value2", "labels", "tail", "source", "say", "seconds"],
  quote: ["type", "text", "attribution", "source", "say", "seconds"],
  outro: ["type", "eyebrow", "title", "subtitle", "url", "source", "say", "seconds"],
  app: ["type", "path", "frame", "beats", "exit"],
};
const BEAT_KEYS = {
  focus: ["do", "target", "caption", "highlight", "zoom", "hover", "say", "seconds"],
  wide: ["do", "caption", "say", "seconds"],
  select: ["do", "control", "option", "caption", "say"],
  click: ["do", "target", "caption", "say"],
  lift: ["do", "target", "caption", "say", "seconds"],
  compare: ["do", "target", "control", "options", "labels", "caption", "say", "seconds"],
};
const BIND_KEYS = ["from", "line", "pick", "nth", "when"];
const PICKS = ["percent", "count", "number", "text"];

const PLACEHOLDER = /\{\{\s*([a-zA-Z][\w]*)\s*\}\}/g;

export function placeholders(text) {
  return [...String(text ?? "").matchAll(PLACEHOLDER)].map((m) => m[1]);
}

function checkLocator(loc, where, errors, { allowControl = false } = {}) {
  if (typeof loc === "string") {
    if (!loc.trim()) errors.push(`${where}: empty selector`);
    return;
  }
  if (!loc || typeof loc !== "object") return errors.push(`${where}: target must be a CSS string or {"card": "Heading"}`);
  const keys = Object.keys(loc);
  const ok = ["card", "cards", "text"].concat(allowControl ? ["control"] : []);
  if (keys.length !== 1 || !ok.includes(keys[0])) return errors.push(`${where}: target object must have exactly one of ${ok.join(", ")}`);
  if (keys[0] === "cards" && (!Array.isArray(loc.cards) || loc.cards.length < 2)) errors.push(`${where}: "cards" needs 2+ headings`);
}

function checkCopy(text, where, country, errors, { allowDigits = false } = {}) {
  if (text == null) return;
  if (typeof text !== "string") return errors.push(`${where}: must be a string`);
  const bare = text.replace(PLACEHOLDER, " ");
  if (!allowDigits && /\d/.test(bare)) {
    errors.push(`${where}: typed digit in "${text}". Every number must come from a bind: use {{name}}.`);
  }
  if (/[{}]/.test(bare)) errors.push(`${where}: stray brace in "${text}" (placeholders are {{name}})`);
  if (/<|>/.test(bare)) errors.push(`${where}: no HTML; use **bold** in captions and *italic* in titles`);
  const hedge = /\b(about|around|nearly|almost|over|under|more than|less than|fewer than|up to|some|at least)\s+\*{0,2}\{\{/i.exec(text);
  if (hedge) errors.push(`${where}: "${hedge[1]}" before a number changes its meaning. State the bound value exactly.`);
  const low = ` ${bare.toLowerCase().replace(/[^a-z~\- ]/g, " ")} `;
  for (const [word, why] of BANNED) {
    const stem = word.endsWith("*");
    const w = word.replace("*", "").replace(/[-]/g, "\\-");
    const re = word === "~" ? /~/ : new RegExp(`(^|[^a-z])${w}${stem ? "" : "([^a-z]|$)"}`);
    if (re.test(low)) errors.push(`${where}: banned phrase "${word}" (${why}) in "${text}"`);
  }
  for (const [c, words] of Object.entries(COUNTRIES)) {
    if (c === country) continue;
    for (const w of words) if (new RegExp(`(^|[^a-z])${w}([^a-z]|$)`).test(low)) errors.push(`${where}: mentions ${w} but story country is ${country}. Scores are in-country only.`);
  }
  for (const w of FOREIGN_SCOPE) if (new RegExp(`(^|[^a-z])${w}([^a-z]|$)`).test(low)) errors.push(`${where}: "${w}" is outside story scope (${country})`);
}

function seconds(obj, kind, where, errors) {
  const L = LIMITS[kind];
  if (obj.seconds == null) return L.def;
  if (typeof obj.seconds !== "number" || obj.seconds < L.min || obj.seconds > L.max) {
    errors.push(`${where}: seconds must be ${L.min}–${L.max} (got ${obj.seconds})`);
    return L.def;
  }
  return obj.seconds;
}

export function validateStory(story) {
  const errors = [];
  const warnings = [];
  const allowedTop = ["$schema", "id", "output", "binds", "scenes", "audio", "sfx", "theme", "research"];
  if (story.research != null && !/^research\/[a-z0-9]+(-[a-z0-9]+)*\.json$/.test(story.research)) errors.push('research must look like "research/<id>.json"');
  if (story.theme != null && !LOOKS.theme.includes(story.theme)) errors.push(`theme must be one of ${LOOKS.theme.join(", ")}`);
  if (story.sfx != null && typeof story.sfx !== "boolean") errors.push("sfx must be true or false");
  for (const k of Object.keys(story)) if (!allowedTop.includes(k)) errors.push(`Unknown top-level key "${k}"`);
  if (!/^[a-z0-9]+(-[a-z0-9]+)*$/.test(story.id || "")) errors.push(`id must be kebab-case (got ${JSON.stringify(story.id)})`);
  if (story.output != null && !/^media\/[a-z0-9-]+\.mp4$/.test(story.output)) errors.push(`output must look like media/<kebab-name>.mp4`);
  if (!Array.isArray(story.scenes) || !story.scenes.length) {
    errors.push("scenes must be a non-empty array");
    return { errors, warnings, country: null };
  }

  const appScenes = story.scenes.filter((s) => s.type === "app");
  if (!appScenes.length) errors.push("At least one app scene is required (numbers are read from the live app)");
  const countries = new Set();
  for (const s of appScenes) {
    const m = /^\/app\/([a-z]+)(?:[/?]|$)/.exec(s.path || "");
    if (!m) errors.push(`app path must start with /app/<country> (got ${JSON.stringify(s.path)})`);
    else if (!COUNTRIES[m[1]]) errors.push(`Unknown country "${m[1]}" in path ${s.path}`);
    else countries.add(m[1]);
  }
  if (countries.size > 1) errors.push(`One country per video. Found: ${[...countries].join(", ")}. Scores are in-country only.`);
  const country = [...countries][0] || null;

  const binds = story.binds || {};
  if (typeof binds !== "object" || Array.isArray(binds)) errors.push("binds must be an object");
  for (const [name, b] of Object.entries(binds)) {
    const w = `binds.${name}`;
    if (!/^[a-zA-Z]\w*$/.test(name)) errors.push(`${w}: name must be letters/digits/underscore`);
    for (const k of Object.keys(b || {})) if (!BIND_KEYS.includes(k)) errors.push(`${w}: unknown key "${k}" (allowed: ${BIND_KEYS.join(", ")})`);
    checkLocator(b?.from, `${w}.from`, errors);
    if (!PICKS.includes(b?.pick)) errors.push(`${w}: pick must be one of ${PICKS.join(", ")}`);
    if (b?.line != null && !(Number.isInteger(b.line) && b.line >= 1)) errors.push(`${w}: line must be a positive integer`);
    if (b?.nth != null && !(Number.isInteger(b.nth) && b.nth >= 1)) errors.push(`${w}: nth must be a positive integer`);
    if (b?.when != null) {
      const ok = b.when && typeof b.when === "object" && Object.keys(b.when).sort().join() === "control,option" && typeof b.when.control === "string" && typeof b.when.option === "string";
      if (!ok) errors.push(`${w}.when: {"control": "Area", "option": "Rural"} — reads the number with that filter applied`);
    }
  }
  const used = new Set();
  const useText = (text, where) => {
    for (const p of placeholders(text)) {
      used.add(p);
      if (!binds[p]) errors.push(`${where}: {{${p}}} has no entry in binds`);
    }
  };

  let sayCount = 0;
  const checkSay = (text, where) => {
    sayCount++;
    checkCopy(text, where, country, errors);
    useText(text, where);
    if (typeof text === "string") {
      if (/\*/.test(text)) errors.push(`${where}: no markdown in narration`);
      const words = text.replace(/\{\{[^}]+\}\}/g, "N").split(/\s+/).filter(Boolean).length;
      if (words > LIMITS.sayWords) errors.push(`${where}: ${words} words; max ${LIMITS.sayWords} per line. Split it across beats.`);
      if (words < 2) errors.push(`${where}: narration line too short`);
    }
  };

  let total = 0;
  story.scenes.forEach((s, i) => {
    const w = `scenes[${i}]`;
    if (!SCENE_KEYS[s.type]) return errors.push(`${w}: type must be title|stat|quote|app|outro (got ${JSON.stringify(s.type)})`);
    for (const k of Object.keys(s)) if (!SCENE_KEYS[s.type].includes(k)) errors.push(`${w}: unknown key "${k}" for type ${s.type}`);
    if (s.type !== "app") {
      total += seconds(s, s.type, w, errors);
      for (const f of TEXT_FIELDS[s.type]) {
        checkCopy(s[f], `${w}.${f}`, country, errors, { allowDigits: f === "url" });
        useText(s[f], `${w}.${f}`);
      }
    }
    if (s.type !== "app" && s.say != null) checkSay(s.say, `${w}.say`);
    if (s.type === "title" && s.reveal != null && !LOOKS.reveal.includes(s.reveal)) errors.push(`${w}.reveal: ${LOOKS.reveal.join(" | ")}`);
    if (s.type === "title" && s.layout != null && !LOOKS.titleLayout.includes(s.layout)) errors.push(`${w}.layout: ${LOOKS.titleLayout.join(" | ")}`);
    if (s.type === "title" && s.layout === "stack" && String(s.title || "").trim().split(/\s+/).length > 4) errors.push(`${w}: "stack" layout puts each word on its own line; use 4 words or fewer`);
    if (s.type === "app" && s.frame != null && !LOOKS.frame.includes(s.frame)) errors.push(`${w}.frame: ${LOOKS.frame.join(" | ")}`);
    if (s.type === "quote") {
      const ph = placeholders(s.text);
      if (!s.text || !/^\{\{\s*[a-zA-Z]\w*\s*\}\}$/.test(String(s.text).trim())) errors.push(`${w}.text: exactly one placeholder, e.g. "{{keyPoint}}" — the quote is a real sentence read from the page`);
      else if (binds[ph[0]] && binds[ph[0]].pick !== "text") errors.push(`${w}.text: bind {{${ph[0]}}} must use "pick": "text" (a whole line from the page)`);
    }
    if (s.type === "app" && s.exit != null && !["drop", "zoom"].includes(s.exit)) errors.push(`${w}.exit: drop | zoom`);
    if (s.type === "title") {
      if (!s.title) errors.push(`${w}: title required`);
      if (s.title && s.title.replace(/\*/g, "").length > LIMITS.titleChars) errors.push(`${w}.title: max ${LIMITS.titleChars} chars`);
      if (s.subtitle && s.subtitle.length > LIMITS.subtitleChars) errors.push(`${w}.subtitle: max ${LIMITS.subtitleChars} chars`);
      if (placeholders(s.title).length) errors.push(`${w}.title: keep numbers out of the title; put them in a stat scene`);
      if (!s.eyebrow) warnings.push(`${w}: eyebrow recommended (e.g. "England · Sunday service")`);
    }
    if (s.type === "stat") {
      if (!s.lead || !s.value) errors.push(`${w}: lead and value required`);
      if (s.value && !/^\{\{\s*[a-zA-Z]\w*\s*\}\}$/.test(s.value.trim())) errors.push(`${w}.value: must be exactly one placeholder like "{{reduction}}"`);
      const layout = s.layout ?? (s.value2 ? "versus" : "center");
      if (!LOOKS.statLayout.includes(layout)) errors.push(`${w}.layout: ${LOOKS.statLayout.join(" | ")}`);
      if (layout === "versus") {
        if (!s.value2 || !/^\{\{\s*[a-zA-Z]\w*\s*\}\}$/.test(String(s.value2).trim())) errors.push(`${w}.value2: versus needs a second single placeholder, e.g. "{{ruralShare}}"`);
        if (!Array.isArray(s.labels) || s.labels.length !== 2) errors.push(`${w}.labels: versus needs two labels, e.g. ["All England", "Rural areas"]`);
        else s.labels.forEach((l, k) => checkCopy(l, `${w}.labels[${k}]`, country, errors));
      } else if (s.value2 || s.labels) errors.push(`${w}: value2/labels are only for "layout": "versus"`);
      if (s.lead && s.lead.length > LIMITS.statLeadChars) errors.push(`${w}.lead: max ${LIMITS.statLeadChars} chars`);
      if (s.tail && s.tail.length > LIMITS.statTailChars) errors.push(`${w}.tail: max ${LIMITS.statTailChars} chars`);
    }
    if (s.type === "app") {
      total += 1.8 + 1.6;
      if (!Array.isArray(s.beats) || !s.beats.length) return errors.push(`${w}: beats must be a non-empty array`);
      s.beats.forEach((b, j) => {
        const bw = `${w}.beats[${j}]`;
        if (!BEAT_KEYS[b.do]) return errors.push(`${bw}: do must be focus|lift|compare|wide|select|click (got ${JSON.stringify(b.do)}). enter/exit are automatic.`);
        for (const k of Object.keys(b)) if (!BEAT_KEYS[b.do].includes(k)) errors.push(`${bw}: unknown key "${k}" for ${b.do}`);
        if (b.caption != null) {
          checkCopy(b.caption, `${bw}.caption`, country, errors);
          useText(b.caption, `${bw}.caption`);
          if (/\*[^*]/.test(b.caption.replace(/\*\*[^*]+\*\*/g, ""))) errors.push(`${bw}.caption: only **bold** is supported in captions`);
        } else warnings.push(`${bw}: no caption — every beat should say what the viewer is looking at`);
        if (b.say != null) checkSay(b.say, `${bw}.say`);
        let sec = LIMITS[b.do].def;
        if (["focus", "wide", "lift", "compare"].includes(b.do)) sec = seconds(b, b.do, bw, errors);
        if (b.do === "lift") checkLocator(b.target, `${bw}.target`, errors);
        if (b.do === "compare") {
          checkLocator(b.target, `${bw}.target`, errors);
          if (typeof b.control !== "string" || !b.control) errors.push(`${bw}.control: the dropdown whose options are compared, e.g. "Area"`);
          if (!Array.isArray(b.options) || b.options.length < 2 || b.options.length > 3) errors.push(`${bw}.options: 2–3 option labels, e.g. ["All Areas", "Rural"]`);
          if (b.labels != null) {
            if (!Array.isArray(b.labels) || b.labels.length !== (b.options || []).length) errors.push(`${bw}.labels: one label per option`);
            else b.labels.forEach((l, k) => checkCopy(l, `${bw}.labels[${k}]`, country, errors));
          }
          for (const f of ["caption", "say"]) {
            if (placeholders(b[f]).length) errors.push(`${bw}.${f}: no {{binds}} in a compare beat — each side shows its own number on screen`);
          }
        }
        if (b.do === "focus") {
          checkLocator(b.target, `${bw}.target`, errors);
          if (b.zoom != null && !(typeof b.zoom === "number" && b.zoom >= 1 && b.zoom <= 2.4)) errors.push(`${bw}.zoom: 1–2.4`);
          if (b.highlight != null && typeof b.highlight !== "boolean") errors.push(`${bw}.highlight: true/false`);
          if (b.hover != null) {
            if (!Array.isArray(b.hover) || b.hover.length < 1 || b.hover.length > 3) errors.push(`${bw}.hover: array of 1–3 targets`);
            else {
              b.hover.forEach((h, k) => {
                if (h !== "bar:tallest" && h !== "bar:shortest") checkLocator(h, `${bw}.hover[${k}]`, errors);
              });
              const need = 2.6 + 1.7 * b.hover.length;
              if (sec < need) errors.push(`${bw}: ${b.hover.length} hover target(s) need seconds >= ${need.toFixed(1)}`);
            }
          }
        }
        if (b.do === "select") {
          if (typeof b.control !== "string" || !b.control) errors.push(`${bw}.control: the dropdown's label, e.g. "Area"`);
          if (typeof b.option !== "string" || !b.option) errors.push(`${bw}.option: option label or value, e.g. "Rural"`);
        }
        if (b.do === "click") checkLocator(b.target, `${bw}.target`, errors);
        total += sec;
      });
    }
  });

  if (story.audio != null) {
    const a = story.audio;
    if (typeof a !== "object" || Array.isArray(a)) errors.push("audio must be an object");
    else {
      for (const k of Object.keys(a)) if (!["music", "voice"].includes(k)) errors.push(`audio: unknown key "${k}" (allowed: music, voice)`);
      for (const k of ["music", "voice"]) {
        const v = a[k];
        if (v == null) errors.push(`audio.${k} missing. Ask the user for the file, or write "none" only if the user said none.`);
        else if (typeof v !== "string" || !(v === "none" || /^media\/audio\/[\w.\/-]+$/.test(v))) {
          errors.push(`audio.${k} must be "none" or a path under media/audio/ (got ${JSON.stringify(v)}). Copy the user's file into media/audio/ first.`);
        }
      }
      if (a.voice && a.voice !== "none" && sayCount === 0) errors.push(`audio.voice is set but no scene or beat has a "say" line`);
      if (a.voice === "none" && sayCount > 0) warnings.push(`audio.voice is "none": the ${sayCount} "say" line(s) will not be heard`);
    }
  }
  for (const name of Object.keys(binds)) if (!used.has(name)) warnings.push(`binds.${name} is never used`);
  if (story.scenes.at(-1)?.type !== "outro") warnings.push("Last scene should be an outro (brand lockup + URL)");
  // Anti-formula: a video made only of zooms reads as a screen recording, not a film.
  const beatKinds = story.scenes.filter((s) => s.type === "app").flatMap((s) => (s.beats || []).map((b) => b.do));
  const distinct = new Set(beatKinds);
  if (beatKinds.length >= 3 && distinct.size < 2) errors.push(`All beats are "${beatKinds[0]}". Use at least two beat types (lift, compare, focus, select, click, wide).`);
  if (beatKinds.length && !distinct.has("lift") && !distinct.has("compare")) warnings.push("No lift or compare beat: the key number never leaves the page. Lift it or compare it.");
  for (let k = 2; k < beatKinds.length; k++) {
    if (beatKinds[k] === beatKinds[k - 1] && beatKinds[k] === beatKinds[k - 2]) errors.push(`Three "${beatKinds[k]}" beats in a row; vary the shots.`);
  }
  if (total < LIMITS.total.min || total > LIMITS.total.max) errors.push(`Total length ${total.toFixed(1)}s outside ${LIMITS.total.min}–${LIMITS.total.max}s`);
  return { errors, warnings, country, total, sayCount };
}
