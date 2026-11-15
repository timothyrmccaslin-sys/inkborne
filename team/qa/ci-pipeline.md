# Inkborne — Build Pipeline & CI Plan (Brandon, DevOps)

Status: **Draft v0, written before SPEC.md exists.** Will be revised once the spec and first code land. Deploy side owned with Rick (Deployment).

## Blockers

1. **No SPEC.md yet.** Crate layout, frontend tooling (wasm-pack vs. trunk vs. plain wasm-bindgen), and hosting target are unknown. Plan below assumes the most common setup; anything marked *[assume]* gets confirmed against the spec.
2. **Repo has no commits and no remote.** `/workspace/inkborne` is `git init`'d on `main` but empty, with no GitHub remote. CI can't run until there's a remote (GitHub Actions assumed). `gh` on the box is authenticated as `timothyrmccaslin-sys`; need Timothy/Marc to confirm the repo name and visibility before I create one.
3. **No code to build yet.** Nothing to validate until dev lands a Cargo workspace and a web shell (index.html, manifest, service worker).

## Environment check (box, 2026-11-15)

| Tool | Version | Notes |
|---|---|---|
| rustc / cargo | 1.100.0 | stable |
| wasm32-unknown-unknown target | installed | |
| clippy / rustfmt | installed today | were missing |
| wasm-pack | 0.13.1 | |
| node / npx | 24.22.1 | for PWA/Lighthouse tooling |
| wasm-bindgen-cli, wasm-opt (binaryen), trunk | **not installed** | install once tooling is chosen; wasm-bindgen-cli must match the crate's wasm-bindgen version exactly |

## Findings by severity

- **High:** wasm-bindgen CLI/crate version mismatch is the #1 cause of broken WASM builds. Pin `wasm-bindgen` exactly (`=x.y.z`) in Cargo.toml and install the same CLI version in CI.
- **High:** Service worker caching is the #1 cause of "stale build on iPad" bugs. The SW cache name must be versioned per build (hash or commit SHA), or players get stuck on old WASM after deploys.
- **Medium:** iPad Safari PWA has specific requirements (apple-touch-icon, `apple-mobile-web-app-capable` meta, landscape `orientation` in manifest, ~50 MB-ish storage pressure). Validate these in CI, not by hand.
- **Medium:** WASM must be served with `Content-Type: application/wasm` for streaming instantiation — a deploy/hosting check for Rick.
- **Low:** Pin toolchain with `rust-toolchain.toml` so box, CI, and dev machines agree.

## CI plan (GitHub Actions *[assume]*)

Triggers: every PR and push to `main`. Deploy job (Rick) runs only on `main` after all checks pass.

**Job 1 — lint** (fast, fails early)
- `cargo fmt --all -- --check`
- `cargo clippy --workspace --all-targets --target wasm32-unknown-unknown -- -D warnings`
- JS/TS lint if a JS shell exists (`npx eslint`), plus `npx prettier --check` *[assume]*

**Job 2 — test**
- `cargo test --workspace` (native: game logic, combat math, save format — coordinate with Richard so logic lives in a crate that tests without a browser)
- `wasm-pack test --headless --chrome --firefox` for wasm-bindgen/web-sys glue
- WebKit smoke test via Playwright (closest CI proxy for iPad Safari): load page, no console errors, reach title screen — shared with Sam's zero-console-errors target and June's test plan

**Job 3 — build**
- `wasm-pack build --release --target web` (or `trunk build --release`) *[assume]*
- `wasm-opt -Oz` on the output
- **Size budget**: fail if `.wasm` (gzipped) exceeds an agreed limit (proposal: 3 MB, confirm with Sam)
- Upload `dist/` as an artifact; Rick's deploy job consumes this exact artifact (build once, deploy what was tested)

**Job 4 — PWA validation**
- Manifest JSON check: `name`, `short_name`, `start_url`, `scope`, `display: standalone|fullscreen`, `orientation: landscape`, `theme_color`, `background_color`, icons at 192 and 512 (plus maskable)
- iOS checks in index.html: `apple-touch-icon` (180×180), `apple-mobile-web-app-capable`, viewport meta
- Service worker: registers on load, cache name includes build hash, precache list covers the .wasm, JS glue, and assets (script diffs precache list against `dist/`), old caches deleted on `activate`
- Offline test (Playwright): load once, go offline, reload, game still boots
- Lighthouse CI PWA/installability audit (`npx @lhci/cli`) against a local static server

**Caching:** `Swatinem/rust-cache` for cargo; cache wasm-pack/wasm-bindgen binaries.

## Recommendations / next steps

1. Timothy/Marc: confirm GitHub repo name + visibility so I can create the remote and add the workflow.
2. Dev team: pin `wasm-bindgen` exactly and add `rust-toolchain.toml`; keep game logic in a browser-free crate for native tests.
3. Rick: confirm hosting target, `application/wasm` MIME, cache headers (`index.html` and `sw.js` no-cache; hashed assets immutable).
4. Me: once SPEC.md lands, finalize tooling, write `.github/workflows/ci.yml` and the manifest/SW validation script, and install the missing tools on the box.
