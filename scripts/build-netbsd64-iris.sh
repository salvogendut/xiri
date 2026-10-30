#!/usr/bin/env bash
set -euo pipefail
repo_root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
source_dir=${XIRI_IRIS64_SOURCE_DIR:-"$repo_root/.work/iris-netbsd64"}
source_dir=$(realpath "$source_dir")
revision=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["emulator_revision"])' "$repo_root/lab/netbsd64/baseline.json")
if [[ $(git -C "$source_dir" rev-parse HEAD) != "$revision" ]] || ! git -C "$source_dir" diff --quiet HEAD; then
    printf 'Use a clean IRIS worktree at %s\n' "$revision" >&2
    exit 2
fi
install -m 0644 "$repo_root/lab/iris/Cargo.lock" "$source_dir/Cargo.lock"
cd "$source_dir"
toolbox run -c xiri-iris env \
    RUSTUP_HOME="$repo_root/.work/rustup" CARGO_HOME="$repo_root/.work/cargo" \
    CARGO_TARGET_DIR="$repo_root/.work/target-netbsd64" CARGO_BUILD_JOBS=8 \
    "$repo_root/.work/cargo/bin/cargo" +nightly-2026-10-28 \
    build --release --locked --bin iris --bin iris-ci
