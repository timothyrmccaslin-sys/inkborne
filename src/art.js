// Image registry from assets/art/manifest.json (SPEC section 5). Missing keys -> procedural placeholders.
export class Art {
  constructor(base) { this.base = base; this.img = {}; this.meta = {}; }
  async load() {
    try { const m = await (await fetch(this.base + 'assets/art/manifest.json')).json(); this.meta = m.images || {}; } catch (e) { this.meta = {}; }
    await Promise.all(Object.entries(this.meta).map(([k, v]) => new Promise((ok) => { const i = new Image(); i.onload = () => { this.img[k] = i; ok(); }; i.onerror = () => ok(); i.src = this.base + 'assets/art/' + v.src; })));
  }
  has(k) { return !!this.img[k]; }
  get(k) { return this.img[k]; }
}
/** Draw frame `f` of a horizontal strip key at (x,y) using its anchor. Returns false if missing. */
export function drawStrip(art, ctx, key, f, x, y, scale = 1, flip = false, alpha = 1) {
  const img = art.get(key), m = art.meta[key]; if (!img || !m) return false;
  const n = m.frames || 1; f = m.loop ? ((f % n) + n) % n : Math.max(0, Math.min(n - 1, f | 0));
  const fw = m.fw, fh = m.fh, ax = (m.anchor || [0.5, 0.5])[0], ay = (m.anchor || [0.5, 0.5])[1];
  ctx.save(); ctx.globalAlpha *= alpha; ctx.translate(x, y); if (flip) ctx.scale(-1, 1); ctx.scale(scale, scale);
  ctx.drawImage(img, (f | 0) * fw, 0, fw, fh, -ax * fw, -ay * fh, fw, fh); ctx.restore(); return true;
}
export function stripFrames(art, key) { return (art.meta[key] && art.meta[key].frames) || 1; }
