#!/bin/sh
set -eu
umask 022
printf ABCDEFGH >shared
chmod 666 shared
rm -f gate
mkfifo gate
chmod 666 gate
