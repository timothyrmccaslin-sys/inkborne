# Inkborne Demo: QA Test Plan
Owner: June (QA) · Lead: Noe · Status: **DRAFT v0.1 (pre-spec)** · 2026-11-15

## Blockers
1. **B1: `SPEC.md` does not exist yet** (`/workspace/inkborne/SPEC.md` missing as of 2026-11-15 14:58 CST). Every pass/fail threshold below marked `[SPEC]` is a placeholder until the spec lands: combo timing windows, transformation trigger rules, shop prices, save model, input bindings.
2. **B2: No build or source in `/workspace/inkborne`** yet, so nothing can be executed. Plan is written against the brief only.
3. **B3: Device access.** Real iPad (iPadOS current + previous major) running Safari and the installed PWA is required; simulators/desktop Safari do not reproduce touch latency, safe areas, audio unlock or storage eviction. Need confirmation of who owns the device or a cloud device farm (BrowserStack/LambdaTest real iPads).
4. **B4: Test split with Richard (Test Writer)** not yet agreed. Proposed split in §9.

## Findings by severity
None yet; no build exists. Findings will be logged here as **S1 Critical** (crash, soft-lock, data loss, demo cannot be completed), **S2 Major** (feature broken with workaround, input method unusable), **S3 Minor** (cosmetic, polish, non-blocking text), **S4 Trivial**. Each entry: ID, area, device/input, steps, expected, actual, frequency, build hash.

## Recommendations
- Land `SPEC.md` with explicit numbers (timing windows in ms/frames, Ink gain values, prices) so tests can assert them.
- Expose a debug overlay / URL flag (`?debug=1`) showing FPS, current input device, combo window state and RNG seed; and a seeded-RNG option for repeatable battles.
- Expose deterministic game-logic hooks from Rust (combo judging, damage, shop transactions) so Richard can unit-test them natively without WASM/browser.

---

## 1. Scope
Full demo loop: **World map → Forest path → Battle (timed combos + transformation) → Town → Dialogue → Shop**, plus the glue: title/boot, save/load, pause, settings, PWA install/offline.
Out of scope: perf profiling (Sam), save tamper (John), CI (Brandon), IP review (Noe), except where a gameplay test surfaces them; those get cross-filed.

## 2. Target matrix
| Dimension | Values | Priority |
|---|---|---|
| Device | iPad (A-series, older supported model), iPad Air/Pro (M-series) | P0 both |
| OS | iPadOS current major; previous major | P0 current, P1 previous |
| Shell | Installed PWA (Add to Home Screen) · Safari tab | P0 PWA, P1 tab |
| Orientation | Landscape (left & right) · portrait (must show rotate prompt or adapt, per [SPEC]) | P0 |
| Input | Touch · Gamepad (MFi/Xbox/DualSense via Gamepad API) · Bluetooth/Magic keyboard | P0 all three |
| Smoke only | Desktop Chrome/Firefox/Safari | P2 |

## 3. Entry / exit criteria
**Entry:** build deployed at a stable URL with build hash visible; SPEC.md v1; smoke test (§5.0) passes.
**Exit for demo sign-off:** 0 open S1; 0 open S2 on P0 matrix cells; full loop completed with each input method on each P0 device; installed PWA launches offline after first load; no console errors during the loop (shared check with Sam).

## 4. Cross-cutting checks (apply to every area)
- **Input parity:** every action reachable by touch, gamepad and keyboard alone; no step requires a second input method. On-screen prompts/glyphs swap to match the last-used device.
- **Hot-swap:** switch input device mid-scene (touch → pad → keyboard) without stuck states; gamepad connect/disconnect mid-battle pauses or recovers cleanly.
- **Touch targets** ≥ 44×44 pt, inside safe areas, not under Home indicator; no accidental Safari gestures (pinch-zoom, double-tap zoom, pull-to-refresh, edge-swipe back, text selection/callout on long-press).
- **Focus/navigation:** pad/keyboard focus always visible, never lost, never trapped.
- **Lifecycle:** backgrounding (Home, app switcher, lock screen, Control Center, incoming notification) then resume in each area: audio resumes, game is paused, no time-based exploit in combo windows.
- **Audio:** first-interaction audio unlock on iOS; mute switch/volume behaviour; no audio after backgrounding.
- **Persistence:** save survives app kill, device restart, and (P1) Safari storage eviction warning; tab vs installed PWA storage are separate on iOS; verify expected behaviour per [SPEC].
- **Text:** no clipping/overflow at all scales; no placeholder strings; no Legend of Dragoon names leaking (flag to Noe).

## 5. Test cases by area
Format: ID · case · expected. Priority P0/P1/P2.

### 5.0 Boot, title, PWA
- BOOT-01 P0 · First load in Safari over network · title screen within [SPEC] s, no console errors.
- BOOT-02 P0 · Add to Home Screen, launch · standalone (no Safari chrome), correct icon/name/splash, landscape locked.
- BOOT-03 P0 · Airplane mode, launch installed PWA · loads fully from service worker cache.
- BOOT-04 P1 · Deploy new build, relaunch · update applied per [SPEC] update flow; no mixed old/new assets.
- BOOT-05 P0 · New Game / Continue with and without a save · Continue disabled or hidden with no save.
- BOOT-06 P1 · Portrait launch · rotate prompt or valid layout.

### 5.1 World map
- MAP-01 P0 · Move with touch (tap-to-move / virtual stick per [SPEC]), pad left stick + d-pad, keyboard WASD + arrows · smooth, 8-dir or per spec, consistent speed.
- MAP-02 P0 · Enter forest path node and town node by each input · correct scene, correct spawn point.
- MAP-03 P1 · Collision at map edges/obstacles · cannot leave bounds or clip.
- MAP-04 P1 · Open menu/pause from map with each input · opens, closes, no movement bleed-through.
- MAP-05 P2 · Rapid repeated scene enter/exit (20×) · no memory growth or audio stacking (report to Sam).

### 5.2 Forest path
- FOR-01 P0 · Traverse start to end with each input · reachable, no soft-lock.
- FOR-02 P0 · Encounter trigger (random or visible per [SPEC]) · battle starts with transition; return to same position after.
- FOR-03 P1 · Encounter rate within [SPEC] over 50 steps-equivalent samples.
- FOR-04 P1 · Interactables (chests, signs) · one-time items stay collected after save/load.
- FOR-05 P1 · Exit back to world map · correct node, state preserved.

### 5.3 Battle: core
- BAT-01 P0 · Turn order and command menu (Attack, Guard, Item, Transform, Flee per [SPEC]) with each input.
- BAT-02 P0 · Target select by touch tap, pad, keyboard · correct target hit; dead targets not selectable.
- BAT-03 P0 · Victory → rewards screen (XP, gold, drops) → return to field; values match [SPEC].
- BAT-04 P0 · Defeat → game over flow per [SPEC]; Continue loads last save.
- BAT-05 P1 · Guard behaviour (damage reduction, HP/Ink regen per [SPEC]).
- BAT-06 P1 · Item use in battle consumes inventory; shared with field inventory.
- BAT-07 P1 · Flee success/failure rules; cannot flee forced fights.
- BAT-08 P1 · Background/resume mid-turn and mid-animation · no skipped turn, no double action.

### 5.4 Battle: timed combos (highest-risk area)
Timing windows are input- and latency-sensitive; test on real iPad only.
- CMB-01 P0 · Hit every prompt in window with touch, pad (A/✕ or mapped), keyboard (Space/Enter or mapped) · full combo completes, damage per [SPEC].
- CMB-02 P0 · Press early / late / miss at each hit index · combo ends at that hit; partial damage per [SPEC].
- CMB-03 P0 · Window size matches [SPEC] ms ±1 frame at 60 Hz and on 120 Hz ProMotion iPads (window must be time-based, not frame-count-based).
- CMB-04 P0 · Mashing / holding the button · does not auto-succeed (anti-mash rule per [SPEC]).
- CMB-05 P1 · Simultaneous inputs from two devices · counted once.
- CMB-06 P1 · Visual, audio and haptic(if any) cue alignment with the true window; measure via slow-mo capture (240 fps) on device.
- CMB-07 P1 · Frame drops during combo (force with heavy FX) · judging still time-correct.
- CMB-08 P1 · Bluetooth controller latency: success rate for a skilled tester ≥ [SPEC]% vs touch baseline; flag if a calibration/offset setting is needed.
- CMB-09 P1 · Pause/background during a combo window · combo safely aborted or paused, no free success.
- CMB-10 P2 · Combo unlock/learning progression per [SPEC].

### 5.5 Battle: transformation
- TRN-01 P0 · Transform unavailable until meter/Ink full per [SPEC]; option greyed with reason.
- TRN-02 P0 · Transform with each input · animation plays, stats/moveset change per [SPEC].
- TRN-03 P0 · Transformation duration/turn count and revert · reverts at correct time; stats restored exactly.
- TRN-04 P1 · Transformed-state special attack (incl. its own timing mechanic if any) · per [SPEC].
- TRN-05 P1 · Battle ends while transformed · character reverts, meter state persisted per [SPEC].
- TRN-06 P1 · KO while transformed; status effects across transform/revert.
- TRN-07 P2 · Skip/shorten transformation animation on repeat (if spec'd).

### 5.6 Town
- TWN-01 P0 · Enter from world map; all buildings/exits reachable with each input.
- TWN-02 P1 · NPC pathing does not block doors or the player permanently.
- TWN-03 P1 · Inn/save point per [SPEC] restores HP/Ink and saves.
- TWN-04 P1 · Exit returns to correct world map node.

### 5.7 Dialogue
- DLG-01 P0 · Start conversation by tap on NPC, pad confirm, keyboard confirm when adjacent.
- DLG-02 P0 · Advance text; first press completes typewriter line, second advances; no skipped lines on fast press.
- DLG-03 P0 · Choices navigable and selectable by all inputs; outcome flags persist after save/load.
- DLG-04 P1 · Input during dialogue does not move the player or open menus behind it.
- DLG-05 P1 · Long names/lines fit; portrait/name plate correct speaker.
- DLG-06 P2 · Text speed / auto / skip options per [SPEC].

### 5.8 Shop
- SHP-01 P0 · Buy item: gold deducted exactly, item added, quantity selector works with each input.
- SHP-02 P0 · Insufficient gold · purchase blocked with message, no state change.
- SHP-03 P0 · Sell item: gold added per [SPEC] sell ratio; key items not sellable.
- SHP-04 P1 · Inventory cap / stack cap reached · purchase blocked or limited correctly.
- SHP-05 P1 · Rapid double-tap Buy · single transaction only.
- SHP-06 P1 · Equip-from-shop comparison stats correct; equipping updates battle stats.
- SHP-07 P1 · App killed mid-transaction then relaunch · no item dupe or gold loss (overlap with John).

### 5.9 Save / load / settings
- SAV-01 P0 · Save in each allowed location, reload · position, party, inventory, gold, flags, transformation meter all restored.
- SAV-02 P1 · Corrupt/old-version save · handled gracefully, no crash (overlap with John).
- SET-01 P1 · Volume, text speed, input remap (if spec'd) persist across relaunch.

## 6. End-to-end loop scripts (run per input method × P0 device)
**E2E-1 Golden path:** New Game → world map → forest path → win ≥1 battle using a full combo and a transformation → town → talk to required NPC (all dialogue choices once) → buy, sell, equip → save → kill app → relaunch PWA offline → Continue → verify state.
**E2E-2 Failure path:** lose a battle → game over → continue → flee a battle → insufficient-gold purchase.
**E2E-3 Input hot-swap:** run E2E-1 switching input method at each scene boundary and once mid-combo.

## 7. Exploratory charters (time-boxed 45 min each)
1. Break the combo judge (latency, pause, multi-device, 120 Hz).
2. Soft-lock hunt: interrupt every transition (scene, battle start/end, dialogue open/close) with backgrounding, rotation, controller disconnect.
3. Safari gesture leakage: try every iOS gesture in every scene.
4. Economy: try to duplicate gold/items via shop + save/load timing.

## 8. Tooling & evidence
- Safari Web Inspector (Mac tethered) for console errors and storage inspection.
- 240 fps slow-motion capture for combo timing verification.
- Bug reports: build hash, device/iPadOS, PWA vs tab, input device, video.
- Debug overlay & seeded RNG requested (see Recommendations).

## 9. Coverage split with Richard (Test Writer) — proposed, pending agreement
| Layer | Owner | Notes |
|---|---|---|
| Rust unit tests: combo judging (time windows, early/late, anti-mash), damage, transformation meter/duration, shop math, inventory caps, save serialize/deserialize | Richard | Native `cargo test`, no browser |
| wasm-bindgen / headless browser integration (`wasm-pack test --headless`) for JS↔WASM boundary, save storage | Richard | |
| Automated E2E smoke (Playwright WebKit) for scene flow with keyboard input | Richard, June reviews | Catches regressions in CI (Brandon) |
| Real-device manual: touch, gamepad, PWA install/offline, lifecycle, gestures, timing feel, 120 Hz | June | Not automatable reliably |
| Exploratory charters | June | |

## 10. Open questions for SPEC / dev
1. Combo window sizes (ms) and anti-mash rule? Time-based or frame-based?
2. Transformation: meter source, duration, revert, persists between battles?
3. Encounter model: random or visible?
4. Save model: manual save points, autosave, or both? Storage backend (localStorage/IndexedDB/OPFS)?
5. Touch scheme for movement (tap-to-move vs virtual stick)?
6. Portrait handling: rotate prompt or responsive?
7. Supported gamepads and default bindings; remapping in scope?
8. Update flow for the installed PWA.
