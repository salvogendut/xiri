#!/bin/sh
set -eu
mkdir -p tree
dd if=/dev/zero of=tree/file bs=1024 count=1 2>/dev/null
chmod 0777 tree
chmod 0666 tree/file
