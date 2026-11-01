#!/bin/sh
set -eu
rm -f data
printf '0123456789abcdef' >data
chmod 666 data
