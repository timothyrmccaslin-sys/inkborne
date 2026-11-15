// Inkborne save helper (Jared, Dev). Plugs in at src/save.js; see team/dev/jared/README.md.
// localStorage key is exactly 'inkborne-save-v1' (SPEC section 1). The JSON comes from the core's save_json()
// and is validated by the core's load_json(); this file only moves strings in and out of storage.
// Every storage call is wrapped: private mode, a disabled store, or a full quota must never break the game,
// and a failed write leaves the previous save as it was (setItem either replaces the value or throws).

export const SAVE_KEY = 'inkborne-save-v1';
export const MAX_SAVE_BYTES = 256 * 1024; // same cap as the core (save.rs MAX_SAVE_BYTES)

function store() {
  try { return typeof localStorage !== 'undefined' ? localStorage : null; } catch (e) { return null; } // access itself can throw (blocked storage)
}

/** Raw save string, or null when there is none / storage is unavailable / it is oversized. */
export function readSave() {
  const ls = store(); if (!ls) return null;
  try {
    const s = ls.getItem(SAVE_KEY);
    if (typeof s !== 'string' || !s) return null;
    if (s.length > MAX_SAVE_BYTES) { console.warn(`[save] ${SAVE_KEY} is ${s.length} bytes (> ${MAX_SAVE_BYTES}); ignored`); return null; }
    return s;
  } catch (e) { console.warn('[save] could not read localStorage:', e && e.message); return null; }
}

/** True when a save exists that at least parses as a JSON object (the core does the real validation). */
export function hasSave() {
  const s = readSave(); if (!s) return false;
  try { const v = JSON.parse(s); return !!v && typeof v === 'object' && !Array.isArray(v); } catch (e) { return false; }
}

/** Write core.save_json() under SAVE_KEY. Returns true on success; on failure the old save is kept. */
export function writeSave(core) {
  let s;
  try { s = core.save_json(); } catch (e) { console.warn('[save] save_json failed; nothing written:', e && e.message); return false; }
  const ls = store(); if (!ls) { console.warn('[save] localStorage unavailable (private mode?); progress not saved'); return false; }
  try { ls.setItem(SAVE_KEY, s); return true; } catch (e) {
    console.warn('[save] write failed (quota or private mode); previous save left as is:', e && (e.name || e.message));
    return false;
  }
}

/** Warnings from the core's last load_json, as an array of { code, path, detail }. */
export function loadWarnings(core) {
  try { return typeof core.load_warnings === 'function' ? JSON.parse(core.load_warnings()) : []; } catch (e) { return []; }
}

/**
 * Make sure the core's current world node exists in world.json (`{ start, nodes: [{ id }] }`, SPEC section 7).
 * An unknown or missing node falls back to `world.start` via the core's set_node() and logs a warning.
 * Returns the node in effect afterwards (or null when there is no world data to check against).
 */
export function fixNode(core, world) {
  if (!world || !Array.isArray(world.nodes) || typeof world.start !== 'string') return null;
  let node = '';
  try { node = core.node(); } catch (e) { node = ''; }
  if (typeof node === 'string' && node && world.nodes.some((n) => n && n.id === node)) return node;
  console.warn(`[save] ${node ? `unknown node '${node}'` : 'no node in save'}; using start node '${world.start}'`);
  try { core.set_node(world.start); } catch (e) { console.warn('[save] set_node failed:', e && e.message); }
  return world.start;
}

/**
 * Load the stored save into the core. Returns true if the core accepted it.
 * Repaired problems (unknown ids, clamped numbers, ...) are logged with console.warn; the save is still loaded.
 * If the core rejects it (malformed JSON, newer version), the core state is unchanged and the stored string
 * is NOT overwritten here, so nothing is lost until the player saves again.
 * Pass the loaded world.json object (game.data.world) as `world` to repair an unknown saved node (see fixNode).
 */
export function loadSave(core, world) {
  const s = readSave(); if (!s) return false;
  let ok = false;
  try { ok = !!core.load_json(s); } catch (e) { console.warn('[save] load_json threw:', e && e.message); ok = false; }
  for (const w of loadWarnings(core)) console.warn(`[save] ${w.code}${w.path ? ' at ' + w.path : ''}${w.detail ? ': ' + w.detail : ''}`);
  if (!ok) { console.warn(`[save] ${SAVE_KEY} could not be loaded; starting from current state`); return false; }
  fixNode(core, world);
  return true;
}

/** Remove the save (e.g. a "delete save" option). Returns true on success. */
export function clearSave() {
  const ls = store(); if (!ls) return false;
  try { ls.removeItem(SAVE_KEY); return true; } catch (e) { console.warn('[save] could not clear:', e && e.message); return false; }
}
