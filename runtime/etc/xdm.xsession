#!/bin/sh
# Select this session as the native desktop user via $HOME/.xsession.
# Native xdm supplies HOME, groups, DISPLAY and X authority.
# The current IRIX socket personality supports IPv4 TCP, not Unix sockets.
# Xdm's local-display authority entries also cover the loopback connection.
case "${DISPLAY:-}" in
    :*) DISPLAY="127.0.0.1$DISPLAY"; export DISPLAY;;
esac
exec /usr/local/bin/xiri-session
