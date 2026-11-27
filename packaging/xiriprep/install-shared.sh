#!/bin/sh
# Install the shared tree once. Both arguments have been identified by xiriprep.
set -eu
PATH=/bin:/sbin:/usr/bin:/usr/sbin:/usr/X11R7/bin
export PATH
umask 022
fail() { echo "xiriprep: $*" >&2; exit 1; }
image=$1 release=$2
case $release in 6.5.22f|6.5.30f) ;; *) exit 2 ;; esac
share=/usr/local/share/xiri
plan=$share/plans/$release.plan
native=$share/desktop-runtime.tgz
state=/var/db/xiri-install
modstat | grep -q '^compat_irix_o32 ' || fail 'boot the XiriBSD kernel with its matching module'
test -s "$plan" && test -s "$native" || fail 'install the complete native xiriprep tools'
test -d "$state" || mkdir -m 700 "$state"
test ! -L "$state" && test "$(stat -f '%u:%Lp' "$state")" = 0:700 || fail "unexpected ownership of $state"
shlock -f "$state/lock" -p $$ || fail 'another desktop installation is running'
work=
cleanup() {
    test -z "$work" || rm -rf "$work"
    rm -f "$state/lock"
}
trap cleanup EXIT
trap 'exit 1' HUP INT TERM
for marker in removing upgrading; do test ! -e "$state/$marker" || fail "pending desktop operation: $marker"; done
# A killed process can leave an unpublished private tree here.
for old in "$state"/donor.*; do
    if test -d "$old" && test ! -L "$old"; then rm -rf "$old"; fi
done
work=$(mktemp -d "$state/donor.XXXXXX")
printf '%s %s %s\n' "$release" "$(sha256 -q "$native")" "$(sha256 -q "$plan")" >"$work/identity"
if test -e "$state/inputs"; then
    cmp -s "$work/identity" "$state/inputs" || fail 'existing desktop belongs to another installation'
fi
owned() {
    test -d "$1" && test ! -L "$1" && cmp -s "$work/identity" "$1/.xiri-install-inputs"
}
need=no
for dest in /emul/irix "$share/fonts"; do
    if ! owned "$dest"; then
        test ! -e "$dest" && test ! -L "$dest" || fail "preserve existing unmanaged $dest"
        need=yes
    fi
done
if test -e /usr/lib/desktop || test -L /usr/lib/desktop; then
    test "$(readlink /usr/lib/desktop)" = /emul/irix/usr/lib/desktop || fail 'conflicting /usr/lib/desktop'
fi
if test "$need" = yes; then
    # The larger qualified plan occupies under 180 MiB including directory
    # fragments. Staging and final trees share blocks when published by rename.
    check_space() {
        dir=$1
        while test ! -d "$dir"; do dir=$(dirname "$dir"); done
        free=$(df -Pk "$dir" | awk 'END {print $4}')
        test "$free" -ge "$2" || fail "$dir needs $2 KiB free ($free available)"
    }
    check_space "$state" 196608
    check_space /emul 188416
    check_space "$share" 8192
    mkdir "$work/tree"
    /usr/local/libexec/xiri/xiri-donor-read --extract "$plan" "$image" "$work/tree"
    cp "$work/identity" "$work/inputs"
    mv "$work/inputs" "$state/inputs"
    for dest in /emul/irix "$share/fonts"; do
        owned "$dest" && continue
        parent=$(dirname "$dest")
        mkdir -p "$parent"
        # Keep interrupted publication on the destination filesystem recoverable.
        stage=$parent/.xiriprep-$(basename "$dest")
        tree="$work/tree$dest"
        cp "$work/identity" "$tree/.xiri-install-inputs"
        if test "$(stat -f %d "$parent")" != "$(stat -f %d "$tree")"; then
            if test -e "$stage" || test -L "$stage"; then
                owned "$stage" || fail "unexpected staging directory $stage"
                rm -rf "$stage"
            fi
            mkdir -m 700 "$stage"
            cp "$work/identity" "$stage/.xiri-install-inputs"
            (cd "$tree" && pax -rw -pe . "$stage")
            chmod 755 "$stage"
            tree=$stage
        fi
        mv "$tree" "$dest"
    done
fi
mkdir "$work/native"
(cd "$work/native" && tar -xzpf "$native")
test -L /usr/lib/desktop || ln -s /emul/irix/usr/lib/desktop /usr/lib/desktop
famd=/usr/local/sbin/famd
if test -e "$famd" || test -L "$famd"; then
    test -f "$famd" && test ! -L "$famd" && cmp -s "$work/native/build/famd" "$famd" ||
        fail "conflicting native daemon at $famd"
else
    install -m 555 "$work/native/build/famd" "$famd"
fi
sh "$work/native/install.sh" --enable-xdm
mkdir -p /emul/irix/etc
mkfontdir "$share/fonts"
# The native installer may already have written just the server flags here.
if ! ( . /etc/rc.subr; load_rc_config xdm; checkyesno xdm ); then
    printf '\nxdm=YES\n' >> /etc/rc.conf.d/xdm
fi
cp "$work/identity" "$work/installed"
mv "$work/installed" "$state/installed"
echo "Installed the shared IRIX $release desktop. Reboot to start its desktop services."
