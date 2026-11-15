// Node smoke test of the built wasm against live data/. Usage: node tools/smoke.mjs <pkg dir>
import { readFileSync } from 'fs';
const pkg = process.argv[2] || '/tmp/rusty-ib-pkg';
const { initSync, Game } = await import(pkg + '/inkborne_core.js');
initSync({ module: readFileSync(pkg + '/inkborne_core_bg.wasm') });
const D = '/workspace/inkborne/data/', J = '/workspace/inkborne/team/systems/jake/';
const d = f => readFileSync(D + f, 'utf8');
const mk = (seed, party = d('party.json')) => { const g = new Game(party, d('enemies.json'), d('items.json'), seed); g.set_rules(d('transformation.json')); g.set_elements(d('elements.json')); return g; };
const st = g => JSON.parse(g.battle_json());
function fight(g) {
  let n = 0;
  while (g.current() >= 0 && n++ < 400) {
    const c = g.current(), s = st(g);
    if (s.fighters[c].side === 1) { g.step(); continue; }
    const t = s.fighters.findIndex(f => f.side === 1 && f.alive);
    let r = JSON.parse(g.begin_stroke(c, t, 0, 0));
    while (r.next) r = JSON.parse(g.press(r.next.target_ms + 20));
  }
  return st(g).over;
}
// 1. normal win with timed chains, rewards present
let g = mk(7); g.start_battle('sumikage_c');
console.log('win:', fight(g), 'rewards:', g.rewards_json().slice(0, 120));
// 2. ambush: enemies act first in round 1
g = mk(7); const s0 = JSON.parse(g.start_battle_opts('sumikage_c', JSON.stringify({ first: 'enemy', canFlee: true })));
console.log('ambush first actor side:', s0.fighters[s0.turn].side, 'first:', s0.first, 'outcome:', fight(g));
// 3. boss: canFlee false refuses
g = mk(7); g.start_battle_opts('sumikage_boss', JSON.stringify({ canFlee: false }));
while (st(g).fighters[g.current()].side === 1) g.step();
console.log('boss flee:', g.flee(g.current()), 'can_flee:', g.can_flee());
// 4. flee until it works (deterministic per seed)
g = mk(11); g.start_battle('sumikage_c'); let tries = 0, res;
while (g.current() >= 0 && tries < 20) { const c = g.current(); if (st(g).fighters[c].side === 1) { g.step(); continue; } tries++; res = JSON.parse(g.flee(c)); }
console.log('flee: attempts', tries, 'last', JSON.stringify(res), 'over:', st(g).over);
// 5. XP with Jake's party.json + xp on enemies (Jake's suggested values)
const e = JSON.parse(d('enemies.json')); const XP = { blotling: 12, hollow_lantern: 18, smudge_ronin: 150 }; e.enemies.forEach(x => x.xp = XP[x.id]);
g = new Game(readFileSync(J + 'party.json', 'utf8'), JSON.stringify(e), d('items.json'), 3); g.set_rules(readFileSync(J + 'transformation.json', 'utf8'));
g.start_battle('sumikage_boss'); console.log('boss with Jake data:', fight(g), 'xp:', JSON.parse(g.rewards_json() || 'null')?.xp, 'party lv/xp:', JSON.parse(g.party_json()).map(m => `${m.id}:${m.lv}/${m.xp}`).join(' '));
