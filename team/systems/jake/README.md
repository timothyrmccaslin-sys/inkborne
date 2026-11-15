# team/systems/jake: party stats and Vermilion Ink (Inkborne)
Owner: Jake (Systems), lead Tim. This is a drop folder, so nothing here is loaded at runtime. Marc copies it into `data/` (SPEC section 9).

## Files
| File | What | Destination |
|---|---|---|
| `party.json` | 3 members in the **exact SPEC v1 section 7 shape** (`id, name, title, element, lv, hp, atk, def, mat, mdf, spd, ink, strokes[], seal{}`) plus extensions: `role`, `base`, `growth`, `stat_table` (L1 to 20), `strokes[].unlock_lv`, `seal.stat`, and a top-level `progression` (level cap, XP formula, `xp_table`) | `data/party.json` (drop-in) |
| `transformation.json` | gauge max, fill sources, reset rules, Unfurl cost and duration, Inkwing form per member (stat multipliers, passive, stroke element) | proposed new `data/transformation.json`, or hardcode as constants in the core |
| `elements.json` | the Six Inks matrix (SPEC section 2 rule spelled out) | optional `data/elements.json` (the core can just hardcode the rule) |
| `DESIGN.md` | model, formulas (damage, XP, gauge), balance intent, worked examples | reference |
| `tools/build.py` | generates all three JSON files from one constants block (stdlib Python) | not shipped |
| `tools/validate.py` | no-dependency checks: SPEC fields, stat_table and xp_table math, element chart, gauge rules vs SPEC, gauge pacing, banned-word IP scan | not shipped |

Run: `python3 tools/build.py && python3 tools/validate.py` (prints the pacing table and `OK`).

## How it plugs into the Rust core (`tabula_core` per SPEC)
SPEC section 7 says the JSON is loaded at boot and passed to the core as strings. Either use that path or embed it with `include_str!("../../data/party.json")`. Serde ignores unknown fields by default, so a minimal SPEC-only struct still parses this file. Don't put `deny_unknown_fields` on these structs.

```rust
use serde::Deserialize;

#[derive(Deserialize, Clone)]
pub struct PartyFile { pub members: Vec<MemberDef>, #[serde(default)] pub progression: Option<Progression> }

#[derive(Deserialize, Clone)]
pub struct MemberDef {
    pub id: String, pub name: String, pub title: String, pub element: Element,
    pub lv: u32, pub hp: u32, pub atk: u32, pub def: u32, pub mat: u32, pub mdf: u32, pub spd: u32,
    pub ink: u32, pub strokes: Vec<StrokeDef>, pub seal: SealDef,
    #[serde(default)] pub stat_table: Vec<StatRow>,          // index = lv - 1
}
#[derive(Deserialize, Clone)]
pub struct StrokeDef { pub id: String, pub name: String, pub hits: Vec<HitDef>, pub finish_mult: f64,
                       #[serde(default = "one")] pub unlock_lv: u32 }
#[derive(Deserialize, Clone, Copy)] pub struct HitDef { pub gap_ms: u32, pub mult: f64 }
#[derive(Deserialize, Clone)]
pub struct SealDef { #[serde(default)] pub id: String, pub name: String, pub seals: u32, pub mult: f64, pub element: Element,
                     #[serde(default = "mat")] pub stat: SealStat }
#[derive(Deserialize, Clone, Copy)] #[serde(rename_all = "lowercase")] pub enum SealStat { Atk, Mat }
#[derive(Deserialize, Clone, Copy, PartialEq)] #[serde(rename_all = "lowercase")]
pub enum Element { Ember, Tide, Gale, Stone, Dawn, Dusk, None }
#[derive(Deserialize, Clone, Copy)]
pub struct StatRow { pub lv: u32, pub hp: u32, pub atk: u32, pub def: u32, pub mat: u32, pub mdf: u32, pub spd: u32 }
#[derive(Deserialize, Clone)] pub struct Progression { pub level_cap: u32, pub xp_table: Vec<XpRow> }
#[derive(Deserialize, Clone, Copy)] pub struct XpRow { pub lv: u32, pub total: u32, pub to_next: u32 }
fn one() -> u32 { 1 }
fn mat() -> SealStat { SealStat::Mat }

// transformation.json (only the fields the rules need)
#[derive(Deserialize)] pub struct InkRules { pub gauge: Gauge, pub fill: Fill, pub unfurl: Unfurl,
                                             pub forms: std::collections::HashMap<String, FormDef> }
#[derive(Deserialize)] pub struct Gauge { pub max: u32 }
#[derive(Deserialize)] pub struct Fill { pub stroke_hit: u32, pub clean_line_bonus: u32, pub chain_complete_bonus: u32,
    pub perfect_chain_bonus: u32, pub kill_bonus: u32, pub damage_taken: DmgFill, pub still_water_use: u32,
    pub still_water_damage_taken_mult: f64 }
#[derive(Deserialize)] pub struct DmgFill { pub per_pct_hp_lost: f64, pub min_if_damaged: u32, pub max_per_hit: u32 }
#[derive(Deserialize)] pub struct Unfurl { pub cost: u32, pub heal_pct_max_hp: u32, pub duration_turns: u32 }
#[derive(Deserialize)] pub struct FormDef { pub form_name: String, pub element: Element,
    pub mult: std::collections::HashMap<String, f64>, pub passive: Passive }
#[derive(Deserialize)] pub struct Passive { pub id: String, pub name: String, pub effect: serde_json::Value }
```
**Save state per member** (core `save_json()`): `lv`, `xp`, `hp`, `ink`. Recompute max stats from `stat_table[lv-1]` on load, then clamp `hp` to 1..max, `ink` to 0..100, and `lv` to 1..level_cap. Inkwing state isn't saved because it always ends with the battle.

Gauge math with no floats: `dmg_fill = clamp((30*dmg*2 + max_hp) / (2*max_hp), 1, 15)` gives round-half-up of 30·dmg/max_hp. For Still Water, multiply by 3/2 before rounding.

## Alignment notes
- **SPEC.md existed and is matched.** Field names, the 0 to 100 gauge, the full-gauge cost, 3 Inkwing turns, ATK/DEF up, Clean Line ×1.25, Still Water halving damage and healing 10%, and the Six Inks rule all match it.
- **Rusty's code:** `core/src/` is still empty, so there are no structs to align with yet. The struct shapes above are the proposal. If he names things differently, the JSON keys stay the SPEC ones and he can use `#[serde(rename)]`.

## Open questions and dependencies
1. **MP (Tim and Marc):** the brief asked for MP, but SPEC v1 has no MP resource. Magic is Inkwing-gated Seal Arts. I left MP out. If we want out-of-form spells (for example, a Benika heal), SPEC needs an `mp` field and a spells list.
2. **Gauge name (resolved):** SPEC v1.1 calls it **Vermilion Ink** (key `ink`), and that name is used here. Party `name` values are the canon names Itsuki, Benika and Gonzō (keep the ō glyph in the UI font).
3. **Element names:** canon says Wind/Fire/Earth. I mapped those to SPEC's Gale/Ember/Stone, which matches the SPEC palette tints.
4. **`transformation.json` isn't in SPEC section 7 (Marc):** add it as `data/transformation.json`, or the core hardcodes the numbers.
5. **Enemy XP (Karen):** SPEC `enemies.json` has `mon` but no `xp`. My suggested values are in DESIGN.md. Karen also owns enemy stats; DESIGN.md has the damage examples I assumed (Blotling def 6, mdf 4).
6. **Ink items (Jane):** `items.json` kind `ink`. I'd suggest powers of 25 and 50 so that 100 is reachable from an item.
7. **Strokes and Seal Arts:** names follow canon (Falling Pine, Three Prayer Slips, Temple Bell). The second Strokes (Wet Edge, Lantern Volley, Mountain Gong) and the Seal Art names are mine. Lisa should approve them. `gap_ms` needs tuning with Rusty and QA on iPad.
8. **Demo showcase:** if the demo has to guarantee one transformation, the integrator can set a member's starting `ink` to around 70 for the scripted fight.
9. **Name with a macron:** `Gonzō` needs the UI font to have the ō glyph. The id is plain ASCII (`gonzo`).

## Combo timing windows (Rusty)
The core grades each press against its target time (previous press + `gap_ms`): clean within ±70 ms, good within ±150 ms (the core's current values per Richard's tests), and a miss otherwise (a miss ends the chain). Rusty keeps these in a data block `combo_windows { clean_ms, good_ms }` with optional per-hit overrides. They are placeholders until he and Richard test on iPad.

Gap floor: no `gap_ms` is below 420 ms, per Richard's iPad timing analysis (`core/tests/combo-timing-findings.md`). He recommends widening the clean window to about 90–100 ms for touch input.
