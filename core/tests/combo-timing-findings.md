# Brushstroke gap timing findings (iPad touch)

Owner: Richard (Test Writer) · For: Jake (Character Systems) · Date: 2026-11-15 (America/Chicago)  
Data: `/workspace/inkborne/team/systems/jake/party.json`  
Core: `/workspace/inkborne/core` (`judge_delta`, `CLEAN_MS`, `GOOD_MS`)  
Tests: `/workspace/inkborne/core/tests/brushstroke_timing.rs`

## Validator

Ran `python3 tools/validate.py` from `/workspace/inkborne/team/systems/jake`.

```
  itsuki  Falling Pine         good chain +19 (6 turns)  perfect +35 (3 turns)  [attack-only, no damage taken]
  benika  Three Prayer Slips   good chain +19 (6 turns)  perfect +35 (3 turns)  [attack-only, no damage taken]
  gonzo   Temple Bell          good chain +14 (8 turns)  perfect +26 (4 turns)  [attack-only, no damage taken]
OK: party.json, transformation.json, elements.json are consistent
```

Exit code 0.

## How the core judges a press (not invented)

From `core/src/lib.rs`: `delta_ms = press time - ring-close time`.

| Result | Grade | Rule |
|---|---|---|
| Clean Line | 2 | `abs(delta_ms) <= 70` (`CLEAN_MS`) |
| good | 1 | `70 < abs(delta_ms) <= 150` (`GOOD_MS`) |
| miss (chain breaks) | 0 | `abs(delta_ms) > 150` |

Windows are **absolute milliseconds**, not a fraction of `gap_ms`. The core has no separate early/late grade: a press 190 ms early and a press 190 ms late are both misses. `gap_ms` only sets how long the ring takes to close (SPEC §7: first hit is from the start; later hits follow the previous close).

`Game::stroke` already stops the chain at the first grade 0 (June CMB-02).

## QA notes the tests follow

- June (`team/qa/test-plan.md`): CMB-01/02/03 — early/good/clean/late presses, time-based windows (not frame counts), ±1 frame tolerance at 60 Hz and 120 Hz. Rust unit tests of combo judging are Richard's layer; real-device feel stays with June.
- Sam (`team/qa/perf-errors-review.md`): one rAF loop with **fixed-timestep** sim + interpolated render; combos must read `event.timeStamp` / `performance.now()`, not frame counts, so a dropped frame does not break a window. No `unwrap` on runtime data. Target is a steady 60 fps (16.6 ms budget) on iPad Safari.
- SPEC §4 already specifies `input.pressedAt` using `performance.now()`, so the **press timestamp should not be quantized**. The visual ring will still update on animation frames, so players can be off by up to one frame of what they see. The JS game loop is not in the tree yet (`src/scenes` is empty), so fixed-timestep quantization is treated as a **planned** 60 Hz risk, not a measured one.

## Error budget used for “effective” window width

These are typical published / commonly measured ranges (also the bands Jake asked me to use), not device captures from this pass.

| Term | Value used | Why |
|---|---|---|
| Touch-to-event latency | 30–60 ms (use **15 ms residual** after compensating the mean) | Typical iPad finger-touch path to a JS event. A skilled player can lead a stable mean; the 30 ms spread is what they cannot cancel. |
| Display / frame time | **16.67 ms** (1 frame at 60 Hz) | Sam's iPad Safari target. 120 Hz ProMotion would be 8.33 ms; we use the worse of the two. Covers visual ring quantization and one frame of display lag. Not double-counted as a second 16.67 ms term. |
| Human rhythmic-tap jitter | **±40 ms** typical (band ±30–50 ms) | Anticipated taps, not simple reaction time. |
| **Reserved, one side** | **71.67 ms** | 15 + 16.67 + 40 |
| Clean too tight if | effective clean width **< 25 ms** (~1.5 frames at 60 Hz) | Below one-and-a-half frames the window is smaller than visual quantization plus a little slack. |
| Good cannot absorb jitter if | effective good half-width **< 50 ms** (worst-end jitter) | |
| Gap too short to re-tap if | `gap_ms` **≤ 340 ms**, or the dead zone between adjacent good windows (`gap_ms - 300`) is **< typical jitter (40–50 ms)** | 340 ms is the floor Jake asked me to consider. A 300 ms good-success window (`±150`) leaves only `gap - 300` ms between a late good on hit *n* and an early good on hit *n+1*. |

Effective widths are the same for every hit, because the core does not scale windows with `gap_ms`:

- Clean total width: 140 ms → 140 − 2×71.67 = **0 ms effective** (below the 25 ms floor).
- Good success window: 300 ms → 300 − 2×71.67 = **156.67 ms effective** (half-width 78.33 ms). This **can** absorb ±40–50 ms jitter.

**Global finding (core windows, not `gap_ms`):** Clean Line is not reliably hittable on iPad touch with `CLEAN_MS = 70`. That is a Rusty constant. A half-width of about 90–100 ms (`CLEAN_MS` in that range) would leave ~20–30 ms after this budget, just above 1.5 frames. Good at 150 ms is acceptable for iPad if mean latency can be led. I am not asking Jake to change every gap to “fix” Clean; widening the window has to happen in the core (or a touch-side latency offset).

## Per-hit table

`dead_ms` = `gap_ms - 2×GOOD_MS` = `gap_ms - 300`. Effective clean/good columns repeat the global figures so the table is complete.

| Member | Stroke | Hit | gap_ms | Clean width (eff.) | Good width (eff.) | dead_ms | Verdict | Suggested gap_ms |
|---|---|---:|---:|---:|---:|---:|---|---:|
| Itsuki | Falling Pine | 0 | 700 | 140 (0) | 300 (157) | 400 | OK | 700 |
| Itsuki | Falling Pine | 1 | 520 | 140 (0) | 300 (157) | 220 | OK | 520 |
| Itsuki | Falling Pine | 2 | 460 | 140 (0) | 300 (157) | 160 | OK | 460 |
| Itsuki | Wet Edge | 0 | 650 | 140 (0) | 300 (157) | 350 | OK | 650 |
| Itsuki | Wet Edge | 1 | 450 | 140 (0) | 300 (157) | 150 | OK | 450 |
| Itsuki | Wet Edge | 2 | 380 | 140 (0) | 300 (157) | 80 | **MARGINAL** | **420** |
| Itsuki | Wet Edge | 3 | 340 | 140 (0) | 300 (157) | 40 | **FLAG** | **420** |
| Benika | Three Prayer Slips | 0 | 760 | 140 (0) | 300 (157) | 460 | OK | 760 |
| Benika | Three Prayer Slips | 1 | 560 | 140 (0) | 300 (157) | 260 | OK | 560 |
| Benika | Three Prayer Slips | 2 | 520 | 140 (0) | 300 (157) | 220 | OK | 520 |
| Benika | Lantern Volley | 0 | 700 | 140 (0) | 300 (157) | 400 | OK | 700 |
| Benika | Lantern Volley | 1 | 500 | 140 (0) | 300 (157) | 200 | OK | 500 |
| Benika | Lantern Volley | 2 | 440 | 140 (0) | 300 (157) | 140 | OK | 440 |
| Benika | Lantern Volley | 3 | 400 | 140 (0) | 300 (157) | 100 | **MARGINAL** | **420** |
| Gonzō | Temple Bell | 0 | 820 | 140 (0) | 300 (157) | 520 | OK | 820 |
| Gonzō | Temple Bell | 1 | 640 | 140 (0) | 300 (157) | 340 | OK | 640 |
| Gonzō | Mountain Gong | 0 | 800 | 140 (0) | 300 (157) | 500 | OK | 800 |
| Gonzō | Mountain Gong | 1 | 600 | 140 (0) | 300 (157) | 300 | OK | 600 |
| Gonzō | Mountain Gong | 2 | 560 | 140 (0) | 300 (157) | 260 | OK | 560 |

## Flagged / marginal gaps (action for Jake)

1. **FLAG — Itsuki / Wet Edge / hit 3: 340 → 420 ms.** At the 340 ms re-tap floor. Dead zone between good windows is only 40 ms, equal to typical jitter, so a slightly late good on hit 2 can feel like it collides with hit 3. A 340 ms ring is ~20 frames at 60 Hz, short to track on a capacitive touchscreen after lifting from the previous tap.
2. **MARGINAL — Itsuki / Wet Edge / hit 2: 380 → 420 ms.** 40 ms above the floor and an 80 ms dead zone (acceptable vs jitter), but it is the penultimate hit of a tightening 4-hit finale that already ends at 340. Bumping both last hits to 420 keeps the accelerando (650, 450, 420, 420) without sitting on the floor.
3. **MARGINAL — Benika / Lantern Volley / hit 3: 400 → 420 ms.** 60 ms above the floor, 100 ms dead zone. Optional, for a consistent ~420 ms minimum on finishing hits of 4-hit chains.

420 ms is already used in the data set (and in the shipped `data/party.json` as a mid-chain gap). It leaves a 120 ms dead zone and ~25 frames of ring preview, still clearly faster than the 520–700 ms opener hits.

Gonzō's slower 2- and 3-hit chains (560–820 ms) are comfortable. Opening hits (650–820 ms) are all fine.

## Test results

`cargo test --test brushstroke_timing` in `/workspace/inkborne/core`: **5 passed, 0 failed.**

- `windows_are_the_documented_absolute_ms`
- `judge_boundaries_match_core_constants`
- `every_jake_hit_judges_early_good_clean_late` — 19 hits × 4 classes (early miss −190 ms, good +110 ms, clean 0 ms, late miss +190 ms), plus the early-side good
- `game_judge_matches_judge_delta` — `Game::judge` / `windows_json` match the free function
- `miss_breaks_chain_at_that_hit` — a mid-chain miss stops later hits (June CMB-02)

Existing `cargo test --lib`: 5 passed (elements, shop, timing, full_battle, guard_heals).

## Assumptions (labelled)

1. Early / late in these tests means **outside the good window** (grade 0), matching June CMB-02 (“press early / late / miss … combo ends”). “Good” uses the midpoint of the good-only band (±110 ms). “Clean” uses a perfect 0 ms press. Offsets are derived from `CLEAN_MS` / `GOOD_MS`.
2. Successive rings are sequential: hit *n+1* starts at hit *n*'s close time (SPEC wording). Not confirmed in a renderer yet; there is no battle scene JS.
3. Mean touch latency is compensable by leading the ring; only the residual spread is subtracted. If we instead treat the full 45 ms mean as uncompensated, Clean is even more unreachable and the late side of Good shrinks to ~48 ms — still barely usable, Clean still not.
4. Fixed-timestep quantization is modeled as one 60 Hz frame on the **visual** cue. Judging itself is assumed timestamp-based per SPEC/Sam, once the loop exists.
5. No real iPad capture was run (June B3 still holds). Thresholds should be re-checked on device with 240 fps capture (June §8).
6. Suggested 420 ms values keep Wet Edge and Lantern Volley as the fast 4-hit chains; I did not retune damage `mult` or finish multipliers.
