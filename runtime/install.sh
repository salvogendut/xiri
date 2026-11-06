#!/bin/sh
set -eu
cd "$(dirname "$0")"
stage=${DESTDIR:-}
build=${BUILDDIR:-build}
xdm=no
case "${1:-}" in '') enable=no;; --enable-services) enable=yes;; --enable-xdm) enable=yes; xdm=yes;; *) echo 'Usage: install.sh [--enable-services|--enable-xdm]' >&2; exit 2;; esac
if test -z "$stage"; then test "$(id -u)" = 0; fi
for dir in /usr/local/bin /usr/local/sbin /usr/local/libexec/xiri /usr/local/share/xiri /usr/libexec /etc/xiri/xdm /etc/rc.d /etc/rc.conf.d; do
    install -d -m 755 "$stage$dir"
done
install -m 444 etc/xdm.xsession "$stage/usr/local/share/xiri/xdm.xsession"
install -m 444 etc/desktop-Xresources "$stage/usr/local/share/xiri/desktop-Xresources"
install -m 555 sbin/xiri-sync-users "$stage/usr/local/sbin/xiri-sync-users"
install -m 444 libexec/account-map.awk "$stage/usr/local/libexec/xiri/account-map.awk"
install -m 444 libexec/sgi-colours.awk "$stage/usr/local/libexec/xiri/sgi-colours.awk"
for name in Xservers Xresources; do
    install -m 444 "etc/xdm-$name" "$stage/etc/xiri/xdm/$name.example"
    test -e "$stage/etc/xiri/xdm/$name" || install -m 644 "etc/xdm-$name" "$stage/etc/xiri/xdm/$name"
done
for name in xiri-desktop xiri-session xiri-launch xiri-logout; do install -m 555 "bin/$name" "$stage/usr/local/bin/$name"; done
for name in session-guard x11-check save-session; do install -m 555 "$build/$name" "$stage/usr/local/libexec/xiri/$name"; done
install -m 555 "$build/shell-handoff" "$stage/usr/libexec/xiri-shell"
for name in desktop-clients.sh setup-pty.sh; do install -m 555 "libexec/$name" "$stage/usr/local/libexec/xiri/$name"; done
ln -snf /bin/sh "$stage/usr/local/libexec/xiri/command-shell"
# IRIX scripts can execute native utilities. Those utilities do not apply the
# emulation-root lookup to their pathname arguments (GIMP's user_install uses
# native cp with /usr/freeware sources, Acrobat's native cat with /usr/adobe).
# Publish these otherwise unused prefixes,
# while preserving any administrator-owned directory or link already there.
for prefix in freeware adobe; do
    if test -d "$stage/emul/irix/usr/$prefix" &&
        ! test -e "$stage/usr/$prefix" && ! test -L "$stage/usr/$prefix"; then
        ln -s "/emul/irix/usr/$prefix" "$stage/usr/$prefix"
    fi
done
# The installed-image import resolves colorscheme to the original schemebr
# executable, but Toolchest uses its canonical name. Expose both names without
# replacing either an existing installation or the imported program bytes.
browser="$stage/emul/irix/usr/sbin/schemebr"
if test -f "$stage/emul/irix/usr/sbin/colorscheme" &&
    ! test -e "$browser" && ! test -L "$browser"; then
    ln -s colorscheme "$browser"
fi
for name in xiri_devices xiri_famd; do install -m 555 "rc.d/$name" "$stage/etc/rc.d/$name"; done
for name in session.conf fam.conf Xresources; do
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
