# Inkborne: integration contract (SPEC v1.1)

Changed in v1.1: the title is back to Inkborne, the gauge is Vermilion Ink (the old name was too close to the source game), the cast and places follow `/workspace/inkborne-creative/story/CANON.md`, James's extra SFX keys are added, and `transformation.json` is added.

Integrator: Marc. Every team delivers into `team/<team>/` (see section 9). Marc reviews each drop
and copies it into the live folders, so nothing in `team/` is loaded by the game directly.
If something is missing, the game uses a procedural placeholder tagged `TODO(team)` in the code.

**IP rule (strict).** This is an original game inspired by the *mechanics* of a classic 1999 JRPG.
Do not use that game's names (characters, places, items, spells, or the word for its transformed
warriors), story beats, dialogue, character designs, logos, music or sprites. Our mechanic names are in section 2.
**Audio rule.** Audio must be synthesized by us, either at runtime or rendered offline from our own code. No outside samples.
**Secrets.** The repo is public on GitHub Pages, so never commit keys, tokens, passwords or e-mail addresses.

## 1. Tech
- The core is Rust (`core/`, crate `inkborne_core`) compiled with `wasm-pack --target web` into `pkg/`, which is committed.
  The core owns the battle rules, damage, Vermilion Ink, timing judgement, the walker collision, the inventory, gold and the save state.
- The renderer is plain ES modules on a single `<canvas>` (`src/`). There is no bundler and no npm runtime.
- The game is a PWA: `manifest.json` plus `sw.js` precache the shell and it works offline. `APP_VERSION` in `src/main.js` and
  `VERSION` in `sw.js` are bumped together on every release (`ib-X.Y.Z`).
- Saves go in localStorage under the key `inkborne-save-v1` and come from the core's `save_json()`.
- The logical resolution is **1280×720**, landscape first. It is scaled to fit with letterboxing, is DPR aware and respects
  `env(safe-area-inset-*)`. It uses the Fullscreen API where available and the standalone display mode on the iPad PWA.

## 2. Mechanic glossary (our names)
| Mechanic | Inkborne name |
|---|---|
| timed multi-hit combo (press as the ring closes) | **Brushstroke Chain** (each press is a Stroke; named chains are Forms of the Brush, e.g. Falling Pine; a fully Clean chain ends with a red Seal stamp) |
| perfect press (tight window, bonus) | **Clean Line** (×1.25 hit damage, +more Ink) |
| gauge filled by successful hits and damage taken | **Vermilion Ink** (0–100 per character; data key `ink`) |
| transform into winged elemental form | **Unfurl** (battle command) into the **Inkwing** form (costs a full gauge, lasts 3 of that character's turns, ATK/DEF up). Forms: Itsuki = Gale Crane, Benika = Ember Kite, Gonzō = Stone Owl |
| timed magic while transformed | **Seal Arts** (press as the brush passes each red seal) |
| guard (halves damage, heals 10% HP) | **Still Water** |
| elements, opposite pairs ×2 / same ×0.5 | **Six Inks**: Ember↔Tide, Gale↔Stone, Dawn↔Dusk |
| currency | **mon** |

## 3. Scenes
There are three views plus overlays:
- `world`: the world map. It uses bold abstract strokes, and the party token travels along the paths between nodes.
- `poi`: a point of interest. It is a detailed walkable area (`forest`, `town`) with ambient motion and triggers.
- `action`: the most detailed view. It has three modes: `battle`, `dialogue` and `shop`.
- `title`: the title screen.

Each scene module is `src/scenes/<name>.js` and exports `create(game, params) -> scene`, where the scene has these members:
```
scene = { name, enter(), exit(), update(dt /*s*/, input), draw(ctx, t /*s*/) , onResult?(result) }
```
The game API is:
- `game.go(name, params)` replaces the current scene with an ink-wipe transition.
- `game.push(name, params)` opens an action screen over a POI.
- `game.pop(result)` returns to the POI, which receives `onResult(result)`.
- `game.core` is the wasm `Game`.
- `game.data` holds the loaded JSON.
- `game.art` is the image registry.
- `game.audio` handles the audio.

## 4. Input map (`src/input.js`)
Every source maps to the same abstract actions: `up down left right` (held, plus an analog `ax, ay` vector),
`confirm`, `cancel` and `menu` (edge-triggered, `input.pressed(a)`; held, `input.down(a)`).

| Action | Keyboard | Gamepad (standard mapping) | Touch |
|---|---|---|---|
| move | WASD / arrows | left stick (dead zone 0.25) or D-pad 12–15 | virtual stick, lower left |
| confirm / timed press | Space, Enter, J | A (0) | **A** button, lower right |
| cancel / Still Water shortcut | Esc, Backspace, K | B (1) | **B** button |
| menu | Tab, M | Start (9) | ☰ button, top right |

The touch controls hide after any gamepad input and come back on the next touch. Timed presses use `input.pressedAt(a)`,
which gives a `performance.now()` timestamp so the judgement is not quantized to frames.

## 5. Art
- **Style.** Sumi-e ink wash, the same as Asura: paper texture, wet ink edges and dry-brush, with red (vermilion) only for accents and seals.
- **Palette.**
  - Paper `#ece6d8`, paper shade `#d9d0bc`, ink `#1b1813`, wash 1 `#3b3730`, wash 2 `#6d675b`, wash 3 `#a39c8c`.
  - Vermilion `#b3261e` and gold leaf `#b08a3e`.
  - Element tints: Ember `#c2452d`, Tide `#2f5d7c`, Gale `#5f8a6a`, Stone `#7a6a52`, Dawn `#d9b45a`, Dusk `#4b3b63`.
- **Detail tiers.**
  - World: large, bold, abstract strokes, with almost no line detail.
  - POI: mid detail.
  - Action: full detail, with the richest animation.
- **Formats.** Use WebP (preferred) or PNG with alpha and sRGB. Put the art in `assets/art/<group>/` and register it in `assets/art/manifest.json`:
```
{ "images": { "<key>": { "src": "bg/forest-far.webp", "w": 2560, "h": 1440, "frames": 1, "fw": 2560, "fh": 1440, "fps": 0, "anchor": [0.5, 1] } } }
```
- **Sizes and keys.**

| What | Key pattern | Size |
|---|---|---|
| world map backdrop | `world-bg` | 2560×1440 |
| POI layers | `poi-<id>-far`, `-mid`, `-near` | 2560×1440, alpha on mid and near |
| field walk sheets | `walk-<char>` | 8 frames × 4 rows (down, left, right, up), 96×128 per frame |
| battle backgrounds | `battle-<poi>` | 2560×1440 |
| battle sprites | `bt-<char>-<anim>`, where anim is `idle`, `stroke`, `hit`, `guard`, `inkwing-idle` or `seal` | horizontal strip, 256×256 per frame, 12 fps unless set |
| enemy sprites | `bt-<enemyId>-<anim>`, where anim is `idle`, `attack`, `hit` or `die` | 256×256 frames |
| portraits | `portrait-<id>-<mood>`, where mood is `calm`, `smile`, `angry` or `sad` | 512×640 |
| icons | `icon-<itemId>` | 128×128 |

- Sprites face **right** for the party and **left** for enemies. The anchor is at the feet.

## 6. Audio
- Runtime synthesis lives in `src/audio.js` (WebAudio). It is unlocked on the first touchend, pointerup or click and sets `navigator.audioSession.type='playback'`.
- Offline music renders go in `assets/music/<id>.mp3` (44.1 kHz stereo, a seamless loop of 30–90 s), together with the generator script under
  `tools/`. Do not use OGG, because iOS cannot play it reliably.
- SFX keys:
  - Combat and menus: `step`, `confirm`, `cancel`, `ring`, `hit`, `clean`, `miss`, `guard`, `heal`, `inkwing`, `seal`, `coin`, `text`, `wipe`.
  - Ambient: `enemy-hit`, `lantern`, `wind`.
- Extras (James, keyed in v1.1): `move` (menu cursor), `step-dirt-02..04` and `step-wood-01..02` (footstep alternates; dirt in the forest, wood in town), `hit-heavy`, `hit-crit` (Clean Line finisher), `combo-finish` (full chain), `enemy-defeat`, and the stereo POI loops `amb-forest` and `amb-town`.
- Files live in `assets/sfx/<key>.mp3`. Loops play with `loop=true`, `loopStart=0.025` and `loopEnd=duration-0.025` to skip the MP3 encoder padding.
- Music keys: `title`, `world`, `forest`, `town`, `battle`.

## 7. Data (`data/*.json`, loaded at boot and passed to the core as strings)
- **`party.json`** `{ "members": [ { "id", "name", "title", "element", "lv", "hp", "atk", "def", "mat", "mdf", "spd", "ink", "strokes": [ { "id", "name", "hits": [ { "gap_ms", "mult" } ], "finish_mult" } ], "seal": { "name", "seals", "mult", "element" } } ] }`
  - `gap_ms` is how long the ring takes to close for that hit. The first hit is measured from the start.
- **`enemies.json`** `{ "enemies": [ { "id", "name", "element", "hp", "atk", "def", "mat", "mdf", "spd", "mon", "xp", "moves": [ { "id", "name", "kind": "phys|elem", "power", "element?", "weight" } ] } ], "encounters": { "<id>": ["enemyId", ...] } }`
  `xp` (int, optional, default 0): experience granted to each surviving party member on victory.
- **`items.json`** `{ "items": [ { "id", "name", "desc", "kind": "heal|healall|ink|bomb", "power", "element?", "price" } ] }`. The sell price is `floor(price/2)`.
- **`shops.json`** `{ "<shopId>": { "name", "keeper", "stock": ["itemId", ...] } }`
- **`world.json`** `{ "nodes": [ { "id", "name", "x", "y", "poi?", "locked?" } ], "paths": [ ["a", "b", [ [x, y] ...bezier ctrl ] ] ], "start": "nodeId" }`
- **`pois/<id>.json`** `{ "id", "name", "w", "h", "spawn": [x, y], "exits": [ { "rect", "to": "world", "node" } ], "solids": [ [x, y, w, h] ], "triggers": [ { "id", "rect": [x, y, w, h], "kind": "battle|dialogue|shop|sign", "ref", "once?" } ], "props": [ { "type", "x", "y", ... } ], "npcs": [ { "id", "x", "y", "name", "look" } ] }`
- **`dialogue.json`** `{ "<scriptId>": { "nodes": { "<nodeId>": { "who", "mood", "text", "next?", "choices?": [ { "text", "next", "set?" } ], "end?" } }, "start" } }`
  - `who` is a party or NPC id, and the portrait key is `portrait-<who>-<mood>`.
- **`transformation.json`** (Jake): gauge fill rules, Unfurl cost and duration, Inkwing form per member.
- **`story.json`** `{ "title", "hook", "chapters": [...] }`

## 8. Folder layout
```
core/            Rust crate -> pkg/ (wasm-pack, committed)
src/             main.js, input.js, ink.js (brush helpers), audio.js, art.js, ui.js, scenes/*.js
data/            JSON from section 7
assets/art/      images and manifest.json; assets/music/; assets/icons/ (PWA icons)
tools/           generators (music render, icon render), not shipped
tests/           Playwright scripts (QA)
team/<team>/     drop folders, never loaded at runtime
```

## 9. Drop folders
- `team/story`: `story.json`, `dialogue.json`, character bios (`cast.md`), plus item and enemy name and flavor text.
  It must match the schema in section 7.
- `team/art`: images named by the keys in section 5, plus an optional `manifest.json`.
- `team/audio`: generator scripts and rendered `mp3`, or JS synth patches exporting `{ key: (ctx, out, t0) => {} }`.
- `team/systems`: numbers to replace in `party.json`, `enemies.json`, `items.json` and `shops.json`, plus a short rationale.
- `team/dev`: patches (`*.patch` against `main`) or new modules with a note saying where they plug in.
- `team/qa`: test scripts and findings (`findings.md`), with each issue labelled `P0`, `P1` or `P2`.
