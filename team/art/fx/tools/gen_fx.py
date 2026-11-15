#!/usr/bin/env python3
"""Inkborne battle FX generator (procedural sumi-e ink frame strips).

Re-render everything:   python3 tools/gen_fx.py            (from team/art/fx)
Render some keys only:  python3 tools/gen_fx.py fx-hit-light fx-seal-gale
Needs numpy, scipy, pillow (with WebP).  Original art only; no outside assets.
"""
# ============================== CONFIG ======================================
import os
HERE = os.path.dirname(os.path.abspath(__file__))
CONFIG = {
    "out_dir": os.path.normpath(os.path.join(HERE, "..")),   # team/art/fx
    "fps": 12,
    "frame": 256,            # SPEC 5 default sprite frame
    "frame_big": 512,        # Seal Arts / Inkwing need more room
    "supersample": 2,        # internal render scale (anti-aliasing)
    "seed": 1337,
    "palette": {             # SPEC 5
        "paper": "#ece6d8", "paper_shade": "#d9d0bc", "ink": "#1b1813",
        "wash1": "#3b3730", "wash2": "#6d675b", "wash3": "#a39c8c",
        "vermilion": "#b3261e",
    },
    "elements": {            # CANON + SPEC 5 tints
        "gale":  {"tint": "#5f8a6a", "member": "itsuki", "form": "Gale Crane", "wing": "crane"},
        "ember": {"tint": "#c2452d", "member": "benika", "form": "Ember Kite", "wing": "kite"},
        "stone": {"tint": "#7a6a52", "member": "gonzo",  "form": "Stone Owl",  "wing": "owl"},
    },
    "frames": {"hit_light": 9, "hit_heavy": 10, "clean_line": 8, "fail": 7,
               "seal_mark": 5, "seal_pass": 8, "seal_art": 18,
               "inkwing": 30, "inkwing_loop": 12, "death": 14},
    "formats": ["webp"],     # add "png" for PNG copies
    "previews": True,
}
# ============================================================================
import sys, json, math
import numpy as np
from PIL import Image, ImageDraw, ImageChops, ImageFont
from scipy import ndimage as ndi

SS = CONFIG["supersample"]; FPS = CONFIG["fps"]; F = CONFIG["frames"]
def hexrgb(h): return np.array([int(h[i:i+2], 16) for i in (1, 3, 5)], np.float32) / 255
PAL = {k: hexrgb(v) for k, v in CONFIG["palette"].items()}
def lerp(a, b, t): return a + (b - a) * t
def sstep(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0, 1); return t * t * (3 - 2 * t)
def eout(t, p=3): return 1 - (1 - np.clip(t, 0, 1)) ** p
def cl(t): return float(np.clip(t, 0, 1))

# ---------------------------------------------------------------- noise bank
_NB = {}
def bank(N):
    if N not in _NB:
        r = np.random.default_rng(99)
        def field(sig):
            f = ndi.gaussian_filter(r.standard_normal((N, N)).astype(np.float32), sig, mode="wrap")
            return np.clip(f / (f.std() * 2.2 + 1e-6), -1, 1)
        d = {"fine": field(0.8 * SS), "mid": field(3 * SS), "coarse": field(10 * SS), "huge": field(28 * SS)}
        g = r.random((N, N)).astype(np.float32)
        fib = ndi.gaussian_filter(g, (0.5 * SS, 4 * SS), mode="wrap") + ndi.gaussian_filter(g, (4 * SS, 0.5 * SS), mode="wrap") \
            + 0.6 * ndi.gaussian_filter(g, 0.7 * SS, mode="wrap")
        fib = (fib - fib.min()) / (fib.max() - fib.min())
        d["grain"] = np.clip((fib - 0.5) * 2.2 + 0.5, 0, 1)
        _NB[N] = d
    return _NB[N]
def nz(N, kind, seed=0):
    f = bank(N)[kind]
    if not seed: return f
    return np.roll(f, ((seed * 7919) % N, (seed * 104729) % N), (0, 1))

# ---------------------------------------------------------------- canvas
class Canvas:
    def __init__(s, size):
        s.size = size; s.N = size * SS
        s.rgb = np.zeros((s.N, s.N, 3), np.float32); s.a = np.zeros((s.N, s.N), np.float32)
    def over(s, col, alpha):
        a = np.clip(alpha, 0, 1)[..., None]
        s.rgb = np.asarray(col, np.float32) * a + s.rgb * (1 - a); s.a = a[..., 0] + s.a * (1 - a[..., 0])
    def image(s):
        n, k = s.size, SS
        pr = s.rgb.reshape(n, k, n, k, 3).mean((1, 3)); a = s.a.reshape(n, k, n, k).mean((1, 3))
        rgb = np.where(a[..., None] > 1e-4, pr / np.maximum(a[..., None], 1e-4), 0)
        return Image.fromarray(np.dstack([np.clip(rgb, 0, 1) * 255, np.clip(a, 0, 1) * 255]).round().astype(np.uint8), "RGBA")

class Mask:
    def __init__(s, size):
        s.N = size * SS; s.im = Image.new("L", (s.N, s.N), 0); s.d = ImageDraw.Draw(s.im)
    def arr(s): return np.asarray(s.im, np.float32) / 255
    def add(s, tmp): s.im = ImageChops.lighter(s.im, tmp); s.d = ImageDraw.Draw(s.im)
    def tmp(s):
        t = Image.new("L", (s.N, s.N), 0); return t, ImageDraw.Draw(t)

def P(x, y): return (x * SS, y * SS)

def ink_layer(C, cov, col, density=1.0, bleed=1.0, rough=0.5, edge=0.35, halo=0.0, halo_col=None,
              grain=0.5, seed=0, fine_w=0.55, holes=0.0, halo_spread=4.0):
    """Turn a coverage mask into wet ink: ragged bleed edge, darker drying rim, paper halo, grain."""
    if density <= 0.003 or cov.max() < 0.01: return
    N = cov.shape[0]
    if halo > 0:
        h = ndi.gaussian_filter(cov, halo_spread * bleed * SS + 2 * SS)
        h = h * (0.75 + 0.35 * nz(N, "coarse", seed + 3)) * halo * density
        h = h * (1 - 0.45 * nz(N, "grain", 0))
        C.over(halo_col if halo_col is not None else col, h)
    blur = ndi.gaussian_filter(cov, max(0.3, bleed) * SS)
    thr = 0.5 + rough * 0.28 * nz(N, "mid", seed)
    shape = sstep(thr - 0.1, thr + 0.1, blur)
    inner = ndi.gaussian_filter(cov, 0.45 * SS)
    a = fine_w * inner * np.maximum(shape, 0.5) + (1 - fine_w) * shape
    rim = np.clip(shape - ndi.gaussian_filter(shape, 2.2 * SS), 0, 1)
    a = np.clip(a + edge * rim * 1.6, 0, 1) * density
    a = a * (0.86 + 0.14 * nz(N, "huge", seed + 5)) * (1 - 0.1 * (1 - shape) * nz(N, "coarse", seed + 7))
    G = nz(N, "grain", 0)
    a = np.clip(a - 0.55 * grain * (1 - a) * G - 0.07 * grain * G, 0, 1)
    if holes > 0:
        a = a * (1 - holes * sstep(0.25, 0.65, nz(N, "fine", seed + 11)))
    colr = lerp(np.asarray(col, np.float32), PAL["wash3"] if np.mean(col) < 0.4 else np.asarray(col), 0.0)
    C.over(colr, a)

# ---------------------------------------------------------------- geometry
def catmull(pts, n=10):
    Pp = np.asarray(pts, np.float32)
    if len(Pp) == 2: return np.linspace(Pp[0], Pp[1], n * 2)
    Pp = np.vstack([Pp[0], Pp, Pp[-1]]); out = []
    t = np.linspace(0, 1, n, endpoint=False)[:, None]
    for i in range(1, len(Pp) - 2):
        p0, p1, p2, p3 = Pp[i - 1], Pp[i], Pp[i + 1], Pp[i + 2]
        out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t ** 2 + (-p0 + 3 * p1 - 3 * p2 + p3) * t ** 3))
    out.append(Pp[-2][None]); return np.vstack(out)

def ell(cx, cy, a, b, ang, n=18):
    t = np.linspace(0, 2 * np.pi, n, endpoint=False); c, s = math.cos(ang), math.sin(ang)
    x, y = a * np.cos(t), b * np.sin(t)
    return [((cx + x[i] * c - y[i] * s) * SS, (cy + x[i] * s + y[i] * c) * SS) for i in range(n)]

def brush(m, pts, width, rng, t0=0.0, t1=1.0, bristles=14, dry=0.35, wet=0.3, taper=(0.12, 0.4),
          local=False, press=None, value=255, head=False, jitter=0.6):
    """Bristle brush: wet solid core at the start, bristle streaks that run dry toward the tail."""
    path = catmull(pts, 10) * SS
    seg = np.hypot(*np.diff(path, axis=0).T); L = np.concatenate([[0], np.cumsum(seg)]); tot = L[-1]
    if tot < 2: return
    n = int(np.clip(tot / (1.4 * SS), 12, 500))
    s = np.linspace(0, tot, n); x = np.interp(s, L, path[:, 0]); y = np.interp(s, L, path[:, 1])
    t = np.linspace(0, 1, n)
    i0 = int(cl(t0) * (n - 1)); i1 = int(math.ceil(cl(t1) * (n - 1)))
    if i1 - i0 < 1: return
    dx, dy = np.gradient(x), np.gradient(y); ln = np.hypot(dx, dy) + 1e-6; nx, ny = -dy / ln, dx / ln
    u = np.clip((t - t0) / max(t1 - t0, 1e-3), 0, 1) if local else t
    a, b = taper; k = np.ones(n)
    if a > 0: k = np.minimum(k, 0.18 + 0.82 * np.clip(u / a, 0, 1) ** 0.6)
    if b > 0: k = np.minimum(k, 0.06 + 0.94 * np.clip((1 - u) / b, 0, 1) ** 0.8)
    if press is not None: k = k * press(t)
    w = width * SS * k * (1 + 0.07 * np.sin(t * 23 + rng.uniform(0, 6)))
    tmp, d = m.tmp()
    cf = np.clip(1.25 - (u - wet) / 0.25, 0, 1)
    for i in range(i0, i1, 2):
        j = min(i + 2, i1)
        if cf[i] < 0.04: continue
        ww0, ww1 = w[i] * 0.42, w[j] * 0.42
        d.polygon([(x[i] + nx[i] * ww0, y[i] + ny[i] * ww0), (x[j] + nx[j] * ww1, y[j] + ny[j] * ww1),
                   (x[j] - nx[j] * ww1, y[j] - ny[j] * ww1), (x[i] - nx[i] * ww0, y[i] - ny[i] * ww0)],
                  fill=int(value * cf[i]))
    offs = np.sort(np.clip(np.linspace(-0.95, 0.95, bristles) + rng.normal(0, 0.05, bristles), -1, 1))
    for o in offs:
        rate = rng.uniform(0.5, 1.5) * dry; ph = rng.uniform(0, 50); fr = rng.uniform(8, 30)
        load = 1.15 - rate * 1.9 * u - (abs(o) ** 2) * dry * 0.9 + 0.28 * np.sin(u * fr + ph) * dry
        on = load > 0.45
        jx, jy = rng.normal(0, jitter * SS * 0.4, 2)
        bx = x + nx * o * w / 2 + jx; by = y + ny * o * w / 2 + jy
        bw = np.maximum(1, w / bristles * 2.7)
        i = i0
        while i < i1:
            if not on[i]: i += 1; continue
            j = i
            while j < i1 and on[j] and j - i < 6: j += 1
            if j > i:
                d.line([(bx[q], by[q]) for q in range(i, j + 1)], fill=value, width=int(bw[(i + j) // 2] + 0.5), joint="curve")
            i = j if j > i else i + 1
    if head:
        r = w[i1 - 1] * 0.55
        d.ellipse([x[i1 - 1] - r, y[i1 - 1] - r, x[i1 - 1] + r, y[i1 - 1] + r], fill=value)
    m.add(tmp)

def flat_brush(m, pts, width, rng, t1=1.0, bristles=40, clumps=6, split=0.8, dry=0.6, wet=0.3, value=255):
    """Broad flat (hake-style) brush: constant width with flat sides, squared ragged start, bristles that
    bunch into clumps and split apart along the stroke, running dry into a frayed tail."""
    path = catmull(pts, 10) * SS
    seg = np.hypot(*np.diff(path, axis=0).T); L = np.concatenate([[0], np.cumsum(seg)]); tot = L[-1]
    if tot < 2: return
    n = int(np.clip(tot / (1.2 * SS), 12, 500))
    s = np.linspace(0, tot, n); x = np.interp(s, L, path[:, 0]); y = np.interp(s, L, path[:, 1]); u = np.linspace(0, 1, n)
    i1 = int(math.ceil(cl(t1) * (n - 1)))
    if i1 < 2: return
    dx, dy = np.gradient(x), np.gradient(y); ln = np.hypot(dx, dy) + 1e-6; nx, ny = -dy / ln, dx / ln
    w = width * SS * (1 + 0.035 * np.sin(u * 17 + rng.uniform(0, 6)))
    tmp, d = m.tmp()
    cf = np.clip(1.3 - (u - wet) / 0.2, 0, 1)
    for i in range(0, i1, 2):  # flat wet core with slightly rough flat sides
        j = min(i + 2, i1)
        if cf[i] < 0.04: continue
        e0 = w[i] * 0.47 * (1 + rng.normal(0, 0.02)); e1 = w[j] * 0.47 * (1 + rng.normal(0, 0.02))
        d.polygon([(x[i] + nx[i] * e0, y[i] + ny[i] * e0), (x[j] + nx[j] * e1, y[j] + ny[j] * e1),
                   (x[j] - nx[j] * e1, y[j] - ny[j] * e1), (x[i] - nx[i] * e0, y[i] - ny[i] * e0)], fill=int(value * cf[i] * 0.9))
    centers = np.sort(np.linspace(-0.85, 0.85, clumps) + rng.normal(0, 0.06, clumps))
    rates = rng.uniform(0.6, 1.4, clumps) * dry
    offs = np.clip(np.linspace(-1, 1, bristles) + rng.normal(0, 0.02, bristles), -1, 1)
    sp = sstep(0.05, 0.85, u) * split
    for o in offs:
        cj = int(np.argmin(np.abs(centers - o))); c = centers[cj]
        oe = o + (c - o) * sp * 0.65
        edge_j = (rng.normal(0, 0.05, n) if abs(o) > 0.85 else 0)
        ph = rng.uniform(0, 50); fr = rng.uniform(6, 22)
        load = 1.2 - rates[cj] * 1.7 * u - (0.35 * u if abs(o) > 0.9 else 0) + 0.3 * dry * np.sin(u * fr + ph)
        st = int(rng.uniform(0, 0.07) * n); en = int((1 - rng.uniform(0, 0.22)) * (n - 1))
        on = (load > 0.42); on[:st] = False; on[en:] = False
        bx = x + nx * (oe + edge_j) * w / 2; by = y + ny * (oe + edge_j) * w / 2
        bw = max(1, int(width * SS / bristles * 1.9 + 0.5))
        i = 0
        while i < i1:
            if not on[i]: i += 1; continue
            j = i
            while j < i1 and on[j] and j - i < 8: j += 1
            if j > i: d.line([(bx[q], by[q]) for q in range(i, j + 1)], fill=value, width=bw)
            i = j if j > i else i + 1
    m.add(tmp)

def make_splat(rng, r, spikes=10, drops=24, dirn=None, spread=1.2, red=0.12):
    def ang():
        return (dirn + rng.normal(0, spread)) if dirn is not None else rng.uniform(0, 2 * np.pi)
    return {"r": r, "harm": [(rng.normal(0, 0.10), rng.uniform(0, 6.28), kk) for kk in range(2, 7)],
            "spikes": [(rng.uniform(0, 2 * np.pi) if rng.random() < 0.5 or dirn is None else ang(), rng.uniform(0.4, 1.3), rng.uniform(0.10, 0.22)) for _ in range(spikes)],
            "drops": [(ang(), rng.uniform(0.3, 1.0) ** 0.7, rng.uniform(0.04, 0.16), rng.uniform(0.5, 2.0), rng.random() < red) for _ in range(drops)]}

def draw_splat(m, red, cx, cy, S, t, blob=True, reach=1.0):
    e = eout(t, 3); r = S["r"]
    tmp, d = m.tmp()
    if blob:
        th = np.linspace(0, 2 * np.pi, 72, endpoint=False)
        rad = r * (0.35 + 0.65 * e) * (1 + sum(a * np.sin(k * th + p) for a, p, k in S["harm"]))
        d.polygon([P(cx + rad[i] * math.cos(th[i]), cy + rad[i] * math.sin(th[i])) for i in range(72)], fill=255)
    for a, lf, wf in S["spikes"]:
        L = r * (0.55 + lf * e * 1.5 * reach); bw = r * wf * (1 - 0.3 * e); c, s = math.cos(a), math.sin(a)
        bx, by = cx + c * r * 0.5, cy + s * r * 0.5
        cu = 0.18 * math.sin(a * 5.3); mx, my = cx + math.cos(a + cu) * L * 0.6, cy + math.sin(a + cu) * L * 0.6
        _pts = catmull([(bx, by), (mx, my), (cx + c * L, cy + s * L)], 8)
        _n = len(_pts); left = []; right = []
        for _i in range(_n):
            _q = _i / (_n - 1); _w = bw * (1 - _q) ** 0.9 * (1 + 0.25 * math.sin(_q * 9 + a)) + 0.4
            left.append(P(_pts[_i][0] - s * _w, _pts[_i][1] + c * _w)); right.append(P(_pts[_i][0] + s * _w, _pts[_i][1] - c * _w))
        d.polygon(left + right[::-1], fill=255)
        rr = bw * 0.35; tx, ty = cx + c * (L + rr), cy + s * (L + rr)
        d.ellipse([(tx - rr) * SS, (ty - rr) * SS, (tx + rr) * SS, (ty + rr) * SS], fill=255)
    m.add(tmp)
    tr = red.tmp() if red is not None else None
    for a, df, sz, el, isred in S["drops"]:
        dist = r * (0.9 + df * e * 2.3 * reach); s_ = max(0.6, r * sz * (1 - 0.3 * e))
        cx2, cy2 = cx + math.cos(a) * dist, cy + math.sin(a) * dist
        poly = ell(cx2, cy2, s_ * (1 + el * (1 - e) * 1.6 + 0.3), s_, a, 14)
        if isred and tr is not None: tr[1].polygon(poly, fill=255)
        else: d.polygon(poly, fill=255)
    m.add(tmp)
    if tr is not None: red.add(tr[0])

GLYPH = [[(-0.48, -0.52), (-0.46, 0.0), (-0.5, 0.56)], [(-0.58, -0.08), (0.0, -0.12), (0.52, -0.18)],
         [(0.06, -0.62), (0.02, 0.08), (0.38, 0.52)], [(0.24, -0.46), (0.56, -0.38)], [(-0.22, 0.34), (0.12, 0.44)]]
def draw_seal(m, cx, cy, size, ang=-0.06, seed=0):
    """Red hanko: rough square with carved border and an invented glyph (original)."""
    rng = np.random.default_rng(seed); h = size / 2; c, s = math.cos(ang), math.sin(ang)
    def T(u, v): return P(cx + (u * c - v * s) * h, cy + (u * s + v * c) * h)
    tmp, d = m.tmp(); pts = []
    for (u0, v0), (u1, v1) in [((-1, -1), (1, -1)), ((1, -1), (1, 1)), ((1, 1), (-1, 1)), ((-1, 1), (-1, -1))]:
        for q in np.linspace(0, 1, 9, endpoint=False):
            pts.append(T(u0 + (u1 - u0) * q + rng.normal(0, 0.03), v0 + (v1 - v0) * q + rng.normal(0, 0.03)))
    d.polygon(pts, fill=255)
    lw = max(1, int(size * 0.075 * SS)); bi = 0.8
    d.line([T(-bi, -bi), T(bi, -bi), T(bi, bi), T(-bi, bi), T(-bi, -bi)], fill=0, width=max(1, int(size * 0.045 * SS)))
    for stroke in GLYPH:
        pp = catmull([(u + rng.normal(0, 0.02), v + rng.normal(0, 0.02)) for u, v in stroke], 6)
        d.line([T(u * 0.95, v * 0.95) for u, v in pp], fill=0, width=lw, joint="curve")
    m.add(tmp)

def ring_pts(cx, cy, R, a0, sweep, n=40, wob=0.0, rng=None):
    out = []
    for i in range(n):
        a = a0 + sweep * i / (n - 1); rr = R * (1 + (wob * math.sin(a * 3 + 1.3) if wob else 0))
        out.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
    return out

# ---------------------------------------------------------------- effects
SEED = CONFIG["seed"]
def R(k): return np.random.default_rng(SEED + k)

def fx_hit(heavy):
    size = CONFIG["frame"]; n = F["hit_heavy" if heavy else "hit_light"]
    rng = R(20 if heavy else 10); cx, cy = 112, 128
    r = 44 if heavy else 30
    S = make_splat(rng, r, spikes=14 if heavy else 8, drops=40 if heavy else 20, dirn=0.0, spread=1.0, red=0.16 if heavy else 0.12)
    S2 = make_splat(rng, r * 0.55, spikes=5, drops=14, dirn=0.0, spread=0.7, red=0.2) if heavy else None
    slashes = [[(cx - 70, cy + 40), (cx, cy + 2), (cx + 80, cy - 34)]]
    if heavy: slashes.append([(cx - 60, cy - 50), (cx + 4, cy - 4), (cx + 74, cy + 52)])
    frames = []
    for f in range(n):
        t = f / (n - 1); C = Canvas(size); ink, red, wash = Mask(size), Mask(size), Mask(size)
        st = cl((f + 1) / 3.0)
        fade = 1 - sstep(0.45, 1.05, t)
        draw_splat(ink, red, cx, cy, S, st)
        if S2 is not None and f >= 1: draw_splat(ink, red, cx + 44, cy - 10, S2, cl(f / 3.0))
        sr = np.random.default_rng(SEED + 5)
        for k, sp in enumerate(slashes):
            p = cl((f + 1 - k * 0.5) / 1.6)
            if f <= 4 and p > 0:
                brush(wash if f >= 3 else ink, sp, 9 if heavy else 6, np.random.default_rng(SEED + 50 + k), t1=p, dry=0.8, wet=0.05, taper=(0.3, 0.5), bristles=8)
        if heavy and 1 <= f <= 6:
            rr = 34 + 70 * eout((f - 1) / 5, 2)
            brush(wash, ring_pts(cx, cy, rr, -0.4, 5.2, 50, 0.04), 7, np.random.default_rng(SEED + 77), dry=0.9, wet=0.0, bristles=7, taper=(0.2, 0.4))
        dens = 0.97 * fade ** 0.9
        col = lerp(PAL["ink"], PAL["wash2"], sstep(0.3, 1, t))
        ink_layer(C, wash.arr(), PAL["wash2"], density=0.75 * (1 - cl((f - 2) / 4)), bleed=0.6, rough=0.3, edge=0.2, grain=0.7, seed=f)
        ink_layer(C, ink.arr(), col, density=dens, bleed=0.8 + 2.2 * t, rough=0.6, edge=0.45, halo=0.28 + 0.3 * t,
                  halo_col=PAL["wash3"], grain=0.5 + 0.4 * t, seed=3)
        ink_layer(C, red.arr(), PAL["vermilion"], density=fade, bleed=0.7 + t, rough=0.4, edge=0.4, halo=0.15, grain=0.5, seed=4)
        frames.append(C.image())
    return frames

def fx_clean_line():
    size = CONFIG["frame"]; n = F["clean_line"]; cx, cy = 128, 128
    frames = []; Sred = make_splat(R(31), 20, spikes=0, drops=18, red=1.0)
    for f in range(n):
        t = f / (n - 1); C = Canvas(size); ink, red, wash = Mask(size), Mask(size), Mask(size)
        prog = [0.42, 0.82, 1.0][min(f, 2)]
        fade = 1 - sstep(0.55, 1.0, t)
        brush(ink, ring_pts(cx, cy, 80, -1.9, 5.85, 60, 0.02), 15, R(30), t1=prog, dry=0.55, wet=0.45, taper=(0.06, 0.35),
              bristles=16, head=f < 2, press=lambda q: 0.85 + 0.3 * np.sin(q * 3.1))
        sp = cl((f - 0.5) / 1.5)
        if sp > 0: brush(ink, [(26, 160), (128, 128), (232, 98)], 10, R(32), t1=sp, dry=0.5, wet=0.3, taper=(0.15, 0.45), bristles=12)
        if f >= 2:
            sc = {2: 1.38, 3: 1.06}.get(f, 1.0)
            draw_seal(red, cx, cy, 50 * sc, -0.08, seed=7)
            if f in (2, 3, 4): draw_splat(red, None, cx, cy, Sred, cl((f - 1.5) / 2.5), blob=False)
        ink_layer(C, ink.arr(), PAL["ink"], density=0.98 * fade, bleed=0.6 + 1.6 * t, rough=0.45, edge=0.5, halo=0.22,
                  halo_col=PAL["wash3"], grain=0.45 + 0.3 * t, seed=1)
        ink_layer(C, red.arr(), PAL["vermilion"], density=0.97 * (1 - sstep(0.7, 1.0, t)), bleed=0.5, rough=0.25, edge=0.3,
                  grain=0.6, holes=0.35, seed=2, fine_w=0.8)
        frames.append(C.image())
    return frames

def fx_fail():
    size = CONFIG["frame"]; n = F["fail"]; cx, cy = 128, 128; frames = []
    arcs = [(-1.9, 1.5), (-0.2, 1.2), (1.3, 1.6)]
    _cr = R(41); crumbs = [(_cr.uniform(40, 216), _cr.uniform(95, 170), _cr.uniform(1.5, 3.5)) for i in range(16)]
    for f in range(n):
        t = f / (n - 1); C = Canvas(size); ink = Mask(size)
        prog = min(1.0, 0.7 + f * 0.15)
        for k, (a0, sw) in enumerate(arcs):
            droop = f * (2 + 2 * k); sx = (k - 1) * f * 1.5
            pts = [(x + sx, y + droop * (0.3 + 0.7 * (i / 23))) for i, (x, y) in enumerate(ring_pts(cx, cy, 80, a0, sw * prog, 24, 0.05))]
            brush(ink, pts, 15, R(43 + k), dry=0.5, wet=0.35, taper=(0.2, 0.45), bristles=12)
        sl = [(30, 150), (90, 132 + f * 2), (150, 132 + f * 4), (220, 110 + f * 5)]
        brush(ink, sl[:2], 14, R(47), t1=min(1, 0.6 + f * 0.3), dry=0.5, wet=0.35, bristles=12)
        if f >= 1: brush(ink, sl[2:], 12, R(48), t1=min(1, (f) * 0.35), dry=0.6, wet=0.2, bristles=10)
        cov = ink.arr()
        crack = sstep(0.015, 0.045, np.abs(nz(cov.shape[0], "mid", 9))) * sstep(0.01, 0.03, np.abs(nz(cov.shape[0], "coarse", 19)))
        cov = cov * crack
        if f >= 2:
            sm = cov.copy()
            for q in range(1, 2 + f):
                sm = np.maximum(sm, np.roll(np.roll(cov, q * 2 * SS, 1), q * SS, 0) * (0.75 ** q))
            cov = sm
        cr = Mask(size)
        for i, (x, y, s_) in enumerate(crumbs):
            if f >= 2:
                yy = y + (f - 2) ** 1.6 * 6; cr.d.ellipse([(x - s_) * SS, (yy - s_) * SS, (x + s_) * SS, (yy + s_) * SS], fill=220)
        cov = np.maximum(cov, cr.arr())
        ink_layer(C, cov, lerp(PAL["wash1"], PAL["wash2"], 0.6), density=0.95 * (1 - sstep(0.5, 1, t)), bleed=0.5 + t, rough=0.6, edge=0.3,
                  grain=0.9, holes=0.2, seed=f + 1, fine_w=0.75)
        frames.append(C.image())
    return frames

def fx_seal_mark():
    size = CONFIG["frame"]; frames = []
    for f in range(F["seal_mark"]):
        C = Canvas(size); red = Mask(size)
        sc = [1.5, 1.18, 0.96, 1.0, 1.0][f]; dens = [0.45, 0.85, 1.0, 1.0, 1.0][f]
        draw_seal(red, 128, 128, 64 * sc, -0.07, seed=11)
        ink_layer(C, red.arr(), PAL["vermilion"], density=dens, bleed=0.5 + (0.5 if f == 0 else 0), rough=0.25, edge=0.35, halo=0.08,
                  grain=0.6, holes=0.3, seed=5, fine_w=0.8)
        frames.append(C.image())
    return frames

def fx_seal_pass():
    size = CONFIG["frame"]; n = F["seal_pass"]; frames = []; S = make_splat(R(70), 26, spikes=6, drops=30, red=1.0)
    for f in range(n):
        t = f / (n - 1); C = Canvas(size); red, ink = Mask(size), Mask(size)
        sc = [1.25, 1.1, 1.0][min(f, 2)]
        draw_seal(red, 128, 128, 64 * sc, -0.07, seed=11)
        draw_splat(red, None, 128, 128, S, cl(f / 4), blob=False)
        rr = 40 + 70 * eout(f / (n - 1), 2)
        brush(red if f < 3 else ink, ring_pts(128, 128, rr, 0.3, 5.6, 50, 0.03), 8, R(71), dry=0.85, wet=0.1, bristles=8)
        ink_layer(C, ink.arr(), PAL["wash2"], density=0.7 * (1 - t), bleed=0.6, rough=0.3, edge=0.2, grain=0.8, seed=6)
        ink_layer(C, red.arr(), PAL["vermilion"], density=1 - sstep(0.5, 1, t), bleed=0.5 + 0.8 * t, rough=0.3, edge=0.4, halo=0.12,
                  grain=0.6, holes=0.25, seed=5, fine_w=0.8)
        frames.append(C.image())
    return frames

# --- Seal Arts -----------------------------------------------------------
TGT = (300, 300); GROUND = 410
def seal_common(f, n, size, ink, red, rng_k, flare_S):
    """Shared opening: seal stamps in, a broad brush sweeps across and passes over it (the press moment)."""
    path = [(24, 318), (120, 296), (205, 266), (330, 246), (492, 214)]
    seal_xy, u_seal = (200, 268), 0.39
    prog = eout(cl((f - 2) / 4.0), 1.6)
    if f >= 0:
        sc = [1.45, 1.12, 1.0][min(f, 2)]
        draw_seal(red, *seal_xy, 66 * sc, -0.08, seed=13)
    if prog > 0:
        brush(ink, path, 40, R(rng_k), t1=prog, dry=0.6, wet=0.35, taper=(0.08, 0.3), bristles=22, head=False,
              press=lambda q: 0.8 + 0.35 * np.sin(q * 3.0 + 0.4))
    f_pass = 2 + 4.0 * (1 - (1 - u_seal) ** (1 / 1.6))
    fl = f - f_pass
    if -0.01 < fl < 4:
        draw_splat(red, None, *seal_xy, flare_S, cl((fl + 0.5) / 3), blob=False)
        rr = 44 + 30 * fl
        brush(red, ring_pts(*seal_xy, rr, -0.6, 5.3, 44, 0.04), 7, R(rng_k + 1), dry=0.85, wet=0.15, bristles=8)
    return f_pass

def fx_seal(el):
    size = CONFIG["frame_big"]; n = F["seal_art"]; E = CONFIG["elements"][el]; T = hexrgb(E["tint"])
    rng = R({"gale": 100, "ember": 200, "stone": 300}[el]); frames = []
    flare = make_splat(R(90), 30, spikes=0, drops=34, red=1.0)
    tx, ty = TGT
    if el == "gale":
        streaks = [dict(y0=rng.uniform(170, 420), A=rng.uniform(20, 55), ph=rng.uniform(0, 6), d=rng.uniform(0, 0.35),
                        w=rng.uniform(5, 13)) for _ in range(9)]
        leaves = [dict(a=rng.uniform(0, 6.28), r=rng.uniform(40, 150), s=rng.uniform(3, 6), sp=rng.uniform(2.5, 4.5)) for _ in range(12)]
    elif el == "ember":
        flames = [dict(x=tx + o, h=rng.uniform(140, 260) * (1.15 - abs(o) / 160), w=rng.uniform(22, 36), ph=rng.uniform(0, 6),
                       d=abs(o) / 400) for o in np.linspace(-110, 110, 8) + rng.normal(0, 8, 8)]
        ash = [dict(x=tx + rng.normal(0, 70), v=rng.uniform(150, 320), s=rng.uniform(1.2, 3.0), ph=rng.uniform(0, 6),
                    d=rng.uniform(0, 0.5), red=rng.random() < 0.25) for _ in range(40)]
    else:
        slabs = [[(tx - 150, ty - 150), (tx - 82, ty - 64), (tx - 6, GROUND - 26)],
                 [(tx + 138, ty - 140), (tx + 70, ty - 58), (tx + 8, GROUND - 18)],
                 [(tx - 175, GROUND - 34), (tx, GROUND - 30), (tx + 175, GROUND - 40)]]
        cracks = []
        for k in range(8):
            a = (np.pi if k % 2 else 0) + rng.normal(0, 0.35) - (0.0 if k < 6 else np.pi / 2)
            pts = [(tx, GROUND - 14)]; L = rng.uniform(90, 200)
            for q in range(6):
                a += rng.normal(0, 0.45); step = L / 6
                pts.append((pts[-1][0] + math.cos(a) * step, pts[-1][1] + math.sin(a) * step * 0.45))
            cracks.append(pts)
        chips = [dict(vx=rng.normal(0, 260), vy=-rng.uniform(150, 420), s=rng.uniform(4, 13), rot=rng.uniform(0, 6)) for _ in range(22)]
    for f in range(n):
        t = f / (n - 1); C = Canvas(size); ink, red, wash, tint = Mask(size), Mask(size), Mask(size), Mask(size)
        seal_common(f, n, size, ink, red, 400, flare)
        te = cl((f - 6) / (n - 7))
        if el == "gale" and f >= 6:
            for k, s_ in enumerate(streaks):
                head = cl((te - s_["d"]) / 0.4); tail = cl((te - s_["d"] - 0.22) / 0.45)
                if head <= tail + 0.01: continue
                pts = [(x, s_["y0"] + s_["A"] * math.sin(x / 120 + s_["ph"]) - 40 * math.exp(-((x - tx) / 90) ** 2))
                       for x in np.linspace(-20, 540, 9)]
                brush(ink if k % 3 else wash, pts, s_["w"], R(110 + k), t0=tail, t1=head, local=True, dry=0.8, wet=0.15,
                      taper=(0.3, 0.5), bristles=8)
                brush(tint, pts, s_["w"] * 2.5, R(130 + k), t0=tail, t1=head, local=True, dry=0.2, wet=0.6, bristles=6)
            for arm in range(3):
                g = cl(te * 1.6); rot = te * 7 + arm * 2.09
                pts = [(tx + (18 + 120 * q * g) * math.cos(rot + q * 4.2), ty + (18 + 120 * q * g) * 0.75 * math.sin(rot + q * 4.2)) for q in np.linspace(0, 1, 12)]
                brush(ink, pts, 10, R(150 + arm), t0=cl(te * 1.5 - 0.6), t1=cl(te * 2.2), local=True, dry=0.75, wet=0.2, bristles=9)
            for k, lf in enumerate(leaves):
                a = lf["a"] + te * lf["sp"]; rr = lf["r"] * (0.6 + 0.8 * te)
                lx, ly = tx + rr * math.cos(a), ty + rr * 0.7 * math.sin(a)
                if te > 0.08: ink.d.polygon(ell(lx, ly, lf["s"] * 1.8, lf["s"] * 0.6, a + 1.2, 10), fill=230)
        if el == "ember" and f >= 5:
            grow = eout(cl(te / 0.45), 2); coll = sstep(0.7, 1.0, te)
            for k, fl in enumerate(flames):
                g = cl((grow - fl["d"]) / (1 - fl["d"] + 1e-3)) * (1 - 0.7 * coll)
                if g <= 0.02: continue
                h = fl["h"] * g
                pts = [(fl["x"] + (12 + 22 * q) * math.sin(q * 5 + fl["ph"] + f * 1.1) * q, GROUND - h * q) for q in np.linspace(0, 1, 7)]
                brush(ink, pts, fl["w"], R(210 + k), dry=0.5, wet=0.35, taper=(0.02, 0.75), bristles=14)
                brush(tint, pts, fl["w"] * 2.2, R(230 + k), dry=0.1, wet=0.8, taper=(0.02, 0.6), bristles=6)
                if k % 2 == 0:
                    brush(red, pts[4:], fl["w"] * 0.35, R(250 + k), dry=0.6, wet=0.3, taper=(0.1, 0.7), bristles=5)
            brush(wash, [(tx - 160, GROUND + 4), (tx, GROUND - 2), (tx + 160, GROUND + 6)], 16 * grow + 1, R(260), dry=0.85, wet=0.1, bristles=12)
            for k, a in enumerate(ash):
                q = cl((te - a["d"]) / 0.6)
                if q <= 0 or q >= 1: continue
                ax_ = a["x"] + 18 * math.sin(q * 6 + a["ph"]); ay_ = GROUND - 60 - a["v"] * q
                (red if a["red"] else wash).d.ellipse([(ax_ - a["s"]) * SS, (ay_ - a["s"]) * SS, (ax_ + a["s"]) * SS, (ay_ + a["s"]) * SS], fill=255)
            if coll > 0:  # flames collapse into grey smoke
                for k in range(4):
                    sy = GROUND - 120 - 160 * coll - k * 30
                    brush(wash, [(tx - 80 + k * 30, sy + 30), (tx - 20 + k * 20, sy), (tx + 60 + k * 10, sy + 20)], 24, R(270 + k),
                          dry=0.4, wet=0.5, bristles=10)
        if el == "stone" and f >= 6:
            for k, sl in enumerate(slabs):
                p = eout(cl((te - k * 0.11) / 0.09), 2)
                if p > 0:
                    flat_brush(ink, sl, 62 if k < 2 else 40, R(310 + k), t1=p, bristles=44 if k < 2 else 32, clumps=7, split=0.9, dry=0.7, wet=0.25)
                    flat_brush(tint, sl, (62 if k < 2 else 40) * 1.35, R(320 + k), t1=p, bristles=20, clumps=4, split=0.4, dry=0.25, wet=0.6)
            cp = eout(cl((te - 0.12) / 0.35), 2)
            for k, cr in enumerate(cracks):
                if cp > 0:
                    brush(ink, cr, 4.5, R(330 + k), t1=cp, dry=0.4, wet=0.6, taper=(0.02, 0.6), bristles=4)
                    brush(red, cr, 7, R(340 + k), t1=cp * 0.8, dry=0.3, wet=0.6, taper=(0.02, 0.7), bristles=4)
            tau = te - 0.12
            if tau > 0:
                for k, ch in enumerate(chips):
                    q = tau * 0.9
                    x = tx + ch["vx"] * q; y = GROUND - 20 + ch["vy"] * q + 0.5 * 900 * q * q
                    if y > GROUND + 30: continue
                    a = ch["rot"] + q * 8; s_ = ch["s"]
                    ink.d.polygon([P(x + s_ * math.cos(a + j * 1.7 + 0.3 * (j % 2)), y + s_ * 0.8 * math.sin(a + j * 1.7)) for j in range(4)], fill=255)
                dust = Mask(size); dust.d.ellipse([(tx - 210) * SS, (GROUND - 40) * SS, (tx + 210) * SS, (GROUND + 22) * SS], fill=255)
                ink_layer(C, dust.arr(), T, density=0.28 * sstep(0.1, 0.35, te) * (1 - sstep(0.7, 1, te)), bleed=6, rough=0.9,
                          edge=0.1, grain=0.8, seed=17)
        # fades
        sfade = 1 - sstep(0.62, 1.0, t)
        efade = 1 - sstep(0.78, 1.0, t)
        ink_layer(C, tint.arr(), lerp(T, PAL["paper_shade"], 0.15), density=0.42 * efade, bleed=2.5, rough=0.7, edge=0.25, grain=0.8, seed=21)
        ink_layer(C, wash.arr(), PAL["wash2"], density=0.75 * efade, bleed=1.0, rough=0.5, edge=0.25, grain=0.8, seed=22)
        ink_layer(C, red.arr() * (1.0 if f < 7 else 1.0), PAL["vermilion"], density=0.97 * sfade, bleed=0.55 + 0.6 * t, rough=0.3,
                  edge=0.35, halo=0.08, grain=0.6, holes=0.25, seed=23, fine_w=0.8)
        ink_layer(C, ink.arr(), lerp(PAL["ink"], T, 0.1), density=0.97 * efade, bleed=0.7 + 1.4 * sstep(0.5, 1, t), rough=0.55,
                  edge=0.45, halo=0.22, halo_col=lerp(PAL["wash3"], T, 0.5), grain=0.5 + 0.3 * t, seed=24)
        frames.append(C.image())
    return frames

# --- Inkwing ---------------------------------------------------------------
ROOT = (256, 268); FEET = 440
WING = {  # local coords: u outward, v up; feathers hang from the arm
    "crane": dict(wrist=(86, 82), tip=(198, 138), nprim=12, nsec=14, plen=(70, 120), slen=(78, 92), pw=15, sw=19, cov=1,
                  pfan=1.05, dark_prim=True, scale_far=0.76, scale_near=0.88),
    "kite":  dict(wrist=(86, 56), tip=(196, 92), nprim=6, nsec=10, plen=(90, 140), slen=(58, 70), pw=12, sw=15, cov=1,
                  pfan=0.85, dark_prim=False, scale_far=0.86),
    "owl":   dict(wrist=(70, 62), tip=(162, 52), scale_far=0.84, scale_near=0.98),
}
# rounded owl silhouette (u outward, v up), leading edge then scalloped trailing edge back to the root
OWL_OUT = [(0, 0), (40, 46), (100, 60), (158, 50), (198, 26), (214, -4), (206, -32), (182, -52), (144, -66), (102, -74), (62, -70), (28, -56), (6, -28)]
OWL_LEAD = [(0, 0), (40, 46), (100, 60), (158, 50), (198, 26), (214, -4)]
def _owl_lead_v(u):
    xs = [p[0] for p in OWL_LEAD]; ys = [p[1] for p in OWL_LEAD]; return float(np.interp(u, xs, ys))

def _wing_xf(side, spread, flap, sc):
    rx, ry = ROOT[0] + side * 16, ROOT[1]
    us = (0.22 + 0.78 * spread) * sc
    def X(u, v, extra=0.0):
        a = flap + 0.16 + extra * (u / 220.0)
        c, s = math.cos(a), math.sin(a)
        uu, vv = u * us, v * sc
        return (rx + side * (uu * c - vv * s), ry - (uu * s + vv * c))
    return X

def owl_wing(masks, side, spread, flap, growth, rng_k, lag=0.0, sc=1.0):
    """Broad, rounded, soft-edged owl wing: wet silhouette wash, irregular rounded feathers, barred primaries,
    slate shingle coverts with faint red cracks."""
    ink, wash, tipm, crack = masks
    X = _wing_xf(side, spread, flap + 0.3, sc); rng = R(rng_k)
    gs = 0.25 + 0.75 * growth
    # soft rounded silhouette
    if growth > 0.15:
        sil = catmull([(u * gs, v * gs) for u, v in OWL_OUT + [OWL_OUT[0]]], 8)
        t_, d_ = wash.tmp()
        d_.polygon([P(*X(u, v, lag)) for u, v in sil], fill=int(85 * cl((growth - 0.15) / 0.4)))
        wash.add(t_)
    # flight feathers: fan from a hand/arm hub out to the scalloped rim, irregular lengths, widths and spacing
    hub_hand, hub_arm = (92, 34), (40, 10)
    rim = catmull([(u, v) for u, v in OWL_OUT[4:13]], 12)  # from upper tip round to the inner trailing edge
    nrim = len(rim); nf = 17
    qs = np.sort(np.clip(np.linspace(0.02, 0.98, nf) + rng.normal(0, 0.018, nf), 0, 1))
    for i, q in enumerate(qs):
        tu, tv = rim[int(q * (nrim - 1))]
        hu = tu * (0.62 if q < 0.35 else 0.85) + rng.normal(0, 4); hv = _owl_lead_v(hu) - 14 + rng.normal(0, 3)
        L = rng.uniform(0.9, 1.1)
        tu, tv = hu + (tu - hu) * L, hv + (tv - hv) * L
        g = cl((growth - q * 0.35) / 0.6)
        if g <= 0.02: continue
        bend = rng.normal(0, 6)
        pts = [(hu + (tu - hu) * s_ * g + bend * math.sin(np.pi * s_), hv + (tv - hv) * s_ * g) for s_ in np.linspace(0, 1, 5)]
        pts = [(u * gs, v * gs) for u, v in pts]
        fw = rng.uniform(20, 31)
        rk = R(rng_k + 40 + i)
        W = [X(u, v, lag) for u, v in pts]
        brush(wash, W, fw * sc, rk, dry=0.2, wet=0.7, taper=(0.12, 0.16), bristles=9)
        brush(tipm, W[2:], fw * 0.95 * sc, rk, dry=0.3, wet=0.6, taper=(0.35, 0.14), bristles=8)  # dark rounded slate tip
        if rng.random() < 0.85:  # shaft line, partial length
            s0 = rng.uniform(0.05, 0.25)
            brush(ink, [X(u + side * 0, v - 2, lag) for u, v in pts], rng.uniform(2.2, 4.2) * sc, rk, t0=s0, t1=rng.uniform(0.8, 1.0), local=True,
                  dry=0.6, wet=0.3, taper=(0.2, 0.4), bristles=3)
        if q < 0.6 and g > 0.6:  # owl barring: short dry dabs across the feather
            for b in range(rng.integers(2, 4)):
                s_ = rng.uniform(0.45, 0.92); u0, v0 = pts[0]; u1, v1 = pts[-1]
                bu, bv = u0 + (u1 - u0) * s_, v0 + (v1 - v0) * s_
                dx, dy = (v1 - v0), -(u1 - u0); ln = math.hypot(dx, dy) + 1e-6; dx, dy = dx / ln * fw * 0.32, dy / ln * fw * 0.32
                brush(ink, [X(bu - dx, bv - dy, lag), X(bu + dx, bv + dy, lag)], rng.uniform(2.5, 4.5) * sc, R(rng_k + 90 + i * 5 + b), dry=0.8, wet=0.2, taper=(0.3, 0.3), bristles=3)
    # coverts: irregular rows of slate shingles over the upper wing
    if growth > 0.3:
        for i in range(26):
            q = rng.random(); row = rng.integers(0, 3)
            u = lerp(16, 170, q) + rng.normal(0, 6); v = _owl_lead_v(lerp(16, 170, q)) - 10 - row * 18 + rng.normal(0, 4)
            g = cl((growth - 0.3 - q * 0.3) / 0.4)
            if g <= 0: continue
            L = rng.uniform(18, 32) * g; ang = -np.pi / 2 + 0.2 + 0.6 * q + rng.normal(0, 0.15)
            pts = [((u + math.cos(ang) * L * s_) * gs, (v + math.sin(ang) * L * s_) * gs) for s_ in (0, 0.5, 1)]
            rk = R(rng_k + 200 + i)
            brush(wash, [X(a, b, lag) for a, b in pts], rng.uniform(16, 26) * sc, rk, dry=0.3, wet=0.6, taper=(0.15, 0.25), bristles=7)
            if rng.random() < 0.65:
                brush(ink, [X(a, b - 2, lag) for a, b in pts[1:]], rng.uniform(2.0, 3.6) * sc, rk, dry=0.55, wet=0.3, taper=(0.2, 0.5), bristles=3)
            if rng.random() < 0.16:
                c0 = X(*pts[0], lag)
                brush(crack, [c0, (c0[0] + side * 6, c0[1] + 7), (c0[0] + side * 1, c0[1] + 15), (c0[0] + side * 5, c0[1] + 24)],
                      1.9, R(rng_k + 300 + i), dry=0.2, wet=0.8, taper=(0, 0.3), bristles=2)
    ga = cl(growth / 0.35)
    if ga > 0:
        arm = [(u * gs, v * gs) for u, v in OWL_LEAD[:5]]
        brush(ink, [X(u, v, lag) for u, v in arm], 15 * sc, R(rng_k + 500), t1=ga, dry=0.55, wet=0.5, taper=(0.1, 0.6), bristles=16, head=False)
    return [X(206 * gs, -32 * gs, lag)]

def wing(masks, kind, side, spread, flap, growth, rng_k, lag=0.0, sc=1.0):
    if kind == "owl": return owl_wing(masks, side, spread, flap, growth, rng_k, lag, sc)
    W = WING[kind]; ink, wash, tipm, crack = masks
    X = _wing_xf(side, spread, flap, sc)
    wr, tp = W["wrist"], W["tip"]
    arm = [(0, 0), (wr[0] * 0.5, wr[1] * 0.75), wr, ((wr[0] + tp[0]) / 2, (wr[1] + tp[1]) / 2 + 6), tp]
    armL = catmull(arm, 8); nA = len(armL)
    flen = 0.3 + 0.7 * spread
    jr = R(rng_k + 999)  # irregularity: uneven spacing, lengths, angles, widths, the odd extra/missing feather
    feathers = []
    for i in range(W["nsec"] + 2):
        q = cl((i + 0.5) / (W["nsec"] + 2) + jr.normal(0, 0.025)); idx = int(q * nA * 0.42)
        if jr.random() < 0.08: continue
        bu, bv = armL[idx]; L = lerp(W["slen"][0], W["slen"][1], q) * flen
        feathers.append(("sec", q, (bu, bv), -np.pi / 2 + 0.05 + 0.3 * q * spread, L, W["sw"]))
    for i in range(W["nprim"]):
        q = cl((i + 0.5) / W["nprim"] + jr.normal(0, 0.03)); idx = int(nA * 0.42 + q * (nA * 0.58 - 1))
        bu, bv = armL[idx]; L = lerp(W["plen"][0], W["plen"][1], q ** 0.7) * flen
        feathers.append(("prim", q, (bu, bv), -np.pi / 2 + 0.35 + W["pfan"] * q * spread, L, W["pw"]))
    order = sorted(range(len(feathers)), key=lambda j: (0 if feathers[j][0] == "sec" else 1, feathers[j][1]))
    for j in order:
        kindf, q, (bu, bv), ang, L, fw = feathers[j]
        pos = j / len(feathers)
        g = cl((growth - pos * 0.45) / 0.55)
        if g <= 0.02: continue
        rk = R(rng_k + j)
        Lg = L * g * rk.uniform(0.78, 1.12); ang += rk.normal(0, 0.09); fw = fw * rk.uniform(0.8, 1.25)
        bend = -0.15 + lag + rk.normal(0, 0.1)
        pts = [X(bu + math.cos(ang + bend * s_) * Lg * s_, bv + math.sin(ang + bend * s_) * Lg * s_, lag * 0.6) for s_ in np.linspace(0, 1, 5)]
        brush(wash, pts, fw * sc, rk, dry=0.25, wet=0.6, taper=(0.15, 0.5), bristles=8)
        if kindf == "prim" and W["dark_prim"]:
            brush(ink, pts[1:], fw * 0.85 * sc, rk, t1=rk.uniform(0.85, 1.0), dry=rk.uniform(0.4, 0.7), wet=0.4, taper=(0.1, 0.55), bristles=10)
        elif rk.random() < 0.8:
            edge = [(x + side * 2, y + 1) for x, y in pts]
            brush(ink, edge, max(2.5, fw * 0.28) * sc, rk, t0=rk.uniform(0, 0.3), t1=rk.uniform(0.7, 1.0), local=True, dry=0.6, wet=0.3, taper=(0.1, 0.6), bristles=4)
        if kind == "kite" and kindf == "prim":
            brush(tipm, pts[3:], fw * 0.9 * sc, rk, dry=0.4, wet=0.5, taper=(0.1, 0.5), bristles=6)
    ga = cl(growth / 0.35)
    if ga > 0:
        brush(ink, [X(u, v) for u, v in arm], 13 * sc, R(rng_k + 500), t1=ga, dry=0.5, wet=0.5, taper=(0.1, 0.5), bristles=14, head=False)
    return [X(*tp)]

def render_wings(C, el, spread, flap, growth, f, fade=1.0, lag=0.0, extra=None):
    E = CONFIG["elements"][el]; T = hexrgb(E["tint"]); kind = E["wing"]; size = C.size
    far = [Mask(size) for _ in range(4)]; near = [Mask(size) for _ in range(4)]
    tips = wing(far, kind, +1, spread, flap * 0.9, growth, 600, lag, WING[kind]["scale_far"])
    tips += wing(near, kind, -1, spread, flap, growth, 700, lag, WING[kind].get("scale_near", 1.0))
    washc = lerp(PAL["wash3"], T, 0.55); inkc = lerp(PAL["ink"], T, 0.12)
    owl = kind == "owl"
    for layer, k in ((far, 0.6), (near, 1.0)):
        ink, wash, tipm, crack = layer
        ink_layer(C, wash.arr(), washc, density=(0.7 if owl else 0.62) * k * fade, bleed=2.2 if owl else 1.4, rough=0.75 if owl else 0.6,
                  edge=0.3 if owl else 0.4, halo=0.3 if owl else 0.2, halo_col=T, grain=0.75, seed=30, fine_w=0.35 if owl else 0.45)
        if owl:
            ink_layer(C, tipm.arr(), lerp(PAL["wash1"], T, 0.35), density=0.7 * k * fade, bleed=1.3, rough=0.6, edge=0.45, halo=0.15, halo_col=T, grain=0.7, seed=31)
        else:
            ink_layer(C, tipm.arr(), lerp(T, PAL["vermilion"], 0.25), density=(0.55 if extra is None else extra.get("tip", 0.55)) * k * fade,
                      bleed=1.2, rough=0.6, edge=0.3, halo=0.3, grain=0.7, seed=31)
        ink_layer(C, ink.arr(), inkc, density=0.95 * k * fade, bleed=0.9 if owl else 0.7, rough=0.5, edge=0.45, grain=0.5, seed=32)
        ink_layer(C, crack.arr(), PAL["vermilion"], density=(0.0 if extra is None else extra.get("crack", 0.45)) * k * fade if owl else 0,
                  bleed=0.9, rough=0.3, edge=0.2, halo=0.4, grain=0.4, seed=33)
    return tips

def vortex(f, ink, dry_m, tint, red, cx0, cy0, cx1, cy1, V):
    """Opening ink vortex: tapering strokes spiral inward with angular acceleration, wet tint bleed,
    a dry speed-streak on the heavy strands, droplets flung off tangentially, a wet core that becomes the wing root."""
    k_c = eout(cl(f / 13), 1.6)
    cx, cy = lerp(cx0, cx1, k_c), lerp(cy0, cy1, k_c)
    theta = 0.16 * f + 0.026 * f * f           # accelerating spin
    shrink = 1 - 0.72 * eout(cl(f / 14), 1.5)
    def spiral(s_, rad_scale=1.0, nq=22):
        pts = []
        for q in np.linspace(0, 1, nq):
            a = s_["a0"] + theta * s_["spd"] + q * 2 * np.pi * s_["lp"]
            r = s_["R"] * shrink * rad_scale * math.exp(-1.9 * q) * (1 + 0.07 * math.sin(q * 11 + s_["a0"])) + 5
            pts.append((cx + r * math.cos(a), cy + r * s_["tilt"] * math.sin(a)))
        return pts
    for k, s_ in enumerate(V["strands"]):
        head = cl(0.22 + f / 6.5 + s_["d"]); tail = cl((f - 5 - s_["d"] * 10) / 9)
        if head <= tail + 0.02: continue
        pts = spiral(s_)
        prs = lambda q, k=k: 0.65 + 0.55 * np.sin(q * 6.5 + k) ** 2
        brush(ink, pts, s_["w"], R(820 + k), t0=tail, t1=head, local=True, dry=s_["dry"], wet=0.45, taper=(0.06, 0.85),
              bristles=max(5, int(s_["w"] * 0.9)), press=prs)
        brush(tint, pts, s_["w"] * 1.8 + 5, R(840 + k), t0=tail, t1=head, local=True, dry=0.1, wet=0.8, taper=(0.1, 0.8), bristles=6)
        if s_["w"] > 11:
            brush(dry_m, spiral(s_, 1.12), s_["w"] * 0.45, R(860 + k), t0=tail, t1=head * 0.8, local=True, dry=0.95, wet=0.0,
                  taper=(0.2, 0.6), bristles=6)
    for d in V["drops"]:
        age = f - d["b"]
        if not (0 <= age < d["life"]): continue
        s_ = V["strands"][d["k"]]
        # birth position on the strand, frozen at birth time
        fb = d["b"]; thb = 0.16 * fb + 0.026 * fb * fb; shb = 1 - 0.72 * eout(cl(fb / 14), 1.5)
        kb = eout(cl(fb / 13), 1.6); bcx, bcy = lerp(cx0, cx1, kb), lerp(cy0, cy1, kb)
        a = s_["a0"] + thb * s_["spd"] + d["q"] * 2 * np.pi * s_["lp"]
        r = s_["R"] * shb * math.exp(-1.9 * d["q"]) + 5
        px, py = bcx + r * math.cos(a), bcy + r * s_["tilt"] * math.sin(a)
        tx, ty = -math.sin(a), s_["tilt"] * math.cos(a)       # spin direction (tangent)
        vx, vy = tx * d["v"] + math.cos(a) * d["v"] * 0.35, ty * d["v"] + math.sin(a) * d["v"] * 0.25 + 2 * age
        x, y = px + vx * age * (1 - 0.06 * age), py + vy * age * (1 - 0.06 * age)
        sz = d["s"] * (1 - age / (d["life"] + 1) * 0.6); el = 1 + 2.2 * (1 - age / d["life"])
        poly = ell(x, y, sz * el, sz, math.atan2(vy, vx), 12)
        (red if d["red"] else ink).d.polygon(poly, fill=255)
    if 4 <= f <= 16:
        rr = lerp(5, 20, cl((f - 4) / 7)) * (1 - 0.6 * cl((f - 12) / 4))
        S = V["core"]; draw_splat(ink, None, cx, cy, S, 1.0) if False else None
        ink.d.polygon([P(cx + rr * (1 + 0.2 * math.sin(3 * a_ + f)) * math.cos(a_), cy + rr * 0.8 * (1 + 0.2 * math.sin(3 * a_ + f)) * math.sin(a_))
                       for a_ in np.linspace(0, 2 * np.pi, 24, endpoint=False)], fill=255)
    return cx, cy

def fx_inkwing(el):
    size = CONFIG["frame_big"]; n = F["inkwing"]; E = CONFIG["elements"][el]; T = hexrgb(E["tint"]); frames = []
    rng = R(800); cx0, cy0 = 256, 318; cx1, cy1 = ROOT[0], ROOT[1] + 10
    ws = np.concatenate([np.exp(rng.uniform(np.log(5), np.log(20), 9)), rng.uniform(2, 3.5, 5)])
    V = {"strands": [dict(a0=k * 2 * np.pi / 10 + rng.normal(0, 0.35), w=float(ws[k]), R=rng.uniform(150, 250), tilt=rng.uniform(0.42, 0.6),
                          lp=rng.uniform(0.9, 1.6), spd=rng.uniform(0.85, 1.2), dry=rng.uniform(0.3, 0.85), d=rng.uniform(0, 0.15)) for k in range(14)],
         "core": None}
    V["drops"] = [dict(k=int(rng.integers(0, 9)), b=int(rng.integers(1, 15)), q=rng.uniform(0.0, 0.3), v=rng.uniform(14, 34),
                       s=rng.uniform(1.6, 5.5), life=int(rng.integers(3, 7)), red=rng.random() < 0.1) for _ in range(130)]
    burst = make_splat(R(810), 22, spikes=0, drops=26, red=0.0)
    redfl = make_splat(R(811), 30, spikes=0, drops=16, red=1.0)
    for f in range(n):
        t = f / (n - 1); C = Canvas(size); ink, red, tint, dry_m = Mask(size), Mask(size), Mask(size), Mask(size)
        sfade = 1 - sstep(11, 18, f)
        if f <= 18:
            vx, vy = vortex(f, ink, dry_m, tint, red, cx0, cy0, cx1, cy1, V)
            if 3 <= f <= 14:
                rr = 5 + 2 * math.sin(f * 1.3) + (5 if f >= 9 else 0)
                red.d.polygon(ell(vx, vy - 2, rr, rr * 1.1, 0.3, 16), fill=255)
            if 9 <= f <= 14: draw_splat(red, None, vx, vy - 2, redfl, cl((f - 9) / 4), blob=False, reach=2.2)
        ink_layer(C, tint.arr(), lerp(T, PAL["paper_shade"], 0.1), density=0.5 * sfade, bleed=3.0, rough=0.8, edge=0.3, grain=0.8, seed=40)
        ink_layer(C, dry_m.arr(), PAL["wash2"], density=0.8 * sfade, bleed=0.4, rough=0.3, edge=0.2, grain=0.9, seed=44, fine_w=0.85)
        ink_layer(C, ink.arr(), lerp(PAL["ink"], T, 0.1), density=0.96 * sfade, bleed=1.1, rough=0.6, edge=0.5, halo=0.32, halo_col=T, grain=0.55, seed=41)
        growth = eout(cl((f - 8) / 12), 1.8); spread = eout(cl((f - 10) / 11), 2)
        flap = 0.22 * math.sin(2 * np.pi * (f - 20) / 9.0) * (1 - (f - 20) / 9.0) if f >= 20 else 0.28 * (1 - spread) - 0.05 * spread
        if growth > 0:
            tips = render_wings(C, el, spread, flap, growth, f, extra={"tip": 0.55, "crack": 0.45 * cl((f - 18) / 5)})
            if 21 <= f <= 27:
                dm = Mask(size)
                for tx_, ty_ in tips: draw_splat(dm, None, tx_, ty_ + 30, burst, cl((f - 20.5) / 5), blob=False, reach=1.2)
                ink_layer(C, dm.arr(), lerp(PAL["ink"], T, 0.15), density=0.9 * (1 - cl((f - 24) / 4)), bleed=0.7, rough=0.4, edge=0.4, grain=0.5, seed=42)
        ink_layer(C, red.arr(), PAL["vermilion"], density=0.95, bleed=0.7, rough=0.4, edge=0.4, halo=0.15, grain=0.5, seed=43)
        frames.append(C.image())
    return frames

def fx_inkwing_loop(el):
    size = CONFIG["frame_big"]; n = F["inkwing_loop"]; E = CONFIG["elements"][el]; T = hexrgb(E["tint"]); frames = []
    rng = R(900); kind = E["wing"]
    wisps = [dict(ph=k / 5 + rng.uniform(-0.04, 0.04), side=(-1 if k % 2 else 1), y=rng.uniform(-30, 60), x=rng.uniform(0, 80)) for k in range(5)]
    ash = [dict(ph=rng.random(), x=rng.uniform(40, 472), y0=rng.uniform(160, 330), s=rng.uniform(1.2, 2.6), red=rng.random() < 0.3) for _ in range(26)]
    for f in range(n):
        C = Canvas(size); ph = f / n
        flap = 0.10 * math.sin(2 * np.pi * ph); lag = 0.06 * math.sin(2 * np.pi * ph - 1.2)
        fx = Mask(size); red = Mask(size)
        if kind == "crane":
            for k, w_ in enumerate(wisps):
                q = (ph + w_["ph"]) % 1.0
                x0 = 256 + w_["side"] * (150 + w_["x"] + 90 * q); y0 = 200 + w_["y"] - 30 * q
                pts = [(x0 - w_["side"] * 40 * (1 - s_), y0 + 10 * math.sin(s_ * 3 + q * 6)) for s_ in np.linspace(0, 1, 5)]
                dens = math.sin(np.pi * q)
                if dens > 0.15: brush(fx, pts, 4 + 3 * dens, R(910 + k), dry=0.8, wet=0.1, taper=(0.4, 0.5), bristles=5)
        else:
            for k, a in enumerate(ash):
                q = (ph + a["ph"]) % 1.0
                if kind == "kite":
                    x = a["x"] + 10 * math.sin(q * 6.28 + k); y = a["y0"] - 90 * q
                else:
                    x = a["x"]; y = a["y0"] + 90 * q + 60
                s_ = a["s"] * math.sin(np.pi * q) + 0.3
                tgt = red if (a["red"] and kind == "kite") else fx
                if kind == "owl":
                    tgt.d.polygon([P(x + s_ * 1.6 * math.cos(j * 1.9 + k), y + s_ * 1.3 * math.sin(j * 1.9 + k)) for j in range(4)], fill=255)
                else:
                    tgt.d.ellipse([(x - s_) * SS, (y - s_) * SS, (x + s_) * SS, (y + s_) * SS], fill=255)
        pulse = 0.5 + 0.5 * math.sin(2 * np.pi * ph)
        render_wings(C, el, 1.0, flap, 1.0, f, lag=lag, extra={"tip": 0.45 + 0.25 * pulse, "crack": 0.3 + 0.3 * pulse})
        ink_layer(C, fx.arr(), lerp(PAL["wash2"], T, 0.3), density=0.8, bleed=0.6, rough=0.4, edge=0.3, grain=0.6, seed=50)
        ink_layer(C, red.arr(), lerp(T, PAL["vermilion"], 0.5), density=0.8, bleed=0.6, rough=0.3, edge=0.3, halo=0.3, grain=0.5, seed=51)
        frames.append(C.image())
    return frames

# --- Enemy death -------------------------------------------------------------
def death_fields(size):
    N = size * SS
    nn = 0.45 * nz(N, "huge", 61) + 0.35 * nz(N, "coarse", 62) + 0.2 * nz(N, "mid", 63)
    nn = (nn - nn.min()) / (nn.max() - nn.min())
    yy = np.linspace(0, 1, N, dtype=np.float32)[:, None]
    D = 0.58 * nn + 0.42 * yy                      # top unwrites first, the feet last
    # paper-fibre wicking: the dissolve front creeps along fibres, so perturb it with grain and fine noise
    return D + 0.07 * (nz(N, "grain", 0) - 0.5) + 0.035 * nz(N, "fine", 64)

def silhouette(size):
    m = Mask(size); rng = R(1000)
    S = make_splat(rng, 50, spikes=0, drops=0); draw_splat(m, None, 140, 168, S, 1.0)
    S2 = make_splat(rng, 30, spikes=0, drops=0); draw_splat(m, None, 92, 140, S2, 1.0)
    for k, (x0, x1) in enumerate([(112, 98), (150, 150), (182, 196)]):
        brush(m, [(x0, 185), (x0 + (x1 - x0) * 0.5, 215), (x1, 240)], 16, R(1010 + k), dry=0.3, wet=0.6, taper=(0.0, 0.5))
    brush(m, [(186, 160), (214, 132), (226, 96), (210, 84)], 15, R(1020), dry=0.5, wet=0.5, taper=(0.05, 0.7))
    brush(m, [(70, 128), (58, 118), (54, 104)], 7, R(1021), dry=0.5, wet=0.5)
    brush(m, [(84, 122), (80, 106), (86, 96)], 7, R(1022), dry=0.5, wet=0.5)
    m.d.ellipse([P(76, 136)[0], P(76, 136)[1], P(86, 146)[0], P(86, 146)[1]], fill=0)
    return m.arr()

def fx_death():
    size = CONFIG["frame"]; n = F["death"]; D = death_fields(size); N = size * SS
    sil = silhouette(size); rng = R(1100)
    drips = [dict(x=x, y=rng.uniform(178, 214), w=rng.uniform(3.5, 7.5), d=rng.uniform(0.15, 0.5), L=rng.uniform(22, 48))
             for x in np.sort(rng.uniform(84, 196, 8))]
    flecks = [dict(x=rng.uniform(60, 210), y=rng.uniform(80, 220), vx=rng.normal(0, 40), vy=-rng.uniform(20, 70), s=rng.uniform(1, 2.6), d=rng.uniform(0, 0.6)) for _ in range(30)]
    pud = make_splat(R(1150), 40, spikes=0, drops=10, red=0.0)
    masks, overlays, demos = [], [], []
    for f in range(n):
        t = f / (n - 1); lvl = lerp(-0.1, 1.12, eout(t, 1.3) * 0.15 + t * 0.85)
        keep = sstep(lvl - 0.09, lvl + 0.09, D)
        mk = np.dstack([np.ones_like(keep)] * 3 + [keep]).reshape(size, SS, size, SS, 4).mean((1, 3))
        masks.append(Image.fromarray((mk * 255).round().astype(np.uint8), "RGBA"))
        ov = Mask(size); trail = Mask(size); cv = Mask(size)
        for k, dp in enumerate(drips):
            q = cl((t - dp["d"]) / 0.42)
            if q <= 0: continue
            y0 = dp["y"] + 6 * q * q; L = dp["L"] * eout(q, 1.5)
            pts = [(dp["x"], y0), (dp["x"] + 1.0, y0 + L * 0.55), (dp["x"] - 0.5, min(244, y0 + L))]
            # tapered drip: hairline at the top swelling into a bead, a lighter wet trail behind it
            brush(ov, pts, dp["w"] * (1 - 0.35 * q), R(1110 + k), dry=0.15, wet=0.9, taper=(0.75, 0.0),
                  press=lambda s_: 0.25 + 0.75 * s_ ** 1.6, head=True)
            brush(trail, [(x + 0.5, y - 4) for x, y in pts], dp["w"] * 1.4, R(1130 + k), dry=0.3, wet=0.6, taper=(0.6, 0.2))
        pg = eout(cl((t - 0.2) / 0.45), 2); pf = 1 - sstep(0.68, 1, t)
        if pg > 0:
            pm = Mask(size); draw_splat(pm, None, 134, size / 2, pud, pg, blob=True, reach=0.7)
            h = max(2, int(N * 0.2)); pa = np.asarray(pm.im.resize((N, h)), np.float32) / 255
            flat = np.zeros((N, N), np.float32); yc = int(238 * SS); y0 = yc - h // 2; y1 = min(N, y0 + h)
            flat[y0:y1] = pa[:y1 - y0]
            ov.add(Image.fromarray((flat * 255).astype(np.uint8)))
        for k, fl in enumerate(flecks):
            q = cl((t - fl["d"]) / 0.5)
            if 0 < q < 1:
                x = fl["x"] + fl["vx"] * q; y = fl["y"] + fl["vy"] * q; s_ = fl["s"] * (1 - q * 0.6)
                cv.d.polygon(ell(x, y, s_ * 1.6, s_, math.atan2(fl["vy"], fl["vx"]), 10), fill=255)
        Co = Canvas(size)
        ink_layer(Co, trail.arr(), PAL["wash2"], density=0.45 * pf, bleed=1.2 + 1.5 * t, rough=0.6, edge=0.3, grain=0.8, seed=74)
        ink_layer(Co, ov.arr(), PAL["ink"], density=0.92 * pf, bleed=0.8 + 2.2 * sstep(0.5, 1, t), rough=0.55, edge=0.45, halo=0.3, halo_col=PAL["wash3"],
                  grain=0.6 + 0.3 * t, seed=70)
        ink_layer(Co, cv.arr(), PAL["wash1"], density=0.85 * (1 - t), bleed=0.6, rough=0.3, edge=0.3, grain=0.6, seed=71)
        overlays.append(Co.image())
        Cd = Canvas(size)
        gone = sil * (1 - keep)
        # unwritten ink wicks outward into the paper as a widening, fading grey wash
        wick = ndi.gaussian_filter(gone, (1.5 + 5 * t) * SS) * (0.8 + 0.4 * nz(N, "coarse", 75))
        ink_layer(Cd, np.clip(wick * 1.6, 0, 1), PAL["wash2"], density=0.55 * (1 - sstep(0.55, 1, t)), bleed=1.5, rough=0.8, edge=0.35, grain=1.0, seed=73, fine_w=0.3)
        front = sil * np.clip(keep * (1 - keep) * 4, 0, 1)
        ink_layer(Cd, np.clip(front * (0.6 + 0.8 * nz(N, "grain", 0)), 0, 1), PAL["wash1"], density=0.7, bleed=0.6, rough=0.6, edge=0.2, grain=0.9, seed=76, fine_w=0.8)
        ink_layer(Cd, sil * keep, PAL["ink"], density=0.97, bleed=0.7, rough=0.45, edge=0.45, halo=0.15, halo_col=PAL["wash3"], grain=0.45, seed=72)
        di = Cd.image(); di.alpha_composite(overlays[-1]); demos.append(di)
    return masks, overlays, demos

# ---------------------------------------------------------------- output
def paper(size):
    N = size; g = bank(max(256, size))["grain"][:N, :N]; c = nz(max(256, size), "huge", 5)[:N, :N]
    base = PAL["paper"][None, None] * 255 - (g[..., None] * 10 + np.clip(c, 0, 1)[..., None] * 8) * (1 - PAL["paper_shade"] / PAL["paper"])[None, None] * 4
    return Image.fromarray(np.clip(base, 0, 255).astype(np.uint8), "RGB").convert("RGBA")

def save_strip(key, frames, fps, loop, anchor, note, layer="over"):
    out = CONFIG["out_dir"]; os.makedirs(out, exist_ok=True)
    fw, fh = frames[0].size; n = len(frames)
    strip = Image.new("RGBA", (fw * n, fh), (0, 0, 0, 0))
    for i, fr in enumerate(frames): strip.paste(fr, (i * fw, 0))
    a = np.asarray(strip).copy(); a[a[..., 3] == 0, :3] = 0; strip = Image.fromarray(a, "RGBA")
    srcs = []
    for fmt in CONFIG["formats"]:
        p = os.path.join(out, f"{key}.{fmt}")
        if fmt == "webp": strip.save(p, "WEBP", lossless=True, method=4)
        else: strip.save(p, "PNG", optimize=True)
        srcs.append(os.path.basename(p))
    meta = {"key": key, "src": "fx/" + srcs[0], "w": fw * n, "h": fh, "frames": n, "fw": fw, "fh": fh, "fps": fps,
            "loop": loop, "anchor": anchor, "layer": layer, "note": note}
    with open(os.path.join(out, f"{key}.json"), "w") as fp: json.dump(meta, fp, indent=2)
    if CONFIG["previews"]:
        pv = os.path.join(out, "previews"); os.makedirs(pv, exist_ok=True)
        pap = paper(fw); comp = []
        for fr in frames:
            c = pap.copy(); c.alpha_composite(fr); comp.append(c.convert("RGB"))
        comp[0].save(os.path.join(pv, f"{key}.gif"), save_all=True, append_images=comp[1:], duration=int(1000 / fps), loop=0)
        cols = min(n, 6 if fw > 256 else 8); rows = (n + cols - 1) // cols; pad = 4
        sheet = Image.new("RGB", (cols * (fw + pad) + pad, rows * (fh + pad) + pad + 22), (200, 194, 180))
        d = ImageDraw.Draw(sheet)
        try: font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 14)
        except Exception: font = None
        d.text((6, 4), f"{key}  {n}f  {fw}x{fh}  {fps}fps  loop={loop}", fill=(27, 24, 19), font=font)
        for i, c in enumerate(comp):
            x = pad + (i % cols) * (fw + pad); y = 22 + pad + (i // cols) * (fh + pad)
            sheet.paste(c, (x, y)); d.text((x + 4, y + 2), str(i), fill=(109, 103, 91), font=font)
        sheet.save(os.path.join(pv, f"{key}_sheet.jpg"), quality=88)
    return meta

C_ = "center on the impact point"
def job(key):
    E = CONFIG["elements"]
    if key == "fx-hit-light": return [save_strip(key, fx_hit(False), FPS, False, [0.4375, 0.5], C_ + "; splash flies to +x (party hitting a left-facing enemy). Flip horizontally for hits on the party.")]
    if key == "fx-hit-heavy": return [save_strip(key, fx_hit(True), FPS, False, [0.4375, 0.5], C_ + "; heavy/finisher variant with shock ring. Flip horizontally for hits on the party.")]
    if key == "fx-brushstroke-clean-line": return [save_strip(key, fx_clean_line(), FPS, False, [0.5, 0.5], "Clean Line (perfect press). Center on the Brushstroke timing ring; enso closes, slash, vermilion seal pops.")]
    if key == "fx-brushstroke-fail": return [save_strip(key, fx_fail(), FPS, False, [0.5, 0.5], "Missed press. Grey, dry-cracked broken ring and stroke that smear and crumble. No red.")]
    if key == "fx-seal-mark": return [save_strip(key, fx_seal_mark(), FPS, False, [0.5, 0.5], "Seal Arts: one red seal stamping onto the path. Hold the last frame; place one per seal (party.json seal.seals).")]
    if key == "fx-seal-pass": return [save_strip(key, fx_seal_pass(), FPS, False, [0.5, 0.5], "Seal Arts: plays on a seal when the press lands as the brush passes it (vermilion flare).")]
    for el in E:
        if key == f"fx-seal-{el}":
            return [save_strip(key, fx_seal(el), FPS, False, [TGT[0] / 512, GROUND / 512],
                               f"Seal Art, {el} ({E[el]['form']}). Anchor = target enemy's feet. Frames 0-2 seal stamps, brush passes over it ~f4 (press moment), effect f6-17.")]
        if key == f"fx-inkwing-{el}":
            return [save_strip(key, fx_inkwing(el), FPS, False, [0.5, FEET / 512],
                               f"Inkwing unfurl, {E[el]['form']}. Anchor = character feet (sprite anchor). Draw BEHIND the battle sprite. Hand off to {key}-loop.", "behind")]
        if key == f"fx-inkwing-{el}-loop":
            return [save_strip(key, fx_inkwing_loop(el), FPS, True, [0.5, FEET / 512],
                               f"Held {E[el]['form']} wings, seamless loop. Anchor = character feet. Draw BEHIND the battle sprite.", "behind")]
    if key == "fx-death":
        m, o, d = fx_death()
        return [save_strip("fx-death-mask", m, FPS, False, [0.5, 1.0], "Alpha mask: draw the enemy frame, then this frame with globalCompositeOperation='destination-in' (white RGB, alpha = keep). Then draw fx-death-ink on top.", "mask"),
                save_strip("fx-death-ink", o, FPS, False, [0.5, 1.0], "Ink overlay for the dissolve: drips, ground puddle that soaks into the paper, drifting flecks. Anchor = enemy feet."),
                save_strip("fx-death-demo", d, FPS, False, [0.5, 1.0], "Demo/fallback: generic left-facing ink beast dissolving (mask + edge wash + overlay applied).")]
    raise SystemExit(f"unknown key {key}")

ALL = ["fx-hit-light", "fx-hit-heavy", "fx-brushstroke-clean-line", "fx-brushstroke-fail", "fx-seal-mark", "fx-seal-pass"] + \
      [f"fx-seal-{e}" for e in CONFIG["elements"]] + [f"fx-inkwing-{e}" for e in CONFIG["elements"]] + \
      [f"fx-inkwing-{e}-loop" for e in CONFIG["elements"]] + ["fx-death"]

def write_manifest():
    out = CONFIG["out_dir"]; imgs = {}
    for fn in sorted(os.listdir(out)):
        if fn.startswith("fx-") and fn.endswith(".json"):
            m = json.load(open(os.path.join(out, fn)))
            imgs[m["key"]] = {k: m[k] for k in ("src", "w", "h", "frames", "fw", "fh", "fps", "anchor", "loop")}
    json.dump({"images": imgs}, open(os.path.join(out, "manifest.json"), "w"), indent=2)
    return imgs

if __name__ == "__main__":
    keys = sys.argv[1:] or ALL
    from multiprocessing import Pool
    with Pool(min(len(keys), os.cpu_count() or 2)) as pool:
        for res in pool.imap_unordered(job, keys):
            for m in res: print(f"{m['key']:30s} {m['frames']:3d}f {m['fw']}x{m['fh']}")
    imgs = write_manifest(); print(f"manifest: {len(imgs)} keys")
    if CONFIG["previews"]:
        pv = os.path.join(CONFIG["out_dir"], "previews")
        sheets = [Image.open(os.path.join(pv, k + ".gif")).convert("RGB") for k in sorted(imgs) if os.path.exists(os.path.join(pv, k + ".gif"))]
        # overview: middle frame of each strip
        tiles = []
        for k in sorted(imgs):
            g = Image.open(os.path.join(pv, k + ".gif")); g.seek(min(g.n_frames - 1, g.n_frames * 2 // 3))
            tiles.append((k, g.convert("RGB").resize((256, 256))))
        cols = 6; rows = (len(tiles) + cols - 1) // cols
        ov = Image.new("RGB", (cols * 260 + 4, rows * 280 + 4), (200, 194, 180)); d = ImageDraw.Draw(ov)
        for i, (k, im) in enumerate(tiles):
            x, y = 4 + (i % cols) * 260, 4 + (i // cols) * 280; ov.paste(im, (x, y + 20)); d.text((x, y + 4), k, fill=(27, 24, 19))
        ov.save(os.path.join(pv, "overview.jpg"), quality=88)
