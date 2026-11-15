# Inkborne progress (integrator)
Updated: Sun Nov 15 2026, 4:00 PM CT. Live: https://timothyrmccaslin-sys.github.io/inkborne/ (ib-0.1.1, commit d290e2a; SW cache ib-0.1.1, offline reload verified)

## Done
- All three views playable: world map -> Sumikage Wood / Hanshi POIs -> battle, dialogue (hanshi_dusk), shop (Kobo Tsuru).
- Battle: Brushstroke Chains (clean ±95 / good ±150 ms), Vermilion Ink, Unfurl -> Inkwing (Frank's FX strips), Seal Arts, Still Water, items, flee, victory/defeat.
- Audio wired: Cody music (manifest loop points), James SFX/ambience, Rita voice blips. All READMEs state self-generated, no samples.
- Wes's sw.js + manifest; offline reload verified on live URL. Real art icons. Kanji subset font.
- QA P0/P1 fixes (findings.md 3:22 PM).
- Smoke: tools-free Playwright run boots, plays boss fight to Victory with Unfurl + Seal Arts, no page errors.

## ib-0.1.1
- Site: Inkborne card on timothymccaslin.com (3758eb3) + intro line (b3ecaa1).
- Battle speech bubbles clamped below the top banner; Flee calls core.flee() (boss refuses -> battle.log.flee_blocked); XP + level-ups on the victory screen.
- Ashley's final ambient.js + encounters.js; zones in data/zones.json (forest first 20% safe, 10 px steps); road/wood encounters merged into enemies.json.
- Jane economy + Ollie story (n12b -> n13b -> n14, short n11 choices), items.json equipment[11], kobo_tsuru sells washi_vest + paper_charm; Luc's 11 equipment icons; shop list scrolls; no equip screen yet.
- Jamie's data/strings.json with runtime {gauge}/{confirm}/{cancel}/{menu} glyphs per input.
- Core: Rusty 0001-0009 (lib 47) + Jared 0010 save.rs + 4 QA tamper tests = 62 lib + Richard 5/5. Jake's party.json progression/stat tables; enemy xp 12/18/150. SPEC enemies schema has xp.
- QA save tamper: ST-1 (incomplete hp/ink backfilled, clamps), ST-2 (Continue only if the save test-loads; rejected save copied to inkborne-save-v1.bak), ST-3 clamps, ST-4 unknown/missing node -> woods_edge (Hakushi Clearing), locked node -> last unlocked.
- FPS meter: ?fps=1, or tap the title's version label 5 times (localStorage inkborne-fps).

## Placeholders still in (procedural, marked TODO(art))
- Character sprites + portraits (Kenji), UI frames (Nancy), ambient loops (Lucy). Smudge Ronin is an original procedural design.

## Next
- poi-town-mid seam fix from Bob (same key) -> rerun tools/integrate.py, tools/gen-sw-list.py, bump version.
- Every release: python3 tools/integrate.py && python3 tools/gen-sw-list.py && tools/bump-version.sh X.Y.Z
