# inkborne_core API: live exports (0.1.0 + landed 0001–0006) + Rusty's patches 0007–0009

`Game` (wasm-bindgen class) from `core/src/lib.rs`. JSON in/out is strings. Fighter indices: party `0..2` (party.json order),
then enemies `3..` (encounter order, max 3). Times are ms from `performance.now()` / `input.pressedAt()`; the core never reads a clock.
**Bold** = added by 0001–0006 (now in the live work tree for 0.1.1). *[0007]*/*[0008]*/*[0009]* = pending patches. Everything else is 0.1.0 and unchanged.

## Construction / rules
| Export | Notes |
|---|---|
| `new Game(party, enemies, items, seed)` | SPEC §7 files. Unknown fields ignored. |
| `set_rules(transformation_json) -> bool` | Inkwing forms/passives (existing). **Now also** gauge/fill/reset/unfurl numbers, `inkwing_rules.still_water_heal_pct`, optional `still_water {damage_mult, heal_pct}` and `combo_windows {}`. |
| **`set_combo_windows(json) -> bool`** | `{ "clean_ms":95, "good_ms":150, "anchor":"press"\|"close", "hits": { "falling_pine#2": { "clean_ms":110 } } }` |
| **`set_elements(elements_json) -> bool`** | Jake's `elements.json` `chart`. |
| **`set_enemy_damage_mult(m)`** | default 0.8 |
| **`ink_rules_json()`** | `{max, unfurl_cost, unfurl_turns, stroke_hit, clean_bonus}` |

Rust-level: `CLEAN_MS = 95.0`, `GOOD_MS = 150.0`, `judge_delta(d)`, **`judge_with(d, clean, good)`**, `elem_mod(a, d)`, `raw(a, d)`.

## Timing semantics (Brushstroke Chain)
- `delta = press_ms − target_ms`. Grades use **half-widths**: `|delta| ≤ clean` → 2 Clean Line (×1.25), `≤ good` → 1 good, else 0 miss. Early = late.
- Hit 0 target = `t0 + gap_ms[0]`; hit n target = **time of the press that landed hit n−1** + `gap_ms[n]` (or previous target with `anchor:"close"`).
- A miss or no press by `target + good` ends the chain. Window precedence: constants < `combo_windows` < `combo_windows.hits["id#n"]` < party.json `hits[n].clean_ms/good_ms`.
- `judge(delta) -> u8` and `windows_json()` → `{"clean":95,"good":150,"clean_ms":95,"good_ms":150,"anchor":"press"}` reflect the live windows.

| Export | Returns |
|---|---|
| **`begin_stroke(actor, target, stroke_idx, t0_ms)`** | `{ok, actor, target, stroke, name, anchor, hits:[{hit,gap_ms,mult,clean_ms,good_ms}], next:{hit,start_ms,target_ms,clean_ms,good_ms,open_ms,close_ms}}` or `{ok:false, reason}` (`over`, `combo_in_progress`, `bad_index`, `not_party_actor`, `target_down`, `bad_time`, `no_strokes`, `no_hits`) |
| **`press(t_ms)`** | `{ok, hit, grade, delta_ms, timeout:false, done, next?}`; when `done`: `result` = the `stroke()` result, turn advanced |
| **`combo_tick(now_ms)`** | `{ok, timeout:false}` or (past the good window) same as `press` with `timeout:true, grade:0, done:true` |
| **`combo_json()`** | `{actor,target,stroke,name,grades,presses,next}` or `null` |
| **`cancel_combo() -> bool`** | only before the first press |
| `stroke(actor, target, idx, grades: Uint8Array)` | pre-judged chain: `{kind:"stroke", name, events:[{hit,grade,dmg?,target?,killed?} …, {glance,dmg,target}?], full, perfect, elem, ink}` |

## Battle flow
| Export | Notes |
|---|---|
| `start_battle(encounter) -> state` | max 3 enemies (**cap added**) |
| `battle_json()` | `{fighters:[{side,idx,id,name,element,hp,max_hp,atk,def,mat,mdf,spd,ink,guarding,inkwing,alive,mon,form}], turn, round, over}` |
| `current() -> i32` | −1 when over |
| **`step()`** | enemy turn → same as `enemy_turn()`; else `{ok:false, reason:"party_turn"\|"over"}` |
| `enemy_turn()` | `{kind:"enemy", actor, move, moveKind, element, target, dmg, elem, guarded, killed}` + **`moveId, targets[], hits:[{target,dmg,elem,guarded,killed}], ai`**; heal moves add `heal` |
| `inkwing(actor)` / **`unfurl(actor)`** | needs ink ≥ cost (100). `{kind:"inkwing", ok, actor, heal, form, turns}` or `{ok:false, reason:"ink_not_full"\|"already_inkwing"\|"not_party_actor"\|"bad_index"}`. Inkwing lasts 3 own turns after the Unfurl turn. |
| **`can_unfurl(actor) -> bool`** | for the menu |
| `seal_art(actor, hits, clean)` | unchanged |
| `guard(actor)` | Still Water: `{kind:"guard", ok, actor, heal, hp, ink, damage_mult}`; ×0.5 damage until own next turn, heal 10% (15% Inkwing), +6 ink (×1.5 ink from damage while guarding) |
| `use_item(actor, id, target)` | unchanged (ink items ignored on an Inkwing target) |
| **`elem(atk, def) -> f64`**, **`affinity_json(target)`** | `{element, weak:[…], resist:[…]}` |
| `spoils()`, `debug_ink(actor, v)` | unchanged |
| save / shop / walker exports | unchanged |

## enemies.json AI fields (all optional)
```
{ "id":"smudge_ronin", …, "ai":"lowest_hp_pct",
  "moves":[ { "id":"drip", "kind":"phys", "power":1.1, "weight":3 },
            { "id":"unwrite", "kind":"elem", "element":"stone", "power":1.3, "weight":1, "target":"weak" },
            { "id":"brace", "kind":"guard", "weight":4, "hp_below":0.3 },
            { "id":"reink", "kind":"heal", "power":2, "weight":2 } ] }
```
`target`: `random` (default) · `lowest_hp` · `lowest_hp_pct` · `highest_hp` · `weak` (member weak to the move element) · `all`.
`heal` is only eligible when an enemy is below 70% HP (heals the most-hurt one by `power × mat`). `hp_below` gates by the enemy's own HP fraction.

## JS sketch
```js
const g = new Game(data.party, data.enemies, data.items, Date.now() >>> 0);
g.set_rules(data.transformation); g.set_elements(data.elements);
g.start_battle(params.encounter);
// Attack chosen:
let r = JSON.parse(g.begin_stroke(g.current(), target, 0, performance.now()));
function frame(now) {
  if (r.next) {                                   // draw ring closing toward r.next.target_ms
    if (input.pressed('confirm')) r = JSON.parse(g.press(input.pressedAt('confirm')));
    else { const t = JSON.parse(g.combo_tick(now)); if (t.timeout) r = t; }
    // r.grade: 2 → sfx 'clean', 1 → 'hit', 0 → 'miss'; r.done → play r.result.events, r.result.perfect → seal stamp
  }
  const c = g.current();
  if (c >= 0 && JSON.parse(g.battle_json()).fighters[c].side === 1 && view.idle()) view.play(JSON.parse(g.step()));
}
```

## Flee and encounter flags *[0007]*
| Export | Notes |
|---|---|
| `start_battle_opts(encounter, opts_json) -> state` | `{ "first": "enemy"\|"party"\|null, "canFlee": bool }` (`can_flee` accepted). `first` = that side acts first in **round 1** (each side still by speed). Bad JSON or unknown values fall back to the defaults (no ambush, Flee allowed). |
| `flee(actor) -> String` | `{kind:"flee", ok:true, fled:bool, actor, chance, roll}` or `{kind:"flee", ok:false, reason}`; reasons `over`, `cannot_flee`, `bad_index`, `not_party_actor`, `not_your_turn`, `combo_in_progress`. On success `current() == -1`, `battle_json().over == "fled"`, HP and Ink saved, no mon/XP. On failure the turn passes. |
| `can_flee() -> bool`, `flee_chance() -> f64` | for the menu (grey out / show %) |
| `set_flee_rules(json) -> bool` | `{ base, per_spd, per_fail, min, max }`; also `set_rules({"flee":{…}})` |

**Formula:** `p = clamp(base + per_spd × (avg living party SPD − avg living enemy SPD) + per_fail × failed_tries, min, max)`, with defaults 0.5 / 0.05 / 0.25 / 0.25 / 0.95. Effective SPD includes Inkwing. The flee succeeds if `rng.next() < p` (seeded xorshift, deterministic per seed).
`battle_json()` adds `canFlee`, `first`, `fleeChance`.

## XP and level-ups *[0008]*
- enemies.json: `xp` per enemy (optional, default 0). party.json (optional): `progression { level_cap, xp_table:[{lv,total,to_next}] }`, `members[].stat_table:[{lv,hp,atk,def,mat,mdf,spd}]`.
- At victory: living members get the sum of enemy `xp`, KO'd get 0. A member levels while `xp ≥ xp_table[lv+1].total` (up to the cap). Stats come from `stat_table`, and current HP rises by the max-HP gained.
- `rewards_json()` / `battle_json().rewards` (null until a win): `{ "mon", "xp", "members": [ { "id","name","alive","gained","xp","lv_before","lv","leveled_up","next_total","stats" } ] }`.
- `party_json()` adds `lv` (current), `xp`, `nextXp`. `save_json()` adds `xp`/`lv` maps; older saves still load.

## Balance *[0009]*
Seal Art damage per target is `raw(seal_stat, target.mdf) × seal.mult × power × 1.6 × elem × var`, where `seal.stat` picks atk or mat and the defender side is always mdf. Variance is `VAR_MIN 0.95 … VAR_MAX 1.05`.
