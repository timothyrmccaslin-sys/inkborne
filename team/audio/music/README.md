# Music (Cody, audio)

All cues are synthesized in-house by `src/generate_music.py` (numpy/scipy oscillators,
filtered breath noise, Karplus-Strong koto plucks, taiko-like drums, algorithmic reverb).
No outside samples or soundfonts. Seeds are fixed, so the output is reproducible:

```
python3 src/generate_music.py .
```

Optional: append track keys to render a subset (`title`, `world`, `forest`, `town`,
`battle`, `extra-transform-sting`, `extra-victory-fanfare`, `extra-victory-loop`, `extra-shop`).
Needs ffmpeg with libmp3lame.

Format follows SPEC section 6: 44.1 kHz stereo MP3 (not OGG), 160 kbps CBR, seamless
loops of 30–90 s for the keyed cues. Integrated loudness is aimed at −16 LUFS, true
peaks at or below −1 dBFS. Loops are exact whole bars at a fixed tempo. Each loop is rendered through
reverb as two cycles and the second cycle (periodic steady state) is kept so the
seam is click-free; a short numerical check of boundary continuity is stored in
`manifest.json`.

## WebAudio loop points (MP3 padding)

MP3 adds encoder padding, so in WebAudio play loops with `source.loop = true` and
set `loopStart ≈ 0.025`, `loopEnd = duration - 0.025`, or fade in a second source.
(Same finding as James's `team/audio/sfx/README.md`.) Per-file values are in
`manifest.json`. `duration` there is the decoded MP3 length, which includes padding.

## SPEC keys (section 6)

| file | key | length | bpm | scale | bars | loop | loopStart–End | mood |
|---|---|---|---|---|---|---|---|---|
| `title.mp3` | `title` | 60.00s | 64 | D miyako-bushi (in) | 16 | yes | 0.025–60.004 | calm-majestic |
| `world.mp3` | `world` | 64.00s | 90 | G yo | 24 | yes | 0.025–64.001 | expansive travelling |
| `forest.mp3` | `forest` | 64.00s | 60 | E hirajoshi | 16 | yes | 0.025–64.001 | misty, gentle mystery |
| `town.mp3` | `town` | 60.00s | 96 | D yo | 24 | yes | 0.025–60.004 | warm, lively but calm |
| `battle.mp3` | `battle` | 60.00s | 128 | A miyako-bushi (in) | 32 | yes | 0.025–60.004 | driving, urgent |

## Extras (not yet keyed in SPEC)

| file | key | length | bpm | scale | bars | loop | loopStart–End | mood |
|---|---|---|---|---|---|---|---|---|
| `extra-transform-sting.mp3` | `extra-transform-sting` | 4.20s | — | A miyako-bushi rising to D yo | — | one-shot | — | rising transformation sting, crest at 2.40 s |
| `extra-victory-fanfare.mp3` | `extra-victory-fanfare` | 8.00s | — | G yo | — | one-shot | — | bright victory fanfare |
| `extra-victory-loop.mp3` | `extra-victory-loop` | 38.40s | 100 | G yo | 16 | yes | 0.025–38.401 | gentle victory loop |
| `extra-shop.mp3` | `extra-shop` | 48.00s | 80 | F yo | 16 | yes | 0.025–48.014 | gentle, cozy shop |

`extra-transform-sting.mp3` is a rising one-shot whose musical crest is at 2.40 s, so
it can layer with James's `inkwing.mp3` whoosh (impact at ~2.4 s) without adding another
low boom. `extra-victory-fanfare.mp3` is a short one-shot; `extra-victory-loop.mp3` is an
optional gentle loop for a results hold. Marc can add keys for any of the extras.

## Regeneration

From this folder (or pass the folder as the first argument):

```
python3 src/generate_music.py .
```

The script writes each MP3 as soon as that track is finished, then rewrites
`manifest.json` and this README. Style is Japanese pentatonic (yo, in / miyako-bushi,
hirajoshi) with shakuhachi-like flute, koto-like plucks, low drones, and taiko-like
drums on the battle cue. The work is original to this project.
