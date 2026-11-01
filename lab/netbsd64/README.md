# Native 64-bit Indy baseline

This lab isolates the LP64 kernel route needed for IRIX n32 work. It builds
`GENERIC64_IP2x` with `COMPAT_NETBSD32`, runs the installed NetBSD 11.0 o32
userland, and exercises original native n32/n64 assembly probes. No IRIX
personality is enabled in this kernel. Vendor asa, echo, 4Dwm and Toolchest
must still fail exec with `ENOEXEC` here.

The [result record](../../docs/results/2026-10-30-netbsd64-native.md) explains
the firmware and emulator fixes, qualification results, and remaining scope.
[baseline.json](baseline.json) pins the source revisions and exact local
artifacts. The successful [o32 asa lab](../irix-o32/README.md#vendor-asa-execution)
keeps its own kernel, emulator build, and inputs.

## Build

Use the existing `xiri-iris` Toolbox, Rust environment and locked dependencies
from the [IRIS lab](../iris/README.md). Prepare separate worktrees from the
user's forks once; if these paths already exist, inspect them instead of
recreating them:

```sh
git -C ../NetBSD-nixbench fetch origin xiri
git -C ../NetBSD-nixbench worktree add --detach "$PWD/.work/netbsd64-src" \
  40d3a490765b8babc8c9cd2aa03a80fa26567320
git -C ../iris fetch origin xiri
git -C ../iris worktree add --detach "$PWD/.work/iris-netbsd64" \
  9df1df14334838a989253efefe26f0547e6da592

./scripts/build-netbsd64-iris.sh

toolbox run -c xiri-iris env \
  RUSTUP_HOME="$PWD/.work/rustup" CARGO_HOME="$PWD/.work/cargo" \
  CARGO_TARGET_DIR="$PWD/.work/target-netbsd64" CARGO_BUILD_JOBS=8 \
  "$PWD/.work/cargo/bin/cargo" +nightly-2026-10-28 test --locked \
  --manifest-path "$PWD/.work/iris-netbsd64/Cargo.toml" --lib cpu::

XIRI_NETBSD_SOURCE_DIR="$PWD/.work/netbsd64-src" \
XIRI_NETBSD_BUILD_DIR="$PWD/.work/netbsd64-build" \
XIRI_NETBSD_TFTP_DIR="$PWD/.work/netbsd64-build/tftp" \
XIRI_NETBSD_CONFIG="$PWD/lab/netbsd64/XIRI_INDY64" \
XIRI_NETBSD_ARCH=mips64eb ./scripts/build-netbsd-kernel.sh all

PYTHONDONTWRITEBYTECODE=1 python3 scripts/build-netbsd64-probes.py
```

After the toolchain exists, `kernel` rebuilds just the kernel. The build
script rejects a reused directory with a different source or target
architecture. `mips64eb` uses the mips64 toolchain; the kernel is n64/LP64,
with 8 KiB pages. The config excludes IP20 Hollywood audio, whose driver
requires 4 KiB pages; this baseline targets the IP24 Indy.

The PROM boots `netbsd.elf32`, an ELF32 wrapper around the 64-bit kernel
payload. The harness installs the native ELF64 `netbsd` as `/netbsd` for
kernel-reading tools. These are distinct files with distinct hashes.
New builds can change timestamps and hashes. Review and repin intended
artifacts before testing; the harness rejects mismatched binaries. Source
changes require a new recorded revision and qualification.

## Run

Prerequisites are the immutable `.work/indy-netbsd-kernel` disk/NVRAM seed,
the existing native o32 fixture, and extracted vendor candidates from the
[reference media](../irix-reference/README.md). Every run uses private copies.

```sh
PYTHONDONTWRITEBYTECODE=1 python3 scripts/probe-netbsd64.py --mode ci
PYTHONDONTWRITEBYTECODE=1 python3 scripts/probe-netbsd64.py --mode ordinary
```

The 33 scenarios cover full-width saved GPRs, FR=1 odd FPRs, wide seek
arguments/returns, private file mapping at a nonzero offset, indirect mmap
using eight argument registers, errors, syscall delay slots, and protected
text in both n32 and n64. The installed compiler builds an o32 compatibility
probe covering file offsets, stat, clock, private mapping/protection, fork,
exec, wait, pipe/poll and a caught signal on an alternate stack, as root and
UID 1234/GID 5678. It also repeats ABI transitions and checks foreign exec
rejection. Native file/swap/kernel controls, checksums and clean shutdown are
required. Successful assembly probes print `XIRI_NATIVE64_OK` and exit 37;
text writes must deliver SIGSEGV. Full logs and result JSON stay in
`.work/netbsd64-runs/`.

The o32 signal test establishes alternate-stack delivery and return, plus
working floating-point arithmetic afterward. It does not establish complete
FPR preservation across signals. Static n64 probes use low virtual addresses;
they do not qualify a complete n64 userland or high-address application maps.

## Emulator regressions

`XIRI_IRIS_BIN_DIR` selects a different emulator and matching CI client for
the shared probe harness. Existing default paths remain unchanged, and each
result records the emulator hash. To retest the qualified o32 kernel with
this emulator:

```sh
export XIRI_IRIS_BIN_DIR="$PWD/.work/target-netbsd64/release"
export PYTHONDONTWRITEBYTECODE=1
python3 scripts/probe-irix-runtime.py --suite dispatch --mode ci
python3 scripts/probe-irix-runtime.py --suite dispatch --mode ordinary
python3 scripts/probe-irix-experiment.py --suite dispatch-regressions \
  --expect compat --mode ci \
  --kernel-directory .work/netbsd-irix-build/dispatch-tftp \
  --ident XIRI_IRIX_DISPATCH_20261030
python3 scripts/probe-irix-experiment.py --suite dispatch-regressions \
  --expect compat --mode ordinary \
  --kernel-directory .work/netbsd-irix-build/dispatch-tftp \
  --ident XIRI_IRIX_DISPATCH_20261030
python3 scripts/probe-irix-reference-dispatch.py
unset XIRI_IRIS_BIN_DIR
```

These require the existing dispatch/reference fixtures. The original IRIX
reference also uses private media copies and its established overlay setup.
No proprietary binaries, firmware, disks, headers or disassembly belong in
Git.

Active development now uses the consolidated [`xiri` branches](../../docs/FORKS.md).
The former topic names in this lab are historical labels; fetch `xiri` and
check out the exact pinned commit to reproduce this checkpoint.
