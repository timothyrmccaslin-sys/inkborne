// Inkborne service worker: versioned, offline-first.
// VERSION must match APP_VERSION in src/main.js (bump both with tools/bump-version.sh).
// Plugs in at the repo root as /sw.js (registered by src/main.js as BASE + 'sw.js').
const VERSION = 'ib-0.1.0';
const PREFIX = 'ib-';

// The shell: everything needed to boot and play offline. Install fails if any of these is missing,
// so a half-cached release never takes control.
const SHELL = [
  './',
  'index.html',
  'style.css',
  'manifest.json',
  'src/main.js', 'src/input.js', 'src/audio.js', 'src/art.js', 'src/ui.js', 'src/ink.js',
  'src/figures.js', 'src/blips.js',
  'src/scenes/title.js', 'src/scenes/world.js', 'src/scenes/poi.js',
  'pkg/inkborne_core.js', 'pkg/inkborne_core_bg.wasm',
  'data/party.json', 'data/enemies.json', 'data/items.json', 'data/transformation.json',
  'data/strings.json', 'data/barks.json', 'data/dialogue.json', 'data/shops.json',
  'data/world.json', 'data/story.json', 'data/elements.json',
  'data/pois/forest.json', 'data/pois/town.json',
  'fonts/permanentmarker.woff2', 'fonts/patrickhandsc.woff2',
  'assets/art/manifest.json',
];

// Best effort: cached at install if present, skipped (not fatal) if missing. Covers scenes and assets
// that are still in flight (TODO(dev) battle/dialogue/shop, TODO(art) icons) plus the heavier media.
const EXTRA = [
  'src/scenes/battle.js', 'src/scenes/dialogue.js', 'src/scenes/shop.js',
  'assets/icons/icon-192.png', 'assets/icons/icon-512.png', 'assets/icons/icon-maskable-512.png',
  'assets/icons/apple-touch-icon.png',
  'assets/art/bg/world-bg.webp', 'assets/art/bg/battle-forest.webp',
  'assets/art/bg/poi-forest-far.webp', 'assets/art/bg/poi-forest-mid.webp', 'assets/art/bg/poi-forest-near.webp',
  'assets/art/bg/poi-town-far.webp', 'assets/art/bg/poi-town-mid.webp', 'assets/art/bg/poi-town-near.webp',
  ...['amb-forest', 'amb-town', 'cancel', 'clean', 'coin', 'combo-finish', 'confirm', 'enemy-defeat', 'enemy-hit', 'guard', 'heal', 'hit', 'hit-crit', 'hit-heavy', 'inkwing', 'lantern', 'miss', 'move', 'ring', 'seal', 'step', 'step-dirt-02', 'step-dirt-03', 'step-dirt-04', 'step-wood-01', 'step-wood-02', 'text', 'wind', 'wipe']
    .map((k) => `assets/sfx/${k}.mp3`),
  ...['itsuki', 'benika', 'gonzo'].flatMap((w) => [
    ...[1, 2, 3].flatMap((n) => ['grunt', 'attack', 'blip'].map((k) => `assets/voice/voice-${w}-${k}-${n}.mp3`)),
    `assets/voice/voice-${w}-unfurl.mp3`, `assets/voice/voice-${w}-ko.mp3`,
  ]),
  'assets/voice/voice-gonzo-hum.mp3',
];

const url = (p) => new URL(p, self.registration.scope).href;
// cache: 'reload' skips the HTTP cache so a new VERSION never precaches stale files from GitHub Pages.
const req = (p) => new Request(url(p), { cache: 'reload' });

self.addEventListener('install', (e) => {
  e.waitUntil((async () => {
    const c = await caches.open(VERSION);
    await c.addAll(SHELL.map(req));
    await Promise.all(EXTRA.map((p) => c.add(req(p)).catch(() => {})));
    // Music tracks are listed in Cody's assets/music/manifest.json, so precache whatever it names.
    try {
      const m = await (await fetch(req('assets/music/manifest.json'))).json();
      await c.put(url('assets/music/manifest.json'), new Response(JSON.stringify(m), { headers: { 'Content-Type': 'application/json' } }));
      await Promise.all((m.tracks || []).map((t) => c.add(req(`assets/music/${t.file || t.key + '.mp3'}`)).catch(() => {})));
    } catch (err) { /* no music yet: the runtime synth fallback covers it */ }
    // No skipWaiting here: src/main.js shows "New version, tap to refresh" and sends SKIP_WAITING.
  })());
});

self.addEventListener('activate', (e) => {
  e.waitUntil((async () => {
    const keys = await caches.keys();
    await Promise.all(keys.filter((k) => k.startsWith(PREFIX) && k !== VERSION).map((k) => caches.delete(k)));
    if (self.registration.navigationPreload) await self.registration.navigationPreload.disable().catch(() => {});
    await self.clients.claim();
  })());
});

self.addEventListener('message', (e) => {
  const t = e.data && e.data.type;
  if (t === 'SKIP_WAITING') self.skipWaiting();
  else if (t === 'GET_VERSION' && e.ports[0]) e.ports[0].postMessage({ version: VERSION });
});

self.addEventListener('fetch', (e) => {
  const r = e.request;
  if (r.method !== 'GET') return;
  const u = new URL(r.url);
  if (u.origin !== location.origin) return; // nothing cross-origin in the shell
  if (r.headers.has('range')) return; // let the network handle partial media requests

  // Page loads: serve the cached shell (any query string), fall back to network, then to the cached index.
  if (r.mode === 'navigate') {
    e.respondWith((async () => {
      const c = await caches.open(VERSION);
      return (await c.match(url('./'), { ignoreSearch: true })) ||
        (await c.match(url('index.html'))) ||
        fetch(r).catch(() => new Response('Inkborne is offline and not cached yet.', { status: 503, headers: { 'Content-Type': 'text/plain' } }));
    })());
    return;
  }

  // Everything else: cache first, then network, and keep a copy in this version's cache.
  e.respondWith((async () => {
    const c = await caches.open(VERSION);
    const hit = await c.match(r, { ignoreSearch: true });
    if (hit) return hit;
    try {
      const res = await fetch(r);
      if (res.ok && res.type === 'basic') c.put(r, res.clone()).catch(() => {});
      return res;
    } catch (err) {
      return new Response('', { status: 504, statusText: 'offline' });
    }
  })());
});
