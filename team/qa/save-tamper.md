# Tabula Rasa (formerly Inkborne): Save Tamper Checks (owner: John, AntiCheat)

Status: **Provisional (pre-spec).** As of Nov 15, 2026, 2:58 PM CST, there is no `SPEC.md` and no game code in `/workspace/tabula-rasa` (the empty `core/`, `src/`, `data/` folders have no files yet). Everything below is the baseline I'll check against once the save system exists. I'll revise it against the real code and spec when they land.

Scope: light touch. This is a single-player demo, so the goal is "a hand-edited or corrupted save never crashes the game or soft-locks progression," not cheat prevention. A local save can't be made tamper-proof in the browser, and we shouldn't try.

## Blockers

1. **No spec or code to review yet.** I can't confirm where saves live (localStorage vs IndexedDB), the format, or the load path. *Unblocks when:* `SPEC.md` and the save module land.

No other blockers are expected. Everything below is a recommendation for the dev team (Rust/WASM side), not a ship-stopper, except items marked **Must**.

## Findings by severity (expected risks, to verify)

### High
- **Must: load must never panic.** In Rust/WASM, an `unwrap()`/`expect()` on deserialize or an out-of-range index (item ID, map ID, party slot) aborts the whole WASM instance, which reads to the player as a frozen or blank game. Every load error should fall back to "save is unreadable, start new or load backup."
- **Must: unknown or out-of-range IDs.** Edited saves can reference item, enemy, map, quest-flag, or dialogue IDs that don't exist. Lookups must be checked (`get()` returning `Option`), not indexed.
- **Soft-lock from inconsistent flags.** For example: "met the shopkeeper" set but "entered town" not, a position inside a wall or on an unloaded map, or a quest step past a required item the player doesn't have. Check for a safe spawn point on load.

### Medium
- **Numeric ranges.** HP/MP above max, negative gold or item counts, level 0 or 9999, transformation gauge over 100%. These cause UI overflow, divide-by-zero, or integer overflow in debug builds (overflow panics in debug, wraps in release).
- **Version drift.** A save from an older demo build loaded by a newer one. Include a `version` field and either migrate or reject cleanly.
- **Storage edge cases on iPad Safari PWA.** Safari can evict script-writable storage (localStorage/IndexedDB) after about 7 days without use for sites not added to the home screen, and private mode/quota errors can make writes fail. A failed write must not corrupt the existing save.

### Low
- **Casual editing** (bumping gold in devtools). Fine for a demo. A checksum just turns it into "save rejected," which is a worse experience than letting it through, unless we want to detect accidental corruption.

## Recommendations (light)

1. **Version + checksum envelope.** Store `{ version, data, checksum }`, where the checksum is a CRC32 or FNV-1a hash over the serialized `data`. On mismatch, treat it as **corruption**, not cheating: offer the backup slot or a new game. No secret key, since a key shipped in WASM isn't secret anyway.
2. **Validate after deserialize.** One `fn validate(&mut SaveData) -> Result<(), SaveError>` that clamps numbers to legal ranges, drops unknown item IDs, resets an invalid position to the last town or map entrance, and rejects only when something can't be repaired.
3. **Atomic write + one backup.** Write to `save_tmp`, verify it reads back, then rotate `save` into `save_bak` and `save_tmp` into `save`. Load falls back to `save_bak`.
4. **Strict deserialization.** Use serde with `#[serde(default)]` for fields added later, and cap the input size (for example, reject anything over 256 KB) before parsing.
5. **No panics in the load path.** `Result` all the way up to the JS boundary, so an error shows a message instead of crashing.

## Test cases for June / Richard (once code exists)

| # | Tamper | Expected |
|---|---|---|
| 1 | Delete the save key | New-game prompt, no error |
| 2 | Replace with `garbage` / empty string / `{}` | "Save unreadable" + new game, no console panic |
| 3 | Truncate JSON mid-object | Same as 2, backup offered |
| 4 | Flip one char in `data` (checksum mismatch) | Backup loaded or new-game prompt |
| 5 | gold = -1, gold = 2^53, HP > max | Clamped, game runs |
| 6 | Unknown item ID / map ID | Item dropped / reset to a safe spawn |
| 7 | Quest flag out of order | No soft-lock, can still reach town/shop/battle |
| 8 | `version` = 0 and 999 | Migrated or cleanly rejected |
| 9 | Very large payload (10 MB) | Rejected before parse, no hang |
| 10 | Storage write throws (quota/private mode) | Existing save intact, user notified |

## Next step
Re-review against `SPEC.md` and the actual save module when they land, then replace "expected" with confirmed findings.
