# Ambient loops: Inkborne (Lucy, art)

Batch 1 for Sumikage Wood: drifting mist and falling leaves. Procedural sumi-e overlays that sit on Bob's v2 POI layers.

These are drop files. Marc reviews them and copies into `assets/art/`; nothing in `team/` is loaded by the game directly.

## This drop

| Key | Slot | Sits above | Parallax | Size | Frames | fps | Loop |
|---|---|---|---|---|---|---|---|
| `poi-forest-mist` | FX slot A | `poi-forest-far` | **0.3** | 3200×1440 | 72 | 12 | seamless, 6 s |
| `poi-forest-leaves` | FX slot B | `poi-forest-mid` | **0.7** | 3200×1440 | 72 | 12 | seamless, 6 s |

Each key is a folder of numbered lossless WebP frames with straight (unpremultiplied) alpha, `00.webp`–`71.webp`. Palette from SPEC section 5: paper `#ece6d8`, ink `#1b1813`, washes `#3b3730` / `#6d675b` / `#a39c8c`. No vermilion in this batch (it is reserved for lanterns and seals).

Placement is 1:1 with Bob's v2 forest layers and left-aligned at `x=0`. Anchor `[0.5, 1.0]` at position `[1600, 1440]` (the bottom-centre of the 3200×1440 layer). Blend is `source-over`. Suggested global opacity: **0.90** for mist (on top of the baked alpha, whose peak is about 0.42) and **1.0** for leaves. Do not use multiply — the RGB is already unmixed paper or ink.

The full placement block, including per-key notes, is in `ambient.json`.

## Width (please note)

Bob's v2 POI layers are **3200×1440**, about 1.25 screens, so the parallax has room to scroll. SPEC section 5 still says 2560. These overlays match Bob. `world-bg` and `battle-forest` stay at 2560×1440.

The game view is a 2560-wide window into the 3200-wide layer (640 px of scroll at parallax 1.0). Mist and leaves cover the full 3200 px so they hold up when the camera moves.

SPEC section 5 only documents horizontal frame strips. A 3200-wide strip of 72 frames would be 230400 px across, which is not practical, so the loops are stored as numbered frames. `src/art.js` currently loads one image per key and draws strips with `drawStrip`. The integrator will need a short loader change (a folder of frames, or an equivalent) before these replace the procedural placeholders in `src/scenes/poi.js`.

## What they look like

- **Mist.** Pale paper-tinted ink-wash veils, centred near `y ≈ 0.62 × 1440` (the band in Bob's original slot-A preview). They sit among the far peaks and the mid-layer tree line, not as a sky fill and not as ground mist on the walk path (ground mist is still a slot-B item, not in this batch). Soft washes with a little dry-brush streak and blotchy density, looping through a periodic noise volume so frame 0 joins frame 71.
- **Leaves.** Bamboo leaves and a few pine-needle clusters, falling through the path openings (about x 809–1110 and 2252–2642) and more sparingly through the groves. Every leaf parameter (fall, sway, wobble) is periodic in 72 frames. They sit above mid and below the party and the near frame. A sparser close-leaf pass for FX slot C is not in this batch.

`src/scenes/poi.js` currently draws procedural paper washes in slot A, ground mist in slot B, and placeholder leaves in slot C. These baked loops should replace the slot-A mist and the slot-B/C forest leaves; the town lantern glow in slot B stays until the lantern batch.

## Previews

Review files live in `previews/` and are not game assets.

- `poi-forest-mist.mp4` / `.gif`, `poi-forest-leaves.mp4` / `.gif`, `poi-forest-ambient.mp4` / `.gif` — composited over Bob's far, mid and near layers, showing the whole 3200-wide layer at 1600×720.
- `poi-forest-mist-still.png` and `poi-forest-leaves-still.png` — full-layer stills (1600×720).
- `poi-forest-mist-view.png` and `poi-forest-leaves-view.png` — the default 2560-wide game view (x=0) at 1280×720. These are the stills to show first.
- `poi-forest-ambient-view.png` and `poi-forest-ambient-view-right-f*.png` — both loops together, left view and a scrolled view (x=640).
- `*-seam.jpg` — last two frames against the first two, to inspect the loop join. The mist seam is composited over Bob's far layer (a pale wash on paper is otherwise invisible); `poi-forest-mist-seam-checker.jpg` shows the same join over a checker.
- `*-alphacheck-f*.jpg` — frames over a checker. Transparent pixels carry paper `#ece6d8` in RGB (WebP saved with `exact=True`, otherwise the encoder zeroes them and you get black fringes if the frame is premultiplied).
- `leaf-stamps.png` — the 14 procedural stamps.

## Re-render

```
cd /workspace/inkborne/team/art/ambient
python3 src/gen_ambient.py              # both loops + previews + ambient.json (~10–15 min)
python3 src/gen_ambient.py mist         # mist frames only
python3 src/gen_ambient.py leaves       # leaves frames only
python3 src/gen_ambient.py --preview    # rebuild previews and ambient.json from existing frames
python3 src/gen_ambient.py --frames 8   # short test
```

Pillow, numpy, scipy and ffmpeg are required. The seed is `20261115`. Frame count, seed and sizes are at the top of `src/gen_ambient.py`.

## Later items (not in this drop)

3. Hanshi lantern flicker — one glow at each of Bob's v2 lantern centres, in 3200×1440 space: mid `(1195,692)`, `(2067,669)`, `(2249,815)`, `(2673,836)`; near `(407,359)`. Mid lanterns belong in FX slot B; the big near lantern sits with the near layer (parallax 1.0–1.2) or in slot C. Vermilion `#b3261e` is the accent. Bob's README lists these; SPEC does not.
4. Sumikage Wood grass sway — optional slow sway on the near-layer grass and ferns (left), the tuft at about x 1350, and the grass by the right-hand rock. Bob also flags optional sway on town willow and bamboo.
5. Hanshi smoke rising — Bob's README does not give a chimney or brazier position. The v2 town mid has tiled roofs and a well, a ground-level vent on the left storehouse, and no obvious chimney pot. Needs a call from Kekai or Bob (kitchen roofline behind the inn/shop, incense on the shrine stair, or the stone lantern).
6. World-map brush-stroke flourish — `world-bg` stays 2560×1440. Not blocked.

FX slot C (a few close leaves, sparingly) can follow with the grass batch.
