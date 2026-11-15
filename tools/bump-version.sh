#!/usr/bin/env bash
# Bump APP_VERSION in the JS entry file and VERSION in sw.js together.
#
# Usage: bump-version.sh <X.Y.Z>
#
# Refuses to run if the two files are currently out of sync, or if the new
# version is not strictly greater than the current one.
# Preserves an existing VERSION prefix (asura-, ib-, …). Drops any +build
# suffix; CI can re-append a hash if desired (e.g. ib-1.2.3+<sha>).
# If VERSION has no prefix yet, DEFAULT_PREFIX is used.

set -euo pipefail

# --- configurable paths (override with APP_JS / SW_JS in the environment) ---
APP_JS="${APP_JS:-src/main.js}"
SW_JS="${SW_JS:-sw.js}"
# SPEC.md cache-name prefix: ib-X.Y.Z. Only used when sw.js has no prefix yet.
DEFAULT_PREFIX="${CACHE_PREFIX:-ib}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CHECK_SCRIPT="${CHECK_SCRIPT:-$SCRIPT_DIR/check-version-sync.sh}"

die() { printf 'bump-version: %s\n' "$*" >&2; exit 1; }

usage() {
  printf 'Usage: %s <X.Y.Z>\n' "${0##*/}" >&2
  exit 2
}

[[ "${1:-}" == "-h" || "${1:-}" == "--help" ]] && usage
[[ $# -eq 1 ]] || usage
NEW="$1"
[[ "$NEW" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]] || die "new version must be X.Y.Z (got: $NEW)"

[[ -f "$APP_JS" ]] || die "missing JS entry file: $APP_JS"
[[ -f "$SW_JS" ]] || die "missing service worker: $SW_JS"

extract_const() {
  local file="$1" name="$2" line=""
  line="$(grep -E -m1 "^[[:space:]]*const ${name} = '" "$file" || true)"
  [[ -n "$line" ]] || die "no 'const ${name} = '...' assignment in $file"
  if [[ "$line" =~ const[[:space:]]${name}[[:space:]]=[[:space:]]\'([^\']+)\' ]]; then
    printf '%s\n' "${BASH_REMATCH[1]}"
  else
    die "could not parse const ${name} in $file (line: $line)"
  fi
}

# Refuse if currently out of sync (same rules as CI).
if ! "$CHECK_SCRIPT" "$APP_JS" "$SW_JS"; then
  die "files are out of sync; fix them before bumping"
fi

app_raw="$(extract_const "$APP_JS" APP_VERSION)"
sw_raw="$(extract_const "$SW_JS" VERSION)"

if [[ "$app_raw" =~ ([0-9]+\.[0-9]+\.[0-9]+) ]]; then
  CUR="${BASH_REMATCH[1]}"
else
  die "no X.Y.Z in APP_VERSION=$app_raw"
fi

prefix="$DEFAULT_PREFIX"
if [[ -n "$prefix" && "$prefix" != *- ]]; then
  prefix="${prefix}-"
fi
# Preserve the prefix already in sw.js (asura- / ib- / …).
if [[ "$sw_raw" =~ ^([^0-9]*?)([0-9]+\.[0-9]+\.[0-9]+) ]]; then
  if [[ -n "${BASH_REMATCH[1]}" ]]; then
    prefix="${BASH_REMATCH[1]}"
  fi
fi

semver_gt() {
  # Return 0 if $1 > $2.
  local IFS=.
  # shellcheck disable=SC2086
  set -- $1 $2
  local a="$1" b="$2" c="$3" d="$4" e="$5" f="$6"
  ((10#$a > 10#$d)) && return 0
  ((10#$a < 10#$d)) && return 1
  ((10#$b > 10#$e)) && return 0
  ((10#$b < 10#$e)) && return 1
  ((10#$c > 10#$f)) && return 0
  return 1
}

if ! semver_gt "$NEW" "$CUR"; then
  die "new version $NEW is not greater than current $CUR"
fi

new_sw="${prefix}${NEW}"

# Replace only the first assignment of each const, keep the rest of the line
# (comments, etc.).
tmp_app="$(mktemp)"
tmp_sw="$(mktemp)"
trap 'rm -f "$tmp_app" "$tmp_sw"' EXIT

awk -v new="$NEW" '
  !done && $0 ~ /^[[:space:]]*const APP_VERSION = '\''/ {
    sub(/const APP_VERSION = '\''[0-9]+\.[0-9]+\.[0-9]+'\''/, "const APP_VERSION = '\''" new "'\''")
    done=1
  }
  { print }
' "$APP_JS" > "$tmp_app"

awk -v new="$new_sw" '
  !done && $0 ~ /^[[:space:]]*const VERSION = '\''/ {
    sub(/const VERSION = '\''[^'\'']+'\''/, "const VERSION = '\''" new "'\''")
    done=1
  }
  { print }
' "$SW_JS" > "$tmp_sw"

# Confirm the edit landed before replacing the originals.
grep -q "const APP_VERSION = '$NEW'" "$tmp_app" || die "failed to update APP_VERSION in $APP_JS"
grep -q "const VERSION = '$new_sw'" "$tmp_sw" || die "failed to update VERSION in $SW_JS"

cat "$tmp_app" > "$APP_JS"
cat "$tmp_sw" > "$SW_JS"

"$CHECK_SCRIPT" "$APP_JS" "$SW_JS"
printf 'bump-version: %s -> %s (APP_VERSION=%s, VERSION=%s)\n' \
  "$CUR" "$NEW" "$NEW" "$new_sw"
