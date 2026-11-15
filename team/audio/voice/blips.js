// Tabula Rasa: runtime dialogue blips (Rita, audio/voice). SPEC section 9 JS synth patch format.
// Each key plays one text-scroll chirp: a pulse wave through two formant band-passes, with a tiny random
// pitch wobble so repeated blips don't machine-gun. Fire one per 2-3 revealed characters, skip spaces.
// The MP3s voice-<id>-blip-1..3 are the same voices pre-rendered, if you'd rather use samples.
const V = {
  itsuki: { f0: 118, f1: 730, f2: 1090, dur: 0.055, wobble: 0.04, gain: 0.22 }, // low, flat, clipped
  benika: { f0: 250, f1: 520, f2: 2300, dur: 0.045, wobble: 0.10, gain: 0.20 }, // high, bright, lively
  gonzo:  { f0: 84,  f1: 520, f2: 760,  dur: 0.075, wobble: 0.03, gain: 0.26 }, // deep, round, slow
  tsuru:  { f0: 200, f1: 400, f2: 1900, dur: 0.040, wobble: 0.06, gain: 0.18 }, // NPC: thin, quick
};
function blip(v) {
  return (ctx, out, t0) => {
    const f = v.f0 * (1 + (Math.random() * 2 - 1) * v.wobble);
    const osc = ctx.createOscillator(); osc.type = 'sawtooth';
    osc.frequency.setValueAtTime(f, t0); osc.frequency.exponentialRampToValueAtTime(f * 0.94, t0 + v.dur);
    const g = ctx.createGain();
    g.gain.setValueAtTime(0.0001, t0); g.gain.exponentialRampToValueAtTime(v.gain, t0 + 0.006);
    g.gain.exponentialRampToValueAtTime(0.0001, t0 + v.dur);
    const mixer = ctx.createGain(); mixer.gain.value = 1;
    for (const [freq, q, lvl] of [[v.f1, 6, 1], [v.f2, 8, 0.6]]) {
      const bp = ctx.createBiquadFilter(); bp.type = 'bandpass'; bp.frequency.value = freq; bp.Q.value = q;
      const l = ctx.createGain(); l.gain.value = lvl * 3; osc.connect(bp); bp.connect(l); l.connect(mixer);
    }
    mixer.connect(g); g.connect(out);
    osc.start(t0); osc.stop(t0 + v.dur + 0.02);
  };
}
export default {
  'blip-itsuki': blip(V.itsuki),
  'blip-benika': blip(V.benika),
  'blip-gonzo': blip(V.gonzo),
  'blip-tsuru': blip(V.tsuru),
};
