#!/bin/sh
# Only inside the disposable access lab. No special devices are opened.
set -eu
umask 022
mkdir -p tree/dir tree/deny tree/search
for name in file owner owner-read owner-exec group group-exec other none noexec empty; do
    printf 'XIRI_ACCESS\n' >tree/$name
done
chmod 0644 tree/file
chown 1234 tree/owner tree/owner-read tree/owner-exec
chmod 0700 tree/owner
chmod 0400 tree/owner-read
chmod 0100 tree/owner-exec
chown 4567 tree/group tree/group-exec
chgrp 2345 tree/group tree/group-exec
chmod 0040 tree/group
chmod 0010 tree/group-exec
chmod 0004 tree/other
chmod 0000 tree/none tree/empty
chmod 0666 tree/noexec
: >tree/empty
printf data >tree/deny/file
printf data >tree/search/file
chmod 0644 tree/deny/file tree/search/file
chmod 0700 tree/deny
chmod 0111 tree/search
chmod 0755 tree/dir
ln tree/file tree/hard
ln -s file tree/link
ln -s missing tree/dangling
ln -s loop-b tree/loop-a
ln -s loop-a tree/loop-b
mkfifo tree/fifo
chmod 0666 tree/fifo
mkdir -p /tmp/xiri-access-namespace
printf native >/tmp/xiri-access-namespace/shadow
printf fallback >/tmp/xiri-access-namespace/fallback
chmod 0666 /tmp/xiri-access-namespace/*
