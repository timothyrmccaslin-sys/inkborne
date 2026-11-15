# Economy note (demo)
Currency is **mon**. Sell price = floor(price/2) (SPEC 7) for sellable stock. Starter gear (`starting_for`) and any equipment with `in_shop` false is unsellable (`sellable: false`, `sell_price: 0`), because the demo shop cannot replace it.

The gauge is **Vermilion Ink** (key `ink`). "Vermilion Gauge" is retired. kind `ink` items add `power` to the target's `ink`, capped at 100. If the target is already in Inkwing form, the use is refused and the item is not consumed (confirmed by Tim).

## Income
Per enemy: blotling 12, hollow_lantern 20, smudge_ronin 150 (boss). Typical Sumikage fights (Ashley's encounters): road_blotling 12, blotling pair 24, blotling+lantern 32, lantern pair 40, boss 150. A random fight averages about 25-30 mon; the demo's 2 fixed fights plus about 1 random is roughly 60-100 mon before the boss, 150 from the boss.

## Consumable prices (Ollie's list)
| Item | Price | Fights to afford (about 28 mon) |
|---|---|---|
| Rice Cake (heal 50) | 15 | 0.5 |
| Plum Tonic (heal 200) | 60 | 2 |
| Pot of Pine Tea (party 80) | 120 | 4 |
| Festival Bento (party 250) | 280 | 10 |
| Inkstone Chip (+25 Vermilion Ink) | 40 | 1.5 |
| Pot of Fresh Ink (+50 Vermilion Ink) | 110 | 4 |
| Paper Firecracker (60 Ember) | 50 | 2 |
| Thunder Jar (150 Gale) | 150 | 5 |

## Shop equipment (Kōbō Tsuru)
| Item | Price | Sell | Fights to afford (about 28 mon) |
|---|---|---|---|
| Layered Washi Vest (armor T1, +3 def) | 40 | 20 | 1.5 |
| Folded Paper Charm (ink accessory, +1 ink per Stroke hit) | 60 | 30 | 2 |

The eight consumables cost 825 mon together. Adding the vest and the charm brings the full shop to 925 mon (about 33 fights), more than a demo run earns, so players must choose. Rice Cake, Plum Tonic, the Washi Vest and the Paper Charm are affordable early; the party and big items are aspirational.
Value check: healing runs about 3.3 HP/mon (cake), 3.3 (tonic), 2 HP/mon per member for Pine Tea (3 members, 80 each: 2/mon), Bento 2.7/mon; singles are cheaper per HP so spam-healing beats party healing early, which is intended.
Ink items: 1.6 mon per ink point (chip) vs 2.2 (pot); the chip is more efficient, the pot saves a turn. The Paper Charm is a lasting alternative: it does not spend a turn or a consumable, and it takes a good chain's fill from 18 to 21 (6 turns down to 5).

## Equipment not in the shop (priced for value only, unsellable)
Proposed budget, unchanged from the first pass and still in line with demo income: tier 1 weapon 40, accessory 60 (starters); tier 2 weapon 180, armor 180, accessory 150. Tier 2 is out of reach of shop income in the demo unless it is found, dropped, or sold after the boss. Starter weapons and Gonzō's Prayer-Bead Mala are unsellable so a unique piece cannot be dumped with no replacement.

Mods in `data/equipment_numbers.json` were **approved by Jake** (2026-11-15) and are a numbers file for the integrator to merge. Applying those bonuses in battle and in the save is a later patch with Jared.

## Balance check (flat mods, Jake's formula)
Each atk point is about 2 raw damage, each def point blocks about 1. A starter +2 atk is a small bump on Itsuki's L1-L6 atk of 22-35. The best demo weapon is +8, still well below Inkwing's roughly +50% atk (about +12 to +18 atk from the form alone at those levels). Tier-1 +3 def takes a few points off a Blotling hit (atk 22); tier-2 +6 is a noticeable but not fight-winning layer. Those sizes are why the older placeholder mods (+4 / +9 weapons, +4 / +9 armor, +3 spd) were retired with the null-id file.
