#!/bin/sh
# Run in an O2 guest with the matching NetBSD 11.0 sgimips X sets.
set -eu
if [ "$#" -ne 1 ]; then
    echo "usage: sh install-greeter.sh /path/to/libXiriO2Greet.so" >&2
    exit 2
fi
test "$(sysctl -n hw.model)" = SGI-IP32
lib=/usr/local/lib/xiri/libXiriO2Greet.so
config=/etc/X11/xdm/xdm-config
resources=/etc/xiri/xdm/Xresources
install -d -m 755 /usr/local/lib/xiri
install -o root -g wheel -m 444 "$1" "$lib"
if ! grep -Fqx "DisplayManager.greeterLib: $lib" "$config"; then
    printf '\nDisplayManager.greeterLib: %s\n' "$lib" >> "$config"
fi
# Retire the greeter-only Xft setting from the first O2 test images.
if grep -Fqx 'Xft.render: false' "$resources"; then
    tmp=$(mktemp "${resources}.XXXXXX")
    trap 'rm -f "$tmp"' EXIT
    sed '/^Xft\.render: false$/d' "$resources" > "$tmp"
    chmod 444 "$tmp"
    mv -f "$tmp" "$resources"
fi
