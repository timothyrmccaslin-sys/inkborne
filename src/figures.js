// Procedural ink figures for the cast, enemies and NPCs (battle, field and portraits).
// TODO(art): replaced per key by painted sprite strips (bt-<id>-<anim>, walk-<id>, portrait-<id>-<mood>)
// when the character artists deliver them (SPEC section 5). Inkwing forms stay avian ink-wash:
// wings only, no armour, helmets or dragon motifs (Noe P2-6).
import { stroke, wash, splat, PAL, rng } from './ink.js';

const LOOK = {
  itsuki: { h: 1.08, w: 0.9, robe: '#8d877a', robe2: '#6f695e', sash: PAL.ink, hair: 'long', skin: '#efe6d6', weapon: 'katana', cord: PAL.red, wing: { tint: '#9fb5a4', kind: 'crane' } },
  benika: { h: 0.86, w: 1.0, robe: '#f3eee4', robe2: PAL.red, sash: PAL.red, hair: 'bob', skin: '#f1e4d0', weapon: 'bow', cord: PAL.red, wing: { tint: '#c8833c', kind: 'kite' } },
  gonzo: { h: 1.12, w: 1.45, robe: '#3e3a33', robe2: '#2d2a25', sash: '#5b4b3a', hair: 'bald', skin: '#e6d6bd', weapon: 'staff', cord: PAL.red, beard: true, beads: true, wing: { tint: '#6c6355', kind: 'owl' } },
  hotaru: { h: 0.82, w: 0.95, robe: '#7a7468', robe2: '#5d584e', sash: '#3b3730', hair: 'bun', skin: '#eadfcd', weapon: 'lantern-pole', cord: PAL.red, stoop: 0.18 },
  tsuru: { h: 0.78, w: 1.05, robe: '#5e5a52', robe2: '#46423b', sash: PAL.red, hair: 'bun', skin: '#ecdfca', weapon: null, cord: PAL.red, stoop: 0.12, apron: true },
};
export const castLook = LOOK;

const lerp = (a, b, k) => a + (b - a) * k;
const ease = (k) => k < 0.5 ? 2 * k * k : 1 - Math.pow(-2 * k + 2, 2) / 2;

/** Pose angles (radians, 0 = straight down) for a given action and phase. */
function pose(action, ph, t, seed) {
  const br = Math.sin(t * 2.1 + seed) * 0.5 + 0.5; // breathing 0..1
  const P = { lean: 0.02, sh: [0.25, -0.2], el: [0.3, -0.35], hip: [0.08, -0.1], kn: [0.02, 0.08], bob: br * 2, crouch: 0, weap: -0.6, look: 0 };
  if (action === 'walk' || action === 'run') {
    const s = Math.sin(ph * Math.PI * 2), amp = action === 'run' ? 0.7 : 0.45;
    P.hip = [s * amp, -s * amp]; P.kn = [Math.max(0, -s) * amp * 1.2, Math.max(0, s) * amp * 1.2];
    P.sh = [-s * amp * 0.6, s * amp * 0.6]; P.el = [0.3, -0.3]; P.bob = Math.abs(Math.cos(ph * Math.PI * 2)) * 4; P.lean = action === 'run' ? 0.18 : 0.05;
  } else if (action === 'strike') { // wind-up -> slash -> follow through
    const k = ph < 0.35 ? ease(ph / 0.35) : 1 - ease((ph - 0.35) / 0.65) * 0.25;
    const sl = ph < 0.35 ? 0 : ease(Math.min(1, (ph - 0.35) / 0.25));
    P.lean = lerp(-0.12, 0.32, sl); P.sh = [lerp(-2.4, 1.3, sl) * k + (1 - k) * 0.2, lerp(-0.9, 0.5, sl)]; P.el = [lerp(-0.6, 0.1, sl), -0.5];
    P.hip = [lerp(-0.2, 0.55, sl), lerp(0.1, -0.5, sl)]; P.kn = [lerp(0.3, 0.1, sl), 0.25]; P.crouch = lerp(6, 14, sl); P.weap = lerp(-2.6, 1.6, sl);
  } else if (action === 'hit') { P.lean = -0.35 * (1 - ph); P.sh = [-0.6, 0.6]; P.el = [-0.8, 0.8]; P.crouch = 8 * (1 - ph); P.look = -0.3; }
  else if (action === 'guard') { P.lean = -0.05; P.sh = [-1.2, -1.0]; P.el = [-1.4, -1.2]; P.crouch = 10; P.hip = [0.35, -0.35]; P.kn = [0.4, 0.4]; P.weap = -1.4; }
  else if (action === 'cast') { const k = ease(Math.min(1, ph * 2)); P.sh = [lerp(0.25, -2.6, k), lerp(-0.2, 2.6, k)]; P.el = [-0.2, 0.2]; P.lean = -0.08 * k; P.bob = br * 2 + k * 6; }
  else if (action === 'ko') { P.lean = 1.25; P.crouch = 40; P.sh = [0.9, 0.7]; P.el = [0.2, 0.1]; P.hip = [1.2, 1.0]; P.kn = [-1.4, -1.2]; P.bob = 0; }
  else { P.sh = [0.2 + br * 0.05, -0.25 - br * 0.05]; P.lean = 0.02 + br * 0.015; }
  return P;
}

function limb(x, y, a1, l1, a2, l2) { const ex = x + Math.sin(a1) * l1, ey = y + Math.cos(a1) * l1; return [[x, y], [ex, ey], [ex + Math.sin(a1 + a2) * l2, ey + Math.cos(a1 + a2) * l2]]; }

/**
 * Draw a humanoid cast member. (x,y) = feet. s = scale (1 => ~210px tall). face: 1 right, -1 left.
 * o: { action, ph (0..1), t, inkwing (0..1 blend), detail (0..1), seed }
 */
export function drawPerson(ctx, id, x, y, s, face, o = {}) {
  const L = LOOK[id] || LOOK.hotaru, t = o.t || 0, seed = (id.charCodeAt(0) * 7) % 13, det = o.detail ?? 1;
  const P = pose(o.action || 'idle', o.ph || 0, t, seed);
  const H = 210 * L.h, W = L.w;
  ctx.save(); ctx.translate(x, y); ctx.scale(s * face, s);
  // ground shadow
  wash(ctx, 0, 2, 46 * W, 9, PAL.ink, 0.22);
  const iw = o.inkwing || 0;
  if (iw > 0) drawWings(ctx, L.wing, H, t, iw, det);
  ctx.translate(0, -P.bob * 0.5);
  const legL = H * 0.46, hipY = -legL + P.crouch, stoop = (L.stoop || 0);
  const lean = P.lean + stoop;
  const chestX = Math.sin(lean) * H * 0.3, chestY = hipY - Math.cos(lean) * H * 0.3;
  const neckX = chestX + Math.sin(lean + stoop) * H * 0.06, neckY = chestY - H * 0.06;
  // legs (hakama / robe skirt): filled trapezoid that follows the legs
  const lg = [limb(-6 * W, hipY, P.hip[0], legL * 0.52, P.kn[0], legL * 0.52), limb(6 * W, hipY, P.hip[1], legL * 0.52, P.kn[1], legL * 0.52)];
  ctx.save(); ctx.fillStyle = L.robe2; ctx.globalAlpha = 0.9; ctx.beginPath();
  ctx.moveTo(-16 * W, hipY - 6); ctx.lineTo(lg[0][1][0] - 12 * W, lg[0][1][1]); ctx.lineTo(lg[0][2][0] - 14 * W, lg[0][2][1] - 8);
  ctx.lineTo(lg[1][2][0] + 14 * W, lg[1][2][1] - 8); ctx.lineTo(lg[1][1][0] + 12 * W, lg[1][1][1]); ctx.lineTo(16 * W, hipY - 6); ctx.closePath(); ctx.fill(); ctx.restore();
  for (const [k, l] of lg.entries()) {
    stroke(ctx, [[l[0][0] + (k ? 12 : -12) * W, l[0][1]], [l[1][0] + (k ? 12 : -12) * W, l[1][1]], [l[2][0] + (k ? 13 : -13) * W, l[2][1] - 8]], { w: 3.5, seed: seed + k, dry: 0.4, alpha: 0.85 });
    stroke(ctx, [[l[2][0] - 8, l[2][1] - 2], [l[2][0] + 12, l[2][1]]], { w: 5, seed: seed + 3 + k, dry: 0 }); // sandal
  }
  if (det > 0.6) for (let i = 0; i < 3; i++) { const px = lerp(-12, 12, i / 2) * W; stroke(ctx, [[px, hipY], [px + (lg[i > 1 ? 1 : 0][2][0]) * 0.4, -10]], { w: 1.4, seed: seed + 20 + i, dry: 0, alpha: 0.35, bleed: false }); } // pleats
  // torso robe
  const tw = 24 * W;
  ctx.save(); ctx.fillStyle = L.robe; ctx.globalAlpha = 0.95; ctx.beginPath();
  ctx.moveTo(chestX - tw, chestY + 4); ctx.quadraticCurveTo(chestX - tw * 1.15, (chestY + hipY) / 2, -tw * 0.85, hipY + 4);
  ctx.lineTo(tw * 0.85, hipY + 4); ctx.quadraticCurveTo(chestX + tw * 1.15, (chestY + hipY) / 2, chestX + tw, chestY + 4);
  ctx.quadraticCurveTo(chestX, chestY - 8, chestX - tw, chestY + 4); ctx.fill(); ctx.restore();
  stroke(ctx, [[chestX - tw, chestY + 4], [chestX - tw * 1.1, (chestY + hipY) / 2], [-tw * 0.85, hipY + 4]], { w: 4.5, seed: seed + 5, dry: 0.5 });
  stroke(ctx, [[chestX + tw, chestY + 4], [chestX + tw * 1.1, (chestY + hipY) / 2], [tw * 0.85, hipY + 4]], { w: 4.5, seed: seed + 6, dry: 0.5 });
  stroke(ctx, [[neckX - 9, neckY + 4], [chestX + 2, chestY + 26], [chestX + 6 * W, hipY - 4]], { w: 3, seed: seed + 7, dry: 0.2 }); // collar fold
  stroke(ctx, [[neckX + 9, neckY + 4], [chestX + 4, chestY + 22]], { w: 2.5, seed: seed + 8, dry: 0.2 });
  // sash
  stroke(ctx, [[-tw * 0.95, hipY - 10], [0, hipY - 8], [tw * 0.95, hipY - 10]], { w: 11, color: L.sash, seed: seed + 9, dry: 0.3, taper: [0.02, 0.02] });
  if (L.apron) { ctx.save(); ctx.fillStyle = 'rgba(240,234,220,0.9)'; ctx.fillRect(-tw * 0.7, hipY - 6, tw * 1.4, legL * 0.7); ctx.restore(); }
  if (L.beads) for (let i = 0; i < 9; i++) { const a = -0.9 + i * 0.22; ctx.save(); ctx.fillStyle = i === 4 ? PAL.red : '#3a2f25'; ctx.beginPath(); ctx.arc(chestX + Math.sin(a) * 22, chestY + 10 + Math.cos(a) * 26, 5.2, 0, Math.PI * 2); ctx.fill(); ctx.restore(); }
  // arms (back arm first)
  const shY = chestY + 8, shL = [chestX - tw * 0.85, shY], shR = [chestX + tw * 0.85, shY];
  const armL = H * 0.17;
  const back = limb(shL[0], shL[1], P.sh[1], armL, P.el[1], armL), front = limb(shR[0], shR[1], P.sh[0], armL, P.el[0], armL);
  stroke(ctx, back, { w: 13 * Math.min(W, 1.3), color: L.robe2, seed: seed + 10, dry: 0.3, taper: [0.05, 0.3] });
  stroke(ctx, back, { w: 3, seed: seed + 11, dry: 0, alpha: 0.7 });
  hand(ctx, back[2], L.skin);
  // head
  const hx = neckX + Math.sin(P.look) * 2, hy = neckY - H * 0.075, hr = H * 0.068;
  ctx.save(); ctx.fillStyle = L.skin; ctx.beginPath(); ctx.ellipse(hx, hy, hr * 0.86, hr, 0, 0, Math.PI * 2); ctx.fill(); ctx.restore();
  stroke(ctx, [[hx - hr * 0.86, hy - hr * 0.2], [hx - hr * 0.7, hy + hr * 0.7], [hx + hr * 0.2, hy + hr * 1.02], [hx + hr * 0.86, hy + hr * 0.3]], { w: 2.6, seed: seed + 12, dry: 0 });
  // face (profile facing +x)
  stroke(ctx, [[hx + hr * 0.25, hy - hr * 0.15], [hx + hr * 0.6, hy - hr * 0.2]], { w: 2.4, seed: seed + 13, dry: 0, bleed: false }); // brow
  ctx.save(); ctx.fillStyle = PAL.ink; ctx.beginPath(); ctx.ellipse(hx + hr * 0.45, hy + hr * 0.05, 1.8, o.action === 'hit' ? 0.8 : 2.2, 0, 0, Math.PI * 2); ctx.fill(); ctx.restore();
  stroke(ctx, [[hx + hr * 0.82, hy + hr * 0.1], [hx + hr * 0.95, hy + hr * 0.32], [hx + hr * 0.8, hy + hr * 0.38]], { w: 1.8, seed: seed + 14, dry: 0, bleed: false });
  hair(ctx, L, hx, hy, hr, t, seed, det);
  if (L.beard) { ctx.save(); ctx.fillStyle = '#8a857a'; ctx.beginPath(); ctx.moveTo(hx - hr * 0.3, hy + hr * 0.3); ctx.quadraticCurveTo(hx + hr * 0.4, hy + hr * 2.1, hx + hr * 0.95, hy + hr * 0.4); ctx.fill(); ctx.restore();
    for (let i = 0; i < 5; i++) stroke(ctx, [[hx + hr * (0.0 + i * 0.18), hy + hr * 0.5], [hx + hr * (0.1 + i * 0.16), hy + hr * 1.6]], { w: 1.4, seed: seed + 30 + i, dry: 0, alpha: 0.7, bleed: false }); }
  // front arm + weapon
  stroke(ctx, front, { w: 13 * Math.min(W, 1.3), color: L.robe, seed: seed + 15, dry: 0.3, taper: [0.05, 0.3] });
  stroke(ctx, [[front[0][0] - 5, front[0][1]], [front[1][0] - 6, front[1][1]], [front[2][0] - 3, front[2][1]]], { w: 3, seed: seed + 16, dry: 0.2 });
  if (id === 'itsuki') stroke(ctx, [[front[1][0] + 6, front[1][1] + 2], [front[1][0] + 2, front[1][1] + 18]], { w: 2, seed: 99, dry: 0, alpha: 0.6 }); // torn sleeve
  weapon(ctx, L, front[2], P.weap, H, o, seed, iw);
  hand(ctx, front[2], L.skin);
  ctx.restore();
}

function hand(ctx, p, skin) { ctx.save(); ctx.fillStyle = skin; ctx.beginPath(); ctx.arc(p[0], p[1], 5.5, 0, Math.PI * 2); ctx.fill(); ctx.strokeStyle = PAL.ink; ctx.lineWidth = 1.5; ctx.stroke(); ctx.restore(); }

function hair(ctx, L, hx, hy, hr, t, seed, det) {
  const sw = Math.sin(t * 1.7 + seed) * 3;
  if (L.hair === 'bald') { stroke(ctx, [[hx - hr * 0.86, hy], [hx - hr * 0.3, hy - hr * 1.05], [hx + hr * 0.5, hy - hr * 0.9]], { w: 2.4, seed, dry: 0 }); return; }
  ctx.save(); ctx.fillStyle = PAL.ink; ctx.beginPath();
  ctx.moveTo(hx + hr * 0.7, hy - hr * 0.45); ctx.quadraticCurveTo(hx, hy - hr * 1.45, hx - hr * 0.95, hy - hr * 0.2);
  if (L.hair === 'bob') { ctx.quadraticCurveTo(hx - hr * 1.15, hy + hr * 0.6, hx - hr * 0.5, hy + hr * 0.9); ctx.quadraticCurveTo(hx - hr * 0.2, hy + hr * 0.1, hx + hr * 0.1, hy - hr * 0.4); }
  else ctx.quadraticCurveTo(hx - hr * 0.6, hy + hr * 0.1, hx + hr * 0.2, hy - hr * 0.5);
  ctx.closePath(); ctx.fill(); ctx.restore();
  if (L.hair === 'long') {
    stroke(ctx, [[hx - hr * 0.8, hy - hr * 0.2], [hx - hr * 1.2 + sw * 0.3, hy + hr * 1.4], [hx - hr * 1.5 + sw, hy + hr * 3.2], [hx - hr * 1.7 + sw * 1.4, hy + hr * 4.4]], { w: hr * 0.55, seed: seed + 40, dry: 0.7, taper: [0.1, 0.8] });
    stroke(ctx, [[hx - hr * 1.0, hy + hr * 1.0], [hx - hr * 1.25, hy + hr * 1.25]], { w: 5, color: L.cord, seed: seed + 41, dry: 0, taper: [0.1, 0.1] });
  }
  if (L.hair === 'bun') { ctx.save(); ctx.fillStyle = '#8a857a'; ctx.beginPath(); ctx.arc(hx - hr * 0.6, hy - hr * 0.95, hr * 0.42, 0, Math.PI * 2); ctx.fill(); ctx.restore(); stroke(ctx, [[hx - hr * 1.0, hy - hr * 1.2], [hx - hr * 0.2, hy - hr * 0.7]], { w: 2, color: PAL.red, seed, dry: 0 }); }
  if (L.hair === 'bob' && det > 0.5) { ctx.save(); ctx.fillStyle = '#f6f1e6'; ctx.translate(hx - hr * 0.2, hy - hr * 0.8); ctx.rotate(-0.4); ctx.fillRect(-4, -9, 8, 16); ctx.restore(); stroke(ctx, [[hx - hr * 0.2, hy - hr * 0.95], [hx - hr * 0.2, hy - hr * 0.6]], { w: 1.4, color: PAL.red, seed, dry: 0 }); }
}

function weapon(ctx, L, p, a, H, o, seed, iw) {
  const k = L.weapon; if (!k) return;
  ctx.save(); ctx.translate(p[0], p[1]); ctx.rotate(-a + Math.PI);
  if (k === 'katana') {
    stroke(ctx, [[0, 10], [0, -18]], { w: 6, seed, dry: 0.2, taper: [0.02, 0.02] }); // brush-handled grip
    stroke(ctx, [[-9, -18], [9, -18]], { w: 4, seed: seed + 1, dry: 0 });
    stroke(ctx, [[0, -18], [3, -70], [8, -H * 0.48]], { w: 4.5, color: '#2b2924', seed: seed + 2, dry: 0, taper: [0.02, 0.9] });
    stroke(ctx, [[1.5, -22], [4, -70], [8, -H * 0.47]], { w: 1.2, color: '#e8e3d8', seed: seed + 3, dry: 0, alpha: 0.8, bleed: false });
    if (o.action === 'strike' && o.ph > 0.3 && o.ph < 0.75) { // ink trail behind the blade
      ctx.restore(); ctx.save(); ctx.translate(p[0], p[1]);
      const k2 = (o.ph - 0.3) / 0.45, pts = []; for (let i = 0; i <= 10; i++) { const aa = -2.6 + (1.6 + 2.6) * Math.min(k2, i / 10); pts.push([Math.sin(aa + Math.PI) * -H * 0.42, Math.cos(aa + Math.PI) * H * 0.42]); }
      stroke(ctx, pts, { w: 16, color: iw ? '#5f8a6a' : PAL.ink, alpha: 0.55 * (1 - k2 * 0.5), seed: seed + 4, dry: 0.8, taper: [0.5, 0.2] });
    }
  } else if (k === 'bow') {
    stroke(ctx, [[0, -H * 0.42], [-16, -H * 0.2], [-18, 0], [-16, H * 0.2], [0, H * 0.42]], { w: 5, seed, dry: 0.3, taper: [0.15, 0.15] });
    ctx.strokeStyle = 'rgba(27,24,19,0.6)'; ctx.lineWidth = 1.2; ctx.beginPath(); ctx.moveTo(0, -H * 0.42); ctx.lineTo(o.action === 'strike' && o.ph < 0.4 ? 18 : 0, 0); ctx.lineTo(0, H * 0.42); ctx.stroke();
    for (const yy of [-H * 0.3, -H * 0.24]) { ctx.fillStyle = '#f6f1e6'; ctx.fillRect(-22, yy, 9, 16 + Math.sin((o.t || 0) * 3 + yy) * 2); ctx.fillStyle = PAL.red; ctx.fillRect(-20, yy + 3, 5, 2); } // prayer slips
  } else if (k === 'staff') {
    stroke(ctx, [[0, 40], [0, -H * 0.62]], { w: 7, color: '#3a332a', seed, dry: 0.4, taper: [0.02, 0.02] });
    for (const yy of [30, -H * 0.55]) stroke(ctx, [[-6, yy], [6, yy]], { w: 6, color: '#55504a', seed: seed + 2, dry: 0 });
  } else if (k === 'lantern-pole') {
    stroke(ctx, [[0, 20], [0, -H * 0.5], [14, -H * 0.55]], { w: 3.5, seed, dry: 0.3 });
    ctx.restore(); ctx.save(); ctx.translate(p[0], p[1]);
  }
  ctx.restore();
}

/** Avian ink-wash wings (Inkwing). Muted elemental tint, no armour or dragon motifs. */
function drawWings(ctx, wg, H, t, a, det) {
  const flap = Math.sin(t * (wg.kind === 'owl' ? 2.2 : 3.4)) * 0.18;
  ctx.save(); ctx.globalAlpha *= a;
  const by = -H * 0.66, span = (wg.kind === 'kite' ? 1.25 : wg.kind === 'owl' ? 0.95 : 1.15) * H;
  wash(ctx, 0, by, span * 0.75, H * 0.45, wg.tint, 0.35);
  for (const side of [-1, 1]) {
    const feathers = wg.kind === 'owl' ? 7 : 9;
    for (let i = 0; i < feathers; i++) {
      const k = i / (feathers - 1), ang = (-0.15 - flap + k * 1.25) * side;
      const len = span * (wg.kind === 'owl' ? 0.55 - k * 0.12 : 0.7 - k * 0.22);
      const x1 = side * 14, y1 = by + 8;
      const x2 = x1 + Math.cos(ang) * len * side * side, y2 = y1 - Math.sin(-ang * side + 0.35) * len * 0.55 + k * H * 0.22;
      stroke(ctx, [[x1, y1], [lerp(x1, x2, 0.55), lerp(y1, y2, 0.4) - 10], [x2, y2]], { w: (wg.kind === 'owl' ? 22 : 15) * (1 - k * 0.4), color: i % 3 === 0 ? PAL.ink : wg.tint, seed: 70 + i + (side > 0 ? 20 : 0), dry: 0.9, alpha: 0.75, taper: [0.1, 0.6] });
      if (wg.kind === 'owl' && det > 0.5) stroke(ctx, [[lerp(x1, x2, 0.4), lerp(y1, y2, 0.4)], [lerp(x1, x2, 0.6), lerp(y1, y2, 0.6) + 4]], { w: 2, color: PAL.red, alpha: 0.4 + 0.3 * Math.sin(t * 3 + i), seed: i, dry: 0, bleed: false }); // glowing cracks
      if (wg.kind === 'kite' && i % 2 === 0) wash(ctx, x2, y2, 9, 9, '#e0662c', 0.35 + 0.2 * Math.sin(t * 6 + i)); // smouldering tips
    }
  }
  ctx.restore();
}

// ---------- enemies ----------
export function drawEnemy(ctx, id, x, y, s, o = {}) {
  const t = o.t || 0, hit = o.action === 'hit' ? 1 - (o.ph || 0) : 0, die = o.action === 'die' ? (o.ph || 0) : 0, atk = o.action === 'attack' ? Math.sin((o.ph || 0) * Math.PI) : 0;
  ctx.save(); ctx.translate(x - atk * 60 + hit * 18, y); ctx.scale(s, s); ctx.globalAlpha *= 1 - die;
  if (die) ctx.scale(1 + die * 0.4, 1 - die * 0.7);
  wash(ctx, 0, 2, 60, 10, PAL.ink, 0.25);
  if (id === 'blotling') {
    const w = 1 + Math.sin(t * 3) * 0.06, sq = 1 - Math.sin(t * 3) * 0.05;
    ctx.save(); ctx.scale(w, sq); ctx.fillStyle = PAL.ink; ctx.globalAlpha *= 0.92; ctx.beginPath();
    for (let i = 0; i <= 24; i++) { const a = Math.PI + i / 24 * Math.PI, r = 52 + Math.sin(a * 5 + t * 2) * 5; ctx.lineTo(Math.cos(a) * r * 1.2, Math.sin(a) * r * 1.1 - 4); }
    ctx.lineTo(70, 0); ctx.quadraticCurveTo(0, 12, -70, 0); ctx.fill(); ctx.restore();
    for (let i = 0; i < 5; i++) splat(ctx, -60 + i * 30, 4, 6 + (i % 2) * 4, PAL.ink, i + 3, 0.7);
    const blink = (Math.sin(t * 0.9) > 0.97) ? 0.15 : 1;
    ctx.save(); ctx.fillStyle = '#efe9dc'; ctx.beginPath(); ctx.ellipse(-10, -36, 15, 12 * blink, 0, 0, Math.PI * 2); ctx.fill();
    ctx.fillStyle = PAL.red; ctx.beginPath(); ctx.arc(-14, -36, 6 * blink, 0, Math.PI * 2); ctx.fill(); ctx.restore();
    for (let i = 0; i < 3; i++) stroke(ctx, [[-30 + i * 25, -50], [-26 + i * 25, -40 + Math.sin(t * 2 + i) * 6]], { w: 4, seed: i, dry: 0, alpha: 0.5 });
  } else if (id === 'hollow_lantern') {
    const fy = -120 + Math.sin(t * 1.6) * 10;
    for (let i = 0; i < 6; i++) wash(ctx, Math.sin(t + i) * 14, fy + 60 + i * 14, 26 - i * 3, 14, PAL.w2, 0.25); // ink smoke
    ctx.save(); ctx.fillStyle = 'rgba(238,230,214,0.92)'; ctx.beginPath(); ctx.ellipse(0, fy, 44, 58, 0, 0, Math.PI * 2); ctx.fill(); ctx.restore();
    const fl = 0.6 + 0.4 * Math.sin(t * 9) * Math.sin(t * 4.3);
    wash(ctx, 0, fy + 6, 30, 34, '#8c8579', 0.5 * fl); wash(ctx, 0, fy + 10, 12, 18, PAL.red, 0.45 * fl);
    for (const k of [-0.75, -0.35, 0, 0.35, 0.75]) stroke(ctx, [[k * 40, fy - 54], [k * 48, fy], [k * 40, fy + 54]], { w: 2.2, seed: 5 + k * 10, dry: 0, alpha: 0.75 });
    for (const yy of [-50, -25, 0, 25, 50]) stroke(ctx, [[-Math.sqrt(1 - (yy / 58) ** 2) * 44, fy + yy], [Math.sqrt(1 - (yy / 58) ** 2) * 44, fy + yy]], { w: 1.4, seed: yy, dry: 0, alpha: 0.45, bleed: false });
    stroke(ctx, [[-30, fy - 58], [30, fy - 58]], { w: 7, seed: 2, dry: 0.3 }); stroke(ctx, [[-28, fy + 58], [28, fy + 58]], { w: 7, seed: 3, dry: 0.3 });
    ctx.save(); ctx.globalCompositeOperation = 'destination-out'; ctx.beginPath(); ctx.moveTo(14, fy - 20); ctx.lineTo(40, fy - 4); ctx.lineTo(22, fy + 22); ctx.lineTo(30, fy - 2); ctx.closePath(); ctx.fill(); ctx.restore(); // tear
    stroke(ctx, [[14, fy - 20], [40, fy - 4], [22, fy + 22]], { w: 1.6, seed: 9, dry: 0, alpha: 0.8 });
  } else if (id === 'smudge_ronin') {
    // Original design: a wandering swordsman half-unwritten by the Blot. Wide straw kasa, tattered ink robe,
    // over-long blade held low; the right side keeps smearing away into paper.
    const br = Math.sin(t * 1.8) * 2, sw = atk ? -atk * 0.9 : Math.sin(t * 1.1) * 0.05;
    stroke(ctx, [[-6, -112], [-22, -56], [-34, 0]], { w: 13, seed: 41, dry: 0.5 }); stroke(ctx, [[8, -112], [22, -58], [30, 0]], { w: 13, seed: 42, dry: 0.5 });
    const hem = []; for (let i = 0; i <= 10; i++) { const k = i / 10; hem.push([lerp(68, -74, k), -52 + Math.sin(t * 3 + i * 1.7) * 6 + (i % 2) * 10]); }
    ctx.save(); ctx.fillStyle = PAL.ink; ctx.globalAlpha *= 0.88; ctx.beginPath(); ctx.moveTo(-34, -200 + br); ctx.lineTo(36, -200 + br); for (const [hx, hy] of hem) ctx.lineTo(hx, hy); ctx.closePath(); ctx.fill(); ctx.restore();
    for (let i = 0; i < 4; i++) { const hx = -60 + i * 38; stroke(ctx, [[hx, -50], [hx - 4 + Math.sin(t * 2.4 + i) * 8, -22 - (i % 2) * 8]], { w: 7, seed: 50 + i, dry: 0.8, alpha: 0.8 }); }
    stroke(ctx, [[-30, -150 + br], [32, -146 + br]], { w: 6, color: '#3a352d', seed: 44, dry: 0.3 }); // obi
    // arm + blade (faces left)
    const hxp = -64 - atk * 40, hyp = -138 + br - atk * 30;
    stroke(ctx, [[-26, -188 + br], [-52, -164 + br], [hxp, hyp]], { w: 12, seed: 45, dry: 0.4 });
    ctx.save(); ctx.translate(hxp, hyp); ctx.rotate(sw - 0.35);
    stroke(ctx, [[0, 0], [-90, -8], [-190, -26]], { w: 5, seed: 46, dry: 0.2, taper: [0.9, 0.05] }); stroke(ctx, [[6, -8], [6, 8]], { w: 7, seed: 47, dry: 0 });
    ctx.restore();
    // head + wide kasa
    ctx.save(); ctx.fillStyle = '#d9cfbd'; ctx.beginPath(); ctx.ellipse(-4, -210 + br, 14, 16, 0, 0, Math.PI * 2); ctx.fill(); ctx.restore();
    ctx.save(); ctx.fillStyle = PAL.ink; ctx.globalAlpha *= 0.95; ctx.beginPath(); ctx.moveTo(-80, -214 + br); ctx.quadraticCurveTo(-30, -236 + br, 0, -262 + br); ctx.quadraticCurveTo(30, -236 + br, 76, -210 + br); ctx.quadraticCurveTo(0, -222 + br, -80, -214 + br); ctx.fill(); ctx.restore();
    for (let i = 0; i < 6; i++) stroke(ctx, [[-60 + i * 22, -214 + br], [-46 + i * 18, -232 + br]], { w: 1.4, color: '#5b554b', seed: 60 + i, dry: 0, alpha: 0.6, bleed: false });
    ctx.save(); ctx.fillStyle = PAL.red; ctx.globalAlpha *= 0.6 + 0.4 * Math.sin(t * 2.3); ctx.beginPath(); ctx.arc(-10, -204 + br, 2.6, 0, Math.PI * 2); ctx.fill(); ctx.restore(); // one ember eye under the hat
    // half-unwritten: dry paper strokes eat the right side
    for (let i = 0; i < 7; i++) { const yy = -236 + i * 30 + Math.sin(t * 2 + i) * 3; stroke(ctx, [[8, yy], [40 + (i % 3) * 12, yy + 8], [72 + Math.sin(t + i) * 8, yy + 24]], { w: 9 - i * 0.6, color: PAL.paper, seed: i, dry: 0.9, alpha: 0.8 }); }
    for (let i = 0; i < 5; i++) { const dy = (t * 40 + i * 37) % 110; splat(ctx, hxp - 150 - i * 6, hyp - 30 + dy, 3, PAL.ink, i, 0.8 * (1 - dy / 110)); } // drips off the blade
  }
  ctx.restore();
}

/** Bust portrait for dialogue/shop (TODO(art): portrait-<id>-<mood> 512x640). */
export function drawPortrait(ctx, id, x, y, s, mood, t, speaking) {
  // bust framed in a 300x376 box (x = centre, y = bottom edge), scaled by s
  const L = LOOK[id] || LOOK.hotaru, bw = 300 * s, bh = 376 * s;
  ctx.save(); ctx.beginPath(); ctx.rect(x - bw / 2, y - bh, bw, bh); ctx.clip();
  wash(ctx, x, y - bh * 0.45, bw * 0.48, bh * 0.5, PAL.w3, 0.22);
  const sc = 2.25 * s / Math.max(0.85, L.h), H = 210 * L.h * sc, bob = speaking ? Math.sin(t * 14) * 1.2 : 0;
  const feet = y - bh + 24 * s + H * 1.02 + bob;
  drawPerson(ctx, id, x, feet, sc, 1, { action: 'idle', t, detail: 1 });
  const fy = feet - H * 0.9, fx = x + 4 * s;
  if (mood === 'angry') stroke(ctx, [[fx - 4 * s, fy - 20 * s], [fx + 26 * s, fy - 10 * s]], { w: 5 * s, seed: 3, dry: 0 });
  if (mood === 'sad') stroke(ctx, [[fx - 2 * s, fy - 12 * s], [fx + 24 * s, fy - 22 * s]], { w: 4 * s, seed: 3, dry: 0 });
  if (mood === 'smile') stroke(ctx, [[fx + 8 * s, fy + 26 * s], [fx + 16 * s, fy + 30 * s], [fx + 24 * s, fy + 24 * s]], { w: 3.5 * s, seed: 5, dry: 0 });
  ctx.restore();
}
