#!/bin/sh
# Read-only checks; unpack the package in its own directory, never over /.
set -eu
cd "$(dirname "$0")"
package=$PWD
root=/
installed=no
while test "$#" -gt 0; do
    case "$1" in
        --root) test "$#" -ge 2; root=$2; shift 2;;
        --verify-installed) installed=yes; shift;;
        *) echo 'Usage: sh preflight.sh [--root TARGET_ROOT] [--verify-installed]' >&2; exit 2;;
    esac
done
root=$(cd "$root" && pwd -P)
fail() { echo "Xiri native preflight: $*" >&2; exit 1; }
test "$(uname -s)" = NetBSD || fail 'run this checker with native NetBSD tools'
sha256 -c SHA256 >/dev/null || fail 'package content checksum mismatch'
. ./target.conf
if test "$root" = /; then
    test "$(uname -m)" = "$machine" || fail "requires $machine"
    test "$(uname -r)" = "$kernel_release" || fail "boot the supplied $kernel_release kernel first"
    version=$(sysctl -n kern.version)
    test "$(printf %s "$version" | sha256 -q)" = "$kernel_version_sha256" || fail 'running kernel version does not match the qualified build'
fi
test -f "$root/netbsd" && test "$(sha256 -q "$root/netbsd")" = "$kernel_sha256" || fail 'target kernel differs from the supplied kernel/module pair'
while IFS='|' read -r path expected; do
    test -f "$root$path" || fail "missing native prerequisite: $path"
    test "$(sha256 -q "$root$path")" = "$expected" || fail "native prerequisite differs: $path"
done <prerequisites.tsv
while IFS='|' read -r path kind mode value policy; do
    target=$package/$path
    if test "$installed" = yes; then
        case "$path" in
            root/*) target=$root/${path#root/};;
            kernel/*) target=$root/${path#kernel/};;
            *) fail "unexpected member: $path";;
        esac
    fi
    case "$kind" in
        symlink) test -L "$target" && test "$(readlink "$target")" = "$value" || fail "link mismatch: $target";;
        file)
            test -f "$target" && test ! -L "$target" || fail "not a regular file: $target"
            if test "$installed" != yes || test "$policy" != preserve-config; then
                test "$(sha256 -q "$target")" = "$value" || fail "file mismatch: $target"
                # Kernel activation is separate. Existing bootable kernels
                # need readable bytes, not a userspace executable-file mode.
                if test "$installed" != yes || test "$policy" != separate-kernel-activation; then
                    test "$(stat -f %Lp "$target")" = "${mode#0}" || fail "mode mismatch: $target"
                fi
            fi;;
        *) fail "unsupported member type: $kind";;
    esac
done <files.tsv
echo 'Xiri native preflight passed. No target files or service settings were changed.'
