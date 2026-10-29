#!/usr/bin/env bash
set -euo pipefail

repo_root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
source_dir="$repo_root/.work/iris"
revision=b188bb9a82842948ddf2534f07d718df8473942c
toolchain=nightly-2026-10-28

if [[ ! -d "$source_dir/.git" ]]; then
    git clone --depth 1 https://github.com/techomancer/iris.git "$source_dir"
fi

if [[ $(git -C "$source_dir" rev-parse HEAD) != "$revision" ]]; then
    git -C "$source_dir" fetch --depth 1 origin "$revision"
    git -C "$source_dir" checkout --detach "$revision"
fi

install -m 0644 "$repo_root/lab/iris/Cargo.lock" "$source_dir/Cargo.lock"
cd "$source_dir"

toolbox run -c xiri-iris env \
    RUSTUP_HOME="$repo_root/.work/rustup" \
    CARGO_HOME="$repo_root/.work/cargo" \
    CARGO_TARGET_DIR="$repo_root/.work/target" \
    CARGO_BUILD_JOBS=8 \
    "$repo_root/.work/cargo/bin/cargo" "+$toolchain" \
    build --release --locked --bin iris --bin iris-ci
