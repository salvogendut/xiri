#!/usr/bin/env bash
set -euo pipefail

repo_root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
release=NetBSD-11.0
release_url="https://cdn.netbsd.org/pub/NetBSD/$release"
work_dir="$repo_root/.work/netbsd-11.0"
gnupg_home="$work_dir/gnupg"
hashes="$work_dir/${release}_hashes.asc"
key="$work_dir/security-officer@netbsd.org.asc"
fingerprint=271133262BF35CB50D4F504689261E17F5EF49FF
manifest="$work_dir/SHA512SUMS"

mkdir -p "$work_dir"
install -d -m 0700 "$gnupg_home"

curl --fail --location --retry 3 --silent --show-error \
    --output "$hashes.tmp" \
    "https://cdn.netbsd.org/pub/NetBSD/security/hashes/${release}_hashes.asc"
mv "$hashes.tmp" "$hashes"
curl --fail --location --retry 3 --silent --show-error \
    --output "$key.tmp" \
    'https://cdn.netbsd.org/pub/NetBSD/security/PGP/security-officer@netbsd.org.asc'
mv "$key.tmp" "$key"

actual_fingerprint=$(gpg --no-autostart --homedir "$gnupg_home" \
    --show-keys --with-colons "$key" | awk -F: '$1 == "fpr" { print $10; exit }')
[[ "$actual_fingerprint" == "$fingerprint" ]] || {
    printf 'Unexpected NetBSD signing key fingerprint: %s\n' "$actual_fingerprint" >&2
    exit 1
}
gpg --no-autostart --homedir "$gnupg_home" --quiet --import "$key"
signature_status=$(gpg --no-autostart --homedir "$gnupg_home" \
    --status-fd 1 --verify "$hashes" 2>/dev/null)
grep -Fq "[GNUPG:] VALIDSIG $fingerprint " <<< "$signature_status" || {
    printf 'NetBSD release hash signature did not match the expected key.\n' >&2
    exit 1
}
printf 'Verified %s release hash signature with %s\n' "$release" "$fingerprint"

: > "$manifest"
while IFS= read -r relative; do
    [[ -z "$relative" || "$relative" == \#* ]] && continue
    expected=$(awk -v path="${release}/${relative}" \
        '$1 == "SHA512" && $2 == "(" path ")" { print $4; exit }' "$hashes")
    [[ -n "$expected" ]] || {
        printf 'No signed SHA512 hash for %s\n' "$relative" >&2
        exit 1
    }

    destination="$work_dir/$relative"
    mkdir -p "$(dirname "$destination")"
    if [[ ! -f "$destination" ]] || ! printf '%s  %s\n' "$expected" "$destination" | sha512sum --check --status; then
        printf 'Downloading %s\n' "$relative"
        curl --fail --location --retry 3 --continue-at - --silent --show-error \
            --output "$destination.part" "$release_url/$relative"
        printf '%s  %s\n' "$expected" "$destination.part" | sha512sum --check --status || {
            printf 'SHA512 mismatch: %s\n' "$relative" >&2
            exit 1
        }
        mv "$destination.part" "$destination"
    fi

    printf '%s  %s\n' "$expected" "$relative" >> "$manifest"
    printf 'Verified %s\n' "$relative"
done < "$repo_root/lab/netbsd-11.0/files.txt"

cmp -s "$manifest" "$repo_root/lab/netbsd-11.0/SHA512SUMS" || {
    printf 'Downloaded file hashes differ from the pinned Xiri manifest.\n' >&2
    exit 1
}

mkdir -p "$work_dir/tftp"
gzip -dc "$work_dir/sgimips/binary/kernel/netbsd-INSTALL32_IP2x.gz" \
    > "$work_dir/tftp/netbsd-INSTALL32_IP2x"
gzip -dc "$work_dir/sgimips/binary/kernel/netbsd-INSTALL32_IP2x.ecoff.gz" \
    > "$work_dir/tftp/netbsd-INSTALL32_IP2x.ecoff"

printf 'Manifest: %s\n' "$manifest"
printf 'TFTP kernels: %s/tftp/\n' "$work_dir"
