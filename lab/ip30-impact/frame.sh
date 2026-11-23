#!/bin/sh
# Leave each state on screen until the host has checked the actual scanout.
set -eu
tty_state=$(stty -g)
trap 'stty "$tty_state"' EXIT
stty -echo
printf 'Octane console restored\n' > /dev/ttyE0
read -r ack
printf '\033[2J\033[2;1HXiri scroll marker\033[42;1H' > /dev/ttyE0
read -r ack
printf '\n' > /dev/ttyE0
read -r ack
