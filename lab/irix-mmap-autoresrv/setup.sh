#!/bin/sh
set -eu
: >input.txt
chmod 444 input.txt
chmod 444 mapping
cp mapping writable
chmod 666 writable
