#!/usr/bin/env node
// Aequitas feature-video renderer.
//
//   node scripts/video/render.mjs inspect "/app/england/service?view=b3_weekend_penalty"
//   node scripts/video/render.mjs check   scripts/video/stories/<id>.json
//   node scripts/video/render.mjs script  scripts/video/stories/<id>.json   (voiceover script + what to ask the user)
//   node scripts/video/render.mjs render  scripts/video/stories/<id>.json [--draft] [--4k]
//
// Music and voice are always supplied by the user (story "audio" block). The final render refuses
// to run until both have been answered (a file under media/audio/, or "none" if the user said none).
//
// Run from frontend/. Needs the dev app (npm run dev, :5173) and the API (:8000) running.
// Every command ends with a line "RESULT: PASS" or "RESULT: FAIL" and a matching exit code.
import { chromium } from "playwright";
import fs from "node:fs";
import path from "node:path";
import { spawn, spawnSync, execFileSync } from "node:child_process";
import { once } from "node:events";
import { fileURLToPath } from "node:url";
import { buildStageHtml, STAGE } from "./engine/stage.mjs";
import { validateStory, placeholders } from "./engine/validate.mjs";
import { compile, richText, plainText } from "./engine/timeline.mjs";
import { TECHNIQUES, techniquesOf, fingerprint, previousStories, varietyErrors, validateResearch, collectWishlist } from "./engine/research.mjs";
import { sayUnits, analyzeVoice, probeAudio, writeScript, writeSrt, mixAudio, detectBeats, sfxEvents, loudness } from "./engine/audio.mjs";

const here = path.dirname(fileURLToPath(import.meta.url));
const FRONTEND = path.resolve(here, "../..");
const REPO = path.resolve(FRONTEND, "..");
const APP = (process.env.AEQUITAS_APP_URL || "http://127.0.0.1:5173").replace(/\/$/, "");
const HELPERS = fs.readFileSync(path.join(here, "engine/page-helpers.js"), "utf8");
const RUNTIME = fs.readFileSync(path.join(here, "engine/runtime.js"), "utf8");
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

// ------------------------------------------------------------------ cli
const [cmd, target, ...rest] = process.argv.slice(2);
const flag = (name) => rest.includes(name);
const opt = (name) => { const i = rest.indexOf(name); return i >= 0 ? rest[i + 1] : null; };

class Fail extends Error {}
const errors = [];
const warnings = [];
const log = (...a) => console.log(...a);

function finish(extra = "") {
  for (const w of warnings) log(`WARN  ${w}`);
  for (const e of errors) log(`ERROR ${e}`);
  if (extra) log(extra);
  log(errors.length ? `RESULT: FAIL (${errors.length} error${errors.length > 1 ? "s" : ""})` : "RESULT: PASS");
  process.exit(errors.length ? 1 : 0);
}

function need(bin) {
  try { execFileSync(bin, ["-version"], { stdio: "ignore" }); } catch { throw new Fail(`${bin} not found on PATH`); }
}

async function ping() {
  try {
    const r = await fetch(APP + "/", { signal: AbortSignal.timeout(5000) });
    if (!r.ok) throw new Error(String(r.status));
  } catch (e) {
    throw new Fail(`App not reachable at ${APP} (${e.message}). Start it: cd frontend && npm run dev (and the API on :8000).`);
  }
}

// ------------------------------------------------------------------ app helpers
async function settle(frame, minMs = 1800) {
  const t0 = Date.now();
  let last = null, stable = 0;
  for (;;) {
    await sleep(250);
    const sig = await frame.evaluate(() => window.__vq && window.__vq.signature());
    if (sig && sig === last) stable++; else { stable = 0; last = sig; }
    if (stable >= 4 && Date.now() - t0 >= minMs) return;
    if (Date.now() - t0 > 30000) throw new Fail("App did not settle within 30s (still loading or animating)");
  }
}

// Binds with "when" are read once, under that filter, and are the same everywhere in the story.
const FIXED = { values: {}, sources: {} };
async function snapshot(frame, binds) {
  const values = { ...FIXED.values }, sources = { ...FIXED.sources }, problems = {};
  for (const [name, spec] of Object.entries(binds)) {
    if (spec.when) continue;
    const r = await frame.evaluate((s) => window.__vq.bind(s), spec);
    if (r.error) problems[name] = r.error; else { values[name] = r.value; sources[name] = r.context; }
  }
  return { values, sources, problems };
}

function resolveOrFail(text, snap, where) {
  for (const p of placeholders(text)) {
    if (snap.values[p] == null) errors.push(`${where}: {{${p}}} could not be read here: ${snap.problems[p] || "unknown"}`);
  }
}

async function newAppPage(browser, dpr = 1) {
  const context = await browser.newContext({ viewport: { width: STAGE.appWidth, height: STAGE.appHeight }, deviceScaleFactor: dpr });
  await context.addInitScript({ content: HELPERS });
  return { context, page: await context.newPage() };
}

async function gotoApp(page, p) {
  await page.goto(APP + p, { waitUntil: "networkidle", timeout: 60000 });
  if (!page.url().includes(p.split("?")[0])) throw new Fail(`Navigating to ${p} landed on ${page.url()} (auth redirect or bad route?)`);
  await settle(page);
}

// ------------------------------------------------------------------ inspect
async function inspect(p) {
  if (!p || !p.startsWith("/app/")) throw new Fail('Usage: inspect "/app/<country>/<page>?<query>"');
  await ping();
  const browser = await chromium.launch({ channel: "chrome", args: ["--window-size=1920,1080", "--force-color-profile=srgb", "--hide-scrollbars"] });
  try {
    const { page } = await newAppPage(browser, 1);
    await gotoApp(page, p);
    const map = await page.evaluate(() => window.__vq.inspect());
    const dir = path.join(REPO, "media/.preview/inspect");
    fs.mkdirSync(dir, { recursive: true });
    const shotPath = path.join(dir, p.replace(/^\/app\//, "").replace(/[^a-z0-9]+/gi, "_") + ".png");
    await page.screenshot({ path: shotPath });
    log(JSON.stringify(map, null, 2));
    log(`\nScreenshot: ${shotPath}`);
    log("Use: cards[].card as {\"card\": \"...\"} targets/bind sources; numericLines[].line as bind line; controls[].control + an option label for select beats; clickables[].text for click beats.");
  } finally {
    await browser.close();
  }
}

// ------------------------------------------------------------------ prepass
async function prepass(browser, story) {
  const binds = story.binds || {};
  const { page, context } = await newAppPage(browser, 4); // 4x so cards lifted up to 2.6x stay sharp at 1080p
  const prep = { scenes: [], report: [], say: {} };
  const crop = async (r) => {
    const buf = await page.screenshot({ clip: { x: r.x, y: r.y, width: r.w, height: r.h }, type: "png" });
    return `data:image/png;base64,${buf.toString("base64")}`;
  };
  const firstApp = story.scenes.findIndex((s) => s.type === "app");
  const whenBinds = Object.entries(binds).filter(([, b]) => b.when);
  if (whenBinds.length) {
    const side = await newAppPage(browser, 1);
    for (const [name, b] of whenBinds) {
      await gotoApp(side.page, story.scenes[firstApp].path);
      const loc = { control: b.when.control };
      const o = await side.page.evaluate((l) => window.__vq.options(l), loc);
      if (o.error) { errors.push(`binds.${name}.when: no dropdown labelled "${b.when.control}"`); continue; }
      const want = b.when.option.toLowerCase();
      const opt = o.options.find((x) => x.label.toLowerCase() === want || x.value.toLowerCase() === want);
      if (!opt) { errors.push(`binds.${name}.when.option "${b.when.option}" not in [${o.options.map((x) => x.label).join(", ")}]`); continue; }
      await side.page.evaluate(([l, v]) => window.__vq.select(l, v), [loc, opt.value]);
      await settle(side.page);
      const r = await side.page.evaluate((sp) => window.__vq.bind(sp), { ...b, when: undefined });
      if (r.error) { errors.push(`binds.${name} (when ${b.when.control} = ${b.when.option}): ${r.error}`); continue; }
      FIXED.values[name] = r.value;
      FIXED.sources[name] = `[${b.when.control} = ${opt.label}] ${r.context}`;
    }
    await side.context.close();
  }
  await gotoApp(page, story.scenes[firstApp].path);
  let snap = await snapshot(page, binds);
  let loadedFirst = true;
  const noteBinds = (where, text) => {
    for (const p of placeholders(text)) if (snap.values[p] != null) prep.report.push(`${where}: {{${p}}} = "${snap.values[p]}"  ← "${snap.sources[p]}"`);
  };

  for (const [i, scene] of story.scenes.entries()) {
    const w = `scenes[${i}]`;
    if (scene.type !== "app") {
      for (const f of ["eyebrow", "title", "subtitle", "lead", "value", "value2", "tail", "source", "url", "text", "attribution", "say"]) {
        if (scene[f] == null) continue;
        resolveOrFail(scene[f], snap, `${w}.${f}`);
        noteBinds(`${w}.${f}`, scene[f]);
      }
      if (scene.type === "stat" && snap.values[placeholders(scene.value)[0]] && !/\d/.test(snap.values[placeholders(scene.value)[0]])) {
        errors.push(`${w}.value resolved to "${snap.values[placeholders(scene.value)[0]]}", which has no number`);
      }
      if (scene.say) prep.say[`s${i}`] = plainText(scene.say, snap.values);
      prep.scenes.push({ values: { ...snap.values } });
      continue;
    }
    if (!(i === firstApp && loadedFirst)) {
      await gotoApp(page, scene.path);
      snap = await snapshot(page, binds);
    }
    loadedFirst = false;
    const sp = { initial: { ...snap.values }, beats: [] };
    for (const [j, b] of scene.beats.entries()) {
      const bw = `${w}.beats[${j}]`;
      const m = {};
      if (b.caption) {
        resolveOrFail(b.caption, snap, `${bw}.caption`);
        noteBinds(`${bw}.caption`, b.caption);
        try { m.caption = richText(b.caption, snap.values); } catch { m.caption = null; }
      }
      if (b.say) {
        resolveOrFail(b.say, snap, `${bw}.say`);
        noteBinds(`${bw}.say`, b.say);
        prep.say[`s${i}b${j}`] = plainText(b.say, snap.values);
      }
      const inView = (r, label) => {
        if (r.y < 0 || r.x < 0 || r.y + r.h > STAGE.appHeight + 1 || r.x + r.w > STAGE.appWidth + 1) {
          errors.push(`${bw}: ${label} is outside the visible page (x=${r.x|0}, y=${r.y|0}, w=${r.w|0}, h=${r.h|0}; page is ${STAGE.appWidth}x${STAGE.appHeight}). Pick a target above the fold.`);
        }
      };
      if (b.do === "focus" || b.do === "lift" || b.do === "compare") {
        const r = await page.evaluate((l) => window.__vq.rect(l), b.target);
        if (r.error) errors.push(`${bw}.target: ${r.error}. Run inspect to list cards.`);
        else {
          m.rect = r.rect; inView(r.rect, `${b.do} target`);
          m.font = await page.evaluate((l) => window.__vq.metrics(l), b.target);
          if (b.do === "lift") m.img = await crop(r.rect);
        }
      }
      if (b.do === "compare" && m.rect) {
        const loc = { control: b.control };
        const o = await page.evaluate((l) => window.__vq.options(l), loc);
        if (o.error) errors.push(`${bw}: no dropdown labelled "${b.control}"`);
        else {
          const original = o.options[o.selected].value;
          const before = { ...snap.values };
          m.sides = [];
          for (const [k, want] of b.options.entries()) {
            const idx = o.options.findIndex((x) => x.label.toLowerCase() === want.toLowerCase() || x.value.toLowerCase() === want.toLowerCase());
            if (idx < 0) { errors.push(`${bw}.options[${k}] "${want}" not in [${o.options.map((x) => x.label).join(", ")}]`); continue; }
            await page.evaluate(([l, v]) => window.__vq.select(l, v), [loc, o.options[idx].value]);
            await settle(page);
            const rr = await page.evaluate((l) => window.__vq.rect(l), b.target);
            if (rr.error) { errors.push(`${bw}: target missing when ${b.control} = ${want}`); continue; }
            const label = b.labels ? b.labels[k] : o.options[idx].label;
            const sideSnap = await snapshot(page, binds);
            for (const [name, v] of Object.entries(sideSnap.values)) prep.report.push(`${bw} compare "${label}": {{${name}}} would read "${v}"`);
            m.sides.push({ label, img: await crop(rr.rect), rect: rr.rect });
          }
          await page.evaluate(([l, v]) => window.__vq.select(l, v), [loc, original]);
          await settle(page);
          snap = await snapshot(page, binds);
          for (const [k, v] of Object.entries(before)) {
            if (snap.values[k] !== v) errors.push(`${bw}: page did not return to its previous state after compare ({{${k}}} ${v} → ${snap.values[k]})`);
          }
        }
      }
      if (b.do === "focus" && m.rect) {
        if (b.hover && m.rect) {
          m.hover = [];
          for (const [k, h] of b.hover.entries()) {
            const hp = await page.evaluate(([tok, region]) => window.__vq.hoverPoint(tok, region), [h, b.target]);
            if (hp.error) errors.push(`${bw}.hover[${k}]: ${hp.error}`);
            else m.hover.push(hp.point);
          }
        }
      } else if (b.do === "select") {
        const loc = { control: b.control };
        const r = await page.evaluate((l) => window.__vq.rect(l), loc);
        const o = await page.evaluate((l) => window.__vq.options(l), loc);
        if (r.error || o.error) { errors.push(`${bw}: no dropdown labelled "${b.control}". Run inspect to list controls.`); sp.beats.push(m); continue; }
        m.control = r.rect; inView(r.rect, "dropdown");
        m.options = o.options; m.currentIndex = o.selected;
        const want = b.option.trim().toLowerCase();
        m.targetIndex = o.options.findIndex((x) => x.value.toLowerCase() === want || x.label.toLowerCase() === want);
        if (m.targetIndex < 0) { errors.push(`${bw}.option "${b.option}" not in [${o.options.map((x) => x.label).join(", ")}]`); sp.beats.push(m); continue; }
        if (m.targetIndex === m.currentIndex) errors.push(`${bw}.option "${b.option}" is already selected`);
        m.targetValue = o.options[m.targetIndex].value;
        const res = await page.evaluate(([l, v]) => window.__vq.select(l, v), [loc, m.targetValue]);
        await settle(page);
        const now = await page.evaluate((l) => window.__vq.options(l), loc);
        if (res.error || now.selected !== m.targetIndex) errors.push(`${bw}: selecting "${b.option}" did not take effect`);
        snap = await snapshot(page, binds);
        m.after = { ...snap.values };
      } else if (b.do === "click") {
        const r = await page.evaluate((l) => window.__vq.rect(l), b.target);
        if (r.error) { errors.push(`${bw}.target: ${r.error}`); sp.beats.push(m); continue; }
        m.rect = r.rect; inView(r.rect, "click target");
        const before = await page.evaluate(() => window.__vq.signature());
        await page.evaluate((l) => window.__vq.click(l), b.target);
        await settle(page);
        if ((await page.evaluate(() => window.__vq.signature())) === before) warnings.push(`${bw}: click changed nothing visible`);
        if (!page.url().startsWith(APP + "/app/")) errors.push(`${bw}: click navigated away to ${page.url()}`);
        snap = await snapshot(page, binds);
        m.after = { ...snap.values };
      }
      sp.beats.push(m);
    }
    prep.scenes.push(sp);
  }
  await context.close();
  return prep;
}

// ------------------------------------------------------------------ stage
async function openStage(browser, compiled, dpr, theme = "paper") {
  const context = await browser.newContext({ viewport: { width: STAGE.width, height: STAGE.height }, deviceScaleFactor: dpr });
  await context.addInitScript({ content: HELPERS });
  const page = await context.newPage();
  const stageUrl = `${APP}/__aequitas_video_stage__`;
  await page.route(stageUrl, (r) => r.fulfill({ status: 200, contentType: "text/html", body: buildStageHtml({ frontendDir: FRONTEND, appOrigin: APP, theme }) }));
  await page.goto(stageUrl, { waitUntil: "load" });
  await page.evaluate(async (tl) => { window.__TL = tl; await document.fonts.ready; }, compiled.TL);
  await page.addScriptTag({ content: RUNTIME });
  const fontsOk = await page.evaluate(async () => {
    await document.fonts.ready;
    return ["Geist", "Instrument Serif"].every((f) => document.fonts.check(`40px "${f}"`));
  });
  if (!fontsOk) throw new Fail("Brand fonts failed to load in the stage");
  const frame = () => page.mainFrame().childFrames()[0];
  return { context, page, frame };
}

function makeActionRunner(page, frame, story) {
  const binds = story.binds || {};
  const verify = async (expect, label) => {
    if (!expect) return;
    const snap = await snapshot(frame(), binds);
    for (const [k, v] of Object.entries(expect)) {
      if (snap.values[k] !== v) throw new Fail(`${label}: {{${k}}} was "${v}" during check but "${snap.values[k]}" during render. Data changed or page not ready; re-run.`);
    }
  };
  return async (a) => {
    if (a.kind === "navigate") {
      await page.evaluate((src) => { document.getElementById("app").src = src; }, APP + a.path);
      await page.waitForFunction((p) => {
        const f = document.getElementById("app");
        try { return f.contentWindow.location.pathname === p && f.contentDocument.readyState === "complete" && !!f.contentWindow.__vq; } catch { return false; }
      }, a.path.split("?")[0], { timeout: 60000 });
      await settle(frame(), 2200);
      await verify(a.expect, `navigate ${a.path}`);
    } else if (a.kind === "select") {
      await frame().evaluate(([c, v]) => window.__vq.select({ control: c }, v), [a.control, a.value]);
      await settle(frame());
      const now = await frame().evaluate((c) => window.__vq.options({ control: c }), a.control);
      if (now.error || now.options[now.selected]?.value !== a.value) throw new Fail(`select ${a.control}=${a.value} did not take effect during render`);
      await verify(a.expect, `select ${a.control}`);
    } else if (a.kind === "click") {
      await frame().evaluate((l) => window.__vq.click(l), a.target);
      await settle(frame());
      await verify(a.expect, "click");
    } else if (a.kind === "hover") {
      const { cursor } = await page.evaluate((t) => window.__render(t), a.t);
      if (cursor) { await page.mouse.move(cursor[0], cursor[1]); await sleep(250); }
    } else if (a.kind === "unhover") {
      await page.mouse.move(4, 4);
      await sleep(150);
    }
  };
}

// Layout QA in the real stage: targets on screen, text inside the safe area.
async function layoutQA(page, compiled) {
  for (const c of compiled.checks) {
    if (c.abs) { errors.push(`${c.label} does not fit the frame. Use a smaller target.`); continue; }
    const r = await page.evaluate(([t, rect]) => window.__screenRect(t, rect), [c.t, c.rect]);
    if (r.x < 16 || r.y < 16 || r.x + r.w > STAGE.width - 16 || r.y + r.h > 950) {
      errors.push(`${c.label} lands off-screen or under the caption at t=${c.t.toFixed(2)}s (screen x=${r.x | 0} y=${r.y | 0} w=${r.w | 0} h=${r.h | 0}). Use a smaller target or lower zoom.`);
    }
  }
  const samples = [
    ...compiled.TL.kinetic.map((k) => ({ t: k.start + (k.end - k.start) * 0.7, label: `${k.type} scene` })),
    ...compiled.TL.captions.map((c) => ({ t: (c.start + c.end) / 2, label: `caption "${c.html.replace(/<[^>]+>/g, "").slice(0, 50)}"` })),
  ];
  for (const s of samples) {
    const boxes = await page.evaluate((t) => window.__visibleText(t), s.t);
    for (const b of boxes) {
      if (b.overflow || b.x < 60 || b.x + b.w > STAGE.width - 60 || b.y < 24 || b.y + b.h > STAGE.height - 20) {
        errors.push(`${s.label}: text "${b.text}" overflows the frame (x=${b.x | 0} w=${b.w | 0} y=${b.y | 0} h=${b.h | 0}). Shorten it.`);
      }
      if (b.cls === "headline" && b.h > 330 && !b.scene.includes("layout-stack")) errors.push(`${s.label}: title wraps to 3+ lines. Shorten it.`);
    }
  }
}

function keyTimes(compiled) {
  const ts = new Set();
  for (const k of compiled.TL.kinetic) ts.add(k.start + (k.end - k.start) * 0.7);
  for (const c of compiled.TL.captions) ts.add(c.start + (c.end - c.start) * 0.6);
  for (const m of compiled.TL.menus) ts.add(m.hotFrom + 0.1);
  for (const sp of compiled.TL.windowSpans) ts.add(sp.enterStart + 0.7);
  return [...ts].map((t) => Math.round(t * 100) / 100).sort((a, b) => a - b);
}

// Explicit clip: without it Chrome may return the visual viewport (e.g. 1920x993).
async function step(page, compiled, t) {
  const { cursor } = await page.evaluate((x) => window.__render(x), t);
  const live = compiled.TL.cursor.live.some((w) => t >= w.start && t <= w.end);
  if (live && cursor) {
    await page.mouse.move(cursor[0], cursor[1]);
    await page.evaluate(() => new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r))));
    await page.evaluate((x) => window.__render(x), t);
  }
}

async function capture(cdp, dpr) {
  const { data } = await cdp.send("Page.captureScreenshot", {
    format: "png", optimizeForSpeed: true, fromSurface: true, captureBeyondViewport: true,
    clip: { x: 0, y: 0, width: STAGE.width, height: STAGE.height, scale: dpr },
  });
  const buf = Buffer.from(data, "base64");
  const w = buf.readUInt32BE(16), h = buf.readUInt32BE(20);
  if (w !== STAGE.width * dpr || h !== STAGE.height * dpr) throw new Fail(`Captured frame is ${w}x${h}, expected ${STAGE.width * dpr}x${STAGE.height * dpr}`);
  return buf;
}

// ------------------------------------------------------------------ check / render
function loadStory(file) {
  if (!file) throw new Fail("Missing story path");
  const abs = path.resolve(process.cwd(), file);
  if (!fs.existsSync(abs)) throw new Fail(`Story not found: ${abs}`);
  let story;
  try { story = JSON.parse(fs.readFileSync(abs, "utf8")); } catch (e) { throw new Fail(`Story is not valid JSON: ${e.message}`); }
  const v = validateStory(story);
  warnings.push(...v.warnings);
  errors.push(...v.errors);
  // Variety: must look different from the last 3 videos made.
  errors.push(...varietyErrors(story, previousStories(abs, story.id)));
  if (errors.length) throw new Fail("Storyboard lint failed");
  story.__file = abs;
  return story;
}

// Research gate: required for the final render, checked (with live link checks) whenever present.
async function researchGate(story, { required }) {
  if (!story.research) {
    const msg = 'No "research" file. Before a final render, study 10+ reference videos and write research/<id>.json (see the skill, Step R).';
    if (required) errors.push(msg); else warnings.push(msg);
    return;
  }
  const file = path.join(here, story.research);
  const r = await validateResearch(file, story, { checkLinks: true });
  errors.push(...r.errors);
  warnings.push(...r.warnings);
  if (!r.errors.length) log(`RSRCH ${r.references} references from ${r.brands} brands · techniques used: ${[...techniquesOf(story)].join(", ")}`);
  if (r.wishlist.length) log(`WISH  ${r.wishlist.length} technique(s) the engine cannot do yet were logged (render.mjs wishlist)`);
  if (errors.length) throw new Fail("Research checks failed");
}

function runHistory() {
  const dir = path.join(here, "stories");
  const rows = fs.readdirSync(dir).filter((f) => f.endsWith(".json")).map((f) => {
    const st = JSON.parse(fs.readFileSync(path.join(dir, f), "utf8"));
    return { id: st.id, mtime: fs.statSync(path.join(dir, f)).mtimeMs, fp: fingerprint(st) };
  }).sort((a, b) => b.mtime - a.mtime);
  for (const r of rows) log(`${r.id}\n  ${Object.entries(r.fp).map(([k, v]) => `${k}=${v}`).join("\n  ")}`);
  log("\nA new story must differ from each of the 3 most recent in at least 4 of: look, title, stat, frame, opening, scenes, shots, exit — and at least 2 of look/title/stat/frame/opening.");
}

function runTechniques() {
  for (const [id, [what, how]] of Object.entries(TECHNIQUES)) log(`${id.padEnd(18)} ${what} — ${how}`);
}

function runWishlist() {
  const items = collectWishlist(path.join(here, "research"));
  if (!items.length) { log("Wishlist is empty."); return; }
  const by = {};
  for (const w of items) (by[w.technique.toLowerCase()] ||= []).push(w);
  for (const [t, ws] of Object.entries(by).sort((a, b) => b[1].length - a[1].length)) {
    log(`${ws.length}× ${t}`);
    for (const w of ws) log(`    ${w.story}: ${w.seen_in}${w.why ? ` — ${w.why}` : ""}`);
  }
}

// The bar a Google product video clears, as numbers. Failing these is an error, not a taste call.
function qualityBar(compiled) {
  for (const l of compiled.legibility) {
    if (l.visual && l.minPx < 17) { warnings.push(`${l.label}: map/chart labels render at ${l.minPx.toFixed(1)}px; the picture carries this shot, so the caption must state the point.`); continue; }
    if (l.minPx < 13) errors.push(`${l.label}: smallest text renders at ${l.minPx.toFixed(1)}px — unreadable. Use lift on one card, or a smaller target.`);
    else if (l.minPx < 17) warnings.push(`${l.label}: smallest text renders at ${l.minPx.toFixed(1)}px (aim for 17px+). Fine for chart axes; not for a key sentence.`);
    if ((l.kind === "lift" || l.kind === "compare") && l.keyPx < 48) warnings.push(`${l.label}: its biggest text is only ${l.keyPx.toFixed(0)}px on screen; lift a card whose number is large.`);
  }
  const TL = compiled.TL;
  const ev = [0, compiled.duration];
  for (const k of TL.kinetic) ev.push(k.start, k.start + 0.5, k.start + 1.4, k.start + 2.2, k.end - 0.6);
  for (const sh of TL.shots) if (!sh.drift && sh.dur > 0) ev.push(sh.at);
  for (const c of TL.captions) ev.push(c.start, c.end);
  for (const k of TL.cursor.keys) ev.push(k.at);
  for (const m of TL.menus) ev.push(m.open);
  for (const L of TL.lifts) ev.push(L.start, L.end - 0.7);
  for (const w of TL.windowSpans) ev.push(w.enterStart, w.exitStart);
  ev.sort((a, b) => a - b);
  let gap = 0, at = 0;
  for (let k = 1; k < ev.length; k++) if (ev[k] - ev[k - 1] > gap) { gap = ev[k] - ev[k - 1]; at = ev[k - 1]; }
  if (gap > 7) errors.push(`Nothing new happens on screen for ${gap.toFixed(1)}s from ${at.toFixed(1)}s. Split that line or add a beat.`);
  else if (gap > 4.5) warnings.push(`Longest stretch with no new visual event: ${gap.toFixed(1)}s from ${at.toFixed(1)}s (aim for under 4.5s).`);
  log(`BAR   longest static stretch ${gap.toFixed(1)}s · ${compiled.legibility.length} legibility checks · ${TL.lifts.length} lift/compare`);
}

// Resolve the story's audio block. Returns { music, voice segments, durations, units }.
function audioPlan(story, prep, { requireDecision }) {
  const units = sayUnits(story);
  const plan = { units, music: null, segments: null, durations: {}, decided: false };
  const a = story.audio;
  if (!a || a.music == null || a.voice == null) {
    const msg = "audio not decided: ask the user for a music file and a voice recording (or \"none\" for either). See the voiceover script.";
    if (requireDecision) errors.push(msg); else warnings.push(msg);
    return plan;
  }
  plan.decided = true;
  if (a.music !== "none") {
    const f = path.join(REPO, a.music);
    if (!fs.existsSync(f)) errors.push(`audio.music file not found: ${f}. Ask the user to place it there.`);
    else {
      const p = probeAudio(f);
      if (p.error) errors.push(`audio.music: ${p.error}`);
      else if (p.duration < 3) errors.push(`audio.music is only ${p.duration.toFixed(1)}s long`);
      else {
        plan.music = f;
        const bt = detectBeats(f, Math.min(p.duration, 150));
        if (bt && bt.confidence >= 3) {
          plan.beats = bt.beats;
          log(`MUSIC ${bt.bpm.toFixed(1)} BPM (beat confidence ${bt.confidence.toFixed(1)}); cuts will land on the beat`);
        } else warnings.push(`Music has no clear beat${bt ? ` (confidence ${bt.confidence.toFixed(1)})` : ""}; cuts are not beat-synced`);
      }
    }
  }
  if (a.voice !== "none") {
    if (!units.length) return plan;
    const r = analyzeVoice(path.join(REPO, a.voice), units.length);
    if (r.error) { errors.push(`audio.voice: ${r.error}`); return plan; }
    plan.segments = r.segments;
    log(`VOICE ${r.method}`);
    r.segments.forEach((seg, k) => {
      const u = units[k];
      if (seg.dur > 12) errors.push(`Voice line ${k + 1} (${u.where}) is ${seg.dur.toFixed(1)}s; max 12s. Shorten the line or split it across beats.`);
      plan.durations[u.key] = seg.dur;
    });
  }
  return plan;
}

async function checkAndCompile(browser, story, dpr, { requireAudio = false } = {}) {
  const prep = await prepass(browser, story);
  for (const line of prep.report) log(`BIND  ${line}`);
  if (errors.length) throw new Fail("Page checks failed");
  const plan = audioPlan(story, prep, { requireDecision: requireAudio });
  const scriptPath = path.join(REPO, "media/audio", `${story.id}-voiceover-script.md`);
  if (plan.units.length) writeScript(scriptPath, story, plan.units, prep.say, plan.segments);
  if (errors.length) throw new Fail("Audio checks failed");
  const compiled = compile(story, prep, plan.durations, plan.beats);
  if (compiled.beatStats.total) log(`BEAT  ${compiled.beatStats.snapped}/${compiled.beatStats.total} scene changes snapped onto the music beat`);
  qualityBar(compiled);
  if (compiled.duration > 90) errors.push(`Video would be ${compiled.duration}s with the recorded voice; max 90s. Shorten the narration.`);
  compiled.cues.forEach((c) => {
    const k = plan.units.findIndex((u) => u.key === c.key);
    Object.assign(c, plan.segments[k], { text: prep.say[c.key], at: c.at });
    log(`VOICE line ${k + 1} at ${c.at.toFixed(2)}s for ${c.dur.toFixed(2)}s: "${c.text}"`);
  });
  const stage = await openStage(browser, compiled, dpr, story.theme ?? "paper");
  await layoutQA(stage.page, compiled);
  if (errors.length) throw new Fail("Layout checks failed");
  return { compiled, stage, plan, prep, scriptPath };
}

async function runScript(file) {
  const story = loadStory(file);
  await researchGate(story, { required: false });
  await ping();
  const browser = await chromium.launch({ channel: "chrome" });
  try {
    const prep = await prepass(browser, story);
    for (const line of prep.report) log(`BIND  ${line}`);
    if (errors.length) throw new Fail("Page checks failed");
    const units = sayUnits(story);
    if (!units.length) {
      warnings.push('No "say" lines in the story, so there is no voiceover script. Add "say" to scenes/beats if the video should be narrated.');
    } else {
      const scriptPath = path.join(REPO, "media/audio", `${story.id}-voiceover-script.md`);
      log(writeScript(scriptPath, story, units, prep.say, null));
      log(`\nScript saved: ${scriptPath}`);
    }
    log(`
ASK THE USER (then stop and wait for the reply):
  1. Music: "Please send the music track for this video (a file you have the rights to use), or say none."
  2. Voice: ${units.length ? `"Please record the voiceover script at ${path.join("media/audio", story.id + "-voiceover-script.md")} and send the file, or say none."` : '"Do you want a voiceover? If yes I will add narration lines and send you a script."'}
Then copy the files into media/audio/ and set in the story:  "audio": { "music": "media/audio/<file>" | "none", "voice": "media/audio/<file-or-folder>" | "none" }`);
  } finally {
    await browser.close();
  }
}

async function runCheck(file) {
  const story = loadStory(file);
  await researchGate(story, { required: false });
  await ping(); need("ffmpeg");
  const browser = await chromium.launch({ channel: "chrome", args: ["--window-size=1920,1080", "--force-color-profile=srgb", "--hide-scrollbars"] });
  try {
    const { compiled, stage } = await checkAndCompile(browser, story, 1);
    const dir = path.join(REPO, "media/.preview", story.id);
    fs.rmSync(dir, { recursive: true, force: true });
    fs.mkdirSync(dir, { recursive: true });
    const run = makeActionRunner(stage.page, stage.frame, story);
    const cdp = await stage.context.newCDPSession(stage.page);
    let ai = 0;
    const times = keyTimes(compiled);
    for (const [n, t] of times.entries()) {
      while (compiled.actions[ai] && compiled.actions[ai].t <= t) await run(compiled.actions[ai++]);
      await step(stage.page, compiled, t);
      fs.writeFileSync(path.join(dir, `${String(n).padStart(2, "0")}_t${t.toFixed(2)}.png`), await capture(cdp, 1));
    }
    const cols = 3, rows = Math.ceil(times.length / cols);
    execFileSync("ffmpeg", ["-v", "error", "-y", "-pattern_type", "glob", "-i", path.join(dir, "[0-9]*_t*.png"),
      "-vf", `scale=640:-1,tile=${cols}x${rows}:padding=8:margin=8:color=0xd8d2c8`, "-frames:v", "1", path.join(dir, "contact-sheet.png")]);
    log(`Length: ${compiled.duration}s · ${compiled.TL.captions.length} captions · ${compiled.actions.filter((a) => a.kind === "select" || a.kind === "click").length} interactions`);
    log(`Keyframes: ${dir}`);
    log(`Contact sheet: ${path.join(dir, "contact-sheet.png")}  ← open it and look before rendering`);
    if (sayUnits(story).length) log(`Voiceover script: ${path.join(REPO, "media/audio", story.id + "-voiceover-script.md")}`);
  } finally {
    await browser.close();
  }
}

async function runRender(file) {
  const story = loadStory(file);
  await researchGate(story, { required: !flag("--draft") });
  await ping(); need("ffmpeg"); need("ffprobe");
  const draft = flag("--draft");
  const uhd = flag("--4k");
  const fps = draft ? 30 : 60;
  const dpr = draft ? 1 : 2;
  const outW = uhd ? 3840 : draft ? 1280 : 1920;
  const outH = Math.round((outW * 9) / 16);
  let out = path.join(REPO, story.output || `media/aequitas-${story.id}.mp4`);
  if (draft) out = out.replace(/\.mp4$/, "-draft.mp4");
  if (uhd) out = out.replace(/\.mp4$/, "-4k.mp4");
  fs.mkdirSync(path.dirname(out), { recursive: true });
  const tmp = out.replace(/\.mp4$/, ".partial.mp4");

  const browser = await chromium.launch({ channel: "chrome", args: ["--window-size=1920,1080", "--force-color-profile=srgb", "--hide-scrollbars"] });
  let ff;
  try {
    const { compiled, stage, plan } = await checkAndCompile(browser, story, dpr, { requireAudio: !draft });
    const run = makeActionRunner(stage.page, stage.frame, story);
    const cdp = await stage.context.newCDPSession(stage.page);
    const total = Math.round(compiled.duration * fps);
    // Motion blur: up to 16 sub-frames across a 180° shutter, averaged by ffmpeg. The number of distinct
    // samples adapts to how far things move inside the shutter (1 when still, 16 for very fast moves), so fast
    // moves smear smoothly instead of showing ghost copies, and still frames cost one capture.
    const sub = draft || flag("--no-blur") ? 1 : 16;
    const blurVf = sub > 1 ? `tmix=frames=${sub}:weights='${Array(sub).fill(1).join(" ")}',trim=start_frame=${sub - 1},framestep=${sub},setpts=N/(${fps}*TB),` : "";
    ff = spawn("ffmpeg", [
      "-v", "error", "-y", "-f", "image2pipe", "-framerate", String(fps * sub), "-i", "-",
      "-vf", `${blurVf}scale=${outW}:${outH}:flags=lanczos+accurate_rnd+full_chroma_int:out_color_matrix=bt709:out_range=tv,format=yuv420p`,
      "-c:v", "libx264", "-preset", draft ? "veryfast" : "slow", "-crf", draft ? "22" : "15", "-tune", "animation",
      "-profile:v", "high", "-g", String(fps * 2), "-bf", "2",
      "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709", "-color_range", "tv",
      "-fps_mode", "cfr", "-r", String(fps), "-movflags", "+faststart", "-an", tmp,
    ], { stdio: ["pipe", "inherit", "inherit"] });
    const ffDone = once(ff, "close");
    let ai = 0, blurred = 0;
    const t0 = Date.now();
    for (let f = 0; f < total; f++) {
      const t = f / fps;
      while (compiled.actions[ai] && compiled.actions[ai].t <= t) await run(compiled.actions[ai++]);
      const put = async (png) => { if (!ff.stdin.write(png)) await once(ff.stdin, "drain"); };
      if (sub === 1) {
        await step(stage.page, compiled, t);
        await put(await capture(cdp, dpr));
      } else {
        const half = 0.25 / fps;
        const a = await stage.page.evaluate((x) => window.__motionRects(x), Math.max(0, t - half));
        const b = await stage.page.evaluate((x) => window.__motionRects(x), t + half);
        let disp = a.length === b.length ? 0 : 4;
        if (a.length === b.length) for (let k = 0; k < a.length; k++) disp = Math.max(disp, Math.abs(a[k] - b[k]));
        // One sample per ~1.5px of travel inside the shutter (power of two so it divides ${sub}).
        const u = disp < 0.35 ? 1 : Math.min(sub, 2 ** Math.ceil(Math.log2(Math.max(2, disp / 1.5))));
        if (u > 1) blurred++;
        for (let k = 0; k < u; k++) {
          await step(stage.page, compiled, Math.max(0, t + ((k + 0.5) / u - 0.5) * 2 * half));
          const png = await capture(cdp, dpr);
          for (let r = 0; r < sub / u; r++) await put(png);
        }
      }
      if (f % (fps * 2) === 0) {
        const el = (Date.now() - t0) / 1000;
        const eta = f ? Math.round((el / f) * (total - f)) : 0;
        log(`frame ${f}/${total}  t=${t.toFixed(1)}s  eta ${eta}s`);
      }
    }
    ff.stdin.end();
    const [code] = await ffDone;
    if (code !== 0) throw new Fail(`ffmpeg exited with ${code}`);

    const cues = plan.segments ? compiled.cues : [];
    const sfx = story.sfx === false ? [] : sfxEvents(compiled.TL);
    if (plan.music || cues.length || sfx.length) {
      const withAudio = out.replace(/\.mp4$/, ".audio.mp4");
      mixAudio({ video: tmp, out: withAudio, duration: compiled.duration, music: plan.music, cues, sfx });
      fs.renameSync(withAudio, tmp);
    }
    if (cues.length) writeSrt(out.replace(/\.mp4$/, ".srt"), cues);
    postQA(tmp, { fps, outW, outH, duration: compiled.duration, audio: !!(plan.music || cues.length || sfx.length), program: !!(plan.music || cues.length), cues, music: !!plan.music });
    if (errors.length) throw new Fail("Output checks failed");
    fs.renameSync(tmp, out);
    const mb = (fs.statSync(out).size / 1e6).toFixed(1);
    if (sub > 1) log(`BLUR  ${blurred}/${total} frames had visible motion and got adaptive motion blur (2–${sub} samples)`);
    log(`Rendered ${compiled.duration}s ${outW}x${outH}@${fps} in ${Math.round((Date.now() - t0) / 1000)}s → ${out} (${mb} MB)`);
  } finally {
    if (ff && ff.exitCode == null) ff.kill("SIGKILL");
    if (fs.existsSync(tmp) && errors.length) fs.rmSync(tmp);
    await browser.close();
  }
}

function postQA(file, exp) {
  const probe = JSON.parse(execFileSync("ffprobe", ["-v", "error", "-show_streams", "-show_format", "-of", "json", file]).toString());
  const v = probe.streams.find((s) => s.codec_type === "video");
  const a = probe.streams.find((s) => s.codec_type === "audio");
  const [num, den] = v.r_frame_rate.split("/").map(Number);
  const dur = Number(probe.format.duration);
  if (v.codec_name !== "h264" || v.pix_fmt !== "yuv420p") errors.push(`Output codec ${v.codec_name}/${v.pix_fmt}, expected h264/yuv420p`);
  if (v.width !== exp.outW || v.height !== exp.outH) errors.push(`Output ${v.width}x${v.height}, expected ${exp.outW}x${exp.outH}`);
  if (Math.abs(num / den - exp.fps) > 0.01) errors.push(`Output fps ${num / den}, expected ${exp.fps}`);
  if (Math.abs(dur - exp.duration) > 2 / exp.fps + 0.05) errors.push(`Output duration ${dur}s, expected ${exp.duration}s`);
  if (exp.audio && !a) errors.push("Music/voice requested but no audio stream in output");
  if (exp.audio && a) {
    const lu = ffmpegStderr(["-i", file, "-af", "ebur128=peak=true", "-f", "null", "-"]);
    const m = /Integrated loudness:\s+I:\s+(-?[\d.]+) LUFS/.exec(lu);
    const tp = /True peak:\s+Peak:\s+(-?[\d.]+|-inf) dBFS/.exec(lu);
    if (tp && tp[1] !== "-inf" && Number(tp[1]) > -1.0) errors.push(`True peak ${tp[1]} dBFS; must be ≤ -1.0`);
    if (exp.program) {
      if (!m) errors.push("Could not measure output loudness");
      else if (Math.abs(Number(m[1]) + 16) > 2) errors.push(`Output loudness ${m[1]} LUFS, expected -16 ±2`);
      else log(`QA    loudness ${m[1]} LUFS · true peak ${tp ? tp[1] : "?"} dBFS`);
    }
    // Voice must sit clearly above the music bed.
    if (exp.cues?.length && exp.music) {
      const speech = exp.cues.filter((c) => c.dur > 1.5).map((c) => [c.at + 0.3, c.at + c.dur - 0.3]);
      const busy = exp.cues.map((c) => [c.at - 0.7, c.at + c.dur + 1.0]);
      const gaps = [];
      for (let t = 1.5; t < exp.duration - 3; t += 0.5) if (!busy.some(([x, y]) => t + 1 > x && t < y)) gaps.push([t, t + 1]);
      const lufs = (ranges) => {
        const vals = ranges.slice(0, 6).map(([x, y]) => loudness(file, x, y)).filter((v) => v != null && v > -70);
        return vals.length ? vals.reduce((s, v) => s + v, 0) / vals.length : null;
      };
      const ls = lufs(speech), lg = lufs(gaps);
      if (ls != null && lg != null) {
        if (ls - lg < 8) errors.push(`Voice is only ${(ls - lg).toFixed(1)} LU above the music between lines; needs 8+`);
        else log(`QA    voice sits ${(ls - lg).toFixed(1)} LU above the music bed`);
      }
    }
  }
  const blackLog = ffmpegStderr(["-i", file, "-vf", "blackdetect=d=0.2:pix_th=0.10", "-an", "-f", "null", "-"]);
  if (/black_start/.test(blackLog)) errors.push("Black frames detected in output");
  const freezeLog = ffmpegStderr(["-i", file, "-vf", "freezedetect=n=0.0003:d=3", "-an", "-f", "null", "-"]);
  if (/freeze_start/.test(freezeLog)) warnings.push("A section of 3s+ has no visible motion; consider shorter seconds");
  log(`QA    ${v.width}x${v.height} ${num / den}fps ${dur.toFixed(2)}s h264 ${Math.round(Number(probe.format.bit_rate) / 1000)} kb/s${a ? " +audio" : ""}`);
}

function ffmpegStderr(args) {
  const r = spawnSync("ffmpeg", ["-v", "info", "-hide_banner", ...args], { encoding: "utf8" });
  return String(r.stderr || "");
}

// ------------------------------------------------------------------ main
try {
  if (cmd === "inspect") await inspect(target);
  else if (cmd === "check") await runCheck(target);
  else if (cmd === "script") await runScript(target);
  else if (cmd === "history") runHistory();
  else if (cmd === "techniques") runTechniques();
  else if (cmd === "wishlist") runWishlist();
  else if (cmd === "render") await runRender(target);
  else throw new Fail("Usage: render.mjs inspect <app-path> | techniques | history | wishlist | check <story.json> | script <story.json> | render <story.json> [--draft] [--4k]");
} catch (e) {
  if (!(e instanceof Fail)) errors.push(`Unexpected: ${e.stack || e.message}`);
  else if (!errors.length || !/failed$/.test(e.message)) errors.push(e.message);
}
finish();
