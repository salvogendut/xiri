#!/bin/sh
set -eu
cd "$(dirname "$0")"
stage=${DESTDIR:-}
build=${BUILDDIR:-build}
xdm=no
case "${1:-}" in '') enable=no;; --enable-services) enable=yes;; --enable-xdm) enable=yes; xdm=yes;; *) echo 'Usage: install.sh [--enable-services|--enable-xdm]' >&2; exit 2;; esac
if test -z "$stage"; then test "$(id -u)" = 0; fi
for dir in /usr/local/bin /usr/local/libexec/xiri /usr/local/share/xiri /usr/libexec /etc/xiri/xdm /etc/rc.d /etc/rc.conf.d; do
    install -d -m 755 "$stage$dir"
done
install -m 444 etc/xdm.xsession "$stage/usr/local/share/xiri/xdm.xsession"
for name in Xservers Xresources; do
    install -m 444 "etc/xdm-$name" "$stage/etc/xiri/xdm/$name.example"
    test -e "$stage/etc/xiri/xdm/$name" || install -m 644 "etc/xdm-$name" "$stage/etc/xiri/xdm/$name"
done
for name in xiri-desktop xiri-session xiri-launch xiri-logout; do install -m 555 "bin/$name" "$stage/usr/local/bin/$name"; done
for name in session-guard x11-check; do install -m 555 "$build/$name" "$stage/usr/local/libexec/xiri/$name"; done
install -m 555 "$build/shell-handoff" "$stage/usr/libexec/xiri-shell"
for name in desktop-clients.sh setup-pty.sh; do install -m 555 "libexec/$name" "$stage/usr/local/libexec/xiri/$name"; done
ln -snf /bin/sh "$stage/usr/local/libexec/xiri/command-shell"
for name in xiri_devices xiri_famd; do install -m 555 "rc.d/$name" "$stage/etc/rc.d/$name"; done
for name in session.conf fam.conf; do
    install -m 444 "etc/$name" "$stage/etc/xiri/$name.example"
    test -e "$stage/etc/xiri/$name" || install -m 644 "etc/$name" "$stage/etc/xiri/$name"
done
if test "$enable" = yes; then
    for name in xiri_devices xiri_famd; do
        if test ! -e "$stage/etc/rc.conf.d/$name"; then
            printf '%s=YES\n' "$name" >"$stage/etc/rc.conf.d/$name"
            chmod 644 "$stage/etc/rc.conf.d/$name"
        fi
    done
    if test ! -e "$stage/etc/rc.conf.d/rpcbind"; then
        printf 'rpcbind=YES\nrpcbind_flags="-h 127.0.0.1"\n' >"$stage/etc/rc.conf.d/rpcbind"
        chmod 644 "$stage/etc/rc.conf.d/rpcbind"
    fi
fi
if test "$xdm" = yes && test ! -e "$stage/etc/rc.conf.d/xdm"; then
    printf 'xdm=YES\nxdm_flags="-server /etc/xiri/xdm/Xservers -resources /etc/xiri/xdm/Xresources"\n' >"$stage/etc/rc.conf.d/xdm"
    chmod 644 "$stage/etc/rc.conf.d/xdm"
fi
