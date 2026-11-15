// ACTION: shop (Kōbō Tsuru). Buy/Sell tabs, item list, description, party compare, keeper line.
// Layout: Helen's LAYOUT_NOTES section 4. Economy (prices, stock): Jane via data/shops.json + items.json.
// TODO(art): item icons (icon-<id>, Luc) and keeper portrait (Kenji) are procedural placeholders.
import { PAL, paper, stroke, wash, seal } from '../ink.js';
import { drawPortrait } from '../figures.js';
import { T, text, panel, wrap, bar, FONT } from '../ui.js';
const ICON = { heal: '餅', healall: '茶', ink: '墨', bomb: '爆', gear: '具' };
export function create(game, params) {
  const shop = game.data.shops[params.shop], core = game.core, A = game.audio, D = game.data.dialogue;
  const line = (k) => { const s = D[`shop_tsuru_${k}`]; return s ? s.nodes[s.start].text : ''; };
  let tab = 0, sel = 0, qty = 0, mood = 'smile', say = line(core.flag('met_tsuru') ? 'greet_again' : 'greet'), shownMon = core.gold(), top = 0;
  const inv = () => JSON.parse(core.inventory_json());
  const list = () => { const v = inv().items; return tab === 0 ? shop.stock.map((id) => v.find((x) => x.id === id)).filter(Boolean) : v.filter((x) => x.count > 0); };
  const party = () => JSON.parse(core.party_json());
  return {
    enter() { core.set_flag('met_tsuru', true); A.setScene('shop'); A.voice('tsuru', 'talk'); },
    update(dt, inp) {
      const g = core.gold(); shownMon += Math.sign(g - shownMon) * Math.min(Math.abs(g - shownMon), dt * 60);
      const L = list(); if (sel >= L.length) sel = Math.max(0, L.length - 1);
      const tap = game.taps[0];
      if (qty) { // S9 qty stepper
        const it = L[sel], max = tab === 0 ? Math.max(1, Math.floor(g / it.price)) : it.count;
        if (inp.pressed('right') || inp.pressed('up')) { qty = Math.min(max, qty + 1); A.play('move'); } if (inp.pressed('left') || inp.pressed('down')) { qty = Math.max(1, qty - 1); A.play('move'); }
        if (inp.pressed('cancel')) { qty = 0; A.play('cancel'); return; }
        if (inp.pressed('confirm') || (tap && tap.y > 620)) {
          const ok = tab === 0 ? core.buy(it.id, qty) : core.sell(it.id, qty);
          if (ok) { A.play('coin'); mood = 'smile'; say = line(tab === 0 ? 'buy_ok' : 'sell_ok') || T(tab === 0 ? 'shop.bought' : 'shop.sold', { item: it.name, qty }); A.voice('tsuru', 'talk'); game.save(); }
          else { A.play('cancel'); mood = 'sad'; say = line('buy_poor') || T('shop.insufficient_funds'); }
          qty = 0;
        }
        return;
      }
      if (inp.pressed('left') || inp.pressed('right')) { tab = 1 - tab; sel = 0; A.play('move'); say = line(tab ? 'sell' : 'buy'); mood = 'calm'; }
      if (inp.pressed('down') && L.length) { sel = (sel + 1) % L.length; A.play('move'); } if (inp.pressed('up') && L.length) { sel = (sel + L.length - 1) % L.length; A.play('move'); }
      if (tap) { if (tap.y < 92 && tap.x < 384) { tab = tap.x < 224 ? 0 : 1; sel = 0; A.play('move'); } const r = Math.floor((tap.y - 132) / 60), i = r >= 0 && r < 8 ? Math.max(0, Math.min(sel - 7, L.length - 8)) + r : -1; if (tap.x > 336 && tap.x < 784 && i >= 0 && i < L.length) { if (i === sel) { qty = 1; } else sel = i; A.play('move'); } }
      if (inp.pressed('confirm') && L.length) { const it = L[sel]; if (tab === 0 && g < it.price) { A.play('cancel'); mood = 'sad'; say = line('buy_poor'); } else { qty = 1; A.play('confirm'); } }
      if (inp.pressed('confirm') && !L.length && tab === 1) say = T('shop.nothing_to_sell');
      if (inp.pressed('cancel') || inp.pressed('menu')) { A.play('cancel'); say = line('leave'); game.save(); game.pop({}); }
    },
    draw(ctx, t) {
      const bg = params.bg && game.art.get('poi-town-mid') ; ctx.drawImage(paper(1280, 720, '#efe8d8', 11), 0, 0);
      if (bg) { ctx.save(); ctx.globalAlpha = 0.18; ctx.filter = 'blur(4px)'; ctx.drawImage(bg, 0, 0, 1280, 720); ctx.restore(); }
      // noren cloth across the top, swaying
      for (let i = 0; i < 5; i++) { const x = 400 + i * 82, sw = Math.sin(t * 1.3 + i) * 3; ctx.save(); ctx.fillStyle = 'rgba(62,58,51,0.12)'; ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x + 78, 0); ctx.lineTo(x + 78 + sw, 30); ctx.lineTo(x + sw, 30); ctx.fill(); ctx.restore(); }
      const L = list(), it = L[sel], g = core.gold();
      // S1 tabs, S2 title, S3 mon
      ['shop.buy', 'shop.sell'].forEach((k, i) => { text(ctx, T(k), 104 + i * 160, 74, { size: 30, font: FONT.title, align: 'center', color: tab === i ? PAL.ink : PAL.w2 }); if (tab === i) stroke(ctx, [[64 + i * 160, 86], [144 + i * 160, 84]], { w: 6, color: PAL.red, seed: 4 + i }); });
      text(ctx, shop.name, 600, 76, { size: 40, font: FONT.title, align: 'center' }); seal(ctx, 790, 64, 26, '鶴', PAL.red);
      panel(ctx, 936, 36, 200, 56, { seed: 81, bw: 3 }); seal(ctx, 966, 64, 22, '文', '#b08a3a'); text(ctx, `${Math.round(shownMon)} mon`, 1120, 74, { size: 26, align: 'right', font: FONT.title });
      // S4/S5 keeper
      ctx.save(); drawPortrait(ctx, 'tsuru', 188, 422, 0.82, mood, t, false); ctx.restore();
      panel(ctx, 64, 430, 248, 40, { seed: 82, bw: 3 }); text(ctx, 'Grandmother Tsuru', 188, 458, { size: 21, align: 'center', font: FONT.title });
      // S6 list
      panel(ctx, 336, 112, 448, 500, { seed: 83 });
      text(ctx, tab ? T('shop.owned',{n:''}).replace(/[:\s]+$/,'') : 'Price', 764, 130, { size: 15, align: 'right', color: PAL.w2 });
      if (!L.length) text(ctx, T('shop.nothing_to_sell'), 560, 300, { size: 22, align: 'center', color: PAL.w2 });
      const off = Math.max(0, Math.min(sel - 7, L.length - 8)); if (off > 0) text(ctx, '▲', 560, 128, { size: 14, align: 'center', color: PAL.w2 }); if (off + 8 < L.length) text(ctx, '▼', 560, 622, { size: 14, align: 'center', color: PAL.w2 });
      L.slice(off, off + 8).forEach((x, j) => { const i = j + off, y = 132 + j * 60;
        if (i === sel) { ctx.save(); ctx.fillStyle = 'rgba(179,38,30,0.08)'; ctx.fillRect(344, y, 432, 58); ctx.restore(); stroke(ctx, [[384, y + 54], [770, y + 52]], { w: 3, color: PAL.red, seed: 20 + j, dry: 0.4 }); }
        if (!drawIcon(ctx, x, 372, y + 29, 48)) {} text(ctx, x.name, 408, y + 30, { size: 22, color: tab === 0 && g < x.price ? PAL.w2 : PAL.ink }); text(ctx, T('shop.owned',{n:x.count}), 408, y + 50, { size: 14, color: PAL.w2 });
        text(ctx, `${tab ? x.sell : x.price} mon`, 764, y + 36, { size: 21, align: 'right' }); });
      // S7 description
      panel(ctx, 808, 112, 408, 224, { seed: 84 });
      if (it) { drawIcon(ctx, it, 880, 190, 110); text(ctx, it.name, 950, 160, { size: 26, font: FONT.title }); wrap(ctx, it.desc, 250, 18).slice(0, 6).forEach((l, k) => text(ctx, l, 950, 190 + k * 22, { size: 18, color: PAL.w1 })); }
      // S8 party compare
      panel(ctx, 808, 352, 408, 136, { seed: 85 });
      if (it) { const P = party(), item = game.data.items.items.find((z) => z.id === it.id) || {};
        P.forEach((m, k) => { const y = 380 + k * 40; text(ctx, m.name, 830, y + 6, { size: 18, font: FONT.title });
          let now, after, max = m.maxHp, lab = 'HP';
          if (it.kind === 'ink') { lab = 'Ink'; now = m.ink; after = Math.min(100, now + (item.power || 0)); max = 100; } else { now = m.hp; after = it.kind === 'heal' || it.kind === 'healall' ? Math.min(max, now + (item.power || 0)) : now; }
          bar(ctx, 930, y - 6, 140, 8, now / max, lab === 'Ink' ? PAL.red : PAL.w1); text(ctx, `${lab} ${Math.round(now)} → ${Math.round(after)}`, 1200, y + 6, { size: 16, align: 'right', color: after > now ? PAL.red : PAL.w2 }); if (after > now && tab === 0) text(ctx, '▲', 1082, y + 4, { size: 14, color: PAL.red }); });
        if (it.kind === 'gear') { const eq = (game.data.items.equipment || []).find((z) => z.id === it.id) || {}; const mods = Object.entries(eq.mods || {}).map(([k, v]) => `${k.toUpperCase()} +${v}`).join('  '); text(ctx, `${(eq.slot || 'gear').toUpperCase()}  ${mods}`, 1012, 292, { size: 16, align: 'center', color: PAL.red }); text(ctx, 'Equip screen arrives in a later build.', 1012, 314, { size: 14, align: 'center', color: PAL.w2 }); }
        if (it.kind === 'bomb') text(ctx, 'For throwing at ink-beasts, not friends.', 1012, 476, { size: 15, align: 'center', color: PAL.w2 }); }
      // S9 keeper line / qty stepper
      panel(ctx, 272, 628, 736, 56, { seed: 86 });
      if (qty && it) { const tot = qty * (tab ? it.sell : it.price); text(ctx, `${tab ? T('shop.sell') : T('shop.buy')} ${it.name}  ◀ ${qty} ▶   ${T('shop.total',{n:tot})}   (A ${T('shop.yes')} / B ${T('shop.no')})`, 640, 664, { size: 20, align: 'center' }); }
      else text(ctx, say, 640, 664, { size: 20, align: 'center', color: PAL.w1 });
      text(ctx, 'B: leave', 1200, 700, { size: 14, align: 'right', color: PAL.w2 });
    },
  };
  function drawIcon(ctx, it, x, y, s) {
    const key = 'icon-' + it.id; if (game.art.has(key)) { ctx.drawImage(game.art.get(key), x - s / 2, y - s / 2, s, s); return true; }
    wash(ctx, x, y, s * 0.42, s * 0.42, it.kind === 'ink' || it.kind === 'bomb' ? PAL.red : PAL.ink, 0.18); seal(ctx, x, y, s * 0.6, ICON[it.kind] || '品', it.kind === 'bomb' ? PAL.ink : PAL.red, 0.85); return false;
  }
}
