#!/usr/bin/env bash
# Fail if APP_VERSION (JS entry) and the semver inside sw.js VERSION are out of step.
# Used by CI against the deployable tree (usually Brandon's dist/ artifact).
#
# Asura / SPEC convention:
#   const APP_VERSION = 'X.Y.Z';
#   const VERSION = '<prefix>-X.Y.Z';          # e.g. asura-3.6.0, ib-0.1.0
#   const VERSION = '<prefix>-X.Y.Z+<suffix>'; # optional build-hash suffix
# The two are in sync when the X.Y.Z cores match. A prefix (asura-, ib-) and an
# optional +build suffix on VERSION are allowed so a per-build cache name can
# coexist with the release version.
#
# Usage: check-version-sync.sh [app_js] [sw_js]
# Paths default to the variables below, or APP_JS / SW_JS in the environment.

set -euo pipefail

# --- configurable paths (defaults match SPEC.md: src/main.js, sw.js) ---
APP_JS="${1:-${APP_JS:-src/main.js}}"
SW_JS="${2:-${SW_JS:-sw.js}}"

die() { printf 'check-version-sync: %s\n' "$*" >&2; exit 1; }

extract_const() {
  # $1=file $2=CONST_NAME -> raw quoted value of the first `const NAME = '...'`
  local file="$1" name="$2" line=""
  [[ -f "$file" ]] || die "missing file: $file"
  line="$(grep -E -m1 "^[[:space:]]*(export[[:space:]]+)?const ${name} = '" "$file" || true)"
  [[ -n "$line" ]] || die "no 'const ${name} = '...' assignment in $file"
  if [[ "$line" =~ const[[:space:]]${name}[[:space:]]=[[:space:]]\'([^\']+)\' ]]; then
    printf '%s\n' "${BASH_REMATCH[1]}"
  else
    die "could not parse const ${name} in $file (line: $line)"
  fi
}

semver_core() {
  # Strip any prefix and optional +build / -prerelease suffix; return X.Y.Z.
  local raw="$1"
  if [[ "$raw" =~ ([0-9]+\.[0-9]+\.[0-9]+) ]]; then
    printf '%s\n' "${BASH_REMATCH[1]}"
  else
    die "no X.Y.Z semver in value: $raw"
  fi
}

app_raw="$(extract_const "$APP_JS" APP_VERSION)"
sw_raw="$(extract_const "$SW_JS" VERSION)"
app_ver="$(semver_core "$app_raw")"
sw_ver="$(semver_core "$sw_raw")"

if [[ "$app_ver" != "$sw_ver" ]]; then
  die "version mismatch: APP_VERSION=$app_raw ($app_ver) in $APP_JS != VERSION=$sw_raw ($sw_ver) in $SW_JS
Bump them together with tools/bump-version.sh <X.Y.Z>."
fi

printf 'check-version-sync: ok %s (APP_VERSION=%s, VERSION=%s)\n' \
  "$app_ver" "$app_raw" "$sw_raw"
