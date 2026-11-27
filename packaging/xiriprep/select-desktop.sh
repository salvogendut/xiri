#!/bin/sh
# Invoked as the desktop owner so every change in HOME has that user's rights.
set -eu
[ "$(id -u)" -ne 0 ] || exit 1
cd "$HOME"
umask 077
template=/usr/local/share/xiri/xdm.xsession
if [ -x .xsession ] && cmp -s "$template" .xsession; then exit 0; fi
draft=$(mktemp ./.xiriprep.XXXXXX)
trap 'rm -f "$draft"' EXIT
trap 'exit 1' HUP INT TERM
install -m 700 "$template" "$draft"
if [ -e .xsession ] || [ -L .xsession ]; then
    [ -f .xsession ] || { echo 'Existing .xsession is not a regular file' >&2; exit 1; }
    backup=.xsession.before-xiriprep
    if [ -e "$backup" ] || [ -L "$backup" ]; then
        [ .xsession -ef "$backup" ] || { echo "Existing backup in $HOME/$backup" >&2; exit 1; }
    else
        ln -Ph .xsession "$backup"
    fi
fi
mv -fh "$draft" .xsession
