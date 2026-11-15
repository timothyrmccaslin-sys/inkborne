# Party stats and the Vermilion Gauge: design notes
Owner: Jake (Systems). Lead: Tim. Status: v1 draft, matches SPEC v1 section 2 and section 7. Updated Nov 15, 2026.

Names come from Lisa's canon (`/workspace/inkborne-creative/story/CANON.md`). Mechanics come from SPEC v1. Where the two use different names for the same thing, the data uses the SPEC field name and the canon display name (see README "Open questions").

## 1. Stat model
Six stats, all SPEC field names: `hp`, `atk` (physical attack), `def` (physical defense), `mat` (magic attack), `mdf` (magic defense), `spd` (turn order). The gauge value is `ink` (0 to 100). There is **no MP**: SPEC v1 has no MP resource, and magic is the Seal Art, which you only get in Inkwing form. Healing comes from Still Water, items, and Benika's Inkwing passive (see open question Q1).

| Member | Role | Element | L1 HP/ATK/DEF/MAT/MDF/SPD | L20 HP/ATK/DEF/MAT/MDF/SPD |
|---|---|---|---|---|
| Itsuki Hane, wandering swordsman | physical DPS | Gale | 120 / 18 / 10 / 8 / 8 / 14 | 386 / 64 / 35 / 25 / 27 / 31 |
| Benika Matsuo, shrine archer | support, magic | Ember | 100 / 13 / 8 / 17 / 13 / 16 | 309 / 43 / 27 / 63 / 45 / 35 |
| Gonzō Kuraishi, retired temple monk | tank, heavy hitter | Stone | 160 / 16 / 15 / 6 / 11 / 8 | 521 / 56 / 53 / 17 / 38 / 18 |

**Growth:** `stat(lv) = base + floor(growth * (lv - 1) + 0.5)`. Growth is linear, so balance stays predictable over a short demo. Every level is precomputed in `stat_table`, so the core can just index it and never needs floats.

**Level cap is 20.** A demo run (forest fights plus the Smudge Ronin) should end around L4 to L6. The cap leaves headroom for a later build.

**XP curve:** `to_next(lv) = floor(20 * lv^1.5 + 10)`, which gives 30, 66, 113, 170, 233 ... 1666 (L19 to L20), for 13,608 XP total to the cap. The full table is `progression.xp_table` (`total` = cumulative XP at that level). Every member alive at victory gets the full encounter XP. KO'd members get none.

Suggested enemy XP (Karen owns it, and it needs an `xp` field in `enemies.json`): Blotling 12, Hollow Lantern 18, Smudge Ronin 150. About six fodder fights plus the boss puts the party at L5.

## 2. Damage formula (proposal for Rusty's core)
```
raw(a, d)     = max(a * 0.25, a * 2 - d)                       // never below a quarter of attack
stroke hit    = raw(atk, def) * hit.mult * clean * elem * guard * var
  last hit of a COMPLETED chain also * stroke.finish_mult
seal (each)   = raw(seal_stat, mdf) * seal.mult * clean * elem * guard * var
  seal_stat   = atk or mat per seal.stat (Itsuki and Gonzō: atk, Benika: mat)
  a missed seal still lands at * 0.5 (magic is forgiving), a missed Stroke ends the chain with no damage for that hit
clean         = 1.25 on a Clean Line press (SPEC), else 1.0
elem          = elements.json chart[attack_element][defender_element]
                normal-form Strokes are neutral ("none" = 1.0), Inkwing Strokes and all Seal Arts use the form element
guard         = 0.5 if the defender used Still Water this round (SPEC)
var           = uniform 0.95..1.05 from the core's seeded RNG
final         = max(1, round_half_up(result))
```
Inkwing stat multipliers apply to `atk/def/mat/mdf/spd` before `raw()`. Max HP never changes. Gonzō's Slate Mantle multiplies damage the party takes by 0.85.

**Worked example, Itsuki L1 vs a Blotling (def 6, Dusk):** raw = max(4.5, 36 − 6) = 30. Falling Pine with all three hits good gives 30×0.7 = 21, 30×0.8 = 24, and 30×1.0×1.3 = 39, so **84** in total. All three Clean is ×1.25 per hit, so **105**.

**Same chain in Gale Crane Inkwing:** atk 18×1.5 = 27, so raw = 48 and the chain does **134**. The Strokes are now Gale, so against a Stone enemy that's ×2, or **269**.

**Seal Arts at L1, vs mdf 4, all seals Clean:**
- Itsuki: raw(27, 4) = 50 × 0.55 × 4 × 1.25 ≈ 138.
- Benika: raw(25.5, 4) = 47 × 0.4 × 5 × 1.25 ≈ 118, plus a party heal of 5% for each Clean seal (25% total).
- Gonzō: raw(22.4, 4) = 40.8 × 0.8 × 3 × 1.25 ≈ 122.

**Taking damage:** an enemy with atk 12 hits Itsuki (def 10) for raw(12, 10) = 14. If he's in Still Water, that's 7, and he also heals 10% max HP (12). Gonzō takes 9.

## 3. Vermilion Gauge (`ink`, 0 to 100 per character)
**Fill sources** (all integers, clamped to 100):

| Source | Ink |
|---|---|
| each Stroke hit landed (good press) | +4 |
| Clean Line bonus on that hit | +4 more (8 total) |
| chain completed (every hit landed) | +6 |
| perfect chain (every hit Clean, the red Seal stamp) | +10, which **replaces** the +6 |
| landing a kill | +3 |
| damage taken | `round_half_up(30 * dmg / max_hp)`, minimum 1 if damaged, max 15 per hit |
| using Still Water | +6, and damage taken that round fills ×1.5 (computed on the halved damage) |
| `ink` item (Jane, `items.json` kind `ink`) | + item `power` |

There's no gain while in Inkwing (no stacking a second Unfurl), and Seal Arts don't fill. The gauge doesn't decay.

**Reset rules:** KO sets it to 0 (the ink spills). Unfurling sets it to 0. It **persists** between battles and is saved, the same way as HP. Fleeing keeps it. Load clamps it to 0 to 100 (see John's save-tamper notes).

**Pacing target** (validate.py prints this): attacking every turn with the starter Stroke and taking no damage, Itsuki and Benika fill in 6 turns with good presses and 3 with perfect ones. Gonzō takes 8 and 4, but as the tank who guards he gets most of his ink from damage and Still Water. Taking a hit for about 12% HP adds about 4 per hit. So a typical player Unfurls once per tough fight, around turns 4 to 5, and a skilled player can do it twice against the boss.

**Example:** Gonzō uses Still Water (+6), then takes a 20 damage hit, halved to 10. That's 10/160 = 6.25% HP, so 30 × 0.0625 = 1.9, ×1.5 = 2.8, which rounds to 3. Total +9 for the round, plus he heals 16 HP.

## 4. Unfurl and Inkwing form
- **Cost:** a full gauge (100), and the command is `Unfurl` (canon), available only at 100. Unfurling **uses the turn**: the character transforms, heals 15% max HP, and their next 3 own turns are in Inkwing (SPEC: "lasts 3 of that character's turns").
- **In Inkwing:** the commands are Seal Art (timed magic), Stroke (now carries the form element), Still Water (heals 15% instead of 10%), and Item.
- **Revert:** at the end of the 3rd Inkwing turn, on KO, or at battle end. Stats go back to normal, current HP is kept (clamped to max), and ink stays 0. You can't revert early. There's one tier for the demo, and the data has `tiers: 1` so a later build can add levels.

| Form | Element | ATK | DEF | MAT | MDF | SPD | Passive |
|---|---|---|---|---|---|---|---|
| Itsuki, Gale Crane | Gale | ×1.5 | ×1.25 | ×1.3 | ×1.25 | ×1.2 | **Tailwind:** acts first every round |
| Benika, Ember Kite | Ember | ×1.25 | ×1.25 | ×1.5 | ×1.4 | ×1.15 | **Kindling Prayer:** each Clean seal heals every living ally 5% max HP |
| Gonzō, Stone Owl | Stone | ×1.4 | ×1.6 | ×1.2 | ×1.4 | ×1.0 | **Slate Mantle:** the party takes ×0.85 damage |

Seal Arts (from `party.json` `seal`): Itsuki's *Gale Crane Script* (4 seals, ×0.55, scales off ATK), Benika's *Ember Kite Litany* (5 seals, ×0.4, MAT), and Gonzō's *Stone Owl Verse* (3 seals, ×0.8, ATK).

## 5. Balance intent
- **Roles are clear at a glance.** Itsuki hits hardest per Stroke and is fragile. Benika is fastest, has the strongest magic, and becomes the healer when she Unfurls. Gonzō has about 1.35× Itsuki's HP and 1.5× his DEF, and he fills the gauge by getting hit.
- **Skill pays, but it isn't required.** Clean Lines give ×1.25 damage and double the ink per hit, so a perfect chain fills the gauge about 2× faster than a sloppy one. Missing a press costs that hit and the chain bonus, but nothing worse.
- **Inkwing is a 3-turn spike:** about +60% damage, and ×2 when you exploit an element. One Unfurl should swing a boss fight without trivializing it.
- **Elements matter most in Inkwing.** Normal Strokes are neutral, so elemental play is a choice you make once you've built up ink.
- Strokes and gap_ms values are starter numbers. Tune them with Rusty and QA on a real iPad (touch latency).
