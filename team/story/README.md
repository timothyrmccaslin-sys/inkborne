Drop folder for the story team. See ../../SPEC.md section 9 for what goes here.

## Jamie (Technical Writer): glossary and UI strings

The game is titled Inkborne (SPEC v1.1), and the repo is /workspace/inkborne.

- `glossary.json`: 52 entries (characters, Inkwings, Strokes, Seal Arts, enemies with flavor lines, places, lore, SPEC §2 mechanics, Six Inks, items). Each has `id`, `name`, `category`, `desc`, `source`, `status` (canon or TBD).
- `glossary.md`: the same glossary as tables, for reading.
- `strings.json`: a flat key map of 147 strings, which goes to `data/strings.json` per Kekai until Marc sets a schema. It covers the title screen, battle menu, targeting, turn order, battle log, results, Brushstroke prompts, Seal Arts prompts, gauge states, Unfurl, shop, pause, status, settings, world/POI prompts, and tutorials for Brushstroke, Unfurl, Still Water and the Six Inks.

Conventions: `{gauge}` always resolves to `battle.gauge.label`, which is "Vermilion Ink" (locked by Marc). `{confirm}`, `{cancel}` and `{menu}` are the SPEC §4 actions shown as the device's button glyph. No numbers live here; stats belong to team/systems.

Open questions:
1. Gauge name: resolved. It's Vermilion Ink.
2. Strings schema: Kekai says use `data/strings.json` as a flat key map until Marc decides otherwise.
3. Items: resolved by Kekai. Names and ids come from Ollie's list (`rice_cake`, `plum_tonic`, `thunder_jar`...), and Jane's numbers get mapped onto them. Jane's ids were removed from the glossary.
4. Second Strokes and Seal Art names: resolved. Lisa approved Jake's names, with "Crane Gale Script" renamed to "Gale Crane Script" (the id stays `crane_gale_script`). `lantern_keeper` is now Old Hotaru.
5. Live `data/party.json` and `data/enemies.json` still hold old placeholder names (Akane, Yuzuru, Tsubaki, Blotwolf, Paper Kappa, The Unwritten). Jake's team/systems/jake/party.json already uses canon.
6. Battle log assumes the Smudge Ronin fight blocks Flee (`battle.log.flee_blocked`). Systems to confirm.
