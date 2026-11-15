// node test/encounters.test.mjs  (no dependencies)
import { readFileSync } from 'node:fs';
import assert from 'node:assert/strict';
import { createEncounters, zoneRect } from '../encounters.js';

const data = JSON.parse(readFileSync(new URL('../zones.json', import.meta.url)));
// Validate against the live game data when it is there (SPEC 7), else the ids it shipped with.
const live = (f) => { try { return JSON.parse(readFileSync(new URL('../../../../data/' + f, import.meta.url))); } catch { return null; } };
const ENEMIES = (live('enemies.json')?.enemies || [{ id: 'blotling' }, { id: 'hollow_lantern' }, { id: 'smudge_ronin' }]).map((e) => e.id);
const WORLD = live('world.json');
const BANNED = /drag[o]on|addition|wingly|spirit/i;
const CANON = ['blotling', 'hollow_lantern', 'smudge_ronin']; // canon rule (Marc via Tim): only these enemies
const BOSS = 'smudge_ronin';
let pass = 0; const ok = (m) => { pass++; console.log('ok -', m); };

// schema
const ids = new Set();
for (const z of data.zones) {
  assert(!ids.has(z.id), 'dup zone ' + z.id); ids.add(z.id);
  assert(['poi', 'world'].includes(z.scene), z.id + ' scene');
  if (z.scene === 'world') {
    assert(Array.isArray(z.path) && z.path.length === 2, z.id + ' path');
    if (WORLD) assert(WORLD.paths.some((p) => (p[0] === z.path[0] && p[1] === z.path[1]) || (p[0] === z.path[1] && p[1] === z.path[0])), z.id + ' path not in world.json');
  } else if (WORLD) assert(WORLD.nodes.some((n) => n.poi === z.poi), z.id + ' poi not in world.json');
  else assert(z.rectN || z.rect, z.id + ' rect');
  if (z.rectN) z.rectN.forEach((v) => assert(v >= 0 && v <= 1, z.id + ' rectN range'));
  if (!z.safe) {
    assert(z.rate && z.rate.avgSteps > z.rate.minSteps && z.rate.maxSteps > z.rate.avgSteps, z.id + ' rate');
    assert(z.table.length && z.table.every((e) => e.weight > 0 && data.encounters[e.encounter]), z.id + ' table refs');
  }
}
for (const [k, list] of Object.entries(data.encounters)) {
  assert(list.length >= 1 && list.length <= 3, k + ' group size 1-3'); list.forEach((e) => { assert(ENEMIES.includes(e), k + ' unknown enemy ' + e); assert(CANON.includes(e), k + ' non-canon enemy ' + e); });
}
for (const z of data.zones) for (const t of z.table || []) assert(!data.encounters[t.encounter].includes(BOSS), z.id + ' random table contains the mini-boss');
for (const k of Object.keys(data.fixed)) assert(data.encounters[k], 'fixed ' + k);
const liveEnc = live('enemies.json')?.encounters || {};
for (const [k, v] of Object.entries(liveEnc)) if (data.encounters[k]) assert.deepEqual(data.encounters[k], v, 'merge would change existing encounter ' + k);
assert(!BANNED.test(JSON.stringify(data)), 'banned term in zones.json');
for (const f of ['../ambient.js', '../encounters.js', '../demo.html', '../README.md']) assert(!/drag[o]on/i.test(readFileSync(new URL(f, import.meta.url), 'utf8')), 'banned word in ' + f);
ok(`zones.json schema, refs, enemy ids (${WORLD ? 'checked against live data/' : 'built-in list'}), IP terms`);

// rates: simulate long walks per zone and check the mean / bounds
const livePoi = (id) => { const p = live('pois/' + id + '.json'); return p ? { id: p.id, w: p.w, h: p.h } : { id, w: 1280, h: 720 }; };
const forest = livePoi('forest');
function sim(q, n = 4000, seed = 7) {
  const e = createEncounters(data, { seed }); const gaps = []; let s = 0;
  e.move({ ...q, dist: 0 });
  while (gaps.length < n) { s++; const hit = e.move({ ...q, dist: data.rules.stepPx[q.scene] }); if (hit) { gaps.push(s); s = 0; } }
  return { mean: gaps.reduce((a, b) => a + b, 0) / n, min: Math.min(...gaps), max: Math.max(...gaps) };
}
for (const z of data.zones.filter((z) => !z.safe)) {
  const q = z.scene === 'world' ? { scene: 'world', path: [...z.path].reverse() } : (() => { const R = zoneRect(z, forest); return { scene: 'poi', poi: forest, x: R[0] + R[2] / 2, y: R[1] + R[3] / 2 }; })();
  const st = sim(q), grace = data.rules.graceStepsOnEnter;
  // the first gap includes the enter grace; the rest are pure. Mean should be within ~12% of avgSteps.
  assert(Math.abs(st.mean - z.rate.avgSteps) / z.rate.avgSteps < 0.12, `${z.id} mean ${st.mean}`);
  assert(st.min >= z.rate.minSteps && st.max <= z.rate.maxSteps + grace, `${z.id} bounds ${st.min}-${st.max}`);
  ok(`${z.id}: mean ${st.mean.toFixed(1)} steps (target ${z.rate.avgSteps}), range ${st.min}-${st.max}`);
}

// safe zones never fire; standing still never fires; priority wins on overlap
{
  const e = createEncounters(data, { seed: 1 }), town = livePoi('town');
  for (let i = 0; i < 20000; i++) assert.equal(e.move({ scene: 'poi', poi: town, x: 500, y: 400, dist: 32 }), null);
  const clear = zoneRect(data.zones.find((z) => z.id === 'sumikage-ronin-clearing'), forest);
  for (let i = 0; i < 20000; i++) assert.equal(e.move({ scene: 'poi', poi: forest, x: clear[0] + 10, y: 500, dist: 32 }), null);
  for (let i = 0; i < 20000; i++) assert.equal(e.move({ scene: 'poi', poi: forest, x: 100, y: 500, dist: 0 }), null);
  assert.equal(e.zoneAt({ scene: 'poi', poi: forest, x: clear[0] + 1, y: 10 }).id, 'sumikage-ronin-clearing');
  assert.equal(e.zoneAt({ scene: 'world', path: ['woods_edge', 'nowhere'] }), null);
  ok('safe zones, standing still and off-zone paths never roll; priority resolves overlap');
}

// determinism + save/restore + grace after battle + fixed encounter
const DEEP_X = (() => { const R = zoneRect(data.zones.find((z) => z.id === 'sumikage-deep'), forest); return R[0] + R[2] / 2; })();
{
  const run = (e) => { const out = []; for (let i = 0; i < 3000; i++) { const h = e.move({ scene: 'poi', poi: forest, x: DEEP_X, y: 500, dist: 13 }); if (h) out.push(i + h.encounter); } return out.join(); };
  assert.equal(run(createEncounters(data, { seed: 42 })), run(createEncounters(data, { seed: 42 })));
  const a = createEncounters(data, { seed: 9 }); run(a); const snap = a.state();
  const b = createEncounters(data, { seed: 1 }); b.restore(snap);
  assert.equal(run(a), run(b));
  const c = createEncounters(data, { seed: 3 }); c.afterBattle(); let n = 0;
  while (!c.move({ scene: 'poi', poi: forest, x: DEEP_X, y: 500, dist: data.rules.stepPx.poi })) n++;
  assert(n >= data.rules.graceStepsAfterBattle + data.zones.find((z) => z.id === 'sumikage-deep').rate.minSteps - 1, 'grace after battle');
  const f = c.fixed('sumikage_boss'); assert.deepEqual(f.enemies, ['smudge_ronin']); assert.equal(f.canFlee, false);
  ok('seeded determinism, state()/restore(), post-battle grace, fixed mini-boss');
}

// Full forest crossing: walk straight from the live spawn to the safe Smudge Ronin clearing at walking
// speed (220 px/s, 60 fps), fighting the scripted 'ambush' trigger on the way (afterBattle after every
// fight). Tim's target: about 1 random fight per crossing on top of the 2 fixed ones.
{
  const fp = live('pois/forest.json') || { id: 'forest', w: 1280, h: 720, spawn: [90, 640], triggers: [{ id: 'ambush', rect: [560, 548, 120, 172] }] };
  const poi = { id: 'forest', w: fp.w, h: fp.h }, ambX = fp.triggers.find((t) => t.id === 'ambush').rect[0];
  const endX = zoneRect(data.zones.find((z) => z.id === 'sumikage-ronin-clearing'), poi)[0], y = fp.spawn[1];
  const N = 20000; let fights = 0, none = 0;
  for (let s = 0; s < N; s++) {
    const e = createEncounters(data, { seed: s + 1 }); let x = fp.spawn[0], fixed = false, mine = 0;
    while (x < endX) { const nx = x + 220 / 60; if (!fixed && nx >= ambX) { fixed = true; e.afterBattle(); } if (e.move({ scene: 'poi', poi, x: nx, y, dist: nx - x })) { mine++; e.afterBattle(); } x = nx; }
    fights += mine; if (!mine) none++;
  }
  const avg = fights / N; globalThis.CROSSING_AVG = avg;
  assert(avg > 0.8 && avg < 1.25, 'crossing average ' + avg);
  assert.equal(zoneRect(data.zones.find((z) => z.id === 'sumikage-trailhead'), poi)[0], 0);
  const deep = data.zones.find((z) => z.id === 'sumikage-deep'), tot = deep.table.reduce((a, b) => a + b.weight, 0);
  assert.equal(deep.table.find((t) => t.encounter === 'sumikage_c').weight / tot, 0.25, 'sumikage_c is a 25% repeat in the deep trees');
  ok(`forest crossing (spawn x ${fp.spawn[0]} to clearing x ${Math.round(endX)}, ${N} seeds): ${avg.toFixed(2)} random fights on average + 2 fixed; ${(100 * none / N).toFixed(0)}% of crossings have none`);
}

// startBattle shape
{
  const { startBattle } = await import('../encounters.js');
  let got; startBattle({ push: (n, p) => (got = [n, p]) }, createEncounters(data, { seed: 1 }).fixed('wood_lantern_pair'));
  assert.equal(got[0], 'battle');
  assert.deepEqual(got[1], { enc: 'wood_lantern_pair', bg: 'battle-forest', boss: false, canFlee: true }, 'params are the battle.js contract { enc, bg, boss } + optional extras only');
  { let g2; startBattle({ push: (n, p) => (g2 = p) }, createEncounters(data, { seed: 1 }).fixed('sumikage_boss')); assert.equal(g2.boss, true); assert.equal(g2.enc, 'sumikage_boss'); assert.equal(g2.canFlee, false); }
  { let g3; startBattle({ push: (n, p) => (g3 = p) }, { encounter: 'wood_blotling', bg: 'forest', canFlee: true, first: 'enemy' }); assert.equal(g3.first, 'enemy'); assert(!('music' in g3) && !('enemies' in g3)); }
  ok('startBattle pushes the battle action screen with encounter params');
}
console.log(`\n${pass} checks passed`);
