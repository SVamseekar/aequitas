// Stage document: brand theme, fonts, and the layered scene graph the runtime animates.
// Brand values mirror frontend/src/index.css (paper #f4f0e8, ink #141311, accent #b84e1f,
// Geist + Instrument Serif). Change them there first, then here.
import fs from "node:fs";
import path from "node:path";

export const STAGE = {
  width: 1920,
  height: 1080,
  appWidth: 1440,
  appHeight: 900,
  titlebar: 40,
  winX: 240,
  winY: 70,
  anchorX: 960,
  anchorY: 500, // focus point sits slightly above centre so captions never cover it
  cursorTip: [5, 3],
  host: "aequitas.souravamseekar.com",
};

function fontData(frontendDir, rel) {
  const p = path.join(frontendDir, "node_modules", rel);
  if (!fs.existsSync(p)) throw new Error(`Font missing: ${p}. Run npm install in frontend/.`);
  return fs.readFileSync(p).toString("base64");
}

export const THEMES = ["paper", "ink", "field", "grid"];

export function buildStageHtml({ frontendDir, appOrigin, theme = "paper" }) {
  const geist = fontData(frontendDir, "@fontsource-variable/geist/files/geist-latin-wght-normal.woff2");
  const serif = fontData(frontendDir, "@fontsource/instrument-serif/files/instrument-serif-latin-400-normal.woff2");
  const serifItalic = fontData(frontendDir, "@fontsource/instrument-serif/files/instrument-serif-latin-400-italic.woff2");
  const S = STAGE;
  return `<!doctype html>
<html><head><meta charset="utf-8"><title>stage</title>
<style>
@font-face{font-family:"Geist";src:url(data:font/woff2;base64,${geist}) format("woff2");font-weight:100 900;font-display:block}
@font-face{font-family:"Instrument Serif";src:url(data:font/woff2;base64,${serif}) format("woff2");font-style:normal;font-display:block}
@font-face{font-family:"Instrument Serif";src:url(data:font/woff2;base64,${serifItalic}) format("woff2");font-style:italic;font-display:block}
:root{--paper:#f4f0e8;--ink:#141311;--accent:#b84e1f;--accent-deep:#8f3a14;
  --bg:#f4f0e8;--text:#141311;--muted:#5a554c;--num:#b84e1f;--em:#b84e1f;--label:#8f3a14;--rule:#b84e1f;
  --blob1:#f0d6bf;--blob2:#e6dccb;--blob3:#f5e3d1;--grid:none;--shadow-rgb:70,45,20;
  --cap-bg:rgba(255,252,247,.95);--cap-text:#141311;--cap-b:#b84e1f;--cap-border:rgba(20,19,17,.08);--hl:rgba(184,78,31,.15);
  --chrome:#ece7df;--chrome-text:#5a554c;--chrome-strong:#141311;--url-bg:rgba(255,255,255,.72);--dot:#d5cec3;
  --veil:rgba(244,240,232,.66);--dim:#f4f0e8;--glow:rgba(232,150,100,.42);--chip-bg:rgba(255,252,247,.85);--chip-text:#8f3a14}
/* Looks. Each stays inside the Aequitas palette: paper, ink, burnt orange, chart blue. */
body.theme-ink{--bg:#12110f;--text:#f4f0e8;--muted:#b7b0a4;--num:#ee8a52;--em:#ee8a52;--label:#f0a070;--rule:#ee8a52;
  --blob1:#4a2716;--blob2:#1c2a35;--blob3:#38200f;--shadow-rgb:0,0,0;
  --cap-bg:rgba(32,30,27,.94);--cap-text:#f4f0e8;--cap-b:#f09a66;--cap-border:rgba(255,255,255,.09);--hl:rgba(238,138,82,.24);
  --chrome:#25221e;--chrome-text:#a9a296;--chrome-strong:#f4f0e8;--url-bg:rgba(255,255,255,.06);--dot:#4a453e;
  --veil:rgba(18,17,15,.62);--dim:#12110f;--glow:rgba(238,138,82,.32);--chip-bg:rgba(255,255,255,.06);--chip-text:#f0a070}
body.theme-field{--bg:#b84e1f;--text:#fff7ef;--muted:rgba(255,239,226,.84);--num:#fff7ef;--em:#ffd8bd;--label:#fff1e4;--rule:#fff7ef;
  --blob1:#cc6431;--blob2:#a3421a;--blob3:#d4743f;--shadow-rgb:70,22,4;
  --hl:rgba(255,255,255,.22);--dim:#b84e1f;--glow:rgba(255,226,200,.5);--chip-bg:rgba(255,247,239,.95);--chip-text:#8f3a14}
body.theme-grid{--bg:#eceeef;--text:#14171a;--muted:#56606b;--blob1:#dde3e8;--blob2:#e9e6e0;--blob3:#efe2d6;
  --grid:linear-gradient(rgba(20,23,26,.055) 1px,transparent 1px),linear-gradient(90deg,rgba(20,23,26,.055) 1px,transparent 1px);
  --shadow-rgb:30,40,50;--chrome:#e1e5e8;--dot:#c5ccd2;--veil:rgba(236,238,239,.7);--dim:#eceeef;--glow:rgba(184,78,31,.26);--cap-border:rgba(20,23,26,.1)}
*{box-sizing:border-box;margin:0;padding:0}
html,body{width:${S.width}px;height:${S.height}px;overflow:hidden;background:var(--bg);color:var(--text);
  font-family:"Geist",ui-sans-serif,system-ui,sans-serif;-webkit-font-smoothing:antialiased;text-rendering:geometricPrecision}
#bg{position:absolute;inset:0;overflow:hidden}
#gridlines{position:absolute;inset:-48px;background-image:var(--grid);background-size:48px 48px}
.blob{position:absolute;border-radius:50%;filter:blur(130px)}
#b1{width:1150px;height:950px;background:var(--blob1);left:-260px;top:-380px;opacity:.85}
#b2{width:1050px;height:850px;background:var(--blob2);right:-300px;bottom:-400px;opacity:.9}
#b3{width:760px;height:760px;background:var(--blob3);left:860px;top:260px;opacity:.7}
#kinetic{position:absolute;inset:0;z-index:5;pointer-events:none}
.scene{position:absolute;inset:0;display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center;padding:0 140px;visibility:hidden}
.eyebrow{font-size:19px;font-weight:600;letter-spacing:.24em;text-transform:uppercase;color:var(--label)}
.headline{text-wrap:balance;font-family:"Instrument Serif",serif;font-weight:400;font-size:150px;line-height:1.02;letter-spacing:-.015em;margin-top:30px;max-width:1640px}
.headline em,.wordmark em{font-style:italic;color:var(--em)}
.word{display:inline-block}
.mask{display:inline-block;overflow:hidden;vertical-align:bottom;padding:0 .05em .16em;margin:0 -.05em -.16em}
.sub{text-wrap:balance;font-size:31px;line-height:1.42;color:var(--muted);margin-top:34px;max-width:1150px;font-weight:400}
.rule{width:132px;height:4px;background:var(--rule);margin-top:26px;transform-origin:0 50%;border-radius:2px}
/* Title layouts */
.scene.layout-left,.scene.layout-stack{align-items:flex-start;text-align:left;padding:0 170px}
.layout-left .headline{font-size:172px;max-width:1520px;text-wrap:pretty}
.layout-stack .headline{font-size:178px;line-height:.9;margin-top:22px}
.layout-stack .headline .word,.layout-stack .headline .mask{display:block}
.layout-left .sub,.layout-stack .sub{max-width:980px;text-wrap:pretty}
/* Stat layouts */
.stat-lead{text-wrap:balance;font-size:40px;line-height:1.3;color:var(--muted);max-width:1300px;font-weight:400}
.stat-num{font-family:"Instrument Serif",serif;font-size:300px;line-height:1;color:var(--num);margin:18px 0 6px;font-variant-numeric:tabular-nums;letter-spacing:-.02em;white-space:nowrap}
.stat-tail{text-wrap:balance;font-size:36px;line-height:1.35;color:var(--text);max-width:1300px;font-weight:450}
.stat-split{flex-direction:row;gap:72px;text-align:left}
.stat-split .stat-num{font-size:330px;margin:0}
.stat-split .col{display:flex;flex-direction:column;gap:26px;max-width:700px}
.stat-split .stat-lead,.stat-split .stat-tail{text-wrap:pretty}
.divider{width:3px;height:300px;background:var(--rule);border-radius:2px;transform-origin:50% 0;flex:none}
.vs-row{display:flex;align-items:flex-end;gap:84px;margin:30px 0 18px}
.vs-item{display:flex;flex-direction:column;align-items:center}
.vs-item .stat-num{font-size:220px;margin:8px 0 0}
.vs-item:first-child .stat-num{color:var(--text)}
.vs-row .divider{height:220px;margin-bottom:24px}
.stat-label{font-size:23px;font-weight:600;letter-spacing:.17em;text-transform:uppercase;color:var(--label)}
/* Quote */
.scene.quote{align-items:flex-start;text-align:left;padding:0 220px}
.qmark{font-family:"Instrument Serif",serif;font-size:260px;line-height:.6;color:var(--em);height:110px}
.qtext{font-family:"Instrument Serif",serif;font-size:74px;line-height:1.16;max-width:1420px;text-wrap:pretty;color:var(--text)}
.qtext mark{color:inherit;background-image:linear-gradient(var(--hl),var(--hl));background-repeat:no-repeat;background-position:0 86%;
  background-size:var(--qhl,0%) 38%;background-color:transparent;-webkit-box-decoration-break:clone;box-decoration-break:clone}
.qattr{margin-top:40px;font-size:22px;font-weight:600;letter-spacing:.17em;text-transform:uppercase;color:var(--label)}
.wordmark{font-family:"Instrument Serif",serif;font-weight:400;font-size:190px;line-height:1;margin-top:22px}
.url-chip{margin-top:40px;font-size:24px;font-weight:550;color:var(--chip-text);background:var(--chip-bg);border:1px solid var(--cap-border);
  padding:14px 30px;border-radius:999px;box-shadow:0 18px 40px -22px rgba(var(--shadow-rgb),.35)}
.source{position:absolute;left:160px;right:160px;bottom:46px;white-space:nowrap;overflow:hidden;font-size:17px;color:var(--muted);letter-spacing:.01em}
#camera{position:absolute;left:0;top:0;width:${S.width}px;height:${S.height}px;transform-origin:0 0;z-index:10}
#window{position:absolute;left:${S.winX}px;top:${S.winY}px;width:${S.appWidth}px;height:${S.appHeight + S.titlebar}px;border-radius:16px;overflow:hidden;
  background:#faf7f2;transform-origin:50% 100%;visibility:hidden;
  box-shadow:0 0 0 1px rgba(20,19,17,.08),0 60px 120px -40px rgba(var(--shadow-rgb),.42),0 24px 48px -28px rgba(var(--shadow-rgb),.32)}
#window.bleed{border-radius:0;box-shadow:none}
#window.bleed #titlebar{visibility:hidden}
#titlebar{height:${S.titlebar}px;background:var(--chrome);border-bottom:1px solid rgba(20,19,17,.07);display:flex;align-items:center;padding:0 18px;position:relative}
.dots{display:flex;gap:8px}.dots i{display:block;width:12px;height:12px;border-radius:50%;background:var(--dot)}
.url{position:absolute;left:50%;transform:translateX(-50%);display:flex;align-items:center;gap:8px;font-size:14px;color:var(--chrome-text);
  background:var(--url-bg);padding:5px 20px;border-radius:8px}
.url b{font-weight:500;color:var(--chrome-strong)}
iframe{display:block;width:${S.appWidth}px;height:${S.appHeight}px;border:0;background:#f4f0e8}
#veil{position:absolute;border-radius:14px;pointer-events:none;opacity:0;box-shadow:0 0 0 4000px rgba(244,240,232,.66)}
#ring{position:absolute;border-radius:14px;pointer-events:none;opacity:0;outline:3px solid #b84e1f;outline-offset:0}
#menu{pointer-events:none;position:absolute;background:#fffdf9;border-radius:10px;padding:6px;transform-origin:50% 0;visibility:hidden;
  box-shadow:0 14px 36px rgba(20,19,17,.18),0 0 0 1px rgba(20,19,17,.09);font-size:15px}
#menu .item{display:flex;align-items:center;gap:6px;height:34px;padding:0 10px;border-radius:6px;color:#141311;white-space:nowrap}
#menu .item .check{display:inline-block;width:16px;font-size:13px}
#menu .item.hot{background:#b84e1f;color:#fff}
#cursor{pointer-events:none;position:absolute;left:0;top:0;width:32px;height:32px;transform-origin:5px 3px;opacity:0;z-index:40;filter:drop-shadow(0 3px 6px rgba(0,0,0,.28))}
#ripple{pointer-events:none;position:absolute;left:0;top:0;width:56px;height:56px;border-radius:50%;border:2.5px solid #b84e1f;background:rgba(184,78,31,.12);opacity:0;z-index:39}
#dim{position:absolute;inset:0;background:var(--dim);opacity:0;z-index:20;pointer-events:none}
#lifts{position:absolute;inset:0;z-index:25;pointer-events:none}
.lift-item{position:absolute;left:0;top:0;transform-origin:50% 50%;visibility:hidden;background:#fff;overflow:hidden}
.shine{position:absolute;inset:0;visibility:hidden;pointer-events:none;
  background:linear-gradient(104deg,transparent 36%,rgba(255,255,255,.0) 40%,rgba(255,255,255,.62) 50%,rgba(255,255,255,0) 60%,transparent 64%)}
.lift-glow{position:absolute;left:0;top:0;visibility:hidden;border-radius:50%;filter:blur(40px);
  background:radial-gradient(closest-side,var(--glow),transparent)}
.lift-item img{display:block;width:100%;height:100%}
.lift-label{position:absolute;left:0;top:0;visibility:hidden;white-space:nowrap;font-size:24px;font-weight:600;letter-spacing:.16em;text-transform:uppercase;color:var(--label)}
#captions{position:absolute;inset:0;z-index:30;pointer-events:none}
.caption{position:absolute;left:50%;bottom:44px;max-width:1760px;white-space:nowrap;visibility:hidden;
  background:var(--cap-bg);border:1px solid var(--cap-border);border-radius:999px;padding:18px 36px;
  font-size:29px;font-weight:500;letter-spacing:-.005em;color:var(--cap-text);box-shadow:0 24px 50px -24px rgba(var(--shadow-rgb),.45)}
.caption b{color:var(--cap-b);font-weight:620}
.caption b{background-image:linear-gradient(rgba(184,78,31,.15),rgba(184,78,31,.15))}
.stat-tail b{background-image:linear-gradient(var(--hl),var(--hl))}
.caption b,.stat-tail b{background-repeat:no-repeat;background-position:0 88%;background-size:var(--hl-w,0%) 42%;padding:0 .1em;margin:0 -.1em;border-radius:.18em}
</style></head>
<body class="theme-${theme}">
<div id="bg"><div id="gridlines"></div><div class="blob" id="b1"></div><div class="blob" id="b2"></div><div class="blob" id="b3"></div></div>
<div id="kinetic"></div>
<div id="camera">
  <div id="window">
    <div id="titlebar"><div class="dots"><i></i><i></i><i></i></div>
      <div class="url"><svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.6"><rect x="4" y="11" width="16" height="10" rx="2"/><path d="M8 11V7a4 4 0 0 1 8 0v4"/></svg>
        <b>${S.host}</b><span id="url-path"></span></div></div>
    <iframe id="app" src="about:blank"></iframe>
    <div id="veil"></div><div id="ring"></div><div id="menu"></div>
  </div>
</div>
<div id="dim"></div>
<div id="lifts"></div>
<div id="captions"></div>
<svg id="cursor" viewBox="0 0 32 32"><path d="M5 3 L5 25 L10.5 19.6 L14.6 28.4 L18.4 26.7 L14.4 18.2 L22 18.2 Z" fill="#141311" stroke="#fff" stroke-width="2" stroke-linejoin="round"/></svg>
<div id="ripple"></div>
<script>window.__APP_ORIGIN=${JSON.stringify(appOrigin)};</script>
</body></html>`;
}
