#!/usr/bin/env bash
# Rebuild patches from the CURRENT live core/ (read-only) in a scratch copy, then publish them into ../patches.
# Usage: tools/chain.sh                 -> 0007-0009 against live (0001-0006 already landed in live 0.1.1 work tree)
#        STEPS=all tools/chain.sh       -> 0001-0009 against git HEAD 0.1.0 (c4ef...), for the record
# Env: RUSTY_WORK (scratch dir, default /tmp/rusty-ib-work), CARGO_TARGET_DIR (default /tmp/rusty-ib-target)
set -euo pipefail
TOOLS=$(cd "$(dirname "$0")" && pwd); LIVE=$(cd "$TOOLS/../../../.." && pwd); OUT=$TOOLS/../patches
export RUSTY_WORK=${RUSTY_WORK:-/tmp/rusty-ib-work}; W=$RUSTY_WORK
export CARGO_TARGET_DIR=${CARGO_TARGET_DIR:-/tmp/rusty-ib-target}
ALL=("p1:combo-timing" "p2:vermilion-ink-unfurl" "p3:elements" "p4:still-water-guard" "p5,p5b:enemy-ai" "p6:tests" "p7:flee-ambush" "p8:enemy-xp" "p9:balance-jake")
rm -rf "$W" && mkdir -p "$W/core" "$W/team/systems"
cp -r "$LIVE/data" "$W/" && cp -r "$LIVE/team/systems/jake" "$W/team/systems/"
cp -r "$LIVE/core/Cargo.toml" "$LIVE/core/Cargo.lock" "$LIVE/core/src" "$LIVE/core/tests" "$W/core/"
if [ "${STEPS:-live}" = all ]; then (cd "$LIVE" && git show HEAD:core/src/lib.rs) > "$W/core/src/lib.rs"; n=0; steps=("${ALL[@]}")
else n=6; steps=("${ALL[@]:6}"); fi
cd "$W" && git init -q && git add core && git -c user.email=r@x -c user.name=rusty commit -qm base
echo "base core/src/lib.rs sha256: $(sha256sum core/src/lib.rs | cut -d' ' -f1)"
TMP=$(mktemp -d)
for step in "${steps[@]}"; do
  scripts=${step%%:*}; name=${step#*:}; n=$((n+1))
  for s in ${scripts//,/ }; do python3 "$TOOLS/$s.py"; done
  if ! (cd core && cargo build -q 2>"$TMP/build.log"); then cat "$TMP/build.log"; exit 1; fi
  f=$(printf "%04d-%s.patch" $n "$name")
  git add core && git diff --cached core > "$TMP/$f" && git -c user.email=r@x -c user.name=rusty commit -qm "$f"
  echo "built + wrote $f ($(wc -l < "$TMP/$f") lines)"
done
# standalone 0009 (Jake balance) against live alone, for isolated review
S=$W-standalone; rm -rf "$S" && mkdir -p "$S/core" && cp -r "$LIVE/core/Cargo.toml" "$LIVE/core/Cargo.lock" "$LIVE/core/src" "$LIVE/core/tests" "$S/core/"
(cd "$S" && git init -q && git add core && git -c user.email=r@x -c user.name=rusty commit -qm base && RUSTY_WORK="$S" python3 "$TOOLS/p9.py" && (cd core && cargo build -q) && git add core && git diff --cached core > "$TMP/0009-balance-jake.standalone.patch")
echo "built + wrote 0009-balance-jake.standalone.patch"
mkdir -p "$OUT"; rm -f "$OUT"/0*.patch; cp "$TMP"/0*.patch "$OUT"/; rm -rf "$TMP"   # publish only after every step built
