#!/bin/sh
set -eu
: >input.txt
chmod 444 input.txt mapping
if test "$1" -eq 0; then
    : >data
else
    dd if=mapping of=data bs="$1" count=1 2>/dev/null
fi
chmod 666 data
cp data zero
chmod 666 zero
ln -sf /dev/zero zero-link
