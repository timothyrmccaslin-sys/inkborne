// POINT OF INTEREST: walkable painted area (Bob's far/mid/near layers) with ambient motion and triggers.
import { PAL, paper, stroke, wash, grassTuft, lantern, splat, rng } from '../ink.js';
import { drawPerson } from '../figures.js';
import { T, text, panel, FONT } from '../ui.js';
import { createAmbient } from '../ambient.js';
import { startBattle } from '../encounters.js';
const SPEED = 210, LEADER = 'itsuki', FOLLOW = ['benika', 'gonzo'];
export function create(game, params) {
  const def = game.data.pois[params.id], raw = game.data.poiRaw[params.id];
  const isForest = def.id === 'forest';
  let px = def.spawn[0], py = def.spawn[1], face = 1, walkPh = 0, moving = false, trail = [], prompt = null, inside = new Set(), cool = 0, stepAcc = 0, banner = 2.8;
  const r = rng(def.id.length * 13);
  const leaves = Array.from({ length: isForest ? 22 : 6 }, () => ({ x: r() * 1280, y: r() * 720, s: 0.6 + r() * 0.8, sp: 20 + r() * 30, ph: r() * 6 }));
  const tufts = Array.from({ length: 14 }, (_, i) => ({ x: 40 + i * 92 + r() * 30, y: 690 + r() * 25, h: 22 + r() * 18 }));
  const layer = (k) => game.art.get(`${def.art}-${k}`);
  function enterWalker() { game.core.walker_load(raw, px, py); }
  function fire(tr) {
    if (tr.kind === 'battle') { game.audio.play('ring'); game.push('battle', { enc: tr.ref, flag: tr.flag, bg: 'battle-forest' }); }
    if (tr.kind === 'dialogue') { game.audio.play('confirm'); game.push('dialogue', { script: tr.ref, bg: def.art }); }
    if (tr.kind === 'shop') { game.audio.play('confirm'); game.push('shop', { shop: tr.ref, bg: def.art }); }
    if (tr.kind === 'sign') { banner = 3; signText = T(tr.ref, {}, 'A broken seal-stone. Its red mark has gone grey at the edges.'); }
  }
  let signText = null;
  const amb = createAmbient({ quality: 'auto', sfx: (k) => game.audio.play(k, { gain: 0.3 }) }); // Ashley: grass, mist, leaves, lanterns
  return {
    enter() { game.audio.setScene(def.id); enterWalker(); game.core.set_node(def.node); amb.load(def); },
    resume() { game.audio.setScene(def.id); enterWalker(); cool = 0.6; },
    onResult(res) { game.enc.afterBattle(); if (res && res.lose) { px = def.spawn[0]; py = def.spawn[1]; enterWalker(); } game.save(); },
    update(dt, inp) {
      banner = Math.max(0, banner - dt); cool = Math.max(0, cool - dt);
      const [mx, my] = inp.move(); moving = Math.hypot(mx, my) > 0.05;
      amb.update(dt, { x: 0, y: 0 }, { player: { x: px, y: py } });
      if (moving) { const ox = px, oy = py; const p = game.core.walker_step(mx * SPEED, my * SPEED * 0.75, dt); px = p[0]; py = p[1];
        const hit = cool > 0 ? null : game.enc.move({ scene: 'poi', poi: def, x: px, y: py, dist: Math.hypot(px - ox, py - oy) }); if (hit) { startBattle(game, hit); return; } if (Math.abs(mx) > 0.1) face = mx > 0 ? 1 : -1; walkPh = (walkPh + dt * 1.6 * Math.hypot(mx, my)) % 1; stepAcc += dt * Math.hypot(mx, my); if (stepAcc > 0.31) { stepAcc = 0; game.audio.play('step', { wood: def.ground === 'wood' }); } }
      if (!trail.length || Math.hypot(trail[0][0] - px, trail[0][1] - py) > 4) { trail.unshift([px, py, face]); trail.length = Math.min(trail.length, 60); }
      const ids = game.core.walker_triggers().split(',').filter(Boolean); prompt = null;
      for (const id of ids) {
        if (id.startsWith('exit:')) { game.audio.play('confirm'); game.go('world', {}); return; }
        const tr = def.triggers.find((x) => x.id === id); if (!tr) continue;
        if (tr.needs && !game.core.flag(tr.needs)) continue;
        if (tr.kind === 'battle') { if ((tr.once && game.core.flag(tr.flag)) || cool > 0 || inside.has(id)) continue; inside.add(id); fire(tr); return; }
        prompt = tr;
      }
      for (const id of [...inside]) if (!ids.includes(id)) inside.delete(id);
      if (prompt && (inp.pressed('confirm') || game.taps.length && game.taps.some((p) => p.y < 600 && Math.abs(p.x - px) < 160))) fire(prompt);
      if (inp.pressed('menu')) game.fullscreen();
    },
    draw(ctx, t) {
      const par = (px - 640) / 640;
      // far layer (parallax 0.2)
      if (layer('far')) ctx.drawImage(layer('far'), -16 - par * 12, -6, 1312, 738); else { ctx.drawImage(paper(1280, 720), 0, 0); /* TODO(art) */ }
      amb.drawBack(ctx, { x: 0, y: 0 }); // Ashley ambient (back): mist bands, far grass
      if (layer('mid')) ctx.drawImage(layer('mid'), -12 - par * 22, -4, 1304, 733);
      // FX slot B: lantern glow (town) / ground mist (forest)
      if (!isForest) for (const [lx, ly] of [[425, 270], [518, 340], [735, 349]]) { const fl = 0.7 + 0.3 * Math.sin(t * 7 + lx) * Math.sin(t * 3.1 + ly); wash(ctx, lx - par * 22, ly + 6, 48, 48, '#e9a33c', 0.32 * fl); }
      else for (let i = 0; i < 3; i++) wash(ctx, ((t * 14 + i * 520) % 1700) - 200, 610 + i * 22, 300, 20, PAL.paper, 0.35);
      // NPCs (idle sway) and party (leader + 2 followers on the trail), depth-sorted by y
      const actors = [];
      for (const n of def.npcs) actors.push({ y: n.y, d: () => drawPerson(ctx, n.id, n.x, n.y + Math.sin(t * 1.3 + n.x) * 0.6, n.small ? 0.36 : 0.42, n.face, { action: 'idle', t, detail: 0.6 }) });
      FOLLOW.forEach((id, i) => { const p = trail[Math.min(trail.length - 1, (i + 1) * 14)] || [px, py, face]; actors.push({ y: p[1] - 0.1, d: () => drawPerson(ctx, id, p[0], p[1], 0.42, p[2], { action: moving ? 'walk' : 'idle', ph: (walkPh + 0.3 * (i + 1)) % 1, t, detail: 0.6 }) }); });
      actors.push({ y: py, d: () => drawPerson(ctx, LEADER, px, py, 0.42, face, { action: moving ? 'walk' : 'idle', ph: walkPh, t, detail: 0.6 }) });
      actors.sort((a, b) => a.y - b.y).forEach((a) => a.d());
      // near layer (parallax 1.1) + swaying grass
      if (layer('near')) ctx.drawImage(layer('near'), -20 - par * 34, -10 + Math.sin(t * 0.8) * 1.5, 1320, 742);
      amb.drawFront(ctx, { x: 0, y: 0 }); // Ashley ambient (front): near grass, leaves, lanterns
      // UI
      if (banner > 0) { const a = Math.min(1, banner); panel(ctx, 440, 26, 400, 60, { seed: 5, alpha: a }); text(ctx, signText || def.name, 640, 66, { size: signText ? 20 : 34, align: 'center', font: signText ? undefined : FONT.title, alpha: a }); if (banner <= 0.05) signText = null; }
      if (prompt && prompt.kind !== 'battle') { const lbl = prompt.kind === 'shop' ? 'A: Enter Kōbō Tsuru' : prompt.kind === 'dialogue' ? 'A: Talk to Old Hotaru' : 'A: Look'; panel(ctx, px - 120, py - 150, 240, 40, { seed: 8 }); text(ctx, lbl, px, py - 123, { size: 20, align: 'center' }); }
      text(ctx, `${game.core.gold()} mon`, 1200, 700, { size: 20, align: 'right', color: '#fbf6ec', shadow: PAL.ink });
    },
  };
}
