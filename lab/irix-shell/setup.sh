#!/bin/sh
set -eu
printf ABCDEFGH >shared
chmod 666 shared
: >input.txt
chmod 444 input.txt
