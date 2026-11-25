#!/bin/sh
# Install first-run preferences alongside the release-matched Mozilla import.
set -eu
base=${DESTDIR:-}/emul/irix/var/netscape/mozilla
test -x "$base/mozilla-bin" || { echo 'Install the optional Mozilla payload first.' >&2; exit 1; }
if grep -Fq '"rv:1.0.2"' "$base/defaults/pref/all.js" 2>/dev/null; then
    milestone=rv:1.0.2
elif test -f "$base/greprefs/all.js" && test -f "$base/defaults/profile/US/bookmarks.html"; then
    milestone=ignore
else
    echo 'Unrecognized Mozilla profile layout.' >&2; exit 1
fi
tmp=$(mktemp -d "$base/.xiri-defaults.XXXXXX")
trap 'rm -rf "$tmp"' EXIT
trap 'exit 1' HUP INT TERM
cat > "$tmp/xiri-welcome.html" <<'EOF'
<!DOCTYPE html>
<html lang="en"><head><title>Welcome to Xiri</title></head>
<body><h1>Welcome to Xiri</h1>
<p>This IRIX browser is running on NetBSD. This start page is available offline.</p>
<p>To choose another home page, open Edit, Preferences, then Navigator.</p>
</body></html>
EOF
cat > "$tmp/prefs.js" <<EOF
// Mozilla User Preferences

user_pref("browser.startup.homepage", "file:///var/netscape/mozilla/xiri-welcome.html");
user_pref("browser.startup.page", 1);
user_pref("browser.startup.homepage_override.mstone", "$milestone");
EOF
chmod 644 "$tmp/prefs.js" "$tmp/xiri-welcome.html"
# Check all destinations before adding any files. Local templates take precedence.
for dst in "$base/xiri-welcome.html" "$base/defaults/profile/prefs.js" "$base/defaults/profile/US/prefs.js"; do
    test -d "${dst%/*}" || { echo "Missing profile directory: ${dst%/*}" >&2; exit 1; }
    if test -e "$dst" || test -L "$dst"; then
        if test -L "$dst" || ! cmp -s "$tmp/${dst##*/}" "$dst"; then
            echo "Existing file has different contents: $dst" >&2; exit 1
        fi
    fi
done
for dst in "$base/xiri-welcome.html" "$base/defaults/profile/prefs.js" "$base/defaults/profile/US/prefs.js"; do
    # Keep the two locale templates independently editable.
    cp -p "$tmp/${dst##*/}" "$tmp/next"
    ln "$tmp/next" "$dst" 2>/dev/null || {
        test ! -L "$dst" && cmp -s "$tmp/${dst##*/}" "$dst" || exit 1
    }
    rm "$tmp/next"
done
