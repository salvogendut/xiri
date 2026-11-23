#!/bin/sh
# Copy next to iris.toml, nvram.bin, flash.bin and netbsd-xiri.chd.
set -eu
ulimit -c 0
cd "$(dirname "$0")"
if [ -z "${XIRI_IRIS:-}" ]; then
    for binary in ../../emulators/iris-ip30-jit-08e53ba7/iris ../../octane-fill/emulator/iris; do
        if [ -x "$binary" ]; then
            XIRI_IRIS=$binary
            break
        fi
    done
fi
unset IRIS_CHD_DIFF_DIR
export IRIS_NO_IDLE=1
exec "${XIRI_IRIS:-iris}" --config iris.toml "$@"
