#!/bin/sh
set -eu
mkdir -p tree/directory/sub tree/empty
printf 'data\n' >tree/file
printf 'one\n' >tree/directory/a
printf 'two\n' >tree/directory/elevenchars
ln -s nowhere tree/directory/link
chmod 755 tree tree/directory tree/empty
