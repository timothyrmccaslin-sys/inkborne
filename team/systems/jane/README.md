# Jane: items, equipment, shop economy (Inkborne demo)

Drop folder only (SPEC section 9). Nothing here is loaded at runtime. Marc the integrator copies or merges it into the live `data/` files. All ids, names and descriptions come from Ollie's `team/story/items.json` and `shops.json`. Nothing here is invented.

## Files
- `data/items.json`: 8 consumables (SPEC 7 schema), Ollie's ids. Prices and powers are mine.
- `data/shops.json`: `kobo_tsuru` stock — Ollie's 8 consumables plus the two shop-sold equipment ids (`washi_vest`, `paper_charm`).
- `data/enemies.mon.json`: `mon` per enemy (blotling 12, hollow_lantern 20, smudge_ronin 150) for Jake's enemies.json.
- `data/equipment_numbers.json`: proposed flat mods, prices and sell rules for the 11 live equipment ids. **Approved by Jake (2026-11-15).**
- `proposed/retired/equipment.json`: the old null-id 3-slots-times-2-tiers budget. Retired; do not merge it.
- `tools/validate.py`: run `python3 tools/validate.py`. Checks schema, Ollie ids, shop stock, elements, ink powers (25 and 50), Jake's gauge field, and that the numbers-file ids match live `data/items.json` exactly.
- `ECONOMY.md`: gold in, gold out, and the equipment price pass.

## Merge path (integrator)
1. Consumables and shop stock can be copied from `data/items.json` and `data/shops.json` into live `data/items.json` (the `items` array) and `data/shops.json`.
2. Equipment numbers are a merge, not a replace. For each entry in `data/equipment_numbers.json`, find the live `data/items.json` `equipment` object with the same `id` and write `mods`, `element`, `price`, `sellable`, `sell_price`, and (when present) `resist` or `ink` onto it. Leave `name`, `desc`, `slot`, `tier`, `equippable_by`, `starting_for` and `in_shop` as Ollie and the integrator set them.
3. Do not merge `proposed/retired/equipment.json`.
4. **Equipment bonuses themselves go in a later patch with Jared**, who owns the save fields (item id to count, gold/`mon` as an int, and equipped ids per member per slot, null when empty). Until that patch, these numbers are a merge source only; the core should not assume equipment mods are already applied.

## Ink items and the gauge
The gauge is **Vermilion Ink** (key `ink`, 0-100). The name "Vermilion Gauge" is retired.

kind `ink` items add `power` to the target's `ink`, capped at 100: `inkstone_chip` = 25, `fresh_ink_pot` = 50. If the target is already in Inkwing form, the use is **refused and the item is not consumed** (confirmed by Tim).

## Equipment (11 ids, 3 slots)
There are 3 slots (weapon, armor, accessory). The earlier "6" was 3 slots times 2 tiers. Mods are **flat bonuses only**, sized from Jake's `party.json` stat_table and a demo that runs about L1 to L6. Damage is `raw = max(a*0.25, 2a - d)`: each atk point is worth about 2 damage, each def point blocks about 1. Weapon atk stays at **+8 or below** so Inkwing's roughly +50% atk is still the big spike.

L1 to L6 ranges (Jake):
- Itsuki: atk 22-35, def 12-19, mat 10-15, mdf 10-16, spd 14-18
- Benika: atk 15-24, mat 22-36, def 10-16, mdf 16-26, spd 16-21
- Gonzō: atk 20-32, def 18-29, mat 8-12, mdf 14-22, spd 8-11

Tier rationale (Jake's guidance, mapped onto the 11 ids):
- **Weapons, tier 1 (starters):** +2 atk, top of Jake's +0 to +2 starter band. Benika's Prayer-Slip Bow also gives +2 mat (and +1 atk), because her Seal Art scales off mat.
- **Weapons, tier 2 (best demo):** +8 atk, Jake's cap. Benika's Crane-Feather Bow gives +4 atk (the mid-tier budget, on her weaker physical side) and +8 mat. There is no mid-tier weapon id in the 11, so a dedicated +4 mid weapon is unused.
- **Armor, tier 1:** +3 def. `washi_vest` is sold at Kōbō Tsuru.
- **Armor, tier 2:** +6 def, plus +3 mdf on `lacquer_haori` (the one optional mdf piece). Both armors are all-party, so Gonzō's +8 def option is unused.
- **Accessories, one of each type Jake asked for:**
  - (a) stat: `prayer_mala` (Gonzō starter) +4 mdf. spd is never above +2; this piece does not use spd.
  - (b) elemental resist: `lantern_bell` makes dusk damage ×0.75, applied after the `elements.json` chart multiplier. ("Keeps the grey at bay." Blotlings are dusk.)
  - (c) one ink accessory: `paper_charm`, +1 ink per Stroke hit landed, no flat ink at the start of battle. That takes a good chain's fill from 18 to 21, so the gauge fills in 5 turns instead of 6. Sold at the shop.

Weapon `element` is left null so normal-form Strokes stay neutral (elements matter most in Inkwing), pending Jake's sign-off.

Starter gear (`starting_for` set) and any piece with `in_shop` false is unsellable. Shop stock sells at `floor(price/2)` (SPEC 7).

## Open questions
- Jake signed off on all five mapping questions on 2026-11-15 (accessory split, Benika's bows, no mid-tier weapon, no Gonzō +8 armor, element-less weapons per DESIGN.md).
- Jared: equipment bonuses go in a later patch with you. Please confirm save keys: item id to count, gold (`mon`, int), and equipped ids per member per slot (null when empty). Unknown ids should be dropped on load.
