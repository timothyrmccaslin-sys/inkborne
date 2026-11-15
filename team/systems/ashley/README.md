# Systems / Ashley: POI ambient motion + encounter zones

Drop for Tim (Systems). Nothing here is loaded at runtime (SPEC 9). Marc copies it in.
Aligned to SPEC v1.1 and the live `data/` (world nodes `woods_edge`, `sumikage`, `hanshi`; POIs `forest` = Sumikage Wood and `town` = Hanshi, both 1280×720; enemies `blotling`, `hollow_lantern`, `smudge_ronin`).

| File | What |
|---|---|
| `ambient.js` | Ambient motion for the `poi` scene: grass sway, drifting mist, falling leaves, swaying paper lanterns. Sumi-e palette (SPEC 5), Canvas 2D, no dependencies. |
| `zones.json` | Random-encounter zones for world paths and POI regions, plus encounter groups in the `enemies.json` `encounters` shape (SPEC 7). |
| `encounters.js` | Step-based encounter roller plus `startBattle(game, hit)`. Pure ES module, runs in Node too. |
| `test/encounters.test.mjs` | `node test/encounters.test.mjs`: schema, refs against the live data, canon-only enemies, IP terms, rate sim, determinism, save/restore. |
| `demo.html` | Standalone harness. Serve the repo root over HTTP and open `team/systems/ashley/demo.html` (`?selftest=1` runs a scripted perf check). |

## ambient.js
```js
import { createAmbient } from './ambient.js';
const amb = createAmbient({ quality: 'full', sfx: (k) => game.audio.play(k) }); // sfx keys: 'wind', 'lantern'
amb.load(poiJson);                   // in poi enter(); uses poi.props of type grass|mist|leaves|lantern, else forest/town presets
amb.update(dt, cam, { player });     // in update(dt, input); cam = view top-left in POI pixels; player {x,y} bends grass
amb.drawBack(ctx, cam);              // in draw(), before NPCs and the walker
amb.drawFront(ctx, cam);             // after them
amb.gust(1); amb.setQuality('lite'); amb.info;
```
- Quality: `full`, `lite` (about half the work), `reduced` (static wash; default when the OS asks for reduced motion). `auto` drops full to lite after 3 s of slow frames.
- Optional prop shapes for `pois/<id>.json` `props`: `{ type: 'grass', x, y, w, h, layer?, density? }`, `{ type: 'mist', y, h, alpha, speed, parallax, layer }`, `{ type: 'leaves', rect, rate }`, `{ type: 'lantern', x, y, len }`. Today both live POIs have `props: []`, so the presets are used.
- iPad budget: grass is capped at `maxBlades` (default 1400) per POI by thinning every grass prop evenly; lite also draws every other blade.

## Encounters
```js
import { createEncounters, startBattle } from './encounters.js';
const enc = createEncounters(game.data.zones, { seed });
const hit = enc.move({ scene: 'poi', poi: poiJson, x: px, y: py, dist });       // POI walker, each update
const hit = enc.move({ scene: 'world', path: ['woods_edge', 'sumikage'], dist }); // world token on a path
if (hit) startBattle(game, hit);   // game.push('battle', { enc, bg: 'battle-forest', boss, canFlee?, first? })
enc.afterBattle();                 // in onResult, after random AND fixed fights; grants grace steps
enc.state() / enc.restore(s);      // tiny, save-friendly
```
- **Battle start (Tim's decision):** the live `src/scenes/battle.js` params are the contract: `{ enc, bg, boss }`. `enc` is the encounter id only; the core resolves the group from `enemies.json` via `core.start_battle(enc)`. `canFlee` and `first` (`'enemy'` = ambush) ride along as optional extras battle.js may ignore. Music is left to the scene. The `hit` object still carries `enemies` for logging/debug, but it is not passed to battle.js.
- **Where the data lives (Tim's decision):** zones stay in their own file. Recommended live path: **`data/zones.json`** (load it into `game.data.zones` at boot). Do not fold it into `enemies.json`. Only the `encounters` block here is meant to be merged into `enemies.json` `encounters`.
- Rate model: a step is `rules.stepPx` of real travel (**10 px in POIs**, 20 on the world map). No roll before `minSteps`, then `1/(avgSteps-minSteps)` per step, `maxSteps` forces one. Standing still never rolls. Grace: 4 steps on entering a zone, 6 after a battle. `avgSteps`/`minSteps`/`maxSteps` are unchanged from v2.
- Zones in Sumikage Wood (`forest`, 1280 px wide): **trail entrance to the seal-stone, x 0–20% (safe, new)**; outer trail 20–40%; deep trees 40–72%; the clearing before the Smudge Ronin 72–100% (safe). All of Hanshi is safe. World roads: Hakushi Clearing to Sumikage Wood, Sumikage Wood to Hanshi. The locked roads (Shuin Stair, Usuzumi Shore) have no zones yet.
- **Canon enemies only** (Marc via Tim): Blotling, Hollow Lantern, Smudge Ronin. Random groups use Blotling and Hollow Lantern (1–3 enemies). The Smudge Ronin only appears in the fixed `sumikage_boss` fight, and the test fails if he ever lands in a random table.
- `sumikage_c` (the scripted ambush group) also stays a **25% repeat** in the deep-trees table (Tim's decision). `sumikage_c` and `sumikage_boss` are byte-identical to the live `enemies.json`, so `encounters` merges straight in. New groups are `road_*` and `wood_*`.

## Sim results (seeded; `node test/encounters.test.mjs`)
Per zone, 4000 encounters each:

| Zone | Target avg (steps) | Measured mean | Range |
|---|---|---|---|
| world-woods_edge-sumikage | 40 | 37.7 | 14–90 |
| world-sumikage-hanshi | 34 | 32.2 | 12–80 |
| sumikage-edge | 36 | 34.0 | 14–80 |
| sumikage-deep | 28 | 26.3 | 10–64 |

The means come in about 6% under target because the `maxSteps` cap cuts off the long tail. The test allows 12%.

**Full forest crossing** (straight walk at 220 px/s from the live spawn x 90 to the Ronin clearing at x 922, fighting the scripted `ambush` trigger on the way, 20,000 seeds): **1.06 random fights on average**, plus the 2 fixed fights (`sumikage_c` ambush, `sumikage_boss`). 21% of crossings have no random fight. The test asserts 0.8–1.25.

Why stepPx changed: with the old 24 px POI step, a straight crossing measured **0.00** random fights (about 35 rollable steps, eaten by the enter grace, `minSteps`, and the reset after the scripted ambush). So the safe entrance alone could not reach ~1. Shortening the POI step to 10 px, with the 0–20% safe entrance and `avgSteps` unchanged, lands at 1.06.

## Render check
`demo.html` was loaded in headless Chrome (from the box's `/opt/google/chrome`, driven over the DevTools protocol, no installs). Screenshot: `test/demo-shot.png`. The only console error was a 404 for `/favicon.ico` from the test server. `?selftest=1` passes in forest, town and world. The per-frame p50 is under 0.5 ms for ambient in every scene and quality, and grass is 1402 blades in the forest. Headless software rendering adds rare multi-second stalls, so the averages are not meaningful. Do a real iPad pass before calling it final.

## Open questions
1. Sumikage Wood POI props are still `[]`, so ambient uses the procedural presets. If the art or level team places `grass`/`mist`/`leaves`/`lantern` props in `pois/*.json`, ambient will use those instead.
2. Locked roads (Shuin Stair, Usuzumi Shore) have no zones yet. Add them when those nodes unlock.
