#!/bin/sh
# Install into the private release overlay from a single-user Octane boot.
set -eu
cd /cdrom
test "$(sysctl -n hw.model)" = IP30
sha256 -c SHA256
mount -u -w /
install -m 444 netbsd /netbsd.ip30
install -m 444 ip30boot /usr/mdec/ip30boot
/usr/mdec/sgivol -q -w boot /usr/mdec/ip30boot /dev/rsd0c
module_dir="$(sysctl -n kern.module.path)/compat_irix_o32"
mkdir -p "$module_dir"
install -m 444 compat_irix_o32.kmod "$module_dir/compat_irix_o32.kmod"
grep -qx compat_irix_o32 /etc/modules.conf
grep -qx 'xdm=YES' /etc/rc.conf.d/xdm
grep -q 'Driver "wsfb"' /usr/local/share/xiri/xorg.conf
# The Octane admin port is IOC3 com0. Screen 0 belongs to wsdisplay/Xorg.
sed -e '/^ttyC0[[:space:]]/s/[[:space:]]off[[:space:]]/ on /' \
    -e '/^ttyZ0[[:space:]]/s/[[:space:]]on[[:space:]]/ off /' /etc/ttys >/etc/ttys.ip30
grep -Eq '^ttyC0[[:space:]].*[[:space:]]on[[:space:]]' /etc/ttys.ip30
mv /etc/ttys.ip30 /etc/ttys
# The release roots use DHCP on the Indy's sq0. The IP30 kernel currently
# supplies loopback networking for the desktop and has no IOC3 Ethernet driver.
printf 'dhcpcd=NO\n' >/etc/rc.conf.d/dhcpcd
cd /
sync
echo OCTANE_DISK_INSTALLED
