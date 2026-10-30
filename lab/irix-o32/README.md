# Static o32 compatibility experiment

This lab supplies original, synthetic MIPS ELF fixtures for IRIX system-call
experiments. The opt-in NetBSD fork kernel executes marked static o32 fixtures
covering arguments, file I/O, private memory mappings, and writable data/BSS.
It contains no vendor
binaries or runtime and does not establish general IRIX application support.
The separate release test retains the original native/rejection baseline.

See the [source audit and implementation plan](../../docs/results/2026-10-30-irix-compat-audit.md)
for the historical references, the [first execution result](../../docs/results/2026-10-30-irix-o32-execution.md),
the [static interface result](../../docs/results/2026-10-30-irix-o32-basics.md),
and the [data/BSS result](../../docs/results/2026-10-30-irix-o32-segments.md)
for the implemented boundary and its limits.

## Release rejection baseline

Prerequisites are the [NetBSD cross-tools](../netbsd-11.0/README.md), the
`xiri-iris` Toolbox, the [custom-kernel checkpoint](../../docs/results/2026-10-30-netbsd-kernel.md),
and the pinned [IRIS build](../iris/README.md). The installed guest must include
the native C compiler. The scripts use the existing lab's paths and networking.

From the Xiri repository:

```sh
./scripts/build-irix-probe.py
./scripts/probe-irix-baseline.py --mode ci
./scripts/probe-irix-baseline.py --mode ordinary
```

The builder uses `mipseb--netbsd-as` and `ld` with big-endian MIPS III/o32
settings. It writes binaries, disassembly, ELF reports, and a hash/tool manifest
under `.work/irix-o32/`. It verifies the ELF class, byte order, architecture,
ABI flags, branding, loadable entry, and absence of an interpreter/dynamic
segment. The unbranded variant omits `PT_NOTE` entirely.

Each guest run gets a fresh disk/NVRAM copy from `.work/indy-netbsd-kernel/`, a
virtual CD containing just the fixtures and runner source, and its own result
directory under `.work/irix-o32-runs/`. The guest verifies the fixture hashes,
compiles the native runner, runs the checks, and halts. Both modes write their
private disk copies directly; this test does not use snapshot restore or CI
disk rollback.

## Fixtures and expected baseline

All three fixtures have a fixed executable load segment at `0x00400000` and
need only a stack and an inherited writable stdout. They attempt to write the
15-byte string `XIRI_ABI_PROBE\n`, check `a3 == 0` and `v0 == 15`, and exit 37.
A failed/short write selects exit 99. No libc, interpreter, TLS, global pointer,
FPU, arguments, environment, or auxiliary-vector contents are consumed.

| Fixture | Identity and calls | Expected result without compatibility |
| --- | --- | --- |
| `native-o32` | NetBSD OSABI, NetBSD version note, calls 4/1 | Exact stdout, exit 37 |
| `irix-o32-marked` | System V OSABI, legacy IRIX o32 flags, Xiri test note, calls 1004/1001 | `execve` fails with `ENOEXEC` |
| `irix-o32-unbranded` | Same foreign ABI and calls, no note | `execve` fails with `ENOEXEC` |

The opt-in note has name `Xiri\0` (`namesz=5`), type `0x49524958`, and a
four-byte big-endian descriptor with value 1. **This is a Xiri test convention,
not an IRIX identification standard.** It permits the experimental loader
to recognize exactly the intended fixture without treating every unbranded
MIPS ELF as IRIX. General vendor-binary recognition is separate work.

[`runner.c`](runner.c) calls `execve` directly so that a shell cannot hide
`ENOEXEC` by trying to interpret the file. A close-on-exec pipe distinguishes
an execution error from a program's exit status; a second pipe captures stdout.
The runner reports errno, byte count, exit status, and terminating signal. Each
fixed, small-output fixture has a bounded wait of approximately 20 guest
seconds. This runner is tailored to these fixtures, not a general subprocess
capture utility.

`BASELINE_PASS native=works irix=ENOEXEC` means all three expected baseline
outcomes occurred. The compatibility mode below expects successful marked
execution and retains the unbranded rejection. Its pass marker is separate
from the release baseline.

## Fork kernel and execution matrix

Source lives on the NetBSD fork's `xiri/irix-o32` branch, initially committed at
`6b6a7967685`, with the working tree under `.work/netbsd-irix-src`. The sibling
fork's primary checkout stays on `trunk`. The unmodified baseline revision is
`a852b4a03800c32a127640b784fcc9fc94159d12`; it reports NetBSD 11.99.9 and uses
NetBSD 11.0 userland on the disposable guest. This is a separate qualification
from the release kernel and Newport X11 profile.

On a fresh lab with the fork commits fetched, reproduce the baseline first:

```sh
git -C ../NetBSD-nixbench worktree add --detach "$PWD/.work/netbsd-irix-src" \
    a852b4a03800c32a127640b784fcc9fc94159d12
export XIRI_NETBSD_SOURCE_DIR="$PWD/.work/netbsd-irix-src"
export XIRI_NETBSD_BUILD_DIR="$PWD/.work/netbsd-irix-build"
export XIRI_NETBSD_TFTP_DIR="$XIRI_NETBSD_BUILD_DIR/baseline-tftp"
export XIRI_NETBSD_CONFIG="$PWD/lab/irix-o32/XIRI_ABI_BASELINE"
./scripts/build-netbsd-kernel.sh all
./scripts/build-irix-experiment.py
for mode in ci ordinary; do
    ./scripts/probe-irix-experiment.py --mode "$mode" --expect baseline \
        --kernel-directory "$XIRI_NETBSD_TFTP_DIR" --ident XIRI_ABI_BASELINE_20261030
done
```

The `all` build creates a separate cross-toolchain. Source/output path stamps
prevent accidental reuse of another tree, and explicit fork builds refuse the
release build/TFTP directories. Build logs record the revision and tracked
patch; stage new source files before a development build so they are included
in that patch. Each kernel configuration has its own object directory.

Then select the committed implementation and enable its option:

```sh
git -C "$XIRI_NETBSD_SOURCE_DIR" switch --detach 6b6a7967685
export XIRI_NETBSD_TFTP_DIR="$XIRI_NETBSD_BUILD_DIR/compat-tftp"
export XIRI_NETBSD_CONFIG="$PWD/lab/irix-o32/XIRI_IRIX_O32"
./scripts/build-netbsd-kernel.sh kernel
for mode in ci ordinary; do
    ./scripts/probe-irix-experiment.py --mode "$mode" --expect compat \
        --kernel-directory "$XIRI_NETBSD_TFTP_DIR" --ident XIRI_IRIX_O32_20261030
done
```

Use unused worktree/output paths if reproducing alongside an existing lab;
these commands are for a fresh setup. Kernel images keep the PROM boot filename
`netbsd-XIRI_INDY` in separate TFTP directories. Every probe cold-boots its
specified image, installs the matching `/netbsd` on a disposable disk, verifies
the identifier and hashes, and runs the original native file/swap smoke check.

The versioned experiment manifest contains 23 fixtures; the runner adds five
marked/native pairs, for 33 cases. `checks.S` tests `EBADF`, `EFAULT`, zero-byte
write, unsupported and indirect numbers, a syscall in a taken branch delay
slot, a bounded infinite loop, and default fault termination. Mutated ELF
headers test note identity/size/bounds, OSABI conflict, n32 flags, ELF64 class,
byte order, PIE, interpreter/dynamic segments, entry, load size, program-header
count, and truncation. They are rejection inputs, not full n32/n64 test programs.

`experiment-runner.c` checks each direct `execve`, exact stdout, exit status,
errno, signal, and forced cleanup. The loop is killed after about three guest
seconds; other cases have approximately 20 guest seconds. Results, serial
logs, configuration, ISO, and disposable disks remain under
`.work/irix-experiment-runs/`. `EXPERIMENT_PASS cases=33` is meaningful together
with the recorded `expect` mode: baseline rejects every foreign fixture,
whereas compat runs the marked fixtures and checks their behavior.

## Static arguments, files, and memory

The follow-up NetBSD branch `xiri/irix-o32-basics`, commit
`c9ab9ccc062650870e17006571c93e665e2133d9`, adds argument setup, read/open/close,
and a bounded private mmap/munmap/mprotect subset. Continue from the isolated
worktree and toolchain setup above, after fetching this branch into the fork:

```sh
git -C "$XIRI_NETBSD_SOURCE_DIR" switch --detach c9ab9ccc062650870e17006571c93e665e2133d9
export XIRI_NETBSD_TFTP_DIR="$XIRI_NETBSD_BUILD_DIR/basics-tftp"
export XIRI_NETBSD_CONFIG="$PWD/lab/irix-o32/XIRI_IRIX_BASIC"
./scripts/build-netbsd-kernel.sh kernel
./scripts/build-irix-experiment.py --basics
for mode in ci ordinary; do
    ./scripts/probe-irix-experiment.py --suite basics --mode "$mode" --expect compat \
        --kernel-directory "$XIRI_NETBSD_TFTP_DIR" --ident XIRI_IRIX_BASIC_20261030
done
```

The builder writes a version 2 manifest and 34 fixtures to `.work/irix-o32-basics/`.
The original 23 fixtures are unchanged; eleven additional programs in
[`basics.S`](basics.S) exercise arguments/environment/static auxv, file effects,
partial/nonblocking transfers, zero-filled and file-backed private mappings,
protection changes, malformed arguments, and access faults. Five marked/native
pairs bring the total to 44 cases. The native parent checks the created file's
contents and permissions; the guest hash check verifies that private mapping
writes leave the backing file unchanged. Both modes must report
`EXPERIMENT_PASS cases=44` and halt cleanly.

Open flags are translated individually, paths use the native guest namespace,
and mmap accepts only a null hint, MAP_PRIVATE, and a nonnegative aligned
32-bit file offset. `/dev/zero` provides zero-filled mappings. Unsupported
flag combinations fail explicitly. The [result record](../../docs/results/2026-10-30-irix-o32-basics.md)
lists the exact supported subset and remaining limits. At that revision the
loader has no writable data/BSS segment or interpreter support; the next
extension below adds data/BSS.

The builder and probe default to the original version 1/minimal suite when
`--basics` and `--suite basics` are omitted. Its earlier kernel and results
remain independently reproducible.

## Writable ELF data and BSS

The `xiri/irix-o32-segments` branch in the NetBSD fork, commit
`6a162a938061d16a60842fd9bb31d69e546d66dc`, extends the static loader
to accept a second, page-separated read/write load segment. The
[segment result record](../../docs/results/2026-10-30-irix-o32-segments.md) pins
the tested commit. Use that revision with the isolated worktree/toolchain
above, then build and probe it as follows:

```sh
git -C "$XIRI_NETBSD_SOURCE_DIR" switch --detach 6a162a938061d16a60842fd9bb31d69e546d66dc
export XIRI_NETBSD_TFTP_DIR="$XIRI_NETBSD_BUILD_DIR/segments-tftp"
export XIRI_NETBSD_CONFIG="$PWD/lab/irix-o32/XIRI_IRIX_SEGMENTS"
./scripts/build-netbsd-kernel.sh kernel
./scripts/build-irix-experiment.py --segments
for mode in ci ordinary; do
    ./scripts/probe-irix-experiment.py --suite segments --mode "$mode" --expect compat \
        --kernel-directory "$XIRI_NETBSD_TFTP_DIR" --ident XIRI_IRIX_SEGMENTS_20261030
done
```

The version 3 manifest in `.work/irix-o32-segments/` includes the unchanged
34 basics fixtures, eight segment programs, and 28 additional rejection inputs.
Five original marked/native pairs and three data/BSS/native triples bring the
matrix to 89 cases. `EXPERIMENT_PASS cases=89`, post-run hashes, and clean
shutdown are required in both modes.

[`segments.S`](segments.S) and [`segments.ld`](segments.ld) cover initialized
data, partial-page BSS, whole BSS pages, pure BSS, page-aligned file data, and
adjacent text/data mappings. Every declared data/BSS byte is checked and then
written; successful programs use BSS as a read/write syscall buffer. A nonzero
file sentinel immediately after initialized data exposes incorrect zero-fill.
Repeated executions check fresh contents, and post-run fixture hashes check
that private writes leave executable files unchanged.

Text-write, gap-read, and end-of-mapping fault fixtures first emit the exact
15-byte marker, then must receive `SIGSEGV`. The `fault-output` expectation
prevents a setup crash from satisfying these checks. The segment end test
accesses the first page after the rounded BSS end, not padding inside its last
page. These tests establish write protection and unmapped-page faults, without
claiming hardware-enforced non-executable data.

The accepted layout is exactly RX text, optional RW data/BSS, then the Xiri
note. Text still starts at `0x00400000` and has equal file/memory size. Data
has nonzero memory size at most 1 MiB, file size no larger than memory size,
page-aligned address/offset, and congruent power-of-two ELF alignment between
one page and 1 MiB. It starts after rounded text and ends at or below
`0x01000000`. File-backed data cannot overlap the text file extent. File bounds,
signed offset limits, wrapping ranges, permissions, and entry-in-text are
checked before the native ELF mapper runs. This bounded image window is a
synthetic test convention; interpreter loading and general IRIX ELF layouts
remain separate work.
