# SFX + ambience (James, audio)

All sounds are synthesized in-house by `src/generate_sfx.py` (numpy/scipy oscillators, filtered noise,
Karplus-Strong plucks, additive bells). No outside samples. Seeds are fixed, so the output is reproducible:
`python3 src/generate_sfx.py .` (needs ffmpeg with libmp3lame). Format follows SPEC section 6: MP3, 44.1 kHz.
SFX are mono and peak at about -3 dBFS. Loops are stereo at about -16 to -18 dBFS RMS.

## SPEC keys (section 6)
| file | len | trigger | suggested gain |
|---|---|---|---|
| step.mp3 | 0.18 s | footstep, dirt (alts: step-dirt-02..04; step-wood-01..02 for town boards) | 0.5, randomize alt + ±5% rate |
| confirm.mp3 | 0.55 s | menu confirm (woodblock + bell) | 0.7 |
| cancel.mp3 | 0.26 s | menu cancel/back | 0.7 |
| ring.mp3 | 0.39 s | Brushstroke ring closing (breath rise, tick at 0.30 s) | 0.6 |
| hit.mp3 | 0.29 s | normal hit (alts: hit-heavy, hit-crit) | 0.8 |
| clean.mp3 | 0.78 s | Clean Line / timed-press success | 0.8 |
| miss.mp3 | 0.39 s | timed press missed / combo broken | 0.8 |
| guard.mp3 | 0.84 s | Still Water | 0.7 |
| heal.mp3 | 1.23 s | heal / item use | 0.7 |
| inkwing.mp3 | 3.03 s | Inkwing transformation whoosh (impact at ~2.4 s) | 0.9 |
| seal.mp3 | 0.68 s | Seal Arts seal hit | 0.8 |
| coin.mp3 | 0.73 s | shop purchase (mon) | 0.7 |
| text.mp3 | 0.08 s | dialogue text blip | 0.3 |
| wipe.mp3 | 0.63 s | ink-wipe scene transition | 0.6 |
| enemy-hit.mp3 | 0.29 s | enemy strikes party | 0.8 |
| lantern.mp3 | 1.54 s | lantern flicker accent (quiet) | 0.4 |
| wind.mp3 | 6.03 s | world-map wind gust one-shot (quiet) | 0.5 |

## Extras (not yet keyed in SPEC)
| file | len | use |
|---|---|---|
| move.mp3 | 0.10 s | menu cursor move |
| combo-finish.mp3 | 1.04 s | full Brushstroke chain completed |
| enemy-defeat.mp3 | 1.65 s | enemy dissolves into ink |
| hit-heavy.mp3, hit-crit.mp3 | 0.47 / 0.60 s | heavy / critical hit |
| amb-forest.mp3 | 48 s loop, stereo | forest POI: wind, birds, leaf rustle |
| amb-town.mp3 | 48 s loop, stereo | town POI: synthesized crowd murmur + wind chimes |

Loops are crossfaded at the wrap, so the seam is clean in the source. MP3 adds encoder padding, so in WebAudio
play them with `source.loop = true` and set `loopStart ≈ 0.025`, `loopEnd = duration - 0.025`, or fade in a second source.
No "Dragoon" anywhere, per the IP rule.
