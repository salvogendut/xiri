#!/bin/sh
# Build a private, release-matched Indy audio update.
set -eu
test "$#" = 4 || { echo 'Usage: package.sh RELEASE DONOR-ROOT MODULE OUTPUT.iso' >&2; exit 2; }
case $1 in
6.5.22f) player=465f678269978b7be7c442677d7a8605ae830e03ab46b34a23c30ec53fdc865f ;;
6.5.30f) player=39669972548d0f0df0a001dd9b11ebb9605ee5a48fc06daa9e07a5db4af3436b ;;
*) exit 2 ;;
esac
root=$2
test "$(sha256sum < "$root/usr/sbin/sfplay" | cut -d' ' -f1)" = "$player" ||
    { echo "Expected the original $1 sfplay." >&2; exit 1; }
here=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
mkdir -p "$(dirname -- "$4")"
tmp=$(mktemp -d "$(dirname -- "$4")/.indy-pcm.XXXXXXXX")
trap 'rm -rf "$tmp"' EXIT
trap 'exit 1' HUP INT TERM
cdroot=$tmp/cd
mkdir -p "$cdroot/lib32/dmedia/audioconverters"
cp "$3" "$cdroot/compat_irix_o32.kmod"
cp "$root/usr/sbin/sfplay" "$here/install.sh" "$here/xiri_pcm" "$cdroot/"
for lib in audio audiofile awareaudio dmedia m malloc mutex; do
    cp -L "$root/usr/lib32/lib$lib.so" "$cdroot/lib32/"
done
for lib in libC.so.2 libCsup.so dmedia/audioconverters/libaudioconvert.so \
    dmedia/audioconverters/libaudiorateconv.so; do
    cp -L "$root/usr/lib32/$lib" "$cdroot/lib32/$lib"
done
cp "$root/usr/share/data/sounds/soundscheme/soundfiles/emptyDumpster.aiff" "$cdroot/example.aiff"
printf '%s\n' "$1" > "$cdroot/release"
(cd "$cdroot" && sha256sum --tag release example.aiff sfplay install.sh xiri_pcm compat_irix_o32.kmod lib32/*.so lib32/libC.so.2 lib32/dmedia/audioconverters/*.so > SHA256)
genisoimage -quiet -R -V XIRI_PCM -o "$tmp/update.iso" "$cdroot"
ln "$tmp/update.iso" "$4"
