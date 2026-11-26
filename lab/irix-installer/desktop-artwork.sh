# Sourced by the SGI Freeware installers. The caller sets root, types, table
# and package and calls artwork_close from its EXIT trap.
art=$root/var/inst/xiri-filetypes
game_state=$root/var/inst/xiri-xmahjongg
zip_state=$root/var/inst/xiri-unzip
own_game_lock=no
own_zip_lock=no
art_opened=no
stage=

artwork_close() {
    if test -n "$stage"; then rm -rf "$stage"; fi
    if test "$art_opened" = yes && test -d "$art"; then artwork_release_base; fi
    if test "$own_zip_lock" = yes; then rm -rf "$zip_state/lock"; fi
    if test "$own_game_lock" = yes; then rm -rf "$game_state/lock"; fi
}

# Walk the old receipts from the live table back to the common starting
# table. Two old installations can be stacked in either order.
legacy_matches() {
    test -f "$1/baseline.otr" || return 1
    for digest in published.sha256 pending.sha256; do
        if test -f "$1/$digest" && test "$(cat "$1/$digest")" = "$2"; then return 0; fi
    done
    test "$(sha256 -q "$1/baseline.otr")" = "$2"
}

artwork_open() {
    mkdir -p -m 700 "$game_state" "$zip_state"
    # These are also the locks taken by the original single-product helpers.
    mkdir "$game_state/lock" || fail "Installer lock in $game_state."
    own_game_lock=yes
    mkdir "$zip_state/lock" || fail "Installer lock in $zip_state."
    own_zip_lock=yes
    stage=$(mktemp -d "$types/.xiri-filetypes.XXXXXX")
    current=$(sha256 -q "$table")
    if test ! -d "$art"; then
        initial=$game_state/lock/receipt
        mkdir -m 700 "$initial"
        source_table=$table
        set -- "$game_state" "$zip_state"
        if legacy_matches "$zip_state" "$current"; then set -- "$zip_state" "$game_state"; fi
        for receipt do
            test -f "$receipt/baseline.otr" || continue
            legacy_matches "$receipt" "$(sha256 -q "$source_table")" || fail "Desktop table differs from the saved receipt in $receipt."
            source_table=$receipt/baseline.otr
            touch "$initial/${receipt##*/xiri-}"
        done
        cp -p "$source_table" "$initial/baseline.otr"
        echo "$current" >"$initial/published.sha256"
        mv "$initial" "$art"
    fi
    if test "$current" != "$(cat "$art/published.sha256")"; then
        test -f "$art/pending.sha256" && test "$current" = "$(cat "$art/pending.sha256")" ||
            fail 'The desktop table changed independently. Review the saved table before continuing.'
    fi
    art_opened=yes
    # The shared receipt is durable before retiring either old snapshot.
    for receipt in "$game_state" "$zip_state"; do
        rm -f "$receipt/baseline.otr" "$receipt/published.sha256" "$receipt/pending.sha256"
    done
}

artwork_release_base() {
    if test ! -e "$art/xmahjongg" && test ! -e "$art/unzip" && test ! -e "$art/gimp"; then
        rm -f "$art/baseline.otr" "$art/published.sha256" "$art/pending.sha256"
        rmdir "$art"
    fi
}

# Rebuild from the installed SGI sources in a fixed order. Put the selected
# types ahead of the original table and preserve that table verbatim when
# the last managed rule is removed.
artwork_publish() {
    set --
    for product in xmahjongg unzip gimp; do
        test -e "$art/$product" || continue
        if test "$package" = "$product" && test "$action" = remove; then continue; fi
        (cd "$types/install" && "$root/usr/sbin/fftr" -o "$stage/$product.otr" "$product.ftr") || fail "Cannot compile $product artwork."
        set -- "$@" "$stage/$product.otr"
    done
    tmp=$stage/desktop.otr
    if test "$#" -eq 0; then cp -p "$art/baseline.otr" "$tmp"
    else
        "$root/usr/sbin/fftr" -o "$tmp" "$@" "$art/baseline.otr"
        test -s "$tmp"
        chmod 444 "$tmp"
    fi
    test "$(sha256 -q "$table")" = "$current" || fail 'The desktop table changed during package maintenance.'
    sha256 -q "$tmp" >"$game_state/lock/next"
    mv "$game_state/lock/next" "$art/pending.sha256"
    mv -f "$tmp" "$table"
    mv "$art/pending.sha256" "$art/published.sha256"
    if test "$action" = remove; then rm -f "$art/$package"; fi
    artwork_release_base
    sha256 "$table"
}
