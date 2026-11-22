#!/bin/sh
# Run from verified fixture media in single-user mode on a private IP28 overlay.
# The saved firmware must select console=g on the next boot.
set -eu
export PATH=/sbin:/usr/sbin:/bin:/usr/bin
test "$(id -u)" = 0
test "$(sysctl -n hw.model)" = SGI-IP28
test -r ./netbsd
test -r ./compat_irix_o32.kmod
sha256 -c SHA256
install -m 444 ./netbsd /netbsd.ip28
install -m 444 ./compat_irix_o32.kmod \
    "$(sysctl -n kern.module.path)/compat_irix_o32/compat_irix_o32.kmod"
# console=g allocates screen 0 in the kernel. Keep the other wscons settings.
sed '/^screen[[:space:]]*0[[:space:]]/d' /etc/wscons.conf >/etc/wscons.conf.ip28-new
mv /etc/wscons.conf.ip28-new /etc/wscons.conf
# Preserve serial B administration and the existing xdm accounts/sessions.
grep -Eq '^ttyZ0[[:space:]].*[[:space:]]on[[:space:]]' /etc/ttys
grep -q '^xdm=' /etc/rc.conf.d/xdm
grep -q '^xdm_flags=' /etc/rc.conf.d/xdm
sed 's/^xdm=.*/xdm=YES/' /etc/rc.conf.d/xdm >/etc/rc.conf.d/xdm.ip28-new
mv /etc/rc.conf.d/xdm.ip28-new /etc/rc.conf.d/xdm
sync
echo XIRI_IP28_CONSOLE_PREPARED
