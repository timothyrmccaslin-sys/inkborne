// Inkborne ambient motion for walkable POIs (forest, town). Systems / Ashley, v1.0.0.
// Grass sway, drifting mist, falling leaves and swaying paper lanterns, all in the
// sumi-e palette (SPEC section 5). Plain ES module, no dependencies, Canvas 2D only.
//
// Cheap by construction (iPad first):
//  - grass blades are batched into one stroke() per depth tier, culled to the view;
//  - mist bands are cached 256x64 textures tiled with drawImage (no per-frame gradients);
//  - leaves are pooled and capped, drawn as one fill() per tint with no save/restore;
//  - lantern glow is a cached sprite; the pendulum is a 1-D spring per lantern.
// Quality: 'full' | 'lite' (about half the work) | 'reduced' (frozen, static wash only;
// default when the OS asks for reduced motion). `auto: true` drops full -> lite when frames run slow.
//
// Coordinates are POI world pixels (the same space as pois/<id>.json). The camera is the
// world-space top-left of the 1280x720 logical view. The renderer is expected to have
// already applied its DPR / letterbox transform to ctx, as for every other scene draw.

export const AMBIENT_VERSION = '1.0.0';
export const AMBIENT_PROP_TYPES = ['grass', 'mist', 'leaves', 'lantern'];

const PAL = {
  paper: '236,230,216', ink: '27,24,19', wash1: '59,55,48', wash2: '109,103,91', wash3: '163,156,140',
  vermilion: '#b3261e', gold: '#b08a3e',
};

const mk = (w, h) => { const c = document.createElement('canvas'); c.width = Math.max(1, w | 0); c.height = Math.max(1, h | 0); return c; };
export function rng(seed) {
  let a = seed >>> 0;
  return () => { a |= 0; a = (a + 0x6D2B79F5) | 0; let t = Math.imul(a ^ (a >>> 15), 1 | a); t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t; return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };
}
const hashStr = (s) => { let h = 2166136261; for (let i = 0; i < s.length; i++) h = Math.imul(h ^ s.charCodeAt(i), 16777619); return h >>> 0; };

// Per-preset tuning. Used for wind and, when a POI has no ambient props, to lay out placeholders.
export const AMBIENT_PRESETS = {
  forest: { wind: 0.4, gustEvery: [6, 12], leafTint: ['#8a5a2e', '#6d675b', '#a3683a'], redLeaf: 0.06 },
  town:   { wind: 0.25, gustEvery: [8, 15], leafTint: ['#a39c8c', '#8a7a5c'], redLeaf: 0.0 },
};

// Placeholder layout for a POI that has no ambient props yet (procedural, seeded by POI id).
export function presetProps(kind, w, h, seed = hashStr(kind)) {
  const r = rng(seed), out = [];
  if (kind === 'forest') {
    out.push({ type: 'mist', y: h * 0.42, h: 150, alpha: 0.55, speed: 10, parallax: 0.5, layer: 'back' });
    out.push({ type: 'mist', y: h * 0.78, h: 110, alpha: 0.28, speed: 18, parallax: 1.15, layer: 'front' });
    for (let y = h * 0.5; y < h - 20; y += 70 + r() * 40) {
      let x = r() * 120;
      while (x < w) { const len = 120 + r() * 260; out.push({ type: 'grass', x, y: y + r() * 20, w: len, h: 20 + r() * 14 }); x += len + 60 + r() * 220; }
    }
    for (let x = 0; x < w; x += 480) out.push({ type: 'leaves', rect: [x, 0, 480, h * 0.92], rate: 0.5 + r() * 0.4 });
    out.push({ type: 'grass', x: 0, y: h - 6, w, h: 44, layer: 'front', density: 10 });
  } else if (kind === 'town') {
    out.push({ type: 'mist', y: h * 0.86, h: 90, alpha: 0.22, speed: 8, parallax: 1.1, layer: 'front' });
    for (let x = 140 + r() * 60; x < w - 60; x += 190 + r() * 90) out.push({ type: 'lantern', x, y: h * 0.33 + (r() - 0.5) * 30, len: 22 + r() * 18 });
    out.push({ type: 'grass', x: 0, y: h - 8, w: w * 0.3, h: 22, density: 8 });
    out.push({ type: 'grass', x: w * 0.72, y: h - 8, w: w * 0.28, h: 22, density: 8 });
    out.push({ type: 'leaves', rect: [w * 0.75, 0, w * 0.25, h * 0.9], rate: 0.25 });
  }
  return out;
}

export function createAmbient(opts = {}) {
  const view = { w: 1280, h: 720 };
  const reducedOS = typeof matchMedia === 'function' && matchMedia('(prefers-reduced-motion: reduce)').matches;
  let quality = opts.quality || (reducedOS ? 'reduced' : 'full');
  const auto = opts.auto !== false;
  const sfx = typeof opts.sfx === 'function' ? opts.sfx : null; // sfx('wind') / sfx('lantern'): SPEC ambient keys
  let preset = AMBIENT_PRESETS.forest, kind = 'forest', world = { w: 1280, h: 720 };
  let t = 0, slowT = 0, dtAvg = 1 / 60, lanternCue = 0;
  const tufts = { back: [], front: [] }, mists = [], leafSrc = [], lanterns = [], leaves = [];
  const wind = { base: 0.3, gust: 0, gt: 0, next: 6, dir: 1 };
  const tex = {};
  let player = null;

  // ---------- cached textures ----------
  function mistTex(i) {
    const k = 'm' + i; if (tex[k]) return tex[k];
    const W = 256, H = 64, c = mk(W, H), g = c.getContext('2d'), r = rng(911 + i * 131);
    for (let n = 0; n < 40; n++) {
      const x = r() * W, y = H * (0.32 + r() * 0.4), rx = 16 + r() * 42, ry = rx * (0.22 + r() * 0.2), a = 0.35 + r() * 0.35;
      for (const ox of [-W, 0, W]) {
        const gr = g.createRadialGradient(0, 0, 0, 0, 0, rx);
        gr.addColorStop(0, `rgba(${PAL.paper},${a})`); gr.addColorStop(1, `rgba(${PAL.paper},0)`);
        g.setTransform(1, 0, 0, ry / rx, x + ox, y); g.fillStyle = gr; g.beginPath(); g.arc(0, 0, rx, 0, 6.29); g.fill();
      }
    }
    g.setTransform(1, 0, 0, 1, 0, 0); g.lineCap = 'round';
    for (let n = 0; n < 14; n++) { // faint grey underside + dry-brush streaks so pale mist reads on pale paper
      const x = r() * W, y = H * (0.55 + r() * 0.15), l = 40 + r() * 80;
      g.strokeStyle = `rgba(${PAL.wash2},${0.06 + r() * 0.07})`; g.lineWidth = 1.5 + r() * 3;
      for (const ox of [-W, 0, W]) { g.beginPath(); g.moveTo(x + ox, y); g.quadraticCurveTo(x + ox + l / 2, y + 1 + r() * 3, x + ox + l, y); g.stroke(); }
    }
    g.globalCompositeOperation = 'destination-in';
    const fe = g.createLinearGradient(0, 0, 0, H);
    fe.addColorStop(0, 'rgba(0,0,0,0)'); fe.addColorStop(0.35, '#000'); fe.addColorStop(0.7, '#000'); fe.addColorStop(1, 'rgba(0,0,0,0)');
    g.fillStyle = fe; g.fillRect(0, 0, W, H);
    return (tex[k] = c);
  }
  function glowTex() {
    if (tex.glow) return tex.glow;
    const S = 128, c = mk(S, S), g = c.getContext('2d'), gr = g.createRadialGradient(S / 2, S / 2, 0, S / 2, S / 2, S / 2);
    gr.addColorStop(0, 'rgba(240,170,90,0.55)'); gr.addColorStop(0.35, 'rgba(220,120,60,0.22)'); gr.addColorStop(1, 'rgba(200,90,50,0)');
    g.fillStyle = gr; g.fillRect(0, 0, S, S);
    return (tex.glow = c);
  }

  // ---------- building from POI props ----------
  function load(poi, presetKind) {
    kind = presetKind || poi.ambient || poi.id || 'forest';
    preset = AMBIENT_PRESETS[kind] || AMBIENT_PRESETS.forest;
    world = { w: poi.w || view.w, h: poi.h || view.h };
    const seed = hashStr(String(poi.id || kind));
    let props = (poi.props || []).filter((p) => AMBIENT_PROP_TYPES.includes(p.type));
    if (!props.length && AMBIENT_PRESETS[kind]) props = presetProps(kind, world.w, world.h, seed);
    tufts.back.length = tufts.front.length = mists.length = leafSrc.length = lanterns.length = leaves.length = 0;
    const r = rng(seed ^ 0x5bd1e995);
    for (const p of props) {
      if (p.type === 'grass') {
        const n = Math.max(1, Math.round((p.w || 100) / 100 * (p.density || 14))), H = p.h || 26;
        const arr = tufts[p.layer === 'front' ? 'front' : 'back'];
        for (let i = 0; i < n; i++) {
          const blades = [], nb = 3 + ((r() * 3) | 0);
          for (let b = 0; b < nb; b++) blades.push({ dx: (r() - 0.5) * 14, h: H * (0.55 + r() * 0.6), lean: (r() - 0.5) * 0.5, tier: (r() * 3) | 0 });
          arr.push({ x: p.x + r() * (p.w || 100), y: p.y + (r() - 0.5) * 10, blades, ph: r() * 6.28, push: 0, h: H });
        }
      } else if (p.type === 'mist') {
        mists.push({ y: p.y, h: p.h || 120, a: p.alpha ?? 0.45, sp: p.speed ?? 12, par: p.parallax ?? 0.7, layer: p.layer === 'front' ? 'front' : 'back', tex: mists.length % 3, off: r() * 512 });
      } else if (p.type === 'leaves') {
        const [x, y, w, h] = p.rect || [p.x || 0, p.y || 0, p.w || 400, p.h || 400];
        leafSrc.push({ x, y, w, h, rate: p.rate ?? 0.8, acc: r(), tint: p.tint ? [p.tint] : preset.leafTint });
      } else if (p.type === 'lantern') {
        lanterns.push({ x: p.x, y: p.y, len: p.len || 28, s: p.size || 1, col: p.color || PAL.vermilion, th: (r() - 0.5) * 0.1, w: 0, ph: r() * 6.28, fl: 1, lit: p.lit !== false });
      }
    }
    for (const k of ['back', 'front']) tufts[k].sort((a, b) => a.y - b.y);
    wind.base = poi.wind ?? preset.wind; wind.gust = 0; wind.gt = 0; wind.next = 3 + r() * 4; t = 0;
    return api;
  }

  // ---------- simulation ----------
  const caps = () => quality === 'lite' ? { leaves: 16, bladeEvery: 2, mistLayers: 1 } : { leaves: 40, bladeEvery: 1, mistLayers: 2 };
  function inView(x, y, cam, m) { return x > cam.x - m && x < cam.x + view.w + m && y > cam.y - m && y < cam.y + view.h + m; }

  function update(dt, cam = { x: 0, y: 0 }, ctx = {}) {
    dt = Math.min(dt, 0.1);
    player = ctx.player || null;
    if (auto && quality === 'full') { dtAvg += (dt - dtAvg) * 0.05; slowT = dtAvg > 1 / 40 ? slowT + dt : 0; if (slowT > 3) quality = 'lite'; }
    if (quality === 'reduced') return;
    t += dt;
    // gusts: a swell every few seconds that drives grass, leaves, lanterns and mist together
    wind.next -= dt;
    if (wind.next <= 0) {
      const [a, b] = preset.gustEvery; wind.gt = 3; wind.next = a + Math.random() * (b - a);
      if (sfx) sfx('wind');
      lanternCue = 1;
    }
    wind.gt = Math.max(0, wind.gt - dt);
    const want = wind.gt > 0 ? Math.sin(Math.PI * (1 - wind.gt / 3)) : 0;
    wind.gust += (want - wind.gust) * Math.min(1, dt * 3);
    const W = wind.base + wind.gust;

    // grass: per-tuft push from the walking player, eased so it springs back
    if (player) for (const k of ['back', 'front']) for (const tf of tufts[k]) {
      if (!inView(tf.x, tf.y, cam, 40)) continue;
      const dx = tf.x - player.x, dy = tf.y - player.y; let target = 0;
      if (dx > -52 && dx < 52 && dy > -26 && dy < 26) target = Math.sign(dx || 1) * (1 - Math.abs(dx) / 52) * 0.9;
      tf.push += (target - tf.push) * Math.min(1, dt * (target ? 12 : 4));
    }

    // leaves: spawn only from sources overlapping the view; pooled, capped
    const cap = caps().leaves;
    for (const s of leafSrc) {
      if (s.x > cam.x + view.w || s.x + s.w < cam.x || s.y > cam.y + view.h || s.y + s.h < cam.y) continue;
      s.acc += dt * s.rate * (quality === 'lite' ? 0.5 : 1) * (1 + wind.gust * 1.5);
      while (s.acc >= 1) {
        s.acc -= 1; if (leaves.length >= cap) continue;
        const red = Math.random() < preset.redLeaf;
        leaves.push({ x: Math.max(s.x, cam.x - 40) + Math.random() * Math.min(s.w, view.w + 80), y: Math.max(s.y, cam.y - 20), gy: s.y + s.h * (0.6 + Math.random() * 0.4),
          vy: 22 + Math.random() * 16, sw: 0.8 + Math.random() * 1.4, ph: Math.random() * 6.28, rot: Math.random() * 6.28, sz: 4 + Math.random() * 3.5,
          col: red ? PAL.vermilion : s.tint[(Math.random() * s.tint.length) | 0], land: 0 });
      }
    }
    for (let i = leaves.length - 1; i >= 0; i--) {
      const L = leaves[i];
      if (L.land) { L.land += dt; if (L.land > 2.5) leaves.splice(i, 1); continue; }
      L.ph += dt * L.sw * 2.2;
      L.x += (Math.sin(L.ph) * 18 + W * 40) * dt; L.y += L.vy * dt * (0.7 + 0.3 * Math.cos(L.ph * 2));
      L.rot += dt * (1.2 + W) * Math.cos(L.ph);
      if (L.y >= L.gy) { L.y = L.gy; L.land = 0.0001; }
      else if (L.y > cam.y + view.h + 40 || L.x > cam.x + view.w + 80) leaves.splice(i, 1);
    }

    // lanterns: damped pendulum, driven by wind with a per-lantern phase; flame flicker
    let cue = false;
    for (const L of lanterns) {
      const g = 9.8 * 60 / Math.max(10, L.len * 3);
      const force = W * 0.9 * (0.55 + 0.45 * Math.sin(t * 0.8 + L.ph)) * wind.dir;
      L.w += (-g * Math.sin(L.th) - 1.6 * L.w + force) * dt; L.th += L.w * dt;
      L.fl = 0.82 + 0.1 * Math.sin(t * 9 + L.ph) + 0.08 * Math.sin(t * 23.7 + L.ph * 3);
      if (lanternCue && Math.abs(L.w) > 0.25 && inView(L.x, L.y, cam, 0)) cue = true;
    }
    if (cue && sfx) { sfx('lantern'); lanternCue = 0; }
    if (wind.gt <= 0) lanternCue = 0;
  }

  // ---------- drawing ----------
  const TIER = [ // back to front: pale wash, mid wash, ink
    { col: `rgba(${PAL.wash3},0.85)`, lw: 1.2 }, { col: `rgba(${PAL.wash2},0.9)`, lw: 1.5 }, { col: `rgba(${PAL.wash1},0.95)`, lw: 1.8 },
  ];
  function drawGrass(ctx, cam, list, thick) {
    if (!list.length) return;
    const W = quality === 'reduced' ? 0 : wind.base + wind.gust, every = caps().bladeEvery;
    ctx.lineCap = 'round';
    for (let tier = 0; tier < 3; tier++) {
      ctx.beginPath();
      let any = false;
      for (const tf of list) {
        const sx = tf.x - cam.x, sy = tf.y - cam.y;
        if (sx < -40 || sx > view.w + 40 || sy < -10 || sy > view.h + tf.h + 10) continue;
        const sway = quality === 'reduced' ? 0 : (W * 0.35) * (0.55 + 0.45 * Math.sin(t * 1.7 + tf.x * 0.011 + tf.ph)) + W * 0.12 * Math.sin(t * 3.1 + tf.ph);
        for (let i = 0; i < tf.blades.length; i += every) {
          const b = tf.blades[i]; if (b.tier !== tier) continue;
          const a = b.lean + sway + tf.push, bx = sx + b.dx, tipX = bx + Math.sin(a) * b.h, tipY = sy - Math.cos(a) * b.h;
          ctx.moveTo(bx - 1.2, sy); ctx.quadraticCurveTo(bx + Math.sin(a * 0.4) * b.h * 0.5, sy - b.h * 0.55, tipX, tipY);
          any = true;
        }
      }
      if (any) { ctx.strokeStyle = TIER[tier].col; ctx.lineWidth = TIER[tier].lw * thick; ctx.stroke(); }
    }
  }
  function drawMist(ctx, cam, layer) {
    const n = caps().mistLayers;
    for (const m of mists) {
      if (m.layer !== layer) continue;
      const sy = m.y - cam.y * (layer === 'front' ? 1 : 0.9) - m.h / 2;
      if (sy > view.h || sy + m.h < 0) continue;
      for (let k = 0; k < n; k++) {
        const tx = mistTex(m.tex + k), sc = m.h / tx.height, tw = tx.width * sc * 2.2;
        const drift = quality === 'reduced' ? 0 : t * m.sp * (k ? 0.6 : 1) * (1 + wind.gust * 1.5);
        let ox = -((m.off + k * 177 + drift + cam.x * m.par) % tw); if (ox > 0) ox -= tw;
        ctx.globalAlpha = m.a * (k ? 0.6 : 1);
        for (let x = ox; x < view.w; x += tw) ctx.drawImage(tx, x, sy + k * m.h * 0.18, tw, m.h);
      }
    }
    ctx.globalAlpha = 1;
  }
  function drawLeaves(ctx, cam) {
    if (!leaves.length || quality === 'reduced') return;
    const byCol = new Map();
    for (const L of leaves) { let a = byCol.get(L.col); if (!a) byCol.set(L.col, (a = [])); a.push(L); }
    for (const [col, arr] of byCol) {
      ctx.beginPath();
      for (const L of arr) {
        const x = L.x - cam.x, y = L.y - cam.y; if (x < -10 || x > view.w + 10 || y < -10 || y > view.h + 10) continue;
        const flip = L.land ? 0.45 : Math.abs(Math.cos(L.ph * 1.3)) * 0.8 + 0.2; // 3-D tumble: width shrinks as it turns edge-on
        const c = Math.cos(L.rot), s = Math.sin(L.rot), lx = L.sz, ly = L.sz * 0.42 * flip;
        ctx.moveTo(x + c * lx, y + s * lx);
        ctx.quadraticCurveTo(x - s * ly * 2, y + c * ly * 2, x - c * lx, y - s * lx);
        ctx.quadraticCurveTo(x + s * ly * 2, y - c * ly * 2, x + c * lx, y + s * lx);
      }
      ctx.globalAlpha = 0.85; ctx.fillStyle = col; ctx.fill();
    }
    // landed leaves fade by drawing a paper veil over them would cost more; instead they just expire.
    ctx.globalAlpha = 1;
  }
  function drawLanterns(ctx, cam) {
    if (!lanterns.length) return;
    const glow = glowTex();
    for (const L of lanterns) {
      const hx = L.x - cam.x, hy = L.y - cam.y; if (hx < -80 || hx > view.w + 80 || hy < -80 || hy > view.h + 80) continue;
      const th = quality === 'reduced' ? 0 : L.th, bx = hx + Math.sin(th) * L.len, by = hy + Math.cos(th) * L.len, s = L.s;
      if (L.lit) { // warm pool of light first, under the lantern
        const f = quality === 'reduced' ? 0.9 : L.fl, R = 70 * s * (0.9 + 0.1 * f);
        ctx.globalAlpha = 0.75 * f; ctx.drawImage(glow, bx - R, by + 8 * s - R, R * 2, R * 2); ctx.globalAlpha = 1;
      }
      ctx.strokeStyle = `rgb(${PAL.ink})`; ctx.lineWidth = 1.2; ctx.beginPath(); ctx.moveTo(hx, hy); ctx.lineTo(bx, by); ctx.stroke();
      // body: a rotated paper lantern built from transformed points (no save/restore)
      const c = Math.cos(th), sn = Math.sin(th), P = (x, y) => [bx + c * x + sn * y, by - sn * x + c * y];
      const w = 11 * s, h = 22 * s;
      ctx.beginPath();
      let p = P(-w * 0.55, 2); ctx.moveTo(p[0], p[1]);
      let q = P(-w * 1.15, h * 0.55); p = P(-w * 0.55, h); ctx.quadraticCurveTo(q[0], q[1], p[0], p[1]);
      p = P(w * 0.55, h); ctx.lineTo(p[0], p[1]);
      q = P(w * 1.15, h * 0.55); p = P(w * 0.55, 2); ctx.quadraticCurveTo(q[0], q[1], p[0], p[1]);
      ctx.closePath(); ctx.fillStyle = L.col; ctx.fill();
      ctx.strokeStyle = `rgba(${PAL.ink},0.8)`; ctx.lineWidth = 1.1; ctx.stroke();
      ctx.beginPath(); // ink caps and a centre rib
      p = P(-w * 0.6, 1); q = P(w * 0.6, 1); ctx.moveTo(p[0], p[1]); ctx.lineTo(q[0], q[1]);
      p = P(-w * 0.6, h + 1); q = P(w * 0.6, h + 1); ctx.moveTo(p[0], p[1]); ctx.lineTo(q[0], q[1]);
      ctx.lineWidth = 2.4; ctx.stroke();
      ctx.beginPath(); p = P(0, 3); q = P(0, h - 1); ctx.moveTo(p[0], p[1]); ctx.lineTo(q[0], q[1]);
      ctx.strokeStyle = `rgba(${PAL.ink},0.35)`; ctx.lineWidth = 1; ctx.stroke();
      if (L.lit) { // flame core showing through paper
        const f = quality === 'reduced' ? 0.9 : L.fl; p = P(0, h * 0.55);
        ctx.globalAlpha = 0.5 * f; ctx.fillStyle = '#f2c27a'; ctx.beginPath(); ctx.arc(p[0], p[1], w * 0.45, 0, 6.29); ctx.fill(); ctx.globalAlpha = 1;
      }
    }
  }

  // Back layer: behind characters and NPCs. Front layer: over them (near grass, near mist, leaves).
  function drawBack(ctx, cam = { x: 0, y: 0 }) { drawMist(ctx, cam, 'back'); drawLanterns(ctx, cam); drawGrass(ctx, cam, tufts.back, 1); }
  function drawFront(ctx, cam = { x: 0, y: 0 }) { drawGrass(ctx, cam, tufts.front, 1.6); drawLeaves(ctx, cam); drawMist(ctx, cam, 'front'); }

  const api = {
    load,
    setView(w, h) { view.w = w || 1280; view.h = h || 720; return api; },
    setQuality(q) { if (q === 'full' || q === 'lite' || q === 'reduced') { quality = q; slowT = 0; if (q === 'reduced') leaves.length = 0; } return api; },
    get quality() { return quality; },
    update, drawBack, drawFront,
    get wind() { return wind.base + wind.gust; },
    gust(strength = 1) { wind.gt = 3 * strength; lanternCue = 1; if (sfx) sfx('wind'); }, // e.g. on a scripted event
    get info() {
      let blades = 0; for (const k of ['back', 'front']) for (const tf of tufts[k]) blades += tf.blades.length;
      return { kind, quality, tufts: tufts.back.length + tufts.front.length, blades, mists: mists.length, lanterns: lanterns.length, leaves: leaves.length, leafSources: leafSrc.length, wind: +(wind.base + wind.gust).toFixed(2) };
    },
  };
  return api;
}
