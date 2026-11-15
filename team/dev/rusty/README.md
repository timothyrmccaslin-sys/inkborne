# team/dev/rusty: battle-core patches for `core/` (inkborne_core)

Owner: Rusty (Dev, lead Tim). Per Marc's direction, these are **patches against the integrator's live
`/workspace/inkborne/core/src/lib.rs`**, not a separate crate. Nothing here edits `core/` and nothing was pushed.
All existing exports keep their names, signatures and JSON shapes; the patches only add.

**Status (2026-11-15 3:43 PM CST).** Patches 0001–0006 have **landed** in the live work tree (going into 0.1.1).
Live `core/src/lib.rs` (sha256 `bfeabf623430cf57eeb3d7088cd5661a2d773dcf7f75b0945a50b95fea416493`, 15:41:09) is byte-for-byte
git HEAD 0.1.0 (`c4ef1569…94318`) + the current 0001–0006 + two integrator lines in `use_item` (`gear` guard, ink-item check).
So they are dropped from `patches/`; `STEPS=all tools/chain.sh` regenerates them against HEAD for the record.
**Base for 0007–0009: live sha `bfeabf62…416493`.** If live changes again, run `tools/chain.sh` (re-reads live core,
writes to a temp dir, publishes only if every step builds).

## Landed (0.1.1): 0001–0006
Combo timing (data-overridable ±95/±150 half-widths, timed `begin_stroke`/`press`/`combo_tick`), Vermilion Ink + Unfurl
from transformation.json (fallback defaults now match Jake's 3:36 PM values 4 / +4 / 6 / 10-replaces, on_ko reset; `on_ko`
accepts a number or "keep"/"reset"), elements chart, Still Water, data-driven enemy AI, 25 tests (`mod rusty_tests`).
Details: API.md.

## Patches (apply in order from `/workspace/inkborne`)
| # | File | What it changes |
|---|---|---|
| 7 | `patches/0007-flee-ambush.patch` | **Core-side Flee + encounter flags**, extending the existing flee. It doesn't add a second one: live `src/scenes/battle.js` has a UI-only Flee that always succeeds and is hidden when `params.boss`, and the core had none. New `start_battle_opts(encounter, opts)` with `{ "first": "enemy"\|"party"\|null, "canFlee": bool }` (`can_flee` also accepted; same names as Ashley's `encounters.js` `first` and `zones.json` `fixed.<id>.canFlee`). `first` reorders **round 1 only** (that side acts first, each side still by speed); round 2+ is pure speed. `flee(actor)` → `{kind:"flee", ok, fled, chance, roll}` or `{ok:false, reason}` (`cannot_flee`, `over`, `not_your_turn`, `not_party_actor`, `bad_index`, `combo_in_progress`). Success: outcome `"fled"`, HP and Vermilion Ink saved (reset.on_flee keep), no mon/XP. Failure uses the turn. `can_flee()`, `flee_chance()`, `set_flee_rules(json)` / `set_rules` `flee {}` block. `battle_json` adds `canFlee`, `first`, `fleeChance`. `start_battle(enc)` unchanged (= canFlee true, no ambush). 7 tests (`mod flee_tests`). |
| 8 | `patches/0008-enemy-xp.patch` | `EnemyDef.xp` (`#[serde(default)]` = 0). Jake's rules: at victory every **living** member gets the full encounter XP (sum of enemy `xp`), KO'd members 0; level-up when cumulative XP ≥ `progression.xp_table[lv+1].total` (cap `level_cap`); stats from `members[].stat_table[lv-1]`; current HP rises by the max-HP gained. Reads optional `progression` + `stat_table` from party.json (Jake's drop has them; **live `data/party.json` doesn't**, so XP accumulates but no level-ups until Marc ships Jake's full file). Starting XP = `xp_table` total for the member's `lv`. Exposed: `rewards_json()` and `battle_json().rewards` = `{mon, xp, members:[{id,name,alive,gained,xp,lv_before,lv,leveled_up,next_total,stats}]}`; `party_json` adds `lv` (current), `xp`, `nextXp`. Save gets `xp`/`lv` maps (`serde(default)`, so old saves load); `load_json` restores level stats, clamps lv, and backfills missing hp/ink entries (a partial save previously panicked in `party_json`'s `st.hp[&id]`). 7 tests (`mod xp_tests`). |
| 9 | `patches/0009-balance-jake.patch` | Jake's approved design fixes: **Seal Arts always use the defender's `mdf`** (`seal.stat` only picks the attacker's atk/mat; before, `stat:"atk"` hit `def`); **damage variance 0.95–1.05** (`VAR_MIN`/`VAR_MAX` consts; was 0.94–1.06). `on_ko` integer parsing already landed in 0002, and 0009 tests it. 3 tests (`mod balance_tests`). `0009-balance-jake.standalone.patch` = same change against live alone, for isolated review (it applies without 0007/0008). |

```
for p in 0007-flee-ambush 0008-enemy-xp 0009-balance-jake; do git apply team/dev/rusty/patches/$p.patch; done
cd core && cargo test --release && cd .. && ./build.sh
```
JS hook-up (optional): `core.start_battle_opts(params.enc, JSON.stringify({ first: params.first ?? null, canFlee: !params.boss && params.canFlee !== false }))`;
Flee menu → `core.flee(cur())`, and on `fled:true` → `game.pop({ fled: true })`; after a win, show `JSON.parse(core.rewards_json())`.

## Verification (real runs, 2026-11-15 3:41–3:43 PM CST)
- Fresh copy of live core (sha `bfeabf62…`), baseline `cargo test`: lib 30/30, Richard's `brushstroke_timing` 5/5.
- `git apply --check` + `git apply` in order, `cargo test` after each: **0007** lib 37/37 + Richard 5/5 · **0008** lib 44/44 + 5/5 · **0009** lib **47/47** + 5/5.
- `patch -p1` in order on a second copy: clean, byte-identical. Re-published patches re-verified identical to the tested tree.
- `0009-balance-jake.standalone.patch` alone on live: applies; lib 33/33 + Richard 5/5.
- **Old-behavior dependence:** none of the integrator's 5 lib tests or Richard's 5 depend on the old variance or Seal-vs-def behavior; all pass after 0009 (chained and standalone).
- `cargo test --release`: 47 + 5 pass, no warnings. `cargo check --target wasm32-unknown-unknown --release`: OK. `wasm-pack build --release --target web`: OK, wasm 325 KB, new exports present in the JS glue.
- Node smoke (`node tools/smoke.mjs <pkg>`, live data/): timed-chain win on sumikage_c; **ambush** `first:"enemy"` → first actor is an enemy, battle still won; **boss** `canFlee:false` → `reason:"cannot_flee"`; **flee** fled on attempt 2 (chance 0.88, seeded); Jake's party.json + xp → boss win, +150 XP each (379→529, below L6 at 612).

## Files
- `patches/` 0007–0009 (+ standalone 0009). `API.md` = live API (0.1.0 + landed 0001–0006) plus 0007–0009 additions.
- `tools/` the patch generators (`chain.sh`, `p1..p9.py`, `p6_tests.rs`, `rep.py`) and `smoke.mjs`.
- `scratch/` an abandoned parallel-crate draft. **Not a crate to integrate.**

## Discrepancies / open questions
1. **Live `data/transformation.json` is stale.** It still has 5 / +4 / 4 / 8 and `on_ko:"keep"`; Jake's drop has 4 / +4 / 6 / 10 and `on_ko:0`. The core reads whichever file it's given, so Marc needs to copy Jake's file into `data/`.
2. **Live `data/party.json` has no `progression`/`stat_table`**, so 0008 awards XP but can't level anyone up until Jake's full party.json is integrated. Enemy `xp` isn't in `data/enemies.json` yet either; Jake's suggested values are blotling 12, hollow_lantern 18, smudge_ronin 150 (Karen owns them).
3. **Flee:** `battle.js` currently pops `{fled:true}` without asking the core, so it always succeeds. To use 0007, call `core.flee()`. Formula defaults are my proposal (base 0.5, +0.05 per point of average SPD lead, +0.25 per failed try, clamp 0.25–0.95). Tim/Jake should tune them.
4. **Ashley's zones.json (3:34 PM) matches live `data/enemies.json`** for sumikage_c/sumikage_boss. Her extra `road_*`/`wood_*` encounters aren't in `data/enemies.json` yet; until they're merged, those ids start a battle with no enemies. Her `fixed.sumikage_boss.canFlee:false` maps directly onto 0007.
5. Kept by decision: 30% glance on a first-hit miss (Tim). Richard retargeted his own test to sumikage_c (not touched by me).
6. **Timed chain + early kill:** damage resolves when the chain ends (unchanged from 0001).
