// Inkborne encounter zones + random-encounter helper. Systems / Ashley, v1.0.0.
// Pure ES module, no DOM, no dependencies (runs in the browser and in Node for tests).
//
//   import { createEncounters, startBattle } from './encounters.js';
//   const enc = createEncounters(zonesJson, { seed });
//   // POI scene, each update while the walker moves:
//   const hit = enc.move({ scene: 'poi', poi: poiJson, x, y, dist });
//   // world scene, while the party token travels along a path:
//   const hit = enc.move({ scene: 'world', path: ['woods_edge', 'sumikage'], dist });
//   if (hit) startBattle(game, hit);
//   // battle over (POI onResult / world resume):
//   enc.afterBattle();
//
// The rate model: a "step" is rules.stepPx of real travel (standing still never rolls).
// No roll before rate.minSteps; then each step hits with p = 1/(avgSteps - minSteps), and
// rate.maxSteps forces a hit, so the mean is about avgSteps and droughts are bounded.

export const ENCOUNTERS_VERSION = '1.0.0';

export function mulberry(seed) {
  let a = seed >>> 0;
  const f = () => { a |= 0; a = (a + 0x6D2B79F5) | 0; let t = Math.imul(a ^ (a >>> 15), 1 | a); t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t; return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };
  f.state = () => a >>> 0; f.set = (s) => { a = s >>> 0; };
  return f;
}

const samePath = (p, q) => p && q && ((p[0] === q[0] && p[1] === q[1]) || (p[0] === q[1] && p[1] === q[0]));

// Zone rectangle in POI pixels. rectN is normalised to the POI's w/h; rect is absolute pixels.
export function zoneRect(z, poi) {
  if (z.rect) return z.rect;
  if (z.rectN && poi) return [z.rectN[0] * poi.w, z.rectN[1] * poi.h, z.rectN[2] * poi.w, z.rectN[3] * poi.h];
  return null;
}

export function pickWeighted(table, r) {
  let total = 0; for (const e of table) total += e.weight;
  let x = r() * total;
  for (const e of table) { x -= e.weight; if (x < 0) return e; }
  return table[table.length - 1];
}

export function createEncounters(data, opts = {}) {
  const rules = data.rules || {};
  const stepPx = Object.assign({ poi: 32, world: 20 }, rules.stepPx);
  const r = opts.rng || mulberry(opts.seed ?? ((Math.random() * 2 ** 32) >>> 0));
  let steps = 0, carry = 0, grace = 0, zoneId = null, enabled = true;

  function zoneAt(q) {
    let best = null;
    for (const z of data.zones) {
      if (z.scene !== q.scene) continue;
      if (q.scene === 'world') { if (!samePath(z.path, q.path)) continue; }
      else {
        const pid = q.poi && (q.poi.id || q.poi);
        if (z.poi && z.poi !== pid) continue;
        const R = zoneRect(z, q.poi); if (!R) continue;
        if (q.x < R[0] || q.y < R[1] || q.x >= R[0] + R[2] || q.y >= R[1] + R[3]) continue;
      }
      if (!best || (z.priority || 0) > (best.priority || 0)) best = z;
    }
    return best;
  }

  function roll(z) {
    const { avgSteps, minSteps = 0, maxSteps = Infinity } = z.rate;
    if (steps < minSteps) return false;
    if (steps >= maxSteps) return true;
    return r() < 1 / Math.max(1, avgSteps - minSteps);
  }

  function build(z, encId, extra) {
    const fixed = (data.fixed || {})[encId] || {};
    const first = z && z.ambush && r() < z.ambush ? 'enemy' : null;
    return Object.assign({
      zone: z ? z.id : null, encounter: encId, enemies: (data.encounters[encId] || []).slice(),
      bg: fixed.bg || (z && z.bg) || 'forest', canFlee: fixed.canFlee ?? true, first,
    }, extra);
  }

  // q = { scene: 'poi'|'world', poi?: poiJson|id, x?, y?, path?: [a, b], dist: px travelled this frame }
  function move(q) {
    if (!enabled) return null;
    const z = zoneAt(q);
    const id = z ? z.id : null;
    if (id !== zoneId) { zoneId = id; if (z && !z.safe) grace = Math.max(grace, rules.graceStepsOnEnter ?? 0); }
    if (!z || z.safe || !z.rate || !z.table || !z.table.length) { carry = 0; return null; }
    carry += Math.max(0, q.dist || 0);
    const sp = z.stepPx || stepPx[q.scene] || 32;
    while (carry >= sp) {
      carry -= sp;
      if (grace > 0) { grace--; continue; }
      steps++;
      if (roll(z)) { steps = 0; carry = 0; return build(z, pickWeighted(z.table, r).encounter); }
    }
    return null;
  }

  return {
    move, zoneAt,
    fixed(encId) { return build(null, encId, { zone: null }); }, // for POI triggers { kind: 'battle', ref }
    afterBattle() { steps = 0; carry = 0; grace = rules.graceStepsAfterBattle ?? 0; },
    reset() { steps = 0; carry = 0; grace = 0; zoneId = null; },
    setEnabled(v) { enabled = !!v; }, // e.g. off during cutscenes or for a debug "no encounters" toggle
    get zone() { return zoneId; },
    get steps() { return steps; },
    state() { return { steps, grace, carry: Math.round(carry), zone: zoneId, rng: r.state ? r.state() : null }; }, // small, save-friendly
    restore(s) { if (!s) return; steps = s.steps | 0; grace = s.grace | 0; carry = s.carry || 0; zoneId = s.zone ?? null; if (s.rng != null && r.set) r.set(s.rng); },
  };
}

// Hands an encounter to the battle screen per SPEC 3: push the action screen over the current view.
// Params are the live src/scenes/battle.js contract: `enc` (an enemies.json encounters id; the core
// resolves the group itself via core.start_battle), `bg` (art key 'battle-<poi>') and `boss` (hides Flee).
// `first` ('enemy' = ambush) and `canFlee` are optional extras battle.js may ignore. Music is left to the scene.
export function startBattle(game, hit, extra = {}) {
  const a = game.audio;
  try { if (a && a.play) a.play('ring'); } catch (e) { /* audio optional */ }
  const bg = hit.bg ? (hit.bg.startsWith('battle-') ? hit.bg : 'battle-' + hit.bg) : 'battle-forest';
  const params = { enc: hit.encounter, bg, boss: hit.canFlee === false };
  if (hit.first) params.first = hit.first;
  if (hit.canFlee !== undefined) params.canFlee = hit.canFlee;
  return game.push('battle', Object.assign(params, extra));
}
