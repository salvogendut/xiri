#!/bin/sh
set -eu
PATH=/bin:/usr/bin:/sbin:/usr/sbin
export PATH
test "$(sysctl -n hw.model)" = IP30
case "$1" in update|restored) version=11.99.9 ;; desktop|rollback) version=11.99.11 ;; *) exit 1 ;; esac
test "$(sysctl -n kern.osrelease)" = "$version"
modstat | grep '^compat_irix_o32 '
test "$(/emul/irix/bin/sh -c 'echo IRIX-shell')" = IRIX-shell
t=$(su - xiritest -c 'mktemp')
su - xiritest -c "/mnt/n32-direct e $t"
if test "$version" = 11.99.11; then test "$(stat -f %m "$t")" = 1234567890
else test "$(stat -f %m "$t")" != 1234567890; fi
rm "$t"
mount -rt cd9660 /dev/cd0a /cdrom
case "$1" in
    update) sh /cdrom/upgrade.sh && sh /cdrom/upgrade.sh ;;
    rollback) sh /cdrom/upgrade.sh --rollback && sh /cdrom/upgrade.sh --rollback ;;
esac
cd /
umount /cdrom
sync
