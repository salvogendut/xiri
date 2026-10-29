# NetBSD 11.0 sgimips input baseline

Run [`scripts/fetch-netbsd-11.sh`](../../scripts/fetch-netbsd-11.sh) from the
repository root. It downloads the paths in [`files.txt`](files.txt) from the
[official NetBSD 11.0 release](https://cdn.netbsd.org/pub/NetBSD/NetBSD-11.0/),
checks the release hash list's signature against the NetBSD Security Officer
key linked from the [official release page](https://www.netbsd.org/releases/formal-11/),
and checks each archive's SHA-512 hash. The resulting hashes must also match
the pinned [`SHA512SUMS`](SHA512SUMS) file in this repository.

The selected files are the Indy IP2x install and generic kernels, the
mandatory `base`, `etc`, and `kern-GENERIC32_IP2x` installation sets,
`modules`, `comp`, and `rescue` for the first guest, and the matching
`src`, `gnusrc`, `sharesrc`, and `syssrc` source sets for the later kernel
build. X11 sets and `xsrc` can be fetched when display testing starts.

Downloads and derived files live under `.work/netbsd-11.0/`, outside Git. The
script writes uncompressed ELF and ECOFF install kernels into
`.work/netbsd-11.0/tftp/` for boot experiments. The
[Indy guest lab](../indy-netbsd/README.md) uses these files for the installed
R4400 baseline. See the [input record](../../docs/results/2026-10-29-netbsd-inputs.md)
for verification details and the
[installation record](../../docs/results/2026-10-29-indy-netbsd-install.md)
for boot results.
