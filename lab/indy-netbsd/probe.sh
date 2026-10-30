#!/bin/sh
# Runs only on a disposable NetBSD lab disk. Arguments come from the host harness.
set -eu
expected_ident=$1
expected_kernel_sha=$2
expected_payload_sha=$3

test "$(sysctl -n kern.configname)" = "$expected_ident"
test "$(sha256 -q /netbsd)" = "$expected_kernel_sha"
test "$(cksum /root/xiri-probe)" = '3540535338 33 /root/xiri-probe'
swapctl -l | grep '^/dev/sd0b ' >/dev/null

# Exercise file creation, a write to disk, and a separate checksum read.
test ! -e /root/xiri-io-probe
cp /cdrom/payload.bin /root/xiri-io-probe
sync
test "$(sha256 -q /root/xiri-io-probe)" = "$expected_payload_sha"
rm /root/xiri-io-probe
sync

printf 'XIRI_PROBE_OK\n'
sysctl kern.configname
cksum /root/xiri-probe
swapctl -l
