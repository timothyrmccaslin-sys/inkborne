// WORLD MAP: bold, abstract folding-screen strokes. The party token travels along paths between nodes.
import { PAL, paper, stroke, wash, seal, splat, rng } from '../ink.js';
import { T, text, panel, FONT } from '../ui.js';
export function create(game, params) {
  const W = game.data.world, N = Object.fromEntries(W.nodes.map((n) => [n.id, n]));
  let at = N[game.core.node()] ? game.core.node() : W.start; let travel = null, toast = null, cache = null;
  const neighbours = (id) => W.paths.filter((p) => p[0] === id || p[1] === id).map((p) => (p[0] === id ? p[1] : p[0]));
  const ctrl = (a, b) => { const A = N[a], B = N[b], mx = (A.x + B.x) / 2, my = (A.y + B.y) / 2, dx = B.x - A.x, dy = B.y - A.y; return [mx - dy * 0.18, my + dx * 0.18]; };
  const bez = (a, b, k) => { const A = N[a], B = N[b], C = ctrl(a, b); const u = 1 - k; return [u * u * A.x + 2 * u * k * C[0] + k * k * B.x, u * u * A.y + 2 * u * k * C[1] + k * k * B.y]; };
  function bake() { // static map layer: bold abstract strokes over Bob's painted screen
    const c = document.createElement('canvas'); c.width = 1280; c.height = 720; const x = c.getContext('2d');
    x.drawImage(paper(1280, 720, PAL.paper, 9), 0, 0);
    if (game.art.has('world-bg')) { x.save(); x.globalAlpha = 0.55; x.filter = 'contrast(1.25) blur(1.2px)'; x.drawImage(game.art.get('world-bg'), 0, 0, 1280, 720); x.restore(); }
    const r = rng(4);
    // huge mountain strokes (abstract), sea swells, forest dabs
    for (const [pts, w] of [[[[20, 330], [150, 150], [260, 120], [380, 210], [520, 160], [660, 260]], 46], [[[560, 240], [700, 170], [830, 230], [900, 200]], 30]]) stroke(x, pts, { w, seed: w, dry: 0.95, alpha: 0.8, taper: [0.08, 0.6] });
    for (let i = 0; i < 6; i++) stroke(x, [[820 + i * 40, 470 + i * 34], [980 + i * 40, 455 + i * 34], [1160 + i * 30, 470 + i * 34]], { w: 10 - i, seed: 30 + i, dry: 0.9, alpha: 0.35 });
    for (let i = 0; i < 26; i++) { const px = 40 + r() * 330, py = 520 + r() * 180; stroke(x, [[px, py + 22], [px + 4, py]], { w: 18 + r() * 12, seed: 50 + i, dry: 0.7, alpha: 0.55, taper: [0.1, 0.8] }); }
    // paths: thick wet strokes
    for (const [a, b] of W.paths) { const pts = []; for (let k = 0; k <= 12; k++) pts.push(bez(a, b, k / 12)); const lock = N[a].locked || N[b].locked; stroke(x, pts, { w: lock ? 6 : 12, seed: a.length * 7 + b.length, dry: 0.6, alpha: lock ? 0.35 : 0.8, taper: [0.15, 0.15] }); }
    cache = c;
  }
  function go(dir) {
    const opts = neighbours(at); let best = null, bs = 0.3;
    for (const o of opts) { const dx = N[o].x - N[at].x, dy = N[o].y - N[at].y, m = Math.hypot(dx, dy); const s = (dx * dir[0] + dy * dir[1]) / m; if (s > bs) { bs = s; best = o; } }
    if (!best) return;
    if (N[best].locked) { toast = { s: `${N[best].name}: ${T('world.locked', {}, 'the ink here is still too wet. Coming later.')}`, t: 2.4 }; game.audio.play('cancel'); return; }
    travel = { from: at, to: best, k: 0 }; game.audio.play('move');
  }
  return {
    enter() { game.audio.setScene('world'); if (!cache) bake(); game.core.set_node(at); game.save(); },
    resume() { game.audio.setScene('world'); },
    onResult() { game.enc.afterBattle(); game.save(); },
    update(dt, inp) {
      if (toast) { toast.t -= dt; if (toast.t <= 0) toast = null; }
      if (travel) { const k0 = travel.k; travel.k += dt / 0.9;
        const a = N[travel.from], b = N[travel.to], hit = game.enc.move({ scene: 'world', path: [travel.from, travel.to], dist: Math.hypot(b.x - a.x, b.y - a.y) * (travel.k - k0) });
        if (hit) { const tr = travel; at = tr.k > 0.5 ? tr.to : tr.from; travel = null; game.core.set_node(at); import('../encounters.js').then((m) => m.startBattle(game, hit)); return; } if ((travel.k * 6 | 0) !== ((travel.k - dt / 0.9) * 6 | 0)) game.audio.play('step', { gain: 0.2 }); if (travel.k >= 1) { at = travel.to; travel = null; game.core.set_node(at); } return; }
      const [mx, my] = inp.move();
      if (inp.pressed('right') || inp.pressed('left') || inp.pressed('up') || inp.pressed('down') || (Math.hypot(mx, my) > 0.6 && !this._held)) { go(Math.hypot(mx, my) > 0.1 ? [mx, my] : [inp.down('right') - inp.down('left'), inp.down('down') - inp.down('up')]); }
      this._held = Math.hypot(mx, my) > 0.6;
      for (const p of game.taps) { for (const n of W.nodes) if (Math.hypot(p.x - n.x, p.y - n.y) < 50) { if (n.id === at) enter(); else if (neighbours(at).includes(n.id)) go([n.x - N[at].x, n.y - N[at].y]); } }
      if (inp.pressed('confirm')) enter();
      function enter() { const n = N[at]; if (n.poi) { game.audio.play('confirm'); game.go('poi', { id: n.poi }); } else toast = { s: T('world.hint', {}, 'Walk the road to a painted place, then press A to enter.'), t: 2.4 }; }
    },
    draw(ctx, t) {
      ctx.drawImage(cache, 0, 0);
      // drifting cloud bands (subtle motion)
      for (let i = 0; i < 4; i++) wash(ctx, ((t * (8 + i * 3) + i * 400) % 1700) - 200, 110 + i * 120, 220, 26, PAL.paper, 0.5);
      wash(ctx, 1110, 110, 52, 52, PAL.red, 0.85); // sun
      for (const n of W.nodes) {
        const here = n.id === at, pulse = here ? 1 + Math.sin(t * 3) * 0.06 : 1;
        // enso node marker
        const pts = []; for (let k = 0; k <= 22; k++) { const a = -1.2 + k / 22 * Math.PI * 1.85; pts.push([n.x + Math.cos(a) * 26 * pulse, n.y + Math.sin(a) * 22 * pulse]); }
        stroke(ctx, pts, { w: n.locked ? 5 : 9, seed: n.x, dry: 0.7, alpha: n.locked ? 0.4 : 0.9, taper: [0.1, 0.5] });
        if (n.poi) seal(ctx, n.x, n.y, 18, n.poi === 'forest' ? '森' : '町', PAL.red, 0.9);
        text(ctx, n.name, n.x, n.y + 50, { size: 22, align: 'center', font: FONT.title, color: n.locked ? PAL.w3 : PAL.ink });
      }
      // party token: red seal on a small brush figure
      const p = travel ? bez(travel.from, travel.to, travel.k) : [N[at].x, N[at].y];
      const hop = travel ? Math.abs(Math.sin(travel.k * Math.PI * 6)) * 6 : Math.sin(t * 2.4) * 2;
      wash(ctx, p[0], p[1] - 4, 22, 8, PAL.ink, 0.3);
      seal(ctx, p[0], p[1] - 34 - hop, 30, '一', PAL.red);
      stroke(ctx, [[p[0], p[1] - 18 - hop], [p[0], p[1] - 4]], { w: 5, dry: 0 });
      panel(ctx, 24, 22, 380, 64, { seed: 3 });
      text(ctx, N[at].name, 40, 52, { size: 26, font: FONT.title });
      text(ctx, N[at].poi ? 'A: enter' : 'Move along the road', 40, 76, { size: 18, color: PAL.w2 });
      text(ctx, `${game.core.gold()} mon`, 390, 52, { size: 20, align: 'right', color: PAL.w1 });
      if (toast) { panel(ctx, 340, 640, 600, 50, { seed: 9 }); text(ctx, toast.s, 640, 672, { size: 20, align: 'center' }); }
    },
  };
}
