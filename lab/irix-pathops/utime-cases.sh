#!/bin/sh
# Run as an ordinary user in a private writable directory. The caller
# supplies absolute paths to the probes and two root-owned fixture files.
set -eu
probes=$1
readonly_file=$2
writable_file=$3
for abi in o32-direct o32-indirect n32-direct n32-indirect; do
    mkdir "$abi"
    (
        cd "$abi"
        touch owned
        ln -s owned link
        check() {
            printf '%s %s ' "$abi" "$1"
            "$probes/$abi" "$2" "$3"
        }
        check explicit e owned
        check symlink e link
        check trailing e owned/
        check negative p owned
        check minus_one s owned
        check bad_times b owned
        check missing e missing
        check missing_bad b missing
        check current n owned
        check denied_before r "$readonly_file"
        check denied e "$readonly_file"
        check denied_now n "$readonly_file"
        check shared_before r "$writable_file"
        check shared_denied e "$writable_file"
        check shared_now n "$writable_file"
    )
done
