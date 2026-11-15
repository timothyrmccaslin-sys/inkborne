# Inkborne — deploy checklist

Live: https://timothyrmccaslin-sys.github.io/inkborne/  
PWA subpath: `/inkborne/`. Use **relative** `start_url` / `scope` in `manifest.json` and relative paths in the `sw.js` precache list so the installable PWA works under that subpath.

Templates to copy to the repo root when the GitHub repo is created: `templates/.github/workflows/deploy.yml`, `templates/tools/*.sh`, `templates/.gitignore`.

## One-time setup

1. Create the **public** repo `timothyrmccaslin-sys/inkborne` (owner go-ahead required; do not create it until then).
2. Enable **GitHub Pages** with source = **GitHub Actions** (not “Deploy from a branch”).
3. Branch protection on `main` is optional.
4. Drop in Brandon’s `CI` workflow and these deploy templates. Contract: his workflow is named `CI`, and it uploads a `dist` artifact (the tested site root). Deploy is a separate workflow that starts on `workflow_run` after `CI` succeeds on `main` — it downloads that exact artifact (build once, deploy what was tested). See the header comment in `templates/.github/workflows/deploy.yml`.
5. **No secrets in the repo, ever.** GITHUB_TOKEN is the only token the workflows use.

## Per-release

1. Bump `APP_VERSION` (`src/main.js`) and `sw.js` `VERSION` together: `tools/bump-version.sh X.Y.Z`. They must stay in step (Asura rule). `VERSION` is `ib-X.Y.Z` per SPEC, plus an optional `+build` suffix (see below).
2. Build and run checks (Brandon’s CI: lint, test, build, PWA).
3. Tag `vX.Y.Z` and push `main` + the tag.
4. Confirm the live URL loads, the service worker updates (“new version” refresh), offline play works, and the install prompt works.
5. CI also curls the live URL, checks `sw.js` is reachable, and checks the `.wasm` is served as `application/wasm` (GitHub Pages does this correctly).

## Rollback

Revert the bad commit on `main`, **bump the version again** to a new `X.Y.Z` (clients will not refresh if the cache name is reused), retag `vX.Y.Z`, and push so CI rebuilds and deploy ships a new cache name.

## Rules

- Never put secrets, tokens, keys, or emails in the repo.
- **Never touch** the `asura-idle`, `odmit`, or personal-site / `timothymccaslin-site` repos.
- GitHub Pages **cannot set custom cache headers** (`index.html` / `sw.js` no-cache, hashed assets immutable). Staleness is handled by **versioned service-worker cache names**, not headers.
- Brandon’s build-hash cache name **coexists** with the team rule to bump `APP_VERSION` and `sw.js` `VERSION` together. `APP_VERSION` stays `X.Y.Z`. `VERSION` may be the semver plus an optional build suffix, e.g. `ib-1.2.3` or `ib-1.2.3+<sha>`. `tools/check-version-sync.sh` compares the `X.Y.Z` cores.
- Live deploys ship Brandon’s `dist/` artifact, not a second local build.
