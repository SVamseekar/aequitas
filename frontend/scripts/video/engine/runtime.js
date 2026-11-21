/* In-page renderer. Pure function of time: window.__render(t) draws frame t.
 * Reads the compiled timeline from window.__TL. No CSS transitions are used;
 * every visual property is computed here so frame capture is deterministic. */
(() => {
  const TL = window.__TL;
  const C = TL.constants;
  const $ = (id) => document.getElementById(id);

  const clamp = (x, a = 0, b = 1) => Math.min(b, Math.max(a, x));
  const prog = (t, a, b) => (b <= a ? (t >= a ? 1 : 0) : clamp((t - a) / (b - a)));
  const lerp = (a, b, x) => a + (b - a) * x;
  const inOut = (x) => (x < 0.5 ? 4 * x * x * x : 1 - Math.pow(-2 * x + 2, 3) / 2);
  const outQuart = (x) => 1 - Math.pow(1 - x, 4);
  const outExpo = (x) => (x >= 1 ? 1 : 1 - Math.pow(2, -10 * x));
  // Material 3 motion: emphasized decelerate (enter) and emphasized accelerate (exit).
  const bezier = (x1, y1, x2, y2) => (x) => {
    if (x <= 0) return 0;
    if (x >= 1) return 1;
    let u = x;
    for (let i = 0; i < 10; i++) {
      const fx = 3 * x1 * u * (1 - u) ** 2 + 3 * x2 * u * u * (1 - u) + u ** 3 - x;
      const d = 3 * x1 * (1 - u) ** 2 + 6 * (x2 - x1) * u * (1 - u) + 3 * (1 - x2) * u * u;
      if (Math.abs(fx) < 1e-5 || Math.abs(d) < 1e-6) break;
      u = clamp(u - fx / d);
    }
    return 3 * y1 * u * (1 - u) ** 2 + 3 * y2 * u * u * (1 - u) + u ** 3;
  };
  const emphDecel = bezier(0.05, 0.7, 0.1, 1);
  // Damped spring for spatial motion (Material 3 Expressive style: slight overshoot, quick settle).
  // x = seconds since the move started. zeta 0.8 ≈ 1.5% overshoot.
  const spring = (x, zeta = 0.8, omega = 9.5) => {
    if (x <= 0) return 0;
    const wd = omega * Math.sqrt(1 - zeta * zeta);
    return 1 - Math.exp(-zeta * omega * x) * (Math.cos(wd * x) + ((zeta * omega) / wd) * Math.sin(wd * x));
  };
  const emphAccel = bezier(0.3, 0, 0.8, 0.15);
  // Smooth in, hold, smooth out. Returns 0..1.
  const span = (t, start, end, fadeIn = 0.45, fadeOut = 0.35) =>
    t < start || t > end ? 0 : Math.min(outQuart(prog(t, start, start + fadeIn)), 1 - inOut(prog(t, end - fadeOut, end)));

  // ---------------------------------------------------------------- camera
  function camera(t) {
    let z = 1, fx = C.anchorX, fy = C.anchorY;
    for (const s of TL.shots) {
      if (t < s.at) break;
      const x = s.dur > 0 ? (s.ease === "in" ? emphAccel(prog(t, s.at, s.at + s.dur)) : inOut(prog(t, s.at, s.at + s.dur))) : 1;
      z = Math.exp(lerp(Math.log(z), Math.log(s.z), x));
      fx = lerp(fx, s.f[0], x);
      fy = lerp(fy, s.f[1], x);
    }
    return { z, fx, fy };
  }
  const toScreen = (cam, wx, wy) => [C.anchorX + cam.z * (wx - cam.fx), C.anchorY + cam.z * (wy - cam.fy)];
  const winToWorld = (p) => [C.winX + p[0], C.winY + p[1]];

  // ---------------------------------------------------------------- cursor
  function cursorPos(t) {
    let p = null;
    for (const k of TL.cursor.keys) {
      if (t < k.at) break;
      if (!p || k.dur <= 0) { p = k.p.slice(); continue; }
      const x = inOut(prog(t, k.at, k.at + k.dur));
      const from = k.from || p;
      const dx = k.p[0] - from[0], dy = k.p[1] - from[1];
      const len = Math.hypot(dx, dy) || 1;
      const arc = Math.sin(Math.PI * x) * Math.min(40, len * 0.12);
      p = [lerp(from[0], k.p[0], x) + (-dy / len) * arc, lerp(from[1], k.p[1], x) + (dx / len) * arc];
    }
    return p;
  }
  // Each key records where the previous move ended, so arcs start from rest.
  (function seal() {
    let last = null;
    for (const k of TL.cursor.keys) {
      if (last && k.dur > 0) k.from = last;
      last = k.p.slice();
    }
  })();

  // ---------------------------------------------------------------- setup
  const kineticEls = {};
  function el(tag, cls, html) {
    const e = document.createElement(tag);
    if (cls) e.className = cls;
    if (html != null) e.innerHTML = html;
    return e;
  }
  const q = (root, sel) => root.querySelector(sel);
  const qa = (root, sel) => [...root.querySelectorAll(sel)];
  for (const k of TL.kinetic) {
    const root = el("div", "scene");
    root.id = k.id;
    if (k.type === "title") {
      root.classList.add(`layout-${k.layout || "center"}`);
      root.append(el("div", "eyebrow", k.eyebrow));
      if (k.layout === "left") root.append(el("div", "rule"));
      const h = el("h1", "headline");
      for (const w of k.words) {
        const word = el("span", "word", w.html);
        if (k.reveal === "mask") { const m = el("span", "mask"); m.append(word); h.append(m, document.createTextNode(" ")); }
        else h.append(word, document.createTextNode(" "));
      }
      root.append(h);
      if (k.subtitle) root.append(el("p", "sub", k.subtitle));
    } else if (k.type === "stat") {
      const layout = k.layout || "center";
      const num = (v) => el("div", "stat-num", v.text);
      if (layout === "split") {
        root.classList.add("stat-split");
        const col = el("div", "col");
        col.append(el("p", "stat-lead", k.lead));
        if (k.tail) col.append(el("p", "stat-tail", k.tail));
        root.append(num(k.values[0]), el("div", "divider"), col);
      } else if (layout === "versus") {
        root.append(el("p", "stat-lead", k.lead));
        const row = el("div", "vs-row");
        k.values.forEach((v, j) => {
          const item = el("div", "vs-item");
          item.append(el("div", "stat-label", k.labels[j]), num(v));
          row.append(item);
          if (j === 0) row.append(el("div", "divider"));
        });
        root.append(row);
        if (k.tail) root.append(el("p", "stat-tail", k.tail));
      } else {
        root.append(el("p", "stat-lead", k.lead), num(k.values[0]));
        if (k.tail) root.append(el("p", "stat-tail", k.tail));
      }
      if (k.source) root.append(el("div", "source", k.source));
    } else if (k.type === "quote") {
      root.classList.add("quote");
      root.append(el("div", "qmark", "\u201C"), el("p", "qtext", `<mark>${k.text}</mark>`));
      if (k.attribution) root.append(el("div", "qattr", k.attribution));
      if (k.source) root.append(el("div", "source", k.source));
    } else if (k.type === "outro") {
      if (k.eyebrow) root.append(el("div", "eyebrow", k.eyebrow));
      root.append(el("h1", "wordmark", k.title));
      if (k.subtitle) root.append(el("p", "sub", k.subtitle));
      if (k.url) root.append(el("div", "url-chip", k.url));
      if (k.source) root.append(el("div", "source", k.source));
    }
    $("kinetic").append(root);
    kineticEls[k.id] = root;
  }
  const SHADOW = getComputedStyle(document.body).getPropertyValue("--shadow-rgb").trim() || "70,45,20";
  const liftEls = {};
  const glowEls = {};
  for (const L of TL.lifts) {
    const glow = el("div", "lift-glow");
    $("lifts").append(glow);
    glowEls[L.id] = glow;
    liftEls[L.id] = L.items.map((it) => {
      const box = el("div", "lift-item");
      box.style.width = it.w + "px";
      box.style.height = it.h + "px";
      box.style.borderRadius = L.radius + "px";
      const img = document.createElement("img");
      img.src = it.img;
      img.style.borderRadius = L.radius + "px";
      const shine = el("div", "shine");
      box.append(img, shine);
      $("lifts").append(box);
      let label = null;
      if (it.label) { label = el("div", "lift-label", it.label); $("lifts").append(label); }
      return { box, label, shine };
    });
  }
  for (const c of TL.captions) {
    const e = el("div", "caption", c.html);
    e.id = c.id;
    $("captions").append(e);
  }

  const fmt = (v, num) =>
    v.prefix + num.toLocaleString("en-GB", { minimumFractionDigits: v.decimals, maximumFractionDigits: v.decimals, useGrouping: v.grouping }) + v.suffix;

  function blurIn(e, x, dy = 36, blur = 14) {
    e.style.opacity = x;
    e.style.transform = `translateY(${(1 - x) * dy}px)`;
    e.style.filter = x >= 1 ? "none" : `blur(${(1 - x) * blur}px)`;
  }

  function renderKinetic(t) {
    for (const k of TL.kinetic) {
      const root = kineticEls[k.id];
      const visible = t >= k.start - 0.01 && t <= k.end + 0.01;
      root.style.visibility = visible ? "visible" : "hidden";
      if (!visible) continue;
      const lt = t - k.start;
      const exit = inOut(prog(t, k.end - 0.6, k.end));
      root.style.opacity = 1 - exit;
      const drift = 1 + 0.025 * prog(t, k.start, k.end); // slow push-in keeps long holds alive
      root.style.transform = `translateY(${-exit * 40}px) scale(${(1 - exit * 0.03) * drift})`;
      root.style.filter = exit > 0 ? `blur(${exit * 10}px)` : "none";
      const ein = (sel, a, b, dy = 24, bl = 8) => { const e = q(root, sel); if (e) blurIn(e, outQuart(prog(lt, a, b)), dy, bl); };
      const src = q(root, ".source");
      if (k.type === "title") {
        ein(".eyebrow", 0.15, 0.85, 18, 6);
        const rule = q(root, ".rule");
        if (rule) rule.style.transform = `scaleX(${emphDecel(prog(lt, 0.25, 1.05))})`;
        const words = qa(root, ".word");
        const mid = (words.length - 1) / 2;
        words.forEach((w, i) => {
          if (k.reveal === "mask") {
            // Each word slides up from behind its own mask.
            const p = emphDecel(prog(lt, 0.35 + i * 0.09, 1.3 + i * 0.09));
            w.style.transform = `translateY(${(1 - p) * 112}%)`;
          } else if (k.reveal === "focus") {
            // Depth reveal: words come into focus from the centre outwards.
            const p = emphDecel(prog(lt, 0.3 + Math.abs(i - mid) * 0.14, 1.5 + Math.abs(i - mid) * 0.14));
            w.style.opacity = clamp(p * 1.4);
            w.style.transform = `scale(${1.28 - 0.28 * p})`;
            w.style.filter = p >= 1 ? "none" : `blur(${(1 - p) * 18}px)`;
          } else blurIn(w, outExpo(prog(lt, 0.45 + i * 0.11, 1.45 + i * 0.11)), 60, 16);
        });
        ein(".sub", 1.35, 2.15);
      } else if (k.type === "stat") {
        ein(".stat-lead", 0.2, 0.9);
        qa(root, ".stat-num").forEach((n, j) => {
          const d = j * 0.4;
          const v = k.values[j];
          n.style.opacity = outQuart(prog(lt, 0.55 + d, 1.1 + d));
          n.style.transform = `scale(${0.9 + 0.1 * spring(lt - 0.55 - d, 0.62, 8)})`;
          const cx = outExpo(prog(lt, 0.6 + d, 2.0 + d));
          n.textContent = cx >= 1 || v.num == null ? v.text : fmt(v, v.num * cx);
        });
        qa(root, ".stat-label").forEach((l, j) => blurIn(l, outQuart(prog(lt, 0.5 + j * 0.4, 1.1 + j * 0.4)), 14, 4));
        const div = q(root, ".divider");
        if (div) div.style.transform = `scaleY(${emphDecel(prog(lt, 0.45, 1.3))})`;
        const tail = q(root, ".stat-tail");
        if (tail) {
          blurIn(tail, outQuart(prog(lt, 1.9, 2.6)), 24, 8);
          tail.style.setProperty("--hl-w", `${emphDecel(prog(lt, 2.4, 3.2)) * 100}%`);
        }
      } else if (k.type === "quote") {
        ein(".qmark", 0.1, 0.7, 30, 6);
        const qt = q(root, ".qtext");
        blurIn(qt, outQuart(prog(lt, 0.35, 1.25)), 30, 10);
        qt.style.setProperty("--qhl", `${emphDecel(prog(lt, 1.2, 2.8)) * 100}%`);
        ein(".qattr", 1.5, 2.1, 14, 4);
      } else if (k.type === "outro") {
        ein(".eyebrow", 0.2, 0.9, 18, 6);
        const wm = q(root, ".wordmark");
        blurIn(wm, outExpo(prog(lt, 0.35, 1.5)), 50, 16);
        ein(".sub", 0.9, 1.6);
        ein(".url-chip", 1.25, 1.95, 20, 6);
      }
      if (src) src.style.opacity = 0.9 * outQuart(prog(lt, k.type === "outro" ? 1.6 : 2.2, k.type === "outro" ? 2.3 : 2.9));
    }
  }

  function screenRectAt(time, r) {
    const cam = camera(time);
    const [x1, y1] = toScreen(cam, ...winToWorld([r.x, r.y]));
    const [x2, y2] = toScreen(cam, ...winToWorld([r.x + r.w, r.y + r.h]));
    return { cx: (x1 + x2) / 2, cy: (y1 + y2) / 2, w: x2 - x1 };
  }

  // Returns how far the window is pushed back (0..1) by an active lift.
  function renderLifts(t) {
    let recede = 0;
    for (const L of TL.lifts) {
      const els = liftEls[L.id];
      const active = t >= L.start && t <= L.end;
      if (!active) { glowEls[L.id].style.visibility = "hidden"; for (const e of els) { e.box.style.visibility = "hidden"; if (e.label) e.label.style.visibility = "hidden"; } continue; }
      recede = Math.max(recede, emphDecel(prog(t, L.start, L.start + 0.8)) * (1 - emphAccel(prog(t, L.end - 0.7, L.end - 0.05))));
      const from = screenRectAt(L.start, L.rect);
      const back = screenRectAt(L.end, L.rect);
      {
        const g = glowEls[L.id];
        const ga = recede;
        const xs = L.items.map((it) => it.to.cx), ys = L.items.map((it) => it.to.cy);
        const gw = Math.max(...L.items.map((it) => it.w * it.to.s)) * (L.items.length > 1 && new Set(ys).size === 1 ? L.items.length : 1) + 300;
        const gh = (Math.max(...ys) - Math.min(...ys)) + Math.max(...L.items.map((it) => it.h * it.to.s)) + 300;
        g.style.visibility = ga > 0.01 ? "visible" : "hidden";
        g.style.opacity = ga;
        g.style.width = gw + "px"; g.style.height = gh + "px";
        g.style.transform = `translate(${(Math.min(...xs) + Math.max(...xs)) / 2}px, ${(Math.min(...ys) + Math.max(...ys)) / 2}px) translate(-50%, -50%) scale(${0.85 + 0.15 * ga})`;
      }
      L.items.forEach((it, k) => {
        const { box, label } = els[k];
        const up = spring(t - L.start - it.delay, 0.8, 8.5); // may overshoot ~1.5%: lands with weight
        const down = emphAccel(prog(t, L.end - 0.7 + it.delay * 0.5, L.end - 0.05));
        const s0 = from.w / it.w, sE = back.w / it.w;
        let cx, cy, sc;
        if (down > 0) { cx = lerp(it.to.cx, back.cx, down); cy = lerp(it.to.cy, back.cy, down); sc = lerp(it.to.s, sE, down); }
        else { cx = lerp(from.cx, it.to.cx, up); cy = lerp(from.cy, it.to.cy, up); sc = lerp(s0, it.to.s, up); }
        const a = clamp(up) * (1 - down);
        const tilt = Math.sin(Math.PI * clamp(up)) * (1 - down) * -7;
        const sp = inOut(prog(t, L.start + it.delay + 0.8, L.start + it.delay + 1.7));
        els[k].shine.style.visibility = sp > 0 && sp < 1 && down === 0 ? "visible" : "hidden";
        els[k].shine.style.transform = `translateX(${-120 + 240 * sp}%)`;
        box.style.visibility = "visible";
        box.style.opacity = k === 0 ? 1 : clamp(up * 4);
        box.style.transform = `translate(${cx}px, ${cy}px) translate(-50%, -50%) perspective(1800px) rotateX(${tilt}deg) scale(${sc})`;
        box.style.boxShadow = `0 ${(46 * a) / sc}px ${(110 * a) / sc}px rgba(${SHADOW},${0.34 * a}), 0 ${(10 * a) / sc}px ${(26 * a) / sc}px rgba(${SHADOW},${0.18 * a})`;
        if (label) {
          const la = clamp((a - 0.65) / 0.35);
          label.style.visibility = la > 0 ? "visible" : "hidden";
          label.style.opacity = la;
          label.style.transform = `translate(${cx}px, ${cy - (it.h * sc) / 2 - 22}px) translate(-50%, -100%) translateY(${(1 - la) * 10}px)`;
        }
      });
    }
    return recede;
  }

  function renderWindow(t, recede = 0, cam = null) {
    const w = $("window");
    const sp = TL.windowSpans.find((s) => t >= s.enterStart && t <= s.exitEnd);
    if (!sp) { w.style.visibility = "hidden"; return; }
    w.style.visibility = "visible";
    $("url-path").textContent = sp.urlPath;
    w.classList.toggle("bleed", sp.frame === "bleed");
    const a = outExpo(prog(t, sp.enterStart, sp.enterEnd));
    const b = inOut(prog(t, sp.exitStart, sp.exitEnd));
    const zoomOut = sp.exit === "zoom";
    const y = (1 - a) * 240 - (zoomOut ? 0 : b * 40);
    const rot = (1 - a) * 18;
    const sc = lerp(0.9, 1, a) * (zoomOut ? 1 : lerp(1, 0.94, b));
    w.style.opacity = Math.min(outQuart(prog(t, sp.enterStart, sp.enterStart + 0.5)), 1 - b);
    // "tilt": the window sits at a 3D angle in wide shots and flattens as the camera pushes in or a card lifts.
    const tilt = sp.frame === "tilt" && cam ? clamp((1.12 - cam.z) / 0.12) * (1 - recede) : 0;
    w.style.transform = `translateY(${y}px) perspective(2400px) rotateX(${rot + 7 * tilt}deg) rotateY(${-15 * tilt}deg) scale(${sc * (1 - 0.06 * tilt)})`;
    const blur = Math.max(b * (zoomOut ? 16 : 8), recede * 9);
    w.style.filter = blur > 0.01 ? `blur(${blur}px)` : "none";
  }

  function renderSpot(t) {
    const veil = $("veil"), ring = $("ring");
    let best = null, alpha = 0;
    for (const s of TL.spots) {
      const a = span(t, s.start, s.end, 0.5, 0.4);
      if (a > alpha) { alpha = a; best = s; }
    }
    if (!best || alpha <= 0) { veil.style.opacity = 0; ring.style.opacity = 0; return; }
    const r = best.rect;
    for (const e of [veil, ring]) {
      e.style.left = r.x + "px"; e.style.top = r.y + "px";
      e.style.width = r.w + "px"; e.style.height = r.h + "px";
    }
    veil.style.opacity = alpha;
    if (best.ring) {
      const lt = t - best.start;
      const pulse = 1 + 0.5 * Math.max(0, Math.sin(Math.min(lt - 0.6, Math.PI) * 1)) * (lt > 0.6 && lt < 0.6 + Math.PI ? 1 : 0);
      ring.style.opacity = alpha;
      ring.style.boxShadow = `0 0 0 ${6 * pulse - 6}px rgba(184,78,31,0.18), 0 0 ${28 * pulse}px rgba(184,78,31,0.35)`;
    } else {
      ring.style.opacity = 0;
    }
  }

  function renderMenu(t) {
    const m = $("menu");
    const menu = TL.menus.find((x) => t >= x.open && t <= x.close + 0.2);
    if (!menu) { m.style.opacity = 0; m.style.visibility = "hidden"; return; }
    if (m.dataset.id !== menu.id) {
      m.dataset.id = menu.id;
      m.innerHTML = menu.items.map((label, i) => `<div class="item"><span class="check">${i === menu.current ? "✓" : ""}</span>${label}</div>`).join("");
      m.style.left = menu.rect.x + "px";
      m.style.top = menu.rect.y + "px";
      m.style.width = menu.rect.w + "px";
    }
    m.style.visibility = "visible";
    const a = outQuart(prog(t, menu.open, menu.open + 0.18));
    const b = inOut(prog(t, menu.close, menu.close + 0.15));
    m.style.opacity = a * (1 - b);
    m.style.transform = `translateY(${(1 - a) * -6}px) scaleY(${0.94 + 0.06 * a})`;
    [...m.children].forEach((it, i) => it.classList.toggle("hot", t >= menu.hotFrom && i === menu.hot));
  }

  function renderCursor(t, cam) {
    const cur = $("cursor"), rip = $("ripple");
    let vis = 0;
    for (const v of TL.cursor.vis) vis = Math.max(vis, span(t, v.start, v.end, 0.3, 0.35));
    const p = cursorPos(t);
    if (!p || vis <= 0) { cur.style.opacity = 0; rip.style.opacity = 0; return null; }
    const [sx, sy] = toScreen(cam, ...winToWorld(p));
    let press = 1, ripple = null;
    for (const c of TL.cursor.clicks) {
      const d = t - c;
      if (Math.abs(d) < 0.09) press = 0.82;
      if (d >= 0 && d < 0.55) ripple = d / 0.55;
    }
    cur.style.opacity = vis;
    cur.style.transform = `translate(${sx - C.cursorTip[0]}px, ${sy - C.cursorTip[1]}px) scale(${press})`;
    if (ripple != null) {
      rip.style.opacity = (1 - ripple) * 0.9;
      rip.style.transform = `translate(${sx - 28}px, ${sy - 28}px) scale(${0.3 + ripple * 1.2})`;
    } else rip.style.opacity = 0;
    return [sx, sy];
  }

  function renderCaptions(t) {
    for (const c of TL.captions) {
      const e = $(c.id);
      const a = span(t, c.start, c.end, 0.45, 0.3);
      e.style.visibility = a > 0 ? "visible" : "hidden";
      e.style.opacity = a;
      e.style.transform = `translateX(-50%) translateY(${(1 - a) * 18}px)`;
      e.style.filter = a < 1 ? `blur(${(1 - a) * 6}px)` : "none";
      e.style.setProperty("--hl-w", `${emphDecel(prog(t, c.start + 0.4, c.start + 1.15)) * 100}%`);
    }
  }

  function renderBackground(t) {
    $("b1").style.transform = `translate(${Math.sin(t * 0.21) * 70}px, ${Math.cos(t * 0.17) * 50}px)`;
    $("b2").style.transform = `translate(${Math.cos(t * 0.19) * 80}px, ${Math.sin(t * 0.23) * 60}px)`;
    $("b3").style.transform = `translate(${Math.sin(t * 0.13 + 1) * 90}px, ${Math.cos(t * 0.11) * 70}px)`;
  }

  window.__render = (t) => {
    const cam = camera(t);
    $("camera").style.transform = `translate(${C.anchorX - cam.z * cam.fx}px, ${C.anchorY - cam.z * cam.fy}px) scale(${cam.z})`;
    renderBackground(t);
    renderKinetic(t);
    const recede = renderLifts(t);
    renderWindow(t, recede, cam);
    $("dim").style.opacity = recede * 0.55;
    renderSpot(t);
    renderMenu(t);
    renderCaptions(t);
    const cursor = renderCursor(t, cam);
    return { cursor, cam };
  };
  // On-screen geometry of everything that can move (not the slow background drift). Comparing two
  // instants gives the real pixel displacement, including scale and 3D tilt, for motion-blur sampling.
  const MOVERS = "#window,#cursor,#ripple,#menu,#veil,#ring,.lift-item,.lift-label,.scene .word,.scene > *,.caption";
  window.__motionRects = (t) => {
    window.__render(t);
    const out = [];
    for (const e of document.querySelectorAll(MOVERS)) {
      const cs = getComputedStyle(e);
      if (cs.visibility === "hidden" || Number(cs.opacity) < 0.02) { out.push(0, 0, 0, 0); continue; }
      const r = e.getBoundingClientRect();
      out.push(r.left, r.top, r.right, r.bottom);
    }
    return out;
  };

  // Screen rect of a window-space rect at time t (for QA).
  window.__screenRect = (t, r) => {
    const cam = camera(t);
    const [x1, y1] = toScreen(cam, ...winToWorld([r.x, r.y]));
    const [x2, y2] = toScreen(cam, ...winToWorld([r.x + r.w, r.y + r.h]));
    return { x: x1, y: y1, w: x2 - x1, h: y2 - y1 };
  };

  // Bounding boxes of visible text blocks at time t (for safe-area QA).
  window.__visibleText = (t) => {
    window.__render(t);
    const out = [];
    const pick = document.querySelectorAll(".scene > *, .caption, .lift-label");
    for (const e of pick) {
      const cs = getComputedStyle(e);
      if (cs.visibility === "hidden" || Number(cs.opacity) < 0.5) continue;
      let p = e.parentElement, hidden = false;
      while (p && p !== document.body) {
        const ps = getComputedStyle(p);
        if (ps.visibility === "hidden" || Number(ps.opacity) < 0.5) { hidden = true; break; }
        p = p.parentElement;
      }
      if (hidden) continue;
      const r = e.getBoundingClientRect();
      out.push({ cls: e.className, scene: e.closest(".scene")?.className || "", text: e.textContent.slice(0, 60), x: r.x, y: r.y, w: r.width, h: r.height, overflow: getComputedStyle(e).whiteSpace === "nowrap" && e.scrollWidth > e.clientWidth + 2 });
    }
    return out;
  };
})();
