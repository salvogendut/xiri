#!/bin/sh
set -eu
TZ=GMT0
export TZ
mkdir -p tree/dir
printf 'XIRI_STAT_DATA\n' >tree/file
printf 'SECOND\n' >tree/second
: >tree/empty
mkfifo tree/fifo
chmod 666 tree/fifo
chmod 644 tree/file tree/second tree/empty
# Read permission is needed by native open before measuring fxstat.
chmod 755 tree/dir
chown 1234 tree/file
chgrp 2345 tree/file
# Parent opens stdin as root before changing the fixture's credentials.
printf 'XIRI_VENDOR_O32\n' >input.txt
chmod 0000 input.txt
dd if=/dev/zero of=tree/large bs=1024 count=1 seek=2097152 2>large-setup.err
touch -t 199901020304.05 tree/file tree/second tree/empty tree/dir tree/fifo tree/large input.txt
