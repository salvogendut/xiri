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
`src`, `gnusrc`, `sharesrc`, and `syssrc` source sets for the kernel build.
The manifest also includes `xbase`, `xcomp`, `xetc`, `xfont`, and `xserver`
for Newport qualification. X11 source (`xsrc`) is separate and is not yet
part of the downloaded source baseline.

Downloads and derived files live under `.work/netbsd-11.0/`, outside Git. The
script writes uncompressed ELF and ECOFF install kernels into
`.work/netbsd-11.0/tftp/` for boot experiments. The
[Indy guest lab](../indy-netbsd/README.md) uses these files for the installed
R4400 baseline. See the [input record](../../docs/results/2026-10-29-netbsd-inputs.md)
for verification details and the
[installation record](../../docs/results/2026-10-29-indy-netbsd-install.md)
for boot results.

## Host kernel build

The [XIRI_INDY configuration](XIRI_INDY) inherits `GENERIC32_IP2x`, adds the
identifier `XIRI_INDY_20261030` and debug symbols, and fixes root to `sd0a`
so a kernel loaded over TFTP uses the installed SCSI filesystem.

With the existing `xiri-iris` Toolbox, install the additional native headers
and run the build from the repository root:

```sh
toolbox run -c xiri-iris sudo dnf install -y zlib-devel ncurses-devel
./scripts/build-netbsd-kernel.sh
```

The host also needs `genisoimage`, used to supply a matching kernel file to
the guest. The script verifies all four source archives against the pinned
manifest, extracts them on first use, and builds cross-tools and a kernel
with eight jobs. Override that count with `XIRI_BUILD_JOBS`.

Sources live under `.work/netbsd-11.0/source-tree/`; tools, objects, logs,
and kernel media live under `.work/netbsd-build/`. A source stamp records
the imported archive hashes. An existing unmarked source tree must be moved
aside before automatic preparation; subsequent runs retain local source
edits. The stamp does not certify that an edited tree is unchanged.

For later iterations:

```sh
./scripts/build-netbsd-kernel.sh kernel
```

Use `tools` instead to rebuild only the cross-tools. All modes use NetBSD's
`-u` incremental option. GNU C17 is selected for host C tools because GCC
16's default C23 mode breaks bundled Texinfo and GMP sources; target compiler
flags are separate.

The kernel stage produces:

- `.work/netbsd-11.0/tftp/netbsd-XIRI_INDY`: ELF kernel for PROM/TFTP boot.
- `.work/netbsd-build/obj/sys/arch/sgimips/compile/XIRI_INDY/netbsd.gdb`:
  kernel with full debug information.
- `.work/netbsd-build/kernel.iso`: virtual CD containing the same kernel
  as `/netbsd`, for guest utilities that read kernel symbols from disk.
- `.work/netbsd-build/kernel.sha256`: hashes of these artifacts.

Install the matching kernel as `/netbsd` on the disposable test disk before
the next boot, retaining the release kernel as `/netbsd.release`. Otherwise
utilities such as `savecore` can read incorrect addresses from the old symbol
table. The [build and boot record](../../docs/results/2026-10-30-netbsd-kernel.md)
contains the exact procedure, validation, and measured build times.

## Cross-debugger

Build GDB from the same verified source sets:

```sh
toolbox run -c xiri-iris sudo dnf install -y expat-devel texinfo
./scripts/build-netbsd-kernel.sh gdb
```

This adds `MKCROSSGDB=yes` to the incremental tools build and produces
`.work/netbsd-build/tools/bin/mipseb--netbsd-gdb`. Fedora's packaged GDB
does not include MIPS in the tested version. Expat provides remote target
XML support; the host Texinfo is needed because the bundled older version
cannot build GDB's documentation. Install both before the first GDB build.
The script restores the executable bit on `gdb/make-init-c`, which the
NetBSD 11.0 source set ships as mode 0644.

See the [debugger and probe instructions](../indy-netbsd/README.md#automated-probes).

## Development fork

Guest source changes belong in the sibling
[`NetBSD-nixbench` fork](https://github.com/salvogendut/NetBSD-nixbench), at
`../NetBSD-nixbench`, on a task branch. The inspected clean `trunk` was
`a852b4a0380` (2026-10-30); it is newer than the verified 11.0 source sets.
Do not substitute it silently for the release tree or reuse release object
files for a trunk build. Select and record the branch baseline and use separate
build outputs when a source change is needed. The existing build script still
uses the verified release tree described above.

Xorg's Newport driver lives in NetBSD's separate `xsrc` repository. Kernel and
base-system changes can go into `NetBSD-nixbench`; an Xorg driver change needs
a matching X source checkout as well.
