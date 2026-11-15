# Inkborne demo: storyboard layout notes
Helen (storyboard), v2, Nov 15, 2026 (revised after Kekai's review). These notes go with the boards in this folder. Every rect is in **logical px at 1280×720** (SPEC v1.1 §1), with % of the screen alongside. The single source of truth is `src/zones.py`: the boards and the tables below are both generated from it, so if a number changes, change it there and re-run.

Names follow SPEC v1.1 §2 and `team/story/CANON.md` (v2). The game title is **Inkborne** (SPEC v1.1 and CANON v2). The gauge is **Vermilion Ink**, now final in both SPEC v1.1 and CANON (confirmed by Marc).

## 0. Global rules
- **Reserved touch rects.** These are drawn on every board, and no other UI element, prompt, chevron, or talk target may sit in them. SPEC §4 only names the corners (stick lower left, A/B lower right, ☰ top right) and gives no rects. **Status:** Kekai approved these rects as the team's proposal and has sent them to Marc to adopt in `src/input.js`. Keep them as they are until Marc confirms or changes them.

| Code | Element | px (x, y, w×h) | % of 1280×720 (x, y, w×h) | Notes |
|---|---|---|---|---|
| T1 | touch stick | 64, 496, 192×188 | 5.0%, 68.9%, 15.0%×26.1% | virtual stick, lower left. PROPOSED rect: SPEC s4 names the corner only. Reserved on every screen. |
| T2 | touch A / B | 1024, 496, 192×188 | 80.0%, 68.9%, 15.0%×26.1% | A = confirm / timed press, B = cancel / Still Water. PROPOSED rect (SPEC s4: lower right). Reserved on every screen. |
| M | menu ☰ | 1152, 36, 64×64 | 90.0%, 5.0%, 5.0%×8.9% | ☰ menu button, top right. PROPOSED rect (SPEC s4: top right). Reserved on every screen. |

  - Inside T2: A is a 68 px circle centred at (1154, 566), and B is a 56 px circle at (1082, 624). Both clear the 44 pt minimum touch target (QA test plan).
  - Touch controls hide after gamepad input (SPEC §4), but the layout still keeps the rects clear so nothing jumps around.
- **Safe margins.** A 64 px left and right title-safe margin (5%) and 36 px top and bottom (5%), *on top of* `env(safe-area-inset-*)`. All HUD lives in 64..1216 × 36..684.
- **The bottom band (y 496–684)** between T1 and T2 runs from **x 272 to 1008** (16 px gutters). Every bottom bar uses exactly this span: the world node prompt, the dialogue text box, the shop keeper line, and the battle party HUD.
- **Red rule.** Vermilion `#b3261e` is used only for meaning: seals, lanterns, blood, the Vermilion Ink gauge, focus underlines, Clean Line, and the advance chevron. The muted Gale tint `#5f8a6a` appears only on the Inkwing (the wings, the HUD chip, and the turns counter).
- **Detail tiers.** World: bold folding-screen strokes. POI: mid detail with ambient motion. Action (battle, dialogue, shop): full detail. The boards follow this, and so should the paint.

## 1. World map (`world`): board 01
| Code | Element | px (x, y, w×h) | % of 1280×720 (x, y, w×h) | Notes |
|---|---|---|---|---|
| W1 | location plate | 64, 36, 400×64 | 5.0%, 5.0%, 31.2%×8.9% | node name; red seal dot when the node opens a POI |
| W2 | node prompt | 400, 600, 480×84 | 31.2%, 83.3%, 37.5%×11.7% | 'Enter Sumikage Wood  [A]'; shows while the token rests on a node |
| W3 | party token | floats, 48×64 | floats, 3.8%×8.9% | floats 24px above node centre; follows path bezier ~260 px/s |

- **Node names.** The boards use canon names. `data/world.json` still has old names, mapped as: `mistcedar` "Mistcedar Path" → **Sumikage Wood** (canon id `sumikage`, POI `forest`) and `hollowbell` "Hollowbell" → **Hanshi** (canon id `hanshi`, POI `town`). The start node (`trailhead`, "Mender's Hut") and the locked node (`palegate`, "The Pale Gate") are unnamed on the boards until Lisa supplies canon names.
- **Framing.** A six-leaf folding screen with fold lines as vertical seams. The ridges sit in the top third, a mist band at y≈300–380, and the river sweep along the bottom. Nodes come from `data/world.json` (230,470 / 560,360 / 930,450 / 1110,210). They all clear T1/T2/☰. The lowest node (230,470) is 26 px above T1: keep it there.
- **Minimal HUD.** Only W1 (location plate), W2 (node prompt, on arrival) and ☰. No party cards on the map.
- **Ambient motion.** The mist band drifts 6 px/s. The node's red element pulses at 0.8 Hz while hovered, and the token bobs 2 px at 1 Hz.

## 2. POIs (`poi`: forest = Sumikage Wood, town = Hanshi): boards 02 and 03
| Code | Element | px (x, y, w×h) | % of 1280×720 (x, y, w×h) | Notes |
|---|---|---|---|---|
| P1 | area toast | 64, 36, 400×56 | 5.0%, 5.0%, 31.2%×7.8% | area name: fade in 0.4s, hold 2.5s, fade 0.6s |
| P2 | interact prompt | floats, 220×44 | floats, 17.2%×6.1% | centred on target x, bottom edge 96px above target feet; clamp outside T1/T2/M |
| P3 | exit marker | floats, 64×64 | floats, 5.0%×8.9% | ink chevron at the screen edge when an exit is on screen; clamp outside T1/T2 |

- **Parallax (Sumikage Wood).** `poi-forest-far` at 0.2× (bamboo and mist), `-mid` at 0.6× (old pines, the path, and a broken seal-stone with a faded red seal), and `-near` at 1.15× (trunks and grass framing the edges, drawn over the walker). These are suggested scroll factors.
- **Walkable band.** Sumikage is y≈520–630 and Hanshi's street is y≈560–640. The camera keeps the walker in the centre third, so the feet only pass behind the translucent T1/T2 at the area ends. NPCs, talk targets, prompts and exits never sit in T1/T2.
- **Exits.** P3 chevrons sit at mid-height on the screen edges (y≈330), never in the lower corners. Sumikage: west goes to the world map and east to Hanshi. Hanshi: west goes to Sumikage Wood or the map, and the shrine stair (right) is the dialogue trigger. The climb prompt stops below y=120 so it stays clear of ☰.
- **Hanshi set dressing.** Paper-walled houses, the Kōbō Tsuru noren with a red shop seal, a lantern string, and the stair up to the red torii of Benika's shrine. NPCs: Grandmother Tsuru at her noren, **Old Hotaru** (`lantern_keeper`, CANON v2: Hanshi's lamplighter, stooped, with a lantern pole) relighting a greying lantern, and a running child.
- **Ambient motion.**
  - Sumikage: 6 falling leaves (30–50 px/s, swaying), the mist drifting 8 px/s, pine boughs swaying ±2° at 0.3 Hz, and the seal-stone flickering at 0.2 Hz.
  - Hanshi: lanterns swaying ±3° at 0.5 Hz with flame flicker, a 4 s glow pulse in the paper windows, and the child's 3 s run loop.
  - Audio hooks: `amb-forest` and `amb-town`, `step-dirt-*` and `step-wood-*`.

## 3. Dialogue (`action`, mode `dialogue`): board 04
| Code | Element | px (x, y, w×h) | % of 1280×720 (x, y, w×h) | Notes |
|---|---|---|---|---|
| D1 | portrait L | 64, 108, 300×376 | 5.0%, 15.0%, 23.4%×52.2% | 512x640 art at ~0.59; bottom edge y=484 stays above T1 |
| D2 | portrait R | 916, 108, 300×376 | 71.6%, 15.0%, 23.4%×52.2% | mirror of D1; bottom y=484 stays above T2 |
| D3 | text box | 272, 500, 736×184 | 21.2%, 69.4%, 57.5%×25.6% | between T1 and T2. 3 lines max, 24px serif, ~44 chars/line, 28px padding |
| D4 | name plate L | 288, 472, 220×40 | 22.5%, 65.6%, 17.2%×5.6% | overlaps D3 top edge; red seal tick on the active speaker |
| D5 | name plate R | 772, 472, 220×40 | 60.3%, 65.6%, 17.2%×5.6% | mirror of D4 |
| D6 | advance mark | 972, 648, 24×24 | 75.9%, 90.0%, 1.9%×3.3% | red brush tick inside D3, bobs 4px at 1.2Hz when the line is fully typed |
| D7 | choices | 424, 248, 432×200 | 33.1%, 34.4%, 33.8%×27.8% | 2-3 rows x 56px, 16px gap, between portraits; focus = red underline |
| D8 | log / auto | 944, 36, 192×44 | 73.8%, 5.0%, 15.0%×6.1% | text log + auto toggle, left of M |

- **Portraits.** 512×640 art drawn at about 0.59 (300×376). The left speaker faces right and the right speaker faces left. The listener is knocked back to 45% ink. The active speaker slides in 12 px with a 150 ms ink-in. Portrait bottoms stop at y=484, above T1 and T2.
- **Text.** 3 lines max, a 24 px serif, about 44 characters per line, and 28 px padding. It types at 40 characters/s with a `text` blip every 2nd character. Tap A (or anywhere in D3) once to finish the line and again to advance.
- **Choices (D7).** 2–3 rows that float between the portraits. Focus is a red brush underline plus a small seal. The board lines are placeholders, because Ollie owns the dialogue text.
- **Background.** A blurred, knocked-back shrine plate (60% paper over it, 6 px blur). Action tier.

## 4. Shop (`action`, mode `shop`, Kōbō Tsuru): board 05
| Code | Element | px (x, y, w×h) | % of 1280×720 (x, y, w×h) | Notes |
|---|---|---|---|---|
| S1 | Buy / Sell tabs | 64, 36, 320×56 | 5.0%, 5.0%, 25.0%×7.8% | active tab = red brush underline |
| S2 | shop title | 400, 36, 400×56 | 31.2%, 5.0%, 31.2%×7.8% | 'Kōbō Tsuru' |
| S3 | mon counter | 936, 36, 200×56 | 73.1%, 5.0%, 15.6%×7.8% | coin icon + amount; counts down 20/s on purchase |
| S4 | keeper portrait | 64, 112, 248×310 | 5.0%, 15.6%, 19.4%×43.1% | Grandmother Tsuru, 512x640 at ~0.48 |
| S5 | keeper name | 64, 430, 248×40 | 5.0%, 59.7%, 19.4%×5.6% | name plate under portrait |
| S6 | item list | 336, 112, 448×500 | 26.2%, 15.6%, 35.0%×69.4% | header 20 + 8 rows x 60: icon 48, name, owned, price right |
| S7 | description | 808, 112, 408×224 | 63.1%, 15.6%, 31.9%×31.1% | 128px icon, name, 2-3 line desc |
| S8 | party compare | 808, 352, 408×136 | 63.1%, 48.9%, 31.9%×18.9% | 3 rows x 40: chip, name, now -> after (HP / Ink) |
| S9 | keeper line | 272, 628, 736×56 | 21.2%, 87.2%, 57.5%×7.8% | one-line barks (Ollie); doubles as qty stepper on confirm |

- **Item list (S6).** A 20 px header, then 8 rows × 60 px with a 48 px icon (from `icon-<itemId>` at 128 px), name, owned count, and price right-aligned. The Sell tab filters to owned items at `floor(price/2)` (SPEC §7).
- **Compare (S8).** SPEC items are consumables (heal, healall, ink, bomb) and there is no equipment, so S8 is a **party compare** (approved by Kekai): HP or Ink now → after for each member, with a red ▲ when a member gains. If gear arrives later, S8 becomes a stat-delta table in the same rect.
- **Buy flow.** On A, the S9 bar turns into the quantity stepper. On confirm the `coin` SFX plays, the mon counter ticks down 20 per second, and Tsuru's portrait swaps to `smile` with a thank-you bark.

## 5. Battle (`action`, mode `battle`): boards 06 (boss) and 06b (standard)
The boards follow the encounters in `data/enemies.json`:
- **06, the boss fight and the Unfurl showcase:** `sumikage_boss` is the **Smudge Ronin solo** (620 HP, Stone, 150 mon). He's drawn at 260 px tall (normal foes are 240) at the Ronin's anchor.
- **06b, the standard fight with no Unfurl:** `sumikage_c` is **Blotling, Hollow Lantern, Blotling** (44 mon total).

Turn order follows `spd` in the data. In the boss fight it's Benika 20, Itsuki 17, Ronin 13, Gonzō 10. In the standard fight it's Benika, Itsuki, Lantern 15, Blotling 12, Blotling 12, Gonzō.
| Code | Element | px (x, y, w×h) | % of 1280×720 (x, y, w×h) | Notes |
|---|---|---|---|---|
| B1 | turn order | 64, 36, 520×48 | 5.0%, 5.0%, 40.6%×6.7% | chips left->right; current actor ringed red |
| B2 | target plate | 600, 36, 400×48 | 46.9%, 5.0%, 31.2%×6.7% | enemy name + HP stroke while targeting |
| B3 | banner | 340, 104, 600×56 | 26.6%, 14.4%, 46.9%×7.8% | action names, 'Clean Line', 'Itsuki Unfurls!'; ink wipe in 180ms |
| B4 | party HUD | 272, 588, 736×96 | 21.2%, 81.7%, 57.5%×13.3% | 3 cards 240x96, gap 8: chip 56, name, HP stroke, Vermilion Ink stroke |
| B5 | command menu | 64, 232, 232×248 | 5.0%, 32.2%, 18.1%×34.4% | title row + 5 rows x 44: Brushstroke, Unfurl, Still Water, Items, Flee |
| B6 | press ring | 904, 234, 192×192 | 70.6%, 32.5%, 15.0%×26.7% | floats on the target hit point (shown on Smudge Ronin) |
| B7 | stroke pips | 904, 436, 192×36 | 70.6%, 60.6%, 15.0%×5.0% | one pip per Stroke; red = Clean Line, grey = good, cracked = miss |
| B8 | seal stamp | 544, 232, 192×192 | 42.5%, 32.2%, 15.0%×26.7% | perfect-chain finisher, near centre |
| B9 | results panel | 340, 176, 600×300 | 26.6%, 24.4%, 46.9%×41.7% | victory: mon, ink kept, drops; party lines up below it |

- **Stage (feet anchors, logical px).** Benika (340,430), Itsuki (470,495), Gonzō (615,565) facing right.
  - Boss: Smudge Ronin at (1010,440), facing left.
  - Standard: Hollow Lantern (860,300), Blotling A (1000,470), Blotling B (1150,455), facing left. Party feet stay above the HUD (y<588), and enemy hit points stay above y=470 so the ring (B6) and pips (B7) never reach T2.
- **The press ring (B6).** A 48 px target circle at the hit point with a red inner line marking the Clean Line. The outer ring closes from r=96 to r=48 over `gap_ms`. Judgement comes from the core (`windows_json`): **Clean ±70 ms, Good ±150 ms**. Stroke pips (B7) sit 130 px under the hit point: a red pip means Clean, grey means Good, cracked means a miss.

### Boss battle beat list (board 06, Smudge Ronin), with suggested timing
The ink values are illustrative. `party.json` starts Itsuki at 85, so in play he will usually arrive at the boss nearly full after the standard fight.
| # | Beat | Timing | Notes |
|---|---|---|---|
| 1 | Boss intro: "Smudge Ronin" | 0.0–2.4 s | An ink wipe in. A wet smear spreads and the faceless Ronin steps out of it, his blade dripping. The name banner holds 1.2 s. |
| 2 | Itsuki's command menu | player | Benika acts first (spd). Itsuki's menu: Brushstroke · Unfurl (greyed until 100) · Still Water · Items · Flee. Brushstroke opens his Strokes (Falling Pine 3, Wet Edge 4), then targeting shows a red chevron and the B2 plate. |
| 3 | Brushstroke Chain: ring closing, Strokes, Clean Line | dash 0.25 s, then 700 / 520 / 460 ms rings | Stroke 1 is Good. Stroke 2 is a Clean Line: a red ring flash, the "Clean Line" banner (red), ×1.25 damage, +4 ink, and `clean` SFX. |
| 4 | ALT: a miss | +0.3 s | Outside ±150 ms: the ring cracks grey, the pip cracks, `miss` plays, and the chain ends with no finisher. Itsuki skids back. |
| 5 | Seal stamp (fully Clean chain) | 120 ms slam + 0.6 s hold | A big red Seal at B8 (scale 1.6→1.0), a 2 px shake, `seal` + `combo-finish`, the Form name in the banner, and the total damage. Ink 58→93. |
| 6 | Enemy turn + Vermilion Ink filling | 1.2 s per enemy action | The Ronin rushes in (leaving a drip trail) and lands Dripping Cut on Itsuki (52), giving +7 ink and reaching 100. Gonzō guards with Still Water. The INK stroke pulses at 25/50/75/100. At 100 it drips and the card gets a red halo. |
| 7 | Unfurl beat 1: trigger | 0.0–0.6 s | See the beat sheet below. |
| 8 | Unfurl beat 2: ink cocoon | 0.6–1.4 s | |
| 9 | Unfurl beat 3: wings unfurl | 1.4–2.0 s | |
| 10 | Reveal: Gale Crane Inkwing + new menu | 2.0–3.2 s | |
| 11 | Inkwing attack: Seal Art "Gale Crane Script" | about 2.5 s | A brush tip runs a path past 4 red seals. Each press as it crosses stamps that seal solid, and missed seals stay faint. It ends in a jade-tinted gale slash through the Ronin. Gale vs Stone is ×2. |
| 12 | Victory / results | until A | The Ronin washes away to blank paper and the party lines up. B9 shows +150 mon and the Vermilion Ink kept (it persists). A ink-wipes back to the POI. |

Board 06 also carries a 13th panel, the zone diagram. That's a key, not a beat.

### Standard battle beat list (board 06b: Blotling, Hollow Lantern, Blotling, no Unfurl)
| # | Beat | Timing | Notes |
|---|---|---|---|
| 1 | Intro + Benika's turn | 0.0–1.6 s, then player | The enemies ink in 0.4 s apart, with no name banner. Benika opens (spd 20) and targets the Hollow Lantern. Unfurl stays greyed because nobody is at 100. |
| 2 | Brushstroke Chain: Three Prayer Slips | rings at 760 / 560 / 520 ms | Benika fires from where she stands (no dash). A fully Clean chain ends with the red Seal at B8, and her ink goes 30→65. **Layout rule:** the Lantern's hit point (860,190) puts B6 under the B3 banner, so the banner waits until the ring clears. |
| 3 | Enemy turn | 1.2 s per action | The Lantern's Dimming Curse is grey smoke on Benika (accuracy down). A Blotling's Ink Splash hits Gonzō, who is in Still Water (half damage, +6 ink). Ink rises but stays below 100. |
| 4 | Finish + results | until A | Gonzō's Temple Bell (820 / 640 ms) hits the last Blotling hard. It splits into two small blots that wash out (CANON), and B9 shows +44 mon. The ink carries over, which sets up the boss Unfurl. |

### Unfurl beat sheet: Itsuki, Gale Crane Inkwing
| Beat | t | Picture | Camera / FX | Audio | UI |
|---|---|---|---|---|---|
| Trigger | 0.0–0.6 s | Unfurl is lit red in the menu, confirmed. Itsuki's wrapped palm (the blank seal) flares red, and three red ink arcs spiral out. | The background knocks back to paper and the enemies freeze. | `inkwing` starts | The menu closes. The HUD card halo goes from red to white. |
| Ink cocoon | 0.6–1.4 s | Wet ink wash and dry-brush wraps close him into a tall cocoon, with one red vein showing through and ink droplets orbiting. | Push in 8%. | | The banner reads "Itsuki Unfurls!", and Vermilion Ink drains 100→0 over 0.5 s. |
| Wings unfurl | 1.4–2.0 s | The cocoon splits down the red vein. Long crane wings sweep out (open 0→0.6 in 0.3 s with overshoot), and the shards become flying droplets. The muted pale jade tint appears for the first time, only on the wings. | A 2 px shake on the split. | a whoosh layer | |
| Reveal | 2.0–3.2 s | The full span (white and grey crane wings with feathered ink edges and a pale jade wash). He hovers 30 px with a slow 0.5 Hz flap, his hair and red cord streaming. | Pull back to neutral. | | The banner reads "Gale Crane Inkwing". The menu becomes Seal Art · Stroke · Still Water · Item, and the HUD shows a jade chip plus "3 turns". "Tailwind: acts first" toasts once. |
| Hold / return | +0.4 s | The idle loop `bt-itsuki-inkwing-idle`. | | | Control returns. Revert (at the end of the 3rd own turn, on KO, or when the battle ends) is the cocoon in reverse at 2× speed. |

Composition constraint: the wingspan (about 2.4 × body height) must stay right of B5 (x>296) and above the HUD (y<588). The boards hover him at x≈570 for the reveal to keep the left wingtip clear of the menu.

## 6. Takeaways by discipline
- **Environment.** Paint the plates at 2560×1440, keeping the important silhouettes in the centre 1152×648 safe area. Keep the bottom corners (T1/T2) and the top right (☰) low-contrast, with no focal props there. Red only on seals, lanterns, and the torii. Battle uses a knocked-back Sumikage plate (`battle-forest`), with the ground line at about y=470–500. Both the boss and standard fights use the same plate.
- **Character.** Silhouettes come from CANON:
  - Itsuki: tall, a torn grey sleeve, long hair tied low with a red cord, and a wrapped left palm.
  - Benika: short and sturdy, with a vermilion hakama (her main red), a paper charm, and a tall bow with prayer slips.
  - Gonzō: huge, with plum-sized beads, a beard, and an iron-banded staff.
  - Blotling: a puddle with one eye. Hollow Lantern: torn paper with a greying red flame. Smudge Ronin: a faceless wet stroke with a half-unwritten outline (boss scale). Old Hotaru: stooped, with a lantern pole.
  - Battle sprites are 256×256 with the anchor at the feet. Portraits are 512×640, cropped so the head sits at about 40% height.
- **UI.** Use the rects in the tables, all derived from `src/zones.py`. Every bottom bar uses x 272–1008. Focus is a red brush underline, and the turn and target chevrons are red. Nothing goes inside T1/T2/M.
- **FX.** The Clean Line flash and Seal stamp are vermilion. A miss fades to grey. The Lantern's curse is grey smoke. The Unfurl uses red ink arcs, then an ink cocoon, then droplets. The muted Gale tint appears only on the Inkwing. Seal Arts are red seals on a brush path.
- **Animation.** The ring close times are the `gap_ms` values from `party.json` (Falling Pine 700/520/460). The Seal stamp lands in 120 ms. The Unfurl runs about 3.2 s in total and should be skippable after the first view (open question). Ambient loops: the forest leaves and mist, and the town lanterns at 0.5 Hz. The dialogue portrait ink-in is 150 ms.

## 7. Resolved after Kekai's review (Nov 15)
- **Title:** Inkborne (SPEC v1.1). Every board, the contact sheet and these notes have been relabelled.
- **Touch rects:** approved as the proposal and sent to Marc for `input.js` (see §0).
- **World node names:** Mistcedar Path is Sumikage Wood and Hollowbell is Hanshi (see §1). Lisa is naming the start and locked nodes.
- **Shop compare:** the HP/Ink party compare is approved.
- **Encounters:** board 06 is the `sumikage_boss` Smudge Ronin solo with the Unfurl showcase. Board 06b is `sumikage_c` with no Unfurl.
- **Gauge name:** Vermilion Ink is final.

## 8. Open questions
1. The Hollow Lantern's high hit point collides with the B3 banner. These notes delay the banner until the ring clears. Is that OK with UI (Jamie), or should the Lantern hover lower (feet at about y=360)?
