#!/bin/sh
# Run only in a disposable, pre-desktop Indy guest. Limit filler writes to tmpfs.
set -eu
export PATH=/bin:/sbin:/usr/bin:/usr/sbin
s=/var/db/xiri-install
rc=/etc/rc.conf.d
examples=/usr/local/share/xiri/examples/rc.conf.d
w=/root/space-check
mkdir -m 700 "$w"
# Keep normal site data and package inputs while exercising a separate target
# filesystem. Refuse to create filler until the mount's device is confirmed.
limited_fs() {
    dest=$1
    mkdir -p "$dest" "$w/seed"
    (cd "$dest" && pax -rw -pe . "$w/seed")
    mount_tmpfs -s 1m tmpfs "$dest"
    test "$(stat -f %d "$dest")" != "$(stat -f %d "$(dirname "$dest")")"
    (cd "$w/seed" && pax -rw -pe . "$dest")
    rm -rf "$w/seed"
}
case "${1:-services}" in
services) limited_fs "$rc";;
payload) mkdir -p "$rc";;
*) exit 2;;
esac
printf '%s\n' 'xiri_famd=YES' '# local service policy' > "$rc/xiri_famd"
su - xiritest -c 'umask 077 && echo "user file" > "$HOME/space-note"'
mkdir -p /etc/xiri
(cd "$w" && pax -rz -f /cdrom/native.tgz root/etc/xiri/fam.conf)
cp "$w/root/etc/xiri/fam.conf" /etc/xiri/fam.conf
echo '# local FAM policy' >> /etc/xiri/fam.conf
files="$rc/xiri_famd /etc/xiri/fam.conf /usr/people/xiritest/space-note /etc/master.passwd /etc/group"
sha256 $files > "$w/site.sha"
stat -f '%i:%u:%g:%Lp %N' $files > "$w/site.stat"
preserved() {
    sha256 -c "$w/site.sha"
    stat -f '%i:%u:%g:%Lp %N' $files | cmp - "$w/site.stat"
}
# The wrapper in the installer shell fills the target only at the chosen
# write. The release CD runs the transaction with the guest's normal tools.
cat > "$w/fill.sh" <<'END'
fill() {
    test ! -e "$limit/.space-fill" || return 0
    test "$(stat -f %d "$limit")" != "$(stat -f %d "$(dirname "$limit")")" || exit 1
    if dd if=/dev/zero of="$limit/.space-fill" bs=4096 count=512 2>"$fill_log"; then exit 1; fi
    grep -qi 'No space left on device' "$fill_log" || exit 1
}
END
if test "${1:-services}" = payload; then
    limit=/usr/local/share/xiri
    limited_fs "$limit"
    export limit fill_log=$w/payload-fill.log
    if sh -c '
        . /root/space-check/fill.sh
        pax() {
            case "${4:-}" in "$limit"/.xiri-stage.*) fill;; esac
            command pax "$@"
        }
        . "$0"
    ' /cdrom/install.sh >"$w/payload-full.log" 2>&1; then
        echo "install incorrectly published a partial font tree" >&2; exit 1
    fi
    grep -i 'No space left on device' "$w/payload-full.log"
    cmp "$s/inputs" /emul/irix/.xiri-install-inputs
    test ! -e "$s/installed"
    test ! -e "$s/lock"
    test ! -e "$limit/fonts"
    test -z "$(find "$limit" -name '.xiri-stage.*' -print)"
    preserved
    rm "$limit/.space-fill"
    sh /cdrom/install.sh >"$w/payload-resume.log" 2>&1
    for receipt in "$s/installed" /emul/irix/.xiri-install-inputs "$limit/fonts/.xiri-install-inputs"; do
        cmp "$s/inputs" "$receipt"
    done
    # mkfontdir refreshes the generated fonts.dir during activation.
    awk '/^SHA256 \(usr\/local\/share\/xiri\/fonts\// && !/\/fonts.dir\)/' /cdrom/VENDOR >"$w/fonts.sha"
    test -s "$w/fonts.sha"
    (cd / && sha256 -c "$w/fonts.sha")
    preserved
    echo 'PASS payload: separate font filesystem filled after IRIX tree publication; retry verified font contents'
    exit 0
fi
export limit=$rc fill_log=$w/install-fill.log
if sh -c '
    . /root/space-check/fill.sh
    sed() {
        case "$2" in /usr/local/share/xiri/examples/rc.conf.d/*) fill;; esac
        command sed "$@"
    }
    . "$0"
' /cdrom/install.sh >"$w/install-full.log" 2>&1; then
    echo "install incorrectly succeeded on a full filesystem" >&2; exit 1
fi
grep -i 'No space left on device' "$w/install-full.log"
grep -F 'could not write /etc/rc.conf.d/' "$w/install-full.log"
test -s "$s/inputs"
test ! -e "$s/installed"
test ! -e "$s/lock"
for tree in /emul/irix /usr/local/share/xiri/fonts; do cmp "$s/inputs" "$tree/.xiri-install-inputs"; done
test -z "$(find "$rc" -name '.xiri-service.*' -print)"
preserved
rm "$rc/.space-fill"
sh /cdrom/install.sh >"$w/install-resume.log" 2>&1
cmp "$s/inputs" "$s/installed"
for service in rpcbind xiri_devices xiri_famd xiri_sessions xdm; do test -s "$rc/$service"; done
cp "$s/installed" "$w/v4"
preserved
echo 'PASS install: full target rejected after tree publication; same-filesystem retry completed'

limited_fs "$examples"
sh /cdrom/upgrade.sh --rollback >"$w/rollback.log" 2>&1
cp "$s/installed" "$w/v3"
! cmp -s "$w/v3" "$w/v4" || exit 1
mkdir "$w/delta"
(cd "$w/delta" && pax -rz -f /cdrom/delta.tgz)
example=$examples/xiri_famd
script=/etc/rc.d/xiri_famd
export limit=$examples fill_log=$w/update-fill.log
if sh -c '
    . /root/space-check/fill.sh
    install() {
        case "$4" in "$limit"/.xiri-upgrade.*) fill;; esac
        command install "$@"
    }
    . "$0"
' /cdrom/upgrade.sh >"$w/update-full.log" 2>&1; then
    echo "upgrade incorrectly succeeded on a full filesystem" >&2; exit 1
fi
grep -i 'No space left on device' "$w/update-full.log"
test -s "$s/upgrading"
test ! -e "$s/lock"
cmp "$s/installed" "$w/v3"
cmp "$script" "$w/delta/new/root$script"
cmp "$example" "$w/delta/old/root$example"
test -z "$(find "$examples" -name '.xiri-upgrade.*' -print)"
preserved
rm "$examples/.space-fill"
sh /cdrom/upgrade.sh >"$w/update-resume.log" 2>&1
sh /cdrom/upgrade.sh >>"$w/update-resume.log" 2>&1
grep -F 'already installed' "$w/update-resume.log"
for receipt in "$s"/installed "$s"/inputs /emul/irix/.xiri-install-inputs /usr/local/share/xiri/fonts/.xiri-install-inputs; do
    cmp "$w/v4" "$receipt"
done
cmp "$example" "$w/delta/new/root$example"
test ! -e "$s/upgrading"
test ! -e "$s/upgrade-progress"
preserved
echo 'PASS upgrade: full target rejected between replacements; same-filesystem retry completed'
