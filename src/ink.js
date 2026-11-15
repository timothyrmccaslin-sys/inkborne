// Sumi-e brush helpers: paper, variable-width strokes, dry-brush, washes, seals, props.
// Everything is procedural so the demo runs with zero art files; painted art from the art
// team (SPEC section 5) replaces these per key via art.js. TODO(art): painted layers.
export const PAL = {
  paper: '#ece6d8', paperShade: '#d9d0bc', ink: '#1b1813', w1: '#3b3730', w2: '#6d675b', w3: '#a39c8c',
  red: '#b3261e', gold: '#b08a3e',
  ember: '#c2452d', tide: '#2f5d7c', gale: '#5f8a6a', stone: '#7a6a52', dawn: '#d9b45a', dusk: '#4b3b63',
};

export function rng(seed) { let s = (seed >>> 0) || 1; return () => { s ^= s << 13; s ^= s >>> 17; s ^= s << 5; return ((s >>> 0) % 100000) / 100000; }; }

export function canvas(w, h) { const c = document.createElement('canvas'); c.width = w; c.height = h; return c; }

/** Paper with fibres and mottling, tinted. Cached per size+tint. */
const paperCache = new Map();
export function paper(w, h, tint = PAL.paper, seed = 3) {
  const k = `${w}x${h}${tint}${seed}`; if (paperCache.has(k)) return paperCache.get(k);
  const c = canvas(w, h), x = c.getContext('2d'), r = rng(seed);
  x.fillStyle = tint; x.fillRect(0, 0, w, h);
  for (let i = 0; i < 70; i++) { // mottling
    const px = r() * w, py = r() * h, rad = 60 + r() * 260;
    const g = x.createRadialGradient(px, py, 0, px, py, rad);
    const a = 0.025 + r() * 0.04; g.addColorStop(0, r() < 0.5 ? `rgba(120,100,70,${a})` : `rgba(255,255,245,${a * 1.4})`); g.addColorStop(1, 'rgba(0,0,0,0)');
    x.fillStyle = g; x.fillRect(px - rad, py - rad, rad * 2, rad * 2);
  }
  x.lineCap = 'round';
  for (let i = 0; i < w * h / 900; i++) { // fibres
    const px = r() * w, py = r() * h, a = r() * Math.PI, l = 4 + r() * 16;
    x.strokeStyle = `rgba(90,75,50,${0.03 + r() * 0.06})`; x.lineWidth = 0.4 + r() * 0.8;
    x.beginPath(); x.moveTo(px, py); x.quadraticCurveTo(px + Math.cos(a) * l * 0.5 + r() * 3, py + Math.sin(a) * l * 0.5, px + Math.cos(a) * l, py + Math.sin(a) * l); x.stroke();
  }
  const v = x.createRadialGradient(w / 2, h / 2, Math.min(w, h) * 0.35, w / 2, h / 2, Math.max(w, h) * 0.75); // vignette
  v.addColorStop(0, 'rgba(0,0,0,0)'); v.addColorStop(1, 'rgba(70,55,30,0.18)'); x.fillStyle = v; x.fillRect(0, 0, w, h);
  paperCache.set(k, c); return c;
}

function catmull(pts, seg = 6) {
  if (pts.length < 3) return pts.slice();
  const out = [];
  for (let i = 0; i < pts.length - 1; i++) {
    const p0 = pts[i - 1] || pts[i], p1 = pts[i], p2 = pts[i + 1], p3 = pts[i + 2] || p2;
    for (let k = 0; k < seg; k++) {
      const t = k / seg, t2 = t * t, t3 = t2 * t;
      out.push([0.5 * (2 * p1[0] + (-p0[0] + p2[0]) * t + (2 * p0[0] - 5 * p1[0] + 4 * p2[0] - p3[0]) * t2 + (-p0[0] + 3 * p1[0] - 3 * p2[0] + p3[0]) * t3),
        0.5 * (2 * p1[1] + (-p0[1] + p2[1]) * t + (2 * p0[1] - 5 * p1[1] + 4 * p2[1] - p3[1]) * t2 + (-p0[1] + 3 * p1[1] - 3 * p2[1] + p3[1]) * t3)]);
    }
  }
  out.push(pts[pts.length - 1]); return out;
}

/**
 * Brush stroke along points. o: { w, color, alpha, taper:[start,end] (0..1), dry (0..1), seed, press(t)->mult, wobble }
 */
export function stroke(ctx, pts, o = {}) {
  const w = o.w ?? 8, color = o.color ?? PAL.ink, r = rng(o.seed ?? 1), dry = o.dry ?? 0.25, wob = o.wobble ?? 0.12;
  const ts = o.taper ? o.taper[0] : 0.18, te = o.taper ? o.taper[1] : 0.35;
  const p = catmull(pts, o.seg ?? 6); if (p.length < 2) return;
  let len = 0; const acc = [0]; for (let i = 1; i < p.length; i++) { len += Math.hypot(p[i][0] - p[i - 1][0], p[i][1] - p[i - 1][1]); acc.push(len); }
  const width = (i) => {
    const t = acc[i] / (len || 1);
    let m = 1; if (t < ts) m = 0.25 + 0.75 * Math.sin((t / ts) * Math.PI / 2); if (t > 1 - te) m *= Math.max(0.04, Math.cos(((t - (1 - te)) / te) * Math.PI / 2));
    if (o.press) m *= o.press(t);
    return w * m * (1 + (Math.sin(t * 17 + (o.seed ?? 1)) * wob));
  };
  const L = [], R = [];
  for (let i = 0; i < p.length; i++) {
    const a = p[Math.max(0, i - 1)], b = p[Math.min(p.length - 1, i + 1)];
    let nx = -(b[1] - a[1]), ny = b[0] - a[0]; const nl = Math.hypot(nx, ny) || 1; nx /= nl; ny /= nl;
    const hw = width(i) / 2; L.push([p[i][0] + nx * hw, p[i][1] + ny * hw]); R.push([p[i][0] - nx * hw, p[i][1] - ny * hw]);
  }
  ctx.save(); ctx.globalAlpha *= o.alpha ?? 1; ctx.fillStyle = color;
  ctx.beginPath(); ctx.moveTo(L[0][0], L[0][1]); for (const q of L) ctx.lineTo(q[0], q[1]); for (let i = R.length - 1; i >= 0; i--) ctx.lineTo(R[i][0], R[i][1]); ctx.closePath(); ctx.fill();
  if (o.bleed !== false && w > 3) { // wet edge bleed: faint wider halo
    ctx.globalAlpha *= 0.12; ctx.lineWidth = Math.max(1, w * 0.18); ctx.strokeStyle = color; ctx.lineJoin = 'round'; ctx.stroke();
  }
  ctx.restore();
  if (dry > 0 && w > 4) { // dry-brush streaks: bristle lines that break up toward the end
    ctx.save(); ctx.strokeStyle = o.paper ?? PAL.paper; ctx.lineCap = 'round';
    const n = Math.round(2 + dry * 5);
    for (let k = 0; k < n; k++) {
      const off = (r() - 0.5) * 0.8, start = Math.floor(p.length * (0.35 + r() * 0.4));
      ctx.globalAlpha = 0.35 + r() * 0.4; ctx.lineWidth = 0.6 + r() * w * 0.07;
      ctx.beginPath();
      for (let i = start; i < p.length; i++) { const x = L[i][0] + (R[i][0] - L[i][0]) * (0.5 + off), y = L[i][1] + (R[i][1] - L[i][1]) * (0.5 + off); i === start ? ctx.moveTo(x, y) : ctx.lineTo(x, y); }
      ctx.stroke();
    }
    ctx.restore();
  }
}

/** Soft ink wash blob. */
export function wash(ctx, x, y, rx, ry, color = PAL.ink, alpha = 0.15) {
  ctx.save(); ctx.translate(x, y); ctx.scale(1, ry / rx);
  const g = ctx.createRadialGradient(0, 0, 0, 0, 0, rx);
  g.addColorStop(0, color); g.addColorStop(0.6, color); g.addColorStop(1, 'rgba(0,0,0,0)');
  ctx.globalAlpha *= alpha; ctx.fillStyle = g; ctx.beginPath(); ctx.arc(0, 0, rx, 0, Math.PI * 2); ctx.fill(); ctx.restore();
}

/** Flat wash band (for mountains, ground) from a polygon, soft-faded downward. */
export function washPoly(ctx, pts, color, alpha, fadeTo) {
  ctx.save(); ctx.globalAlpha *= alpha;
  let minY = Infinity, maxY = -Infinity; for (const p of pts) { minY = Math.min(minY, p[1]); maxY = Math.max(maxY, p[1]); }
  const g = ctx.createLinearGradient(0, minY, 0, fadeTo ?? maxY); g.addColorStop(0, color); g.addColorStop(1, 'rgba(0,0,0,0)');
  ctx.fillStyle = g; ctx.beginPath(); ctx.moveTo(pts[0][0], pts[0][1]); for (const p of catmull(pts, 4)) ctx.lineTo(p[0], p[1]); ctx.closePath(); ctx.fill(); ctx.restore();
}

export function splat(ctx, x, y, s, color = PAL.ink, seed = 1, alpha = 0.9) {
  const r = rng(seed); ctx.save(); ctx.fillStyle = color; ctx.globalAlpha *= alpha;
  ctx.beginPath(); for (let i = 0; i <= 14; i++) { const a = i / 14 * Math.PI * 2, rr = s * (0.7 + r() * 0.5); i ? ctx.lineTo(x + Math.cos(a) * rr, y + Math.sin(a) * rr) : ctx.moveTo(x + Math.cos(a) * rr, y + Math.sin(a) * rr); } ctx.fill();
  for (let i = 0; i < 9; i++) { const a = r() * Math.PI * 2, d = s * (1.2 + r() * 1.6); ctx.beginPath(); ctx.arc(x + Math.cos(a) * d, y + Math.sin(a) * d, s * (0.05 + r() * 0.16), 0, Math.PI * 2); ctx.fill(); }
  ctx.restore();
}

/** Red hanko seal with a glyph. */
export function seal(ctx, x, y, s, text, color = PAL.red, alpha = 0.92) {
  ctx.save(); ctx.globalAlpha *= alpha; ctx.fillStyle = color;
  const r = rng(text.charCodeAt(0)); ctx.beginPath();
  ctx.moveTo(x - s / 2 + r() * 2, y - s / 2); ctx.lineTo(x + s / 2, y - s / 2 + r() * 2); ctx.lineTo(x + s / 2 - r() * 2, y + s / 2); ctx.lineTo(x - s / 2, y + s / 2 - r() * 2); ctx.closePath(); ctx.fill();
  ctx.globalCompositeOperation = 'destination-out'; ctx.font = `${Math.round(s * 0.62)}px Kanji, serif`; ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
  if (text.length > 1) { ctx.font = `${Math.round(s * 0.4)}px Kanji, serif`; ctx.fillText(text[0], x, y - s * 0.2); ctx.fillText(text[1], x, y + s * 0.22); } else ctx.fillText(text, x, y + s * 0.03);
  ctx.restore();
}

// ---------- props ----------
export function cedar(ctx, x, y, h, seed = 1, sway = 0, detail = 1, color = PAL.ink, alpha = 1) {
  const r = rng(seed); ctx.save(); ctx.globalAlpha *= alpha;
  stroke(ctx, [[x, y], [x + sway * 0.3, y - h * 0.5], [x + sway, y - h]], { w: h * 0.035 + 2, color, seed, dry: 0.5, taper: [0.02, 0.6] });
  const tiers = Math.round(5 + detail * 4);
  for (let i = 0; i < tiers; i++) {
    const t = 0.25 + i / tiers * 0.72, yy = y - h * t, span = h * (0.32 - t * 0.26) * (0.85 + r() * 0.3), sx = x + sway * t;
    for (const dir of [-1, 1]) {
      const droop = h * 0.04 * (1 - t);
      stroke(ctx, [[sx, yy], [sx + dir * span * 0.5, yy + droop * 0.4 - h * 0.01], [sx + dir * span, yy + droop]], { w: h * 0.018 + 1.5, color, seed: seed + i * 7 + dir, dry: 0.6, taper: [0.1, 0.7] });
      if (detail > 0.5) for (let k = 0; k < 3; k++) { const f = 0.3 + k * 0.25; stroke(ctx, [[sx + dir * span * f, yy + droop * f * 0.5], [sx + dir * span * (f + 0.06), yy + droop * f + h * 0.025]], { w: 2.2, color, seed: seed + k, dry: 0, alpha: 0.7 }); }
    }
  }
  ctx.restore();
}

export function grassTuft(ctx, x, y, h, t, seed = 1, color = PAL.ink, alpha = 0.8) {
  const r = rng(seed); const n = 4 + Math.floor(r() * 4);
  for (let i = 0; i < n; i++) {
    const lean = (r() - 0.5) * h * 0.8 + Math.sin(t * 1.6 + seed + i * 0.7) * h * 0.18, hh = h * (0.6 + r() * 0.5), bx = x + (r() - 0.5) * h * 0.5;
    stroke(ctx, [[bx, y], [bx + lean * 0.35, y - hh * 0.55], [bx + lean, y - hh]], { w: 2.4, color, seed: seed + i, dry: 0, taper: [0.02, 0.9], alpha, bleed: false });
  }
}

export function rock(ctx, x, y, s, seed = 1, color = PAL.ink) {
  const r = rng(seed);
  wash(ctx, x, y - s * 0.3, s * 0.9, s * 0.45, PAL.w2, 0.35);
  stroke(ctx, [[x - s, y], [x - s * 0.6, y - s * (0.5 + r() * 0.3)], [x + s * 0.1, y - s * (0.75 + r() * 0.2)], [x + s * 0.8, y - s * 0.4], [x + s, y]], { w: s * 0.12 + 2, color, seed, dry: 0.7 });
  stroke(ctx, [[x - s * 0.2, y - s * 0.6], [x, y - s * 0.3], [x - s * 0.1, y - s * 0.05]], { w: s * 0.05 + 1, color, seed: seed + 3, alpha: 0.7 });
}

export function lantern(ctx, x, y, s, t, seed = 1) {
  const fl = 0.75 + 0.25 * Math.sin(t * 9 + seed) * Math.sin(t * 5.3 + seed * 2);
  wash(ctx, x, y, s * 3.2, s * 3.2, '#e9a33c', 0.22 * fl);
  ctx.save(); ctx.fillStyle = `rgba(214,120,48,${0.55 + 0.35 * fl})`; ctx.beginPath(); ctx.ellipse(x, y, s * 0.7, s, 0, 0, Math.PI * 2); ctx.fill(); ctx.restore();
  stroke(ctx, [[x, y - s * 1.6], [x, y - s]], { w: 2, dry: 0 });
  stroke(ctx, [[x - s * 0.7, y - s * 0.95], [x + s * 0.7, y - s * 0.95]], { w: 3, dry: 0 });
  stroke(ctx, [[x - s * 0.6, y + s * 0.95], [x + s * 0.6, y + s * 0.95]], { w: 3, dry: 0 });
  for (const k of [-0.35, 0, 0.35]) stroke(ctx, [[x + s * k, y - s * 0.9], [x + s * k * 1.3, y], [x + s * k, y + s * 0.9]], { w: 1.2, dry: 0, alpha: 0.5, bleed: false });
}

export function house(ctx, x, y, w, h, seed = 1, opt = {}) {
  const r = rng(seed);
  wash(ctx, x, y - h * 0.35, w * 0.7, h * 0.5, PAL.w3, 0.25);
  // walls
  ctx.save(); ctx.fillStyle = 'rgba(244,238,224,0.85)'; ctx.fillRect(x - w * 0.42, y - h * 0.55, w * 0.84, h * 0.55); ctx.restore();
  stroke(ctx, [[x - w * 0.42, y], [x - w * 0.42, y - h * 0.56]], { w: 4, seed, dry: 0.3 });
  stroke(ctx, [[x + w * 0.42, y], [x + w * 0.42, y - h * 0.56]], { w: 4, seed: seed + 1, dry: 0.3 });
  for (const k of [-0.14, 0.14]) stroke(ctx, [[x + w * k, y], [x + w * k, y - h * 0.5]], { w: 2, seed: seed + 9, alpha: 0.6 });
  // shoji grid
  ctx.save(); ctx.strokeStyle = 'rgba(27,24,19,0.35)'; ctx.lineWidth = 1;
  for (let i = 1; i < 4; i++) { ctx.beginPath(); ctx.moveTo(x - w * 0.4, y - h * 0.12 * i); ctx.lineTo(x + w * 0.4, y - h * 0.12 * i); ctx.stroke(); }
  ctx.restore();
  // roof: sweeping curved eaves
  const ry = y - h * 0.55, top = y - h;
  ctx.save(); ctx.fillStyle = opt.roof ?? PAL.w1; ctx.globalAlpha = 0.85; ctx.beginPath();
  ctx.moveTo(x - w * 0.62, ry + 6); ctx.quadraticCurveTo(x - w * 0.4, ry - h * 0.05, x - w * 0.18, top); ctx.lineTo(x + w * 0.18, top); ctx.quadraticCurveTo(x + w * 0.4, ry - h * 0.05, x + w * 0.62, ry + 6); ctx.quadraticCurveTo(x, ry - h * 0.08, x - w * 0.62, ry + 6); ctx.fill(); ctx.restore();
  stroke(ctx, [[x - w * 0.66, ry + 2], [x - w * 0.35, ry - h * 0.06], [x, ry - h * 0.08], [x + w * 0.35, ry - h * 0.06], [x + w * 0.66, ry + 2]], { w: 6, seed: seed + 4, dry: 0.5, taper: [0.1, 0.1] });
  stroke(ctx, [[x - w * 0.2, top], [x + w * 0.2, top]], { w: 7, seed: seed + 5, dry: 0.4, taper: [0.05, 0.05] });
  if (opt.noren) { // shop curtain
    ctx.save(); ctx.fillStyle = opt.noren; ctx.globalAlpha = 0.9;
    for (let i = 0; i < 3; i++) ctx.fillRect(x - w * 0.24 + i * w * 0.165, y - h * 0.5, w * 0.15, h * 0.2 + Math.sin(opt.t * 2 + i) * 2); ctx.restore();
  }
  stroke(ctx, [[x - w * 0.5, y + 2], [x + w * 0.5, y + 2]], { w: 3, seed: seed + 6, alpha: 0.5 });
}
