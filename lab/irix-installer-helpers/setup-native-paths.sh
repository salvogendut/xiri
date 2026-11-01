#!/bin/sh
# Disposable NetBSD lab only: aliases for the observed bootstrap utility paths.
set -eu
test "$(uname -s)" = NetBSD
test "$(id -u)" = 0
for name in ls mkdir mv ln; do
    target=/bin/$name
    link=/usr/bin/$name
    test -x "$target"
    if test -e "$link" || test -L "$link"; then
        test -L "$link" && test "$(readlink "$link")" = "$target" || {
            echo "Refusing to replace $link" >&2
            exit 1
        }
    else
        ln -s "$target" "$link"
    fi
    echo "XIRI_NATIVE_HELPER $link -> $target"
done
