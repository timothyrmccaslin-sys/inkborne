# team/dev/jared: save module (`inkborne-save-v1`)

Owner: Jared (Dev, lead Tim). This folder is a drop folder. Nothing here edits `core/`, `src/`, `data/` or `pkg/`, and nothing was pushed.
Marc integrates it per SPEC section 9.

## Base and order
- **Core patch `0010-save-module.patch` applies after Rusty's 0009.** It was built on live `core/src/lib.rs` sha `bfeabf62…416493` with
  Rusty's `0007-flee-ambush`, `0008-enemy-xp` and `0009-balance-jake` applied in that order. That result is sha `796d2cd4…c595f0`.
- At 3:45 PM CST the live `lib.rs` became exactly `796d2cd4…` (0007 to 0009 had landed in live). So 0010 applies to **current live** directly. Rusty's
  0007 to 0009 no longer apply to live because they are already in.
- Rusty's 0001 to 0006 were already in the `bfeabf62` base, and his `patches/` folder no longer ships them.
- The JS patch `0011-main-js-save.patch` applies to the current live `src/main.js`, which includes Marc's ib-0.1.1 gear/zones changes.
- If `lib.rs` moves again, run `python3 tools/apply_save.py <copy-of-core>` to regenerate. It anchors on the `Save` struct and on Rusty's 0008 `load_json`.

## Files
| File | What |
|---|---|
| `0010-save-module.patch` | Core: adds `core/src/save.rs` and changes **two spots** in `lib.rs`. The `Save` struct moves to save.rs as `mod save; use save::Save;`. `load_json` delegates to the validated loader. `save_json` and every other line are untouched. |
| `0011-main-js-save.patch` | JS: adds `src/save.js`. `main.js` uses it for `game.save/hasSave/load` and calls `core.set_equipment(items)` right after `set_rules` (guarded with `if (core.set_equipment)`, so it is safe with an old `pkg/`). |
| `core/src/save.rs` | The save module, standalone (same as in 0010). It includes 11 unit tests (`mod save_tests`). |
| `src/save.js` | The localStorage helper, standalone (same as in 0011). |
| `tools/apply_save.py` | Regenerates the lib.rs edit and copies save.rs into a core copy. |
| `tools/smoke.mjs` | Node smoke test: built wasm, live data, mocked localStorage (quota failure, tamper, malformed). |

## Apply (from `/workspace/inkborne`)
```
git apply team/dev/jared/0010-save-module.patch      # creates core/src/save.rs, edits core/src/lib.rs
git apply team/dev/jared/0011-main-js-save.patch     # creates src/save.js, edits src/main.js
cd core && cargo test && cd .. && ./build.sh         # rebuild pkg/
python3 tools/gen-sw-list.py                         # src/save.js must be in the sw.js precache list
```

## Save JSON schema (v1)
Key: `localStorage["inkborne-save-v1"]`, value = `core.save_json()`. Maps are sorted by key.
| Field | Type | Meaning / load rule |
|---|---|---|
| `version` | int | Schema version, currently `1`. If it is missing, the save is treated as v0 (the ib-0.1.0 shape) and migrated with no field rewrites. If it is greater than 1, the load returns `false` (`version_too_new`). |
| `gold` | int | mon. Floats are floored, negatives become 0, and the value is capped at 9,999,999 (`clamped`). |
| `inv` | `{ itemId: count }` | Valid ids are items.json `items` plus equipment ids (carried gear). Unknown ids are dropped (`unknown_item`). Counts are integers capped at 999, and a count of 0 is removed. An `inventory` key is accepted as an alias on load. |
| `equipped` | `{ memberId: { slot: equipId \| null } }` | Slots are `weapon`, `armor` and `accessory`, read from the data. Every equippable member gets every slot (`null` when empty). The loader drops: an unknown member (`unknown_member`), a member outside `equippable_by` (`not_equippable`), an unknown slot (`unknown_slot`), an unknown id (`unknown_equipment`), an id in the wrong slot (`wrong_slot`), and an id the member can't wear per its per-item `equippable_by` (`not_equippable`). |
| `hp` | `{ memberId: number }` | Clamped to 0..max HP at the member's loaded level. A missing member is filled with max HP. |
| `ink` | `{ memberId: number }` | Vermilion Ink, clamped to 0..100. A missing member gets 0, the same as Rusty's 0008. |
| `flags` | `{ key: bool }` | Non-bool values are dropped. |
| `node` | string | World node id. The core does not load `world.json`, so `src/save.js` checks it after a successful load: when `node` is unknown or missing, it calls `core.set_node(world.start)` and `console.warn`s. `start` is the field in `data/world.json`, currently `woods_edge`. |
| `xp` | `{ memberId: int }` | Rusty's 0008. A missing member gets the `xp_table` total for its level (0 when there is no table). |
| `lv` | `{ memberId: int }` | Rusty's 0008. Clamped to 1..cap (`clamped`), then `apply_level` restores the stat_table row, the same as his loader. |

Unknown top-level keys are ignored (`unknown_field`). The members are the `party.json` ids (`itsuki`, `benika`, `gonzo`).

Example (a fresh game with live data, after buying one rice cake; real `save_json()` output):
```json
{"version":1,"gold":105,"inv":{"inkstone_chip":1,"paper_cracker":1,"rice_cake":4},
 "equipped":{"benika":{"accessory":null,"armor":null,"weapon":"prayerslip_bow"},
             "gonzo":{"accessory":"prayer_mala","armor":null,"weapon":"ironband_staff"},
             "itsuki":{"accessory":null,"armor":null,"weapon":"redcord_katana"}},
 "hp":{"benika":177.0,"gonzo":288.0,"itsuki":214.0},"ink":{"benika":30.0,"gonzo":20.0,"itsuki":85.0},
 "flags":{},"node":"hanshi","xp":{"benika":0,"gonzo":0,"itsuki":0},"lv":{"benika":5,"gonzo":5,"itsuki":5}}
```

## Core API (new or changed)
- `load_json(s) -> bool` is lenient. It repairs what it can and records warnings. It returns `false`, with **state untouched**, only for input over 256 KB, invalid JSON, a non-object root, or `version` > 1. Every `return false` happens before any mutation.
- `load_warnings() -> string`: a JSON array of `{code, path, detail}` from the last load. It is `[]` after a clean load.
- `set_equipment(json) -> bool` takes the live `data/items.json` text (its `equipment` array: `id`, `slot`, `equippable_by`, `starting_for`) or Jane's `equipment.json` shape. Call it **before** `load_json`. Without it there are no slots, so every equipped id is dropped. It also puts `starting_for` gear into empty slots for a new game.
- `equip(member, slot, id) -> bool` (empty `id` clears the slot), `equipped_json()`, `save_version()`.
- `save_json()` is unchanged. The catalog and warnings live in a `#[serde(skip)]` field of `Save`, so the `Game` struct and constructor were not touched. That keeps this patch off the lines Rusty edits.

JS (`src/save.js`): `SAVE_KEY`, `readSave()`, `hasSave()`, `writeSave(core)`, `loadSave(core, world)`, `fixNode(core, world)`, `loadWarnings(core)`, `clearSave()`.
`loadSave` runs `console.warn` once per load warning. After a successful load it runs `fixNode`, which checks the saved node against `world.nodes[].id` and falls back to `world.start` through the core's existing `set_node()`. `main.js` passes `game.data.world`. The core did not change for this.
Every storage call is wrapped in try/catch to cover private mode, blocked storage and quota errors. A failed write keeps the old save. A rejected load does not overwrite storage.

## Test results (2026-11-15, ~3:46 PM CST)
- Path A: live `bfeabf62` (sha verified), then `git apply` of Rusty's 0007, 0008 and 0009 (all clean, sha `796d2cd4`), then `git apply 0010`. `cargo test` gives lib **58 passed, 0 failed**: Rusty's 47 plus 11 `save_tests`. Richard's `brushstroke_timing` passes 5/5. There are no compiler warnings.
- Path B: current live (`796d2cd4`) plus 0010, `cargo test --release`: the same result, 58 + 5.
- `wasm-pack build --release --target web` (0.13.1) builds OK. The `.wasm` is 348 KB, and the glue exports `set_equipment`, `load_warnings`, `equip`, `equipped_json` and `save_version`. Nothing was written to the repo's `pkg/`.
- Update (~3:50 PM CST): the node fallback is JS-only, so the core is unchanged and the cargo results above still hold. `0011` was regenerated and `git apply --check` passes on the current live `main.js` (sha `447129a3…`).
- `tools/smoke.mjs` (built wasm, live data, save.js, mocked localStorage):
  - Write and read back works, and `save_json` is byte-identical after a load with 0 warnings.
  - A quota failure returns `false` and keeps the old save.
  - A tampered save loads with the warnings `unknown_item inv.mystery`, `clamped ink.itsuki 400 -> 100` and `not_equippable equipped.benika.weapon`.
  - A truncated JSON returns `false`, and both the state and the stored string are unchanged.
  - An unknown node (`atlantis`) and a missing node both load and fall back to `woods_edge` with a warning. A valid node (`hanshi`) is kept, with no warning.
- `save_tests`:
  - round_trip
  - fresh_game_saves_full_shape
  - drops_unknown_ids_with_warnings
  - without_equipment_catalog_equipped_ids_are_dropped
  - ink_and_numbers_clamped
  - malformed_json_keeps_state (empty, garbage, truncated, array, null, number, v999, >256 KB)
  - missing_fields_default
  - loads_v0_ib_0_1_0_save
  - level_and_xp_restore_and_clamp
  - live_items_json_equipment
  - equip_validates

## Resolved (Tim, 3:48 PM CST)
1. **3 slots** (`weapon`, `armor`, `accessory`). Jane's "6" was 3 slots × 2 tiers.
2. **Live `data/items.json` is the source of truth** for equipment: 11 entries with per-item `equippable_by` and `starting_for`. Jane is moving her stat mods onto those entries. Her `equipment.json` shape is still accepted.
3. **Keep `inv`**, with `inventory` accepted as an alias on load, so ib-0.1.0 saves load unchanged.
4. **Caps are fine for the demo** (gold 9,999,999, item count 999, 256 KB). **A missing `xp` defaults to the level's `xp_table` total**, so it never demotes anyone. Tim is telling Rusty.
5. **Unknown or missing `node`** falls back to `world.start` in `src/save.js` (see the schema above).

## Deferred to a later patch
- Equipment stat bonuses (`mods`) and equip/unequip inventory accounting wait until Jane and Jake design them. `equip()` today only validates and records the slot. `starting_for` gear is placed on a new game.

## Open questions
1. **Level stats on load** rely on Rusty's `apply_level`. Live `data/party.json` has no `stat_table`, so a loaded level does not change stats until Jake's full party.json ships (Rusty's note 2).
2. **Missing `ink` = 0** follows Rusty's 0008.
3. **No backup slot:** QA (John, `save-tamper.md`) suggests a backup key and a checksum. The brief asked for exactly one key, so neither is included. A rejected load never overwrites storage. Tell me if you want an `inkborne-save-v1.bak` rotation.
