#!/bin/sh
# Run only inside this disposable lab directory, on either kernel.
set -eu
TZ=GMT0
export TZ
mkdir -p tree/dir tree/deny
printf 'XIRI_STAT_DATA\n' >tree/file
: >tree/empty
printf 'SECRET\n' >tree/deny/file
ln tree/file tree/hard
ln -s file tree/link
ln -s missing tree/dangling
ln -s loop-b tree/loop-a
ln -s loop-a tree/loop-b
mkfifo tree/fifo
mknod tree/char c 1 2
mknod tree/block b 3 4
chmod 0600 tree/char tree/block
mkdir -p /tmp/xiri-xstat-namespace
cp tree/file /tmp/xiri-xstat-namespace/shadow
cp tree/file /tmp/xiri-xstat-namespace/fallback
chmod 0640 /tmp/xiri-xstat-namespace/*
chown 1234 /tmp/xiri-xstat-namespace/*
chgrp 2345 /tmp/xiri-xstat-namespace/*
chmod 0640 tree/file
chmod 0000 tree/empty
chmod 0751 tree/dir
chmod 0700 tree/deny
chmod 0620 tree/fifo
chown 1234 tree/file
chgrp 2345 tree/file
# Sparse file crosses the signed 32-bit size limit without allocating 2 GiB.
dd if=/dev/zero of=tree/large bs=1024 count=1 seek=2097152 2>large-setup.err
touch -t 199901020304.05 tree/file tree/empty tree/large tree/dir tree/fifo
