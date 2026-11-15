Drop folder for the art team. See ../../SPEC.md section 9 for what goes here.

<!-- environments:start -->
# Environment backgrounds (Bob), v2

All files follow SPEC section 5: sRGB, using the section 5 palette (paper #ece6d8, ink #1b1813, washes #3b3730 / #6d675b / #a39c8c, vermilion #b3261e as the only accent).
Each key comes as `.webp` (q90, preferred) and `.png` (lossless master). `manifest-environments.json` holds the entries for `assets/art/manifest.json`, assuming the files go in `assets/art/bg/`.

**Width change in v2 (integrator, please note):** the POI layers (`poi-forest-*` and `poi-town-*`) are now **3200×1440**, about 1.25 screens, so the parallax has room to scroll. The Creative Director asked for this; SPEC section 5 says 2560. The far, mid and near layers of each POI are the same size and aligned at x=0. `world-bg` and `battle-forest` stay at 2560×1440.

| Key | Size | Alpha | Contents (v2) |
|---|---|---|---|
| `world-bg` | 2560×1440 | no | Bold folding-screen map: 4 gestural mountain masses, a dry-brush river into a pale-wash sea on the right, tonal forest bleeds in the lower left, a small ink mark for Hanshi, a red sun, faint 6-panel seams. The paths and nodes in `data/world.json` (×2 from the 1280×720 logical space) are kept as open paper. `world-bg@1080.png` is a 1920×1080 copy. |
| `poi-forest-far` | 3200×1440 | no | Sumikage Wood far layer: misty peaks and a distant tree line. No sun. |
| `poi-forest-mid` | 3200×1440 | **yes** | Pines and a bamboo grove with solid, opaque stalks. Seal-stones; two carry small cracked vermilion seals at about (1499,901) and (2514,1063). Opaque ground band from y≈1150. |
| `poi-forest-near` | 3200×1440 | **yes** | Framing: pine branch (top left), grass and ferns (left), a grass tuft (about x 1350), bamboo and a rock (right). |
| `poi-town-far` | 3200×1440 | no | Hanshi far layer: the shrine stair up to a vermilion torii at about (1262,498), with misty hills. |
| `poi-town-mid` | 3200×1440 | **yes** | Storehouse, inn, well, and the street of paper-walled houses, with opaque walls. v2.1: an old black pine (trunk about x 1340–1420, canopy over the roofs to x≈1700) stands at the old tile seam, full alpha, so the main street is solid right up to the trunk. Between the inn and the pine, the far layer's shrine stair and torii show through. The Kōbō Tsuru shop has Luc's mark on its noren at about (2429,838). Lanterns at about (1195,692), (2067,669), (2249,815), (2673,836). Opaque street from y≈1065. |
| `poi-town-near` | 3200×1440 | **yes** | An eave with the big foreground lantern at about (407,359), a stone lantern and fence (left), willow and a water barrel (right). |
| `battle-forest` | 2560×1440 | no | Unchanged composition. A hairline vermilion crack now runs down from the left seal-stone's seal (about x 810, y 710–900). The open fighting ground is about x 300–2300, y 760–1250. |

## Layer order and parallax (back to front)
1. `*-far`: parallax **0.2**
2. **FX slot A**: distant mist bands and slow fog (0.3)
3. `*-mid`: parallax **0.5**. The opaque ground band is the walk plane.
4. **FX slot B**: falling leaves (forest), lantern glow and flicker at the lantern coordinates above (town), ground mist
5. Player, NPCs, props: **1.0**
6. `*-near`: parallax **1.0 to 1.2**. Optional slow sway on the grass, bamboo and willow.
7. **FX slot C**: a few close leaves or ash, sparingly

With 3200-wide layers and a 2560 view, there are 640px of scroll at parallax 1.0. Scale offsets per layer, or clamp the camera.

## Notes and known weaknesses
- The source images are capped at 1152×864, so the POI layers were built from two tiles each, scaled 1.67× and stitched, instead of a true native render. Fine line work is still a little soft, though sharper than v1's 2×.
- Each POI layer has a stitch zone at about x 1280–1920. In town-mid (v2.1), the seam is hidden behind a solid pine instead of fading. Forest layers still use the multiply and crossfade there.
- `world-bg`: the mountains come from a generated image; the river, coast, sea, forests, the Hanshi mark and the seams are painted procedurally at 2560. The river's dry-brush texture is a little regular.
- Alpha is keyed from luminance. Enclosed areas, bamboo stalks and the ground bands are filled opaque.
- `src-environments/v2/` holds the raw images and scripts. Run them in this order: `stitch.py`, `process_v2.py`, `world_v2.py`, `fix_town_seam.py` (rebuilds town-mid), `previews.py`. They write to `../out` relative to the script folder.
