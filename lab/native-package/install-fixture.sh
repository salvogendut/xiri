#!/bin/sh
# Qualification fixture only: the caller owns a disposable guest, has already
# checked preflight and stopped xdm/FAM/rpcbind. Kernel activation is separate.
set -eu
cd "${1:?unpacked native package directory}"
while IFS='|' read -r path kind mode value policy; do
    case "$path" in root/*) target=/${path#root/};; kernel/*) continue;; *) exit 1;; esac
    if test "$policy" = preserve-config && test -e "$target"; then continue; fi
    install -d -m 755 "$(dirname "$target")"
    case "$kind" in
        file) install -m "$mode" "$path" "$target";;
        symlink)
            if test -L "$target"; then test "$(readlink "$target")" = "$value"
            elif test ! -e "$target"; then ln -s "$value" "$target"
            else echo "Conflicting target: $target" >&2; exit 1; fi;;
        *) exit 1;;
    esac
done <files.tsv
