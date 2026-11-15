# Party voice (Rita, audio/voice)

Every sound in this folder is formant-synthesized by `src/generate_voice.py`. A glottal pulse source with jitter,
shimmer, vibrato and, for Gonzō, subharmonic growl, plus aspiration noise, goes through time-varying vowel formant
resonators. There are **no samples and no recorded voices**. The seeds are fixed, so the output is reproducible:
`python3 src/generate_voice.py .` (needs numpy, scipy, and ffmpeg with libmp3lame).
The format follows SPEC section 6: MP3, 44.1 kHz, mono. One-shots peak at -3 dBFS, while blips and the hum peak at -6 dBFS.
`blips.js` is a SPEC section 9 JS synth patch (`{ key: (ctx, out, t0) => {} }`) for runtime text blips.

Voices follow `team/story/CANON.md` / `cast.md` and Ollie's barks:
- **Itsuki** (~118 Hz) is calm, dry and guarded. His voice is breathy, with small pitch moves and clipped exhales. Even his Unfurl cry is controlled.
- **Benika** (~245 Hz) is bright, stubborn and quick to laugh. She has forward formants, a wide pitch range and lively vibrato, and her finisher is a laugh.
- **Gonzō** (~84 Hz) is gruff, slow and kind. His voice is deep and rough, with a rolled "hrraah" (from his barks), long low falls, and an off-key hum.

## Keys (file = `<key>.mp3`)
| key | len | trigger | suggested gain |
|---|---|---|---|
| `voice-itsuki-grunt-1` | 0.23 s | hurt ("hn.", matches bark "Hn. Barely a scratch.") | 0.8 |
| `voice-itsuki-grunt-2` | 0.19 s | hurt / effort ("hah") | 0.8 |
| `voice-itsuki-grunt-3` | 0.24 s | Still Water / guard ("mm.") | 0.7 |
| `voice-itsuki-attack-1` | 0.19 s | Brushstroke press ("ha!") | 0.9 |
| `voice-itsuki-attack-2` | 0.23 s | Brushstroke press ("eya!") | 0.9 |
| `voice-itsuki-attack-3` | 0.27 s | final stroke / Wet Edge ("tsha!") | 0.9 |
| `voice-itsuki-unfurl` | 1.73 s | Unfurl into Gale Crane, rising controlled cry | 1.0 |
| `voice-itsuki-ko` | 0.78 s | KO, falling exhale | 0.9 |
| `voice-itsuki-blip-1..3` | 0.07 s | dialogue text blip (rotate) | 0.3 |
| `voice-benika-grunt-1` | 0.17 s | hurt, indignant "ah!" (bark "Rude!") | 0.8 |
| `voice-benika-grunt-2` | 0.19 s | hurt / effort ("uh!") | 0.8 |
| `voice-benika-grunt-3` | 0.23 s | Still Water / stubborn "mm!" | 0.7 |
| `voice-benika-attack-1` | 0.19 s | Brushstroke press ("hya!") | 0.9 |
| `voice-benika-attack-2` | 0.25 s | Brushstroke press, bow release ("te-ya!") | 0.9 |
| `voice-benika-attack-3` | 0.36 s | quick laugh "ha-ha-ha!" for a finisher, Clean Line or crit | 0.9 |
| `voice-benika-unfurl` | 1.41 s | Unfurl into Ember Kite, bright soaring cry | 1.0 |
| `voice-benika-ko` | 0.69 s | KO, falling "ah... aah..." | 0.9 |
| `voice-benika-blip-1..3` | 0.05 s | dialogue text blip (rotate) | 0.3 |
| `voice-gonzo-grunt-1` | 0.28 s | hurt, low "hrnh." | 0.8 |
| `voice-gonzo-grunt-2` | 0.30 s | Still Water / guard, or a thoughtful "hm." | 0.7 |
| `voice-gonzo-grunt-3` | 0.25 s | hurt / effort ("oof") | 0.8 |
| `voice-gonzo-attack-1` | 0.44 s | Brushstroke press, rolled "hrraah!" | 0.9 |
| `voice-gonzo-attack-2` | 0.29 s | Brushstroke press, staff slam "doh!" | 0.9 |
| `voice-gonzo-attack-3` | 0.53 s | final stroke / Mountain Gong, bigger "hrrRAH!" | 0.9 |
| `voice-gonzo-unfurl` | 1.93 s | Unfurl into Stone Owl, slow huge "ohhrrr-OOHH-aah" | 1.0 |
| `voice-gonzo-ko` | 0.93 s | KO, long low "mmoohh..." | 0.9 |
| `voice-gonzo-blip-1..3` | 0.08 s | dialogue text blip (rotate) | 0.3 |
| `voice-gonzo-hum` | 4.39 s | extra: off-key hum for victory / idle / camp (notes 3 and 5 are flat on purpose) | 0.5 |

## JS patch keys (`blips.js`, default export)
`blip-itsuki`, `blip-benika`, `blip-gonzo`, `blip-tsuru` (an NPC bonus voice for Grandmother Tsuru). Each call plays one
chirp with a random ±pitch wobble. Fire one blip per 2–3 revealed characters and skip spaces. To use them, wire them into `src/audio.js`, for example
`import blips from '../team/audio/voice/blips.js'` and then `blips['blip-benika'](ctx, sfxBus, ctx.currentTime)`.

## Integration notes
- Battle: on each Brushstroke press, pick a random `attack-1/2` and use `attack-3` on the last stroke of a chain. Pick a random `grunt` when the character is hit.
  Play `unfurl` together with James's `sfx/inkwing.mp3` (whoosh impact ~2.4 s). Start the cry at about 0.5 s so it peaks into the impact.
- Vary playback rate by ±3% per play so repeats don't sound identical. Voices are dry, so they can share the SFX bus.
- These keys aren't in SPEC section 6 yet. Proposed SPEC addition: `voice-<id>-{grunt-1..3,attack-1..3,unfurl,ko,blip-1..3}`.
