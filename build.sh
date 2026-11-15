#!/usr/bin/env bash
# Rebuild the Rust core into ./pkg (committed so GitHub Pages serves it as-is).
set -euo pipefail
cd "$(dirname "$0")/core"
cargo test --release
wasm-pack build --release --target web --out-dir ../pkg --no-typescript
rm -f ../pkg/.gitignore ../pkg/package.json ../pkg/README.md
echo "Remember: bump VERSION in sw.js and APP_VERSION in src/main.js together for each release."
