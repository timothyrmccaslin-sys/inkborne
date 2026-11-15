#!/usr/bin/env python3
"""Inkborne music generator.

All audio is synthesized in-house from oscillators, filtered noise, and
Karplus-Strong plucks. No outside samples or soundfonts.

Usage:
    python3 src/generate_music.py .                 # render all tracks
    python3 src/generate_music.py . title battle    # render selected keys
"""
from __future__ import annotations
import json, os, re, subprocess, sys, wave
import numpy as np
from scipy import signal
import numba

SR = 44100
TARGET_LUFS = -16.0
PEAK_DB = -1.0
BITRATE = "160k"
MP3_PAD = 0.025  # lame encoder delay ~1105 samples; see James's sfx README

# ---------------------------------------------------------------------------
# Musical helpers
# ---------------------------------------------------------------------------
_PC = {
    "C": 0, "C#": 1, "Db": 1, "D": 2, "D#": 3, "Eb": 3, "E": 4,
    "F": 5, "F#": 6, "Gb": 6, "G": 7, "G#": 8, "Ab": 8, "A": 9,
    "A#": 10, "Bb": 10, "B": 11,
}

def midi_of(name: str) -> int:
    return 12 * (int(name[-1]) + 1) + _PC[name[:-1]]

def hz(note) -> float:
    if isinstance(note, (int, float)):
        return float(note)
    return 440.0 * 2 ** ((midi_of(note) - 69) / 12.0)

def loop_safe_freq(f: float, T: float) -> float:
    if T <= 0:
        return f
    return max(1.0, round(f * T) / T)

def beat_s(beats: float, bpm: float) -> float:
    return beats * 60.0 / bpm

def at_bar(bar: float, beat: float, bpm: float, sig: int = 4) -> float:
    return (bar * sig + beat) * 60.0 / bpm

# ---------------------------------------------------------------------------
# Core DSP
# ---------------------------------------------------------------------------
def t_(d: float) -> np.ndarray:
    return np.arange(max(1, int(round(d * SR))), dtype=np.float64) / SR

def noise(n, rng) -> np.ndarray:
    if isinstance(n, float):
        n = int(round(n * SR))
    return rng.standard_normal(int(n))

def _sos(kind, cut, order=2):
    return signal.butter(order, cut, kind, fs=SR, output="sos")

def lp(x, f, order=2):
    f = float(np.clip(f, 20, SR * 0.45))
    return signal.sosfilt(_sos("low", f, order), x)

def hp(x, f, order=2):
    f = float(np.clip(f, 20, SR * 0.45))
    return signal.sosfilt(_sos("high", f, order), x)

def bp(x, lo, hi, order=2):
    lo = float(np.clip(lo, 20, SR * 0.44))
    hi = float(np.clip(max(lo * 1.05, hi), lo * 1.05, SR * 0.45))
    return signal.sosfilt(signal.butter(order, [lo, hi], "bandpass", fs=SR, output="sos"), x)

def filt_loop(x, fn, pad_s=0.75):
    """Apply an IIR function with wrap padding so the loop stays continuous."""
    pad = int(pad_s * SR)
    if x.ndim == 1:
        y = np.concatenate([x[-pad:], x, x[:pad]])
        return fn(y)[pad:pad + len(x)]
    y = np.concatenate([x[:, -pad:], x, x[:, :pad]], axis=1)
    return fn(y)[:, pad:pad + x.shape[1]]

def dc_block(x, f=20.0, loop=False):
    def _hp1(y):
        return hp(y, f, 1)
    if loop:
        return filt_loop(x, (lambda y: _hp1(y)) if x.ndim == 1 else (lambda y: np.stack([_hp1(y[0]), _hp1(y[1])])))
    return _hp1(x) if x.ndim == 1 else np.stack([_hp1(x[0]), _hp1(x[1])])

def equal_power(pan: float):
    """pan 0 = left, 1 = right."""
    p = float(np.clip(pan, 0, 1))
    return np.cos(p * np.pi / 2), np.sin(p * np.pi / 2)

def env_adsr(n, a=0.02, d=0.08, s=0.7, r=0.12, sr=SR):
    t = np.arange(n) / sr
    dur = n / sr
    e = np.ones(n)
    na, nd, nr = int(a * sr), int(d * sr), int(r * sr)
    nr = min(nr, n)
    if na > 0:
        e[:na] = np.linspace(0, 1, na)
    if nd > 0 and na + nd < n:
        e[na:na + nd] = np.linspace(1, s, nd)
    elif na < n:
        e[na:] = s
    if n - nr > na:
        e[n - nr:] = e[n - nr] * np.linspace(1, 0, nr)
    else:
        e *= np.linspace(1, 0, n) ** 0.5
    # ensure start/end at 0
    if n:
        e[0] = 0.0
    return e

# ---------------------------------------------------------------------------
# Karplus-Strong (koto / bass strings)
# ---------------------------------------------------------------------------
@numba.njit(cache=True)
def _ks_core(n, N, buf, damp):
    out = np.empty(n)
    idx = 0
    for i in range(n):
        nxt = (idx + 1) % N
        out[i] = buf[idx]
        buf[idx] = 0.5 * (buf[idx] + buf[nxt]) * damp
        idx = nxt
    return out

_KS_CACHE: dict = {}

def ks_pluck(freq, dur, damp=0.996, bright=0.65, seed=0, oshi=0.0):
    """Koto-like Karplus-Strong pluck. oshi is a late upward pitch hint in cents (0=off)."""
    n = int(round(dur * SR))
    if n <= 4:
        return np.zeros(max(n, 1))
    key = (round(freq, 3), n, round(damp, 5), round(bright, 3), int(seed))
    if key in _KS_CACHE and oshi == 0:
        return _KS_CACHE[key].copy()
    N = max(2, int(round(SR / float(freq))))
    rng = np.random.default_rng(int(seed) + 17)
    buf = rng.uniform(-1.0, 1.0, N).astype(np.float64)
    # brightness: one-pole on the excitation
    a = 0.25 + 0.75 * float(np.clip(bright, 0, 1))
    for i in range(1, N):
        buf[i] = a * buf[i] + (1 - a) * buf[i - 1]
    buf -= buf.mean()
    peak = np.max(np.abs(buf)) or 1.0
    buf /= peak
    body = _ks_core(n, N, buf.copy(), float(damp))
    # pick noise (hitsu)
    t = np.arange(n) / SR
    click_n = min(n, int(0.03 * SR))
    click = np.zeros(n)
    click[:click_n] = hp(rng.standard_normal(click_n), 3500, 1) * np.exp(-t[:click_n] * 180)
    out = body * 0.92 + click * 0.10
    out *= np.clip(t / 0.002, 0, 1)
    # soft release so we can overlap
    rel = int(min(0.04 * SR, n * 0.2))
    if rel > 0:
        out[-rel:] *= np.linspace(1, 0, rel)
    if oshi:
        # after ~40 ms, gently raise residual pitch by mixing a slightly shorter delay copy
        start = int(0.04 * SR)
        if start < n - 100:
            ratio = 2 ** (oshi / 1200.0)
            # resample tail upward
            tail = body[start:]
            new_len = int(len(tail) / ratio)
            if new_len > 8:
                idx = np.linspace(0, len(tail) - 1, new_len)
                bent = np.interp(idx, np.arange(len(tail)), tail)
                fade = np.linspace(0, 1, min(int(0.08 * SR), len(bent)))
                bent[: len(fade)] *= fade
                mix = np.zeros_like(body)
                mix[start:start + len(bent)] = bent
                # fade original tail down a bit
                out = out * 0.7 + mix * 0.5
    # normalize pluck to a stable peak
    p = np.max(np.abs(out)) or 1.0
    out = out / p * 0.9
    if oshi == 0:
        _KS_CACHE[key] = out.copy()
    return out

# ---------------------------------------------------------------------------
# Shakuhachi-like flute
# ---------------------------------------------------------------------------
def shakuhachi(freq, dur, artic="norm", seed=0, end_freq=None, vib_depth=12.0):
    """Breathy flute: sine partials + filtered breath, vibrato, nayashi / meri bends."""
    n = int(round(dur * SR))
    if n <= 8:
        return np.zeros(max(n, 1))
    t = np.arange(n) / SR
    rng = np.random.default_rng(int(seed) + 101)
    # envelopes
    if artic == "soft":
        att, rel, breath0, amp = 0.09, min(0.22, dur * 0.25), 0.12, 0.85
        nayashi, meri = 0.14, 0.0
    elif artic == "accent":
        att, rel, breath0, amp = 0.025, min(0.12, dur * 0.2), 0.28, 1.05
        nayashi, meri = 0.06, 0.0
    elif artic == "fall":
        att, rel, breath0, amp = 0.05, min(0.28, dur * 0.35), 0.16, 0.95
        nayashi, meri = 0.08, 1.0
    elif artic == "legato":
        att, rel, breath0, amp = 0.035, min(0.08, dur * 0.15), 0.10, 0.95
        nayashi, meri = 0.0, 0.0
    else:
        att, rel, breath0, amp = 0.055, min(0.16, dur * 0.22), 0.16, 1.0
        nayashi, meri = 0.10, 0.0

    att = min(att, dur * 0.35)
    rel = min(rel, dur * 0.45)
    e = np.ones(n)
    na, nr = int(att * SR), int(rel * SR)
    if na:
        # slightly concave attack (breath first)
        e[:na] = np.linspace(0, 1, na) ** 1.4
    if nr:
        e[-nr:] = e[-nr] * np.linspace(1, 0, nr) ** 1.1
    # slow swell in the body of long notes
    if dur > 1.2:
        mid = 0.85 + 0.15 * np.sin(np.pi * np.clip(t / dur, 0, 1))
        e *= mid
    e *= amp

    # pitch contour in cents
    cents = np.zeros(n)
    if nayashi > 0:
        nn = int(min(nayashi, dur * 0.4) * SR)
        cents[:nn] += -28.0 * (1 - np.linspace(0, 1, nn)) ** 2
    if meri or artic == "fall":
        mn = int(min(0.35, dur * 0.4) * SR)
        cents[-mn:] += -55.0 * np.linspace(0, 1, mn) ** 1.4
    # delayed vibrato
    vib_hz = 4.8
    vib_on = np.clip((t - 0.18) / 0.28, 0, 1)
    # slight irregularity
    jitter = lp(rng.standard_normal(n), 6, 1)
    jitter /= (np.max(np.abs(jitter)) or 1)
    cents += vib_on * (vib_depth * np.sin(2 * np.pi * vib_hz * t) + 3.0 * jitter)

    f0 = float(freq)
    f1 = float(end_freq) if end_freq is not None else f0
    if end_freq is not None:
        # portamento across the note
        glide = 0.5 - 0.5 * np.cos(np.pi * np.clip(t / max(dur * 0.7, 1e-3), 0, 1))
        f_base = f0 * (1 - glide) + f1 * glide
    else:
        f_base = np.full(n, f0)
    inst = f_base * (2 ** (cents / 1200.0))
    phase = 2 * np.pi * np.cumsum(inst) / SR
    # hollow partials (odd-leaning, modest even for air)
    tone = (
        1.00 * np.sin(phase)
        + 0.16 * np.sin(2 * phase)
        + 0.09 * np.sin(3 * phase)
        + 0.04 * np.sin(4 * phase)
        + 0.02 * np.sin(5 * phase)
    )
    # breath: bandpass noise around the note, stronger at attack
    br = bp(rng.standard_normal(n), max(80, f0 * 0.7), min(8000, f0 * 3.5 + 1200), 1)
    b_env = breath0 * (0.55 + 0.45 * e) + 0.22 * breath0 * np.exp(-t / max(att, 0.04))
    if artic == "accent":
        b_env += 0.35 * np.exp(-t * 18)
    voice = (0.86 * tone + 0.22 * br * b_env) * e
    # tiny DC / start click guard
    fade = min(int(0.004 * SR), n // 8)
    if fade:
        voice[:fade] *= np.linspace(0, 1, fade)
    return voice

# ---------------------------------------------------------------------------
# Taiko / light percussion
# ---------------------------------------------------------------------------
def taiko(kind="don", seed=0):
    rng = np.random.default_rng(int(seed) + 202)
    if kind == "don":
        d, f0, drop, ndec, nlo, nhi, body, noise_amp = 0.85, 78, 0.62, 7.0, 80, 520, 1.0, 0.55
    elif kind == "chu":
        d, f0, drop, ndec, nlo, nhi, body, noise_amp = 0.55, 130, 0.55, 10.0, 200, 1400, 0.85, 0.5
    elif kind == "ka":
        d, f0, drop, ndec, nlo, nhi, body, noise_amp = 0.22, 280, 0.35, 28.0, 800, 5000, 0.25, 0.9
    else:  # soft wood / tsuzumi-like
        d, f0, drop, ndec, nlo, nhi, body, noise_amp = 0.16, 420, 0.25, 40.0, 600, 3500, 0.45, 0.5
    t = t_(d)
    fr = f0 * (1 - drop * np.clip(t / (d * 0.55), 0, 1) ** 0.7)
    thump = np.sin(2 * np.pi * np.cumsum(fr) / SR)
    # second partial, quicker decay
    thump += 0.35 * np.sin(2 * np.pi * np.cumsum(fr * 1.7) / SR) * np.exp(-t * (ndec + 4))
    thump *= np.exp(-t * ndec / 1.6) * np.clip(t / 0.003, 0, 1)
    skin = bp(rng.standard_normal(len(t)), nlo, nhi, 1) * np.exp(-t * (ndec * 1.8))
    skin *= np.clip(t / 0.0015, 0, 1)
    # shell thud for don
    shell = 0.0
    if kind in ("don", "chu"):
        shell = lp(rng.standard_normal(len(t)), 180, 1) * np.exp(-t * 12) * 0.25
    out = body * thump + noise_amp * skin + shell
    p = np.max(np.abs(out)) or 1.0
    return out / p * 0.95

def wood_click(seed=0):
    rng = np.random.default_rng(int(seed) + 303)
    d = 0.11
    t = t_(d)
    tone = (np.sin(2 * np.pi * 890 * t) + 0.4 * np.sin(2 * np.pi * 1480 * t)) * np.exp(-t * 55)
    tick = bp(rng.standard_normal(len(t)), 2000, 7000, 1) * np.exp(-t * 90)
    return (tone * 0.7 + tick * 0.5) * np.clip(t / 0.001, 0, 1)

# ---------------------------------------------------------------------------
# Pads / drones
# ---------------------------------------------------------------------------
def pad_drone(notes, dur, seed, tone="dark", cycles=4, air=0.04):
    n = int(round(dur * SR))
    t = np.arange(n) / SR
    rng = np.random.default_rng(int(seed))
    L = np.zeros(n)
    R = np.zeros(n)
    cut = {"dark": 780, "warm": 1400, "mist": 2200, "bright": 1800, "tense": 1100}[tone]
    for i, note in enumerate(notes):
        f0 = loop_safe_freq(hz(note), dur)
        det = 6.0 + (i % 3)
        for mul, amp in ((1.0, 1.0), (2.0, 0.16 if tone != "mist" else 0.08), (3.0, 0.05)):
            fl = loop_safe_freq(f0 * mul * 2 ** (-det / 1200.0), dur)
            fr = loop_safe_freq(f0 * mul * 2 ** (det / 1200.0), dur)
            ph = rng.uniform(0, 2 * np.pi)
            L += amp * np.sin(2 * np.pi * fl * t + ph)
            R += amp * np.sin(2 * np.pi * fr * t + ph + 0.15)
    lfo = 0.78 + 0.22 * np.sin(2 * np.pi * cycles * t / dur)
    # a second slower shimmer (coprime cycle count)
    c2 = cycles - 1 if cycles > 2 else 2
    lfo *= 0.92 + 0.08 * np.sin(2 * np.pi * c2 * t / dur + 0.7)

    def _cut(y):
        return lp(y, cut, 2)

    L = filt_loop(L * lfo, _cut)
    R = filt_loop(R * lfo, _cut)
    if air > 0:
        nL = filt_loop(lp(rng.standard_normal(n), cut * 0.6, 1), lambda y: lp(y, cut * 0.6, 1))
        nR = filt_loop(lp(rng.standard_normal(n), cut * 0.6, 1), lambda y: lp(y, cut * 0.6, 1))
        L += nL * air
        R += nR * air
    # normalize pad to ~0.5 peak so mix staging is predictable
    st = np.stack([L, R])
    p = np.max(np.abs(st)) or 1.0
    return st / p * 0.5

# ---------------------------------------------------------------------------
# Reverb (Freeverb-ish) and loop wrap
# ---------------------------------------------------------------------------
def _comb(x, delay, fb, damp=0.25):
    d = int(delay)
    y = np.zeros(len(x))
    buf = np.zeros(d)
    flt = 0.0
    idx = 0
    for i in range(len(x)):
        v = buf[idx]
        flt = (1 - damp) * v + damp * flt
        buf[idx] = x[i] + flt * fb
        y[i] = v
        idx += 1
        if idx >= d:
            idx = 0
    return y

_comb_jit = numba.njit(_comb, cache=True)

def _allpass(x, delay, g=0.5):
    d = int(delay)
    b = np.zeros(d + 1)
    a = np.zeros(d + 1)
    b[0], b[d] = -g, 1.0
    a[0], a[d] = 1.0, -g
    return signal.lfilter(b, a, x)

def reverb_stereo(st, wet=0.32, room=0.82, damp=0.3, predelay_s=0.018):
    """Return dry + wet reverb, same shape as st (2, n)."""
    L, R = np.asarray(st[0], dtype=np.float64), np.asarray(st[1], dtype=np.float64)
    pd = int(predelay_s * SR)
    if pd > 0:
        Lp = np.concatenate([np.zeros(pd), L])
        Rp = np.concatenate([np.zeros(pd), R])
    else:
        Lp, Rp = L, R
    combs_l = (1116, 1188, 1277, 1356, 1422, 1491, 1557, 1617)
    combs_r = tuple(c + 23 for c in combs_l)
    fb = float(np.clip(room, 0.5, 0.93))
    wL = np.zeros(len(Lp))
    wR = np.zeros(len(Rp))
    for d in combs_l:
        wL += _comb_jit(Lp, d, fb, damp)
    for d in combs_r:
        wR += _comb_jit(Rp, d, fb, damp)
    wL /= 4.2
    wR /= 4.2
    for d, g in ((556, 0.5), (441, 0.5), (341, 0.5), (225, 0.5)):
        wL = _allpass(wL, d, g)
        wR = _allpass(wR, d + 11, g)
    # trim predelay back to original length (reverb continues through predelay offset)
    wL = wL[pd:pd + len(L)] if pd else wL
    wR = wR[pd:pd + len(R)] if pd else wR
    if len(wL) < len(L):
        wL = np.pad(wL, (0, len(L) - len(wL)))
        wR = np.pad(wR, (0, len(R) - len(wR)))
    out = np.stack([L + wet * wL[: len(L)], R + wet * wR[: len(R)]])
    return out

def loop_with_reverb(st, wet=0.32, room=0.82, damp=0.3, tail_s=3.0, predelay_s=0.018):
    """Render two cycles + silent tail, extract the second cycle, wrap the tail."""
    n = st.shape[1]
    extra = int(round(tail_s * SR))
    silent = np.zeros((2, extra))
    doubled = np.concatenate([st, st, silent], axis=1)
    wet_sig = reverb_stereo(doubled, wet=wet, room=room, damp=damp, predelay_s=predelay_s)
    # Second cycle is already in periodic steady state (rt60 << loop length),
    # so it loops cleanly. Do not add the silent tail onto the start — that
    # double-counts decay and creates a seam click.
    mid = wet_sig[:, n:2 * n].copy()
    return mid

def seam_metrics(st, ms=8.0):
    """Boundary continuity of a looped stereo buffer."""
    k = max(2, int(ms * SR / 1000.0))
    wrap = np.concatenate([st[:, -k:], st[:, :k]], axis=1)
    jump = st[:, 0] - st[:, -1]
    d_join = jump
    d_after = st[:, 1] - st[:, 0]
    d_before = st[:, -1] - st[:, -2]
    steps = np.abs(np.diff(st, axis=1))
    typ = float(np.median(steps))
    return {
        "abs_jump": float(np.max(np.abs(jump))),
        "typical_step": typ,
        "jump_over_typical": float((np.max(np.abs(jump)) / typ) if typ else 0),
        "deriv_err": float(np.max(np.abs(d_join - 0.5 * (d_before + d_after)))),
        "wrap_peak": float(np.max(np.abs(wrap))),
        "wrap_rms": float(np.sqrt(np.mean(wrap ** 2))),
    }

# ---------------------------------------------------------------------------
# Loudness (ITU-R BS.1770-4 K-weight) + limiter
# ---------------------------------------------------------------------------
def _k_weight_sos(sr=SR):
    # Official analog prototypes, bilinear-transformed at sr.
    # Pre-filter: high shelf, f0=1681.974..., G=3.9998 dB, Q=0.707175
    # RLB highpass: f0=38.13547, Q=0.500327
    def shelf_and_hp():
        # high shelf
        f0, G, Q = 1681.974450955533, 3.999843853973347, 0.7071752369554196
        A = 10 ** (G / 40.0)
        w0 = 2 * np.pi * f0 / sr
        alpha = np.sin(w0) / (2 * Q)
        b0 = A * ((A + 1) + (A - 1) * np.cos(w0) + 2 * np.sqrt(A) * alpha)
        b1 = -2 * A * ((A - 1) + (A + 1) * np.cos(w0))
        b2 = A * ((A + 1) + (A - 1) * np.cos(w0) - 2 * np.sqrt(A) * alpha)
        a0 = (A + 1) - (A - 1) * np.cos(w0) + 2 * np.sqrt(A) * alpha
        a1 = 2 * ((A - 1) - (A + 1) * np.cos(w0))
        a2 = (A + 1) - (A - 1) * np.cos(w0) - 2 * np.sqrt(A) * alpha
        sos1 = np.array([b0 / a0, b1 / a0, b2 / a0, 1.0, a1 / a0, a2 / a0])
        # RLB 2nd-order highpass
        f1, Q1 = 38.13547087602444, 0.5003270373223665
        w1 = 2 * np.pi * f1 / sr
        al = np.sin(w1) / (2 * Q1)
        b0 = (1 + np.cos(w1)) / 2
        b1 = -(1 + np.cos(w1))
        b2 = (1 + np.cos(w1)) / 2
        a0 = 1 + al
        a1 = -2 * np.cos(w1)
        a2 = 1 - al
        sos2 = np.array([b0 / a0, b1 / a0, b2 / a0, 1.0, a1 / a0, a2 / a0])
        return np.stack([sos1, sos2])

    return shelf_and_hp()

_K_SOS = _k_weight_sos(SR)

def integrated_lufs(st):
    """Gated integrated LUFS, stereo (2, n)."""
    z = np.stack([signal.sosfilt(_K_SOS, st[0]), signal.sosfilt(_K_SOS, st[1])])
    # 400 ms blocks, 75% overlap (hop 100 ms) per BS.1770
    block = int(0.4 * SR)
    hop = int(0.1 * SR)
    if z.shape[1] < block:
        ms = np.mean(z ** 2, axis=1)
        zsum = ms[0] + ms[1]
        return float(-0.691 + 10 * np.log10(zsum + 1e-20))
    powers = []
    for i in range(0, z.shape[1] - block + 1, hop):
        seg = z[:, i:i + block]
        powers.append(np.mean(seg ** 2, axis=1).sum())
    powers = np.asarray(powers)
    # absolute gate -70 LUFS  (LUFS = -0.691 + 10 log10(P))
    abs_thr = 10 ** ((-70 + 0.691) / 10)
    gated = powers[powers >= abs_thr]
    if gated.size == 0:
        return -70.0
    rel_thr = 10 ** ((-0.691 + 10 * np.log10(np.mean(gated)) - 10 + 0.691) / 10)
    # relative threshold is 10 dB below the absolute-gated loudness
    gated2 = powers[(powers >= abs_thr) & (powers >= rel_thr)]
    if gated2.size == 0:
        gated2 = gated
    return float(-0.691 + 10 * np.log10(np.mean(gated2) + 1e-20))

def true_peak_db(st):
    # 4x oversample peak as a cheap true-peak estimate
    up = signal.resample_poly(st, 4, 1, axis=1)
    p = np.max(np.abs(up)) or 1e-12
    return float(20 * np.log10(p))

@numba.njit(cache=True)
def _limiter_gain(absx, ceiling, att, rel):
    n = absx.shape[0]
    env = 0.0
    g = np.empty(n)
    inv_att = 1.0 / att
    for i in range(n):
        v = absx[i]
        if v > env:
            env += (v - env) * inv_att
        else:
            env += (v - env) * rel
        if env > ceiling:
            g[i] = ceiling / (env + 1e-12)
        else:
            g[i] = 1.0
    return g

def limit_loop_safe(st, ceiling_db=PEAK_DB, attack_ms=1.5, release_ms=80.0):
    ceiling = 10 ** (ceiling_db / 20.0)
    att = max(1, int(attack_ms * 1e-3 * SR))
    rel = np.exp(-1.0 / max(1, release_ms * 1e-3 * SR))
    # wrap pad so the limiter envelope is periodic
    pad = int(0.2 * SR)
    ext = np.concatenate([st[:, -pad:], st, st[:, :pad]], axis=1)
    absx = np.maximum(np.abs(ext[0]), np.abs(ext[1]))
    # lookahead: shift envelope earlier
    la = att
    abs_la = np.concatenate([absx[la:], absx[-1:]])[: len(absx)]
    g = _limiter_gain(abs_la, ceiling, float(att), float(rel))
    # slight smoothing already inherent; apply
    out = ext * g
    return out[:, pad:pad + st.shape[1]]

def normalize_music(st, target=TARGET_LUFS, peak_db=PEAK_DB, loop=False):
    st = dc_block(st, loop=loop)
    # safety clip of wild intermediates before measuring
    p = np.max(np.abs(st)) or 1.0
    if p > 2.5:
        st = st * (2.5 / p)
    lufs = integrated_lufs(st)
    gain = 10 ** ((target - lufs) / 20.0)
    st = st * gain
    peak = true_peak_db(st)
    if peak > peak_db + 0.05:
        st = limit_loop_safe(st, ceiling_db=peak_db - 0.1)
        # re-check integrated (limiter may reduce LUFS slightly)
        lufs2 = integrated_lufs(st)
        if lufs2 < target - 1.5:
            # gentle make-up, then limit again
            st = limit_loop_safe(st * 10 ** ((target - lufs2) / 20.0), ceiling_db=peak_db - 0.1)
    # hard ceiling as last resort
    hard = 10 ** (peak_db / 20.0)
    p = np.max(np.abs(st)) or 1.0
    if p > hard:
        st = st * (hard / p)
    return st, integrated_lufs(st), true_peak_db(st)

# ---------------------------------------------------------------------------
# Mixer / I/O
# ---------------------------------------------------------------------------
class Mixer:
    def __init__(self, dur, loop=True):
        self.n = int(round(dur * SR))
        self.dur = self.n / SR
        self.loop = loop
        self.L = np.zeros(self.n)
        self.R = np.zeros(self.n)

    def add(self, sig, t, pan=0.5, gain=1.0):
        if sig is None or len(sig) == 0 or gain == 0:
            return
        x = np.asarray(sig, dtype=np.float64) * gain
        gL, gR = equal_power(pan)
        start = int(round(t * SR))
        s = len(x)
        if not self.loop:
            if start >= self.n:
                return
            if start < 0:
                x = x[-start:]
                s = len(x)
                start = 0
            end = min(start + s, self.n)
            take = end - start
            self.L[start:end] += x[:take] * gL
            self.R[start:end] += x[:take] * gR
            return
        # wrap
        start %= self.n
        if start + s <= self.n:
            self.L[start:start + s] += x * gL
            self.R[start:start + s] += x * gR
            return
        pos = 0
        idx = start
        while pos < s:
            take = min(self.n - idx, s - pos)
            self.L[idx:idx + take] += x[pos:pos + take] * gL
            self.R[idx:idx + take] += x[pos:pos + take] * gR
            pos += take
            idx = 0

    def add_stereo(self, st, t=0.0, gain=1.0):
        st = np.asarray(st, dtype=np.float64) * gain
        self.add(st[0], t, pan=0.0, gain=1.0)
        self.add(st[1], t, pan=1.0, gain=1.0)

    def stereo(self):
        return np.stack([self.L, self.R])

def write_wav(path, st):
    data = np.clip(st, -1.0, 1.0)
    inter = (data * 32767.0).astype(np.int16).T.reshape(-1)
    with wave.open(path, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(inter.tobytes())

def encode_mp3(wav, mp3):
    subprocess.run(
        [
            "ffmpeg", "-y", "-loglevel", "error",
            "-i", wav,
            "-c:a", "libmp3lame", "-b:a", BITRATE, "-ar", "44100", "-ac", "2",
            mp3,
        ],
        check=True,
    )

def probe_duration(path):
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", path],
        capture_output=True, text=True, check=True,
    )
    return float(r.stdout.strip())

def measure_ffmpeg_lufs(wav):
    r = subprocess.run(
        ["ffmpeg", "-i", wav, "-af", "ebur128=peak=true", "-f", "null", "-"],
        capture_output=True, text=True,
    )
    err = r.stderr
    # parse the Summary block (last Integrated / True peak)
    integ = re.findall(r"I:\s+([-0-9.]+)\s+LUFS", err)
    tpk = re.findall(r"Peak:\s+([-0-9.]+)\s+dBFS", err)
    if not tpk:
        tpk = re.findall(r"True peak:\s+([-0-9.]+)\s+dBTP", err)
    return (float(integ[-1]) if integ else None, float(tpk[-1]) if tpk else None)

# ---------------------------------------------------------------------------
# Sequencing helpers
# ---------------------------------------------------------------------------
def place_koto(mix, events, bpm, rng_seed=0):
    """events: (bar, beat, dur_beats, note, gain, pan, damp, bright, oshi_cents)"""
    for i, ev in enumerate(events):
        bar, beat, dur_b, note, gain, pan = ev[:6]
        damp = ev[6] if len(ev) > 6 else 0.9965
        bright = ev[7] if len(ev) > 7 else 0.62
        oshi = ev[8] if len(ev) > 8 else 0.0
        dur = beat_s(dur_b, bpm)
        sig = ks_pluck(hz(note), max(dur, 0.35), damp=damp, bright=bright,
                       seed=rng_seed + i * 13, oshi=oshi)
        mix.add(sig, at_bar(bar, beat, bpm), pan=pan, gain=gain)

def place_flute(mix, events, bpm, rng_seed=0):
    """events: (bar, beat, dur_beats, note, artic, gain, pan, end_note?)"""
    for i, ev in enumerate(events):
        bar, beat, dur_b, note, artic, gain, pan = ev[:7]
        end = ev[7] if len(ev) > 7 else None
        dur = beat_s(dur_b, bpm)
        # slight natural overlap for legato
        if artic == "legato":
            dur *= 1.05
        end_f = hz(end) if end is not None else None
        sig = shakuhachi(hz(note), dur, artic=artic, seed=rng_seed + i * 19,
                         end_freq=end_f)
        mix.add(sig, at_bar(bar, beat, bpm), pan=pan, gain=gain)

def place_drums(mix, events, bpm, rng_seed=0):
    """events: (bar, beat, kind, gain, pan)"""
    for i, ev in enumerate(events):
        bar, beat, kind, gain = ev[:4]
        pan = ev[4] if len(ev) > 4 else 0.5
        if kind == "wood":
            sig = wood_click(rng_seed + i * 7)
        else:
            sig = taiko(kind, seed=rng_seed + i * 7)
        mix.add(sig, at_bar(bar, beat, bpm), pan=pan, gain=gain)


# ---------------------------------------------------------------------------
# Compositions
# ---------------------------------------------------------------------------
def compose_title():
    """Calm-majestic title. D miyako-bushi (in), 64 BPM, 16 bars = 60 s."""
    bpm, bars = 64, 16
    T = bars * 4 * 60 / bpm
    mix = Mixer(T, loop=True)
    # Low ink-wash drone
    mix.add_stereo(pad_drone(["D2", "A2", "D3"], T, seed=6401, tone="dark", cycles=4, air=0.05), gain=0.95)
    # A quieter fifth colour that breathes in the second half of each 8-bar span
    t = t_(T)
    swell = 0.5 + 0.5 * np.sin(2 * np.pi * 2 * t / T - np.pi / 2)
    color = pad_drone(["Bb2", "F3"], T, seed=6402, tone="dark", cycles=2, air=0.02)
    mix.add_stereo(color * swell, gain=0.28)

    koto = []
    # Opening fifths, very spaced (ma)
    open_pat = [
        (0, 0, 4.0, "D3", 0.55, 0.42, 0.9972, 0.45),
        (0, 3, 3.0, "A3", 0.40, 0.62, 0.9968, 0.55),
        (1, 2, 3.0, "D4", 0.32, 0.55, 0.9965, 0.55),
        (2, 0, 4.0, "G3", 0.48, 0.38, 0.9970, 0.48),
        (2, 2.5, 3.0, "D4", 0.30, 0.65, 0.9965, 0.6),
        (3, 1, 3.0, "A3", 0.36, 0.58, 0.9968, 0.5),
        (3, 3, 2.5, "Bb3", 0.22, 0.48, 0.9960, 0.58, 40),
    ]
    # Mid: more motion, still restrained
    mid_pat = [
        (4, 0, 3.5, "D3", 0.50, 0.40, 0.9972, 0.48),
        (4, 1, 2.5, "A3", 0.28, 0.60, 0.9965, 0.55),
        (4, 2.5, 2.5, "D4", 0.34, 0.52, 0.9966, 0.58),
        (5, 0, 3.0, "G3", 0.42, 0.36, 0.9970, 0.5),
        (5, 2, 2.5, "D4", 0.30, 0.64, 0.9964, 0.6),
        (5, 3.5, 2.0, "A3", 0.24, 0.48, 0.9965, 0.52),
        (6, 0, 3.0, "Bb3", 0.38, 0.44, 0.9966, 0.5),
        (6, 2, 3.0, "A3", 0.34, 0.58, 0.9966, 0.52),
        (6, 3, 2.5, "G3", 0.26, 0.40, 0.9968, 0.48),
        (7, 0, 4.0, "D3", 0.46, 0.42, 0.9972, 0.45),
        (7, 3, 2.5, "A3", 0.28, 0.62, 0.9968, 0.55),
        # 8-11
        (8, 0, 3.0, "D3", 0.44, 0.40, 0.9972, 0.48),
        (8, 2, 2.5, "A3", 0.30, 0.60, 0.9966, 0.55),
        (8, 3.5, 2.0, "D4", 0.26, 0.52, 0.9964, 0.6),
        (9, 1, 3.0, "G4", 0.22, 0.68, 0.9960, 0.65),
        (9, 3, 2.5, "D4", 0.24, 0.36, 0.9964, 0.55),
        (10, 0, 3.0, "Bb3", 0.36, 0.45, 0.9966, 0.5, 30),
        (10, 2, 2.5, "A3", 0.32, 0.58, 0.9966, 0.52),
        (11, 0, 4.0, "D4", 0.30, 0.50, 0.9965, 0.55),
        (11, 2.5, 3.0, "A3", 0.28, 0.40, 0.9968, 0.5),
        # return, leading back into bar 0
        (12, 0, 4.0, "D3", 0.52, 0.42, 0.9972, 0.45),
        (12, 3, 3.0, "A3", 0.38, 0.62, 0.9968, 0.55),
        (13, 2, 3.0, "D4", 0.30, 0.55, 0.9965, 0.55),
        (14, 0, 4.0, "G3", 0.46, 0.38, 0.9970, 0.48),
        (14, 2.5, 3.0, "D4", 0.28, 0.65, 0.9965, 0.6),
        (15, 1, 3.0, "A3", 0.34, 0.58, 0.9968, 0.5),
        (15, 3, 2.5, "D3", 0.40, 0.46, 0.9972, 0.45),
    ]
    koto.extend(open_pat)
    koto.extend(mid_pat)
    place_koto(mix, koto, bpm, rng_seed=6410)

    # Shakuhachi: ink-brush motif, generous rests
    flute = [
        # first statement
        (4, 0, 3.0, "D5", "soft", 0.52, 0.50),
        (4, 3, 1.15, "Eb5", "legato", 0.40, 0.50),
        (5, 0, 2.1, "G5", "norm", 0.48, 0.48),
        (5, 2, 2.1, "A4", "soft", 0.44, 0.52),
        (6, 0, 1.1, "Bb4", "legato", 0.42, 0.50),
        (6, 1, 1.1, "A4", "legato", 0.40, 0.50),
        (6, 2, 2.2, "G4", "norm", 0.46, 0.50),
        (7, 0, 3.8, "D4", "fall", 0.50, 0.50),
        # answer, starting higher then settling
        (10, 0, 2.1, "A4", "soft", 0.44, 0.49),
        (10, 2, 1.05, "Bb4", "legato", 0.40, 0.50),
        (10, 3, 1.15, "D5", "norm", 0.48, 0.50),
        (11, 0, 2.1, "Eb5", "soft", 0.42, 0.51),
        (11, 2, 2.1, "D5", "norm", 0.46, 0.50),
        (12, 0, 3.0, "G5", "norm", 0.48, 0.48),
        (12, 3, 1.15, "A4", "legato", 0.40, 0.52),
        (13, 0, 2.1, "Bb4", "soft", 0.42, 0.50),
        (13, 2, 1.05, "A4", "legato", 0.38, 0.50),
        (13, 3, 1.15, "G4", "norm", 0.40, 0.50),
        (14, 0, 2.1, "D5", "soft", 0.46, 0.50),
        (14, 2, 2.1, "A4", "soft", 0.42, 0.50),
        (15, 0, 2.0, "G4", "fall", 0.40, 0.50),
    ]
    place_flute(mix, flute, bpm, rng_seed=6420)
    return mix.stereo(), dict(bpm=bpm, bars=bars, duration_s=T,
                              key_scale="D miyako-bushi (in)", mood="calm-majestic")


def compose_world():
    """Expansive travelling world map. G yo, 90 BPM, 24 bars = 64 s."""
    bpm, bars = 90, 24
    T = bars * 4 * 60 / bpm
    mix = Mixer(T, loop=True)
    mix.add_stereo(pad_drone(["G2", "D3", "G3"], T, seed=9001, tone="warm", cycles=4, air=0.04), gain=0.82)
    # horizon colour, slightly brighter
    mix.add_stereo(pad_drone(["D3", "A3"], T, seed=9002, tone="bright", cycles=3, air=0.02), gain=0.22)

    koto = []
    # Walking ostinato, 2-bar cell with 8-bar variations
    def ost(bar0, variant=0, g=1.0):
        ev = []
        for b in range(8):
            bar = bar0 + b
            acc = 1.0 if b % 2 == 0 else 0.88
            if variant == 0:
                ev += [
                    (bar, 0.0, 1.6, "G3", 0.42 * g * acc, 0.40, 0.9968, 0.55),
                    (bar, 1.0, 1.2, "D4", 0.28 * g, 0.62, 0.9962, 0.62),
                    (bar, 1.5, 1.2, "E4", 0.24 * g, 0.58, 0.9960, 0.62),
                    (bar, 2.0, 1.6, "C4", 0.32 * g, 0.45, 0.9965, 0.58),
                    (bar, 3.0, 1.2, "A3", 0.26 * g, 0.36, 0.9966, 0.55),
                    (bar, 3.5, 1.2, "D4", 0.22 * g, 0.64, 0.9962, 0.6),
                ]
            elif variant == 1:
                ev += [
                    (bar, 0.0, 1.6, "C3", 0.40 * g * acc, 0.42, 0.9970, 0.5),
                    (bar, 1.0, 1.2, "G3", 0.28 * g, 0.58, 0.9965, 0.58),
                    (bar, 1.5, 1.2, "A3", 0.24 * g, 0.55, 0.9964, 0.58),
                    (bar, 2.0, 1.6, "D4", 0.34 * g, 0.48, 0.9964, 0.6),
                    (bar, 3.0, 1.2, "E4", 0.24 * g, 0.66, 0.9960, 0.65),
                    (bar, 3.5, 1.2, "D4", 0.22 * g, 0.50, 0.9962, 0.6),
                ]
            else:
                ev += [
                    (bar, 0.0, 1.8, "G3", 0.44 * g * acc, 0.40, 0.9968, 0.55),
                    (bar, 1.5, 1.2, "D4", 0.26 * g, 0.62, 0.9962, 0.62),
                    (bar, 2.0, 1.6, "E3", 0.30 * g, 0.38, 0.9970, 0.5),
                    (bar, 3.0, 1.2, "C4", 0.24 * g, 0.58, 0.9964, 0.58),
                    (bar, 3.5, 1.2, "D4", 0.22 * g, 0.52, 0.9962, 0.6),
                ]
            # occasional high sparkle
            if b in (3, 7) and variant != 2:
                ev.append((bar, 2.5, 2.0, "G4", 0.16 * g, 0.72, 0.9958, 0.7))
        return ev

    koto += ost(0, 0, 1.0)
    koto += ost(8, 1, 0.95)
    koto += ost(16, 2, 1.0)
    place_koto(mix, koto, bpm, rng_seed=9010)

    # very soft low pulse on every other downbeat (travelling step, not battle)
    drums = []
    for bar in range(24):
        if bar % 2 == 0:
            drums.append((bar, 0, "don", 0.16 if bar % 8 else 0.22, 0.5))
        if bar % 8 == 7:
            drums.append((bar, 3.0, "ka", 0.10, 0.58))
    place_drums(mix, drums, bpm, rng_seed=9020)

    flute = [
        # A theme (bars 4-7)
        (4, 0, 2.1, "G4", "soft", 0.50, 0.50),
        (4, 2, 1.05, "A4", "legato", 0.44, 0.50),
        (4, 3, 1.15, "C5", "norm", 0.48, 0.50),
        (5, 0, 2.1, "D5", "norm", 0.52, 0.49),
        (5, 2, 1.05, "E5", "legato", 0.46, 0.50),
        (5, 3, 1.15, "D5", "norm", 0.44, 0.50),
        (6, 0, 2.1, "C5", "soft", 0.48, 0.50),
        (6, 2, 2.1, "A4", "soft", 0.44, 0.51),
        (7, 0, 3.2, "G4", "fall", 0.50, 0.50),
        # B, more open (bars 9-15)
        (9, 0, 1.05, "D5", "norm", 0.48, 0.50),
        (9, 1, 1.05, "E5", "legato", 0.46, 0.50),
        (9, 2, 2.2, "G5", "norm", 0.52, 0.48),
        (10, 0, 1.05, "E5", "legato", 0.44, 0.50),
        (10, 1, 1.05, "D5", "legato", 0.42, 0.50),
        (10, 2, 2.2, "C5", "soft", 0.46, 0.50),
        (11, 0, 2.1, "A4", "soft", 0.44, 0.51),
        (11, 2, 1.05, "C5", "legato", 0.42, 0.50),
        (11, 3, 1.15, "D5", "norm", 0.48, 0.50),
        (12, 0, 3.8, "G4", "soft", 0.50, 0.50),
        (13, 2, 1.05, "A4", "soft", 0.36, 0.50),
        (13, 3, 1.15, "C5", "legato", 0.38, 0.50),
        (14, 0, 2.1, "D5", "norm", 0.46, 0.50),
        (14, 2, 2.1, "E5", "soft", 0.42, 0.50),
        (15, 0, 3.6, "D5", "fall", 0.46, 0.50),
        # A' return (bars 18-23)
        (18, 0, 2.1, "G4", "soft", 0.48, 0.50),
        (18, 2, 1.05, "A4", "legato", 0.42, 0.50),
        (18, 3, 1.15, "C5", "norm", 0.46, 0.50),
        (19, 0, 2.1, "D5", "norm", 0.50, 0.49),
        (19, 2, 1.05, "E5", "legato", 0.44, 0.50),
        (19, 3, 1.15, "D5", "norm", 0.42, 0.50),
        (20, 0, 2.1, "C5", "soft", 0.46, 0.50),
        (20, 2, 2.1, "A4", "soft", 0.42, 0.51),
        (21, 0, 2.1, "G4", "norm", 0.48, 0.50),
        (21, 2, 2.1, "D5", "soft", 0.40, 0.50),
        (22, 0, 3.0, "E5", "soft", 0.42, 0.50),
        (22, 3, 1.15, "D5", "legato", 0.38, 0.50),
        (23, 0, 3.0, "G4", "fall", 0.46, 0.50),
    ]
    place_flute(mix, flute, bpm, rng_seed=9030)
    return mix.stereo(), dict(bpm=bpm, bars=bars, duration_s=T,
                              key_scale="G yo", mood="expansive travelling")


def compose_forest():
    """Misty, gentle mystery. E hirajoshi, 60 BPM, 16 bars = 64 s."""
    bpm, bars = 60, 16
    T = bars * 4 * 60 / bpm
    mix = Mixer(T, loop=True)
    mix.add_stereo(pad_drone(["E2", "B2", "E3"], T, seed=6001, tone="mist", cycles=4, air=0.07), gain=0.90)
    # high thin mist
    mix.add_stereo(pad_drone(["E4", "B4"], T, seed=6002, tone="mist", cycles=2, air=0.05), gain=0.18)

    # koto water-drops, irregular, high, quiet
    drops = [
        (0, 2.5, 3.0, "E5", 0.22, 0.68, 0.9958, 0.72),
        (1, 1.0, 3.0, "B4", 0.18, 0.32, 0.9960, 0.65),
        (2, 3.5, 2.5, "G5", 0.16, 0.74, 0.9955, 0.75),
        (3, 0.5, 3.0, "F#4", 0.20, 0.40, 0.9962, 0.58),
        (4, 2.0, 3.0, "E5", 0.20, 0.62, 0.9958, 0.7),
        (5, 0.0, 2.5, "C5", 0.15, 0.30, 0.9960, 0.68),
        (5, 3.0, 2.5, "B4", 0.17, 0.70, 0.9960, 0.65),
        (6, 1.5, 3.0, "G4", 0.18, 0.45, 0.9964, 0.55),
        (7, 3.0, 3.0, "E5", 0.16, 0.58, 0.9958, 0.72),
        (8, 1.0, 3.0, "B5", 0.14, 0.78, 0.9954, 0.78),
        (9, 2.5, 2.5, "G5", 0.15, 0.28, 0.9956, 0.74),
        (10, 0.0, 3.0, "E4", 0.20, 0.42, 0.9966, 0.5),
        (10, 3.5, 2.5, "F#5", 0.14, 0.66, 0.9956, 0.72),
        (12, 1.5, 3.0, "B4", 0.18, 0.36, 0.9960, 0.62),
        (13, 0.0, 3.0, "E5", 0.20, 0.60, 0.9958, 0.7),
        (14, 2.0, 3.0, "C5", 0.15, 0.48, 0.9960, 0.66),
        (15, 3.0, 2.5, "B4", 0.16, 0.55, 0.9960, 0.62),
    ]
    place_koto(mix, drops, bpm, rng_seed=6010)

    # a few deeper strings, like damp earth
    low = [
        (0, 0, 6.0, "E3", 0.28, 0.48, 0.9976, 0.35),
        (4, 0, 6.0, "B2", 0.24, 0.50, 0.9978, 0.32),
        (8, 0, 6.0, "E3", 0.26, 0.47, 0.9976, 0.35),
        (12, 0, 6.0, "G3", 0.22, 0.52, 0.9974, 0.36),
        (14, 0, 5.0, "E3", 0.24, 0.49, 0.9976, 0.34),
    ]
    place_koto(mix, low, bpm, rng_seed=6015)

    flute = [
        (2, 0, 4.0, "E4", "soft", 0.48, 0.50),
        (4, 0, 2.1, "B4", "soft", 0.44, 0.49),
        (4, 2, 1.05, "C5", "legato", 0.36, 0.50),
        (4, 3, 1.15, "B4", "soft", 0.38, 0.50),
        (5, 0, 2.1, "G4", "soft", 0.42, 0.50),
        (5, 2, 2.1, "F#4", "soft", 0.40, 0.50),
        (6, 0, 4.0, "E4", "fall", 0.46, 0.50),
        (9, 0, 1.1, "C5", "soft", 0.36, 0.51),
        (9, 1, 3.0, "B4", "soft", 0.42, 0.50),
        (10, 0, 2.1, "G4", "soft", 0.40, 0.50),
        (10, 2, 2.1, "B4", "soft", 0.38, 0.50),
        (11, 0, 2.1, "F#4", "soft", 0.40, 0.50),
        (11, 2, 2.1, "E4", "fall", 0.44, 0.50),
        (13, 0, 2.1, "E5", "soft", 0.34, 0.48),
        (13, 2, 1.05, "F#5", "legato", 0.30, 0.50),
        (13, 3, 1.15, "G5", "soft", 0.32, 0.52),
        (14, 0, 4.0, "B4", "soft", 0.38, 0.50),
        (15, 0, 3.2, "E4", "fall", 0.42, 0.50),
    ]
    place_flute(mix, flute, bpm, rng_seed=6020)
    return mix.stereo(), dict(bpm=bpm, bars=bars, duration_s=T,
                              key_scale="E hirajoshi", mood="misty, gentle mystery")


def compose_town():
    """Warm, lively but calm town. D yo, 96 BPM, 24 bars = 60 s."""
    bpm, bars = 96, 24
    T = bars * 4 * 60 / bpm
    mix = Mixer(T, loop=True)
    mix.add_stereo(pad_drone(["D2", "A2", "D3"], T, seed=9601, tone="warm", cycles=4, air=0.035), gain=0.80)
    mix.add_stereo(pad_drone(["A3", "E3"], T, seed=9602, tone="warm", cycles=3, air=0.015), gain=0.16)

    koto = []
    def ost(bar0, g=1.0, mode=0):
        ev = []
        for b in range(8):
            bar = bar0 + b
            acc = 1.05 if b % 4 == 0 else 0.92
            if mode == 0:
                ev += [
                    (bar, 0.0, 1.4, "D4", 0.40 * g * acc, 0.44, 0.9964, 0.62),
                    (bar, 1.0, 1.0, "A3", 0.26 * g, 0.36, 0.9966, 0.55),
                    (bar, 1.5, 1.0, "D4", 0.24 * g, 0.50, 0.9964, 0.6),
                    (bar, 2.0, 1.4, "E4", 0.32 * g, 0.60, 0.9962, 0.65),
                    (bar, 3.0, 1.0, "G4", 0.22 * g, 0.68, 0.9960, 0.68),
                    (bar, 3.5, 1.0, "E4", 0.20 * g, 0.55, 0.9962, 0.62),
                ]
            else:
                ev += [
                    (bar, 0.0, 1.4, "G3", 0.38 * g * acc, 0.40, 0.9966, 0.55),
                    (bar, 1.0, 1.0, "D4", 0.26 * g, 0.58, 0.9963, 0.62),
                    (bar, 1.5, 1.0, "E4", 0.22 * g, 0.62, 0.9962, 0.65),
                    (bar, 2.0, 1.4, "A3", 0.30 * g, 0.38, 0.9966, 0.55),
                    (bar, 3.0, 1.0, "B3", 0.22 * g, 0.52, 0.9964, 0.58),
                    (bar, 3.5, 1.0, "D4", 0.20 * g, 0.48, 0.9964, 0.6),
                ]
            if b % 4 == 3:
                ev.append((bar, 2.5, 1.8, "A4", 0.16 * g, 0.74, 0.9958, 0.72, 40))
        return ev

    koto += ost(0, 1.0, 0)
    koto += ost(8, 0.95, 1)
    koto += ost(16, 1.0, 0)
    # low open string on downbeats of each 2-bar group
    for bar in range(0, 24, 2):
        koto.append((bar, 0, 3.0, "D3", 0.30, 0.48, 0.9972, 0.4))
    place_koto(mix, koto, bpm, rng_seed=9610)

    drums = []
    for bar in range(24):
        drums.append((bar, 1.0, "wood", 0.18 if bar % 2 else 0.14, 0.62))
        drums.append((bar, 3.0, "wood", 0.16, 0.38))
        if bar % 4 == 0:
            drums.append((bar, 0.0, "don", 0.14, 0.50))
        if bar % 8 == 7:
            drums.append((bar, 3.5, "wood", 0.14, 0.55))
    place_drums(mix, drums, bpm, rng_seed=9620)

    flute = [
        (2, 0, 1.05, "A4", "norm", 0.46, 0.50),
        (2, 1, 1.05, "B4", "legato", 0.42, 0.50),
        (2, 2, 2.15, "D5", "norm", 0.50, 0.50),
        (3, 0, 1.05, "E5", "norm", 0.46, 0.49),
        (3, 1, 0.55, "D5", "legato", 0.40, 0.50),
        (3, 1.5, 0.55, "B4", "legato", 0.38, 0.50),
        (3, 2, 2.1, "A4", "soft", 0.44, 0.50),
        (4, 0, 1.05, "G4", "soft", 0.40, 0.50),
        (4, 1, 1.05, "A4", "legato", 0.40, 0.50),
        (4, 2, 2.15, "B4", "norm", 0.46, 0.50),
        (5, 0, 3.6, "A4", "soft", 0.48, 0.50),
        # mid phrase
        (8, 0, 1.05, "D5", "norm", 0.46, 0.50),
        (8, 1, 1.05, "E5", "legato", 0.44, 0.50),
        (8, 2, 1.05, "G5", "norm", 0.48, 0.48),
        (8, 3, 1.15, "E5", "legato", 0.42, 0.50),
        (9, 0, 2.1, "D5", "soft", 0.46, 0.50),
        (9, 2, 2.1, "B4", "soft", 0.42, 0.51),
        (10, 0, 1.05, "A4", "norm", 0.42, 0.50),
        (10, 1, 1.05, "G4", "legato", 0.38, 0.50),
        (10, 2, 2.15, "A4", "soft", 0.44, 0.50),
        (11, 0, 3.6, "D5", "fall", 0.46, 0.50),
        # closing return
        (16, 0, 1.05, "A4", "norm", 0.44, 0.50),
        (16, 1, 1.05, "B4", "legato", 0.40, 0.50),
        (16, 2, 2.15, "D5", "norm", 0.48, 0.50),
        (17, 0, 1.05, "E5", "norm", 0.44, 0.49),
        (17, 1, 0.55, "D5", "legato", 0.38, 0.50),
        (17, 1.5, 0.55, "B4", "legato", 0.36, 0.50),
        (17, 2, 2.1, "A4", "soft", 0.42, 0.50),
        (18, 0, 2.1, "G4", "soft", 0.40, 0.50),
        (18, 2, 2.1, "A4", "soft", 0.42, 0.50),
        (19, 0, 3.6, "D4", "fall", 0.48, 0.50),
        (21, 0, 1.05, "B4", "soft", 0.36, 0.50),
        (21, 1, 1.05, "A4", "legato", 0.36, 0.50),
        (21, 2, 2.1, "G4", "soft", 0.38, 0.50),
        (22, 0, 3.8, "A4", "soft", 0.42, 0.50),
    ]
    place_flute(mix, flute, bpm, rng_seed=9630)
    return mix.stereo(), dict(bpm=bpm, bars=bars, duration_s=T,
                              key_scale="D yo", mood="warm, lively but calm")


def compose_battle():
    """Driving taiko, urgent koto / shakuhachi. A miyako-bushi, 128 BPM, 32 bars = 60 s."""
    bpm, bars = 128, 32
    T = bars * 4 * 60 / bpm
    mix = Mixer(T, loop=True)
    mix.add_stereo(pad_drone(["A1", "A2", "E2"], T, seed=12801, tone="tense", cycles=8, air=0.03), gain=0.72)
    # restless fifth, slightly more present in "B" section via... just leave constant, arrangement carries energy

    # taiko: 8-bar cycle, last bar is a fill into the next (and into the loop)
    drums = []
    for bar in range(32):
        b = bar % 8
        # dynamic: slightly hotter in bars 16-23
        hot = 1.12 if 16 <= bar < 24 else 1.0
        if b == 7:
            drums += [
                (bar, 0.0, "don", 1.00 * hot, 0.50),
                (bar, 1.0, "ka", 0.70 * hot, 0.62),
                (bar, 1.5, "ka", 0.62 * hot, 0.38),
                (bar, 2.0, "chu", 0.88 * hot, 0.50),
                (bar, 3.0, "ka", 0.68 * hot, 0.58),
                (bar, 3.5, "ka", 0.80 * hot, 0.42),
            ]
        elif b % 2 == 0:
            drums += [
                (bar, 0.0, "don", 1.00 * hot, 0.50),
                (bar, 2.0, "don", 0.78 * hot, 0.50),
                (bar, 3.0, "ka", 0.66 * hot, 0.60),
            ]
            if b == 4:
                drums.append((bar, 1.5, "ka", 0.50 * hot, 0.40))
        else:
            drums += [
                (bar, 0.0, "don", 0.95 * hot, 0.50),
                (bar, 1.5, "ka", 0.60 * hot, 0.36),
                (bar, 2.0, "don", 0.82 * hot, 0.50),
                (bar, 3.0, "ka", 0.55 * hot, 0.62),
                (bar, 3.5, "ka", 0.70 * hot, 0.40),
            ]
    place_drums(mix, drums, bpm, rng_seed=12810)

    koto = []
    for bar in range(32):
        b = bar % 4
        g = 1.08 if 16 <= bar < 24 else 1.0
        # syncopated urgent cell
        if b == 0:
            koto += [
                (bar, 0.0, 1.1, "A3", 0.48 * g, 0.40, 0.9960, 0.62),
                (bar, 1.0, 0.8, "E4", 0.34 * g, 0.62, 0.9958, 0.68),
                (bar, 1.5, 0.8, "F4", 0.30 * g, 0.58, 0.9958, 0.68),
                (bar, 2.5, 0.8, "E4", 0.28 * g, 0.52, 0.9958, 0.65),
                (bar, 3.0, 1.0, "Bb3", 0.32 * g, 0.36, 0.9962, 0.58),
            ]
        elif b == 1:
            koto += [
                (bar, 0.0, 1.1, "A3", 0.46 * g, 0.42, 0.9960, 0.62),
                (bar, 0.5, 0.7, "D4", 0.26 * g, 0.55, 0.9958, 0.65),
                (bar, 1.5, 0.8, "E4", 0.32 * g, 0.64, 0.9958, 0.68),
                (bar, 2.5, 0.8, "F4", 0.28 * g, 0.48, 0.9958, 0.66),
                (bar, 3.5, 0.8, "E4", 0.24 * g, 0.60, 0.9956, 0.7),
            ]
        elif b == 2:
            koto += [
                (bar, 0.0, 1.1, "D3", 0.44 * g, 0.38, 0.9964, 0.55),
                (bar, 1.0, 0.8, "A3", 0.32 * g, 0.50, 0.9960, 0.6),
                (bar, 1.5, 0.8, "Bb3", 0.28 * g, 0.44, 0.9960, 0.6),
                (bar, 2.5, 0.8, "D4", 0.30 * g, 0.62, 0.9958, 0.68),
                (bar, 3.0, 1.0, "E4", 0.28 * g, 0.58, 0.9958, 0.66),
            ]
        else:
            koto += [
                (bar, 0.0, 1.1, "A3", 0.46 * g, 0.40, 0.9960, 0.62),
                (bar, 1.0, 0.8, "E4", 0.30 * g, 0.62, 0.9958, 0.68),
                (bar, 2.0, 0.8, "F4", 0.28 * g, 0.55, 0.9958, 0.66),
                (bar, 3.0, 0.7, "E4", 0.26 * g, 0.48, 0.9958, 0.65),
                (bar, 3.5, 0.8, "A4", 0.22 * g, 0.70, 0.9955, 0.75),
            ]
        # low tonic every bar
        koto.append((bar, 0.0, 2.0, "A2", 0.36 * g, 0.50, 0.9970, 0.35))
    place_koto(mix, koto, bpm, rng_seed=12820)

    flute = [
        # short urgent calls with space for taiko
        (2, 0, 0.55, "A5", "accent", 0.50, 0.50),
        (2, 0.5, 0.55, "Bb5", "legato", 0.42, 0.50),
        (2, 1.0, 1.05, "A5", "norm", 0.48, 0.50),
        (2, 2.0, 1.05, "F5", "norm", 0.46, 0.50),
        (2, 3.0, 1.1, "E5", "fall", 0.44, 0.50),
        (4, 0, 0.55, "D5", "accent", 0.46, 0.50),
        (4, 0.5, 0.55, "E5", "legato", 0.42, 0.50),
        (4, 1.0, 1.05, "F5", "norm", 0.48, 0.50),
        (4, 2.0, 0.55, "E5", "legato", 0.42, 0.50),
        (4, 2.5, 0.55, "D5", "legato", 0.40, 0.50),
        (4, 3.0, 1.1, "Bb4", "fall", 0.44, 0.50),
        (8, 0, 2.1, "A5", "accent", 0.52, 0.49),
        (8, 2, 1.05, "F5", "norm", 0.44, 0.50),
        (8, 3, 1.15, "E5", "fall", 0.46, 0.50),
        (10, 0, 0.55, "D5", "accent", 0.44, 0.50),
        (10, 0.5, 1.05, "E5", "norm", 0.46, 0.50),
        (10, 2.0, 2.1, "A4", "fall", 0.44, 0.50),
        # mid: held tension
        (16, 0, 3.0, "A5", "accent", 0.54, 0.50),
        (16, 3, 1.15, "Bb5", "legato", 0.46, 0.50),
        (17, 0, 2.1, "A5", "norm", 0.50, 0.50),
        (17, 2, 2.1, "F5", "fall", 0.48, 0.50),
        (20, 0, 1.05, "E5", "accent", 0.48, 0.50),
        (20, 1, 1.05, "F5", "legato", 0.44, 0.50),
        (20, 2, 2.15, "A5", "norm", 0.52, 0.49),
        (21, 0, 2.1, "E5", "norm", 0.46, 0.50),
        (21, 2, 2.1, "D5", "fall", 0.46, 0.50),
        # return
        (24, 0, 0.55, "A5", "accent", 0.50, 0.50),
        (24, 0.5, 0.55, "Bb5", "legato", 0.42, 0.50),
        (24, 1.0, 1.05, "A5", "norm", 0.48, 0.50),
        (24, 2.0, 1.05, "F5", "norm", 0.46, 0.50),
        (24, 3.0, 1.1, "E5", "fall", 0.44, 0.50),
        (26, 0, 0.55, "D5", "accent", 0.46, 0.50),
        (26, 0.5, 0.55, "E5", "legato", 0.42, 0.50),
        (26, 1.0, 1.05, "F5", "norm", 0.48, 0.50),
        (26, 2.0, 2.1, "A5", "norm", 0.50, 0.50),
        (28, 0, 2.1, "E5", "norm", 0.46, 0.50),
        (28, 2, 2.1, "D5", "soft", 0.42, 0.50),
        (30, 0, 2.0, "Bb4", "soft", 0.40, 0.50),
        (30, 2, 1.8, "A4", "fall", 0.44, 0.50),
    ]
    place_flute(mix, flute, bpm, rng_seed=12830)
    return mix.stereo(), dict(bpm=bpm, bars=bars, duration_s=T,
                              key_scale="A miyako-bushi (in)", mood="driving, urgent")


def compose_transform_sting():
    """Rising 4.2 s one-shot. Musical crest at 2.40 s to sit on inkwing.mp3's impact."""
    dur = 4.2
    mix = Mixer(dur + 0.6, loop=False)  # extra room for decay, trimmed later
    # swelling tense drone
    t = t_(dur + 0.6)
    n = len(t)
    swell = np.clip(t / 2.40, 0, 1) ** 1.15
    swell = np.minimum(swell, np.clip((dur + 0.15 - t) / 1.6, 0, 1))
    pad = pad_drone(["A2", "E3", "A3"], dur + 0.6, seed=2401, tone="tense", cycles=2, air=0.04)
    # pad_drone normalizes; apply swell
    mix.add_stereo(pad * swell, gain=1.05)

    # rising koto run, accelerating into 2.4 s
    # times chosen to land a bright chord at 2.40
    run = [
        # (t, note, gain, pan, dur)
        (0.12, "A3", 0.30, 0.40, 0.8),
        (0.28, "Bb3", 0.32, 0.60, 0.8),
        (0.44, "D4", 0.34, 0.35, 0.8),
        (0.58, "E4", 0.36, 0.65, 0.8),
        (0.72, "F4", 0.38, 0.38, 0.7),
        (0.86, "A4", 0.40, 0.62, 0.7),
        (0.98, "Bb4", 0.42, 0.40, 0.7),
        (1.10, "D5", 0.44, 0.60, 0.7),
        (1.22, "E5", 0.46, 0.42, 0.65),
        (1.32, "F5", 0.48, 0.58, 0.65),
        (1.42, "G5", 0.50, 0.36, 0.65),  # lift out of the in-scale toward open colour
        (1.52, "A5", 0.52, 0.64, 0.6),
        (1.62, "Bb5", 0.50, 0.45, 0.6),
        (1.72, "D6", 0.48, 0.55, 0.55),
        (1.82, "E6", 0.46, 0.40, 0.55),
        (1.92, "F6", 0.44, 0.60, 0.5),
        (2.02, "G6", 0.42, 0.50, 0.5),
    ]
    for i, (tt, note, g, pan, d) in enumerate(run):
        sig = ks_pluck(hz(note), d, damp=0.9955, bright=0.75, seed=2410 + i)
        mix.add(sig, tt, pan=pan, gain=g * 0.7)

    # crest chord at 2.40: open D-A-D (transformation opening the ink)
    for note, g, pan in (("D4", 0.55, 0.35), ("A4", 0.60, 0.50),
                         ("D5", 0.70, 0.50), ("A5", 0.50, 0.65),
                         ("D6", 0.42, 0.55)):
        sig = ks_pluck(hz(note), 1.8, damp=0.9970, bright=0.7, seed=2450 + midi_of(note))
        mix.add(sig, 2.40, pan=pan, gain=g * 0.85)

    # shakuhachi rise, peak at 2.4
    # 0.15 start, long rising phrase
    f0, f1 = hz("A4"), hz("D6")
    flute = shakuhachi(f0, 2.45, artic="accent", seed=2460, end_freq=f1, vib_depth=8)
    # extra rise envelope
    fe = np.linspace(0.45, 1.0, len(flute)) ** 0.8
    mix.add(flute * fe, 0.12, pan=0.5, gain=0.55)
    # hold the crest note
    hold = shakuhachi(hz("D6"), 1.7, artic="fall", seed=2461, vib_depth=14)
    mix.add(hold, 2.40, pan=0.5, gain=0.58)

    # soft mid tom at 2.40 — not a boom (inkwing carries the whoosh impact)
    mix.add(taiko("chu", seed=2470), 2.40, pan=0.5, gain=0.28)
    # after-ripple koto
    for i, (tt, note, g, pan) in enumerate([
        (2.55, "A5", 0.28, 0.70),
        (2.68, "F5", 0.24, 0.30),
        (2.84, "E5", 0.22, 0.62),
        (3.02, "D5", 0.26, 0.48),
        (3.25, "A4", 0.22, 0.40),
        (3.50, "D4", 0.20, 0.52),
    ]):
        sig = ks_pluck(hz(note), 1.1, damp=0.9964, bright=0.6, seed=2480 + i)
        mix.add(sig, tt, pan=pan, gain=g)

    st = mix.stereo()
    # trim to 4.2 s with a short natural tail already inside
    n = int(round(4.2 * SR))
    st = st[:, :n]
    # ensure end is faded
    fo = int(0.25 * SR)
    fade = np.linspace(1, 0, fo)
    st[:, -fo:] *= fade
    fi = int(0.008 * SR)
    st[:, :fi] *= np.linspace(0, 1, fi)
    return st, dict(bpm=None, bars=None, duration_s=4.2,
                    key_scale="A miyako-bushi rising to D yo",
                    mood="rising transformation sting, crest at 2.40 s")


def compose_victory_fanfare():
    """Bright 8 s one-shot in G yo."""
    dur = 8.0
    mix = Mixer(dur + 0.4, loop=False)
    t = t_(dur + 0.4)
    env = np.clip((dur - 0.15 - t) / 2.2, 0, 1)
    env = np.minimum(env, np.clip(t / 0.12, 0, 1))
    pad = pad_drone(["G2", "D3", "G3"], dur + 0.4, seed=8001, tone="bright", cycles=2, air=0.03)
    mix.add_stereo(pad * env, gain=0.85)

    mix.add(taiko("don", seed=8010), 0.00, pan=0.5, gain=0.85)
    mix.add(taiko("ka", seed=8011), 0.12, pan=0.62, gain=0.35)
    mix.add(taiko("chu", seed=8012), 3.20, pan=0.5, gain=0.40)
    mix.add(taiko("don", seed=8013), 6.10, pan=0.5, gain=0.55)

    run = [
        (0.00, "G3", 0.50, 0.40),
        (0.09, "A3", 0.48, 0.60),
        (0.18, "C4", 0.50, 0.35),
        (0.27, "D4", 0.52, 0.65),
        (0.36, "E4", 0.54, 0.38),
        (0.45, "G4", 0.56, 0.62),
        (0.54, "A4", 0.58, 0.42),
        (0.64, "C5", 0.60, 0.58),
        (0.74, "D5", 0.62, 0.50),
        (0.86, "G5", 0.64, 0.50),
    ]
    for i, (tt, note, g, pan) in enumerate(run):
        sig = ks_pluck(hz(note), 1.4, damp=0.9966, bright=0.72, seed=8020 + i)
        mix.add(sig, tt, pan=pan, gain=g * 0.7)
    # open cadence chord
    for tt, notes in (
        (0.86, (("G3", 0.5, 0.4), ("D4", 0.55, 0.5), ("G4", 0.6, 0.55), ("D5", 0.5, 0.6))),
        (3.20, (("E3", 0.4, 0.4), ("C4", 0.45, 0.5), ("G4", 0.5, 0.55), ("C5", 0.45, 0.6))),
        (6.10, (("G3", 0.55, 0.4), ("D4", 0.55, 0.5), ("G4", 0.6, 0.5), ("B4", 0.4, 0.62), ("D5", 0.5, 0.58))),
    ):
        for note, g, pan in notes:
            sig = ks_pluck(hz(note), 2.2, damp=0.9972, bright=0.62, seed=8040 + midi_of(note) + int(tt * 10))
            mix.add(sig, tt, pan=pan, gain=g * 0.7)

    flute = [
        # using absolute times via a tiny helper: we'll place manually
    ]
    phrases = [
        (0.40, "G4", 0.55, "accent", 0.50),
        (0.95, "A4", 0.50, "legato", 0.48),
        (1.40, "C5", 0.70, "norm", 0.52),
        (2.10, "D5", 0.70, "norm", 0.54),
        (2.80, "G5", 1.40, "norm", 0.56),
        (4.20, "E5", 0.55, "norm", 0.48),
        (4.75, "D5", 0.50, "legato", 0.46),
        (5.25, "C5", 0.55, "legato", 0.44),
        (5.80, "D5", 0.50, "norm", 0.48),
        (6.30, "G5", 1.50, "fall", 0.54),
    ]
    for i, (tt, note, d, artic, g) in enumerate(phrases):
        sig = shakuhachi(hz(note), d, artic=artic, seed=8060 + i, vib_depth=10)
        mix.add(sig, tt, pan=0.5, gain=g)

    st = mix.stereo()
    n = int(round(8.0 * SR))
    st = st[:, :n]
    fo = int(0.35 * SR)
    st[:, -fo:] *= np.linspace(1, 0, fo)
    fi = int(0.006 * SR)
    st[:, :fi] *= np.linspace(0, 1, fi)
    return st, dict(bpm=None, bars=None, duration_s=8.0,
                    key_scale="G yo", mood="bright victory fanfare")


def compose_victory_loop():
    """Gentle post-fanfare loop. G yo, 100 BPM, 16 bars = 38.4 s."""
    bpm, bars = 100, 16
    T = bars * 4 * 60 / bpm
    mix = Mixer(T, loop=True)
    mix.add_stereo(pad_drone(["G2", "D3", "G3"], T, seed=10001, tone="bright", cycles=4, air=0.03), gain=0.78)

    koto = []
    for bar in range(16):
        acc = 1.05 if bar % 4 == 0 else 0.9
        koto += [
            (bar, 0.0, 1.6, "G3", 0.40 * acc, 0.42, 0.9968, 0.55),
            (bar, 1.0, 1.2, "D4", 0.26, 0.60, 0.9964, 0.62),
            (bar, 2.0, 1.6, "E4" if bar % 8 < 4 else "C4", 0.30, 0.52, 0.9964, 0.6),
            (bar, 3.0, 1.2, "D4", 0.24, 0.48, 0.9964, 0.6),
            (bar, 3.5, 1.2, "G4" if bar % 2 == 0 else "A4", 0.18, 0.68, 0.9960, 0.7),
        ]
        if bar % 4 == 0:
            koto.append((bar, 0.0, 3.5, "G2", 0.32, 0.50, 0.9974, 0.35))
    place_koto(mix, koto, bpm, rng_seed=10010)

    drums = []
    for bar in range(16):
        if bar % 2 == 0:
            drums.append((bar, 0, "don", 0.18, 0.50))
        drums.append((bar, 2.0, "wood", 0.10, 0.58))
    place_drums(mix, drums, bpm, rng_seed=10020)

    flute = [
        (2, 0, 2.1, "G4", "soft", 0.46, 0.50),
        (2, 2, 1.05, "A4", "legato", 0.40, 0.50),
        (2, 3, 1.15, "C5", "norm", 0.44, 0.50),
        (3, 0, 2.1, "D5", "norm", 0.48, 0.50),
        (3, 2, 2.1, "G5", "soft", 0.46, 0.50),
        (4, 0, 2.1, "E5", "soft", 0.42, 0.50),
        (4, 2, 2.1, "D5", "soft", 0.42, 0.50),
        (5, 0, 3.6, "G4", "fall", 0.44, 0.50),
        (8, 0, 1.05, "D5", "norm", 0.44, 0.50),
        (8, 1, 1.05, "E5", "legato", 0.42, 0.50),
        (8, 2, 2.15, "G5", "norm", 0.48, 0.50),
        (9, 0, 2.1, "E5", "soft", 0.42, 0.50),
        (9, 2, 2.1, "D5", "soft", 0.40, 0.50),
        (10, 0, 2.1, "C5", "soft", 0.40, 0.50),
        (10, 2, 2.1, "A4", "soft", 0.38, 0.50),
        (11, 0, 3.6, "G4", "fall", 0.44, 0.50),
        (13, 0, 2.1, "A4", "soft", 0.36, 0.50),
        (13, 2, 2.1, "C5", "soft", 0.38, 0.50),
        (14, 0, 3.8, "D5", "soft", 0.42, 0.50),
        (15, 0, 3.0, "G4", "fall", 0.40, 0.50),
    ]
    place_flute(mix, flute, bpm, rng_seed=10030)
    return mix.stereo(), dict(bpm=bpm, bars=bars, duration_s=T,
                              key_scale="G yo", mood="gentle victory loop")


def compose_shop():
    """Gentle cozy shop tune. F yo, 80 BPM, 16 bars = 48 s."""
    bpm, bars = 80, 16
    T = bars * 4 * 60 / bpm
    mix = Mixer(T, loop=True)
    mix.add_stereo(pad_drone(["F2", "C3", "F3"], T, seed=80001, tone="warm", cycles=4, air=0.04), gain=0.88)

    koto = []
    for bar in range(16):
        acc = 1.06 if bar % 4 == 0 else 0.9
        # cozy 3-note groupings, intimate mid register
        pat = [
            (0.0, "F3", 0.40 * acc, 0.44, 1.8),
            (1.0, "C4", 0.26, 0.60, 1.2),
            (1.5, "F4", 0.24, 0.55, 1.2),
            (2.0, "G3" if bar % 4 < 2 else "Bb3", 0.32, 0.38, 1.6),
            (3.0, "D4", 0.22, 0.64, 1.2),
            (3.5, "C4", 0.20, 0.50, 1.2),
        ]
        if bar % 8 >= 4:
            pat = [
                (0.0, "Bb3", 0.38 * acc, 0.42, 1.8),
                (1.0, "F4", 0.26, 0.62, 1.2),
                (1.5, "D4", 0.24, 0.52, 1.2),
                (2.0, "C4", 0.32, 0.40, 1.6),
                (3.0, "G3", 0.22, 0.36, 1.2),
                (3.5, "F3", 0.22, 0.48, 1.2),
            ]
        for beat, note, g, pan, d in pat:
            koto.append((bar, beat, d, note, g, pan, 0.9968, 0.52))
        if bar % 4 == 0:
            koto.append((bar, 0.0, 4.0, "F2", 0.28, 0.50, 0.9976, 0.32))
        if bar % 8 == 3:
            koto.append((bar, 2.5, 2.2, "A4", 0.14, 0.72, 0.9960, 0.7, 30))  # A is not in F yo? F yo is F G Bb C D. No A!
            # fix: use D5 or G4
    # fix the accidental A4 — replace last added if any; we'll just not use A. Rebuild that ornament:
    koto = [e for e in koto if not (len(e) > 8 and e[3] == "A4")]
    for bar in range(3, 16, 8):
        koto.append((bar, 2.5, 2.2, "D5", 0.14, 0.72, 0.9960, 0.7, 30))
    place_koto(mix, koto, bpm, rng_seed=80010)

    # almost no drums — one very soft wood on beat 3 every other bar
    drums = [(bar, 3.0, "wood", 0.08, 0.58) for bar in range(0, 16, 2)]
    place_drums(mix, drums, bpm, rng_seed=80020)

    flute = [
        (3, 0, 2.1, "F4", "soft", 0.40, 0.50),
        (3, 2, 1.05, "G4", "legato", 0.34, 0.50),
        (3, 3, 1.15, "Bb4", "soft", 0.36, 0.50),
        (4, 0, 2.1, "C5", "soft", 0.38, 0.50),
        (4, 2, 2.1, "G4", "soft", 0.34, 0.50),
        (5, 0, 3.8, "F4", "fall", 0.40, 0.50),
        (8, 0, 2.1, "D5", "soft", 0.34, 0.50),
        (8, 2, 2.1, "C5", "soft", 0.34, 0.50),
        (9, 0, 2.1, "Bb4", "soft", 0.32, 0.50),
        (9, 2, 2.1, "G4", "soft", 0.32, 0.50),
        (10, 0, 3.8, "F4", "fall", 0.38, 0.50),
        (13, 0, 2.1, "G4", "soft", 0.32, 0.50),
        (13, 2, 2.1, "Bb4", "soft", 0.32, 0.50),
        (14, 0, 2.1, "C5", "soft", 0.34, 0.50),
        (14, 2, 2.1, "D5", "soft", 0.30, 0.50),
        (15, 0, 3.2, "F4", "fall", 0.36, 0.50),
    ]
    place_flute(mix, flute, bpm, rng_seed=80030)
    return mix.stereo(), dict(bpm=bpm, bars=bars, duration_s=T,
                              key_scale="F yo", mood="gentle, cozy shop")


# ---------------------------------------------------------------------------
# Render pipeline
# ---------------------------------------------------------------------------
TRACKS = [
    dict(key="title", file="title.mp3", loop=True, fn=compose_title,
         reverb=dict(wet=0.38, room=0.86, damp=0.28, tail_s=3.2)),
    dict(key="world", file="world.mp3", loop=True, fn=compose_world,
         reverb=dict(wet=0.34, room=0.84, damp=0.30, tail_s=3.0)),
    dict(key="forest", file="forest.mp3", loop=True, fn=compose_forest,
         reverb=dict(wet=0.40, room=0.88, damp=0.36, tail_s=3.4)),
    dict(key="town", file="town.mp3", loop=True, fn=compose_town,
         reverb=dict(wet=0.24, room=0.76, damp=0.32, tail_s=2.2)),
    dict(key="battle", file="battle.mp3", loop=True, fn=compose_battle,
         reverb=dict(wet=0.22, room=0.74, damp=0.28, tail_s=2.0)),
    dict(key="extra-transform-sting", file="extra-transform-sting.mp3", loop=False,
         fn=compose_transform_sting, reverb=dict(wet=0.36, room=0.84, damp=0.28, tail_s=1.6)),
    dict(key="extra-victory-fanfare", file="extra-victory-fanfare.mp3", loop=False,
         fn=compose_victory_fanfare, reverb=dict(wet=0.30, room=0.80, damp=0.28, tail_s=2.0)),
    dict(key="extra-victory-loop", file="extra-victory-loop.mp3", loop=True,
         fn=compose_victory_loop, reverb=dict(wet=0.28, room=0.80, damp=0.30, tail_s=2.4)),
    dict(key="extra-shop", file="extra-shop.mp3", loop=True, fn=compose_shop,
         reverb=dict(wet=0.20, room=0.72, damp=0.34, tail_s=1.8)),
]


def silent_gaps(st, win_s=1.0, thr_db=-46):
    """Return list of (start_s, end_s) windows quieter than thr_db RMS."""
    w = int(win_s * SR)
    hop = w // 2
    thr = 10 ** (thr_db / 20.0)
    gaps = []
    i = 0
    n = st.shape[1]
    while i + w <= n:
        rms = float(np.sqrt(np.mean(st[:, i:i + w] ** 2)))
        if rms < thr:
            t0, t1 = i / SR, (i + w) / SR
            if gaps and t0 <= gaps[-1][1] + 1e-6:
                gaps[-1] = (gaps[-1][0], t1)
            else:
                gaps.append((t0, t1))
        i += hop
    return gaps


def render_track(spec, outdir):
    key = spec["key"]
    print(f"==> composing {key} ...", flush=True)
    dry, meta = spec["fn"]()
    loop = spec["loop"]
    rv = spec["reverb"]
    print(f"    dry {dry.shape[1]/SR:.3f}s  peak={20*np.log10(np.max(np.abs(dry))+1e-12):.1f} dBFS", flush=True)
    if loop:
        st = loop_with_reverb(dry, wet=rv["wet"], room=rv["room"], damp=rv["damp"], tail_s=rv["tail_s"])
        seam = seam_metrics(st)
        # tiny 2 ms safety crossfade only if the join still jumps
        # A large residual join is smoothed with a short wrapped cosine splice.
        if seam["abs_jump"] > 8 * max(seam.get("typical_step", 0.001), 1e-6):
            k = int(0.004 * SR)
            # Smooth the 2k samples straddling the join with a raised-cosine
            # average against a linear interpolation across the join.
            wrap = np.concatenate([st[:, -k:], st[:, :k]], axis=1)
            # target path: linear from first to last of this window
            t = np.linspace(0, 1, 2 * k)
            # only gently pull the centre toward a spline; keep ends pinned
            w = np.sin(np.pi * t) ** 2  # 0 at ends, 1 at the join
            lin = wrap[:, :1] + (wrap[:, -1:] - wrap[:, :1]) * t
            # actually pin ends of wrap (already themselves); blend only near centre
            blended = wrap * (1 - 0.7 * w) + lin * (0.7 * w)
            st[:, -k:] = blended[:, :k]
            st[:, :k] = blended[:, k:]
            seam = seam_metrics(st)
    else:
        # one-shot: reverb with silent tail, then trim to declared length
        n = dry.shape[1]
        extra = int(rv["tail_s"] * SR)
        ext = np.concatenate([dry, np.zeros((2, extra))], axis=1)
        wet = reverb_stereo(ext, wet=rv["wet"], room=rv["room"], damp=rv["damp"])
        st = wet[:, :n]
        # keep natural decay already written into the composition length
        fo = int(0.02 * SR)
        st[:, -fo:] *= np.linspace(1, 0, fo)
        seam = None

    st, lufs, tpeak = normalize_music(st, loop=loop)
    if loop:
        seam = seam_metrics(st)
    gaps = silent_gaps(st)
    peak_abs = float(np.max(np.abs(st)))
    print(f"    LUFS={lufs:.2f}  TPpeak={tpeak:.2f} dB  peak={20*np.log10(peak_abs+1e-12):.2f} dBFS"
          + (f"  seam_jump={seam['abs_jump']:.5f}  deriv_err={seam['deriv_err']:.5f}" if seam else ""),
          flush=True)
    if gaps:
        print(f"    quiet windows (>1s, <-46 dB RMS): {gaps}", flush=True)

    wav = os.path.join("/tmp", f"tr-{key}.wav")
    mp3 = os.path.join(outdir, spec["file"])
    write_wav(wav, st)
    encode_mp3(wav, mp3)
    ff_lufs, ff_peak = measure_ffmpeg_lufs(wav)
    mp3_dur = probe_duration(mp3)
    size = os.path.getsize(mp3)
    os.remove(wav)
    print(f"    wrote {mp3}  {size/1024:.0f} KiB  mp3_dur={mp3_dur:.3f}s  ebur128 I={ff_lufs} TP={ff_peak}",
          flush=True)

    rec = {
        "key": key,
        "file": spec["file"],
        "duration_s": round(st.shape[1] / SR, 4),
        "mp3_duration_s": round(mp3_dur, 4),
        "bpm": meta["bpm"],
        "key_scale": meta["key_scale"],
        "bars": meta["bars"],
        "loop": loop,
        "loopStart": MP3_PAD if loop else None,
        "loopEnd": round(mp3_dur - MP3_PAD, 4) if loop else None,
        "mood": meta["mood"],
        "lufs_integrated": round(lufs, 2),
        "true_peak_dbfs": round(tpeak, 2),
        "ffmpeg_lufs": ff_lufs,
        "ffmpeg_true_peak": ff_peak,
        "bytes": size,
        "seam": seam,
        "quiet_windows_s": gaps,
    }
    return rec


def write_manifest(outdir, records):
    path = os.path.join(outdir, "manifest.json")
    doc = {
        "game": "Inkborne",
        "format": "mp3",
        "codec": "libmp3lame",
        "sample_rate": SR,
        "channels": 2,
        "bitrate": BITRATE,
        "loudness_target_lufs": TARGET_LUFS,
        "peak_ceiling_dbfs": PEAK_DB,
        "mp3_loop_note": (
            "MP3 encoder padding is about 25 ms (lame delay ~1105 samples at 44.1 kHz). "
            "In WebAudio play loops with source.loop=true, loopStart≈0.025, "
            "loopEnd=duration-0.025, or fade in a second source."
        ),
        "generator": "src/generate_music.py",
        "tracks": records,
    }
    with open(path, "w") as f:
        json.dump(doc, f, indent=2)
        f.write("\n")
    return path


def write_readme(outdir, records):
    path = os.path.join(outdir, "README.md")
    rows = []
    for r in records:
        loop = "yes" if r["loop"] else "one-shot"
        lp = f"{r['loopStart']:.3f}–{r['loopEnd']:.3f}" if r["loop"] else "—"
        bpm = r["bpm"] if r["bpm"] is not None else "—"
        bars = r["bars"] if r["bars"] is not None else "—"
        rows.append(
            f"| `{r['file']}` | `{r['key']}` | {r['duration_s']:.2f}s | {bpm} | {r['key_scale']} | {bars} | {loop} | {lp} | {r['mood']} |"
        )
    body = f"""# Music (Cody, audio)

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
""" + "\n".join(rows[:5]) + """

## Extras (not yet keyed in SPEC)

| file | key | length | bpm | scale | bars | loop | loopStart–End | mood |
|---|---|---|---|---|---|---|---|---|
""" + "\n".join(rows[5:]) + """

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
"""
    with open(path, "w") as f:
        f.write(body)
    return path


def main():
    args = sys.argv[1:]
    outdir = args[0] if args else os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
    outdir = os.path.abspath(outdir)
    wanted = args[1:] if len(args) > 1 else None
    os.makedirs(outdir, exist_ok=True)

    # Warm up JIT so the first track's timing is honest
    _ = ks_pluck(220, 0.2, seed=1)
    _ = _comb_jit(np.zeros(8), 4, 0.8, 0.2)
    _ = _limiter_gain(np.ones(8), 0.9, 2.0, 0.9)

    manifest_path = os.path.join(outdir, "manifest.json")
    existing = []
    if os.path.isfile(manifest_path):
        try:
            existing = json.load(open(manifest_path)).get("tracks", [])
        except Exception:
            existing = []
    by_key = {r["key"]: r for r in existing}

    chosen = [s for s in TRACKS if (wanted is None or s["key"] in wanted or s["file"] in wanted)]
    if not chosen:
        print("no matching tracks", file=sys.stderr)
        sys.exit(1)

    for spec in chosen:
        rec = render_track(spec, outdir)
        by_key[rec["key"]] = rec
        # keep SPEC order
        records = [by_key[s["key"]] for s in TRACKS if s["key"] in by_key]
        write_manifest(outdir, records)
        write_readme(outdir, records)

    print("done.", flush=True)


if __name__ == "__main__":
    main()
