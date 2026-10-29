# NetBSD 11.0 sgimips inputs — 2026-10-29

## Acquisition and verification

The 16 paths in [`lab/netbsd-11.0/files.txt`](../../lab/netbsd-11.0/files.txt)
were downloaded from the [official NetBSD 11.0 distribution](https://cdn.netbsd.org/pub/NetBSD/NetBSD-11.0/).
They include the Indy IP2x install and generic kernels, six guest sets,
the installation instructions, and four matching source sets. The download
directory uses about 892 MiB. Archives and the full signed hash list remain
under ignored `.work/netbsd-11.0/`.

The release hash list was downloaded from the URL linked on the
[NetBSD 11.0 release page](https://www.netbsd.org/releases/formal-11/).
Its SHA-256 is `07b6c7b1abb5b38c871794dc77114cecbfbe9ca72151a7b50c502a43033bda98`.
The Security Officer key from the same page has fingerprint
`271133262BF35CB50D4F504689261E17F5EF49FF` and file SHA-256
`c5cc5ce722aa878189eb4e9095d22bb309259ffec3ec30abd0799095aa013499`.
GnuPG reported a valid signature from this key. The key was checked in an
isolated keyring; its identity was anchored to the official HTTPS release
page rather than a local web-of-trust certification.

Each file matched the signed SHA-512 value in the release hash list. A second
`sha512sum -c` check passed for all 16 files. The selected values are retained
in [`lab/netbsd-11.0/SHA512SUMS`](../../lab/netbsd-11.0/SHA512SUMS), whose
SHA-256 is `3b528a831cd7fc95a5ed9c9ea14eef2f7a812b864f66e0b7ba567dc85fc5fcfa`.
The [fetch script](../../scripts/fetch-netbsd-11.sh) checks both the signature
and this pinned manifest on future runs.

## Boot inputs prepared

| Derived file in `.work/netbsd-11.0/tftp/` | Format | SHA-256 |
| --- | --- | --- |
| `netbsd-INSTALL32_IP2x` | 32-bit big-endian MIPS ELF | `5112de53767423cbe69ba2442ad89f53819e745647be750a1197026e9efe7fbd` |
| `netbsd-INSTALL32_IP2x.ecoff` | big-endian MIPS ECOFF | `0b9cd4cafc67525ef2c6e3703e0318a514e316560fcd43865b3036ae5306ad35` |

The files were decompressed from verified archives. Both formats are retained
because the [sgimips installation notes](https://cdn.netbsd.org/pub/NetBSD/NetBSD-11.0/sgimips/INSTALL.html)
describe PROM-dependent ELF/ECOFF boot support. IRIS has not booted either
kernel yet. Guest disk, network boot, installation, and modified-kernel tests
remain pending.
