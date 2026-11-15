# Inkborne progress (integrator)
Updated: Sun Nov 15 2026, 3:37 PM CT. Live: https://timothyrmccaslin-sys.github.io/inkborne/ (ib-0.1.0, commit 63923da)

## Done
- All three views playable: world map -> Sumikage Wood / Hanshi POIs -> battle, dialogue (hanshi_dusk), shop (Kobo Tsuru).
- Battle: Brushstroke Chains (clean ±95 / good ±150 ms), Vermilion Ink, Unfurl -> Inkwing (Frank's FX strips), Seal Arts, Still Water, items, flee, victory/defeat.
- Audio wired: Cody music (manifest loop points), James SFX/ambience, Rita voice blips. All READMEs state self-generated, no samples.
- Wes's sw.js + manifest; offline reload verified on live URL. Real art icons. Kanji subset font.
- QA P0/P1 fixes (findings.md 3:22 PM).
- Smoke: tools-free Playwright run boots, plays boss fight to Victory with Unfurl + Seal Arts, no page errors.

## Placeholders still in (procedural, marked TODO(art))
- Character sprites + portraits (Kenji), UI frames (Nancy), ambient loops (Lucy). Smudge Ronin is an original procedural design.

## Next
- poi-town-mid seam fix from Bob (same key) -> rerun tools/integrate.py, tools/gen-sw-list.py, bump version.
- Every release: python3 tools/integrate.py && python3 tools/gen-sw-list.py && tools/bump-version.sh X.Y.Z
- timothymccaslin.com project card (not done by this run).
