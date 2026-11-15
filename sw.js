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
  'src/art.js',
  'src/audio.js',
  'src/blips.js',
  'src/figures.js',
  'src/ink.js',
  'src/input.js',
  'src/main.js',
  'src/scenes/battle.js',
  'src/scenes/dialogue.js',
  'src/scenes/poi.js',
  'src/scenes/shop.js',
  'src/scenes/title.js',
  'src/scenes/world.js',
  'src/ui.js',
  'pkg/inkborne_core.js',
  'pkg/inkborne_core_bg.wasm',
  'data/barks.json',
  'data/dialogue.json',
  'data/elements.json',
  'data/enemies.json',
  'data/items.json',
  'data/party.json',
  'data/pois/forest.json',
  'data/pois/town.json',
  'data/shops.json',
  'data/story.json',
  'data/strings.json',
  'data/transformation.json',
  'data/world.json',
  'fonts/inkborne-kanji.woff2',
  'fonts/patrickhandsc.woff2',
  'fonts/permanentmarker.woff2',
  'assets/art/manifest.json',
];

// Best effort: cached at install if present, skipped (not fatal) if missing. Covers scenes and assets
// that are still in flight (TODO(dev) battle/dialogue/shop, TODO(art) icons) plus the heavier media.
const EXTRA = [
  'assets/icons/apple-touch-icon.png',
  'assets/icons/icon-192.png',
  'assets/icons/icon-512.png',
  'assets/icons/icon-maskable-512.png',
  'assets/art/bg/battle-forest.webp',
  'assets/art/bg/poi-forest-far.webp',
  'assets/art/bg/poi-forest-mid.webp',
  'assets/art/bg/poi-forest-near.webp',
  'assets/art/bg/poi-town-far.webp',
  'assets/art/bg/poi-town-mid.webp',
  'assets/art/bg/poi-town-near.webp',
  'assets/art/bg/world-bg.webp',
  'assets/art/fx/fx-brushstroke-clean-line.webp',
  'assets/art/fx/fx-brushstroke-fail.webp',
  'assets/art/fx/fx-death-demo.webp',
  'assets/art/fx/fx-death-ink.webp',
  'assets/art/fx/fx-death-mask.webp',
  'assets/art/fx/fx-hit-heavy.webp',
  'assets/art/fx/fx-hit-light.webp',
  'assets/art/fx/fx-inkwing-ember-loop.webp',
  'assets/art/fx/fx-inkwing-ember.webp',
  'assets/art/fx/fx-inkwing-gale-loop.webp',
  'assets/art/fx/fx-inkwing-gale.webp',
  'assets/art/fx/fx-inkwing-stone-loop.webp',
  'assets/art/fx/fx-inkwing-stone.webp',
  'assets/art/fx/fx-seal-ember.webp',
  'assets/art/fx/fx-seal-gale.webp',
  'assets/art/fx/fx-seal-mark.webp',
  'assets/art/fx/fx-seal-pass.webp',
  'assets/art/fx/fx-seal-stone.webp',
  'assets/art/icons/icon-festival_bento.webp',
  'assets/art/icons/icon-fresh_ink_pot.webp',
  'assets/art/icons/icon-inkstone_chip.webp',
  'assets/art/icons/icon-paper_cracker.webp',
  'assets/art/icons/icon-pine_tea.webp',
  'assets/art/icons/icon-plum_tonic.webp',
  'assets/art/icons/icon-rice_cake.webp',
  'assets/art/icons/icon-thunder_jar.webp',
  'assets/music/battle.mp3',
  'assets/music/extra-shop.mp3',
  'assets/music/extra-transform-sting.mp3',
  'assets/music/extra-victory-fanfare.mp3',
  'assets/music/extra-victory-loop.mp3',
  'assets/music/forest.mp3',
  'assets/music/title.mp3',
  'assets/music/town.mp3',
  'assets/music/world.mp3',
  'assets/sfx/amb-forest.mp3',
  'assets/sfx/amb-town.mp3',
  'assets/sfx/cancel.mp3',
  'assets/sfx/clean.mp3',
  'assets/sfx/coin.mp3',
  'assets/sfx/combo-finish.mp3',
  'assets/sfx/confirm.mp3',
  'assets/sfx/enemy-defeat.mp3',
  'assets/sfx/enemy-hit.mp3',
  'assets/sfx/guard.mp3',
  'assets/sfx/heal.mp3',
  'assets/sfx/hit-crit.mp3',
  'assets/sfx/hit-heavy.mp3',
  'assets/sfx/hit.mp3',
  'assets/sfx/inkwing.mp3',
  'assets/sfx/lantern.mp3',
  'assets/sfx/miss.mp3',
  'assets/sfx/move.mp3',
  'assets/sfx/ring.mp3',
  'assets/sfx/seal.mp3',
  'assets/sfx/step-dirt-02.mp3',
  'assets/sfx/step-dirt-03.mp3',
  'assets/sfx/step-dirt-04.mp3',
  'assets/sfx/step-wood-01.mp3',
  'assets/sfx/step-wood-02.mp3',
  'assets/sfx/step.mp3',
  'assets/sfx/text.mp3',
  'assets/sfx/wind.mp3',
  'assets/sfx/wipe.mp3',
  'assets/voice/voice-benika-attack-1.mp3',
  'assets/voice/voice-benika-attack-2.mp3',
  'assets/voice/voice-benika-attack-3.mp3',
  'assets/voice/voice-benika-blip-1.mp3',
  'assets/voice/voice-benika-blip-2.mp3',
  'assets/voice/voice-benika-blip-3.mp3',
  'assets/voice/voice-benika-grunt-1.mp3',
  'assets/voice/voice-benika-grunt-2.mp3',
  'assets/voice/voice-benika-grunt-3.mp3',
  'assets/voice/voice-benika-ko.mp3',
  'assets/voice/voice-benika-unfurl.mp3',
  'assets/voice/voice-gonzo-attack-1.mp3',
  'assets/voice/voice-gonzo-attack-2.mp3',
  'assets/voice/voice-gonzo-attack-3.mp3',
  'assets/voice/voice-gonzo-blip-1.mp3',
  'assets/voice/voice-gonzo-blip-2.mp3',
  'assets/voice/voice-gonzo-blip-3.mp3',
  'assets/voice/voice-gonzo-grunt-1.mp3',
  'assets/voice/voice-gonzo-grunt-2.mp3',
  'assets/voice/voice-gonzo-grunt-3.mp3',
  'assets/voice/voice-gonzo-hum.mp3',
  'assets/voice/voice-gonzo-ko.mp3',
  'assets/voice/voice-gonzo-unfurl.mp3',
  'assets/voice/voice-itsuki-attack-1.mp3',
  'assets/voice/voice-itsuki-attack-2.mp3',
  'assets/voice/voice-itsuki-attack-3.mp3',
  'assets/voice/voice-itsuki-blip-1.mp3',
  'assets/voice/voice-itsuki-blip-2.mp3',
  'assets/voice/voice-itsuki-blip-3.mp3',
  'assets/voice/voice-itsuki-grunt-1.mp3',
  'assets/voice/voice-itsuki-grunt-2.mp3',
  'assets/voice/voice-itsuki-grunt-3.mp3',
  'assets/voice/voice-itsuki-ko.mp3',
  'assets/voice/voice-itsuki-unfurl.mp3',
  'assets/music/manifest.json',
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
