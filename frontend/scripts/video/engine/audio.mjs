// Narration + music: voiceover script, voice take analysis, mix, subtitles.
// The user records the voice and supplies the music; nothing here generates audio.
import fs from "node:fs";
import path from "node:path";
import { execFileSync, spawnSync } from "node:child_process";

const AUDIO_EXT = /\.(wav|mp3|m4a|aac|aif|aiff|flac|ogg|opus|caf)$/i;
export const LEAD = { title: 1.0, stat: 0.5, outro: 0.8, focus: 0.5, wide: 0.4, select: 0.3, click: 0.3, lift: 0.6, compare: 0.7, quote: 0.7 };
export const TAIL = { kinetic: 0.9, beat: 0.5 };
const WORDS_PER_SEC = 2.5;

// Narrated units in story order: { key, kind, where, label, text(raw) }.
export function sayUnits(story) {
  const out = [];
  story.scenes.forEach((s, i) => {
    if (s.type !== "app") {
      if (s.say) out.push({ key: `s${i}`, kind: s.type, where: `scenes[${i}]`, label: { title: "Title card", stat: "Big number", outro: "Closing card", quote: "Pull quote from the page" }[s.type], text: s.say });
      return;
    }
    s.beats.forEach((b, j) => {
      if (!b.say) return;
      const tgt = b.target ? (typeof b.target === "string" ? b.target : Object.values(b.target).flat().join(" + ")) : "";
      const label = {
        focus: `Close-up on ${tgt}${b.hover ? " (cursor hovers the chart)" : ""}`,
        wide: "Whole page",
        select: `Cursor sets ${b.control} to ${b.option}`,
        click: `Cursor clicks ${tgt}`,
        lift: `${tgt} lifts out of the page`,
        compare: `${tgt} side by side: ${(b.labels || b.options || []).join(" vs ")}`,
      }[b.do];
      out.push({ key: `s${i}b${j}`, kind: b.do, where: `scenes[${i}].beats[${j}]`, label, text: b.say });
    });
  });
  return out;
}

export function probeAudio(file) {
  const r = spawnSync("ffprobe", ["-v", "error", "-show_streams", "-show_format", "-of", "json", file], { encoding: "utf8" });
  if (r.status !== 0) return { error: `Cannot read audio file ${file}: ${(r.stderr || "").trim().split("\n")[0]}` };
  const j = JSON.parse(r.stdout);
  const a = (j.streams || []).find((s) => s.codec_type === "audio");
  if (!a) return { error: `${file} has no audio stream` };
  return { duration: Number(j.format.duration), channels: a.channels, rate: Number(a.sample_rate) };
}

// Integrated loudness (EBU R128; silence is gated out, so a voice take with pauses measures its speech).
export function loudness(file, start = null, end = null) {
  const args = ["-hide_banner", "-nostats"];
  if (start != null) args.push("-ss", String(start), "-to", String(end));
  args.push("-i", file, "-af", "loudnorm=print_format=json", "-f", "null", "-");
  const r = spawnSync("ffmpeg", args, { encoding: "utf8" });
  const m = /\{[^{}]*"input_i"[^{}]*\}/s.exec(r.stderr || "");
  if (!m) return null;
  const v = Number(JSON.parse(m[0]).input_i);
  return Number.isFinite(v) ? v : null;
}

function silences(file, noiseDb, minSilence) {
  const r = spawnSync("ffmpeg", ["-hide_banner", "-nostats", "-i", file, "-af", `silencedetect=noise=${noiseDb}dB:d=${minSilence}`, "-f", "null", "-"], { encoding: "utf8" });
  const out = [];
  let cur = null;
  for (const line of (r.stderr || "").split("\n")) {
    let m = /silence_start: (-?[\d.]+)/.exec(line);
    if (m) cur = { start: Math.max(0, Number(m[1])) };
    m = /silence_end: ([\d.]+)/.exec(line);
    if (m && cur) { cur.end = Number(m[1]); out.push(cur); cur = null; }
  }
  if (cur) cur.end = Infinity;
  if (cur) out.push(cur);
  return out;
}

function speech(file, duration, noiseDb, minSilence) {
  const sil = silences(file, noiseDb, minSilence);
  const segs = [];
  let pos = 0;
  for (const s of sil) {
    if (s.start > pos) segs.push({ start: pos, end: s.start });
    pos = Math.min(duration, s.end);
  }
  if (pos < duration) segs.push({ start: pos, end: duration });
  return segs
    .filter((s) => s.end - s.start >= 0.3)
    .map((s) => ({ start: Math.max(0, s.start - 0.06), end: Math.min(duration, s.end + 0.15) }));
}

// Returns { segments:[{file,start,end,dur,gainDb}], method } or { error }.
export function analyzeVoice(voicePath, count) {
  if (!fs.existsSync(voicePath)) return { error: `Voice not found: ${voicePath}` };
  const TARGET = -17;
  if (fs.statSync(voicePath).isDirectory()) {
    const files = fs.readdirSync(voicePath).filter((f) => AUDIO_EXT.test(f)).sort((a, b) => a.localeCompare(b, "en", { numeric: true }));
    if (files.length !== count) return { error: `Voice folder has ${files.length} audio files; script has ${count} lines. Name them 01, 02, ... one per line.` };
    const segments = [];
    for (const f of files) {
      const file = path.join(voicePath, f);
      const p = probeAudio(file);
      if (p.error) return { error: p.error };
      const sp = speech(file, p.duration, -40, 0.35);
      if (!sp.length) return { error: `${f} seems silent` };
      const start = sp[0].start, end = sp.at(-1).end;
      const lu = loudness(file);
      segments.push({ file, start, end, dur: end - start, gainDb: lu == null ? 0 : TARGET - lu });
    }
    return { segments, method: `${count} files in ${voicePath}` };
  }
  const p = probeAudio(voicePath);
  if (p.error) return { error: p.error };
  const lu = loudness(voicePath);
  const gainDb = lu == null ? 0 : TARGET - lu;
  const tried = [];
  for (const d of [0.7, 0.55, 0.9, 1.2, 0.45]) {
    for (const n of [-38, -32, -44, -28, -50]) {
      const segs = speech(voicePath, p.duration, n, d);
      tried.push(segs.length);
      if (segs.length === count) {
        return { segments: segs.map((s) => ({ file: voicePath, ...s, dur: s.end - s.start, gainDb })), method: `one take, split at pauses (${n} dB, ${d}s)` };
      }
    }
  }
  const common = tried.sort((a, b) => tried.filter((x) => x === b).length - tried.filter((x) => x === a).length)[0];
  return {
    error: `Voice take splits into ${common} spoken part(s) at its pauses, but the script has ${count} lines. ` +
      `Ask the user to re-record with a clear 1–2 second silence between lines (and none inside a line), ` +
      `or to supply one file per line in a folder (01.wav, 02.wav, ...).`,
  };
}

export function writeScript(file, story, units, resolved, segments) {
  const lines = [];
  lines.push(`# Voiceover script — ${story.id}`, "");
  lines.push("## How to record", "");
  lines.push("- Read the lines below in order, in one take. Leave a clear pause of 1–2 seconds of silence between lines, and no long pause inside a line.");
  lines.push("- Or record one file per line and put them in a folder named after the video, files named 01, 02, 03 ...");
  lines.push("- Quiet room, phone or mic about a hand's width from your mouth, no music playing. WAV or M4A is best.");
  lines.push("- Read numbers exactly as written (\"41.2%\" is \"forty-one point two percent\"). Do not round them.");
  lines.push("- Natural pace. The video stretches each scene to fit your line, so do not rush.");
  lines.push("");
  lines.push("## Lines", "");
  units.forEach((u, k) => {
    const words = resolved[u.key].split(/\s+/).length;
    const seg = segments?.[k];
    lines.push(`${k + 1}. **${resolved[u.key]}**`);
    lines.push(`   - On screen: ${u.label}. About ${Math.max(1, Math.round(words / WORDS_PER_SEC))} s at a natural pace.${seg ? ` Recorded: ${seg.dur.toFixed(1)} s.` : ""}`);
  });
  lines.push("", "## Files to send back", "");
  lines.push(`- Voice: one take, e.g. \`media/audio/${story.id}-voice.m4a\` (or a folder \`media/audio/${story.id}-voice/\`).`);
  lines.push(`- Music: a track you have the rights to use, e.g. \`media/audio/${story.id}-music.mp3\`. It loops or trims to the video length and dips under the voice automatically.`);
  fs.mkdirSync(path.dirname(file), { recursive: true });
  fs.writeFileSync(file, lines.join("\n") + "\n");
  return lines.join("\n");
}

const srtTime = (t) => {
  const ms = Math.max(0, Math.round(t * 1000));
  const h = Math.floor(ms / 3600000), m = Math.floor((ms % 3600000) / 60000), s = Math.floor((ms % 60000) / 1000);
  return `${String(h).padStart(2, "0")}:${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")},${String(ms % 1000).padStart(3, "0")}`;
};
export function writeSrt(file, cues) {
  const body = cues.map((c, k) => `${k + 1}\n${srtTime(c.at)} --> ${srtTime(c.at + Math.max(1.2, c.dur))}\n${c.text}\n`).join("\n");
  fs.writeFileSync(file, body);
}

// Mux music and/or voice onto a silent video. Every level is measured after processing:
//   1. voice stem: each line cut from the take, cleaned (high-pass, gentle compression), placed at its cue;
//      measured, then set to -14 LUFS (stereo).
//   2. music: levelled to -29 LUFS under voice (-16 if no voice), looped/trimmed, faded, ducked by the voice.
//   3. mix measured once more; one static gain + limiter brings it to -16 LUFS. (Dynamic loudnorm would
//      pump the music up in the pauses between lines.)
const VOICE_TARGET = -14;
const BED_TARGET = -26;
const PROGRAM_TARGET = -16;

function run(args) {
  execFileSync("ffmpeg", ["-v", "error", "-y", ...args], { stdio: ["ignore", "inherit", "inherit"] });
}

export function mixAudio({ video, out, duration, music, cues, sfx }) {
  const D = duration.toFixed(3);
  const base = out.replace(/\.mp4$/, "");
  const temps = [];
  try {
    let voiceWav = null, voiceGain = 0;
    if (cues?.length) {
      const args = [];
      const fileIdx = new Map();
      for (const c of cues) if (!fileIdx.has(c.file)) { fileIdx.set(c.file, fileIdx.size); args.push("-i", c.file); }
      const g = cues.map((c, k) => {
        const len = c.end - c.start;
        return `[${fileIdx.get(c.file)}:a]atrim=start=${c.start.toFixed(3)}:end=${c.end.toFixed(3)},asetpts=PTS-STARTPTS,` +
          `aformat=sample_rates=48000:channel_layouts=mono,volume=${c.gainDb.toFixed(2)}dB,` +
          `afade=t=in:d=0.03,afade=t=out:st=${Math.max(0, len - 0.08).toFixed(3)}:d=0.08,adelay=${Math.round(c.at * 1000)}:all=1[v${k}]`;
      });
      g.push(`${cues.map((_, k) => `[v${k}]`).join("")}amix=inputs=${cues.length}:normalize=0:duration=longest,` +
        `highpass=f=80,acompressor=threshold=-24dB:ratio=2.5:attack=5:release=120:makeup=4,apad=whole_dur=${D},atrim=0:${D},pan=stereo|c0=c0|c1=c0[voice]`);
      voiceWav = `${base}.voice.wav`; temps.push(voiceWav);
      run([...args, "-filter_complex", g.join(";"), "-map", "[voice]", "-c:a", "pcm_s24le", voiceWav]);
      const lv = loudness(voiceWav);
      voiceGain = lv == null ? 0 : VOICE_TARGET - lv;
    }
    let sfxWav = null;
    if (sfx?.length) { sfxWav = `${base}.sfx.wav`; temps.push(sfxWav); renderSfx(sfx, duration, sfxWav); }
    const args = [];
    const g = [];
    let i = 0;
    if (voiceWav) { args.push("-i", voiceWav); g.push(`[${i++}:a]volume=${voiceGain.toFixed(2)}dB[voice]`); }
    if (music) {
      args.push("-stream_loop", "-1", "-i", music);
      const lm = loudness(music);
      const mg = lm == null ? 0 : (voiceWav ? BED_TARGET : PROGRAM_TARGET) - lm;
      g.push(`[${i++}:a]atrim=0:${D},asetpts=PTS-STARTPTS,aformat=sample_rates=48000:channel_layouts=stereo,volume=${mg.toFixed(2)}dB,` +
        `afade=t=in:st=0:d=1.2,afade=t=out:st=${Math.max(0, duration - 2.5).toFixed(3)}:d=2.5[m]`);
    }
    const parts = [];
    if (voiceWav && music) {
      g.push(`[voice]asplit=2[vs][vm]`, `[m][vs]sidechaincompress=threshold=0.03:ratio=4:attack=40:release=600[md]`);
      parts.push("[md]", "[vm]");
    } else if (voiceWav) parts.push("[voice]");
    else if (music) parts.push("[m]");
    if (sfxWav) { args.push("-i", sfxWav); g.push(`[${i++}:a]anull[fx]`); parts.push("[fx]"); }
    g.push(parts.length > 1 ? `${parts.join("")}amix=inputs=${parts.length}:normalize=0:duration=first[mix]` : `${parts[0]}anull[mix]`);
    const mixWav = `${base}.mix.wav`; temps.push(mixWav);
    run([...args, "-filter_complex", g.join(";"), "-map", "[mix]", "-t", D, "-c:a", "pcm_s24le", "-ar", "48000", mixWav]);
    const lmix = loudness(mixWav);
    // Foley alone is not normalised up to programme loudness; it stays at its designed level.
    const gain = !voiceWav && !music ? 0 : lmix == null ? 0 : PROGRAM_TARGET - lmix;
    run(["-i", video, "-i", mixWav, "-filter_complex", `[1:a]volume=${gain.toFixed(2)}dB,alimiter=limit=0.84:level=false,aresample=48000[a]`,
      "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-t", D, "-movflags", "+faststart", out]);
  } finally {
    for (const f of temps) fs.rmSync(f, { force: true });
  }
}

// ---------------------------------------------------------------- music beats
// Onset envelope (rectified log-energy rise, full band + high band) → tempo by autocorrelation
// (60–180 BPM, weighted toward 120) → phase by best-aligned grid. Returns null for beatless music.
function pcm(file, sr, filter, seconds) {
  const r = spawnSync("ffmpeg", ["-v", "error", "-i", file, "-t", String(seconds), "-ac", "1", "-ar", String(sr), "-af", filter, "-f", "f32le", "-"], { maxBuffer: 1 << 30 });
  const b = r.stdout;
  return new Float32Array(b.buffer.slice(b.byteOffset, b.byteOffset + b.length - (b.length % 4)));
}
function onsets(x, hop) {
  const frames = Math.floor(x.length / hop);
  const env = new Float32Array(frames);
  let prev = null;
  for (let f = 0; f < frames; f++) {
    let e = 0;
    for (let i = f * hop; i < (f + 1) * hop; i++) e += x[i] * x[i];
    const le = Math.log(1e-10 + e / hop);
    env[f] = prev == null ? 0 : Math.max(0, le - prev);
    prev = le;
  }
  return env;
}
export function detectBeats(file, seconds) {
  const sr = 11025, hop = 256, fps = sr / hop;
  const a = onsets(pcm(file, sr, "highpass=f=40", seconds), hop);
  const b = onsets(pcm(file, sr, "highpass=f=2000", seconds), hop);
  const n = Math.min(a.length, b.length);
  if (n < fps * 6) return null;
  const env = new Float32Array(n);
  let mean = 0;
  for (let i = 0; i < n; i++) { env[i] = a[i] + b[i]; mean += env[i]; }
  mean /= n;
  for (let i = 0; i < n; i++) env[i] = Math.max(0, env[i] - mean);
  const minLag = Math.floor((60 / 180) * fps), maxLag = Math.ceil((60 / 60) * fps);
  const ac = [];
  for (let l = minLag; l <= maxLag; l++) {
    let s = 0;
    for (let i = 0; i + l < n; i++) s += env[i] * env[i + l];
    ac.push(s / (n - l));
  }
  const weighted = ac.map((v, k) => v * Math.exp(-0.5 * (Math.log2(60 * fps / (k + minLag) / 120) / 0.9) ** 2));
  let best = 0;
  for (let k = 1; k < weighted.length; k++) if (weighted[k] > weighted[best]) best = k;
  const m = ac.reduce((s, v) => s + v, 0) / ac.length;
  const sd = Math.sqrt(ac.reduce((s, v) => s + (v - m) ** 2, 0) / ac.length) || 1;
  const confidence = (ac[best] - m) / sd;
  // Parabolic refinement of the period.
  let lag = best + minLag;
  if (best > 0 && best < ac.length - 1) {
    const y0 = ac[best - 1], y1 = ac[best], y2 = ac[best + 1];
    const d = y0 - 2 * y1 + y2;
    if (d !== 0) lag += (0.5 * (y0 - y2)) / d;
  }
  let phase = 0, bestScore = -1;
  for (let o = 0; o < lag; o += 0.25) {
    let sc = 0;
    for (let p = o; p < n; p += lag) sc += env[Math.round(p)] || 0;
    if (sc > bestScore) { bestScore = sc; phase = o; }
  }
  const beats = [];
  for (let p = phase; p < n; p += lag) beats.push(p / fps);
  return { bpm: (60 * fps) / lag, beats, confidence };
}

// ---------------------------------------------------------------- sound design
// Procedural UI foley (no samples, no licensing): click, tick, whoosh, rise, pop.
const SFX_SRC = {
  click: ["-f", "lavfi", "-i", "aevalsrc=exprs='0.5*sin(2*PI*1800*t)*exp(-t*70)+0.3*(random(1)*2-1)*exp(-t*600)':s=48000:d=0.09"],
  tick: ["-f", "lavfi", "-i", "aevalsrc=exprs='0.35*sin(2*PI*2600*t)*exp(-t*120)':s=48000:d=0.06"],
  whoosh: ["-f", "lavfi", "-i", "anoisesrc=d=0.75:c=pink:r=48000:a=0.6", "-af", "highpass=f=250,lowpass=f=2800,afade=t=in:d=0.45:curve=qsin,afade=t=out:st=0.45:d=0.3:curve=qsin"],
  pop: ["-f", "lavfi", "-i", "aevalsrc=exprs='0.45*sin(2*PI*(300+300*exp(-t*30))*t)*exp(-t*12)':s=48000:d=0.35"],
};
export function sfxEvents(TL) {
  const ev = [];
  for (const c of TL.cursor.clicks) ev.push({ t: c, kind: "click", db: 0 });
  for (const m of TL.menus) ev.push({ t: m.open, kind: "tick", db: -4 });
  for (const w of TL.windowSpans) { ev.push({ t: w.enterStart, kind: "whoosh", db: -3 }); ev.push({ t: w.exitStart - 0.2, kind: "whoosh", db: -9 }); }
  for (const L of TL.lifts) {
    ev.push({ t: L.start, kind: "whoosh", db: -5 });
    L.items.forEach((it) => ev.push({ t: L.start + it.delay + 0.55, kind: "pop", db: -6 }));
    ev.push({ t: L.end - 0.7, kind: "whoosh", db: -11 });
  }
  for (const k of TL.kinetic) {
    if (k.start > 0.1) ev.push({ t: k.start - 0.15, kind: "whoosh", db: -10 });
    if (k.type === "stat") k.values.forEach((v, j) => { if (v.num != null) ev.push({ t: k.start + 2.0 + j * 0.4, kind: "pop", db: -4 }); });
  }
  return ev.filter((e) => e.t >= 0).sort((a, b) => a.t - b.t);
}
export function renderSfx(events, duration, outWav) {
  const dir = fs.mkdtempSync(path.join(path.dirname(outWav), ".sfx-"));
  try {
    const files = {};
    for (const [k, src] of Object.entries(SFX_SRC)) {
      files[k] = path.join(dir, `${k}.wav`);
      run([...src, "-ac", "1", files[k]]);
    }
    const args = [];
    const g = [];
    events.forEach((e, i) => {
      args.push("-i", files[e.kind]);
      g.push(`[${i}:a]volume=${(e.db - 12).toFixed(1)}dB,adelay=${Math.round(e.t * 1000)}:all=1[e${i}]`);
    });
    g.push(`${events.map((_, i) => `[e${i}]`).join("")}amix=inputs=${events.length}:normalize=0:duration=longest,apad=whole_dur=${duration.toFixed(3)},atrim=0:${duration.toFixed(3)},pan=stereo|c0=c0|c1=c0[sfx]`);
    run([...args, "-filter_complex", g.join(";"), "-map", "[sfx]", "-c:a", "pcm_s24le", "-ar", "48000", outWav]);
  } finally {
    fs.rmSync(dir, { recursive: true, force: true });
  }
}
