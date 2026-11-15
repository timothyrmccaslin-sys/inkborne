# Inkborne: Save Tamper Checks (owner: John, AntiCheat)

- **Build tested:** live Pages demo [https://timothyrmccaslin-sys.github.io/inkborne/](https://timothyrmccaslin-sys.github.io/inkborne/) — **ib-0.1.0**, commit **63923da**.
- **When:** Sunday, Nov 15, 2026, 3:48 PM America/Chicago (CST).
- **Method:** headless Chromium via Playwright. Each case loaded the live page, wrote or replaced `localStorage` key `inkborne-save-v1`, reloaded, used Begin/Continue, then probed `party_json` / `start_battle` / `inventory_json` and walked world → POI / battle / shop where it was reachable. A mid-game fixture (`gold: 777`, `node: "hanshi"`, `flags.won_ambush`, custom inv) was used to confirm overwrite vs. silent repair.
- **Local tree:** `/workspace/inkborne` HEAD is `afdfcc9` (PROGRESS only) plus later uncommitted edits that now diverge from 63923da (`core/src/lib.rs`, `src/`, `pkg/`, data). This report cites **63923da** (the build that was actually tested), not the dirty tree.
- **Scope:** light touch. Goal is that an edited or corrupted save never crashes the game or soft-locks progression — not cheat-proofing.

Save schema (core `Save` in `core/src/lib.rs:54`):

```json
{"gold":120,"inv":{"inkstone_chip":1,"paper_cracker":1,"rice_cake":3},"hp":{"benika":177.0,"gonzo":288.0,"itsuki":214.0},"ink":{"benika":30.0,"gonzo":20.0,"itsuki":85.0},"flags":{},"node":"woods_edge"}
```

Fields: `gold`/`inv` counts are `u32`; `hp`/`ink` values are `f64`; `flags` is `string → bool`; `node` is a string. Party stats (`lv`, `atk`, `def`, `spd`, …) and POI walker position are **not** saved. A real New Game write matches the object above.

JS `readSave()` (`src/main.js:31`) only checks that the value is JSON and that `gold` is a number and `hp` / `inv` are objects. That is a weaker gate than Rust `load_json` (`core/src/lib.rs:103`), which requires every `Save` field and rejects out-of-range `u32`s.

---

## Blockers

Two P0s. Both are reproducible on the live build.

1. **ST-1 (P0) — incomplete `hp` / `ink` maps abort WASM when the player opens a shop or starts a battle.** World map still runs after Continue; the crash is on the next `party_json` or `start_battle`. See below.
2. **ST-2 (P0) — Continue on a JS-valid but Rust-rejected save silently starts a new game and overwrites the slot.** A mid-game file (777 mon, Hanshi, flags, items) with `gold: -1` or a string HP value offered Continue, then landed at Hakushi Clearing with 120 mon and the default inventory. The bad file is gone; there is no backup and no “save unreadable” message.

No other crash or hard soft-lock turned up in the cases below. Unknown world nodes fall back to `world.start`. POI position cannot be tampered through this key.

---

## Findings by severity

### P0 — crash, blank screen, or save destroyed

#### ST-1. `party_json` / `start_battle` index `hp` and `ink` maps and panic if a party id is missing

- **Repro (exact JSON, then Continue, then enter a shop or start a fight):**

```json
{"gold":777,"inv":{"rice_cake":9,"thunder_jar":2},"hp":{},"ink":{"benika":30,"gonzo":20,"itsuki":85},"flags":{"won_ambush":true},"node":"hanshi"}
```

The same abort happens with `"hp": {"itsuki": 150}` (Benika and Gonzō missing) and with a present `hp` map but `"ink": {}`.

- **Observed:** Continue loads the save (gold 777, node `hanshi` stay). The world map is playable. Opening Kōbō Tsuru calls `party_json` from `shop.js` draw (`src/scenes/shop.js:14,66`). That throws `RuntimeError: unreachable` (and a later `recursive use of an object detected which would lead to unsafe aliasing in rust`). The shop is left half-drawn (item list visible, party-compare panel empty) and the rAF loop dies. Pushing a battle calls `start_battle` from `battle.js` `enter()` and leaves a dark blank canvas with only the touch chrome. `panic = "abort"` in the wasm release profile tears the instance down for the rest of the session.
- **File:line (63923da):** `core/src/lib.rs:125` (`self.st.hp[&m.id]` and `self.st.ink[&m.id]` in `party_json`); `core/src/lib.rs:138,140` (same index in `start_battle`); `src/scenes/shop.js:14,66`; `src/scenes/battle.js:134`.
- **Suggested fix:** Look up with `get` and default (`hp` → member max HP, `ink` → 0, then clamp). Never index these maps. Keep `load_json` itself panic-free, and consider filling missing keys right after deserialize.

#### ST-2. Continue on a Rust-rejected save overwrites the slot with a fresh default

- **Repro (mid-game fixture; `gold` is a JSON number so JS shows Continue, but `u32` deserialize fails):**

```json
{"gold":-1,"inv":{"rice_cake":9,"thunder_jar":2},"hp":{"benika":100,"gonzo":200,"itsuki":150},"ink":{"benika":30,"gonzo":20,"itsuki":85},"flags":{"won_ambush":true},"node":"hanshi"}
```

Same outcome with `gold: 1e300`, `"hp": {"itsuki":"full","benika":100,"gonzo":200}`, `"inv":{"rice_cake":-3,...}`, `"inv":{"rice_cake":1e20,...}`, or a JS-valid object that omits required Rust field `node`.

- **Observed:** Title shows Begin and Continue. Continue calls `game.load()` (`src/scenes/title.js:17`), which returns `false`, and the result is ignored; the game always `go('world')`. Core state is still the boot default from `Game::new` (120 mon, starting items, full HP, empty flags, empty node). `world.js:6` then falls back to `W.start` (`woods_edge`), and `world.enter()` (`src/scenes/world.js:31`) does `set_node(at); game.save()`, which overwrites `inkborne-save-v1`. Confirmed with the mid-game fixture: 777 mon, Hanshi, `won_ambush`, and the custom inventory were all replaced by the New Game blob. No console error.
- **File:line (63923da):** `src/scenes/title.js:17-18`; `src/scenes/world.js:31`; `src/main.js:31-33` (`readSave` vs `load_json`); `core/src/lib.rs:103`.
- **Suggested fix:** If `load()` is false, stay on the title with a short “save unreadable” line and do **not** enter the world (so `world.enter` cannot write). Rotate the bad slot to `inkborne-save-v1.bak` before any new write. Tighten `readSave()` so Continue is hidden unless Rust would accept the file (or call `load_json` in a scratch game and key off that).

---

### P1 — bad state that is recoverable or confusing

#### ST-3. After a successful deserialize, numbers are not clamped

- **Repro:**

```json
{"gold":120,"inv":{"inkstone_chip":1,"paper_cracker":1,"rice_cake":3},"hp":{"itsuki":-10,"benika":-5,"gonzo":-99},"ink":{"benika":30,"gonzo":20,"itsuki":85},"flags":{},"node":"woods_edge"}
```

Also: `"hp": {"itsuki":99999,"benika":99999,"gonzo":99999}` and `"hp": {"itsuki":1e300,...}`.

- **Observed:** Load succeeds, no crash. Shop compare shows `HP -10 → 40` (and the same for the others). `start_battle` uses `.max(1.0)`, so a fight starts at 1 HP and is playable. HP above max or `1e300` is used as current HP in battle (god-mode / broken bars) and is written back on the next save. Ink is not clamped on load either (`ink` is a `f64`).
- **File:line:** `core/src/lib.rs:103` (assign as-is); `core/src/lib.rs:138` (battle-only floor at 1); `src/scenes/shop.js:66-70`.
- **Suggested fix:** After deserialize, clamp each known member’s HP to `[1, max_hp]`, ink to `[0, 100]`, and drop or reset anything else.

#### ST-4. World node and flags are trusted; unknown nodes are silently repaired

- **Repro (locked node, sequence break):**

```json
{"gold":777,"inv":{"rice_cake":9,"thunder_jar":2},"hp":{"benika":100,"gonzo":200,"itsuki":150},"ink":{"benika":30,"gonzo":20,"itsuki":85},"flags":{},"node":"shrine_stair"}
```

Unknown node: `"node": "no_such_node"`. Once-flags: `"flags": {"won_ambush":true,"won_ronin":true,"met_tsuru":true,"totally_fake":true}`.

- **Observed:** `shrine_stair` is a real, locked, no-POI node. Continue spawns the party on Shuin Stair with 777 mon kept. The only neighbor is unlocked Hanshi; `world.js:27` blocks travel only when the *destination* is locked, so this is a sequence break, not a confirmed soft-lock. An unknown node id is accepted by Rust, then `world.js:6` falls back to `W.start` and `enter()` saves `woods_edge` (other fields kept). Unknown flags are safe (`flag()` defaults to false). Setting `won_ambush` / `won_ronin` skips the one-time forest fights (`poi.js` `once` + `needs`).
- **File:line:** `src/scenes/world.js:6,27,31`; `core/src/lib.rs:103,106-108`; `data/pois/forest.json` triggers (`once`, `flag`, `needs`).
- **Suggested fix:** If `node` is missing or unknown, or if it is marked `locked` in `world.json`, reset to `world.start` (or the last unlocked town). Do not need to scrub unknown flags for a demo; optional: ignore flags not in a known list.

---

### P2 — cosmetic / hardening

#### ST-5. `save_json` still `unwrap`s the serializer

- **Repro:** not hit. `Save` is only `u32` / `f64` / `String` / maps of those, so `serde_json::to_string` should not fail in practice.
- **Observed:** n/a. A panic here would abort wasm; `game.save()`’s JS `try/catch` would not catch it.
- **File:line:** `core/src/lib.rs:102`.
- **Suggested fix:** Return `Result<String, JsValue>` or a fallback `"{}"` plus a log.

#### ST-6. Turn-order `partial_cmp` `unwrap` is not reachable from this save key

- **Repro:** not applicable via `inkborne-save-v1`. `spd` / `atk` / `lv` live on `Member` from `party.json`, not in `Save`. Battle copies `m.spd` in `start_battle` (`lib.rs:139-140`). A NaN speed would still panic `partial_cmp` at `lib.rs:156` if data were bad, but a tampered *save* cannot inject it.
- **Suggested fix:** still worth `f64::total_cmp` or `unwrap_or(Ordering::Equal)` as hardening. The old enemy-def `.unwrap()` at the AI path is already a `match` in 63923da (`lib.rs:295`) and was not reproducible.

#### ST-7. Unknown inventory ids are kept but hidden; huge `u32` counts and gold are accepted

- **Repro:** `"inv": {..., "phantom_scroll": 7}` — shop and `inventory_json` only walk `items.json`, so the phantom id never appears; it is still in the next `save_json`. `"gold": 4294967295` and `"inv": {"rice_cake": 4294967295}` load and render (shop opened, no crash). `commit` / `buy` use wrapping `u32` add in release (`lib.rs:116,186`); overflow was not exercised.
- **Suggested fix:** Drop unknown item ids on load; cap gold and counts to a demo-sane maximum.

#### ST-8. No `version` field and no checksum

- **Observed:** the blob is a bare `Save`. There is nothing to migrate or to treat as accidental corruption (as opposed to cheating). Out of scope to cheat-proof a local slot.
- **Suggested fix:** optional `{ version, data, crc }` envelope. A bad CRC is corruption: offer the backup or a new game, do not treat it as cheating. Cap payload size before parse (4 MB already fits in this Chrome’s localStorage; 5 MB `setItem` throws `QuotaExceededError` and is treated as “no save”).

#### ST-9. JS-invalid garbage hides Continue, and New Game still overwrites the key with no backup

- **Repro:** key missing, `garbage`, `""`, `{}`, or truncated JSON. `readSave()` returns null, Continue is hidden, Begin starts a normal game. `world.enter()` then writes a fresh save over the garbage. No crash.
- **Suggested fix:** same backup rotation as ST-2. For a missing key this is expected.

---

## Recommendations (light)

1. **Validate and clamp after deserialize** in `load_json` (or a `validate(&mut Save)` used only there): fill missing party `hp`/`ink` keys, clamp HP and ink, cap gold and counts, drop unknown item ids, reset an unknown or locked `node` to `world.start`. Reject only what cannot be repaired.
2. **No panics on the load or battle/shop paths.** Replace every `map[id]` / `unwrap` on save-derived data with `get` + a default. `save_json` should not `unwrap` either (ST-5).
3. **Honor `load()` in the title** and keep a backup: if load fails, tell the player and leave the slot alone; before any new write, copy `inkborne-save-v1` → `inkborne-save-v1.bak`.
4. **Add a `version` field** and migrate or refuse cleanly.
5. **Optional CRC** over the serialized data, treated as corruption, not cheating. Reject over-size payloads before parse.
6. Do not bother making a browser localStorage save tamper-proof.

---

## Cases tested

PASS = no crash / blank screen / soft-lock (the game stayed playable). P0/P1 notes still apply. “Overwrite” means the slot was replaced with the New Game default (progress lost). “Repaired” means the rest of the save was kept.

| # | Case | Payload (head) | Continue? | Result |
|---|---|---|---|---|
| C01 | Missing key | *(no key)* | no | PASS — New Game, world / forest POI ok |
| C02 | Garbage | `garbage` | no | PASS — treated as no save; New Game overwrites key (ST-9) |
| C03 | Empty string | `""` | no | PASS — same as C02 |
| C04 | Empty object | `{}` | no | PASS — same as C02 |
| C05 | Truncated JSON | real save cut in half | no | PASS — same as C02 |
| C06 | `gold: -1` | see ST-2 (also mid-game fixture F1) | **yes** | PASS for crash; **P0 ST-2** — load false, slot overwritten (777 mon / Hanshi / flags lost) |
| C07 | `gold: 1e300` | `u32` overflow | **yes** | same as C06 (ST-2) |
| C08 | Party HP negative | `"hp":{"itsuki":-10,"benika":-5,"gonzo":-99}` | yes | PASS — shop shows negative HP; battle starts at 1 HP (ST-3) |
| C09 | HP is a string | `"itsuki":"full"` | **yes** | **P0 ST-2** — serde fails, slot overwritten |
| C10 | HP above max | `"hp":{…:99999}` | yes | PASS — battle uses 99999 (ST-3) |
| C11 | `hp: {}` | missing all member keys | yes | **FAIL P0 ST-1** — `party_json` / `start_battle` abort; shop frozen, battle blank |
| C12 | Unknown item id | `"phantom_scroll":7` | yes | PASS — hidden in shop, kept in save (ST-7) |
| C13 | Inv count `-3` | `u32` reject | **yes** | **P0 ST-2** |
| C14 | Inv count `1e20` | `u32` reject | **yes** | **P0 ST-2** |
| C15 | Unknown node | `"node":"no_such_node"` | yes | PASS — fallback to `woods_edge`, other fields kept (ST-4) |
| C16 | Locked node | `"node":"shrine_stair"` | yes | PASS — spawn on Shuin Stair, sequence break (ST-4) |
| C17 | Unknown + once flags | `won_ambush`, `totally_fake`, … | yes | PASS — flags trusted; once-battles skipped (ST-4) |
| C18 | ~5 MB payload | valid `Save` + `pad` of 5×1024² `'x'` | no* | PASS — `QuotaExceededError` on `setItem`; treated as no save. 1–4 MB *do* store. Direct `load_json` of a 5 MB string succeeded in ~17 ms, fields kept |
| C19 | `gold: 4294967295` | `u32::MAX` | yes | PASS — shop shows the value (ST-7) |
| C20 | HP `1e300` | f64 accepts | yes | PASS — battle uses `1e300` HP, no `partial_cmp` panic (ST-3, ST-6) |
| C21 | `ink: {}` | missing ink keys | yes | **FAIL P0 ST-1** — same abort as C11 |
| C22 | Missing `node` field | JS-valid, Rust-invalid | **yes** | **P0 ST-2** |
| C23 | Inv count `4294967295` | `u32::MAX` | yes | PASS — shop lists the count (ST-7) |
| C24 | Partial `hp` | `"hp":{"itsuki":214}` | yes | **FAIL P0 ST-1** — same abort as C11 |

Baseline New Game (no tamper) wrote the canonical save above and reached world → forest POI → battle → town shop with no page errors.

### Could not test (and why)

- **POI position outside bounds / inside a solid:** walker `x,y` is not in `Save`. Every POI enter reloads the spawn from the POI JSON (`src/scenes/poi.js:9,23`). N/A for this key.
- **NaN `spd` (or other battle stats) from a save:** those fields are not saved; they come from `party.json`. ST-6 is therefore latent, not save-reachable.
- **`fighters[target]` / leftover enemy `.unwrap()`:** target indexes come from the battle UI, not the save. The enemy-def lookup is already a safe `match` in 63923da.
- **Winning a battle at `u32::MAX` gold, or buying with a `u32::MAX` stack:** not run. Overflow would wrap in this release wasm; worth a clamp (ST-7).
- **iPad Safari / Private Mode / 7-day eviction:** not in this desktop Chromium pass.
- **Checksum mismatch:** no checksum is implemented, so there was nothing to flip.

