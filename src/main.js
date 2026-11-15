// Inkborne boot: wasm core, data, art, audio, input, scene manager with ink-wipe transitions.
import init, { Game } from '../pkg/inkborne_core.js';
import { Input } from './input.js';
import { Audio } from './audio.js';
import { Art } from './art.js';
import { setStrings } from './ui.js';
import { PAL, paper, rng } from './ink.js';
export const APP_VERSION = 'ib-0.1.0';
const SAVE_KEY = 'inkborne-save-v1';
const W = 1280, H = 720;
const BASE = new URL('../', import.meta.url).href;
const SCENES = {};
const scenes = ['title', 'world', 'poi', 'battle', 'dialogue', 'shop'];

const cv = document.getElementById('c'), ctx = cv.getContext('2d');
const game = { W, H, base: BASE, ctx, version: APP_VERSION, t: 0, stack: [], wipe: null, flags: {} };
window.__ib = game; // test hook

function fit() {
  const dpr = Math.min(2, window.devicePixelRatio || 1), vw = innerWidth, vh = innerHeight;
  const s = Math.min(vw / W, vh / H); game.scale = s; game.ox = (vw - W * s) / 2; game.oy = (vh - H * s) / 2;
  cv.width = Math.round(vw * dpr); cv.height = Math.round(vh * dpr); cv.style.width = vw + 'px'; cv.style.height = vh + 'px'; game.dpr = dpr;
}
addEventListener('resize', fit); fit();
/** client px -> logical */
game.toLogical = (p) => p && { x: (p.x - game.ox) / game.scale, y: (p.y - game.oy) / game.scale };

async function json(p) { const r = await fetch(BASE + p); if (!r.ok) throw new Error(p + ' ' + r.status); return r.text(); }

game.save = () => { try { localStorage.setItem(SAVE_KEY, game.core.save_json()); } catch (e) {} };
function readSave() { try { const s = localStorage.getItem(SAVE_KEY); if (!s) return null; const v = JSON.parse(s); if (!v || typeof v !== 'object' || typeof v.gold !== 'number' || typeof v.hp !== 'object' || typeof v.inv !== 'object') return null; return s; } catch (e) { return null; } }
game.hasSave = () => !!readSave();
game.load = () => { const s = readSave(); try { return s ? game.core.load_json(s) : false; } catch (e) { return false; } };

function make(name, params) { const sc = SCENES[name].create(game, params || {}); sc.name = name; return sc; }
game.go = (name, params) => transition(() => { for (const s of game.stack) s.exit && s.exit(); game.stack = [make(name, params)]; game.stack[0].enter && game.stack[0].enter(); });
game.push = (name, params) => transition(() => { const s = make(name, params); game.stack.push(s); s.enter && s.enter(); });
game.pop = (result) => transition(() => { const s = game.stack.pop(); s && s.exit && s.exit(); const top = game.top(); if (top) { top.resume && top.resume(); top.onResult && top.onResult(result); } });
game.top = () => game.stack[game.stack.length - 1];

// ink-wipe: a bold brush sweep covers the screen, the scene swaps underneath, then the ink drains
function transition(swap) {
  if (game.wipe) { game.wipe.queue.push(swap); return; }
  game.audio.play('wipe'); game.wipe = { t: 0, swap, done: false, queue: [], seed: (Math.random() * 1000) | 0 };
}
function drawWipe(w) {
  const k = w.t / 0.9; const cover = k < 0.5 ? k * 2 : 2 - k * 2; if (cover <= 0) return;
  const r = rng(w.seed);
  ctx.save(); ctx.fillStyle = PAL.ink;
  for (let i = 0; i < 9; i++) { // nine bristle bands, staggered
    const y = i * H / 9 - 12, lag = r() * 0.25, c = Math.max(0, Math.min(1, cover * 1.3 - lag));
    const x0 = k < 0.5 ? -80 : W + 80 - (W + 200) * c, x1 = k < 0.5 ? -80 + (W + 200) * c : W + 80;
    ctx.beginPath(); ctx.moveTo(x0, y); ctx.lineTo(x1, y + 6); ctx.quadraticCurveTo(x1 + 40, y + H / 18, x1, y + H / 9 + 22); ctx.lineTo(x0, y + H / 9 + 16); ctx.closePath(); ctx.fill();
    for (let j = 0; j < 4; j++) { ctx.globalAlpha = 0.5; ctx.fillRect(x1 + r() * 60, y + r() * H / 9, 6 + r() * 20, 2 + r() * 3); ctx.globalAlpha = 1; }
  }
  ctx.restore();
}

let last = performance.now();
function frame(now) {
  const dt = Math.min(0.05, (now - last) / 1000); last = now; game.t += dt; game.now = now;
  const inp = game.input; inp.begin();
  game.taps = inp.pointerTaps.map(game.toLogical);
  const top = game.top();
  if (game.wipe) { const w = game.wipe; w.t += dt; if (!w.done && w.t >= 0.45) { w.done = true; w.swap(); } if (w.t >= 0.9) { game.wipe = w.queue.length ? { t: 0, swap: w.queue.shift(), done: false, queue: w.queue, seed: w.seed + 1 } : null; } }
  else if (top) top.update(dt, inp);
  ctx.setTransform(game.dpr, 0, 0, game.dpr, 0, 0); ctx.fillStyle = '#16130f'; ctx.fillRect(0, 0, cv.width, cv.height);
  ctx.setTransform(game.dpr * game.scale, 0, 0, game.dpr * game.scale, game.dpr * game.ox, game.dpr * game.oy);
  ctx.save(); ctx.beginPath(); ctx.rect(0, 0, W, H); ctx.clip();
  // overlays draw over the scene beneath them
  const base = game.stack.length > 1 && game.top().overlay ? game.stack[game.stack.length - 2] : null;
  if (base) base.draw(ctx, game.t);
  if (top) top.draw(ctx, game.t);
  if (game.wipe) drawWipe(game.wipe);
  ctx.restore();
  inp.end(); game.painted = (game.painted || 0) + 1;
  requestAnimationFrame(frame);
}

// fullscreen: Fullscreen API where supported (not iPhone/iPad Safari; the installed PWA is already fullscreen)
game.fullscreen = () => { const d = document.documentElement; const rq = d.requestFullscreen || d.webkitRequestFullscreen; if (rq && !document.fullscreenElement && !document.webkitFullscreenElement) try { const p = rq.call(d, { navigationUI: 'hide' }); p && p.catch && p.catch(() => {}); } catch (e) {} };
game.standalone = matchMedia('(display-mode: standalone)').matches || navigator.standalone === true;
document.getElementById('menu-btn').addEventListener('click', () => game.fullscreen());

async function boot() {
  try {
    await init();
    const [party, enemies, items, trans, strings, barks, dialogue, shops, world, story, forest, town] = await Promise.all(
      ['party', 'enemies', 'items', 'transformation', 'strings', 'barks', 'dialogue', 'shops', 'world', 'story', 'pois/forest', 'pois/town'].map((n) => json(`data/${n}.json`)));
    game.data = { party: JSON.parse(party), enemies: JSON.parse(enemies), items: JSON.parse(items), strings: JSON.parse(strings), barks: JSON.parse(barks).barks, dialogue: JSON.parse(dialogue), shops: JSON.parse(shops), world: JSON.parse(world), story: JSON.parse(story), pois: { forest: JSON.parse(forest), town: JSON.parse(town) }, poiRaw: { forest, town } };
    game.core = new Game(party, enemies, items, (Date.now() & 0xffff) >>> 0); game.core.set_rules(trans);
    setStrings(game.data.strings);
    game.input = new Input(document.body); game.audio = new Audio(BASE); game.art = new Art(BASE);
    await Promise.all([game.art.load(), document.fonts && document.fonts.ready]);
    paper(W, H); // warm the paper cache
    for (const n of scenes) SCENES[n] = await import(`./scenes/${n}.js`);
    game.stack = [make('title')]; game.stack[0].enter();
    document.getElementById('boot').remove();
    requestAnimationFrame(frame);
  } catch (e) { document.getElementById('boot').textContent = 'Could not start: ' + e.message; console.error(e); }
}
boot();

// service worker + update notice
if ('serviceWorker' in navigator && location.protocol !== 'file:') {
  navigator.serviceWorker.register(BASE + 'sw.js').then((reg) => {
    const show = () => { const n = document.getElementById('update'); n.hidden = false; n.onclick = () => { reg.waiting && reg.waiting.postMessage({ type: 'SKIP_WAITING' }); }; };
    if (reg.waiting && navigator.serviceWorker.controller) show();
    reg.addEventListener('updatefound', () => { const w = reg.installing; w && w.addEventListener('statechange', () => { if (w.state === 'installed' && navigator.serviceWorker.controller) show(); }); });
  }).catch(() => {});
  // Reload only when an existing worker is replaced (the update button), not when the first install claims the page.
  const hadController = !!navigator.serviceWorker.controller;
  let reloaded = false; navigator.serviceWorker.addEventListener('controllerchange', () => { if (hadController && !reloaded) { reloaded = true; location.reload(); } });
}
