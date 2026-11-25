#!/bin/sh
# Install on the November 25 Mozilla input Indy. Preserve local configuration.
set -eu
fail() { echo "$*" >&2; exit 1; }
[ "$(id -u)" = 0 ] || fail 'Run as NetBSD root.'
[ "$(uname -smr)" = 'NetBSD 11.99.11 sgimips' ] || fail 'This update requires the November 25 NetBSD/sgimips kernel.'
[ "$(sha256 -q /netbsd)" = e989c42d3469f5d59e2ec759fdb3d7f54d7a893acdc326f6f3a3c4487f19fd22 ] || fail 'Kernel checksum differs from the qualified Indy kernel.'
cd "$(dirname "$0")"
while read -r hash file; do
    [ "$(sha256 -q "./$file")" = "$hash" ] || fail "Bad checksum: $file"
done < SHA256
mod=/stand/sgimips/11.99.11/modules/compat_irix_o32/compat_irix_o32.kmod
old=38873c2f84ef23bf50e263b833ebf6ce3077482ed770d061ffdc7ee83fcddcb4
new=$(sha256 -q compat_irix_o32.kmod)
current=$(sha256 -q "$mod")
[ "$current" = "$old" ] || [ "$current" = "$new" ] || fail 'Installed module differs from the qualified Mozilla input module.'
helper=/usr/local/libexec/xiri/mount_xiri_hosts
svc=/etc/rc.d/xiri_hosts
conf=/etc/rc.conf.d/xiri_hosts
dest=/emul/irix/ns/.local/hosts.byname
backup="$mod.pre-browser-network"
for path in "$helper" "$svc"; do
    if [ -e "$path" ] || [ -L "$path" ]; then
        [ ! -L "$path" ] && cmp -s "./${path##*/}" "$path" || fail "Existing installation differs: $path"
    fi
done
if [ -e "$backup" ] || [ -L "$backup" ]; then
    [ ! -L "$backup" ] && [ "$(sha256 -q "$backup")" = "$old" ] || fail 'Existing module backup differs.'
elif [ "$current" = "$old" ]; then
    cp -p "$mod" "$backup"
fi
mkdir -p "${helper%/*}" /etc/rc.conf.d "$dest"
if [ ! -f "$helper" ]; then install -m 555 mount_xiri_hosts "$helper"; fi
if [ ! -f "$svc" ]; then install -m 555 xiri_hosts "$svc"; fi
if [ ! -e "$conf" ] && [ ! -L "$conf" ]; then
    printf 'xiri_hosts=YES\n' > "$conf"
fi
if [ "$current" != "$new" ]; then
    tmp=$(mktemp "$mod.XXXXXX")
    trap 'rm -f "$tmp"' EXIT
    trap 'exit 1' HUP INT TERM
    install -m 444 compat_irix_o32.kmod "$tmp"
    mv "$tmp" "$mod"
fi
echo "Installed. Reboot to load the module. Resolver settings: $conf"
