# inkborne_core battle API (Rusty, first cut v0.2)

Crate `inkborne_core` (Rust → WASM via `wasm-pack --target web`). One exported class, `Game`.
This crate is a **superset of the integrator's current `core/`**: every export that `core/src/lib.rs`
has today keeps its name, arguments and return shape (marked *compat*), so Marc can swap the
folder in and Richard's `core/tests/brushstroke_timing.rs` keeps compiling. New, renderer-friendly
step-and-query exports are marked *new*.

All JSON in and out is a string. Indices are **fighter indices**: party members are `0..P-1`
(in `party.json` order), enemies follow at `P..P+E-1` (encounter order). They never change during a battle.
Times are milliseconds from `performance.now()` (or `input.pressedAt(a)`, SPEC §4). The core never reads a clock.

## 1. Construction and data

| Export | Returns | Notes |
|---|---|---|
| `new Game(party_json, enemies_json, items_json, seed:u32)` *compat* | `Game` or throws a string `"party.json: …"` | SPEC §7 files. Extra fields are ignored (no `deny_unknown_fields`). |
| `set_rules(transformation_json) -> bool` *compat* | ok | Jake's `transformation.json` (fill amounts, Unfurl, forms, passives). Also reads an optional top-level `combo_windows`. Missing keys keep defaults (= Jake's current values). |
| `set_elements(elements_json) -> bool` *new* | ok | Jake's `elements.json` `chart`. Without it the core uses the SPEC §2 rule (opposite ×2, same ×0.5). |
| `set_combo_windows(json) -> bool` *new* | ok | See §4. |
| `set_config(json) -> bool` *new* | ok | `{ "enemy_damage_mult": 0.8, "seal_gap_ms": 600, "flee_base": 0.5, "var_min": 0.95, "var_max": 1.05 }`, any subset. |

Constants (Rust, also used by Richard's tests): `CLEAN_MS = 95.0`, `GOOD_MS = 150.0`, `judge_delta(delta_ms) -> u8`, `elem_mod(atk, def) -> f64`, `raw(a, d) -> f64`.

## 2. Battle lifecycle

| Export | Returns | Notes |
|---|---|---|
| `start_battle(encounter_id) -> state` *compat* | state JSON (§6) | `enemies.json` `encounters[id]`. |
| `start_battle_opts(encounter_id, opts_json) -> state` *new* | state JSON | `opts = { "can_flee": true, "first": "enemy"\|"party"\|null, "enemies": ["blotling", …] }`. `first` is Ashley's ambush flag (round 1 only). `enemies` overrides the encounter list (1–3 ids; extra are dropped). |
| `current() -> i32` *compat* | fighter index whose turn it is, `-1` when over | |
| `phase() -> String` *new* | `"command"`, `"combo"`, `"seal"`, `"enemy"`, `"over"` | `enemy` = call `step()`/`enemy_turn()`. |
| `outcome() -> String` *new* | `""`, `"win"`, `"lose"`, `"fled"` | |
| `state_json() -> String` *new* (= `battle_json()` *compat*) | §6 | |
| `drain_events() -> String` *new* | JSON array of events (§7), then clears the log | Call once per frame, play them in order. |
| `step() -> String` *new* | result JSON | If the current fighter is an enemy, runs its AI turn (same as `enemy_turn()`); otherwise `{"ok":false,"reason":"party_turn"}`. |
| `enemy_turn() -> String` *compat* | `{kind:"enemy", actor, move, moveKind, element, target, dmg, elem, guarded, killed}` | |
| `spoils() -> u32` *compat* | total `mon` of the encounter | |
| `rewards_json() -> String` *new* | `{ "mon", "xp", "levels": [{ "id", "lv", "xp", "up": bool }] }` after a win | `xp` = sum of optional enemy `xp` (Jake's DESIGN values are the fallback: blotling 12, hollow_lantern 18, smudge_ronin 150). |

## 3. Queries for the command menu

| Export | Returns |
|---|---|
| `actions_json() -> String` *new* | for the current party actor: `[ { "kind", "label", "enabled", "reason"?, … } ]` (below) |
| `targets_json(kind, ref) -> String` *new* | `{ "mode": "one_enemy"\|"one_ally"\|"all_enemies"\|"all_allies"\|"self"\|"none", "targets": [idx…], "default": idx }` |

Action entries (order is the menu order):
```
{ "kind":"stroke",      "label":"Attack",   "enabled":true, "strokes":[{ "index":0, "id":"falling_pine", "name":"Falling Pine", "hits":3, "element":""|"gale", "unlocked":true }] }
{ "kind":"still_water", "label":"Still Water", "enabled":true }
{ "kind":"item",        "label":"Item",     "enabled":bool, "items":[{ "id","name","kind","count","target_mode" }] }
{ "kind":"unfurl",      "label":"Unfurl",   "enabled":bool, "reason":"ink 60/100"|"already Inkwing", "form":"Gale Crane" }
{ "kind":"seal_art",    "label":"Gale Crane Script", "enabled":bool, "reason":"Inkwing only", "seals":4, "element":"gale" }
{ "kind":"magic",       "label":"Magic",    "enabled":bool, "spells":[{ "index","id","name","element","ink_cost","target":"one|all","enabled" }] }   // only if party.json member has `spells`
{ "kind":"flee",        "label":"Flee",     "enabled":bool, "chance":0.0..1.0 }
```
`kind` values for `targets_json`: `stroke`, `item` (ref = item id), `magic` (ref = spell index), `seal_art`, `still_water`, `unfurl`, `flee`.

## 4. Brushstroke Chain (timed Attack): timing semantics

`begin_stroke(actor, target, stroke_index, t0_ms) -> String` *new*: starts the chain and returns the windows:
```
{ "ok":true, "actor":0, "target":3, "stroke":"falling_pine", "name":"Falling Pine", "anchor":"press",
  "hits":[ { "hit":0, "gap_ms":700, "mult":0.7, "clean_ms":95, "good_ms":150 }, … ],
  "next": { "hit":0, "target_ms": t0+700, "clean_ms":95, "good_ms":150, "open_ms": t0+550, "close_ms": t0+850 } }
```
- **Target time.** Hit 0's target is `t0_ms + hits[0].gap_ms`. Hit *n*'s target is **the time of the press that landed hit n−1** `+ hits[n].gap_ms` (`anchor:"press"`, agreed with Jake/Tim). Set `combo_windows.anchor = "close"` to measure from the previous *target* instead (SPEC §7 wording "later hits follow the previous close").
- **Grades** with `delta = press_ms − target_ms` and **half-widths**: `|delta| ≤ clean_ms` → **2 Clean Line** (×1.25 damage, +Ink bonus); `|delta| ≤ good_ms` → **1 good**; otherwise **0 miss**. Early and late are symmetric. A miss, or no press by `target_ms + good_ms`, **ends the chain**; that hit deals no damage.
- **Defaults** `clean_ms = 95`, `good_ms = 150` (`CLEAN_MS`, `GOOD_MS`; Richard's iPad analysis). Override order (last wins): constants → `combo_windows {clean_ms, good_ms}` → `combo_windows.hits["<stroke_id>#<hit>"]` → `hits[i].clean_ms / good_ms` in party.json.
- **Ring drawing.** Draw the ring closing from the previous anchor to `target_ms`; `open_ms`/`close_ms` are the good edges.

| Export | Returns |
|---|---|
| `press(t_ms) -> String` *new* | `{ "hit", "grade", "delta_ms", "dmg"?, "killed"?, "done", "next"? }`. Grades the pending hit. When `done` is true the turn has advanced (see `combo_end` event). |
| `combo_tick(now_ms) -> String` *new* | Call every frame during `combo`/`seal`. If `now_ms > target_ms + good_ms` the pending hit is judged a miss (no press). Returns `{ "timeout":bool, … same as press }` or `{"timeout":false}`. |
| `combo_json() -> String` *new* | the in-progress chain (`null` when none). |
| `cancel_combo() -> bool` *new* | only before the first press; returns to `command`. |
| `stroke(actor, target, stroke_idx, grades: Uint8Array) -> String` *compat* | Pre-judged chain (tests, auto-battle). Stops at the first 0. `{kind:"stroke", name, events:[{hit, grade, dmg?, target?, killed?}], full, perfect, elem, ink}` |
| `judge(delta_ms) -> u8` *compat* | default windows |
| `windows_json() -> String` *compat* | `{ "clean":95, "good":150, "clean_ms":95, "good_ms":150, "anchor":"press" }` |

Seal Arts use the same machinery: `begin_seal(actor, t0_ms)` → `{ "seals":[{ "seal":i, "gap_ms", "clean_ms","good_ms" }], "next":{…} }`; each seal's target is the previous anchor + `seal_gap_ms` (default 600). A missed seal **does not** end the art; it lands at ×0.5. After the last seal, the art resolves against **all** living enemies.

## 5. Other commands

| Export | Notes |
|---|---|
| `act(action_json) -> String` *new* | One entry point for untimed commands. `{"kind":"still_water"}`, `{"kind":"unfurl"}`, `{"kind":"item","item":"pine_needle_tea","target":1}`, `{"kind":"magic","spell":0,"target":3}`, `{"kind":"flee"}`, `{"kind":"stroke","stroke":0,"target":3,"grades":[2,1,2]}`, `{"kind":"seal_art","grades":[2,2,1,0]}`. Acts for `current()`. Returns `{ "ok", "kind", … }` or `{ "ok":false, "reason" }`. |
| `guard(actor)` *compat* | Still Water: damage ×0.5 until the actor's next turn; heals 10% max HP (15% in Inkwing); +6 Ink (not in Inkwing); Ink from damage taken while guarding ×1.5. |
| `inkwing(actor)` *compat* | Unfurl. Only when `ink ≥ 100` and not already Inkwing. Ink → 0, heals 15% max HP, uses the turn, then the next **3** own turns are Inkwing. |
| `seal_art(actor, hits, clean)` *compat* | Pre-judged Seal Art (counts). |
| `use_item(actor, item_id, target)` *compat* | `heal`, `healall`, `ink`, `bomb` (SPEC §7). |
| `debug_ink(actor, v)` *compat* | |

## 6. State JSON
```
{ "phase":"command", "round":1, "turn":0, "over":null, "outcome":"", "can_flee":true, "encounter":"sumikage_c",
  "order":[0,4,1,3,2,5],            // this round, by speed
  "fighters":[ { "idx":0, "side":0, "slot":0, "id":"itsuki", "name":"Itsuki", "element":"gale", "hp":214, "max_hp":214,
                 "atk":32, "def":18, "mat":14, "mdf":14, "spd":17,   // effective (Inkwing multipliers applied)
                 "ink":60, "guarding":false, "inkwing":0, "form":"Gale Crane", "form_element":"gale", "alive":true, "mon":0 } ],
  "combo": null }
```
`inkwing` = Inkwing turns left (0 = normal form). `side` 0 = party, 1 = enemy.

## 7. Events (`drain_events()`)
Every event has `"type"`. In order of a typical turn:
`battle_start {encounter, party:[idx], enemies:[idx], first}` · `round_start {round, order}` · `turn_start {actor}` ·
`combo_start {actor, target, stroke, name, hits}` · `press {actor, hit, grade, delta_ms, timeout}` ·
`damage {source, target, dmg, elem, guarded, killed, hit?, grade?}` · `heal {target, amount, source}` · `ink {actor, gain, ink, reason}` ·
`combo_end {actor, landed, full, perfect}` (perfect = red Seal stamp) · `guard {actor, heal}` · `unfurl {actor, form, heal}` · `inkwing_end {actor}` ·
`seal_start {actor, seals}` · `seal_end {actor, power}` · `item {actor, item, kind, target}` · `magic {actor, spell, element}` ·
`enemy_move {actor, move, name, kind, element, targets}` · `ko {target}` · `flee {ok, chance}` · `battle_end {outcome, mon, xp}`.

Event → SFX (SPEC §6): `press grade 2` → `clean`, `grade 1` → `hit`, `grade 0` → `miss`; `combo_end perfect` → `combo-finish` + seal stamp; `guard` → `guard`; `unfurl` → `inkwing`; `heal` → `heal`; `ko` (enemy) → `enemy-defeat`.

## 8. Data the core reads (and optional extensions)
- `party.json` (Jake): SPEC §7 member shape. Uses `strokes[].unlock_lv` (default 1), `seal.id`, `seal.stat` (`atk`|`mat`, default `mat`), optional `hits[].clean_ms/good_ms`, optional top-level `combo_windows`, optional `progression.xp_table` + `members[].stat_table` for level-ups, optional `members[].spells` (out-of-form Magic, see below).
- `enemies.json`: SPEC §7. Optional per enemy `xp`; optional per move AI fields: `"target": "random"|"lowest_hp"|"highest_hp"|"weak"|"all"`, `"hp_below": 0.5` (only when own HP fraction < value), `"kind": "phys"|"elem"|"heal"|"guard"`.
- `items.json` (Jane): SPEC §7 kinds `heal|healall|ink|bomb`.
- `transformation.json` (Jake): `fill.*`, `unfurl.{cost,heal_pct_max_hp,duration_turns}`, `inkwing_rules.still_water_heal_pct`, `reset.on_ko`, `forms.<id>.{form_name, element, mult, passive.id, strokes_element}`. Passives implemented: `tailwind` (acts first), `kindling_prayer` (5% party heal per Clean seal), `slate_mantle` (party takes ×0.85).
- `members[].spells` (optional, not in SPEC yet): `[{ "id","name","element","power","ink_cost","target":"one|all","kind":"elem|heal" }]` — Magic costs Vermilion Ink. Without it, Magic = Seal Arts (Inkwing-gated), per SPEC §2.

## 9. Formulas (Jake's DESIGN.md)
`raw(a,d) = max(a*0.25, a*2-d)`; stroke hit = `raw(atk,def) * hit.mult * (1.25 if Clean) * elem * guard * var`, last hit of a completed chain also `* finish_mult`; seal = `raw(seal_stat, mdf) * seal.mult * (1.25|1|0.5) * elem * var` per seal; enemy = `raw(atk,def)` (phys) or `raw(mat,mdf)*elem` (elem) `* power * var * enemy_damage_mult`; `var` uniform 0.95–1.05 (seeded xorshift, WASM-safe); final `max(1, round)`. Ink from damage taken: `round(30*dmg/max_hp)` clamped 1..15, ×1.5 in Still Water.

## 10. JS example
```js
import init, { Game } from './pkg/inkborne_core.js';
await init();
const g = new Game(data.party, data.enemies, data.items, Date.now() >>> 0);
g.set_rules(data.transformation); g.set_elements(data.elements);
g.start_battle_opts('sumikage_c', JSON.stringify({ can_flee: true, first: null }));
function frame(now) {
  for (const ev of JSON.parse(g.drain_events())) battleView.play(ev);   // animate + sfx
  const ph = g.phase();
  if (ph === 'enemy' && battleView.idle()) g.step();
  if (ph === 'combo' || ph === 'seal') {
    if (input.pressed('confirm')) g.press(input.pressedAt('confirm'));
    else g.combo_tick(now);
  }
  if (ph !== 'over') requestAnimationFrame(frame); else game.pop({ outcome: g.outcome(), rewards: JSON.parse(g.rewards_json()) });
}
// menu: JSON.parse(g.actions_json()); on Attack + target pick:
const w = JSON.parse(g.begin_stroke(g.current(), target, 0, performance.now()));  // draw rings from w.next
```
