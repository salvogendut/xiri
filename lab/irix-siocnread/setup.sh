#!/bin/sh
set -eu
printf ' XIRI_VENDOR_O32\n' >input.txt
chmod 666 input.txt
rm -f fifo
mkfifo fifo
chmod 666 fifo
