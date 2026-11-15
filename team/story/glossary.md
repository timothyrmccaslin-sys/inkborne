# Inkborne glossary

Generated from glossary.json. Names come from CANON.md (Lisa), SPEC §2, and Ollie's item list (Kekai-approved).

## title

| id | name | status | description |
|---|---|---|---|
| `inkborne` | Inkborne | canon | Title of the game. SPEC v1.1 says "the title is back to Inkborne". |

## place

| id | name | status | description |
|---|---|---|---|
| `shirofuda` | Shirofuda | canon | The world, painted into being by the First Brush; everything in it is ink on living paper. |
| `hanshi` | Hanshi | canon | Border town of paper-walled houses and red lanterns, named for calligraphy paper. World node and POI `town`. |
| `sumikage` | Sumikage Wood | canon | "Ink-shadow wood": bamboo, old pines, mist, and broken seal-stones along the path. World node and POI `forest`. |

## lore

| id | name | status | description |
|---|---|---|---|
| `first_brush` | First Brush | canon | The brush that painted Shirofuda. Each party member carries a fragment of its red ink. |
| `the_blot` | the Blot | canon | A creeping smear soaking through cracked seals, unwriting what it touches into blank paper and ink-beasts. |
| `red_seals` | red seals | canon | Seals of the old shrines that keep the painting true. They are cracking. |

## shop

| id | name | status | description |
|---|---|---|---|
| `kobo_tsuru` | Kōbō Tsuru | canon | General store in Hanshi run by Grandmother Tsuru. Shop id `kobo_tsuru`. |

## npc

| id | name | status | description |
|---|---|---|---|
| `tsuru` | Grandmother Tsuru | canon | Old shopkeeper of Kōbō Tsuru. Keeper id `tsuru`. |
| `lantern_keeper` | Old Hotaru | canon | Hanshi's lamplighter, a stooped, soft-spoken old man who relights the red lanterns every dusk and talks to each flame like a grandchild. First to notice the flames are greying. |

## character

| id | name | status | description |
|---|---|---|---|
| `itsuki` | Itsuki Hane | canon | Wandering Swordsman. Lead, physical. Calm, guarded, no memory before waking in Sumikage Wood with a blank seal on his palm. Gale ink. |
| `benika` | Benika Matsuo | canon | Shrine Archer. Healer and support. Bright, stubborn keeper of Hanshi's shrine. Ember ink. |
| `gonzo` | Gonzō Kuraishi | canon | Retired Temple Monk. Tank and heavy hitter. Gruff, kind, haunted by a seal he failed to protect. Stone ink. |

## inkwing

| id | name | status | description |
|---|---|---|---|
| `gale_crane` | Gale Crane | canon | Itsuki's Inkwing: long white-and-grey crane wings, muted pale jade tint. |
| `ember_kite` | Ember Kite | canon | Benika's Inkwing: wide kite-bird wings smoldering at the tips, muted ochre tint, drifting ash. |
| `stone_owl` | Stone Owl | canon | Gonzō's Inkwing: heavy owl wings like layered slate, cracks glowing faintly red. |

## stroke

| id | name | status | description |
|---|---|---|---|
| `falling_pine` | Falling Pine | canon | Itsuki's signature Stroke chain. |
| `three_prayer_slips` | Three Prayer Slips | canon | Benika's signature Stroke chain. |
| `temple_bell` | Temple Bell | canon | Gonzō's signature Stroke chain. |
| `wet_edge` | Wet Edge | canon | Itsuki's second Stroke. |
| `lantern_volley` | Lantern Volley | canon | Benika's second Stroke. |
| `mountain_gong` | Mountain Gong | canon | Gonzō's second Stroke. |

## seal_art

| id | name | status | description |
|---|---|---|---|
| `crane_gale_script` | Gale Crane Script | canon | Itsuki's Seal Art while Unfurled. |
| `ember_kite_litany` | Ember Kite Litany | canon | Benika's Seal Art while Unfurled. |
| `stone_owl_verse` | Stone Owl Verse | canon | Gonzō's Seal Art while Unfurled. |

## enemy

| id | name | status | description |
|---|---|---|---|
| `blotling` | Blotling | canon | A small puddle of living ink with one blinking eye. Splits when struck hard. |
| `hollow_lantern` | Hollow Lantern | canon | A torn paper lantern on ink smoke, its red flame going grey. Casts a dimming curse that lowers accuracy. |
| `smudge_ronin` | Smudge Ronin | canon | Demo mini-boss. A samurai half-unwritten by the Blot, with a dripping blade and only a wet brushstroke for a face. |

## mechanic

| id | name | status | description |
|---|---|---|---|
| `brushstroke` | Brushstroke | canon | Timed multi-hit combo: press as the ring closes. Each press is a Stroke; named chains are also Strokes. |
| `stroke` | Stroke | canon | One press in a Brushstroke, or a character's named chain. |
| `clean_line` | Clean Line | canon | Perfect press in a tight window: x1.25 hit damage and extra ink. |
| `inkwing` | Inkwing | canon | Winged elemental form. Costs a full gauge, lasts 3 of that character's turns. |
| `unfurl` | Unfurl | canon | The act and battle command that transforms a character into their Inkwing. |
| `seal_arts` | Seal Arts | canon | Timed magic while Unfurled: press as the brush passes each red seal. |
| `still_water` | Still Water | canon | Guard: halves damage taken and heals 10% HP. |
| `six_inks` | Six Inks | canon | The elements: Ember/Tide, Gale/Stone, Dawn/Dusk. Opposites x2, same x0.5. |
| `mon` | mon | canon | Currency. |
| `transform_gauge` | Vermilion Ink | canon | Per-character 0-100 gauge filled by successful hits; a full gauge lets you Unfurl. UI key: battle.gauge.label. |

## element

| id | name | status | description |
|---|---|---|---|
| `ember` | Ember | canon | One of the Six Inks. |
| `tide` | Tide | canon | One of the Six Inks. |
| `gale` | Gale | canon | One of the Six Inks. |
| `stone` | Stone | canon | One of the Six Inks. |
| `dawn` | Dawn | canon | One of the Six Inks. |
| `dusk` | Dusk | canon | One of the Six Inks. |

## item

| id | name | status | description |
|---|---|---|---|
| `rice_cake` | Rice Cake | canon | Sweet and filling. Restores a little HP to one ally. |
| `plum_tonic` | Plum Tonic | canon | Sour enough to wake the dead, nearly. Restores a lot of HP to one ally. |
| `shared_tea` | Pot of Pine Tea | canon | One pot, three cups. Restores some HP to the whole party. |
| `festival_bento` | Festival Bento | canon | Packed for a feast that never came. Restores a lot of HP to the whole party. |
| `inkstone_chip` | Inkstone Chip | canon | Grind it, wet it, and the brush drinks. Restores a little ink. |
| `vermilion_pot` | Pot of Fresh Ink | canon | Rich and dark, still smelling of pine soot. Restores a lot of ink. |
| `paper_cracker` | Paper Firecracker | canon | Festival leftovers. Bangs loudly enough to scatter a Blotling. |
| `thunder_jar` | Thunder Jar | canon | Grandmother Tsuru won't say what's in it. Hits all enemies. |
