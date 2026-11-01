#!/bin/sh
# Disposable guest fixture tree; all paths are reserved by this lab.
set -eu
chmod -R u+rwx data 2>/dev/null || true
rm -rf data /tmp/xiri-mkdir-native /tmp/xiri-mkdir-shadow
mkdir -p data/exists data/parent data/nosearch data/nowrite data/group data/owner data/sgid /tmp/xiri-mkdir-native /tmp/xiri-mkdir-shadow
chmod 777 data /tmp/xiri-mkdir-native /tmp/xiri-mkdir-shadow data/parent
chmod 755 data/exists
printf unchanged >data/file
chmod 644 data/file
ln -s exists data/linkdir
ln -s missing-target data/dangling
ln -s parent data/linkparent
ln -s loop-b data/loop-a
ln -s loop-a data/loop-b
chmod 666 data/nosearch
chmod 555 data/nowrite
chown 4567 data/group data/sgid
chown 1234 data/owner
chgrp 5678 data/group data/owner data/sgid
chmod 770 data/group
chmod 700 data/owner
chmod 2777 data/sgid
