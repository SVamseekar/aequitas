import { chromium } from "playwright";
import fs from "node:fs";
import { execSync } from "node:child_process";
import path from "node:path";

const videoDir = "/tmp/aequitas-director-render";
if (fs.existsSync(videoDir)) fs.rmSync(videoDir, { recursive: true, force: true });
fs.mkdirSync(videoDir, { recursive: true });

const outputDir = "/Users/souravamseekarmarti/Projects/aequitas/media";
fs.mkdirSync(outputDir, { recursive: true });
const finalMp4Path = path.join(outputDir, "aequitas-england-sunday-cliff-feature.mp4");

console.log("Launching Chromium in 1920x1080 studio viewport...");
const browser = await chromium.launch({
  channel: "chrome",
  headless: true,
  args: [
    "--enable-webgl",
    "--use-gl=angle",
    "--use-angle=swiftshader",
    "--window-size=1920,1080",
    "--font-render-hinting=none"
  ]
});

const context = await browser.newContext({
  viewport: { width: 1920, height: 1080 },
  deviceScaleFactor: 1,
  recordVideo: { dir: videoDir, size: { width: 1920, height: 1080 } }
});

const page = await context.newPage();
console.log("Navigating to Aequitas England Service view...");
await page.goto("http://127.0.0.1:5173/app/england/service?view=b3_weekend_penalty", { waitUntil: "networkidle" });
await page.waitForTimeout(1000);

// Setup presentation layer
await page.evaluate(() => {
  const style = document.createElement("style");
  style.id = "director-styles";
  style.textContent = `
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=Space+Grotesk:wght@500;700&display=swap');

    * { box-sizing: border-box; }
    
    html, body {
      background: #06080E !important;
      margin: 0 !important;
      padding: 0 !important;
      overflow: hidden !important;
      width: 1920px !important;
      height: 1080px !important;
      font-family: 'Plus Jakarta Sans', -apple-system, sans-serif !important;
    }

    #stage-background {
      position: absolute;
      inset: 0;
      background: 
        radial-gradient(circle at 50% 15%, rgba(37, 99, 235, 0.24) 0%, transparent 60%),
        radial-gradient(circle at 80% 85%, rgba(13, 148, 136, 0.16) 0%, transparent 50%),
        linear-gradient(180deg, #06080E 0%, #090E1A 100%);
      z-index: 1;
      overflow: hidden;
    }

    .grid-lines {
      position: absolute;
      inset: 0;
      background-size: 40px 40px;
      background-image: 
        linear-gradient(to right, rgba(255, 255, 255, 0.025) 1px, transparent 1px),
        linear-gradient(to bottom, rgba(255, 255, 255, 0.025) 1px, transparent 1px);
      mask-image: radial-gradient(circle at 50% 50%, black, transparent 80%);
    }

    #director-camera {
      position: absolute;
      inset: 0;
      display: flex;
      align-items: center;
      justify-content: center;
      z-index: 10;
      transition: transform 1.3s cubic-bezier(0.16, 1, 0.3, 1);
      transform-origin: 50% 50%;
    }

    #studio-window {
      width: 1600px;
      height: 940px;
      background: #FFFFFF;
      border-radius: 16px;
      box-shadow: 
        0 40px 100px -15px rgba(0, 0, 0, 0.85),
        0 0 0 1px rgba(255, 255, 255, 0.1),
        0 0 50px -10px rgba(59, 130, 246, 0.22);
      display: flex;
      flex-direction: column;
      overflow: hidden;
      position: relative;
    }

    #studio-titlebar {
      height: 46px;
      background: #F8FAFC;
      border-bottom: 1px solid #E2E8F0;
      display: flex;
      align-items: center;
      padding: 0 20px;
      user-select: none;
      flex-shrink: 0;
      gap: 16px;
    }

    .mac-dots {
      display: flex;
      gap: 8px;
    }
    .mac-dot {
      width: 12px;
      height: 12px;
      border-radius: 50%;
    }
    .mac-red { background: #FF5F56; box-shadow: 0 0 0 1px #E0443E; }
    .mac-yellow { background: #FFBD2E; box-shadow: 0 0 0 1px #DEA123; }
    .mac-green { background: #27C93F; box-shadow: 0 0 0 1px #1AAB29; }

    .url-pill {
      margin: 0 auto;
      background: #FFFFFF;
      border: 1px solid #E2E8F0;
      border-radius: 8px;
      padding: 5px 24px;
      font-size: 13px;
      font-weight: 500;
      color: #334155;
      display: flex;
      align-items: center;
      gap: 8px;
      box-shadow: 0 1px 2px rgba(0,0,0,0.04);
    }

    .live-badge {
      font-size: 11px;
      font-weight: 700;
      color: #059669;
      background: #ECFDF5;
      padding: 4px 12px;
      border-radius: 100px;
      border: 1px solid #A7F3D0;
      letter-spacing: 0.02em;
      display: flex;
      align-items: center;
      gap: 6px;
    }
    .pulse-dot {
      width: 6px;
      height: 6px;
      border-radius: 50%;
      background: #10B981;
      box-shadow: 0 0 8px #10B981;
    }

    #studio-viewport {
      flex: 1;
      overflow-y: auto;
      position: relative;
    }

    /* Virtual Cursor */
    #virtual-cursor {
      position: fixed;
      width: 28px;
      height: 28px;
      top: 600px;
      left: 960px;
      z-index: 99999;
      pointer-events: none;
      transition: left 0.9s cubic-bezier(0.2, 0.8, 0.2, 1), top 0.9s cubic-bezier(0.2, 0.8, 0.2, 1);
      filter: drop-shadow(0 4px 10px rgba(0,0,0,0.4));
      opacity: 0;
    }
    #virtual-cursor.visible {
      opacity: 1;
    }

    .cursor-ripple {
      position: absolute;
      top: -12px;
      left: -12px;
      width: 44px;
      height: 44px;
      border-radius: 50%;
      background: rgba(37, 99, 235, 0.4);
      border: 2px solid rgba(37, 99, 235, 0.9);
      transform: scale(0);
      opacity: 0;
      pointer-events: none;
    }
    .cursor-ripple.click {
      animation: rippleAnim 0.6s ease-out forwards;
    }
    @keyframes rippleAnim {
      0% { transform: scale(0.2); opacity: 1; }
      100% { transform: scale(1.8); opacity: 0; }
    }

    /* Kinetic Callout Badges */
    .callout-overlay {
      position: absolute;
      bottom: 44px;
      left: 50%;
      transform: translateX(-50%) translateY(30px);
      background: rgba(15, 23, 42, 0.94);
      backdrop-filter: blur(20px);
      border: 1px solid rgba(255, 255, 255, 0.14);
      border-radius: 16px;
      padding: 16px 28px;
      display: flex;
      align-items: center;
      gap: 16px;
      color: white;
      box-shadow: 0 25px 60px rgba(0,0,0,0.7);
      opacity: 0;
      transition: all 0.6s cubic-bezier(0.16, 1, 0.3, 1);
      z-index: 500;
      max-width: 820px;
    }
    .callout-overlay.active {
      transform: translateX(-50%) translateY(0);
      opacity: 1;
    }
    .callout-pill {
      background: #2563EB;
      color: white;
      font-size: 11px;
      font-weight: 800;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      padding: 6px 14px;
      border-radius: 6px;
    }
    .callout-pill.alert {
      background: #DC2626;
      box-shadow: 0 0 20px rgba(220, 38, 38, 0.4);
    }
    .callout-title {
      font-size: 18px;
      font-weight: 700;
      letter-spacing: -0.01em;
    }
    .callout-sub {
      font-size: 13.5px;
      color: #94A3B8;
      margin-top: 2px;
    }

    /* Fullscreen Title Card */
    #title-card {
      position: absolute;
      inset: 0;
      z-index: 2000;
      background: #06080E;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      color: white;
      text-align: center;
      transition: opacity 0.8s ease, transform 0.8s cubic-bezier(0.16, 1, 0.3, 1);
    }
    #title-card.hide {
      opacity: 0;
      transform: scale(1.05);
      pointer-events: none;
    }

    /* Outro Card */
    #outro-card {
      position: absolute;
      inset: 0;
      z-index: 2000;
      background: #06080E;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      color: white;
      text-align: center;
      opacity: 0;
      transform: scale(0.96);
      transition: opacity 0.8s ease, transform 0.8s cubic-bezier(0.16, 1, 0.3, 1);
      pointer-events: none;
    }
    #outro-card.show {
      opacity: 1;
      transform: scale(1);
      pointer-events: auto;
    }

    /* Highlights */
    .director-highlight {
      outline: 3px solid #2563EB !important;
      outline-offset: 4px !important;
      border-radius: 8px !important;
      box-shadow: 0 0 30px rgba(37, 99, 235, 0.45) !important;
      transition: all 0.4s ease !important;
    }
    .director-highlight-red {
      outline: 3px solid #EF4444 !important;
      outline-offset: 4px !important;
      border-radius: 8px !important;
      box-shadow: 0 0 35px rgba(239, 68, 68, 0.55) !important;
      transition: all 0.4s ease !important;
    }
  `;
  document.head.appendChild(style);

  // Build UI wrappers
  const bg = document.createElement("div");
  bg.id = "stage-background";
  bg.innerHTML = `<div class="grid-lines"></div>`;
  document.body.prepend(bg);

  const root = document.getElementById("root");
  const camera = document.createElement("div");
  camera.id = "director-camera";

  const win = document.createElement("div");
  win.id = "studio-window";

  const titlebar = document.createElement("div");
  titlebar.id = "studio-titlebar";
  titlebar.innerHTML = `
    <div class="mac-dots">
      <span class="mac-dot mac-red"></span>
      <span class="mac-dot mac-yellow"></span>
      <span class="mac-dot mac-green"></span>
    </div>
    <div class="url-pill">
      <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"></rect><path d="M7 11V7a5 5 0 0 1 10 0v4"></path></svg>
      aequitas.souravamseekar.com / england / service-quality
    </div>
    <div class="live-badge">
      <span class="pulse-dot"></span>
      32,844 LSOAs · BODS GTFS
    </div>
  `;

  const viewport = document.createElement("div");
  viewport.id = "studio-viewport";

  document.body.appendChild(camera);
  camera.appendChild(win);
  win.appendChild(titlebar);
  win.appendChild(viewport);
  viewport.appendChild(root);

  // Add virtual cursor
  const cursor = document.createElement("div");
  cursor.id = "virtual-cursor";
  cursor.innerHTML = `
    <svg width="28" height="28" viewBox="0 0 24 24" fill="#0F172A" stroke="white" stroke-width="1.8">
      <path d="M4.5 3L11.5 21L14.5 13.5L22 10.5L4.5 3Z"/>
    </svg>
    <div class="cursor-ripple" id="cursor-ripple"></div>
  `;
  document.body.appendChild(cursor);

  // Add lower-third callout badge
  const callout = document.createElement("div");
  callout.id = "callout-overlay";
  callout.className = "callout-overlay";
  callout.innerHTML = `
    <div class="callout-pill" id="callout-pill">NATIONAL BASELINE</div>
    <div>
      <div class="callout-title" id="callout-title">Sunday Transit Penalty in England</div>
      <div class="callout-sub" id="callout-sub">Evaluating 32,844 small areas against official GTFS timetables</div>
    </div>
  `;
  document.body.appendChild(callout);

  // Add title card
  const titleCard = document.createElement("div");
  titleCard.id = "title-card";
  titleCard.innerHTML = `
    <div style="display:inline-flex;align-items:center;gap:8px;background:rgba(37,99,235,0.18);border:1px solid rgba(59,130,246,0.35);padding:6px 18px;border-radius:100px;font-size:12px;font-weight:700;color:#60A5FA;letter-spacing:0.08em;margin-bottom:28px;">
      AEQUITAS BRIEFING // ENGLAND #01
    </div>
    <h1 style="font-size:64px;font-weight:800;letter-spacing:-0.03em;margin:0 0 18px 0;background:linear-gradient(180deg,#FFFFFF 30%,#94A3B8 100%);-webkit-background-clip:text;-webkit-text-fill-color:transparent;line-height:1.1;">
      The Sunday Transit Cliff
    </h1>
    <p style="font-size:22px;color:#94A3B8;max-width:700px;line-height:1.5;margin:0 0 38px 0;">
      How weekend bus cuts leave 41% of rural communities across England in complete transport isolation.
    </p>
    <div style="display:flex;gap:14px;font-size:13px;font-weight:600;color:#64748B;">
      <span style="background:rgba(255,255,255,0.06);padding:8px 16px;border-radius:8px;border:1px solid rgba(255,255,255,0.08);">BODS GTFS FEEDS</span>
      <span style="background:rgba(255,255,255,0.06);padding:8px 16px;border-radius:8px;border:1px solid rgba(255,255,255,0.08);">32,844 LSOAs</span>
      <span style="background:rgba(255,255,255,0.06);padding:8px 16px;border-radius:8px;border:1px solid rgba(255,255,255,0.08);">INDEX OF MULTIPLE DEPRIVATION</span>
    </div>
  `;
  document.body.appendChild(titleCard);

  // Add outro card
  const outroCard = document.createElement("div");
  outroCard.id = "outro-card";
  outroCard.innerHTML = `
    <div style="display:inline-flex;align-items:center;gap:8px;background:rgba(16,185,129,0.15);border:1px solid rgba(16,185,129,0.3);padding:6px 18px;border-radius:100px;font-size:12px;font-weight:700;color:#34D399;letter-spacing:0.08em;margin-bottom:28px;">
      OBJECTIVE PUBLIC SECTOR INTELLIGENCE
    </div>
    <h1 style="font-size:72px;font-weight:800;letter-spacing:-0.03em;margin:0 0 16px 0;color:#FFFFFF;line-height:1;">
      Aequitas
    </h1>
    <p style="font-size:22px;color:#94A3B8;max-width:650px;line-height:1.5;margin:0 0 36px 0;">
      Evidence-based transport equity briefings against official deprivation indices.
    </p>
    <div style="font-size:20px;font-weight:700;color:#60A5FA;background:rgba(37,99,235,0.12);border:1px solid rgba(59,130,246,0.3);padding:10px 28px;border-radius:12px;letter-spacing:0.02em;">
      aequitas.souravamseekar.com
    </div>
  `;
  document.body.appendChild(outroCard);
});

console.log("Starting choreographed camera director sequence...");

// HELPER: Move virtual cursor
async function moveCursor(x, y, duration = 800) {
  await page.evaluate(({ x, y, duration }) => {
    const cur = document.getElementById("virtual-cursor");
    cur.classList.add("visible");
    cur.style.transition = `left ${duration}ms cubic-bezier(0.2, 0.8, 0.2, 1), top ${duration}ms cubic-bezier(0.2, 0.8, 0.2, 1)`;
    cur.style.left = `${x}px`;
    cur.style.top = `${y}px`;
  }, { x, y, duration });
  await page.waitForTimeout(duration);
}

// HELPER: Trigger click animation
async function clickCursor() {
  await page.evaluate(() => {
    const ripple = document.getElementById("cursor-ripple");
    ripple.classList.remove("click");
    void ripple.offsetWidth;
    ripple.classList.add("click");
  });
  await page.waitForTimeout(400);
}

// HELPER: Set camera transform
async function setCamera(scale, translateX, translateY) {
  await page.evaluate(({ scale, translateX, translateY }) => {
    const cam = document.getElementById("director-camera");
    cam.style.transform = `scale(${scale}) translate(${translateX}px, ${translateY}px)`;
  }, { scale, translateX, translateY });
}

// HELPER: Update Callout
async function setCallout(pill, title, sub, isAlert = false, visible = true) {
  await page.evaluate(({ pill, title, sub, isAlert, visible }) => {
    const el = document.getElementById("callout-overlay");
    const p = document.getElementById("callout-pill");
    const t = document.getElementById("callout-title");
    const s = document.getElementById("callout-sub");
    if (!visible) {
      el.classList.remove("active");
      return;
    }
    p.textContent = pill;
    p.className = isAlert ? "callout-pill alert" : "callout-pill";
    t.textContent = title;
    s.textContent = sub;
    el.classList.add("active");
  }, { pill, title, sub, isAlert, visible });
}

// ==========================================
// SCENE 1: THE INTRO TITLE CARD (0s - 4.5s)
// ==========================================
console.log("Scene 1: Title Card intro...");
await page.waitForTimeout(4200);

// ==========================================
// SCENE 2: REVEAL DASHBOARD & BASELINE (4.5s - 10.5s)
// ==========================================
console.log("Scene 2: Revealing England dashboard & national baseline...");
await page.evaluate(() => {
  document.getElementById("title-card").classList.add("hide");
});
await page.waitForTimeout(600);

// Smooth zoom to 1.18x framing the metrics pair
await setCamera(1.18, 0, 40);
await setCallout("NATIONAL BASELINE", "50.8% Weekend Reduction Across England", "6,745 small areas (20.0%) have zero scheduled Sunday bus service");
await page.waitForTimeout(2500);

// Highlight the pair of metric cards
await page.evaluate(() => {
  const pair = document.querySelector(".service-metrics-pair");
  if (pair) pair.classList.add("director-highlight");
});
await page.waitForTimeout(2200);

// ==========================================
// SCENE 3: APPLYING THE FILTER (10.5s - 17.5s)
// ==========================================
console.log("Scene 3: Focusing on Area filter and clicking Rural...");
await page.evaluate(() => {
  const pair = document.querySelector(".service-metrics-pair");
  if (pair) pair.classList.remove("director-highlight");
});

// Zoom closer to filter bar with proper vertical framing
await setCamera(1.36, 0, 160);
await setCallout("CONTEXT FILTER", "Isolating Rural Geography", "Testing if low-density communities face higher weekend penalties");

// Move cursor smoothly to Area select dropdown using live bounding rect
const selCoords = await page.evaluate(() => {
  const sel = document.querySelector("select[aria-label='Area']");
  if (!sel) return { x: 800, y: 150 };
  const r = sel.getBoundingClientRect();
  return { x: r.left + r.width / 2, y: r.top + r.height / 2 };
});
await moveCursor(selCoords.x, selCoords.y, 1000);
await page.waitForTimeout(600);

// Hover and click animation
await clickCursor();
await page.evaluate(() => {
  const select = document.querySelector("select[aria-label='Area']");
  if (select) {
    select.classList.add("director-highlight");
    select.value = "rural";
    select.dispatchEvent(new Event("change", { bubbles: true }));
  }
});
await page.waitForTimeout(1400);

// ==========================================
// SCENE 4: THE DRAMATIC REVEAL (17.5s - 25.5s)
// ==========================================
console.log("Scene 4: Data updates - 41.2% Sunday deserts revealed!");
// Pull camera back to 1.18x to capture the dramatic number changes
await setCamera(1.18, 0, 30);
await page.evaluate(() => {
  const select = document.querySelector("select[aria-label='Area']");
  if (select) select.classList.remove("director-highlight");
  const pair = document.querySelector(".service-metrics-pair");
  if (pair) pair.classList.add("director-highlight-red");
});

await setCallout(
  "CRITICAL FINDING",
  "41.2% of Rural Areas Face Total Sunday Isolation",
  "2,291 rural communities in England lose all bus connectivity on Sundays (68.5% drop)",
  true
);
await page.waitForTimeout(5500);

// ==========================================
// SCENE 5: REGIONAL CHART DRILLDOWN (25.5s - 31.5s)
// ==========================================
console.log("Scene 5: Panning to regional departure comparison...");
await page.evaluate(() => {
  const pair = document.querySelector(".service-metrics-pair");
  if (pair) pair.classList.remove("director-highlight-red");
});

// Pan camera down to the chart
await setCamera(1.24, 0, -120);
await setCallout(
  "REGIONAL BREAKDOWN",
  "Severe Weekend Cliffs Across the North & Midlands",
  "East Midlands: 66% drop · Yorkshire: 66% drop · North West: 52% drop"
);

// Glide cursor over the regional chart
await moveCursor(640, 560, 1100);
await page.waitForTimeout(1000);
await moveCursor(860, 560, 1100);
await page.waitForTimeout(2000);

// ==========================================
// SCENE 6: OUTRO TRANSITION (31.5s - 36s)
// ==========================================
console.log("Scene 6: Outro card and closing...");
await setCallout("", "", "", false, false);
await setCamera(1.0, 0, 0);
await page.waitForTimeout(600);

await page.evaluate(() => {
  document.getElementById("outro-card").classList.add("show");
});
await page.waitForTimeout(3800);

console.log("Finishing recording session...");
await page.close();
await context.close();
await browser.close();

// Find recorded webm file
const files = fs.readdirSync(videoDir).filter(f => f.endsWith(".webm"));
if (!files.length) throw new Error("No webm video found in " + videoDir);
const rawWebmPath = path.join(videoDir, files[0]);
console.log("Raw recording saved at: " + rawWebmPath);

// Convert with FFmpeg to 60fps high-bitrate MP4
console.log("Encoding pristine 1080p 60fps MP4 with FFmpeg...");
const ffmpegCmd = `ffmpeg -y -i "${rawWebmPath}" -c:v libx264 -preset slow -crf 17 -r 60 -pix_fmt yuv420p -movflags +faststart "${finalMp4Path}"`;
execSync(ffmpegCmd, { stdio: "inherit" });

console.log("SUCCESS! Feature video generated at: " + finalMp4Path);
