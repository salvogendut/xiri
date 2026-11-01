#!/bin/sh
# Create a native NetBSD account with the requested IRIX-style home location.
set -eu

die() { echo "setup-xiri-user: $*" >&2; exit 1; }
[ "$(uname -s)" = NetBSD ] || die 'run this inside the NetBSD target'
[ "$(id -u)" = 0 ] || die 'account creation requires root'
[ "$#" -ge 1 ] && [ "$#" -le 2 ] || die 'usage: setup-xiri-user.sh username [uid]'
name=$1
case "$name" in ''|*[!a-z0-9_-]*|[0-9-]*) die 'invalid account name';; esac
requested_uid=${2-}
if [ -n "$requested_uid" ]; then
    case "$requested_uid" in *[!0-9]*) die 'uid must be numeric';; esac
    [ "$requested_uid" -gt 0 ] || die 'use a non-root uid'
fi
home_path=/usr/people/$name
[ -x /bin/ksh ] || die 'native /bin/ksh is required'

if account=$(getent passwd "$name"); then
    existing_home=$(printf '%s\n' "$account" | cut -d: -f6)
    [ "$existing_home" = "$home_path" ] || die "existing account uses $existing_home; migrate it separately"
    if [ -n "$requested_uid" ]; then
        [ "$(id -u "$name")" = "$requested_uid" ] || die 'existing uid differs'
    fi
    [ -d "$home_path" ] && [ ! -L "$home_path" ] || die 'existing home is not a directory'
    [ "$(stat -f %u "$home_path")" = "$(id -u "$name")" ] || die 'home owner differs'
    echo "XIRI_USER existing name=$name home=$home_path"
    exit 0
fi

# Do not adopt pre-existing files or create an emulation-root shadow of HOME.
[ ! -e "$home_path" ] && [ ! -L "$home_path" ] || die 'home path already exists'
[ ! -L /usr/people ] || die '/usr/people must be a native directory'
install -d -m 755 /usr/people
if [ -n "$requested_uid" ]; then
    useradd -m -u "$requested_uid" -d "$home_path" -s /bin/ksh "$name"
else
    useradd -m -d "$home_path" -s /bin/ksh "$name"
fi
chmod 700 "$home_path"
echo "XIRI_USER created name=$name home=$home_path shell=/bin/ksh"
# Native useradd installs /etc/skel. IRIX clients create their own desktop
# state under HOME; passwords and login policy remain native administration.
