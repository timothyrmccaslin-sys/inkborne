// ACTION: battle. Turn-based party battle with Brushstroke Chains (timed presses on a closing ring),
// Vermilion Ink, Unfurl into an Inkwing form, Seal Arts (press as the brush passes each seal),
// Still Water and items. Rules + judgement live in the Rust core; this file is presentation.
// Layout from Helen's LAYOUT_NOTES (B3 banner, B4 party HUD, B5 command menu, stage anchors).
import { PAL, paper, stroke, wash, seal, splat, rng } from '../ink.js';
import { drawPerson, drawEnemy } from '../figures.js';
import { drawStrip, stripFrames } from '../art.js';
import { T, text, panel, bar, menu, menuHit, FONT, wrap } from '../ui.js';
const PARTY_POS = { benika: [340, 430], itsuki: [470, 495], gonzo: [615, 565] };
const ENEMY_POS = { hollow_lantern: [860, 300], smudge_ronin: [1010, 440], blotling: [1150, 455] };
const EXTRA_POS = [[1000, 520], [1150, 330]];
const ELEM_TINT = { gale: '#5f8a6a', ember: '#c2452d', stone: '#7a6a52', tide: '#2f5d7c', dawn: '#d9b45a', dusk: '#4b3b63' };
const FORM = { itsuki: 'Gale Crane', benika: 'Ember Kite', gonzo: 'Stone Owl' };
const now = () => performance.now();
export function create(game, params) {
  const core = game.core, A = game.audio, art = game.art, W = JSON.parse(core.windows_json());
  const partyDef = Object.fromEntries(game.data.party.members.map((m) => [m.id, m]));
  let st = null, F = [], vis = [], phase = 'intro', tPhase = 0, sel = 0, sub = null, target = 0, box = null;
  let chain = null, sealg = null, unfurl = null, queue = [], banner = null, floaters = [], fx = [], shake = 0, bark = null, result = null, hint = null, seenHint = false, rewards = null;
  const r = rng(7), motes = Array.from({ length: 16 }, () => ({ x: r() * 1280, y: r() * 720, s: 0.5 + r(), v: 10 + r() * 20, p: r() * 6 }));
  function refresh() { st = JSON.parse(core.battle_json()); F = st.fighters; }
  function home(i) { const f = F[i]; if (f.side === 0) return PARTY_POS[f.id] || [300 + i * 120, 480]; const ids = F.filter((x) => x.side === 1).map((x) => x.id); const k = F.slice(0, i).filter((x) => x.side === 1 && x.id === f.id).length; const p = ENEMY_POS[f.id]; return k === 0 && p ? p : EXTRA_POS[(k + ids.indexOf(f.id)) % EXTRA_POS.length]; }
  const hitPt = (i) => { const [x, y] = vis[i].pos; const f = F[i]; return f.side === 1 ? [x - 10, y - (f.id === 'hollow_lantern' ? 120 : f.id === 'smudge_ronin' ? 150 : 50)] : [x + 10, y - 110]; };
  const alive = (side) => F.map((f, i) => [f, i]).filter(([f]) => f.side === side && f.alive).map(([, i]) => i);
  const name = (i) => (F[i].side === 0 ? partyDef[F[i].id].name : F[i].name);
  function say(id, ev) { const b = game.data.barks[id] && game.data.barks[id][ev]; if (b && b.length) bark = { i: F.findIndex((f) => f.id === id), s: b[(Math.random() * b.length) | 0], t: 2.4 }; }
  function float(i, s, color, big) { const p = hitPt(i); floaters.push({ x: p[0] + (Math.random() - 0.5) * 20, y: p[1] - 10, s: String(s), c: color || PAL.ink, t: 0, big }); }
  function addFx(key, x, y, o = {}) { if (art.has(key)) fx.push({ key, x, y, t: 0, n: stripFrames(art, key), fps: art.meta[key].fps || 12, ...o }); }
  function setBanner(s, red, d = 1.6) { banner = { s, red, t: d }; }
  function seq(d, on, done) { queue.push({ d, t: 0, on, done }); }
  const cur = () => st.turn;

  function nextTurn() {
    refresh();
    if (st.over) { phase = st.over; tPhase = 0; result = st.over; if (st.over === 'win') { A.stopMusic(0.4); A.sting('extra-victory-fanfare'); setTimeout(() => A.music('extra-victory-loop'), 2600); const lead = alive(0)[0]; if (lead != null) say(F[lead].id, 'victory'); } else { A.stopMusic(1.5); } return; }
    const c = cur(); if (c < 0) return;
    if (F[c].side === 1) { phase = 'enemy'; tPhase = 0; return; }
    phase = 'menu'; sel = 0; sub = null; tPhase = 0;
  }
  function commands() {
    const f = F[cur()], iw = f.inkwing > 0, full = f.ink >= 100;
    const list = [];
    if (iw) list.push({ id: 'seal', label: T('battle.menu.seal_arts') });
    list.push({ id: 'stroke', label: T('battle.menu.brushstroke') });
    if (!iw) list.push({ id: 'unfurl', label: T('battle.menu.unfurl'), disabled: !full });
    list.push({ id: 'guard', label: T('battle.menu.still_water') }, { id: 'items', label: T('battle.menu.items') });
    list.push({ id: 'flee', label: T('battle.menu.flee'), dim: !!params.boss || params.canFlee === false });
    return list;
  }
  function inventory() { return JSON.parse(core.inventory_json()).items.filter((x) => x.count > 0 && x.kind !== 'gear'); }

  // ---------- actions ----------
  function startChain(actor, tgt, strokeIdx) {
    const s = partyDef[F[actor].id].strokes[strokeIdx];
    phase = 'chain'; vis[actor].dash = 0;
    chain = { actor, tgt, strokeIdx, s, k: -1, grades: [], start: 0, close: 0, msg: null, done: false, t0: now() };
    say(F[actor].id, 'brushstroke');
    setBanner(s.name, false, 1.2);
    seq(0.25, (k) => { vis[actor].dash = k; }, () => nextRing());
  }
  function nextRing() { const c = chain; c.k++; if (c.k >= c.s.hits.length) return finishChain(); c.start = now(); c.close = c.start + c.s.hits[c.k].gap_ms; A.play('ring', { gain: 0.35 }); }
  function judgePress(ts) {
    const c = chain; if (!c || c.k < 0 || c.done || c.k >= c.s.hits.length) return;
    const delta = ts - c.close; let g = delta < -W.good ? 0 : core.judge(delta);
    c.grades.push(g); const [hx, hy] = hitPt(c.tgt);
    vis[c.actor].action = 'strike'; vis[c.actor].ph = 0;
    if (g === 0) { c.msg = { s: T('combo.miss'), t: 0.8, c: PAL.w2 }; A.play('miss'); addFx('fx-brushstroke-fail', hx, hy); return finishChain(); }
    if (g === 2) { c.msg = { s: T('combo.clean_line'), t: 0.8, c: PAL.red }; A.play('clean'); addFx('fx-brushstroke-clean-line', hx, hy); setBanner(T('combo.clean_line'), true, 0.7); }
    else { c.msg = { s: T('combo.good'), t: 0.7, c: PAL.ink }; A.play('hit'); addFx('fx-hit-light', hx, hy); }
    A.voice(F[c.actor].id, 'attack'); vis[c.tgt].action = 'hit'; vis[c.tgt].ph = 0; shake = g === 2 ? 4 : 2;
    nextRing();
  }
  function finishChain() {
    const c = chain; c.done = true; c.k = c.s.hits.length;
    const res = JSON.parse(core.stroke(c.actor, c.tgt, c.strokeIdx, new Uint8Array(c.grades)));
    let delay = 0;
    for (const e of res.events) { if (e.dmg == null) continue; const d = delay; setTimeout(() => { float(e.target, e.dmg, e.grade === 2 ? PAL.red : PAL.ink, e.grade === 2); if (e.killed) kill(e.target); }, d); delay += 120; }
    if (res.perfect) { setTimeout(() => { A.play('seal'); A.play('combo-finish'); stamp = { t: 0 }; shake = 3; say(F[c.actor].id, 'clean_line'); setBanner(`${c.s.name}! ${T('combo.all_clean')}`, true, 1.4); }, delay); }
    else if (res.full) setTimeout(() => { A.play('hit-heavy'); setBanner(T('combo.complete'), false, 1.0); }, delay);
    seq(0.45 + delay / 1000, () => {}, () => seq(0.25, (k) => { vis[c.actor].dash = 1 - k; }, () => { chain = null; nextTurn(); }));
  }
  let stamp = null;
  function kill(i) { vis[i].action = 'die'; vis[i].ph = 0; A.play('enemy-defeat'); const [x, y] = vis[i].pos; addFx('fx-death-ink', x, y); }
  function doUnfurl(actor) {
    phase = 'unfurl'; const f = F[actor], el = f.element;
    unfurl = { actor, t: 0, el, applied: false };
    A.play('inkwing'); A.sting('extra-transform-sting'); A.voice(f.id, 'unfurl'); say(f.id, 'unfurl');
  }
  function startSeal(actor) {
    const m = partyDef[F[actor].id], n = m.seal.seals, period = 3200;
    const seals = Array.from({ length: n }, (_, i) => ({ ang: -Math.PI / 2 + (i + 1) * (Math.PI * 2) / (n + 1), res: null }));
    sealg = { actor, m, n, start: now() + 600, period, seals, msg: null };
    for (const s of sealg.seals) s.time = sealg.start + ((s.ang + Math.PI / 2) / (Math.PI * 2)) * period;
    phase = 'seal'; setBanner(m.seal.name, true, 1.4); say(F[actor].id, 'seal_arts');
  }
  function sealPress(ts) {
    const g = sealg; let best = null, bd = 1e9; for (const s of g.seals) if (!s.res) { const d = Math.abs(ts - s.time); if (d < bd) { bd = d; best = s; } }
    if (!best || bd > 320) return; const grade = bd > W.good ? 0 : core.judge(ts - best.time);
    best.res = grade === 2 ? 'clean' : grade === 1 ? 'hit' : 'miss';
    A.play(grade ? 'seal' : 'miss', { gain: grade ? 0.6 : 0.6 }); g.msg = { s: grade === 2 ? T('combo.clean_line') : grade ? T('seal.hit') : T('seal.miss'), t: 0.6, c: grade ? PAL.red : PAL.w2 };
    best.fx = 0;
  }
  function finishSeal() {
    const g = sealg; const hits = g.seals.filter((s) => s.res === 'hit' || s.res === 'clean').length, clean = g.seals.filter((s) => s.res === 'clean').length;
    const res = JSON.parse(core.seal_art(g.actor, hits, clean)); phase = 'anim';
    setBanner(`${g.m.seal.name}!`, true, 1.6); vis[g.actor].action = 'cast'; vis[g.actor].ph = 0;
    for (const e of res.events) { const [x, y] = vis[e.target].pos; addFx(`fx-seal-${res.element}`, x, y, { scale: 0.8 }); setTimeout(() => { float(e.target, e.dmg, e.elem > 1 ? PAL.red : PAL.ink, true); if (e.elem > 1) setBanner(T('battle.log.weak', { element: res.element[0].toUpperCase() + res.element.slice(1) }), true, 1.2); vis[e.target].action = 'hit'; vis[e.target].ph = 0; A.play('hit-heavy'); shake = 5; if (e.killed) kill(e.target); }, 700); }
    for (const h of res.heals || []) setTimeout(() => { if (h.heal > 0) float(h.target, '+' + h.heal, '#5f8a6a'); }, 900);
    sealg = null; seq(1.6, () => {}, nextTurn);
  }
  function doGuard(actor) { const res = JSON.parse(core.guard(actor)); A.play('guard'); A.voice(F[actor].id, 'grunt'); say(F[actor].id, 'still_water'); vis[actor].action = 'guard'; vis[actor].ph = 0; float(actor, '+' + res.heal, '#5f8a6a'); setBanner(T('battle.log.still_water', { name: name(actor) }), false, 1.2); phase = 'anim'; seq(0.9, () => {}, nextTurn); }
  function doFlee(actor) {
    const res = JSON.parse(core.flee(actor));
    if (!res.ok) { A.play('cancel'); setBanner(T('battle.log.flee_blocked'), false, 1.6); return; }
    phase = 'anim';
    if (res.fled) { setBanner(T('battle.log.flee_ok'), false, 1.2); seq(1.0, () => {}, () => game.pop({ fled: true })); }
    else { setBanner(T('battle.log.flee_fail'), false, 1.2); refresh(); seq(0.9, () => {}, nextTurn); }
  }
  function doItem(actor, item, tgt) {
    const res = JSON.parse(core.use_item(actor, item.id, tgt)); if (!res.ok) { A.play('cancel'); setBanner(res.reason === 'inkwing' ? 'The Inkwing needs no more ink.' : T('battle.menu.no_items'), false, 1.4); phase = 'menu'; sub = null; return; } phase = 'anim';
    setBanner(T('battle.log.item_used', { name: name(actor), item: item.name }), false, 1.3);
    for (const e of res.events) { if (e.heal != null) { float(e.target, '+' + e.heal, '#5f8a6a'); A.play('heal'); } if (e.ink != null) { float(e.target, 'Ink ' + Math.round(e.ink), PAL.red); A.play('heal'); } if (e.dmg != null) { const [x, y] = hitPt(e.target); addFx('fx-hit-heavy', x, y); float(e.target, e.dmg, e.elem > 1 ? PAL.red : PAL.ink, true); A.play('hit-heavy'); if (e.killed) kill(e.target); } }
    seq(1.0, () => {}, nextTurn);
  }
  function enemyAct() {
    const me = cur(); const res = JSON.parse(core.enemy_turn()); phase = 'anim';
    setBanner(`${F[me].name}: ${res.move}`, false, 1.2); vis[me].action = 'attack'; vis[me].ph = 0;
    seq(0.42, () => {}, () => {
      refresh(); const t = res.target; const [x, y] = hitPt(t);
      addFx('fx-hit-light', x, y, { flip: true }); float(t, res.dmg, res.elem > 1 ? PAL.red : PAL.ink); A.play('enemy-hit'); A.voice(F[t].id, res.killed ? 'ko' : 'grunt'); shake = 3;
      vis[t].action = res.killed ? 'ko' : res.guarded ? 'guard' : 'hit'; vis[t].ph = 0; if (res.guarded) floaters.push({ ...floaters[floaters.length - 1], s: T('battle.menu.still_water'), y: y - 40, c: '#5f8a6a', t: 0 });
      if (!res.killed && Math.random() < 0.5) say(F[t].id, 'hurt'); if (res.killed) say(F[t].id, 'ko');
      seq(0.7, () => {}, nextTurn);
    });
  }

  // ---------- scene ----------
  const sc = {
    phaseName: () => phase, chainState: () => chain, sealState: () => sealg, fighters: () => F,
    enter() {
      refresh(); rewards = null; core.start_battle_opts(params.enc, JSON.stringify({ first: params.first ?? null, canFlee: !params.boss && params.canFlee !== false })); refresh();
      if (params.boss) { const i = F.findIndex((f) => f.id === 'itsuki'); if (i >= 0 && F[i].ink < 100) { core.debug_ink(i, 100); hint = { s: 'The seal-stone bleeds red ink into Itsuki\'s palm. Vermilion Ink is full: Unfurl!', t: 4.5 }; } refresh(); }
      vis = F.map((f, i) => ({ pos: home(i), action: f.alive ? 'idle' : 'ko', ph: 0, dash: 0, iw: f.inkwing > 0 ? 1 : 0 }));
      A.setScene('battle'); const n = alive(1).length; setBanner(n > 1 ? T('battle.log.appears_many', { count: n }) : T('battle.log.appears', { enemy: F[alive(1)[0]].name }), false, 1.8);
      phase = 'intro'; tPhase = 0; say(params.boss ? 'benika' : 'itsuki', 'battle_start');
    },
    overlay: false,
    update(dt, inp) {
      tPhase += dt; shake = Math.max(0, shake - dt * 14);
      if (banner) { banner.t -= dt; if (banner.t <= 0) banner = null; } if (bark) { bark.t -= dt; if (bark.t <= 0) bark = null; } if (hint) { hint.t -= dt; if (hint.t <= 0) hint = null; }
      for (const v of vis) { v.ph += dt / (v.action === 'strike' ? 0.32 : v.action === 'die' ? 1.1 : 0.5); if (v.ph >= 1 && !['ko', 'die', 'guard'].includes(v.action)) { v.action = 'idle'; v.ph = 0; } if (v.action === 'die' && v.ph >= 1) v.gone = true; }
      F.forEach((f, i) => { vis[i].iw += ((f.inkwing > 0 ? 1 : 0) - vis[i].iw) * Math.min(1, dt * 3); if (f.side === 0 && f.alive && vis[i].action === 'ko') vis[i].action = 'idle'; });
      for (const f of floaters) f.t += dt; floaters = floaters.filter((f) => f.t < 1.3);
      for (const f of fx) f.t += dt; fx = fx.filter((f) => f.loop || f.t * f.fps < f.n);
      if (stamp) { stamp.t += dt; if (stamp.t > 1.0) stamp = null; }
      if (queue.length) { const q = queue[0]; q.t += dt; q.on && q.on(Math.min(1, q.t / q.d)); if (q.t >= q.d) { queue.shift(); q.done && q.done(); } }
      const press = inp.pressed('confirm') || game.taps.length > 0, pressTs = inp.pressed('confirm') ? inp.pressedAt('confirm') : game.taps.length ? now() : 0;
      if (phase === 'intro') { if (tPhase > 1.3 || (press && tPhase > 0.4)) nextTurn(); return; }
      if (phase === 'enemy') { if (tPhase > 0.6) enemyAct(); return; }
      if (phase === 'chain') { if (!seenHint) { seenHint = true; hint = { s: T('combo.hint', {}, 'Press A as the red ring closes on the circle. Tight timing is a Clean Line.'), t: 3.5 }; }
        if (chain && chain.k >= 0 && !chain.done) { if (inp.pressed('confirm')) judgePress(inp.pressedAt('confirm')); else if (game.taps.length) judgePress(now()); else if (now() > chain.close + W.good && chain.k < chain.s.hits.length) { chain.grades.push(0); chain.msg = { s: T('combo.miss'), t: 0.8, c: PAL.w2 }; A.play('miss'); const [hx, hy] = hitPt(chain.tgt); addFx('fx-brushstroke-fail', hx, hy); finishChain(); } }
        if (chain && chain.msg) chain.msg.t -= dt; return; }
      if (phase === 'seal') { const g = sealg; if (press && now() > g.start - 200) sealPress(pressTs); for (const s of g.seals) { if (!s.res && now() > s.time + W.good) { s.res = 'miss'; } if (s.fx != null) s.fx += dt; } if (g.msg) g.msg.t -= dt; if (now() > g.start + g.period + 250) finishSeal(); return; }
      if (phase === 'unfurl') { const u = unfurl; u.t += dt; if (u.t > 0.6 && !u.applied) { u.applied = true; const res = JSON.parse(core.inkwing(u.actor)); refresh(); setBanner(T('battle.unfurl.announce', { name: name(u.actor), inkwing: FORM[F[u.actor].id] || 'Inkwing' }), true, 2.6); if (res.heal) float(u.actor, '+' + res.heal, '#5f8a6a'); shake = 4; }
        if (u.t > 3.2 || (press && u.t > 2.2)) { unfurl = null; nextTurn(); } return; }
      if (phase === 'win' || phase === 'lose') { if (tPhase > 1.2 && press) { if (phase === 'win') { if (params.flag) core.set_flag(params.flag, true); game.pop({ win: true }); } else { core.rest(); game.pop({ lose: true }); } phase = 'done'; } return; }
      if (phase === 'menu') {
        const cmds = commands();
        if (sub) return subUpdate(inp, cmds);
        if (inp.pressed('down')) { sel = (sel + 1) % cmds.length; A.play('move'); } if (inp.pressed('up')) { sel = (sel + cmds.length - 1) % cmds.length; A.play('move'); }
        if (inp.pressed('cancel')) { const g = cmds.findIndex((c) => c.id === 'guard'); sel = g; }
        let pick = inp.pressed('confirm') ? sel : -1; for (const p of game.taps) { const i = menuHit(box, cmds.length, p); if (i >= 0) pick = sel = i; }
        if (pick < 0) return; const c = cmds[pick]; if (c.disabled) { A.play('cancel'); setBanner(T('battle.menu.unfurl_locked'), false, 1.2); return; }
        if (c.id === 'flee' && c.dim) { A.play('cancel'); setBanner(T('battle.log.flee_blocked', {}, 'The Ronin bars the path. There is no slipping away.'), false, 1.6); return; }
        A.play('confirm');
        if (c.id === 'stroke') { const ss = partyDef[F[cur()].id].strokes; sub = ss.length > 1 ? { kind: 'stroke', sel: 0, list: ss.map((s) => ({ label: s.name, sub: s.hits.length + ' hits' })) } : { kind: 'target', side: 1, then: (t) => startChain(cur(), t, 0) }; if (sub.kind === 'target') target = alive(1)[0]; }
        if (c.id === 'seal') startSeal(cur());
        if (c.id === 'unfurl') doUnfurl(cur());
        if (c.id === 'guard') doGuard(cur());
        if (c.id === 'items') { const inv = inventory(); if (!inv.length) { setBanner(T('battle.menu.no_items'), false, 1.2); return; } sub = { kind: 'item', sel: 0, inv, list: inv.map((x) => ({ label: x.name, sub: 'x' + x.count })) }; }
        if (c.id === 'flee') doFlee(cur());
      }
    },
    draw(ctx, t) {
      const sx = (Math.random() - 0.5) * shake, sy = (Math.random() - 0.5) * shake;
      ctx.save(); ctx.translate(sx, sy);
      if (art.has(params.bg || 'battle-forest')) ctx.drawImage(art.get(params.bg || 'battle-forest'), -10, -6, 1300, 732); else ctx.drawImage(paper(1280, 720), 0, 0);
      if (phase === 'unfurl') { const k = Math.min(1, unfurl.t / 0.5) * (unfurl.t > 2.6 ? Math.max(0, 1 - (unfurl.t - 2.6) / 0.6) : 1); ctx.save(); ctx.globalAlpha = 0.6 * k; ctx.fillStyle = PAL.paper; ctx.fillRect(-20, -20, 1320, 760); ctx.restore(); }
      for (let i = 0; i < 4; i++) wash(ctx, ((t * (12 + i * 5) + i * 400) % 1700) - 200, 380 + i * 50, 260, 26, PAL.paper, 0.35);
      // fighters, depth sorted
      const order = F.map((f, i) => i).sort((a, b) => vis[a].pos[1] - vis[b].pos[1]);
      for (const i of order) drawFighter(ctx, i, t);
      for (const m of motes) { m.y += m.v * 0.016; m.x += Math.sin(t + m.p) * 0.3; if (m.y > 720) m.y = -10; stroke(ctx, [[m.x, m.y], [m.x + 6 * m.s, m.y + 3 * m.s]], { w: 4 * m.s, color: PAL.w1, alpha: 0.5, seed: m.p * 9 | 0, dry: 0, bleed: false }); }
      for (const f of fx.filter((f) => !f.behind)) drawStrip(art, ctx, f.key, Math.floor(f.t * f.fps), f.x, f.y, f.scale || 1, f.flip);
      // chain ring
      if (phase === 'chain' && chain && chain.k >= 0 && !chain.done && chain.k < chain.s.hits.length) {
        const [hx, hy] = hitPt(chain.tgt), gap = chain.s.hits[chain.k].gap_ms, k = Math.max(0, Math.min(1.25, (now() - chain.start) / gap)), rr = 96 - 48 * k;
        const ens = []; for (let j = 0; j <= 26; j++) { const a = -1.3 + j / 26 * Math.PI * 1.92; ens.push([hx + Math.cos(a) * 48, hy + Math.sin(a) * 48]); }
        stroke(ctx, ens, { w: 7, seed: 3, dry: 0.6, alpha: 0.9 });
        ctx.save(); ctx.strokeStyle = PAL.red; ctx.globalAlpha = 0.5; ctx.lineWidth = 2; ctx.beginPath(); ctx.arc(hx, hy, 48 - 7, 0, Math.PI * 2); ctx.stroke(); ctx.restore();
        ctx.save(); ctx.strokeStyle = PAL.red; ctx.lineWidth = 6 + 4 * k; ctx.globalAlpha = 0.85; ctx.beginPath(); ctx.arc(hx, hy, Math.max(20, rr), 0, Math.PI * 2); ctx.stroke(); ctx.restore();
        // stroke pips (B7)
        chain.s.hits.forEach((h, j) => { const g = chain.grades[j], px = hx - (chain.s.hits.length - 1) * 14 + j * 28, py = hy + 130 > 470 ? hy - 80 : hy + 130; ctx.save(); ctx.fillStyle = g === 2 ? PAL.red : g === 1 ? PAL.w2 : 'rgba(27,24,19,0.15)'; ctx.beginPath(); ctx.arc(px, py, 8, 0, Math.PI * 2); ctx.fill(); ctx.restore(); });
      }
      if (chain && chain.msg && chain.msg.t > 0) { const [hx, hy] = hitPt(chain.tgt); text(ctx, chain.msg.s, hx, hy - 70 - (0.8 - chain.msg.t) * 30, { size: 34, font: FONT.title, align: 'center', color: chain.msg.c, alpha: Math.min(1, chain.msg.t * 3) }); }
      if (stamp) { const k = Math.min(1, stamp.t / 0.12), s = 1.6 - 0.6 * k; seal(ctx, 640, 300, 120 * s, '印', PAL.red, Math.min(1, (1.0 - stamp.t) * 3)); }
      if (phase === 'seal') drawSeal(ctx, t);
      for (const f of floaters) text(ctx, f.s, f.x, f.y - f.t * 50, { size: f.big ? 42 : 32, font: FONT.title, align: 'center', color: f.c, alpha: Math.min(1, (1.3 - f.t) * 3), shadow: 'rgba(236,230,216,0.9)' });
      ctx.restore();
      drawHud(ctx, t);
    },
  };
  function subUpdate(inp, cmds) {
    if (sub.kind === 'target') {
      const list = sub.side === 1 ? alive(1) : alive(0); if (!list.includes(target)) target = list[0];
      const k = list.indexOf(target);
      if (inp.pressed('right') || inp.pressed('down')) { target = list[(k + 1) % list.length]; A.play('move'); }
      if (inp.pressed('left') || inp.pressed('up')) { target = list[(k + list.length - 1) % list.length]; A.play('move'); }
      for (const p of game.taps) for (const i of list) { const [x, y] = vis[i].pos; if (Math.abs(p.x - x) < 80 && p.y < y + 10 && p.y > y - 220) { target = i; sub.then(i); sub = null; return; } }
      if (inp.pressed('cancel')) { sub = null; A.play('cancel'); return; }
      if (inp.pressed('confirm')) { A.play('confirm'); const f = sub.then; sub = null; f(target); }
      return;
    }
    const n = sub.list.length;
    if (inp.pressed('down')) { sub.sel = (sub.sel + 1) % n; A.play('move'); } if (inp.pressed('up')) { sub.sel = (sub.sel + n - 1) % n; A.play('move'); }
    if (inp.pressed('cancel')) { sub = null; A.play('cancel'); return; }
    let pick = inp.pressed('confirm') ? sub.sel : -1; for (const p of game.taps) { const i = menuHit(sub.box, n, p); if (i >= 0) pick = sub.sel = i; }
    if (pick < 0) return; A.play('confirm');
    if (sub.kind === 'stroke') { const si = pick; sub = { kind: 'target', side: 1, then: (tg) => startChain(cur(), tg, si) }; target = alive(1)[0]; return; }
    if (sub.kind === 'item') { const it = sub.inv[pick]; const actor = cur();
      if (it.kind === 'healall') { sub = null; doItem(actor, it, actor); }
      else { const side = it.kind === 'bomb' ? 1 : 0; sub = { kind: 'target', side, then: (tg) => doItem(actor, it, tg) }; target = alive(side)[0]; } }
  }
  function drawFighter(ctx, i, t) {
    const f = F[i], v = vis[i]; if (v.gone) return;
    let [x, y] = v.pos;
    if (chain && chain.actor === i) { const [tx] = vis[chain.tgt].pos; x += (tx - 170 - x) * v.dash; }
    if (f.side === 0) {
      const iw = v.iw, hover = iw * (30 + Math.sin(t * Math.PI) * 6);
      const el = f.element, fxKey = `fx-inkwing-${el}`;
      if (phase === 'unfurl' && unfurl.actor === i) {
        const u = unfurl; if (u.t < 0.6) for (let j = 0; j < 3; j++) { const a = t * 6 + j * 2.1, rr = 30 + u.t * 140; stroke(ctx, [[x + 8, y - 110], [x + Math.cos(a) * rr * 0.6, y - 110 + Math.sin(a) * rr * 0.5], [x + Math.cos(a + 0.7) * rr, y - 110 + Math.sin(a + 0.7) * rr * 0.7]], { w: 9, color: PAL.red, alpha: 0.8, seed: j, dry: 0.7 }); }
        if (u.t >= 0.6 && art.has(fxKey)) { const fr = Math.floor((u.t - 0.6) * 12); drawStrip(art, ctx, fr < stripFrames(art, fxKey) ? fxKey : fxKey + '-loop', fr < stripFrames(art, fxKey) ? fr : fr, x, y - hover * 0.6, 0.85); }
        else if (u.t >= 0.6 && u.t < 1.4) { wash(ctx, x, y - 100, 60, 130, PAL.ink, 0.6 * Math.min(1, (u.t - 0.6) * 3)); stroke(ctx, [[x, y - 200], [x + 4, y - 100], [x, y - 10]], { w: 4, color: PAL.red, alpha: 0.8 }); }
      } else if (iw > 0.05 && art.has(fxKey + '-loop')) drawStrip(art, ctx, fxKey + '-loop', Math.floor(t * 12), x, y - hover, 0.85, false, iw);
      const useProcWings = !art.has(fxKey + '-loop');
      const showWing = useProcWings ? (phase === 'unfurl' && unfurl.actor === i ? Math.max(0, Math.min(1, (unfurl.t - 1.4) / 0.6)) : iw) : 0;
      drawPerson(ctx, f.id, x, y - hover, 0.86, 1, { action: f.alive ? v.action : 'ko', ph: v.ph, t, inkwing: showWing, detail: 1 });
      if (iw > 0.5) { ctx.save(); ctx.globalAlpha = 0.25; wash(ctx, x, y - 100 - hover, 70, 110, ELEM_TINT[el], 0.5); ctx.restore(); }
      if (phase === 'menu' && cur() === i && !sub) { const bob = Math.sin(t * 5) * 4; stroke(ctx, [[x - 12, y - 236 - hover + bob], [x, y - 220 - hover + bob], [x + 12, y - 236 - hover + bob]], { w: 6, color: PAL.red, seed: 2, dry: 0 }); }
    } else {
      drawEnemy(ctx, f.id, x, y, f.id === 'smudge_ronin' ? 1 : 1, { action: v.action === 'die' ? 'die' : f.alive ? v.action : 'die', ph: f.alive ? v.ph : Math.max(v.ph, v.action === 'die' ? v.ph : 1), t: t + i });
      if (f.alive) { const [hx, hy] = hitPt(i); bar(ctx, x - 50, (f.id === 'hollow_lantern' ? y - 210 : f.id === 'smudge_ronin' ? y - 270 : y - 110), 100, 6, f.hp / f.max_hp, PAL.ink); }
    }
    if (sub && sub.kind === 'target' && target === i) { const [hx, hy] = hitPt(i), bob = Math.sin(t * 6) * 5; stroke(ctx, [[hx - 16, hy - 92 + bob], [hx, hy - 70 + bob], [hx + 16, hy - 92 + bob]], { w: 8, color: PAL.red, seed: 5, dry: 0 }); text(ctx, name(i), hx, hy - 100 + bob, { size: 22, align: 'center', font: FONT.title, shadow: 'rgba(236,230,216,0.9)' }); }
  }
  function drawSeal(ctx, t) {
    const g = sealg, cx = 640, cy = 300, R = 150, k = (now() - g.start) / g.period;
    ctx.save(); ctx.fillStyle = 'rgba(236,230,216,0.55)'; ctx.beginPath(); ctx.arc(cx, cy, R + 40, 0, Math.PI * 2); ctx.fill(); ctx.restore();
    const ens = []; for (let j = 0; j <= 40; j++) { const a = -Math.PI / 2 + j / 40 * Math.PI * 2 * 0.97; ens.push([cx + Math.cos(a) * R, cy + Math.sin(a) * R]); }
    stroke(ctx, ens, { w: 5, seed: 8, dry: 0.7, alpha: 0.5 });
    for (const s of g.seals) { const sx = cx + Math.cos(s.ang) * R, sy = cy + Math.sin(s.ang) * R;
      if (art.has('fx-seal-mark')) drawStrip(art, ctx, 'fx-seal-mark', 4, sx, sy, 0.32, false, s.res === 'miss' ? 0.3 : 1); else seal(ctx, sx, sy, 30, '印', s.res === 'miss' ? PAL.w3 : PAL.red);
      if (s.fx != null && s.res !== 'miss') drawStrip(art, ctx, 'fx-seal-pass', Math.floor(s.fx * 12), sx, sy, 0.5); }
    if (k >= 0 && k <= 1.05) { const a = -Math.PI / 2 + k * Math.PI * 2, bx = cx + Math.cos(a) * R, by = cy + Math.sin(a) * R; const tail = []; for (let j = 0; j <= 8; j++) { const aa = a - j * 0.06; tail.push([cx + Math.cos(aa) * R, cy + Math.sin(aa) * R]); } stroke(ctx, tail.reverse(), { w: 16, seed: 4, dry: 0.8, taper: [0.6, 0.05] }); wash(ctx, bx, by, 14, 14, PAL.ink, 0.8); }
    text(ctx, T('seal.prompt'), cx, cy + 8, { size: 20, align: 'center', color: PAL.w1 });
    text(ctx, T('seal.counter', { n: g.seals.filter((s) => s.res === 'hit' || s.res === 'clean').length, total: g.n }), cx, cy + 36, { size: 22, align: 'center', font: FONT.title });
    if (g.msg && g.msg.t > 0) text(ctx, g.msg.s, cx, cy - 30, { size: 34, align: 'center', font: FONT.title, color: g.msg.c });
  }
  function drawHud(ctx, t) {
    // B4 party HUD: 3 cards 240x96 from x 272
    F.filter((f) => f.side === 0).forEach((f, j) => {
      const i = F.indexOf(f), x = 272 + j * 248, y = 588, active = cur() === i && phase === 'menu';
      panel(ctx, x, y, 240, 92, { seed: 20 + j, fill: active ? 'rgba(250,244,230,0.97)' : undefined, bw: active ? 6 : 4 });
      seal(ctx, x + 32, y + 46, 40, { gale: '風', ember: '火', stone: '石' }[f.element] || '墨', f.inkwing > 0 ? ELEM_TINT[f.element] : f.alive ? PAL.red : PAL.w3);
      text(ctx, partyDef[f.id].name, x + 62, y + 26, { size: 22, font: FONT.title, color: f.alive ? PAL.ink : PAL.w3 });
      text(ctx, `${Math.ceil(f.hp)}/${f.max_hp}`, x + 232, y + 26, { size: 16, align: 'right', color: PAL.w1 });
      bar(ctx, x + 62, y + 38, 166, 9, f.hp / f.max_hp, f.hp / f.max_hp < 0.3 ? PAL.red : PAL.w1);
      if (f.inkwing > 0) { text(ctx, `${FORM[f.id]} · ${T(f.inkwing === 1 ? 'battle.gauge.turns_left_one' : 'battle.gauge.turns_left', { n: f.inkwing })}`, x + 62, y + 78, { size: 16, color: ELEM_TINT[f.element] }); bar(ctx, x + 62, y + 56, 166, 7, f.inkwing / 3, ELEM_TINT[f.element]); }
      else { bar(ctx, x + 62, y + 56, 166, 7, f.ink / 100, PAL.red, { glow: f.ink >= 100, t }); text(ctx, f.ink >= 100 ? T('battle.gauge.ready') : `${T('battle.gauge.label')} ${Math.floor(f.ink)}`, x + 62, y + 80, { size: 15, color: f.ink >= 100 ? PAL.red : PAL.w2 }); }
    });
    // B5 command menu
    if (phase === 'menu') {
      const cmds = commands(); text(ctx, T('battle.turn.now', { name: name(cur()) }), 64, 222, { size: 20, font: FONT.title, color: '#fbf6ec', shadow: PAL.ink });
      box = menu(ctx, cmds, sub && sub.kind !== 'target' ? -1 : sel, 82, 270, { w: 200, lh: 44, size: 23 });
      if (sub && sub.kind !== 'target') sub.box = menu(ctx, sub.list, sub.sel, 320, 270, { w: 260, lh: 44, size: 22, seed: 9 });
      if (sub && sub.kind === 'item') { const it = sub.inv[sub.sel]; if (it) { panel(ctx, 310, 290 + sub.list.length * 44, 280, 50, { seed: 3 }); wrap(ctx, it.desc, 260, 16).slice(0, 2).forEach((l, k) => text(ctx, l, 320, 310 + sub.list.length * 44 + k * 18, { size: 16, color: PAL.w1 })); } }
    }
    if (banner) { const a = Math.min(1, banner.t * 3); ctx.save(); ctx.globalAlpha = a; stroke(ctx, [[340, 132], [640, 126], [940, 132]], { w: 52, color: banner.red ? PAL.red : PAL.ink, alpha: 0.85, seed: 12, dry: 0.8, taper: [0.06, 0.12] }); ctx.restore(); text(ctx, banner.s, 640, 142, { size: 26, align: 'center', font: FONT.title, color: '#fbf6ec', alpha: a }); }
    if (bark) { const i = bark.i; if (i >= 0 && vis[i]) { const [x, y] = vis[i].pos, lines = wrap(ctx, bark.s, 230, 18), bh = 16 + lines.length * 22; const by = Math.max(176, y - 300 - lines.length * 20), bx = Math.max(16, Math.min(1264 - 250, x - 120)); panel(ctx, bx, by, 250, bh, { seed: 30, bw: 3 }); lines.forEach((l, k) => text(ctx, l, bx + 12, by + 20 + k * 22, { size: 18 })); } }
    if (hint) { panel(ctx, 272, 500, 736, 56, { seed: 40 }); wrap(ctx, hint.s, 700, 19).slice(0, 2).forEach((l, k) => text(ctx, l, 640, 522 + k * 22, { size: 19, align: 'center' })); }
    if (phase === 'win' || phase === 'lose') {
      const a = Math.min(1, tPhase * 2); ctx.save(); ctx.globalAlpha = a * 0.55; ctx.fillStyle = PAL.paper; ctx.fillRect(0, 0, 1280, 720); ctx.restore();
      panel(ctx, 440, 220, 400, 200, { seed: 50, alpha: a });
      text(ctx, phase === 'win' ? T('battle.result.victory') : T('battle.result.defeat'), 640, 290, { size: 52, align: 'center', font: FONT.title, color: phase === 'win' ? PAL.red : PAL.ink, alpha: a });
      if (phase === 'win') text(ctx, T('battle.result.mon', { n: core.spoils() }), 640, 340, { size: 26, align: 'center', alpha: a });
      if (phase === 'win') { if (!rewards) { try { rewards = JSON.parse(core.rewards_json()); } catch (e) { rewards = {}; } }
        if (rewards.xp) text(ctx, `+${rewards.xp} XP`, 640, 368, { size: 20, align: 'center', color: PAL.w2, alpha: a });
        const ups = (rewards.members || []).filter((m) => m.leveled_up); if (ups.length) text(ctx, ups.map((m) => `${m.name} Lv ${m.lv}`).join('   '), 640, 430, { size: 20, align: 'center', color: PAL.red, alpha: a }); }
      if (tPhase > 1.2) text(ctx, phase === 'win' ? T('battle.result.continue') : T('battle.result.defeat_retry'), 640, 392, { size: 20, align: 'center', color: PAL.w2 });
    }
  }
  return sc;
}
