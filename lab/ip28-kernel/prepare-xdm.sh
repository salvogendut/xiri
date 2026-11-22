#!/bin/sh
# Opt the qualified, single-user IP28 lab image into normal native xdm boot.
# Run once on a private overlay. No account/password or IRIX payload changes.
set -eu
export PATH=/usr/local/sbin:/usr/local/bin:/usr/X11R7/bin:/sbin:/usr/sbin:/bin:/usr/bin
test "$(id -u)" = 0
test "$(sysctl -n hw.model)" = SGI-IP28
test -r "$(sysctl -n kern.module.path)/compat_irix_o32/compat_irix_o32.kmod"
grep -qx compat_irix_o32 /etc/modules.conf
test -x /etc/rc.d/xiri_devices
test -x /usr/people/xiritest/.xsession
test ! -e /home/netbsdtest/.xsession
test "$(id -u xiritest)" = 1234
test "$(id -u netbsdtest)" = 1236
# A serial console does not allocate wsdisplay screen 0 in the kernel.
# Native wscons runs before LOGIN/xdm and provides that screen at boot.
test -e /etc/wscons.conf.before-ip28-xdm || cp -p /etc/wscons.conf /etc/wscons.conf.before-ip28-xdm
if ! grep -Eq '^screen[[:space:]]+0[[:space:]]' /etc/wscons.conf; then
    { printf '# IP28 serial-console desktop display.\nscreen 0 - vt100\n'; cat /etc/wscons.conf; } >/etc/wscons.conf.ip28-new
    mv /etc/wscons.conf.ip28-new /etc/wscons.conf
fi
printf 'wscons=YES\n' >/etc/rc.conf.d/wscons
test -e /etc/ttys.before-ip28-xdm || cp -p /etc/ttys /etc/ttys.before-ip28-xdm
sed '/^ttyE0[[:space:]]/s/[[:space:]]on[[:space:]]/ off /' /etc/ttys.before-ip28-xdm >/etc/ttys
grep -Eq '^ttyZ0[[:space:]].*[[:space:]]on[[:space:]]' /etc/ttys
grep -q '^xdm=YES$' /etc/rc.conf.d/xdm
grep -q 'Driver "wsfb"' /usr/local/share/xiri/xorg.conf
test -e /usr/local/share/xiri/xorg.conf.before-ip28-xdm || cp -p /usr/local/share/xiri/xorg.conf /usr/local/share/xiri/xorg.conf.before-ip28-xdm
sed -e 's/Identifier "Indy"/Identifier "IP28"/' \
    -e 's/NewportScreen/ImpactScreen/g' -e 's/"Newport"/"IMPACT"/g' \
    -e '/Experimental acceleration profile/d' -e '/Option "NoAccel"/d' \
    /usr/local/share/xiri/xorg.conf.before-ip28-xdm >/usr/local/share/xiri/xorg.conf
echo XIRI_IP28_XDM_PREPARED
cat /etc/rc.conf.d/wscons /etc/rc.conf.d/xdm /etc/modules.conf
sha256 /etc/wscons.conf /etc/ttys /usr/local/share/xiri/xorg.conf
sync
