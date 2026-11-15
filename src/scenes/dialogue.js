// ACTION: dialogue. Two ink portraits (D1/D2), name plates, a typed text box (D3), choices (D7).
// Layout: Helen's LAYOUT_NOTES section 3. Text: team/story dialogue.json (Ollie/Lisa).
// TODO(art): painted portraits (portrait-<id>-<mood>, Kenji) replace the procedural ones when delivered.
import { PAL, paper, stroke, wash, seal } from '../ink.js';
import { drawPortrait } from '../figures.js';
import { T, text, panel, wrap, FONT } from '../ui.js';
export const ALIAS = { lantern_keeper: 'hotaru' };
export const NPC_NAMES = { hotaru: 'Old Hotaru', tsuru: 'Grandmother Tsuru' };
const PARTY = ['itsuki', 'benika', 'gonzo'];
export function create(game, params) {
  const sc = game.data.dialogue[params.script]; const pd = Object.fromEntries(game.data.party.members.map((m) => [m.id, m.name]));
  const nameOf = (id) => pd[id] || NPC_NAMES[ALIAS[id] || id] || id;
  let node = null, id = null, shown = 0, t0 = 0, sel = 0, left = 'itsuki', right = null, lastBlip = 0, act = 0, box = null;
  function go(nid) {
    id = nid; node = sc.nodes[nid]; shown = 0; sel = 0; act = 0;
    if (!node) return game.pop({ done: true });
    const who = ALIAS[node.who] || node.who;
    if (PARTY.includes(who)) left = who; else right = who;
    game.audio.voice(who, 'talk');
  }
  return {
    enter() { if (!sc) return game.pop(); const first = sc.nodes[sc.start]; for (const n of Object.values(sc.nodes)) { const w = ALIAS[n.who] || n.who; if (!PARTY.includes(w)) { right = right || w; } } go(sc.start); game.audio.play('confirm'); },
    update(dt, inp) {
      if (!node) return; act = Math.min(1, act + dt / 0.15);
      const full = node.text.length, before = Math.floor(shown); shown = Math.min(full, shown + dt * 40);
      if (Math.floor(shown) !== before && Math.floor(shown) % 2 === 0 && node.text[Math.floor(shown)] !== ' ') game.audio.blip(ALIAS[node.who] || node.who);
      const tap = game.taps[0], adv = inp.pressed('confirm') || (tap && tap.y > 460);
      if (shown < full) { if (adv || inp.pressed('cancel')) shown = full; return; }
      if (node.choices) {
        const n = node.choices.length; if (inp.pressed('down')) { sel = (sel + 1) % n; game.audio.play('move'); } if (inp.pressed('up')) { sel = (sel + n - 1) % n; game.audio.play('move'); }
        let pick = inp.pressed('confirm') ? sel : -1; if (tap) node.choices.forEach((c, i) => { if (tap.x > 424 && tap.x < 856 && tap.y > 248 + i * 72 && tap.y < 248 + i * 72 + 56) pick = i; });
        if (pick >= 0) { const c = node.choices[pick]; game.audio.play('confirm'); if (c.set) game.core.set_flag(c.set, true); go(c.next); }
        return;
      }
      if (adv) { game.audio.play('move'); if (node.end || !node.next) { if (params.flag) game.core.set_flag(params.flag, true); game.save(); game.pop({ done: true }); node = null; } else go(node.next); }
    },
    draw(ctx, t) {
      // blurred, knocked-back background plate
      const bg = params.bg && game.art.get(params.bg);
      if (bg) { ctx.save(); ctx.filter = 'blur(6px)'; ctx.drawImage(bg, -20, -12, 1320, 744); ctx.restore(); ctx.save(); ctx.globalAlpha = 0.6; ctx.drawImage(paper(1280, 720), 0, 0); ctx.restore(); } else ctx.drawImage(paper(1280, 720), 0, 0);
            if (!node) return;
      const who = ALIAS[node.who] || node.who, speakL = who === left, speakR = who === right && !speakL;
      const portrait = (pid, x, active, flip) => { ctx.save(); ctx.globalAlpha = active ? 1 : 0.45; ctx.translate(x + (active ? (flip ? -12 : 12) * act : 0), 0); if (flip) { ctx.translate(150, 0); ctx.scale(-1, 1); ctx.translate(-150, 0); } drawPortrait(ctx, pid, 150, 484, 1, active ? node.mood : 'calm', t, active && shown < node.text.length); ctx.restore(); };
      if (left) portrait(left, 64, speakL, false);
      if (right) portrait(right, 916, speakR, true);
      panel(ctx, 272, 500, 736, 184, { seed: 61 });
      const plate = (x, nm, on) => { panel(ctx, x, 472, 220, 40, { seed: 62, bw: 3, fill: on ? 'rgba(250,244,230,0.98)' : 'rgba(236,230,216,0.8)' }); text(ctx, nm, x + 18, 500, { size: 22, font: FONT.title, color: on ? PAL.ink : PAL.w2 }); if (on) seal(ctx, x + 200, 492, 18, '', PAL.red); };
      if (left) plate(288, nameOf(left), speakL); if (right) plate(772, nameOf(right), speakR);
      const lines = wrap(ctx, node.text.slice(0, Math.floor(shown)), 680, 24, FONT.body);
      lines.slice(0, 4).forEach((l, i) => text(ctx, l, 300, 556 + i * 32, { size: 24 }));
      if (shown >= node.text.length && !node.choices) stroke(ctx, [[974, 652 + Math.sin(t * 7.5) * 4], [984, 664 + Math.sin(t * 7.5) * 4], [996, 646 + Math.sin(t * 7.5) * 4]], { w: 5, color: PAL.red, seed: 3, dry: 0 });
      if (node.choices && shown >= node.text.length) node.choices.forEach((c, i) => {
        const y = 248 + i * 72; panel(ctx, 424, y, 432, 56, { seed: 70 + i, bw: 3, fill: i === sel ? 'rgba(250,244,230,0.98)' : 'rgba(236,230,216,0.88)' });
        const ls = wrap(ctx, c.text, 380, 19); ls.slice(0, 2).forEach((l, k) => text(ctx, l, 456, y + (ls.length > 1 ? 24 : 35) + k * 21, { size: 19 }));
        if (i === sel) { seal(ctx, 440, y + 28, 14, '', PAL.red); stroke(ctx, [[452, y + 52], [840, y + 50]], { w: 4, color: PAL.red, seed: 9 + i, dry: 0.5 }); }
      });
      text(ctx, T('dialogue.advance', { confirm: 'A' }), 1000, 676, { size: 15, align: 'right', color: PAL.w2 });
    },
  };
}
