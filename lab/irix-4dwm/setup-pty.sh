#!/bin/sh
# Disposable NetBSD guest only. These are native devices and namespace aliases.
set -eu
# Run before opening any PTYs: ptyfs does not support mount updates.
umount /dev/pts
mount -t ptyfs -o group=0,mode=0600 ptyfs /dev/pts
mkdir -p /emul/irix/dev
# O_CREAT pathname lookup selects this emulation directory for shell
# redirection. Supply the native null device there; otherwise root can create
# a regular "null" file and ordinary users cannot redirect to /dev/null.
null_major=$(stat -f '%Hr' /dev/null)
null_minor=$(stat -f '%Lr' /dev/null)
if test ! -e /emul/irix/dev/null; then
    mknod /emul/irix/dev/null c "$null_major" "$null_minor"
fi
test -c /emul/irix/dev/null
test "$(stat -f %Hr /emul/irix/dev/null)" = "$null_major"
test "$(stat -f %Lr /emul/irix/dev/null)" = "$null_minor"
chmod 666 /emul/irix/dev/null
# Absolute symlinks are resolved inside the selected emulation root. Share
# the actual native ptyfs view there so libc's two slave names reach one vnode.
mkdir -p /emul/irix/dev/pts
mount -t null /dev/pts /emul/irix/dev/pts
# ptm minor 2 allocates a native master and grants its slave to the real UID.
# This native clone entry already supplies ownership and revocation checks.
pty_major=$(stat -f '%Hr' /dev/ptmx)
if test ! -c /emul/irix/dev/ptc; then mknod /emul/irix/dev/ptc c "$pty_major" 2; fi
test "$(stat -f %Hr /emul/irix/dev/ptc)" = "$pty_major"
test "$(stat -f %Lr /emul/irix/dev/ptc)" = 2
chmod 666 /emul/irix/dev/ptc
i=0
while test "$i" -lt 400; do
    if test "$i" -lt 200; then letter=q; unit=$i; else letter=r; unit=$((i - 200)); fi
    if test -L "/emul/irix/dev/tty$letter$unit"; then
        test "$(readlink "/emul/irix/dev/tty$letter$unit")" = "/dev/pts/$i"
    else
        ln -s "/dev/pts/$i" "/emul/irix/dev/tty$letter$unit"
    fi
    i=$((i + 1))
done
# /dev/pts/N itself uses the ordinary emulation-root native-path fallback.
ls -l /emul/irix/dev/ptc /emul/irix/dev/ttyq0 /emul/irix/dev/ttyr199
