#!/bin/sh
# Native devices and IRIX namespace aliases; run once at boot before LOGIN.
set -eu
# Run before opening any PTYs. Preserve an already configured native mount;
# ptyfs does not support mount updates, and an in-use mount cannot be replaced.
if mount | awk '$2 == "on" && $3 == "/emul/irix/dev/pts" { found=1 } END { exit !found }'; then
    umount /emul/irix/dev/pts
fi
case "$(mount_ptyfs -o getargs ptyfs /dev/pts)" in
    *,\ gid=0,\ mode=0600) ;;
    *)
        umount /dev/pts
        mount -t ptyfs -o group=0,mode=0600 ptyfs /dev/pts
        ;;
esac
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
# NetBSD's /../ prefix explicitly selects the real root during emulation
# lookup, including absolute symlinks. Reach the native ptyfs vnode directly:
# GNOME reopens its slave after setsid, and a nullfs controlling-tty vnode
# can panic the native session teardown when it is revoked.
if test -L /emul/irix/dev/pts; then
    test "$(readlink /emul/irix/dev/pts)" = /../dev/pts
else
    if test -d /emul/irix/dev/pts; then rmdir /emul/irix/dev/pts; fi
    ln -s /../dev/pts /emul/irix/dev/pts
fi
# ptm minor 2 allocates a native master and grants its slave to the real UID.
# Both IRIX entry names need this behavior. Native /dev/ptmx (minor 0) does
# not grant on open; falling through to it sends GNOME's helper down the
# IRIX mkpts ownership-repair path instead of using the native PTY owner.
pty_major=$(stat -f '%Hr' /dev/ptmx)
for device in ptc ptmx; do
    path=/emul/irix/dev/$device
    if test ! -c "$path"; then mknod "$path" c "$pty_major" 2; fi
    test "$(stat -f %Hr "$path")" = "$pty_major"
    test "$(stat -f %Lr "$path")" = 2
    chmod 666 "$path"
done
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
ls -l /emul/irix/dev/ptc /emul/irix/dev/ptmx /emul/irix/dev/ttyq0 /emul/irix/dev/ttyr199
