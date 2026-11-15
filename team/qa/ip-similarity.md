# Inkborne IP-similarity review (Legend of Dragoon)

- Reviewer: Noe (Quality & Security), 15 Nov 2026, America/Chicago
- Scope: `/workspace/inkborne` (SPEC v1.1, live `data/`, `src/`, `core/src`, `team/story`, `team/systems` (Jake, Jane, Ashley), `team/audio`, `team/art`, `team/BRIEF.md`). Compared against published Legend of Dragoon (Sony, 1999) names, element pairs, and story beats.
- Rule used: mechanics (timed combos, a transformation, opposed elements) are not protectable. Names, story beats, dialogue, designs, logos, music, and art that track LoD too closely are in scope. The combination of mechanics plus naming can still read as derivative.

## Blockers

No P0 blockers in current shipping text. SPEC v1.1 has already renamed the transformation gauge from **Spirit Ink** to **Vermilion Ink**, and live `data/items.json` uses that name. No LoD character, place, item, spell, enemy, or reserved term (`Dragoon`, `Wingly`, `Addition`) appears in player-facing data or code.

Two issues should still be cleaned up before the demo is treated as final: leftover "Spirit Ink" copy in story/systems docs (it can leak back into UI), and the live placeholder party in `data/party.json`, whose wind-element spear user tracks Lavitz too closely if that cast ships.

## P0 — must change before demo

None.

## P1 — should change

### P1-1. "Spirit Ink" leftovers, and the UI gauge label is still TBD

LoD's transformation gauge is **Spirit Points (SP)**. A **Spirit Potion** fills it by 100. Canon already bans "Spirit" as a mechanic term. SPEC v1.1 and live item text have moved to **Vermilion Ink**, but several source-of-truth docs still present "Spirit Ink" as current or as a live candidate, and the UI string for the gauge is still `TBD`. If those docs are copied into the build, the demo ships the one name that most clearly tracks LoD.

| File:line | What is wrong |
|---|---|
| `team/story/CANON.md:41` | Gauge still listed as **TBD**, and the line says SPEC currently calls it "Spirit Ink". SPEC v1.1 already says **Vermilion Ink**. |
| `team/story/CANON.md:63` | "Avoid 'Spirit' in player-facing text until the gauge name is settled." The name is settled. |
| `team/story/cast.md:44` | "SPEC's 'Spirit Ink' may become 'Vermilion Ink', pending Marc." |
| `team/story/glossary.md:96` | `transform_gauge` still TBD, description still cites Spirit Ink. |
| `team/story/glossary.json:335` | Same stale description. |
| `team/story/glossary.json:339` | `"Spirit Ink"` is still a `candidates` value. |
| `team/story/README.md:11` | Says `battle.gauge.label` is TBD and still names Spirit Ink as the SPEC term. |
| `team/story/strings.json:65` | `"battle.gauge.label": "TBD"` — the leak path into battle UI, logs, and tutorials (`{gauge}`). |
| `team/BRIEF.md:6` | "The gauge name is on hold, because 'Spirit Ink' may be renamed for IP reasons." |
| `team/systems/jake/README.md:72` | Still describes a SPEC / canon conflict around Spirit Ink (and a Tabula Rasa save key that SPEC v1.1 has already dropped). |

Suggested replacement: use **Vermilion Ink** everywhere (display name and UI). Keep the data key as `ink`. Remove "Spirit Ink" from glossary candidates. Jake's internal display name **Vermilion Gauge** should be aligned to **Vermilion Ink** so the team does not ship two official names. Jane's `Vermilion Drop` / `Cinnabar Cake` copy ("adds N to one ally's ink gauge") is already safe and can stay.

### P1-2. Live placeholder party: Yuzuru is a wind-element spear user

`data/party.json:6-9` — Yuzuru, title "Ronin of the long spear", element `gale`, stroke **Reed-Wind Thrust**, seal art **Cedar Gale**.

This is the live file the game loads. In LoD, **Lavitz Slambert** (later **Albert**) is the starting-party **Wind** (Jade Dragoon) fighter whose weapon is a **spear**, with wind-named Additions such as **Gust of Wind Dance** and magic such as **Wing Blaster**. A wind spearman in a game that also copies LoD's timed-combo-plus-transformation combat, even under an original Japanese name, is the combination most likely to read as derivative.

Suggested replacement: follow SPEC v1.1 and swap the live cast, places, and enemies for canon (`itsuki` / `benika` / `gonzo`; Sumikage Wood and Hanshi; Blotling, Hollow Lantern, Smudge Ronin). If the Akane / Yuzuru / Tsubaki placeholder cast is intentionally kept, change Yuzuru's weapon or his element so he is not a wind spearman (for example a gale swordsman, or a stone- or ember-element spear).

Related live files that would go with a canon swap (not themselves LoD copies, but they disagree with SPEC and canon): `data/story.json`, `data/world.json`, `data/enemies.json`, `data/shops.json`, `data/items.json`, and Ashley's zones, which are keyed to Mistcedar / Hollowbell / Blotwolf.

## P2 — minor or watch

### P2-1. Six Inks pairs match LoD's three opposed pairs

`SPEC.md:34`, `team/systems/jake/elements.json:21-28` (and the `opposite` / `chart` blocks).

Six Inks: **Ember↔Tide**, **Gale↔Stone**, **Dawn↔Dusk**, with ×2 / same ×0.5. LoD's opposed pairs are **Fire↔Water**, **Wind↔Earth**, **Light↔Dark**, with the same multipliers. LoD also has Thunder (no opposite) and Void/Unbased; Inkborne omits those and stops at the three pairs.

The pairings are a common JRPG pattern and are not protectable as mechanics. The names are original. No change required. If the team wants more distance, swap one pairing or add a seventh, unpaired ink.

### P2-2. "Fog that never lifts" in the live hook

`data/story.json:2` — "the Blank creeps inward like morning fog that never lifts."

This faintly echoes LoD's **Moon That Never Sets**. It is a simile about fog, not a celestial body, and the rest of the hook (a painted scroll, a missing master, red ink) is original.

Suggested replacement if you want zero echo: "like morning fog," "like a stain that will not dry," or "like frost that will not melt."

### P2-3. "Who is breaking the seals" in canon

`team/story/CANON.md:8` (and `team/story/story.json:3`) — the party sets out "to find who is breaking the seals."

LoD's late plot turns on destroying the **Signet Spheres** that seal the **Moon That Never Sets** (the body of the God of Destruction) away from its soul. "Seals" here is also native to Inkborne's shrine-and-red-ink aesthetic, and the demo does not involve a moon, a divine tree, or a sealed god. Fine for the demo if the seals stay local (shrine seal-stones, ink wards). Watch any later plot that adds a sealed moon, a world-tree, or a god split into body and soul; rewrite that beat if it appears.

### P2-4. Starting-party roles (canon)

Canon lead Itsuki (male wandering swordsman) plus Benika (female archer and healer) plus an older heavy hitter loosely resembles LoD's early party shape (Dart the swordsman, Shana the childhood-friend archer and healer, Lavitz the older physical fighter). Names, looks (kimono / miko / temple monk vs LoD's Western-fantasy designs), elements (Gale / Ember / Stone, not Fire / Light / Wind), and hook (amnesia and a cracking shrine, not a burned village and a captured friend) are original. No change needed. Do not later add "his village was burned" or "his childhood friend was captured and must be rescued from a prison" — those are specific LoD opening beats (Seles / Shana / Hellena, and Dart's destroyed hometown Neet / the Black Monster).

### P2-5. QA shorthand "SP"

`team/qa/test-plan.md:14`, `:78`, `:97`, `:108` still say "SP" for the gauge. Internal only, but it is LoD's exact abbreviation. Replace with "Ink" or "Vermilion Ink" so it does not show up in bug titles or UI copy.

### P2-6. Inkwing sprites (when they land)

Written Inkwing forms (Gale Crane, Ember Kite, Stone Owl) are original bird-and-ink designs, which is the right direction. LoD Dragoons are winged, floating, elemental-armored warriors. When `bt-<char>-inkwing-idle` and related sprites are added, they should stay clearly avian / ink-wash and not read as Dragoon armor, helmets, or dragon motifs. No character or transformation art is in `team/art` yet.

### P2-7. Staging filename "spirit_paper" (outside this tree)

`/workspace/inkborne-creative/luc/out/icon/icon-spirit_paper.webp` is not in the demo repo. If it is imported, rename it; "Spirit" is the banned mechanic term.

## Clear

Checked against LoD's published names and beats, and found fine:

- Reserved terms: no player-facing or code use of **Dragoon**, **Wingly**, or **Addition** (only bans, comments, and validator lists). Jake's `validate.py` and Ashley's encounter tests already reject those words.
- Party and NPC names in canon / Jake (Itsuki Hane, Benika Matsuo, Gonzō Kuraishi, Grandmother Tsuru, Old Hotaru) and in live placeholders (Akane, Yuzuru, Tsubaki, Ohana) do not match Dart, Shana, Lavitz, Albert, Rose, Haschel, Meru, Kongol, Miranda, Lloyd, Melbu Frahma, Zieg, or other LoD names.
- Places: Shirofuda, Sumikage Wood, Hanshi, Kōbō Tsuru; and live Kasane, Mender's Hut, Mistcedar Path, Hollowbell, The Pale Gate. None match Seles, Neet, Hellena, Bale, Lohan, Kazas, Hoax, Endiness, Serdio, the Divine Tree, or the Moon That Never Sets.
- Enemies and moves: Blotling, Hollow Lantern, Smudge Ronin; live Blotwolf, Paper Kappa, The Unwritten, and their move names. None match Virage, Feyrbrand, or other LoD enemy names.
- Items: live Lotus Salve, Sun-Steeped Tea, Ink Phial, Ember Charm, Tide Charm; Jane's Pine Needle Tea, Plum Rice Ball, Lantern Incense, Vermilion Drop, Cinnabar Cake, and the elemental charms. None copy Healing Potion, Spirit Potion, Angel's Prayer, or named LoD attack items. Ink Phial / Vermilion Drop / Cinnabar Cake fill the transform gauge (same *role* as a Spirit Potion); the names are original and the mechanic is not protectable.
- Stroke and Seal Art names (Falling Pine, Wet Edge, Three Prayer Slips, Lantern Volley, Temple Bell, Mountain Gong, Gale Crane Script, Ember Kite Litany, Stone Owl Verse; live Threefold Line, Reed-Wind Thrust, Bell-Chime Rhythm, Vermilion Comet, Cedar Gale, Undertow Hymn) do not match Additions (Double Slash, Volcano, Crush Dance, Harpoon, Gust of Wind Dance, etc.) or Dragoon Magic (Flameshot, Final Burst, Wing Blaster, Gaspless, Red-Eyed Dragon, etc.).
- Story: no burned hometown, no kidnapped childhood friend, no Black Monster revenge quest, no Moon That Never Sets, no Divine Tree, no God of Destruction / Virage Embryo. The painted-scroll world, the Blot / Blank, and the amnesia / shrine-keeper hook are original.
- Mechanic names in SPEC §2: Brushstroke / Forms of the Brush, Clean Line, Vermilion Ink, Unfurl, Inkwing, Seal Arts, Still Water, Six Inks, mon.
- Art in `team/art/environments` (world map, forest far/mid/near, town far/mid, battle source): sumi-e ink wash, pines and bamboo, a red-disk sun, a torii-and-stair peak, paper-walled houses with red lanterns, seal-stones in a clearing. This does not resemble LoD's pre-rendered Western-fantasy locations (Seles, Hellena's towers, Bale, the opening forest, the Moon, the Divine Tree) or its logos. No character sprites or logos are in `team/art` yet. No storyboards were present under `team/art` at review time.
- Audio under `team/audio`: synthesized / self-generated SFX and beds; the SFX readme states there is no "Dragoon" in the drop. No LoD music or samples are present. This review did not do a note-by-note comparison to the LoD soundtrack.
