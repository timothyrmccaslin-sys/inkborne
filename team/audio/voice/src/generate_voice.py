#!/usr/bin/env python3
"""Tabula Rasa party voice generator (Rita, audio/voice).
Pure formant synthesis: a glottal pulse source (with jitter, shimmer, vibrato and optional
subharmonic roughness) and aspiration noise, run through time-varying formant resonators.
No samples, no recorded voices. Seeds are fixed so output is reproducible.
Usage: python3 generate_voice.py [outdir]   (needs numpy, scipy, ffmpeg with libmp3lame)
"""
import sys, os, subprocess, wave, zlib, numpy as np
from scipy import signal

SR = 44100
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
BLOCK = 128

# Adult male formants (F1..F4 Hz) and bandwidths; scaled per character.
VOW = {
    'a': (730, 1090, 2440, 3400), 'e': (530, 1840, 2480, 3500), 'i': (300, 2250, 3000, 3700),
    'o': (570, 840, 2410, 3300), 'u': (320, 870, 2240, 3300), 'U': (450, 1200, 2400, 3400),  # schwa-ish
    'm': (250, 1100, 2300, 3300), 'n': (260, 1500, 2500, 3400), 'r': (500, 1300, 1700, 3200),
}
BW = (80, 110, 160, 220)
AMPS = {'m': (1, .06, .03, .02), 'n': (1, .08, .04, .02)}

# Character voices.
CHARS = {
    # Itsuki: calm, dry, guarded. Low-mid baritone, slightly breathy, restrained contours.
    'itsuki': dict(f0=118, fscale=1.0, breath=0.10, jitter=0.006, shimmer=0.05, sub=0.0, tilt=0.55, seed=11),
    # Benika: bright, stubborn, quick to laugh. Higher, forward formants, lively vibrato.
    'benika': dict(f0=245, fscale=1.17, breath=0.07, jitter=0.005, shimmer=0.04, sub=0.0, tilt=0.35, seed=22),
    # Gonzo: gruff, slow, kind. Deep, rough (subharmonic + more jitter), dark formants.
    'gonzo':  dict(f0=84, fscale=0.90, breath=0.12, jitter=0.014, shimmer=0.10, sub=0.35, tilt=0.70, seed=33),
}

def glottal(f0_curve, amp_curve, ch, rng, vib_rate=5.5, vib_depth=0.0):
    n = len(f0_curve); t = np.arange(n) / SR
    jit = signal.sosfilt(signal.butter(1, 30, fs=SR, output='sos'), rng.standard_normal(n)) * ch['jitter'] * 25
    f = f0_curve * (1 + jit + vib_depth * np.sin(2 * np.pi * vib_rate * t))
    ph = np.cumsum(f) / SR
    frac = ph % 1.0
    # Rosenberg-like pulse: smooth open phase, sharp closure -> rich harmonics.
    op = 0.6
    g = np.where(frac < op, 0.5 * (1 - np.cos(np.pi * frac / op)), np.cos(np.pi / 2 * (frac - op) / (1 - op)))
    g = np.where(frac < op, g, np.clip(np.cos(np.pi / 2 * (frac - op) / (1 - op) * 3), 0, 1))
    d = np.diff(g, prepend=0) * SR / 1000.0  # derivative = radiated flow
    if ch['sub'] > 0:  # vocal fry / growl: amplitude-modulate every other period
        d *= 1 - ch['sub'] * 0.5 * (1 + np.sign(np.sin(np.pi * ph)))
    shim = 1 + ch['shimmer'] * signal.sosfilt(signal.butter(1, 40, fs=SR, output='sos'), rng.standard_normal(n)) * 20
    src = d * shim
    # spectral tilt (darker voice = more low-pass)
    src = signal.sosfilt(signal.butter(1, 4000 * (1.2 - ch['tilt']), fs=SR, output='sos'), src) * 0.6 + src * 0.4 * (1 - ch['tilt'])
    return src / (np.max(np.abs(src)) + 1e-9) * amp_curve

def resonator_coeffs(f, bw):
    r = np.exp(-np.pi * bw / SR); th = 2 * np.pi * f / SR
    return np.array([1 - r]), np.array([1, -2 * r * np.cos(th), r * r])

def formant_filter(x, ftracks, gains):
    """Parallel bank of 4 time-varying resonators, processed in blocks with carried state."""
    n = len(x); y = np.zeros(n)
    for k in range(4):
        zi = np.zeros(2)
        for s in range(0, n, BLOCK):
            e = min(n, s + BLOCK); f = float(np.mean(ftracks[k][s:e]))
            b, a = resonator_coeffs(min(f, SR / 2 - 500), BW[k] * (1 + 0.002 * f / 10))
            seg, zi = signal.lfilter(b, a, x[s:e], zi=zi)
            y[s:e] += seg * gains[k][s:e]
    return y

def render(ch_id, segs, vib=0.0, vib_rate=5.5, gain_db=-3.0, tail=0.03):
    """segs: list of (dur, phoneme, f0_start_ratio, f0_end_ratio, amp_start, amp_end, breath_extra)."""
    ch = CHARS[ch_id]; rng = np.random.default_rng(ch['seed'] + zlib.crc32(str(segs).encode()) % 1000)
    f0 = []; amp = []; br = []; fts = [[] for _ in range(4)]; gs = [[] for _ in range(4)]
    prev = None
    for (d, ph, p0, p1, a0, a1, b) in segs:
        n = int(d * SR); w = np.linspace(0, 1, n)
        f0.append(ch['f0'] * (p0 + (p1 - p0) * w)); amp.append(a0 + (a1 - a0) * w); br.append(np.full(n, b))
        tgt = np.array(VOW.get(ph, VOW['U'])) * ch['fscale']
        src = tgt if prev is None else prev
        glide = np.clip(w / 0.35, 0, 1)  # coarticulation glide over first 35% of segment
        ga = AMPS.get(ph, (1, .7, .35, .18))
        for k in range(4):
            fts[k].append(src[k] + (tgt[k] - src[k]) * glide); gs[k].append(np.full(n, ga[k]))
        prev = tgt
    f0 = np.concatenate(f0); amp = np.concatenate(amp); br = np.concatenate(br)
    fts = [np.concatenate(v) for v in fts]; gs = [np.concatenate(v) for v in gs]
    amp = signal.sosfiltfilt(signal.butter(2, 60, fs=SR, output='sos'), amp)
    amp = np.clip(amp, 0, None)
    voiced = glottal(f0, amp, ch, rng, vib_rate, vib)
    asp = rng.standard_normal(len(f0)) * amp * (ch['breath'] + br)
    asp = signal.sosfilt(signal.butter(2, [400, 7000], 'bandpass', fs=SR, output='sos'), asp)
    y = formant_filter(voiced * (1 - np.clip(br, 0, 1)) + asp * 0.9, fts, gs)
    # light room: two short early reflections, keeps it 'in the world' without reverb tails
    y = y + 0.12 * np.pad(y, (int(0.017 * SR), 0))[:len(y)] + 0.07 * np.pad(y, (int(0.031 * SR), 0))[:len(y)]
    y = signal.sosfilt(signal.butter(2, 70, 'highpass', fs=SR, output='sos'), y)
    y = np.concatenate([y, np.zeros(int(tail * SR))])
    return y, gain_db

def burst(d=0.02, lo=1500, hi=6000, seed=0):
    g = np.random.default_rng(seed); x = g.standard_normal(int(d * SR))
    x = signal.sosfilt(signal.butter(2, [lo, hi], 'bandpass', fs=SR, output='sos'), x)
    return x * np.exp(-np.arange(len(x)) / SR * 120)

def prepend(burst_x, y, level=0.35):
    y = y.copy(); b = burst_x / (np.max(np.abs(burst_x)) + 1e-9) * level * np.max(np.abs(y))
    return np.concatenate([b, y])

def trill(y, start, end, rate=26, depth=0.6):
    t = np.arange(len(y)) / SR; m = np.ones(len(y))
    sel = (t >= start) & (t < end); m[sel] = 1 - depth * 0.5 * (1 + np.sin(2 * np.pi * rate * t[sel]))
    return y * m

def write(name, y, db=-3.0):
    fi, fo = int(0.003 * SR), int(0.02 * SR)
    y = y.copy(); y[:fi] *= np.linspace(0, 1, fi); y[-fo:] *= np.linspace(1, 0, fo)
    y = y / (np.max(np.abs(y)) + 1e-9) * 10 ** (db / 20)
    wav = f'/tmp/voice_{name}.wav'
    with wave.open(wav, 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((np.clip(y, -1, 1) * 32767).astype(np.int16).tobytes())
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', wav, '-ar', str(SR), '-ac', '1',
                    '-c:a', 'libmp3lame', '-q:a', '2', os.path.join(OUT, f'{name}.mp3')], check=True)
    os.remove(wav); print(f'{name}.mp3  {len(y) / SR:.2f}s')

S = lambda d, ph, p0, p1, a0, a1, b=0.0: (d, ph, p0, p1, a0, a1, b)

def make_all():
    # ---------------- Itsuki: calm, clipped, dry. Small pitch range, exhale-heavy. --------------
    c = 'itsuki'
    y, _ = render(c, [S(.03, 'U', 1.0, 1.0, 0, .5, .6), S(.11, 'U', 1.02, .9, .5, .2, .2), S(.06, 'm', .9, .86, .2, 0)])
    write('voice-itsuki-grunt-1', y)                           # "hn." (hurt, contained)
    y, _ = render(c, [S(.04, 'a', 1.1, 1.1, 0, .8, .5), S(.12, 'a', 1.1, .92, .8, 0, .15)])
    write('voice-itsuki-grunt-2', y)                           # "hah" (effort / getting hit)
    y, _ = render(c, [S(.05, 'm', .95, .95, 0, .6), S(.16, 'm', .95, .82, .6, 0, .05)])
    write('voice-itsuki-grunt-3', y)                           # "mm." (dry acknowledgement / block)
    y, _ = render(c, [S(.03, 'U', 1.15, 1.2, 0, 1, .4), S(.12, 'a', 1.25, 1.0, 1, 0, .05)])
    write('voice-itsuki-attack-1', prepend(burst(.012, 2000, 6000, 1), y, .5))   # "ha!" (sharp, short)
    y, _ = render(c, [S(.04, 'e', 1.1, 1.3, 0, 1, .2), S(.16, 'a', 1.3, 1.05, 1, 0, .05)])
    write('voice-itsuki-attack-2', y)                          # "eya!"
    y, _ = render(c, [S(.03, 'i', 1.3, 1.35, 0, .9, .3), S(.05, 'a', 1.35, 1.35, .9, 1), S(.15, 'a', 1.35, 1.0, 1, 0, .1)])
    write('voice-itsuki-attack-3', prepend(burst(.015, 2500, 7000, 2), y, .55))  # "tsha!" (finisher)
    y, _ = render(c, [S(.25, 'U', .9, 1.0, 0, .35, .7),                  # in-breath
                      S(.10, 'o', 1.1, 1.3, .3, .9, .1), S(.55, 'a', 1.35, 1.55, .9, 1.0),
                      S(.45, 'a', 1.55, 1.45, 1.0, .9), S(.35, 'o', 1.45, 1.2, .9, 0, .15)], vib=0.012, vib_rate=5.2)
    write('voice-itsuki-unfurl', y)                            # rising, controlled cry: "ho-aaah"
    y, _ = render(c, [S(.10, 'U', 1.0, .95, 0, .6, .5), S(.30, 'a', .95, .7, .6, .2, .3),
                      S(.35, 'U', .7, .55, .2, 0, .6)], vib=0.006)
    write('voice-itsuki-ko', y)                                # falling exhale "haa..."
    for i, (v, p) in enumerate([('a', 1.0), ('o', .95), ('U', 1.05)], 1):
        y, _ = render(c, [S(.012, v, p, p, 0, 1), S(.045, v, p, p * .97, 1, 0)], tail=.01)
        write(f'voice-itsuki-blip-{i}', y, db=-6)

    # ---------------- Benika: bright, punchy, wide pitch range, a laugh. ----------------
    c = 'benika'
    y, _ = render(c, [S(.03, 'a', 1.2, 1.25, 0, 1, .3), S(.10, 'U', 1.25, 1.0, 1, 0, .1)])
    write('voice-benika-grunt-1', prepend(burst(.01, 2500, 7000, 3), y, .3))  # "ah!" (hurt, indignant)
    y, _ = render(c, [S(.04, 'u', 1.0, 1.1, 0, .9), S(.12, 'U', 1.15, .95, .9, 0, .15)])
    write('voice-benika-grunt-2', y)                           # "uh!" (effort)
    y, _ = render(c, [S(.04, 'm', 1.1, 1.15, 0, .7), S(.16, 'm', 1.25, .9, .7, 0)])
    write('voice-benika-grunt-3', y)                           # "mm!" (stubborn, pursed)
    y, _ = render(c, [S(.03, 'i', 1.2, 1.35, 0, 1, .3), S(.13, 'a', 1.4, 1.15, 1, 0, .05)])
    write('voice-benika-attack-1', y)                          # "hya!"
    y, _ = render(c, [S(.03, 'e', 1.1, 1.2, 0, 1, .2), S(.06, 'i', 1.3, 1.35, 1, .9), S(.12, 'a', 1.4, 1.2, .9, 0)])
    write('voice-benika-attack-2', prepend(burst(.012, 3000, 8000, 4), y, .45))  # "te-ya!" (bow release)
    # quick laugh: "ha-ha!" (she's quick to laugh, used on Clean Line / crit)
    segs = []
    for k, p in enumerate([1.35, 1.45, 1.3]):
        segs += [S(.035, 'U', p, p, 0, .7, .7), S(.075, 'a', p, p * .92, .7 + .1 * k, .05, .05)]
    y, _ = render(c, segs)
    write('voice-benika-attack-3', y)
    y, _ = render(c, [S(.18, 'U', 1.0, 1.05, 0, .35, .7),
                      S(.10, 'e', 1.2, 1.45, .35, 1, .1), S(.45, 'a', 1.5, 1.8, 1, 1),
                      S(.35, 'a', 1.8, 1.7, 1, .9), S(.30, 'e', 1.7, 1.55, .9, 0, .1)], vib=0.02, vib_rate=6.0)
    write('voice-benika-unfurl', y)                            # bright soaring cry "ha-eeyaaah!"
    y, _ = render(c, [S(.08, 'a', 1.2, 1.1, 0, .8, .3), S(.28, 'a', 1.1, .75, .8, .2, .2),
                      S(.30, 'U', .75, .6, .2, 0, .6)], vib=0.012)
    write('voice-benika-ko', y)                                # "ah... aah..." falling
    for i, (v, p) in enumerate([('i', 1.15), ('e', 1.05), ('a', 1.25)], 1):
        y, _ = render(c, [S(.01, v, p, p, 0, 1), S(.035, v, p, p * 1.03, 1, 0)], tail=.01)
        write(f'voice-benika-blip-{i}', y, db=-6)

    # ---------------- Gonzo: deep, gruff, slow, warm. Rolled R, off-key hum. ----------------
    c = 'gonzo'
    y, _ = render(c, [S(.05, 'U', 1.0, 1.0, 0, .8, .3), S(.20, 'U', 1.0, .85, .8, 0, .1)])
    write('voice-gonzo-grunt-1', y)                            # "hrnh." (hurt, low)
    y, _ = render(c, [S(.05, 'm', .95, 1.0, 0, .8), S(.22, 'm', 1.0, .88, .8, 0)])
    write('voice-gonzo-grunt-2', y)                            # "hm." (his whole vocabulary)
    y, _ = render(c, [S(.04, 'o', 1.0, 1.05, 0, 1, .3), S(.18, 'U', 1.05, .9, 1, 0, .15)])
    write('voice-gonzo-grunt-3', y)                            # "oof"
    y, _ = render(c, [S(.04, 'U', 1.1, 1.15, 0, .8, .5), S(.12, 'r', 1.15, 1.2, .8, 1), S(.25, 'a', 1.25, 1.0, 1, 0, .05)])
    y = trill(y, .04, .16, rate=28, depth=.7)
    write('voice-gonzo-attack-1', y)                           # "hrraah!" (from barks)
    y, _ = render(c, [S(.04, 'o', 1.05, 1.2, 0, 1, .2), S(.20, 'o', 1.2, .95, 1, 0, .05)])
    write('voice-gonzo-attack-2', prepend(burst(.02, 400, 2500, 5), y, .5))    # "doh!" (staff slam)
    y, _ = render(c, [S(.05, 'U', 1.0, 1.1, 0, .9, .4), S(.10, 'r', 1.1, 1.15, .9, 1), S(.10, 'a', 1.2, 1.3, 1, 1),
                      S(.25, 'a', 1.3, .95, 1, 0, .05)])
    y = trill(y, .05, .15, rate=26, depth=.7)
    write('voice-gonzo-attack-3', y)                           # bigger "hrrRAH!" (finisher, Mountain Gong)
    y, _ = render(c, [S(.30, 'U', .85, .9, 0, .4, .6),
                      S(.15, 'o', 1.0, 1.15, .4, .9, .1), S(.25, 'r', 1.15, 1.25, .9, 1),
                      S(.70, 'o', 1.3, 1.45, 1, 1), S(.50, 'a', 1.45, 1.3, 1, 0, .1)], vib=0.015, vib_rate=4.6)
    y = trill(y, .45, .70, rate=24, depth=.6)
    write('voice-gonzo-unfurl', y)                             # slow, huge "ohhrrr-OOHH-aah"
    y, _ = render(c, [S(.10, 'm', 1.0, .95, 0, .7), S(.40, 'o', .95, .7, .7, .3, .2), S(.40, 'U', .7, .55, .3, 0, .5)], vib=0.01)
    write('voice-gonzo-ko', y)                                 # "mmoohh..." long low fall
    for i, (v, p) in enumerate([('o', 1.0), ('U', .95), ('a', 1.05)], 1):
        y, _ = render(c, [S(.015, v, p, p, 0, 1), S(.06, v, p, p * .96, 1, 0)], tail=.01)
        write(f'voice-gonzo-blip-{i}', y, db=-6)
    # Bonus: Gonzo's off-key hum (idle / victory). Deliberately a bit flat on the 3rd and 5th notes.
    notes = [(0, .45), (2, .35), (3.6, .55), (2, .35), (6.6, .7), (5, .45), (2, .4), (0, .8)]  # semitones, 3.6/6.6 = flat
    segs = [S(.06, 'm', 1, 1, 0, .6)]
    for st, d in notes:
        r = 2 ** (st / 12); segs.append(S(d, 'm', r, r * 1.004, .6, .55))
    segs.append(S(.25, 'm', 1, .97, .55, 0))
    y, _ = render(c, segs, vib=0.01, vib_rate=4.2)
    write('voice-gonzo-hum', y, db=-6)

if __name__ == '__main__':
    os.makedirs(OUT, exist_ok=True); make_all()
