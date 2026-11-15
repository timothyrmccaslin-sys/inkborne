# Battle FX: Inkborne demo (Frank, art)

Procedural sumi-e ink FX as horizontal frame strips (lossless WebP, sRGB, straight alpha), one JSON sidecar per strip, and `manifest.json` in SPEC section 5 format (`src` is relative to `assets/art/`, so copy these files into `assets/art/fx/`). Each manifest entry also has a `loop` field. Palette and tints follow SPEC section 5 and CANON: paper/ink/washes, vermilion `#b3261e` as the only saturated accent, and muted element tints Gale `#5f8a6a` (Itsuki, Gale Crane), Ember `#c2452d` (Benika, Ember Kite), Stone `#7a6a52` (Gonzō, Stone Owl).

Keys use SPEC's kebab-case style (`bt-…`, `poi-…`) with an `fx-` group, because SPEC section 5 has no FX key pattern. Anchors are `[x, y]` fractions of the frame, the same as SPEC's `anchor`.

| key | file | frames | frame | fps | loop | anchor | layer | use |
|---|---|---|---|---|---|---|---|---|
| `fx-brushstroke-clean-line` | `fx-brushstroke-clean-line.webp` | 8 | 256×256 | 12 | false | [0.500, 0.500] | over | Clean Line (perfect press). Center on the Brushstroke timing ring; enso closes, slash, vermilion seal pops. |
| `fx-brushstroke-fail` | `fx-brushstroke-fail.webp` | 7 | 256×256 | 12 | false | [0.500, 0.500] | over | Missed press. Grey, dry-cracked broken ring and stroke that smear and crumble. No red. |
| `fx-death-demo` | `fx-death-demo.webp` | 14 | 256×256 | 12 | false | [0.500, 1.000] | over | Demo/fallback: generic left-facing ink beast dissolving (mask + edge wash + overlay applied). |
| `fx-death-ink` | `fx-death-ink.webp` | 14 | 256×256 | 12 | false | [0.500, 1.000] | over | Ink overlay for the dissolve: drips, ground puddle that soaks into the paper, drifting flecks. Anchor = enemy feet. |
| `fx-death-mask` | `fx-death-mask.webp` | 14 | 256×256 | 12 | false | [0.500, 1.000] | mask | Alpha mask: draw the enemy frame, then this frame with globalCompositeOperation='destination-in' (white RGB, alpha = keep). Then draw fx-death-ink on top. |
| `fx-hit-heavy` | `fx-hit-heavy.webp` | 10 | 256×256 | 12 | false | [0.438, 0.500] | over | center on the impact point; heavy/finisher variant with shock ring. Flip horizontally for hits on the party. |
| `fx-hit-light` | `fx-hit-light.webp` | 9 | 256×256 | 12 | false | [0.438, 0.500] | over | center on the impact point; splash flies to +x (party hitting a left-facing enemy). Flip horizontally for hits on the party. |
| `fx-inkwing-ember-loop` | `fx-inkwing-ember-loop.webp` | 12 | 512×512 | 12 | true | [0.500, 0.859] | behind | Held Ember Kite wings, seamless loop. Anchor = character feet. Draw BEHIND the battle sprite. |
| `fx-inkwing-ember` | `fx-inkwing-ember.webp` | 30 | 512×512 | 12 | false | [0.500, 0.859] | behind | Inkwing unfurl, Ember Kite. Anchor = character feet (sprite anchor). Draw BEHIND the battle sprite. Hand off to fx-inkwing-ember-loop. |
| `fx-inkwing-gale-loop` | `fx-inkwing-gale-loop.webp` | 12 | 512×512 | 12 | true | [0.500, 0.859] | behind | Held Gale Crane wings, seamless loop. Anchor = character feet. Draw BEHIND the battle sprite. |
| `fx-inkwing-gale` | `fx-inkwing-gale.webp` | 30 | 512×512 | 12 | false | [0.500, 0.859] | behind | Inkwing unfurl, Gale Crane. Anchor = character feet (sprite anchor). Draw BEHIND the battle sprite. Hand off to fx-inkwing-gale-loop. |
| `fx-inkwing-stone-loop` | `fx-inkwing-stone-loop.webp` | 12 | 512×512 | 12 | true | [0.500, 0.859] | behind | Held Stone Owl wings, seamless loop. Anchor = character feet. Draw BEHIND the battle sprite. |
| `fx-inkwing-stone` | `fx-inkwing-stone.webp` | 30 | 512×512 | 12 | false | [0.500, 0.859] | behind | Inkwing unfurl, Stone Owl. Anchor = character feet (sprite anchor). Draw BEHIND the battle sprite. Hand off to fx-inkwing-stone-loop. |
| `fx-seal-ember` | `fx-seal-ember.webp` | 18 | 512×512 | 12 | false | [0.586, 0.801] | over | Seal Art, ember (Ember Kite). Anchor = target enemy's feet. Frames 0-2 seal stamps, brush passes over it ~f4 (press moment), effect f6-17. |
| `fx-seal-gale` | `fx-seal-gale.webp` | 18 | 512×512 | 12 | false | [0.586, 0.801] | over | Seal Art, gale (Gale Crane). Anchor = target enemy's feet. Frames 0-2 seal stamps, brush passes over it ~f4 (press moment), effect f6-17. |
| `fx-seal-mark` | `fx-seal-mark.webp` | 5 | 256×256 | 12 | false | [0.500, 0.500] | over | Seal Arts: one red seal stamping onto the path. Hold the last frame; place one per seal (party.json seal.seals). |
| `fx-seal-pass` | `fx-seal-pass.webp` | 8 | 256×256 | 12 | false | [0.500, 0.500] | over | Seal Arts: plays on a seal when the press lands as the brush passes it (vermilion flare). |
| `fx-seal-stone` | `fx-seal-stone.webp` | 18 | 512×512 | 12 | false | [0.586, 0.801] | over | Seal Art, stone (Stone Owl). Anchor = target enemy's feet. Frames 0-2 seal stamps, brush passes over it ~f4 (press moment), effect f6-17. |

## Playback notes
- **Hits:** the splash flies toward +x, which suits the party hitting left-facing enemies. Flip horizontally when an enemy hits the party. Use `fx-hit-heavy` for finishers.
- **Brushstroke:** play `fx-brushstroke-clean-line` on a perfect press, centered on the timing ring (the enso is drawn to read as the ring closing). Play `fx-brushstroke-fail` on a miss. A normal (non-Clean) hit can just use `fx-hit-light`.
- **Seal Arts:** `fx-seal-<element>` is a complete 18-frame strip. The seal stamps in on f0–2, the brush sweeps across from f2–6 and passes over the seal at about f4 (the press moment), and the element effect lands on the target from f6–17 (Gale: sweeping wind streaks and a vortex; Ember: rising flame strokes and ash; Stone: slab strokes slamming down, red-lit cracks, flying chips). Party data gives 4–5 seals per Seal Art, so for a multi-press version place several `fx-seal-mark` along the brush path (hold the last frame) and play `fx-seal-pass` on each successful press.
- **Inkwing:** draw `fx-inkwing-<element>` (30 f) **behind** the battle sprite with the anchor at the sprite's feet, then switch to `fx-inkwing-<element>-loop` (12 f, seamless) for the 3 transformed turns. The swirl in the first frames is wide enough to show around the silhouette. The last unfurl frame matches loop frame 0 (same wing pose).
- **Enemy death:** draw the enemy frame, then the matching `fx-death-mask` frame with `globalCompositeOperation='destination-in'`, then reset to `source-over` and draw `fx-death-ink` (drips, a puddle that soaks into the paper, flecks). All three strips are 14 frames at the enemy's feet. `fx-death-demo` shows the result on a placeholder ink beast and can serve as a fallback.

## Placeholder assumptions
- FX keys, the `fx/` group, `loop` and `layer` are my proposal, because SPEC defines no FX keys. Rename them freely; the generator config is in one place.
- Frames are 256×256, except Seal Arts and Inkwing, which use 512×512 for room.
- Inkwing wing roots sit at (256, 268) in the 512 frame, with the feet at y = 440 (anchor 0.859). That assumes a character about 170–190 px tall in a 256 `bt-` frame. If the sprites are shorter or taller, change `ROOT` and `FEET` in the generator.
- The Seal Arts target is at x = 300 with the ground at y = 410 in the 512 frame; the anchor is at the target's feet.
- The seal glyph is an invented abstract mark, not a real character. Swap it if the story team wants a specific mon.
- `data/party.json` still holds placeholder members (akane/ember, yuzuru/gale, tsubaki/**tide**), while CANON has itsuki/gale, benika/ember, gonzo/stone. The FX follow CANON and the director's tints. There is no Tide Seal Art; tell me if Tide is still needed.

## Re-render
```
cd /workspace/inkborne/team/art/fx && python3 tools/gen_fx.py            # everything (~1 min, multi-core)
python3 tools/gen_fx.py fx-seal-gale fx-death                          # selected keys
```
The config block at the top of `tools/gen_fx.py` sets the output dir, frame sizes, fps, supersampling, palette, elements and tints, and frame counts. Previews (GIF over paper plus contact sheets, and `overview.jpg`) go to `previews/`. These are not game assets.
