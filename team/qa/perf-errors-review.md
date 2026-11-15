# Inkborne: Performance & Error-Handling Review
- Owner: Sam (Error Handling & Code Efficiency) · Lead: Noe · For: Marc
- Snapshot: **2026-11-15, ~3:45 PM America/Chicago (CST)**, HEAD `afdfcc9` (on top of `63923da`, ib-0.1.0)
- Status: **PARTIAL. This is a static code review only.** The runtime pass (WebKit with iPad landscape emulation, fps sampling, console capture, storage and service-worker fault injection) was stopped twice by Grok Bot request limits. It's queued to run next.
- Scope: `src/*.js`, `src/scenes/*.js`, `sw.js`, `index.html`, `core/src/lib.rs`, `core/Cargo.toml`, `pkg/`. No game source was edited.

## Blockers
**None found in this static pass.** The earlier boot blockers in `findings.md` look fixed at `afdfcc9`, which Noe should confirm:
- P0-1: `src/scenes/battle.js`, `dialogue.js`, and `shop.js` now exist.
- P0-2: the `Audio` constructor no longer has `this.music = null`.
- P1-1: `sw.js` exists, with `VERSION = 'ib-0.1.0'` matching `APP_VERSION`.
- All 37 `SHELL` precache URLs in `sw.js` exist on disk, so `addAll` won't fail on a missing file at this commit.

Open gate: the goals of a solid iPad frame rate and zero console errors are **unverified** until the runtime pass and a real-iPad check happen.

## P1 (should fix before the demo)

### P1-S1. A full-screen canvas blur runs every frame in dialogue and shop
- **Where:** `src/scenes/dialogue.js:40` (`ctx.filter = 'blur(6px)'` on a 1320×744 draw) and `src/scenes/shop.js:42` (`blur(4px)`). Both run inside `draw()`.
- **Impact:** A Gaussian blur over the whole frame at device pixel ratio 2 is probably the most expensive thing per frame in the game. Expect fps drops on iPad whenever a dialogue or shop is open. Also, Canvas2D `filter` support in Safari is recent, and older iPadOS ignores it silently, so the look will differ by device.
- **Fix:** Blur once, not per frame. Render the blurred background into an offscreen canvas in `enter()` (or ship a pre-blurred `.webp`) and `drawImage` that:
  ```js
  // enter()
  blurred = canvas(1280, 720); const x = blurred.getContext('2d');
  x.filter = 'blur(6px)'; x.drawImage(bg, -20, -12, 1320, 744);
  // draw()
  ctx.drawImage(blurred, 0, 0);
  ```
  `world.js:13` already does it this way, baking the filter once into an offscreen canvas.

### P1-S2. One exception in a scene permanently freezes the game, and nothing global catches errors
- **Where:** `src/main.js` `frame()`, lines ~66-84. `top.update()` and `draw()` have no guard around them, and `requestAnimationFrame(frame)` is the last line. No `window.onerror` or `unhandledrejection` handler exists anywhere.
- **Impact:** Any throw (for example a bad JSON field from the core or a missing art key) leaves one uncaught error in the console, stops the loop, and freezes the canvas with no way to recover. That fails both goals at once.
- **Fix:** Schedule the next frame first and isolate the work:
  ```js
  function frame(now) {
    requestAnimationFrame(frame);
    try { step(now); } catch (e) { if (!game.err) { game.err = e; console.error(e); } showRecover(e); }
  }
  addEventListener('error', (e) => report(e.error || e.message));
  addEventListener('unhandledrejection', (e) => { report(e.reason); e.preventDefault(); });
  ```
  `showRecover` would be a small paper panel offering to return to title, using the last save.

### P1-S3. The canvas backing store is very large on iPad, and the whole thing repaints every frame
- **Where:** `src/main.js:19-23` `fit()`. The canvas is sized to the **whole viewport** times DPR (capped at 2), but the game is a 1280×720 letterboxed area.
- **Impact:** An iPad Pro 12.9" in landscape gets a 2732×2048 canvas (5.6 megapixels). Every frame clears it, letterbox included, and redraws gradients and washes. Canvas2D fill-rate is the usual fps limit on iPad Safari.
- **Fix:** Size the canvas to the game area only (`W*s*dpr × H*s*dpr`) and position it with CSS, using a CSS background for the letterbox. Lower the DPR cap to 1.5 on touch devices, or adjust it from measured frame time (drop to 1.5 or 1.25 if p95 > 18 ms). The ink art is soft, so it won't visibly lose detail at 1.5.

### P1-S4. The Rust battle exports index arrays without bounds checks, so a bad index kills the core for the session
- **Where:** `core/src/lib.rs`. These are exported calls that take an index from JS: `stroke`, `guard`, `inkwing`, `use_item`, and `seal_art`, which index `self.fighters[actor]` / `[target]` at lines 192, 211-212, 234, 268, and 274. Line 245 does `self.party[self.fighters[actor].idx]`, which is wrong if `actor` is an enemy.
- **Impact:** `Cargo.toml` sets `panic = "abort"`, so an out-of-range index traps with `RuntimeError: unreachable`. After that trap the `Game` object is generally unusable, and every later call throws, which means a cascade of console errors and a dead battle. Normal UI flow passes valid indices, but stale targets, overlapping inputs during transitions, or a tampered save can trigger it.
- **Fix:** Validate at the boundary and return an error object instead of panicking:
  ```rust
  let Some(a) = self.fighters.get(actor) else { return r#"{"error":"bad actor"}"#.into() };
  if a.side != 0 { return r#"{"error":"not a party member"}"#.into() }
  ```
  Then have the JS check `res.error` before animating. Keep `panic = "abort"` for size, but add a debug-build `console_error_panic_hook` so any remaining panic gives a readable message.

## P2 (polish and efficiency)

- **P2-S1. Failed saves are silent.** `main.js:30`: `game.save` swallows every error. In Safari Private Browsing, or when the quota is full (`QuotaExceededError`), the player thinks they saved and loses progress. Return a boolean and show a short "Couldn't save" banner.
- **P2-S2. The first tap triggers a big decode spike.** `audio.js` `unlock()` calls `loadAll()`, which fetches and decodes every SFX and roughly 40 voice clips at once on the first touch. That can hitch the title screen and spike memory on iPad. Load SFX first, then voices per scene and in the background, with a small concurrency limit.
- **P2-S3. The first install competes with boot.** In the `sw.js` install, about 130 `EXTRA` `cache.add` calls fire in parallel on the first visit, alongside the game's own boot fetches, art loading, and audio decoding. Limit concurrency to around 6, or warm the `EXTRA` items after the title screen is up (for example from a `message` sent to the worker).
- **P2-S4. Walking allocates every frame.** `poi.js:29` calls `game.core.walker_step(...)`, which returns a `Vec<f64>`, so a new typed array crosses the JS/WASM boundary every frame while the player moves. That's small but steady garbage. Return nothing, and read `walker_x()` / `walker_y()` getters, or a view into WASM memory.
- **P2-S5. Gradients are rebuilt on every call.** `ink.js` `wash()` and `washPoly()` create a new gradient object each time. Anywhere they run inside a per-frame `draw()`, cache the result by pre-rendering into an offscreen canvas, as `ambient.js` already does for mist and glow. I still need to measure which scenes call them per frame.
- **P2-S6. Old cache prefixes aren't cleaned.** `sw.js` `activate` only deletes `ib-*` caches. If any earlier test deploy used a different prefix, those caches stay on testers' iPads for good. This is low risk, so make a one-time cleanup of known legacy prefixes, or of all non-`ib-` caches this origin owns.
- **P2-S7. Audio unlock listeners are never removed.** `audio.js:16` keeps four global listeners that run `unlock()` on every tap and keypress. The cost is small, but once `ctx.state === 'running'` they can come off (keep a `visibilitychange` resume instead, since iOS suspends audio in the background).

## What's already good
- There is a single `requestAnimationFrame` loop with `dt` clamped to 50 ms, and no `setInterval` loops.
- DPR is capped at 2, and the canvas is only resized on `resize`.
- `fetch` checks `r.ok`, boot failures show a message on screen, and dynamic scene imports sit inside the `try` block.
- `localStorage` reads and writes are wrapped, and the save's shape is validated before `load_json`.
- One `AudioContext` is unlocked on a user gesture, with `audioSession` set to playback and decoded buffers cached.
- The service worker uses a versioned cache and `cache: 'reload'` on precache, bypasses Range requests, doesn't skip waiting until the update button is tapped, and only reloads on a real controller change.
- The release profile uses `opt-level="s"`, `lto`, `codegen-units=1`, `panic="abort"`, and `wasm-opt -Os`. The `.wasm` is 239 KB.
- Text drawn every frame goes through `fillText` in `ui.js`. That's acceptable at this text volume, so measure it on device before optimizing.

## Not yet verified (next pass)
1. Fps (average, p95, max frame time) in WebKit with iPad landscape emulation and 4× CPU throttle, for idle world, battle, Inkwing, dialogue, and shop.
2. The console-error count across the full loop: title, world, forest, battle (combos plus Inkwing), town, dialogue, shop, save, then reload.
3. Fault injection: `localStorage` throwing on read and write, a corrupt `inkborne-save-v1`, an offline reload after the worker installs, the update path with old-cache cleanup, and one asset returning 404.
4. A **real iPad** pass with Safari Web Inspector Timelines. Headless WebKit isn't a substitute for thermal behavior or Safari's Canvas2D GPU path.

## Review criteria (condensed)
- **Frame rate:** steady 60 fps (16.6 ms per frame), with no battle frame over 33 ms. One rAF loop, no per-frame boundary allocations, a capped backing store, no per-frame filters, pre-rendered static layers, and combo timing taken from `event.timeStamp`.
- **Errors:** no `unwrap` or unchecked indexing on runtime data in Rust, `Result`/error objects at the boundary, every `fetch` checked, global error nets, guarded storage, and a service worker that never `addAll`s a 404. The console stays empty through the full test-plan loop.
