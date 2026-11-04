#!/bin/sh
# Native controls for the emulation-root policy; run only on a disposable guest.
set -eu
base=/usr/xiri-rename-checks
emulated=/emul/irix$base
results=/tmp/xiri-rename-namespace
test ! -e "$base" && test ! -e "$emulated" && test ! -e "$results"
mkdir -p "$base" "$emulated" "$results"
trap 'rm -rf "$base" "$emulated"' EXIT HUP INT TERM
for abi in o32 n32; do
    for call in direct indirect; do
        executable=/tmp/xiri-pathops/$abi-$call
        for policy in emulation native-escape fallback cross-root; do
            label=$abi-$call-$policy
            native=$base/$label
            alternate=$emulated/$label
            mkdir "$native"
            printf 'native\n' >"$native/src"
            : >"$native/input.txt"
            chown -R 1234:1234 "$native"
            if test "$policy" != fallback; then
                mkdir "$alternate"
                printf 'emulated\n' >"$alternate/src"
                : >"$alternate/input.txt"
                chown -R 1234:1234 "$alternate"
            fi
            case "$policy" in
                emulation) source=$native/src; destination=$native/dst; directory=$alternate;;
                native-escape) source=/..$native/src; destination=/..$native/dst; directory=$native;;
                fallback) source=$native/src; destination=$native/dst; directory=$native;;
                cross-root) source=/..$native/src; destination=$native/dst; directory=$native;;
            esac
            (cd "$directory"; /tmp/xiri-pathops/runner "$executable" 1234 1234 1234 1234 -- 0 "$source" "$destination") >"$results/$label.log"
            grep -q 'errno_bytes=0 errno=0 exit=0 signal=0 killed=0' "$results/$label.log"
            grep -q 'GROUP absent=1' "$results/$label.log"
            case "$policy" in
                emulation)
                    test ! -e "$alternate/src" && test "$(cat "$alternate/dst")" = emulated
                    test "$(cat "$native/src")" = native && test ! -e "$native/dst";;
                native-escape)
                    test ! -e "$native/src" && test "$(cat "$native/dst")" = native
                    test "$(cat "$alternate/src")" = emulated && test ! -e "$alternate/dst";;
                fallback)
                    test ! -e "$native/src" && test "$(cat "$native/dst")" = native;;
                cross-root)
                    test ! -e "$native/src" && test "$(cat "$alternate/dst")" = native
                    test "$(cat "$alternate/src")" = emulated && test ! -e "$native/dst";;
            esac
            echo "PASS $label"
        done
    done
done
