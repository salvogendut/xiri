#!/bin/sh
set -eu
[ "$#" = 5 ] || { echo 'Usage: package.sh RELEASE DONOR-ROOT SGIVC.so DESKTOP-SOUND OUTPUT.iso' >&2; exit 2; }
rel=$1
case $rel in
    6.5.22f) hash=5d5daccfb4c6ba35ee61ffead3b69397d665777254e18af983c850cc8fa4efef ;;
    6.5.30f) hash=38b46ec4f8e1c1ba1cd2d04788c15074d9be159fa21d752dc903770f49844f0d ;;
    *) exit 2 ;;
esac
test "$(sha256sum < "$2/usr/sbin/ssplay" | cut -d' ' -f1)" = "$hash" ||
    { echo "The donor ssplay does not match $rel." >&2; exit 1; }
here=$(CDPATH= cd -- "$(dirname "$0")" && pwd)
mkdir -p "$(dirname "$5")"
tmp=$(mktemp -d "$(dirname "$5")/.indy-panels.XXXXXXXX")
trap 'rm -rf "$tmp"' EXIT
trap 'exit 1' HUP INT TERM
cdroot=$tmp/cd
mkdir "$cdroot"
cp "$3" "$cdroot/libsgivc.so"
cp "$4" "$cdroot/desktop-sound"
cp "$2/usr/sbin/ssplay" "$cdroot/ssplay"
python3 "$here/prepare.py" "$2/usr/share/data/sounds/soundscheme" "$cdroot/sounds"
cp "$here/install.sh" "$here/../../runtime/libexec/desktop-clients.sh" "$cdroot/"
printf '%s\n' "$rel" > "$cdroot/release"
printf 'Section "Module"\n    Load "sgivc"\nEndSection\n' > "$cdroot/91-xiri-sgivc.conf"
(cd "$cdroot" && sha256sum --tag release install.sh desktop-clients.sh desktop-sound libsgivc.so 91-xiri-sgivc.conf ssplay sounds/* > SHA256)
genisoimage -quiet -R -V XIRI_INDY_PANELS -o "$tmp/update.iso" "$cdroot"
ln "$tmp/update.iso" "$5"
