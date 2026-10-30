#!/bin/sh
# Bounded filesystem exercise on a disposable disk, followed by a cold read.
set -eu
phase=$1
rounds=${2:-3}
directory=/root/xiri-disk-test

check_file() {
    source=$1
    destination=$2
    expected=$(cat "/cdrom/$source.sha256")
    actual=$(sha256 -q "$destination")
    test "$actual" = "$expected"
    printf 'XIRI_DISK_HASH %s %s\n' "$destination" "$actual"
}

case "$phase" in
write)
    test ! -e "$directory"
    mkdir "$directory"
    round=0
    while [ "$round" -lt "$rounds" ]; do
        # Alternate destinations so every round overwrites different bytes.
        first=$((round % 2))
        second=$((1 - first))
        cp "/cdrom/payload$first.bin" "$directory/first.bin"
        cp "/cdrom/payload$second.bin" "$directory/second.bin"
        sync
        check_file "payload$first.bin" "$directory/first.bin"
        check_file "payload$second.bin" "$directory/second.bin"
        printf '%s\n' "$first" > "$directory/last-round"
        sync
        round=$((round + 1))
        printf 'XIRI_DISK_ROUND %s\n' "$round"
    done
    printf 'XIRI_DISK_WRITE_OK\n'
    ;;
verify)
    first=$(cat "$directory/last-round")
    case "$first" in 0|1) ;; *) exit 1 ;; esac
    second=$((1 - first))
    check_file "payload$first.bin" "$directory/first.bin"
    check_file "payload$second.bin" "$directory/second.bin"
    printf 'XIRI_DISK_COLD_READ_OK\n'
    ;;
*) exit 2 ;;
esac
