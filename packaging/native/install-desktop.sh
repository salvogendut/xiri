#!/bin/sh
# Run from read-only Xiri install media after booting the matching kernel.
set -eu
PATH=/bin:/sbin:/usr/bin:/usr/sbin:/usr/X11R7/bin
export PATH
umask 022
fail() { echo "Xiri installer: $*" >&2; exit 1; }
test "$#" -eq 0 && test "$(id -u)" = 0 && test "$(uname -s)" = NetBSD || fail 'run as root on NetBSD'
media=$(cd "$(dirname "$0")" && pwd -P)
cd "$media"
sha256 -c SHA256 || fail 'media checksum mismatch'
release=$(cat release)
state=/var/db/xiri-install
if test ! -d "$state"; then mkdir -m 700 "$state"; fi
test ! -L "$state" && test "$(stat -f '%u:%Lp' "$state")" = 0:700 || fail "unexpected owner or mode on $state"
shlock -f "$state/lock" -p $$ || fail 'another installation is running'
scratch=
cleanup() { test -z "$scratch" || rm -rf "$scratch"; rm -f "$state/lock"; }
trap cleanup EXIT
trap 'exit 1' HUP INT TERM
test ! -e "$state/upgrading" || fail 'resume the pending native upgrade first'
test ! -e "$state/removing" || fail 'finish the interrupted uninstall first'
remember_missing() {
    if test -d "$state/created" && test ! -e "$1" && test ! -L "$1"; then
        mkdir -p "$state/created$1"
    fi
}
owned() { test ! -L "$1" && test -f "$1/.xiri-install-inputs" && cmp -s "$state/inputs" "$1/.xiri-install-inputs"; }
space() {
    directory=$1
    while test ! -d "$directory"; do directory=$(dirname "$directory"); done
    available=$(df -Pk "$directory" | awk 'END {print $4}')
    test "$available" -ge "$2" || fail "$directory needs at least $2 KiB free ($available available)"
}
# Bind a partial install to its input archives. Installer fixes may use new media.
identity="$release $(awk '$2=="(native.tgz)" {print $4}' SHA256) $(awk '$2=="(payload.tgz)" {print $4}' SHA256)"
if test -f "$state/inputs"; then
    test "$(cat "$state/inputs")" = "$identity" || fail 'this target belongs to different input archives'
fi
# Only this installer owns work.* inside its private, locked state directory.
for old in "$state"/work.*; do
    if test -d "$old" && test ! -L "$old"; then rm -rf "$old"; fi
done
read -r native_kib vendor_kib < "$media/space"
if owned /emul/irix && owned /usr/local/share/xiri/fonts; then vendor_kib=0; fi
space "$state" "$((native_kib * 2 + vendor_kib + 8192))"
space /usr "$((native_kib + vendor_kib + 8192))"
space /emul "$((vendor_kib + 8192))"
scratch=$(mktemp -d "$state/work.XXXXXX")
mkdir "$scratch/native"
(cd "$scratch/native" && pax -rzpe -f "$media/native.tgz" && sh preflight.sh)
modstat | grep -Eq '^compat_irix_o32[[:space:]]+exec[[:space:]]+filesys' || fail 'load the matching module at boot'
if test ! -f "$state/inputs"; then
    for dest in /emul/irix /usr/local/share/xiri/fonts; do
        test ! -e "$dest" && test ! -L "$dest" || fail "existing unmanaged $dest"
    done
    printf '%s\n' "$identity" >"$scratch/inputs"
    mkdir -p "$state/created"
    mv "$scratch/inputs" "$state/inputs"
fi
verify_vendor() (
    cd "$1"
    sha256 -c "$media/VENDOR" >"$state/vendor-check.log" || fail "vendor checksum mismatch (see $state/vendor-check.log)"
    original=emul/irix/usr/lib/filetype/desktop.otr
    if test -f "$original.before-xiri"; then original=$original.before-xiri; fi
    test "$(sha256 -q "$original")" = "$(cat "$media/table.sha")" || fail 'original filetype table mismatch'
    while IFS='|' read -r path target; do
        test -L "$path" && test "$(readlink "$path")" = "$target" || fail "catalog or runtime link differs: $path"
    done <"$media/links"
)
if ! owned /emul/irix || ! owned /usr/local/share/xiri/fonts; then
    mkdir "$scratch/vendor"
    (cd "$scratch/vendor" && pax -rzpe -f "$media/payload.tgz")
    verify_vendor "$scratch/vendor"
    for dest in /emul/irix /usr/local/share/xiri/fonts; do
        if owned "$dest"; then continue; fi
        test ! -e "$dest" && test ! -L "$dest" || fail "unmanaged target $dest"
        parent=$(dirname "$dest")
        mkdir -p "$parent"
        tree="$scratch/vendor$dest"
        cp "$state/inputs" "$tree/.xiri-install-inputs"
        # Publish by rename. For a separate /usr, finish copying on that filesystem first.
        if test "$(stat -f %d "$parent")" != "$(stat -f %d "$tree")"; then
            stage=$(mktemp -d "$parent/.xiri-stage.XXXXXX")
            (cd "$tree" && pax -rw -pe . "$stage") || { rm -rf "$stage"; exit 1; }
            tree=$stage
        fi
        mv "$tree" "$dest"
    done
else
    verify_vendor /
fi
echo "Verified IRIX $release files and catalog links."
cd "$scratch/native"
while IFS='|' read -r path kind mode value policy; do
    case "$path" in root/*) dest=/${path#root/};; kernel/*) continue;; *) fail "$path";; esac
    mkdir -p "$(dirname "$dest")"
    remember_missing "$dest"
    if test "$kind" = symlink; then
        if test -L "$dest"; then test "$(readlink "$dest")" = "$value" || fail "$dest"
        else ln -s "$value" "$dest"; fi
        continue
    fi
    if test -L "$dest"; then
        test "$dest" = /usr/X11R7/lib/modules/drivers/newport_drv.so &&
            test "$(readlink "$dest")" = newport_drv.so.0 || fail "unexpected link $dest"
        saved="$state/original$dest"
        mkdir -p "$(dirname "$saved")"
        if test ! -L "$saved"; then ln -s newport_drv.so.0 "$saved"; fi
    elif test -e "$dest"; then
        test -f "$dest" || fail "unexpected type $dest"
        if test "$policy" = preserve-config; then continue; fi
        if test "$(sha256 -q "$dest")" = "$value" && test "$(stat -f %Lp "$dest")" = "${mode#0}"; then continue; fi
        saved="$state/original$dest"
        if test ! -e "$saved" && test ! -L "$saved" && test ! -d "$state/created$dest"; then
            mkdir -p "$(dirname "$saved")"
            cp -p "$dest" "$saved.tmp" && mv "$saved.tmp" "$saved"
        fi
    fi
    new=$(mktemp "$(dirname "$dest")/.xiri-file.XXXXXX")
    install -m "$mode" "$path" "$new" && mv -f "$new" "$dest"
done <files.tsv
sh preflight.sh --verify-installed
if test -L /usr/lib/desktop; then
    test "$(readlink /usr/lib/desktop)" = /emul/irix/usr/lib/desktop || fail 'conflicting /usr/lib/desktop'
else
    test ! -e /usr/lib/desktop || fail 'conflicting /usr/lib/desktop'
    remember_missing /usr/lib/desktop
    ln -s /emul/irix/usr/lib/desktop /usr/lib/desktop
fi
for prefix in adobe freeware; do
    if test -d "/emul/irix/usr/$prefix" && test ! -e "/usr/$prefix" && test ! -L "/usr/$prefix"; then
        remember_missing "/usr/$prefix"
        ln -s "/emul/irix/usr/$prefix" "/usr/$prefix"
    fi
done
mkdir -p /emul/irix/etc
/usr/local/sbin/xiri-sync-users
mkfontdir /usr/local/share/xiri/fonts
remember_missing /usr/bin/nawk
/usr/local/sbin/xiri-update-filetypes
mkdir -p /etc/rc.conf.d
for service in rpcbind xiri_devices xiri_famd xiri_sessions xdm; do
    dest=/etc/rc.conf.d/$service
    if test ! -e "$dest" && test ! -L "$dest"; then
        remember_missing "$dest"
        new=$(mktemp /etc/rc.conf.d/.xiri-service.XXXXXX)
        # Only the enabled settings seed the live configuration. Comments
        # document optional settings in the example across package versions.
        sed '/^#/d' "/usr/local/share/xiri/examples/rc.conf.d/$service" >"$new" &&
            chmod 644 "$new" && mv "$new" "$dest"
    fi
done
cp "$state/inputs" "$scratch/installed" && mv "$scratch/installed" "$state/installed"
echo "Installed IRIX $release. Select the Xiri .xsession for participating users and reboot."
