#!/usr/bin/env bash
set -euo pipefail

repo_root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
source_dir=${IRIS_SOURCE_DIR:-"$repo_root/.work/iris"}
repository=https://github.com/salvogendut/iris.git
revision=d6420795a00f139cd0f638a623c55a071b46e9e9
toolchain=nightly-2026-10-28

if [[ -n ${IRIS_SOURCE_DIR:-} ]]; then
    source_dir=$(cd -- "$source_dir" && pwd)
    if [[ $(git -C "$source_dir" rev-parse HEAD) != "$revision" ]]; then
        echo "IRIS_SOURCE_DIR must be at the qualified revision $revision" >&2
        exit 1
    fi
else
    if [[ ! -d "$source_dir/.git" ]]; then
        git clone --depth 1 --branch xiri/netbsd-io "$repository" "$source_dir"
    fi
    if [[ $(git -C "$source_dir" rev-parse HEAD) != "$revision" ]]; then
        git -C "$source_dir" fetch "$repository" "$revision"
        git -C "$source_dir" checkout --detach "$revision"
    fi
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
