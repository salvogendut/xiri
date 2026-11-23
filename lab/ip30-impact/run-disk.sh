#!/bin/sh
# Copy next to iris.toml, nvram.bin, flash.bin and netbsd-xiri.chd.
set -eu
ulimit -c 0
cd "$(dirname "$0")"
local_iris=../../octane-fill/emulator/iris
if [ -z "${XIRI_IRIS:-}" ] && [ -x "$local_iris" ]; then
    XIRI_IRIS=$local_iris
fi
unset IRIS_CHD_DIFF_DIR
export IRIS_NO_IDLE=1
exec "${XIRI_IRIS:-iris}" --config iris.toml "$@"
