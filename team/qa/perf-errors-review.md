# Tabula Rasa (formerly Inkborne): Performance & Error-Handling Review
Owner: Sam (Error Handling & Code Efficiency) · Lead: Noe · Status: **Pre-review (no code yet)** · Updated 2026-11-15

## Blockers
1. **No SPEC.md and no source yet.** `/workspace/tabula-rasa` has only empty scaffold folders (`assets core data pkg src tools`) and `team/`. The actual review of Rust/WASM and JS code can't start until code lands. Until then, this file holds the standards I'll review against, so dev can build to them from day one.

## Findings by severity
_None yet. Findings will be filed as **Critical / High / Medium / Low** with file:line, repro, and measured impact (iPad Safari, landscape, installed PWA)._

## Review criteria (what I'll check once code exists)

### Frame rate on iPad Safari (target: steady 60 fps, 16.6 ms budget; no frame > 33 ms in battle)
- **One `requestAnimationFrame` loop**, driven from JS or `wasm-bindgen`, with fixed-timestep simulation + interpolated render. No `setInterval` game loops.
- **No per-frame allocation across the JS/WASM boundary.** No `String`/`Vec` returns, `JsValue` churn, or closures created every frame. Use shared typed-array views into WASM memory and re-create views only after `memory.grow`.
- **Batch draw calls.** WebGL2 with sprite atlases and instanced/batched quads preferred; if Canvas2D, pre-render static layers (map tiles, UI frames) to offscreen canvases.
- **Cap the backing-store size.** Canvas at `devicePixelRatio` capped (e.g. ≤2) and resized only on `resize`/orientation change; iPad Retina at full DPR is a common fps killer.
- **Text/dialogue:** render glyphs from an atlas or cache rasterized lines. Never `fillText` every frame for unchanged text.
- **Timed combos:** read input timestamps from `event.timeStamp` / `performance.now()`, not frame counts, so a dropped frame doesn't break a combo window.
- **Release build settings:** `opt-level = "s"` or `3`, `lto = true`, `codegen-units = 1`, `panic = "abort"` (after the panic hook decision below), `wasm-opt -O`. Track `.wasm` size in CI with Brandon.
- **Thermal throttling:** soak test 15+ min of battle on a real iPad; watch for fps decay.
- **Audio:** one `AudioContext`, resumed on first user gesture (iOS requirement), decoded buffers cached, no new nodes graph per SFX beyond source+gain.

### Zero console errors
- **Rust:** no `unwrap()`/`expect()` on runtime data (assets, saves, input). Return `Result<_, JsValue>` from exported fns; install `console_error_panic_hook` in debug builds only.
- **Asset loading:** every `fetch` checks `response.ok`; missing asset = logged once + fallback, never an uncaught rejection.
- **Global nets:** `window.onerror` and `unhandledrejection` handlers that report (in dev) and show a recoverable error screen (in prod) instead of a frozen canvas.
- **Save data:** `localStorage`/IndexedDB access wrapped in try/catch (Safari private mode and quota errors throw). Validate + version saves; a corrupt save must not crash boot. Coordinate with John's tamper checks.
- **Service worker:** versioned cache name, old caches deleted on `activate`, no `addAll` of URLs that 404 (one bad URL fails the whole install), correct MIME type `application/wasm` so `instantiateStreaming` works, with an `instantiate` fallback.
- **PWA manifest:** valid icons at all declared sizes (missing icons log errors), `display: fullscreen`/`standalone`, `orientation: landscape`.
- **Input:** Gamepad API polled only when `navigator.getGamepads` exists; touch handlers registered `{ passive: false }` only where `preventDefault` is actually needed (otherwise Safari logs warnings and scrolling jank).
- **No deprecated APIs or 404s in the network tab** (favicon, source maps in prod).

### How I'll measure
- Safari Web Inspector (remote, from a Mac) Timelines: JS + rendering frames, memory.
- In-game debug overlay (please build one): fps, frame-time p95/max, draw calls, WASM heap size.
- Console must be empty through June's full test-plan loop: world map, forest path, battle (combos + transformation), town, dialogue, shop, save/load, offline relaunch.

## Recommendations (for dev now)
1. Add the debug overlay and global error handlers in the first commit; they're cheap and make every later review faster.
2. Pick WebGL2 + atlas rendering up front; retrofitting from per-sprite Canvas2D draws is costly.
3. Define a single `GameError` enum in Rust, mapped to `JsValue` at the boundary.
4. Get a release-profile WASM build into CI early so perf is measured on real builds, not debug.
