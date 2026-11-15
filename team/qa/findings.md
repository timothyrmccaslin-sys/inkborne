# Inkborne QA findings (team rollup)

- Author: Noe (Quality & Security), for Marc
- Snapshot: **2026-11-15 3:22 PM America/Chicago (CST)** — code is still landing; several files in `src/` and `data/` were rewritten in the hour before this pass

> **Integrator status note, 2026-11-15 3:52 PM CST (ib-0.1.1 build). The 3:22 PM snapshot below is out of date; Noe to refresh on the next pass.**
> - P0-1 **fixed** (battle/dialogue/shop scenes exist; 0.1.0 boots live). P0-2 **fixed** (Audio no longer shadows `music()`).
> - P1-1 **fixed** (`sw.js` present, VERSION synced with APP_VERSION, offline reload verified on 0.1.0). P1-2 **fixed** (art team icons in `assets/icons/`).
> - P1-3 **fixed** (guarded `readSave()`/`hasSave`/load; a failed load stays on title). P1-4 **addressed in 0.1.1** by Jared's save module (0010/0011: validation, clamps, version and size checks) if it passes the release gate. P1-5 **fixed** (enemy_turn unwrap removed).
> - P2-6 **fixed** (leftover "Tabula Rasa" comment in `src/blips.js`). P2-10 **fixed** (`fonts/inkborne-kanji.woff2`). P2-7 / P2-8 (`save_json` / turn-order `unwrap`) still open. IP watch items P2-1 to P2-5 unchanged.

- SPEC: v1.1 (title Inkborne, crate `inkborne_core`, save key `inkborne-save-v1`, version prefix `ib-`, gauge **Vermilion Ink**)
- Scope: rollup of `team/qa/` inputs, plus a light static first pass on the code that exists now. No files outside `team/qa/` were edited. The demo was not booted in a browser; there is no playable build yet.

## Inputs rolled up

| File | Owner | Status at this snapshot |
|---|---|---|
| `ip-similarity.md` | Noe | Completed against SPEC v1.1 and then-current data/docs. Originally **0 P0, 2 P1, 7 P2**. Live data and story docs have since moved: both P1s and two of the P2s are **resolved** in the current tree (see Resolved). Remaining items are watch-list P2s below. |
| `test-plan.md` | June | **Pre-review.** Draft v0.1 written at 2:58 PM CST, before `SPEC.md` and any code existed. Still a useful matrix (iPad PWA landscape, touch / gamepad / keyboard, full demo loop), but every `[SPEC]` threshold is a placeholder and nothing in it has been executed. |
| `perf-errors-review.md` | Sam | **Pre-review.** Written before source existed (and still titled Tabula Rasa). Holds review criteria only; no measured iPad fps or console-error findings yet. This static pass checks a subset of those criteria against current `src/` and `core/src`. |
| `save-tamper.md` | John | **Pre-review.** Written before SPEC and the save module existed (still titled Tabula Rasa). The "Must" items are now checked lightly against `save_json` / `load_json`; John's ten tamper cases have not been run. |
| `ci-pipeline.md` | Brandon | **Pre-review.** Draft v0, written before SPEC. A temporary Pages deploy workflow (`.github/workflows/pages-temp.yml`) has landed; the planned lint / test / build / PWA CI has not. |

## Blockers

Two P0 issues prevent the demo from booting at all:

1. **P0-1.** `src/main.js` imports `battle`, `dialogue`, and `shop` scene modules that do not exist, so `boot()` rejects before the title screen.
2. **P0-2.** Even after those modules land, `title.enter()` will still throw: `Audio` stores `this.music = null`, which shadows the `music()` method that `setScene('title')` calls.

Until both are fixed, there is no playable build to test. Missing `sw.js` and PWA icons are P1 (the game can run in a Safari tab without them, but the installable offline PWA in SPEC §1 cannot).

---

## P0 — must change before demo

### P0-1. Action scene modules are missing, and boot imports them unconditionally

- **Owner:** dev
- **File:** `src/main.js:13`, `src/main.js:95`; missing `src/scenes/battle.js`, `src/scenes/dialogue.js`, `src/scenes/shop.js`
- **What is wrong:** SPEC §3 requires `title`, `world`, `poi`, and an `action` view with modes `battle`, `dialogue`, and `shop`. `title.js`, `world.js`, and `poi.js` exist and export `create`. The three action modules do not. `boot()` still does `for (const n of scenes) SCENES[n] = await import(\`./scenes/${n}.js\`)` over `['title', 'world', 'poi', 'battle', 'dialogue', 'shop']` before creating the title scene. A missing module rejects, the `catch` writes "Could not start: …" into `#boot`, and the rAF loop never starts. `poi.js:16-18` already `game.push`es those three names, so the full loop would break at the first trigger even if boot were relaxed.
- **Fix:** Land the three action scene modules with the SPEC §3 `create` / `enter` / `exit` / `update` / `draw` / `onResult` shape (battle needs Brushstroke Chain, Vermilion Ink, Unfurl / Inkwing, Seal Arts, and Still Water). Do not skip the import of a name that `poi.js` can push.

### P0-2. `this.music = null` shadows `Audio.music()`, so the title scene cannot enter

- **Owner:** dev (audio)
- **File:** `src/audio.js:13`, also `:27` and `:61`; called from `src/scenes/title.js:8` (and later `world.js:31`, `poi.js:23`)
- **What is wrong:** The constructor sets an instance field `this.music = null`. That shadows the class method `async music(key)` on every instance. `title.enter()` now calls `game.audio.setScene('title')`, and `setScene` does `if (kind in M) this.music(M[kind])`. That is `TypeError: this.music is not a function`. `enter()` runs inside `boot()`'s `try` before `#boot` is removed and before `requestAnimationFrame(frame)`, so boot fails with "Could not start: this.music is not a function". Reproduced with a standalone class of the same shape. `this.musicSrc` / `this.musicKey` already track the playing cue; the field is leftover.
- **Fix:** Delete `this.music = null` from the constructor, or rename the field (for example `this._music`). Do not rename the method without updating every `this.music(...)` call. Re-test `setScene` for `title`, `world`, `forest`, `town`, and `battle`.

---

## P1 — should change

### P1-1. No service worker (`sw.js` is missing)

- **Owner:** dev
- **File:** expected at `/workspace/inkborne/sw.js` (registered from `src/main.js:105-110`); SPEC §1
- **What is wrong:** `index.html` and `manifest.json` exist. `sw.js` does not. `boot` registers `BASE + 'sw.js'` and swallows the failure, so a Safari-tab session can still start once P0 is fixed, but the game is not an offline-capable PWA. `APP_VERSION` is `ib-0.1.0`; there is no matching `VERSION` in `sw.js` to bump with it. The temporary Pages workflow skips the version-sync check when `sw.js` is absent.
- **Fix:** Add `sw.js` with `VERSION = 'ib-0.1.0'` (keep it in lockstep with `APP_VERSION` via `tools/check-version-sync.sh`), a versioned cache name, a precache of the shell + `pkg/inkborne_core_bg.wasm` + committed assets, `activate` cleanup of old caches, and a `SKIP_WAITING` message handler. Do not `addAll` a URL that 404s.

### P1-2. PWA icons are referenced but `assets/icons/` is empty

- **Owner:** art (icons), dev to hook them up if paths change
- **File:** `index.html:14-15`, `manifest.json:16-18`, empty dir `assets/icons/`
- **What is wrong:** The HTML asks for `assets/icons/icon-192.png` and `assets/icons/apple-touch-icon.png`. The manifest also asks for `icon-512.png` and `icon-maskable-512.png`. None of those files exist. Missing icons log console errors and break installability on iPad (Add to Home Screen).
- **Fix:** Add the four PNGs at the declared sizes (192, 512, 512 maskable, 180 apple-touch-icon) and confirm the paths in `index.html` / `manifest.json`.

### P1-3. `hasSave` / `load` are not guarded; a failed load still enters the world

- **Owner:** dev
- **File:** `src/main.js:31-32`, used from `src/scenes/title.js:6` and `:17`
- **What is wrong:** `game.save()` is wrapped in `try/catch`. `game.hasSave()` and `game.load()` are not. `items()` calls `hasSave()` on every title `update` / `draw`. On iPad Safari, private mode and storage-quota errors throw from `localStorage`; there is no `try` in `frame()`, so that throw kills the rAF loop (frozen canvas). If Continue is chosen and `load_json` returns `false` (corrupt JSON), `title.js` ignores the result and still `game.go('world')`. `world.js:6` falls back to `W.start` when the node is empty, so this is not obviously a soft-lock, but the player is not told the save was unreadable.
- **Fix:** Wrap `hasSave` / `load` in `try/catch` like `save`. If `load` fails, show a short "save unreadable" message and start at `world.start`. Avoid calling `hasSave()` every frame (cache it on enter).

### P1-4. Save load accepts any structurally valid JSON with no validation

- **Owner:** dev (coordinate with systems)
- **File:** `core/src/lib.rs:103` (`load_json`); see also `save_json` at `:102`
- **What is wrong:** `load_json` already returns `false` on a parse error and does not panic, which is the right shape for John's "Must: load must never panic" on bad JSON. After a successful deserialize it assigns `self.st = v` with no clamp, no drop of unknown item / node IDs, no checksum, no backup slot, and no schema `version`. Out-of-range gold / HP / ink, or a node / item that does not exist, is therefore trusted. John's tamper table (cases 5–8) is still untested.
- **Fix:** After deserialize, clamp numbers (gold, HP, ink 0–100, item counts), drop unknown IDs, reset an unknown node to the last safe town / start, and either migrate or reject an unknown version. Keep parse failures as `false` (no `unwrap`). A simple checksum-plus-backup envelope is enough for a demo; do not try to make a local save tamper-proof.

### P1-5. Enemy AI path `unwrap`s a missing enemy definition

- **Owner:** dev
- **File:** `core/src/lib.rs:295`
- **What is wrong:** `let def = self.enemies.iter().find(|e| e.id == self.fighters[me].id).cloned().unwrap();` runs on the enemy turn. If the battling id is not in the enemies table (bad encounter data, or a tampered save that later starts a fight), this panics. Release profile is `panic = "abort"`, which tears down the WASM instance and reads as a frozen game. `Game::new` and `set_rules` already return `Result` / `bool` for JSON, so this is the remaining sharp edge on runtime data.
- **Fix:** If the definition is missing, skip the turn or end the battle with a safe result; never `unwrap` / `expect` / `panic!` on lookup of save, encounter, or JSON data.

---

## P2 — minor or watch

### P2-1. Six Inks opposed pairs match Legend of Dragoon's three pairs (watch)

- **Owner:** systems / story
- **File:** `SPEC.md:34` (and systems element data)
- **What is wrong:** Ember↔Tide, Gale↔Stone, Dawn↔Dusk with ×2 / same ×0.5 track LoD's Fire↔Water, Wind↔Earth, Light↔Dark multipliers. Names are original; the pairing is a common JRPG pattern and is not a blocker.
- **Fix:** No change required for the demo. If more distance is wanted later, swap one pairing or add an unpaired ink.

### P2-2. "Who is breaking the seals" / cracking shrine seals (watch)

- **Owner:** story
- **File:** live `data/story.json` hook (and `team/story/CANON.md`)
- **What is wrong:** The live hook is now about cracking red shrine seals and the Blot, not "fog that never lifts" (that earlier wording is gone). "Seals" is native to the ink-and-shrine aesthetic, but LoD's late plot turns on Signet Spheres that seal the Moon That Never Sets. Fine for the demo if seals stay local.
- **Fix:** Watch any later plot that adds a sealed moon, a world-tree, or a god split into body and soul, and rewrite that beat if it appears.

### P2-3. Starting-party roles resemble LoD's early party shape (watch)

- **Owner:** story
- **File:** live `data/party.json` (Itsuki swordsman / Benika archer-healer / Gonzō older heavy hitter)
- **What is wrong:** The shape is loosely familiar; names, looks, elements, and hook are original. No change needed.
- **Fix:** Do not later add "his village was burned" or "his childhood friend was captured and must be rescued from a prison."

### P2-4. Inkwing sprites, when they land, must not read as Dragoon armor

- **Owner:** art
- **File:** not in tree yet (`bt-<char>-inkwing-idle` and related keys, SPEC §5)
- **What is wrong:** Written forms (Gale Crane, Ember Kite, Stone Owl) are the right direction. LoD Dragoons are winged, floating, elemental-armored warriors.
- **Fix:** Keep Inkwing art clearly avian / ink-wash. No dragon motifs, helmets, or Dragoon-like plate.

### P2-5. Staging filename `spirit_paper` (outside this repo)

- **Owner:** art
- **File:** `/workspace/inkborne-creative/luc/out/icon/icon-spirit_paper.webp` (not in the demo tree)
- **What is wrong:** "Spirit" is the banned mechanic term. Harmless until imported.
- **Fix:** Rename before copying into `assets/`.

### P2-6. Leftover "Tabula Rasa" comment in live audio JS

- **Owner:** audio
- **File:** `src/blips.js:1`
- **What is wrong:** The file is a live ES module (`src/audio.js` imports it). The first line still says "Tabula Rasa". Not player-facing. The only other hit outside `team/` is `tools/integrate.py:11`, which is an intentional `replace('Tabula Rasa', 'Inkborne').replace('Spirit Ink', 'Vermilion Ink')` helper, not a leftover in output.
- **Fix:** Change the comment to Inkborne. (Related doc typo, not live code: `team/systems/jake/README.md:16` still says crate `tabula_core`; SPEC v1.1 and `core/Cargo.toml` use `inkborne_core`.)

### P2-7. `save_json` uses `unwrap` on serialize

- **Owner:** dev
- **File:** `core/src/lib.rs:102`
- **What is wrong:** `serde_json::to_string(&self.st).unwrap()`. This is the core's own `Save` struct, so failure is unlikely, but a panic on save would abort WASM. `game.save()` already swallows JS exceptions, which would not catch a Rust abort.
- **Fix:** Return `Result<String, JsValue>` (or a fallback `"{}"` plus a log) instead of `unwrap`.

### P2-8. Turn-order sort `unwrap`s `partial_cmp`

- **Owner:** dev
- **File:** `core/src/lib.rs:156`
- **What is wrong:** `key(b).partial_cmp(&key(a)).unwrap()` panics if a speed key is NaN (bad stats in data or a tampered save).
- **Fix:** Use `f64::total_cmp`, or `unwrap_or(Ordering::Equal)`.

### P2-9. Per-frame allocations on the JS / WASM boundary and in the rAF loop

- **Owner:** dev
- **File:** `src/main.js:62`; `src/scenes/poi.js:31`
- **What is wrong:** There is a single `requestAnimationFrame` loop (started once in `boot`, continues at `main.js:76`). No second rAF and no `setInterval` game loop in current `src/`. Two obvious per-frame costs remain: `game.taps = inp.pointerTaps.map(game.toLogical)` allocates an array and objects every frame, and `game.core.walker_triggers().split(',').filter(Boolean)` pulls a new Rust `String` across the WASM boundary every POI frame. Sam's iPad 60 fps budget is unmeasured.
- **Fix:** Reuse a taps buffer; have the core expose trigger ids without allocating a comma-separated string every frame (shared buffer or a cached dirty flag). Revisit once a build can be profiled on an iPad.

### P2-10. Kanji font is referenced but not in `fonts/`

- **Owner:** art
- **File:** `style.css:3` (`fonts/inkborne-kanji.woff2`); used by `src/ink.js:119-120` (seal stamps such as the title "墨生")
- **What is wrong:** `fonts/` only has `permanentmarker.woff2` and `patrickhandsc.woff2`. The `@font-face` for Kanji 404s; seals fall back to generic serif. Cosmetic, not a boot blocker.
- **Fix:** Add `fonts/inkborne-kanji.woff2`, or drop the `@font-face` until the file exists so the network tab stays clean.

### P2-11. `wasm-bindgen` is not pinned exactly

- **Owner:** dev (with Brandon)
- **File:** `core/Cargo.toml:12` (`wasm-bindgen = "0.2"`)
- **What is wrong:** Brandon's pre-review flagged CLI / crate skew as the usual cause of broken WASM builds. `cargo check` succeeds on this box (cargo 1.100.0, wasm-pack 0.13.1), and `pkg/inkborne_core.js` + `pkg/inkborne_core_bg.wasm` are committed, so this is not broken today.
- **Fix:** Pin an exact `=x.y.z` and install the same CLI in CI.

---

## Resolved since earlier reviews (do not re-open)

These were real findings in `ip-similarity.md` and are fixed in the **current** tree:

- **P1 "Spirit Ink" leftovers / UI label TBD.** Live `data/strings.json` has `battle.gauge.label: "Vermilion Ink"`. `team/story` source (`strings.json`, `CANON.md`, `cast.md`, `glossary.md`, `README.md`) and `team/BRIEF.md` have been updated to the locked name. `tools/integrate.py` also forces the label on integrate. No player-facing "Spirit Ink" remains outside historical QA notes.
- **P1 placeholder party (Yuzuru, wind-element spear).** Live `data/party.json` is now the canon cast: Itsuki (gale swordsman), Benika (ember shrine archer), Gonzō (stone monk), with Falling Pine / Three Prayer Slips / Temple Bell and the matching Seal Arts. No Yuzuru / Akane / Tsubaki in `data/`.
- **P2 "fog that never lifts"** is gone from the live hook.
- **P2 QA shorthand "SP"** is gone from `test-plan.md` (now "Ink").

---

## Static first-pass results (this snapshot)

- **(a) Syntax and imports.** `node --check` passed on all 11 files under `src/**/*.js`. Every static `import` resolves to a file that exists (`pkg/inkborne_core.js` included). The only broken imports are the three dynamic `./scenes/{battle,dialogue,shop}.js` loads in P0-1.
- **(b) PWA shell and SPEC §3 scenes.** `index.html` and `manifest.json` are present and named Inkborne, landscape, `display: fullscreen`. `sw.js` is absent (P1-1). Scene set: `title`, `world`, `poi` yes; `battle`, `dialogue`, `shop` no (P0-1). All twelve `data/*.json` files that `boot()` fetches exist, including `transformation.json` and `pois/forest.json` / `pois/town.json`.
- **(c) Leftover `tabula` / "Spirit Ink" outside `team/`.** Only `src/blips.js:1` (comment, P2-6) and the intentional rename helper in `tools/integrate.py:11`. No leftover in live `data/` or in the Rust crate name. A stale `tabula_core.wasm` still sits under `core/target/` from an earlier build; it is not shipped (`pkg/` has `inkborne_core_*`, and the Pages workflow excludes `core/`).
- **(d) Save key and version.** `SAVE_KEY = 'inkborne-save-v1'` and `APP_VERSION = 'ib-0.1.0'` in `src/main.js:8-9` match SPEC §1. `VERSION` in `sw.js` cannot be checked because the file is missing.
- **(e) Rust panics on runtime data.** Production `unwrap` sites in `core/src/` are `save_json` (P2-7), turn-order `partial_cmp` (P2-8), and the enemy-def lookup (P1-5). `load_json` and `Game::new` do not unwrap parse errors. Test-only `unwrap`s in the `#[cfg(test)]` module are ignored.
- **(f) `cargo check`.** cargo and wasm-pack are installed. `cargo check` in `core/` **passed** (dev profile, finished in 6.5s) for crate `inkborne_core` 0.1.0. No toolchain was installed for this review.
- **(g) Animation loop.** One rAF loop, no `setInterval` game loop. Per-frame allocations noted in P2-9. Canvas DPR is already capped at 2 (`main.js:20`).

---

## Not yet testable

What's missing for a playable build, and for June's full-loop plan:

- A boot that reaches the title screen (P0-1 and P0-2).
- Action scenes: battle (timed Brushstroke Chain, Vermilion Ink, Unfurl / Inkwing, Seal Arts, Still Water), dialogue, and shop.
- `sw.js`, PWA icons, and the Kanji font — needed for an installable offline iPad PWA and for seal typography.
- A deployed build URL with a visible version / hash (June's entry criterion).
- Real iPad hardware (or a real-device farm) for Safari and installed-PWA landscape testing with touch, gamepad, and keyboard. Desktop smoke only is P2 in the test plan.
- `tests/` Playwright scripts — the folder does not exist yet.
- In-browser save/load and John's tamper cases; Sam's fps / zero-console-error pass on iPad; soak / thermal test.
- CI beyond the temporary Pages deploy: no lint / unit / wasm-pack / Playwright / Lighthouse job is wired up.

`PROGRESS.md` agrees with this list (TODO: `battle.js`, `dialogue.js`, `shop.js`, `sw.js`, icons, kanji font, tests, deploy).

---

## Next QA deliverables

1. **Dev** lands P0-1 and P0-2 (and, ideally, `sw.js` + icons). Noe re-runs a boot smoke as soon as a build is available and updates this file.
2. **June** revises `test-plan.md` to v0.2 against SPEC v1.1 (fill in the `[SPEC]` placeholders: input map, Vermilion Ink / Unfurl rules, localStorage key, PWA update flow) and executes the loop on iPad once a build URL exists.
3. **Sam** replaces the pre-review with a real `perf-errors-review.md` (and a Sam section in this file) against `core/`, `src/`, and `pkg/`: one rAF, WASM traffic, global error handlers, iPad frame time. The 4:00 PM CT nudge still applies if this is not started.
4. **John** re-reviews the actual `save_json` / `load_json` path, runs the tamper table, and replaces the provisional `save-tamper.md`.
5. **Brandon** (with Rick) lands the real CI workflow in place of `pages-temp.yml`, pins `wasm-bindgen`, and validates manifest / SW / icons / version sync once `sw.js` exists.
6. **Noe** re-runs the IP-similarity check when Inkwing / character sprites land, and keeps this rollup current as scenes ship.

---

## Sam (perf/errors), static pass at `afdfcc9`, 2026-11-15 ~3:45 PM CST. PARTIAL: the runtime fps and console pass is still pending
Full detail with fix snippets is in `perf-errors-review.md`. **No new P0s.** P0-1, P0-2, and P1-1 above look fixed at `afdfcc9`: the scene modules exist, `this.music = null` is gone, and `sw.js` exists with all 37 shell URLs present. Noe, please confirm.

### P1-S1. A full-screen `ctx.filter` blur runs every frame in dialogue and shop
- **Owner:** dev
- **File:** `src/scenes/dialogue.js:40`, `src/scenes/shop.js:42`
- **What is wrong:** `blur(6px)` / `blur(4px)` is applied to a full-frame `drawImage` inside `draw()`, so it runs every frame at DPR 2. This is the likely worst fps cost on iPad, and older Safari ignores Canvas2D `filter`.
- **Fix:** Blur once into an offscreen canvas in `enter()` (the way `world.js:13` does) or ship a pre-blurred `.webp`.

### P1-S2. One exception freezes the game, and there are no global error handlers
- **Owner:** dev
- **File:** `src/main.js` `frame()` (~66-84)
- **What is wrong:** Scene `update`/`draw` has no guard, and the next `requestAnimationFrame` is scheduled last, so any throw stops the loop for good. There's no `window.onerror` or `unhandledrejection` handler.
- **Fix:** Call rAF first, wrap the step in try/catch (log once, show a "return to title" panel), and add global `error` and `unhandledrejection` handlers.

### P1-S3. The canvas backing store covers the whole viewport at DPR 2 and repaints in full every frame
- **Owner:** dev
- **File:** `src/main.js:19-23`
- **What is wrong:** An iPad Pro 12.9" in landscape gets a 2732×2048 Canvas2D surface, letterbox included, cleared and redrawn every frame.
- **Fix:** Size the canvas to the 1280×720 game area times scale; cap DPR at 1.5 on touch devices, or adjust it from measured frame time.

### P1-S4. Rust battle exports index without bounds checks, and `panic = "abort"` makes the core unusable for the session
- **Owner:** dev (core)
- **File:** `core/src/lib.rs:192, 211-212, 234, 245, 268, 274` (`stroke`, `guard`, `inkwing`, `use_item`, `seal_art`)
- **What is wrong:** `self.fighters[actor]` and `self.party[self.fighters[actor].idx]` are unchecked. A bad index traps (`RuntimeError: unreachable`), and every later call on `Game` fails.
- **Fix:** Use `fighters.get(i)` plus a side check at each export, return `{"error":…}` JSON, and have the JS check `res.error`.

### P2-S1 to P2-S7 (efficiency and polish)
- **P2-S1** (`main.js:30`): a failed save is silent in Private mode or when the quota is full. Return a boolean and show a banner.
- **P2-S2** (`audio.js` `unlock` → `loadAll`): every SFX and voice decodes on the first tap. Stage it: SFX first, voices per scene.
- **P2-S3** (`sw.js` install): about 130 parallel `EXTRA` adds compete with boot. Limit concurrency or warm them after the title screen is up.
- **P2-S4** (`poi.js:29`): `walker_step` returns a new `Vec<f64>` every frame. Use getters or a shared buffer.
- **P2-S5** (`ink.js` `wash`/`washPoly`): a new gradient is built on every call. Pre-render wherever it runs per frame.
- **P2-S6** (`sw.js` activate): only `ib-*` caches get cleaned. Remove any legacy-prefix caches once.
- **P2-S7** (`audio.js:16`): the global unlock listeners are never removed. Drop them once the audio context is running, and resume on `visibilitychange`.

---

## Save tamper (John)

Executed Sunday, Nov 15, 2026, 3:48 PM America/Chicago (CST) against the live build https://timothyrmccaslin-sys.github.io/inkborne/ (ib-0.1.0, commit **63923da**). Full write-up and the case table are in `save-tamper.md`. The local tree has since diverged; line numbers below are for 63923da.

### Blockers

- **ST-1 P0.** Incomplete `hp` or `ink` maps (`{}` or a missing party id) load fine, then `party_json` / `start_battle` index the maps and abort WASM (`RuntimeError: unreachable`). Opening the shop freezes on a half-drawn frame; starting a battle leaves a dark blank canvas. `core/src/lib.rs:125,138,140`. See save-tamper.md ST-1.
- **ST-2 P0.** Continue is offered for JS-valid JSON that Rust `load_json` rejects (`gold: -1` / `1e300`, string HP, negative or huge `u32` item counts, missing `node`). `title.js` ignores the `false` return, `world.enter()` writes a fresh default save, and mid-game progress is destroyed with no backup or message. `src/scenes/title.js:17-18`, `src/scenes/world.js:31`, `src/main.js:31-33`. See save-tamper.md ST-2.

### P1

- **ST-3 P1.** Successful loads do not clamp `hp` / `ink`. Negative HP is shown in the shop (`HP -10 → 40`); battle floors it to 1. HP of 99999 or `1e300` is used as current HP. `core/src/lib.rs:103,138`. See save-tamper.md ST-3.
- **ST-4 P1.** An unknown `node` is silently repaired to `world.start`. A locked node (`shrine_stair`) is a playable sequence break. Once-battle flags are trusted and can skip forest fights. `src/scenes/world.js:6,27,31`. See save-tamper.md ST-4.

### P2

- **ST-5 P2.** `save_json` still `unwrap`s serialize (`core/src/lib.rs:102`). Not hit with the current `Save` shape.
- **ST-6 P2.** Turn-order `partial_cmp(...).unwrap()` (`lib.rs:156`) is not reachable from this save key (`spd` is not stored). Still worth `total_cmp`. The enemy-def `unwrap` flagged in the earlier static pass is already a safe `match` in 63923da (`lib.rs:295`).
- **ST-7 P2.** Unknown item ids persist but are hidden from the shop; `u32::MAX` gold and stacks load and display. Cap or drop on load.
- **ST-8 P2.** No `version` field or CRC; treat a checksum as corruption, not cheating. A 5 MB `setItem` hits `QuotaExceededError` (1–4 MB store; a 5 MB `load_json` parse is fine).
- **ST-9 P2.** Garbage / empty / `{}` / truncated JSON hide Continue; New Game still overwrites the key with no backup.

POI walker position and party stats (`spd`, `lv`, …) are not in the save, so those tamper cases could not be run. 24 Playwright cases plus mid-game follow-ups; C11, C21, and C24 crashed (ST-1). Full table in `save-tamper.md`.
