# PWA shell (Wes), first cut

Files and where they go:
- `sw.js` goes to the repo root as `/sw.js`. `src/main.js` already registers `BASE + 'sw.js'`.
- `manifest.json` replaces the root `manifest.json`. The only changes are `start_url` and `scope`, which are now `./`, so the same file works under `/inkborne/` on Pages and at `/` locally. I also added `dir` and `prefer_related_applications`.
- `main-controllerchange.patch` is optional but recommended (see below).

How sw.js works:
- The cache is named `VERSION` (`ib-0.1.0`), which matches `APP_VERSION` in `src/main.js`. On activate it deletes every other `ib-*` cache.
- On install it precaches `SHELL` atomically: html, css, manifest, all src modules, the pkg js and wasm, all data JSON, fonts, and the art manifest. If any of those is missing, the install fails so a half-cached release never takes over.
- `EXTRA` is precached best-effort: the battle, dialogue and shop scenes, PWA icons, the bg art, every SFX and voice mp3, plus whatever `assets/music/manifest.json` lists.
- Page loads are served from the cached shell, which is cache-first and ignores the query string. Other same-origin GETs are cache-first with a network fallback, and anything new is stored in the current version's cache. Range requests and cross-origin requests are passed through untouched.
- Precache uses `cache: 'reload'` so a new VERSION never picks up stale files from the GitHub Pages HTTP cache.
- There's no auto skipWaiting. The existing update button in `main.js` posts `SKIP_WAITING`, and the worker also answers `GET_VERSION` through a MessageChannel.

Tested in headless Chrome with a copy of the repo served at /inkborne/:
- The first visit installs and the worker takes control, caching 135 entries, music included.
- Offline reload boots from cache, with wasm, data and modules all loading. Boot then stops on app bugs, listed below.
- After a VERSION bump, the update button appears. Tapping it reloads into `ib-0.1.1`, and the old cache is deleted.
- `node --check` passes.

Issues found (not in my files):
- P1: `src/main.js` imports `scenes/battle.js`, `dialogue.js` and `shop.js`, which don't exist yet, so boot fails online and offline until they land.
- P1: in `src/audio.js` the constructor sets `this.music = null`, which shadows the `music()` method. Boot then throws "this.music is not a function". The fix is to rename the field (for example `this.battleSynth`).
- P2: the `main.js` controllerchange handler reloads the page on the very first install too, because `clients.claim()` fires controllerchange. The patch only reloads when a previous worker was in control.
- P2: `tools/check-version-sync.sh` and `bump-version.sh` look for a line starting with `const APP_VERSION`, but `main.js` has `export const APP_VERSION`. The check fails as a result. Allow an optional `export ` in both regexes.
- Blocker for installability: `assets/icons/` is empty. `icon-192.png`, `icon-512.png`, `icon-maskable-512.png` and `apple-touch-icon.png` are needed from art or a `tools/` icon render.
