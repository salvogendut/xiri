#!/bin/sh
# Run from read-only qualification media, in single-user mode.
set -eu
export PATH=/bin:/sbin:/usr/bin:/usr/sbin
ulimit -c 0
test "$(sysctl -n kern.securelevel)" = 0
work=$(mktemp -d /var/tmp/ip28-module.XXXXXX)
trap 'cd /; rm -rf "$work"' EXIT
cp /cdrom/runner.c /cdrom/lifecycle.c /cdrom/vendor-asa "$work/"
cd "$work"
chmod 755 vendor-asa
cc -O2 -Wall -Wextra -Werror runner.c -o runner
cc -O2 -Wall -Wextra -Werror lifecycle.c -o lifecycle
printf ' XIRI_MODULE_OK\n' >input.txt
observe() {
    ./runner ./vendor-asa >observation
    cat observation
    grep -q "errno_bytes=$1 errno=$2 exit=$3 signal=0 killed=0" observation
    grep -q '^STDERR bytes=0 hex=$' observation
    if test "$2" = 0; then
        grep -q '^STDOUT bytes=15 hex=584952495f4d4f44554c455f4f4b0a$' observation
    else
        grep -q '^STDOUT bytes=0 hex=$' observation
    fi
}
! modstat | grep '^compat_irix_o32 '
observe 4 8 126
modload /cdrom/compat_irix_o32.kmod
modstat
observe 0 0 0
/emul/irix/bin/sh -c '/bin/echo XIRI_IP28_VENDOR_SHELL_OK; /bin/pwd'
./lifecycle ./vendor-asa >lifecycle.log
cat lifecycle.log
grep -q 'BUSY result=-1 errno=16' lifecycle.log
grep -q 'IDLE result=0 errno=0' lifecycle.log
observe 4 8 126
modload /cdrom/compat_irix_o32.kmod
observe 0 0 0
/emul/irix/bin/sh -c '/bin/echo XIRI_IP28_VENDOR_RELOAD_OK'
module_dir=$(sysctl -n kern.module.path)/compat_irix_o32
mkdir -p "$module_dir"
install -m 444 /cdrom/compat_irix_o32.kmod "$module_dir/compat_irix_o32.kmod"
modunload compat_irix_o32
observe 4 8 126
echo XIRI_IP28_MODULE_LIFECYCLE_PASSED
