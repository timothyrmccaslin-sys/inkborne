#!/usr/bin/env python3
"""
Sumikage Wood ambient loops for Inkborne (Lucy, art).

Seamless 12 fps overlay loops, 2560x1440, WebP with straight alpha:
  1. poi-forest-mist    — distant drifting ink-wash fog (FX slot A, parallax 0.3)
  2. poi-forest-leaves  — falling bamboo leaves and pine needles (FX slot B, parallax 0.7)

Usage (from team/art/ambient, or by path):
  python3 src/gen_ambient.py              # both loops + previews + manifest
  python3 src/gen_ambient.py mist
  python3 src/gen_ambient.py leaves
  python3 src/gen_ambient.py --preview    # rebuild previews from existing frames
  python3 src/gen_ambient.py --frames 8   # short test render

Nothing here is loaded by the game directly; Marc copies from team/art/.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]  # team/art/ambient
ART = ROOT.parent                           # team/art

# SPEC section 5 palette
PAPER = np.array([0xEC, 0xE6, 0xD8], dtype=np.float64)
PAPER_SHADE = np.array([0xD9, 0xD0, 0xBC], dtype=np.float64)
INK = np.array([0x1B, 0x18, 0x13], dtype=np.float64)
WASH1 = np.array([0x3B, 0x37, 0x30], dtype=np.float64)
WASH2 = np.array([0x6D, 0x67, 0x5B], dtype=np.float64)
WASH3 = np.array([0xA3, 0x9C, 0x8C], dtype=np.float64)
VERMILION = np.array([0xB3, 0x26, 0x1E], dtype=np.float64)

W, H = 2560, 1440
FPS = 12
N_DEFAULT = 72  # 6 s — slow enough for mist, one screen-fall for leaves
SEED = 20261115


# ---------------------------------------------------------------------------
# Noise / ink helpers
# ---------------------------------------------------------------------------

def periodic_volume(nt: int, ny: int, nx: int, rng: np.random.Generator, sigma) -> np.ndarray:
    """Unit-variance Gaussian field, periodic on every axis (so a time loop is seamless)."""
    g = rng.normal(0.0, 1.0, (nt, ny, nx)).astype(np.float32)
    g = ndi.gaussian_filter(g, sigma, mode="wrap")
    g -= g.mean()
    std = float(g.std())
    if std > 1e-8:
        g /= std
    return g


def zoom_slice(vol_t: np.ndarray, height: int, width: int) -> np.ndarray:
    sy = height / vol_t.shape[0]
    sx = width / vol_t.shape[1]
    return ndi.zoom(vol_t, (sy, sx), order=3, mode="wrap")


def mix_rgb(a: np.ndarray, b: np.ndarray, t: float) -> np.ndarray:
    return a * (1.0 - t) + b * t


def rgba_from_density(density: np.ndarray, color: np.ndarray, peak_alpha: float) -> np.ndarray:
    """Straight (unpremultiplied) RGBA. Fully transparent pixels carry `color` (not black)."""
    a = np.clip(density, 0.0, 1.0) * peak_alpha
    a = np.where(a < 1.0 / 255.0, 0.0, a)
    out = np.zeros(density.shape + (4,), dtype=np.float32)
    out[..., 0] = color[0]
    out[..., 1] = color[1]
    out[..., 2] = color[2]
    out[..., 3] = a * 255.0
    return out


def to_image(rgba: np.ndarray) -> Image.Image:
    return Image.fromarray(np.clip(rgba, 0, 255).astype(np.uint8), "RGBA")


def save_webp(im: Image.Image, path: Path) -> None:
    # Lossless keeps soft alpha edges clean (important for ink washes).
    im.save(path, "WEBP", lossless=True, method=4)


def paste_rgba(dst: Image.Image, src: Image.Image, cx: float, cy: float) -> None:
    """Composite `src` onto `dst` with its centre at (cx, cy). Clips at the edges."""
    x = int(round(cx - src.width / 2))
    y = int(round(cy - src.height / 2))
    sw, sh = src.size
    dw, dh = dst.size
    sx0 = 0 if x >= 0 else -x
    sy0 = 0 if y >= 0 else -y
    sx1 = sw if x + sw <= dw else dw - x
    sy1 = sh if y + sh <= dh else dh - y
    if sx1 <= sx0 or sy1 <= sy0:
        return
    crop = src.crop((sx0, sy0, sx1, sy1))
    layer = Image.new("RGBA", dst.size, (0, 0, 0, 0))
    layer.paste(crop, (x + sx0, y + sy0))
    dst.alpha_composite(layer)


# ---------------------------------------------------------------------------
# Mist
# ---------------------------------------------------------------------------

def build_mist_volumes(n: int, rng: np.random.Generator):
    """Low-res periodic volumes, one slice per frame. Multiple octaves + fibres."""
    # Spatial cells are large (soft landscape fog), time is one sample per frame.
    vols = {
        "low": periodic_volume(n, 20, 36, rng, sigma=(1.4, 1.6, 1.8)),
        "mid": periodic_volume(n, 36, 64, rng, sigma=(1.2, 1.3, 1.4)),
        "hi": periodic_volume(n, 64, 112, rng, sigma=(1.0, 1.1, 1.0)),
        "fiber": periodic_volume(n, 80, 48, rng, sigma=(0.8, 0.7, 1.6)),  # elongated in x
        "edge": periodic_volume(n, 90, 160, rng, sigma=(0.7, 0.8, 0.8)),
        "envx": periodic_volume(n, 12, 20, rng, sigma=(1.6, 1.8, 1.8)),
    }
    return vols


def vertical_profile(h: int) -> np.ndarray:
    """Concentrate mist around Bob's preview band (y ≈ 0.62 H) plus two quieter neighbours.

    Distant fog lives among the far-layer peaks and the mid-layer tree line, not in the
    upper sky and not as ground mist on the walk path (ground mist is FX slot B).
    """
    yy = np.linspace(0.0, 1.0, h, dtype=np.float64)[:, None]
    p = 1.00 * np.exp(-((yy - 0.62) / 0.10) ** 2)
    p += 0.62 * np.exp(-((yy - 0.52) / 0.07) ** 2)
    p += 0.48 * np.exp(-((yy - 0.72) / 0.08) ** 2)
    p *= np.clip((yy - 0.34) / 0.08, 0.0, 1.0)
    p *= np.clip((0.88 - yy) / 0.08, 0.0, 1.0)
    return p.astype(np.float32)


def mist_frame(t: int, vols: dict, profile: np.ndarray, rng_grain: np.random.Generator) -> Image.Image:
    """Build one seamless mist frame as pale ink-wash veils (mostly paper-coloured)."""
    low = zoom_slice(vols["low"][t], H, W)
    mid = zoom_slice(vols["mid"][t], H, W)
    hi = zoom_slice(vols["hi"][t], H, W)
    fiber = zoom_slice(vols["fiber"][t], H, W)
    edge_n = zoom_slice(vols["edge"][t], H, W)
    envx = zoom_slice(vols["envx"][t], H, W)

    # Field in 0..1 with blotchy, not-too-smooth contrast (ink, not CG fog).
    field = 0.55 * low + 0.32 * mid + 0.13 * hi
    field = 0.5 + 0.5 * np.tanh(field * 0.95)
    # Horizontal envelope so the belt is uneven — thicker in some valleys, thin in others.
    env = 0.55 + 0.45 * (0.5 + 0.5 * np.tanh(envx * 1.1))
    d = field * env * profile

    # Soft wet wash.
    wet = ndi.gaussian_filter(d, sigma=(7.0, 18.0), mode="nearest")  # slightly streaked in x
    # Fibrous dry-brush streaks, wind-aligned (horizontal).
    fib = np.clip(0.5 + 0.5 * fiber, 0.0, 1.0)
    streaks = ndi.gaussian_filter(d * fib, sigma=(1.2, 14.0), mode="nearest")
    # Broken edges: residual of the wet wash, gated by high-frequency noise.
    residual = np.clip(d - ndi.gaussian_filter(d, 5.0, mode="nearest"), 0.0, None)
    dry = residual * np.clip(edge_n * 0.7 + 0.15, 0.0, 1.0) ** 1.4

    ink = np.clip(0.72 * wet + 0.28 * streaks + 0.22 * dry, 0.0, 1.0)
    # Soft contrast roll so peaks are wisps, not slabs.
    ink = np.power(np.clip(ink, 0.0, 1.0), 1.15)
    ink *= 1.15
    ink = np.clip(ink, 0.0, 1.0)
    # Tiny static-looking grain that is actually in the looping volume (moves with the wash).
    ink *= 0.92 + 0.08 * np.clip(0.5 + 0.5 * edge_n, 0.0, 1.0)

    # Colour: almost paper, a little wash-3 in denser cores so the veil greys slightly.
    # Paper-coloured mist lightens the dark mountains and stays nearly invisible on the sky —
    # the same convention as Bob's static slot-A preview and the procedural placeholder in poi.js.
    tcol = np.clip(ink * 0.55, 0.0, 1.0)[..., None]
    color = PAPER * (1.0 - tcol) + mix_rgb(PAPER, WASH3, 0.35) * tcol
    # Per-pixel colour (can't use rgba_from_density's single colour).
    a = np.clip(ink, 0.0, 1.0) * 0.46  # peak ~0.46, close to Bob's 0.45 static band
    a = np.where(a < 1.0 / 255.0, 0.0, a)
    out = np.zeros((H, W, 4), dtype=np.float32)
    out[..., 0] = color[..., 0]
    out[..., 1] = color[..., 1]
    out[..., 2] = color[..., 2]
    out[..., 3] = a * 255.0
    return to_image(out)


def generate_mist(n: int, seed: int) -> list[Path]:
    out_dir = ROOT / "poi-forest-mist"
    if out_dir.exists():
        for p in out_dir.glob("*.webp"):
            p.unlink()
    out_dir.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(seed)
    print(f"[mist] building periodic volumes ({n} frames)…")
    vols = build_mist_volumes(n, rng)
    profile = vertical_profile(H)
    paths = []
    for t in range(n):
        im = mist_frame(t, vols, profile, rng)
        path = out_dir / f"{t:02d}.webp"
        save_webp(im, path)
        paths.append(path)
        if t % 8 == 0 or t == n - 1:
            a = np.array(im.split()[-1])
            print(f"  [mist] frame {t:02d}/{n-1}  alpha max={a.max()} mean={a.mean():.2f}  {path.stat().st_size//1024}KB")
    return paths


# ---------------------------------------------------------------------------
# Leaves
# ---------------------------------------------------------------------------

def _spine_leaf(rng: np.random.Generator, size: int, kind: str) -> np.ndarray:
    """Raster a single sumi-e bamboo leaf or a small pine-needle cluster. Returns RGBA uint8."""
    s = size
    yy, xx = np.mgrid[0:s, 0:s].astype(np.float64)
    rgba = np.zeros((s, s, 4), dtype=np.float64)

    if kind == "needles":
        # 2–3 tapered needles radiating from a point, slightly fanned.
        n_needles = int(rng.integers(2, 4))
        base_ang = rng.uniform(-0.5, 0.5)
        cx, cy = s * 0.5, s * 0.55
        for k in range(n_needles):
            ang = base_ang + (k - (n_needles - 1) / 2) * rng.uniform(0.18, 0.32)
            length = s * rng.uniform(0.38, 0.55)
            ca, sa = math.cos(ang), math.sin(ang)
            # Sample along the needle.
            n = 60
            t = np.linspace(0.0, 1.0, n)
            # taper: widest near the base, pointed tip
            env = (1.0 - t) ** 0.7 * rng.uniform(1.2, 2.0)
            px = cx + t * length * ca
            py = cy + t * length * sa
            dist = np.full((s, s), 1e9)
            tt = np.zeros((s, s))
            ww = np.zeros((s, s))
            for i in range(n):
                d = np.hypot(xx - px[i], yy - py[i])
                closer = d < dist
                dist = np.where(closer, d, dist)
                tt = np.where(closer, t[i], tt)
                ww = np.where(closer, env[i], ww)
            alpha = np.clip((ww - dist) / 0.9, 0.0, 1.0)
            # Dry breaks along the shaft.
            noise = rng.normal(0.0, 1.0, (s // 2, s // 2))
            noise = ndi.zoom(noise, (s / noise.shape[0], s / noise.shape[1]), order=1)
            if rng.random() < 0.5:
                alpha *= np.clip(0.75 + 0.4 * noise, 0.0, 1.0)
            shade = 0.15 + 0.85 * (1.0 - tt)  # darker toward the base
            col = mix_rgb(INK, WASH2, rng.uniform(0.0, 0.25))
            rgb_a = alpha * (0.75 + 0.25 * shade) * rng.uniform(0.85, 1.0)
            for c in range(3):
                rgba[..., c] = np.where(rgb_a[..., None] if False else rgb_a > rgba[..., 3] / 255.0,
                                        col[c], rgba[..., c])  # placeholder, fixed below
            # Simple over: darker ink wins.
            src_a = rgb_a
            out_a = rgba[..., 3] / 255.0
            new_a = src_a + out_a * (1.0 - src_a)
            for c in range(3):
                rgba[..., c] = np.where(
                    new_a > 1e-6,
                    (col[c] * src_a + rgba[..., c] * out_a * (1.0 - src_a)) / np.maximum(new_a, 1e-6),
                    rgba[..., c],
                )
            rgba[..., 3] = new_a * 255.0
        rgba[..., 3] = np.where(rgba[..., 3] < 1.0, 0.0, rgba[..., 3])
        return np.clip(rgba, 0, 255).astype(np.uint8)

    # Bamboo leaf: curved lanceolate stroke, pointed at both ends, one wetter edge, a faint vein.
    angle = rng.uniform(-0.55, 0.55)
    curve = rng.uniform(-0.45, 0.45)
    length = s * rng.uniform(0.70, 0.90)
    maxw = s * rng.uniform(0.075, 0.155)
    wetness = rng.uniform(0.25, 0.95)  # high = soft wash, low = dry-brush
    cx, cy = s * 0.5, s * 0.5
    ca, sa = math.cos(angle), math.sin(angle)
    n = 90
    t = np.linspace(0.0, 1.0, n)
    # Slightly fuller toward the base (t=0), still pointed at both ends.
    env = (np.sin(np.pi * np.clip(t ** 0.85, 0, 1)) ** 0.80) * maxw
    px = cx + (t - 0.5) * length * ca - 4.0 * curve * t * (1.0 - t) * length * sa
    py = cy + (t - 0.5) * length * sa + 4.0 * curve * t * (1.0 - t) * length * ca
    dist = np.full((s, s), 1e9)
    tt = np.zeros((s, s))
    ww = np.zeros((s, s))
    # Side: signed left/right of the spine, for a wetter edge.
    side = np.zeros((s, s))
    for i in range(n):
        d = np.hypot(xx - px[i], yy - py[i])
        closer = d < dist
        dist = np.where(closer, d, dist)
        tt = np.where(closer, t[i], tt)
        ww = np.where(closer, env[i], ww)
        # Normal to the local tangent.
        if 0 < i < n - 1:
            tx, ty = px[i + 1] - px[i - 1], py[i + 1] - py[i - 1]
        elif i == 0:
            tx, ty = px[1] - px[0], py[1] - py[0]
        else:
            tx, ty = px[-1] - px[-2], py[-1] - py[-2]
        nrm = math.hypot(tx, ty) + 1e-8
        nx_, ny_ = -ty / nrm, tx / nrm
        sd = (xx - px[i]) * nx_ + (yy - py[i]) * ny_
        side = np.where(closer, sd, side)

    edge_soft = 0.7 + 2.2 * wetness
    alpha = np.clip((ww - dist) / edge_soft, 0.0, 1.0)
    # Wet bloom: slight bleed outside the body.
    if wetness > 0.5:
        bloom = ndi.gaussian_filter(alpha, sigma=1.2 + 1.4 * wetness)
        alpha = np.clip(np.maximum(alpha, bloom * 0.35), 0.0, 1.0)
    # Dry-brush: eat holes near the edges when wetness is low.
    noise = rng.normal(0.0, 1.0, (max(8, s // 3), max(8, s // 3)))
    noise = ndi.zoom(noise, (s / noise.shape[0], s / noise.shape[1]), order=1)
    noise = ndi.gaussian_filter(noise, 0.8)
    if wetness < 0.7:
        edge = np.clip(alpha * (1.0 - alpha) * 4.0, 0.0, 1.0)
        bite = np.clip(0.55 + 0.7 * noise, 0.0, 1.2)
        alpha = np.clip(alpha * (1.0 - (1.0 - wetness) * 0.55 * edge * (1.0 - bite)), 0.0, 1.0)
        # A few fibrous streaks along the leaf axis.
        # Approximate by slightly stretching noise along angle.
        alpha *= np.clip(0.82 + 0.28 * noise, 0.25, 1.0) ** (1.0 - 0.6 * wetness)

    # Ink density: darker on one edge, a little paler toward the tip.
    wet_edge = 0.5 + 0.5 * np.tanh(side / max(2.0, maxw * 0.35))
    tip = np.clip(tt, 0.0, 1.0)
    shade = 0.55 + 0.45 * wet_edge
    shade *= 0.75 + 0.25 * (1.0 - tip)
    shade = np.clip(shade, 0.0, 1.0)
    col_dark = mix_rgb(INK, WASH1, rng.uniform(0.0, 0.25))
    col_pale = mix_rgb(WASH2, WASH3, rng.uniform(0.0, 0.4))
    color = col_dark[None, None, :] * shade[..., None] + col_pale[None, None, :] * (1.0 - shade[..., None])

    # Central vein: a thinner, darker line along the spine, fading at the tip.
    vein_w = max(0.7, maxw * 0.10)
    vein = np.clip((vein_w - dist) / 0.8, 0.0, 1.0) * (1.0 - tip) ** 0.6 * 0.55
    vein *= (alpha > 0.15).astype(np.float64)
    color = color * (1.0 - vein[..., None]) + INK[None, None, :] * vein[..., None]
    alpha = np.clip(alpha + vein * 0.15, 0.0, 1.0)

    alpha *= rng.uniform(0.82, 1.0)
    rgba[..., :3] = color
    rgba[..., 3] = np.where(alpha < 1.0 / 255.0, 0.0, alpha * 255.0)
    return np.clip(rgba, 0, 255).astype(np.uint8)


def make_stamps(rng: np.random.Generator) -> list[Image.Image]:
    stamps = []
    # A set of unique leaves / needles at a working resolution; scaled per instance later.
    for _ in range(10):
        arr = _spine_leaf(rng, 160, "bamboo")
        stamps.append(Image.fromarray(arr, "RGBA"))
    for _ in range(4):
        arr = _spine_leaf(rng, 120, "needles")
        stamps.append(Image.fromarray(arr, "RGBA"))
    return stamps


def plan_leaves(n: int, rng: np.random.Generator, n_leaves: int = 34) -> list[dict]:
    """Every parameter is periodic in `n` frames, so the loop joins without a jump."""
    margin = 110
    leaves = []
    for i in range(n_leaves):
        # Prefer the open path and the tree edges, where falling leaves read clearly.
        # Path opening is roughly x 700–1860 in 2560 space.
        zone = rng.random()
        if zone < 0.55:
            x0 = rng.uniform(720, 1860)
        elif zone < 0.80:
            x0 = rng.uniform(180, 720)   # left grove
        else:
            x0 = rng.uniform(1860, 2420)  # right grove
        # Varied fall periods → slight speed variation, all still wrap once per loop.
        period = (H + 2 * margin) * rng.uniform(0.88, 1.28)
        speed = period / n  # px per frame
        y_phase = rng.uniform(0.0, period)
        sway_amp = rng.uniform(24.0, 90.0)
        sway_cycles = int(rng.choice([1, 1, 1, 2]))  # integer cycles
        sway_ph = rng.uniform(0.0, 2 * math.pi)
        rot0 = rng.uniform(-40.0, 40.0)
        rot_amp = rng.uniform(10.0, 38.0)
        rot_cycles = int(rng.choice([1, 1, 2]))
        rot_ph = rng.uniform(0.0, 2 * math.pi)
        # Distant leaves are smaller and paler (we bake paleness into a per-leaf opacity).
        depth = rng.uniform(0.0, 1.0)
        scale = 0.28 + 0.55 * (0.35 + 0.65 * depth)  # ~0.28–0.83 of the 160px stamp
        if rng.random() < 0.25:
            scale *= rng.uniform(0.7, 0.9)  # a few tiny ones
        opacity = 0.55 + 0.45 * depth
        sid = int(rng.integers(0, 14))
        # Needles a bit smaller.
        if sid >= 10:
            scale *= 0.85
        leaves.append(dict(
            x0=x0, y_phase=y_phase, period=period, speed=speed, margin=margin,
            sway_amp=sway_amp, sway_cycles=sway_cycles, sway_ph=sway_ph,
            rot0=rot0, rot_amp=rot_amp, rot_cycles=rot_cycles, rot_ph=rot_ph,
            scale=scale, opacity=opacity, sid=sid,
        ))
    return leaves


def leaf_pose(leaf: dict, t: int, n: int) -> tuple[float, float, float, float]:
    u = t / n
    y = (leaf["y_phase"] + leaf["speed"] * t) % leaf["period"] - leaf["margin"]
    x = leaf["x0"] + leaf["sway_amp"] * math.sin(2 * math.pi * leaf["sway_cycles"] * u + leaf["sway_ph"])
    rot = leaf["rot0"] + leaf["rot_amp"] * math.sin(2 * math.pi * leaf["rot_cycles"] * u + leaf["rot_ph"])
    return x, y, rot, leaf["opacity"]


def generate_leaves(n: int, seed: int) -> list[Path]:
    out_dir = ROOT / "poi-forest-leaves"
    if out_dir.exists():
        for p in out_dir.glob("*.webp"):
            p.unlink()
    out_dir.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(seed + 17)
    stamps = make_stamps(rng)
    # Cache rotated/scaled stamps? Rotations are continuous, so we rotate each time.
    leaves = plan_leaves(n, rng)
    # Pre-scale stamps once (rotation stays per-frame).
    scaled = []
    # We'll scale per leaf, so keep originals.
    print(f"[leaves] {len(leaves)} leaves, {len(stamps)} stamps, {n} frames…")
    paths = []
    for t in range(n):
        canvas = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        # Draw back-to-front by scale (smaller / paler first).
        order = sorted(range(len(leaves)), key=lambda i: leaves[i]["scale"])
        for i in order:
            lf = leaves[i]
            x, y, rot, opacity = leaf_pose(lf, t, n)
            if y < -leaf_size_guard(lf) or y > H + leaf_size_guard(lf):
                continue
            st = stamps[lf["sid"]]
            nw = max(8, int(round(st.width * lf["scale"])))
            nh = max(8, int(round(st.height * lf["scale"])))
            im = st.resize((nw, nh), Image.Resampling.LANCZOS)
            im = im.rotate(rot, resample=Image.Resampling.BICUBIC, expand=True)
            if opacity < 0.999:
                a = np.array(im, copy=True)
                a[..., 3] = (a[..., 3].astype(np.float64) * opacity).astype(np.uint8)
                im = Image.fromarray(a, "RGBA")
            paste_rgba(canvas, im, x, y)
        path = out_dir / f"{t:02d}.webp"
        save_webp(canvas, path)
        paths.append(path)
        if t % 8 == 0 or t == n - 1:
            a = np.array(canvas.split()[-1])
            print(f"  [leaves] frame {t:02d}/{n-1}  alpha max={a.max()} nz={(a>0).mean()*100:.2f}%  {path.stat().st_size//1024}KB")
    # Save a stamp sheet for the README / debugging.
    sheet = Image.new("RGBA", (15 * 170, 180), tuple(int(c) for c in PAPER) + (255,))
    for i, st in enumerate(stamps):
        sheet.paste(st, (i * 170 + 5, 10), st)
    sheet.convert("RGB").save(ROOT / "previews" / "leaf-stamps.png")
    return paths


def leaf_size_guard(lf: dict) -> float:
    return 160 * lf["scale"] + 8


# ---------------------------------------------------------------------------
# Previews, manifest, verification
# ---------------------------------------------------------------------------

def load_layer(name: str) -> Image.Image:
    p = ART / f"{name}.png"
    im = Image.open(p)
    if im.size != (W, H):
        im = im.resize((W, H), Image.Resampling.LANCZOS)
    return im.convert("RGBA") if im.mode != "RGBA" else im


def composite_preview(far, mid, near, mist=None, leaves=None) -> Image.Image:
    out = far.convert("RGBA")
    if mist is not None:
        out = Image.alpha_composite(out, mist)
    out = Image.alpha_composite(out, mid)
    if leaves is not None:
        out = Image.alpha_composite(out, leaves)
    out = Image.alpha_composite(out, near)
    return out


def checker_bg(w=W, h=H, cell=40) -> Image.Image:
    yy, xx = np.indices((h, w))
    c = ((xx // cell) + (yy // cell)) % 2
    g = np.where(c == 0, 168, 210).astype(np.uint8)
    return Image.fromarray(np.dstack([g, g, g]), "RGB").convert("RGBA")


def load_frames(folder: Path, n: int) -> list[Path]:
    paths = [folder / f"{t:02d}.webp" for t in range(n)]
    missing = [p for p in paths if not p.exists()]
    if missing:
        raise FileNotFoundError(f"missing frames, e.g. {missing[0]}")
    return paths


def write_preview_sequence(name: str, frames: list[Image.Image], tmp: Path) -> list[Path]:
    tmp.mkdir(parents=True, exist_ok=True)
    paths = []
    for i, im in enumerate(frames):
        p = tmp / f"{name}_{i:03d}.png"
        im.save(p)
        paths.append(p)
    return paths


def encode_mp4(frame_glob: str, out: Path, fps: int = FPS) -> None:
    subprocess.check_call([
        "ffmpeg", "-y", "-framerate", str(fps), "-i", frame_glob,
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18", "-movflags", "+faststart",
        str(out),
    ], stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)


def encode_gif(mp4: Path, out: Path, width: int = 960) -> None:
    palette = out.with_suffix(".palette.png")
    subprocess.check_call([
        "ffmpeg", "-y", "-i", str(mp4),
        "-vf", f"fps={FPS},scale={width}:-1:flags=lanczos,palettegen=stats_mode=full",
        str(palette),
    ], stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
    subprocess.check_call([
        "ffmpeg", "-y", "-i", str(mp4), "-i", str(palette),
        "-lavfi", f"fps={FPS},scale={width}:-1:flags=lanczos[x];[x][1:v]paletteuse=dither=bayer:bayer_scale=4",
        str(out),
    ], stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
    palette.unlink(missing_ok=True)


def still(im: Image.Image, path: Path) -> None:
    im.convert("RGB").resize((1280, 720), Image.Resampling.LANCZOS).save(path, quality=92, optimize=True)


def seam_strip(paths: list[Path], out: Path, crop=None) -> None:
    """Last two frames + first two, side by side, to inspect the loop join."""
    idxs = [len(paths) - 2, len(paths) - 1, 0, 1]
    labels = ["N-2", "N-1", "0", "1"]
    imgs = [Image.open(paths[i]).convert("RGBA") for i in idxs]
    if crop:
        imgs = [im.crop(crop) for im in imgs]
    # Downscale each to a manageable strip tile.
    tw = 480
    tiles = []
    for im in imgs:
        th = int(im.height * tw / im.width)
        tiles.append(im.resize((tw, th), Image.Resampling.LANCZOS))
    sheet = Image.new("RGBA", (tw * 4 + 6, tiles[0].height + 8), (236, 230, 216, 255))
    for i, t in enumerate(tiles):
        sheet.paste(t, (i * tw + (i + 1) * 1, 4), t if t.mode == "RGBA" else None)
    sheet.convert("RGB").save(out, quality=90)
    print(f"  wrote seam strip {out}  (order: {' | '.join(labels)})")


def verify_loop(name: str, paths: list[Path]) -> dict:
    """Compare first/last join against a mid-loop step. Check alpha hygiene."""
    def load_a(p):
        im = Image.open(p).convert("RGBA")
        return np.array(im)

    a0 = load_a(paths[0])
    a1 = load_a(paths[1])
    aLm = load_a(paths[-1])
    # The loop step is last -> first; an interior step is 0 -> 1.
    d_loop = np.abs(a0.astype(np.int16) - aLm.astype(np.int16)).mean()
    d_step = np.abs(a1.astype(np.int16) - a0.astype(np.int16)).mean()
    # If the motion is constant, these should be similar. A snap would make d_loop >> d_step.
    ratio = float(d_loop / (d_step + 1e-6))
    alpha = a0[..., 3]
    # Transparent pixels should not be RGB-black (we'd get fringes if someone premultiplies wrong).
    trans = alpha == 0
    if trans.any():
        rgb = a0[..., :3][trans]
        # We write paper or ink under transparent px; black is a red flag.
        black_frac = float((rgb.max(axis=1) == 0).mean())
    else:
        black_frac = 0.0
    report = {
        "name": name,
        "frames": len(paths),
        "size": list(a0.shape[1::-1]),
        "mae_loop_step": round(float(d_loop), 3),
        "mae_interior_step": round(float(d_step), 3),
        "loop_to_step_ratio": round(ratio, 3),
        "alpha_min": int(alpha.min()),
        "alpha_max": int(alpha.max()),
        "alpha_mean": round(float(alpha.mean()), 3),
        "alpha_nonzero_pct": round(float((alpha > 0).mean()) * 100, 3),
        "transparent_black_rgb_frac": round(black_frac, 4),
        "seamless_ok": ratio < 2.5,
        "alpha_ok": black_frac < 0.01 and int(alpha.max()) > 0,
    }
    flag = "OK" if report["seamless_ok"] and report["alpha_ok"] else "CHECK"
    print(f"  [verify {name}] {flag}  loop MAE={d_loop:.3f}  step MAE={d_step:.3f}  ratio={ratio:.2f}  "
          f"alpha nz={report['alpha_nonzero_pct']}% max={report['alpha_max']}  trans-black={black_frac:.4f}")
    return report


def write_manifest(n_mist: int, n_leaves: int, reports: list[dict]) -> None:
    data = {
        "title": "Inkborne",
        "poi": {
            "forest": "Sumikage Wood",
            "town": "Hanshi",
        },
        "notes": (
            "Full-screen 2560x1440 looping overlays, one WebP frame per file, 12 fps, straight alpha. "
            "SPEC section 5 only documents horizontal strips; a 2560-wide strip of 72 frames is impractical "
            "(184320 px). Load the numbered frames, or the preview animated files for review. "
            "Position registers 1:1 with Bob's POI layers (anchor [0.5, 1.0] at the stage bottom-centre). "
            "Palette from SPEC section 5; no vermilion in these two keys (leaves and mist are ink/paper only)."
        ),
        "palette": {
            "paper": "#ece6d8",
            "paper_shade": "#d9d0bc",
            "ink": "#1b1813",
            "wash1": "#3b3730",
            "wash2": "#6d675b",
            "wash3": "#a39c8c",
            "vermilion": "#b3261e",
        },
        "images": {
            "poi-forest-mist": {
                "src": "ambient/poi-forest-mist/",
                "pattern": "ambient/poi-forest-mist/%02d.webp",
                "files": [f"{i:02d}.webp" for i in range(n_mist)],
                "w": W, "h": H, "fw": W, "fh": H,
                "frames": n_mist, "fps": FPS, "loop": True,
                "x": 1280, "y": 1440,
                "position": [1280, 1440],
                "anchor": [0.5, 1.0],
                "sit_above": "poi-forest-far",
                "layer": "fx-slot-a",
                "parallax": 0.3,
                "opacity": 0.90,
                "blend": "source-over",
                "poi": "forest",
                "name": "Sumikage Wood mist drift",
                "notes": (
                    "Distant ink-wash fog bands among the far peaks and the mid-layer tree line, "
                    "centred near y≈0.62×1440 (Bob's slot-A preview band). Pale paper-tinted veils. "
                    "Suggested global opacity 0.90 on top of the baked alpha (peak baked alpha ≈ 0.46). "
                    "Do not use multiply — the RGB is already unmixed paper/wash."
                ),
            },
            "poi-forest-leaves": {
                "src": "ambient/poi-forest-leaves/",
                "pattern": "ambient/poi-forest-leaves/%02d.webp",
                "files": [f"{i:02d}.webp" for i in range(n_leaves)],
                "w": W, "h": H, "fw": W, "fh": H,
                "frames": n_leaves, "fps": FPS, "loop": True,
                "x": 1280, "y": 1440,
                "position": [1280, 1440],
                "anchor": [0.5, 1.0],
                "sit_above": "poi-forest-mid",
                "layer": "fx-slot-b",
                "parallax": 0.7,
                "opacity": 1.0,
                "blend": "source-over",
                "poi": "forest",
                "name": "Sumikage Wood falling leaves",
                "notes": (
                    "Bamboo leaves and a few pine-needle clusters falling through the path opening and the groves. "
                    "Sits above mid, below the party and the near frame. Parallax 0.7 is between mid (0.5) and "
                    "the walker (1.0). A sparser close-leaf pass for FX slot C is not in this batch."
                ),
            },
        },
        "verify": reports,
    }
    path = ROOT / "ambient.json"
    path.write_text(json.dumps(data, indent=2) + "\n")
    print(f"wrote {path}")


def build_previews(n_mist: int, n_leaves: int) -> list[Path]:
    prev = ROOT / "previews"
    prev.mkdir(exist_ok=True)
    print("[preview] loading Bob's layers…")
    far = load_layer("poi-forest-far")
    mid = load_layer("poi-forest-mid")
    near = load_layer("poi-forest-near")
    mist_paths = load_frames(ROOT / "poi-forest-mist", n_mist)
    leaf_paths = load_frames(ROOT / "poi-forest-leaves", n_leaves)
    assert n_mist == n_leaves, "preview composite expects the same frame count"

    reports = [verify_loop("poi-forest-mist", mist_paths),
               verify_loop("poi-forest-leaves", leaf_paths)]

    # Seam strips: a mid-band crop where mist lives (y 600–1200), and a wider crop for leaves.
    seam_strip(mist_paths, prev / "poi-forest-mist-seam.jpg", crop=(0, 560, W, 1200))
    seam_strip(leaf_paths, prev / "poi-forest-leaves-seam.jpg", crop=(480, 0, 2080, H))

    # Alpha checks on frame 0 and a mid frame.
    chk = checker_bg().convert("RGBA")
    for name, paths, idx in (("mist", mist_paths, 0), ("mist", mist_paths, n_mist // 3),
                             ("leaves", leaf_paths, 0), ("leaves", leaf_paths, n_leaves // 3)):
        im = Image.open(paths[idx]).convert("RGBA")
        still(Image.alpha_composite(chk, im), prev / f"poi-forest-{name}-alphacheck-f{idx:02d}.jpg")

    # Composited preview frames (1280x720) for mp4/gif + stills.
    tmp = prev / "_tmp"
    if tmp.exists():
        shutil.rmtree(tmp)
    tmp.mkdir()
    still_idxs = {0, n_mist // 4, n_mist // 2}

    print("[preview] compositing over Bob's layers…")
    mist_only_paths = []
    leaves_only_paths = []
    both_paths = []
    for t in range(n_mist):
        mist = Image.open(mist_paths[t]).convert("RGBA")
        leaves = Image.open(leaf_paths[t]).convert("RGBA")
        c_mist = composite_preview(far, mid, near, mist=mist, leaves=None).resize((1280, 720), Image.Resampling.LANCZOS)
        c_leaves = composite_preview(far, mid, near, mist=None, leaves=leaves).resize((1280, 720), Image.Resampling.LANCZOS)
        c_both = composite_preview(far, mid, near, mist=mist, leaves=leaves).resize((1280, 720), Image.Resampling.LANCZOS)
        p1 = tmp / f"mist_{t:03d}.png"
        p2 = tmp / f"leaves_{t:03d}.png"
        p3 = tmp / f"both_{t:03d}.png"
        c_mist.convert("RGB").save(p1)
        c_leaves.convert("RGB").save(p2)
        c_both.convert("RGB").save(p3)
        mist_only_paths.append(p1)
        leaves_only_paths.append(p2)
        both_paths.append(p3)
        if t in still_idxs:
            c_mist.convert("RGB").save(prev / f"poi-forest-mist-still-f{t:02d}.png", optimize=True)
            c_leaves.convert("RGB").save(prev / f"poi-forest-leaves-still-f{t:02d}.png", optimize=True)
            c_both.convert("RGB").save(prev / f"poi-forest-ambient-still-f{t:02d}.png", optimize=True)
        if t % 12 == 0:
            print(f"  [preview] frame {t}/{n_mist-1}")

    # Canonical still names for reviewers (mid-loop, both and each).
    mid_i = n_mist // 4
    shutil.copy(prev / f"poi-forest-mist-still-f{mid_i:02d}.png", prev / "poi-forest-mist-still.png")
    shutil.copy(prev / f"poi-forest-leaves-still-f{mid_i:02d}.png", prev / "poi-forest-leaves-still.png")
    shutil.copy(prev / f"poi-forest-ambient-still-f{mid_i:02d}.png", prev / "poi-forest-ambient-still.png")

    print("[preview] encoding mp4 / gif…")
    encode_mp4(str(tmp / "mist_%03d.png"), prev / "poi-forest-mist.mp4")
    encode_mp4(str(tmp / "leaves_%03d.png"), prev / "poi-forest-leaves.mp4")
    encode_mp4(str(tmp / "both_%03d.png"), prev / "poi-forest-ambient.mp4")
    encode_gif(prev / "poi-forest-mist.mp4", prev / "poi-forest-mist.gif", 960)
    encode_gif(prev / "poi-forest-leaves.mp4", prev / "poi-forest-leaves.gif", 960)
    encode_gif(prev / "poi-forest-ambient.mp4", prev / "poi-forest-ambient.gif", 960)

    shutil.rmtree(tmp, ignore_errors=True)
    write_manifest(n_mist, n_leaves, reports)
    return reports


def main(argv=None):
    ap = argparse.ArgumentParser(description="Generate Sumikage Wood ambient loops")
    ap.add_argument("what", nargs="*", default=[], help="mist, leaves, and/or preview (default: all)")
    ap.add_argument("--frames", type=int, default=N_DEFAULT)
    ap.add_argument("--seed", type=int, default=SEED)
    ap.add_argument("--preview", action="store_true", help="rebuild previews from existing frames only")
    args = ap.parse_args(argv)

    what = set(args.what) if args.what else {"mist", "leaves", "preview"}
    if args.preview:
        what.add("preview")
    n = args.frames
    if n < 2 or n > 240:
        sys.exit("--frames must be in 2..240")

    (ROOT / "previews").mkdir(parents=True, exist_ok=True)

    if "mist" in what:
        generate_mist(n, args.seed)
    if "leaves" in what:
        generate_leaves(n, args.seed)
    if "preview" in what:
        # Infer frame counts from folders if we didn't just render.
        def count(folder):
            return len(sorted((ROOT / folder).glob("*.webp")))
        nm = count("poi-forest-mist")
        nl = count("poi-forest-leaves")
        if nm == 0 or nl == 0:
            sys.exit("preview needs both mist and leaves frame folders")
        if nm != nl:
            print(f"warning: mist has {nm} frames, leaves has {nl}; compositing min={min(nm,nl)}")
        build_previews(min(nm, nl), min(nm, nl))
    print("done.")


if __name__ == "__main__":
    main()
