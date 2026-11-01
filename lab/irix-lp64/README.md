# IRIX o32/n32 on the LP64 Indy kernel

Later checkpoint: [original winterm now runs a native interactive shell](../../docs/results/2026-11-01-irix-shell.md), with measured descriptor/session/exec interfaces and actual keyboard input.

This lab ports the bounded IRIX personality to the qualified LP64 kernel and
adds n32 dispatch, ELF loading and heap growth. It retains the original o32
kernel route. The [result record](../../docs/results/2026-10-30-irix-lp64.md)
records the final application checks, reference differences and scope.

[baseline.json](baseline.json) pins the LP64 kernel, source, emulator and
private inputs. [o32-regression.json](o32-regression.json) pins a separate
32-bit build of the same source, with the established o32 expectations.
[reference.json](reference.json) contains original-IRIX observations for the
same original fixtures and vendor command inputs. No vendor files are stored
in this repository.

## Build

Use the existing `xiri-iris` Toolbox and [native LP64 baseline](../netbsd64/README.md).
The emulator is unchanged from that baseline. Prepare the separate source
worktree once; inspect existing paths before creating anything:

```sh
git -C ../NetBSD-nixbench fetch origin xiri
git -C ../NetBSD-nixbench worktree add --detach "$PWD/.work/netbsd-irix64-src" \
  "$(python3 -c 'import json; print(json.load(open("lab/irix-lp64/baseline.json"))["source_revision"])')"

XIRI_NETBSD_SOURCE_DIR="$PWD/.work/netbsd-irix64-src" \
XIRI_NETBSD_BUILD_DIR="$PWD/.work/netbsd-irix64-build" \
XIRI_NETBSD_TFTP_DIR="$PWD/.work/netbsd-irix64-build/tftp" \
XIRI_NETBSD_CONFIG="$PWD/lab/irix-lp64/XIRI_IRIX_LP64" \
XIRI_NETBSD_ARCH=mips64eb ./scripts/build-netbsd-kernel.sh all

PYTHONDONTWRITEBYTECODE=1 python3 scripts/build-netbsd64-probes.py
PYTHONDONTWRITEBYTECODE=1 python3 scripts/build-irix-lp64.py
```

After tools exist, `kernel` rebuilds just the kernel. Each build directory is
bound to one source path and architecture. Kernel timestamps may change
hashes; review and repin intentional rebuilds before qualification. The PROM
boots the ELF32 wrapper; `/netbsd` must contain the matching native ELF64 file.
The harness checks both hashes and installs the latter.

The LP64 configuration uses GENERIC64_IP2x, COMPAT_NETBSD32 and
COMPAT_IRIX_O32, with 8192-byte pages and fixed sd0a root. Hollywood audio is
excluded as in the native baseline. The historic option name now covers both
foreign ABIs; it does not imply general IRIX compatibility.

## Qualify

Prepare the immutable `.work/indy-netbsd-kernel` disk/NVRAM seed, original
native o32 fixture, native n32/n64 fixtures, and privately extracted asa,
echo, both libc versions and both rld versions from the
[reference media](../irix-reference/README.md).

```sh
export PYTHONDONTWRITEBYTECODE=1
python3 scripts/probe-irix-lp64.py --mode ci
python3 scripts/probe-irix-lp64.py --mode ordinary
python3 scripts/probe-irix-reference-lp64.py
```

Every run uses private disk/NVRAM copies and requires clean shutdown. The
NetBSD harness uses the isolated `.work/target-netbsd64/release` emulator;
the reference uses the existing default emulator and records its hash.
The reference checks disk size and relies on the previously established
intake hash for content identity. It validates runtime and uploaded-fixture
checksums inside IRIX.

Each LP64 run has 243 scenarios: 29 native controls, 87 foreign dispatch and
mapping cases, 32 heap cases, 60 loader cases, one n32 FP case, eight identity
cases, 14 asa cases and 12 echo cases. Both vendor programs run as root and
UID 1234/GID 5678 with original runtime files. The native parent independently
captures stdout, stderr, exec errors, termination and timeout. Heap probes
use a 16 MiB data limit. Traces retain asa and echo startup syscall sequences.
The 133 reference scenarios cover dispatch, heap, FP and the vendor inputs;
they do not claim original IRIX rejects Xiri's narrower loader layouts.

The original assembly uses explicit ABI flags and 32-bit pointers. n32 tests
preserve full-width saved GPRs, exercise register arguments through indirect
mmap, and check FR=1 odd floating-point registers. The current foreign
allowlist has only 32-bit argument and return types. Native wide-seek probes
are native controls, not evidence for IRIX 64-bit syscall support.

Synthetic interpreters validate all auxiliary entries, argc/argv/envp,
string alignment, initialized data and partial/whole BSS. Malformed variants
cover mixed ABIs, header flags/counts, executable entry, overlapping/wrapping
segments and 4 KiB-only alignment. Heap probes cover unaligned growth,
zero-fill after regrowth, retained data, released-page faults, collisions,
data-limit failure and invalid bounds in both direct/indirect forms.

Full logs stay in `.work/irix-lp64-runs/` and
`.work/irix-reference/lp64-runs/`. The result JSON records harness and input
hashes. Generated fixtures, firmware, vendor files, disks and disassembly
remain ignored.

## Preserve the 32-bit route

Build the same source in its own directory and repin the kernel hash and
revision in `o32-regression.json` if intentionally rebuilt:

```sh
XIRI_NETBSD_SOURCE_DIR="$PWD/.work/netbsd-irix64-src" \
XIRI_NETBSD_BUILD_DIR="$PWD/.work/netbsd-irix64-o32-build" \
XIRI_NETBSD_TFTP_DIR="$PWD/.work/netbsd-irix64-o32-build/tftp" \
XIRI_NETBSD_CONFIG="$PWD/lab/irix-lp64/XIRI_IRIX_O32" \
./scripts/build-netbsd-kernel.sh all

export XIRI_IRIS_BIN_DIR="$PWD/.work/target-netbsd64/release"
export PYTHONDONTWRITEBYTECODE=1
for mode in ci ordinary; do
  python3 scripts/probe-irix-runtime.py --suite dispatch --mode "$mode" \
    --pin lab/irix-lp64/o32-regression.json \
    --kernel-directory .work/netbsd-irix64-o32-build/tftp
  python3 scripts/probe-irix-experiment.py --suite dispatch-regressions \
    --expect compat --mode "$mode" \
    --kernel-directory .work/netbsd-irix64-o32-build/tftp \
    --ident XIRI_IRIX_O32_LP64_20261030
done
unset XIRI_IRIS_BIN_DIR
```

These retain the established 148 runtime/dispatch and 89 static/native cases
per mode. Earlier branches and pins remain separately reproducible. The
32-bit kernel continues to reject foreign n32 images.

The subsequent [TCP checkpoint](../irix-tcp/README.md) adds the initial client
transport and reruns this workload with an explicit alternate pin/build directory.
The default commands above retain the earlier LP64 kernel checkpoint.

Latest follow-up: the [legacy recvmsg checkpoint](../irix-recvmsg/README.md)
retains this coverage and adds received-data, fault-consumption and header-output
comparisons. Its [results](../../docs/results/2026-10-31-irix-recvmsg.md) record
the current Toolchest boundary; this lab keeps its historical kernel and expectations.

Active development now uses the consolidated [`xiri` branches](../../docs/FORKS.md).
The former topic names in this lab are historical labels; fetch `xiri` and
check out the exact pinned commit to reproduce this checkpoint.
