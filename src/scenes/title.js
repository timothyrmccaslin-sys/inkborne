// Title screen: Inkborne, the story hook (Lisa), Begin / Continue.
import { PAL, paper, stroke, wash, seal, splat } from '../ink.js';
import { T, text, wrap, menu, menuHit, FONT } from '../ui.js';
export function create(game) {
  let sel = 0, box = null, t0 = 0;
  const items = () => [{ label: T('title.new_game') }, ...(game.hasSave() ? [{ label: T('title.continue') }] : [])];
  return {
    enter() { game.audio.setScene('title'); t0 = game.t; },
    update(dt, inp) {
      const n = items().length;
      if (inp.pressed('down') || inp.pressed('right')) { sel = (sel + 1) % n; game.audio.play('move'); }
      if (inp.pressed('up') || inp.pressed('left')) { sel = (sel + n - 1) % n; game.audio.play('move'); }
      for (const p of game.taps) { const i = menuHit(box, n, p); if (i >= 0) { sel = i; start(); return; } }
      if (inp.pressed('confirm')) start();
      function start() {
        game.audio.unlock(); game.audio.play('confirm'); if (!game.standalone) game.fullscreen();
        if (sel === 1) game.load(); else { game.core.set_node(game.data.world.start); }
        game.go('world', {});
      }
    },
    draw(ctx, t) {
      const k = Math.min(1, (t - t0) / 1.6);
      ctx.drawImage(paper(1280, 720), 0, 0);
      if (game.art.has('world-bg')) { ctx.save(); ctx.globalAlpha = 0.28; ctx.drawImage(game.art.get('world-bg'), 0, 0, 1280, 720); ctx.restore(); }
      wash(ctx, 640, 250, 520, 170, PAL.paper, 0.75);
      // big brushed sun + title
      wash(ctx, 905, 150, 70, 70, PAL.red, 0.85 * k);
      stroke(ctx, [[260, 300], [520, 280], [780, 292], [1030, 276]], { w: 26 * k, seed: 11, dry: 0.9, alpha: 0.85, taper: [0.05, 0.5] });
      text(ctx, 'Inkborne', 640, 250, { size: 118, font: FONT.title, align: 'center', alpha: k });
      seal(ctx, 1000, 205, 64, '墨生');
      splat(ctx, 300, 205, 9, PAL.ink, 5, 0.7 * k);
      const lines = wrap(ctx, game.data.story.hook, 820, 21);
      lines.forEach((l, i) => text(ctx, l, 640, 352 + i * 27, { size: 21, align: 'center', color: PAL.w1, alpha: k }));
      box = menu(ctx, items(), sel, 560, 560, { w: 170, lh: 44, size: 28 });
      text(ctx, T('title.press_start', { confirm: game.input.source === 'pad' ? 'A' : game.input.source === 'touch' ? 'A' : 'Space' }), 640, 692, { size: 18, align: 'center', color: PAL.w2, alpha: 0.6 + 0.4 * Math.sin(t * 3) });
      text(ctx, `${game.version} · original story & art · Rust + WebAssembly`, 1268, 712, { size: 14, align: 'right', color: PAL.w3 });
    },
  };
}
