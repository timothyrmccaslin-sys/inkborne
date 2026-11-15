# Storyboards: Inkborne demo (Helen)
These are rough sumi-e layout thumbnails of the demo flow. They're drawn in code (Python/PIL), so every UI rect is exact at the logical **1280×720** resolution. Each panel is one 1280×720 frame.

| File | What |
|---|---|
| `00_contact_sheet.png` | All six boards on one page |
| `01_world_map.png` | Shirofuda folding-screen map: composition, the Sumikage Wood and Hanshi nodes, the party token, a minimal HUD, and the zones |
| `02_sumikage_wood.png` | Forest POI: parallax layers, walking, ambient motion, triggers and exits, and the zones |
| `03_hanshi.png` | Town POI: the Kōbō Tsuru entrance, NPCs, lanterns, the shrine stair, exits, and the zones |
| `04_dialogue.png` | Portraits L/R, text box, name plate, advance chevron, choices, and the zones |
| `05_shop.png` | Buy list, description, mon, Grandmother Tsuru, quantity, Sell, party compare, and the zones |
| `06_battle.png` | **Boss fight `sumikage_boss`: Smudge Ronin solo**, with the showcase Unfurl. 12 beats: boss intro, menu, Brushstroke Chain (ring closing, Clean Line, a miss, the Seal stamp), enemy turn, Vermilion Ink, the Unfurl into the Gale Crane Inkwing (trigger, cocoon, wings, reveal and the new menu), a Seal Art, and victory. A 13th panel is the zone key. |
| `06b_battle_standard.png` | **Standard fight `sumikage_c`: Blotling, Hollow Lantern, Blotling**, no Unfurl. 4 beats: intro and Benika's turn, the Three Prayer Slips chain ending in a Seal, the enemy turn, and finish plus results. |
| `LAYOUT_NOTES.md` | Every rect in px and %, the reserved touch rects, safe margins, framing, ambient motion, battle timing, the Unfurl beat sheet, takeaways per discipline, and open questions |

**Legend.** Dashed boxes are UI zones, labelled with the codes in LAYOUT_NOTES. The grey-filled dashed boxes are the **reserved touch rects** (T1 stick, T2 A/B, M ☰), drawn on every board. The touch rects are the team proposal Kekai approved, and Marc is adopting them in `input.js`. Red marks something meaningful.

**Rebuild.** Run `cd src && for f in b0[1-6]*_*.py; do python3 $f; done && python3 b00_contact.py && python3 gen_notes.py`. `src/zones.py` is the single source of truth for every rect. `gen_notes.py` writes the zone tables to `/tmp/LAYOUT_NOTES.md.tables` for pasting into the notes.

These are not final art, and nothing here is loaded by the game. Names follow SPEC v1.1 §2 and `team/story/CANON.md`.
