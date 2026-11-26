#!/bin/sh
# Register the original desktop menu route after the release's installer bootstrap.
set -eu
export PATH=/bin:/usr/bin:/sbin:/usr/sbin
test "$(id -u)" = 0
cd "$(dirname "$0")"
dest=/usr/local/libexec/xiri-software
entry=/emul/irix/usr/sbin/SoftwareManager
test -s /emul/irix/var/inst/hist && test -x /emul/irix/usr/sbin/swmgr
read -r release rest </var/db/xiri-install/installed
case "$release" in
    6.5.22f) original=910a9298ef1e48e5ef64b11dc5385094dc9959fe0b7e8f856e3e642d7c5f9c86 ;;
    6.5.30f) original=bebf4a5be084974868685cdd8ca65c3afe8ddf6f9eaf7a7b48b44d9dc1557990 ;;
    *) exit 1 ;;
esac
test -f "$entry" && test ! -L "$entry"
alias=/usr/sbin/SoftwareManager
if test -e "$alias" || test -L "$alias"; then
    test -L "$alias" && test "$(readlink "$alias")" = "$entry" || {
        echo "Local launcher already occupies $alias" >&2; exit 1;
    }
fi
install -d -m 755 "$dest"
if test ! -e "$dest/SoftwareManager.sgi"; then
    test "$(sha256 -q "$entry")" = "$original"
    install -m 555 "$entry" "$dest/SoftwareManager.sgi.new"
    mv "$dest/SoftwareManager.sgi.new" "$dest/SoftwareManager.sgi"
fi
test "$(sha256 -q "$dest/SoftwareManager.sgi")" = "$original"
current=$(sha256 -q "$entry")
if test "$current" != "$original" && ! cmp -s software-manager "$entry"; then
    test -f "$dest/launcher.sha256" && test "$current" = "$(cat "$dest/launcher.sha256")" || {
        echo "Local changes in $entry" >&2; exit 1;
    }
fi
for file in authorize manage desktop-artwork.sh; do
    install -m 555 "$file" "$dest/$file.new"
    mv -f "$dest/$file.new" "$dest/$file"
done
install -m 555 software-manager "$entry.xiri-new"
mv -f "$entry.xiri-new" "$entry"
sha256 -q "$entry" >"$dest/launcher.sha256.new"
mv "$dest/launcher.sha256.new" "$dest/launcher.sha256"
if test ! -L "$alias"; then ln -s "$entry" "$alias"; fi
echo 'Software Manager is ready in Toolchest and the DesktopTools catalog.'
