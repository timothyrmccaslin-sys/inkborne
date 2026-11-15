// Text + panel helpers, and the flat string map (data/strings.json, Jamie).
import { PAL, stroke, wash, seal } from './ink.js';
let STR = {};
export function setStrings(s) { STR = s || {}; }
let SRC = () => 'touch';
export function setInputSource(f) { SRC = f; }
const GLYPH = { touch: { confirm: 'A', cancel: 'B', menu: '☰' }, pad: { confirm: 'A', cancel: 'B', menu: 'Start' }, keyboard: { confirm: 'Enter', cancel: 'Esc', menu: 'Tab' } };
export function glyph(k) { return (GLYPH[SRC()] || GLYPH.touch)[k]; }
export function T(key, vars = {}, fallback) {
  let s = STR[key] ?? fallback ?? key;
  return s.replace(/\{(\w+)\}/g, (m, k) => (vars[k] ?? (k === 'gauge' ? STR['battle.gauge.label'] : (k === 'confirm' || k === 'cancel' || k === 'menu') ? glyph(k) : m)));
}
export const FONT = { title: '"Marker", serif', body: '"Hand", "Trebuchet MS", sans-serif', kanji: 'Kanji, serif' };
export function text(ctx, s, x, y, o = {}) {
  ctx.save(); ctx.font = `${o.size ?? 22}px ${o.font ?? FONT.body}`; ctx.fillStyle = o.color ?? PAL.ink; ctx.textAlign = o.align ?? 'left'; ctx.textBaseline = o.base ?? 'alphabetic';
  if (o.alpha != null) ctx.globalAlpha *= o.alpha;
  if (o.shadow) { ctx.fillStyle = o.shadow; ctx.fillText(s, x + 1.5, y + 1.5); ctx.fillStyle = o.color ?? PAL.ink; }
  ctx.fillText(s, x, y); ctx.restore();
}
export function wrap(ctx, s, maxW, size, font = FONT.body) {
  ctx.save(); ctx.font = `${size}px ${font}`; const out = []; let line = '';
  for (const w of s.split(' ')) { const tst = line ? line + ' ' + w : w; if (ctx.measureText(tst).width > maxW && line) { out.push(line); line = w; } else line = tst; }
  if (line) out.push(line); ctx.restore(); return out;
}
/** Paper panel with brushed border. */
export function panel(ctx, x, y, w, h, o = {}) {
  ctx.save(); ctx.fillStyle = o.fill ?? 'rgba(240,234,220,0.93)'; ctx.globalAlpha *= o.alpha ?? 1;
  ctx.beginPath(); ctx.moveTo(x + 6, y); ctx.lineTo(x + w - 4, y + 3); ctx.lineTo(x + w, y + h - 5); ctx.lineTo(x + 3, y + h); ctx.closePath(); ctx.fill();
  ctx.restore();
  const s = o.seed ?? 1;
  stroke(ctx, [[x - 4, y + 2], [x + w * 0.5, y - 1], [x + w + 6, y + 3]], { w: o.bw ?? 5, seed: s, dry: 0.6, taper: [0.05, 0.25] });
  stroke(ctx, [[x + w + 2, y - 2], [x + w + 1, y + h * 0.5], [x + w - 1, y + h + 4]], { w: (o.bw ?? 5) * 0.8, seed: s + 1, dry: 0.6, taper: [0.05, 0.3] });
  stroke(ctx, [[x + w + 4, y + h], [x + w * 0.5, y + h + 2], [x - 6, y + h - 1]], { w: o.bw ?? 5, seed: s + 2, dry: 0.6, taper: [0.05, 0.25] });
  stroke(ctx, [[x + 1, y + h + 3], [x - 1, y + h * 0.5], [x + 2, y - 3]], { w: (o.bw ?? 5) * 0.8, seed: s + 3, dry: 0.6, taper: [0.05, 0.3] });
}
export function bar(ctx, x, y, w, h, frac, color, o = {}) {
  ctx.save(); ctx.fillStyle = 'rgba(27,24,19,0.15)'; ctx.fillRect(x, y, w, h); ctx.fillStyle = color; ctx.fillRect(x, y, w * Math.max(0, Math.min(1, frac)), h);
  if (o.glow) { ctx.globalAlpha = 0.3 + 0.3 * Math.sin(o.t * 6); ctx.fillStyle = '#fff1c8'; ctx.fillRect(x, y, w, h); }
  ctx.restore(); stroke(ctx, [[x - 2, y + h + 1], [x + w + 2, y + h + 1]], { w: 2, dry: 0, alpha: 0.6, bleed: false });
}
/** Menu list with a red brush cursor. items: [{label, disabled, sub}] */
export function menu(ctx, items, sel, x, y, o = {}) {
  const lh = o.lh ?? 40, w = o.w ?? 260;
  panel(ctx, x - 18, y - 30, w + 30, lh * items.length + 22, { seed: o.seed ?? 4 });
  items.forEach((it, i) => {
    const yy = y + i * lh;
    if (i === sel) { stroke(ctx, [[x - 8, yy - 6], [x + w * 0.6, yy - 9], [x + w - 6, yy - 5]], { w: lh * 0.62, color: PAL.red, alpha: 0.85, seed: 7 + i, dry: 0.7, taper: [0.05, 0.4] }); }
    text(ctx, it.label, x + 6, yy + 2, { size: o.size ?? 24, color: (it.disabled || it.dim) ? PAL.w3 : i === sel ? '#fbf6ec' : PAL.ink });
    if (it.sub) text(ctx, it.sub, x + w - 10, yy + 2, { size: 18, align: 'right', color: i === sel ? '#fbf6ec' : PAL.w2 });
  });
  return { x: x - 18, y: y - 30, w: w + 30, lh };
}
/** returns index hit by a tap (logical coords) for a menu drawn with menu() */
export function menuHit(box, n, p) { if (!p || p.x < box.x || p.x > box.x + box.w) return -1; const i = Math.floor((p.y - box.y - 30 + box.lh * 0.75) / box.lh); return i >= 0 && i < n ? i : -1; }
export { seal, wash };
