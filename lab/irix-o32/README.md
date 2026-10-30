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

## Vendor interpreter bring-up

The separate `xiri/irix-o32-runtime` fork branch, commit
`64915ea0900cd81e3bc2577504c709fb33051854`, accepts a bounded o32 executable
and its libc interpreter. The [runtime record](../../docs/results/2026-10-30-irix-o32-runtime.md)
describes the accepted layouts, the actual vendor startup boundary, and the n32
kernel route. This does not yet make asa's filter work.

Prepare the supplied media and four vendor candidates using the
[reference lab](../irix-reference/README.md). In addition to `/lib/rld`, extract
the exact interpreter requested by asa; it matches the previously extracted
`/lib/libc.so.1` in this image:

```sh
mkdir -p .work/irix-reference/vendor/usr/lib
LIBGUESTFS_BACKEND=direct \
LIBGUESTFS_CACHEDIR="$PWD/.work/irix-reference/guestfs-cache" \
LIBGUESTFS_TMPDIR="$PWD/.work/irix-reference/tmp" \
guestfish --ro -a "$PWD/.work/irix-reference/media/irix65.raw" \
    -m /dev/sda1:/:ro,norecovery:xfs \
    download /usr/lib/libc.so.1 "$PWD/.work/irix-reference/vendor/usr/lib/libc.so.1"
```

Build from the isolated worktree/toolchain above, preserving the prior kernels:

```sh
git -C "$XIRI_NETBSD_SOURCE_DIR" switch --detach 64915ea0900cd81e3bc2577504c709fb33051854
export XIRI_NETBSD_TFTP_DIR="$XIRI_NETBSD_BUILD_DIR/runtime-tftp"
export XIRI_NETBSD_CONFIG="$PWD/lab/irix-o32/XIRI_IRIX_RUNTIME"
./scripts/build-netbsd-kernel.sh kernel
./scripts/build-irix-experiment.py --segments
python3 scripts/build-irix-runtime.py
for mode in ci ordinary; do
    python3 scripts/probe-irix-runtime.py --mode "$mode"
    ./scripts/probe-irix-experiment.py --suite segments --mode "$mode" --expect compat \
        --kernel-directory "$XIRI_NETBSD_TFTP_DIR" --ident XIRI_IRIX_RUNTIME_20261030
done
```

The runtime harness verifies the kernel and vendor hashes pinned in
[`runtime.json`](runtime.json), and the original vendor candidate manifest.
Each mode uses a disposable disk/NVRAM clone, a native runner compiled with
`-Wall -Wextra -Werror`, bounded direct exec, and separate stdout/stderr/exec-error
pipes. It installs the runtime under `/emul/irix`; NetBSD's emulation-root lookup
has normal native-path fallback and is not a chroot. Originals never leave the
ignored workspace except as copies inside these disposable guests.

The 37 runtime cases cover a synthetic interpreter and repeated execution,
28 malformed executable/interpreter variants, missing interpreter (`ENOENT`),
four unchanged vendor executables, and two native controls. The original
89-case static suite runs separately against the same kernel. Full results and
logs remain under `.work/irix-runtime-runs/` and `.work/irix-experiment-runs/`.
The previous vendor-rejection harness remains pinned to its original kernel.

The synthetic interpreter verifies all seven auxv entries, argument-string
alignment, initial data and zero-fill in both images (with nonzero file poison
after initialized data), writes to private BSS, and transfer to the main entry.
The main fixture prints the 15-byte marker and exits 37. It is original assembly
with a minimal dynamic header, not a test of vendor relocation logic.

For asa in this pinned runtime baseline, passing means successful exec followed
by exactly 44 stderr bytes, exit 239, and the pinned three-call trace: unsupported syscall 1040
`syssgi(SGI_SYSCONF, _SC_CAP)`, write, exit. The return value is IRIX `ENOSYS=89`
by the dispatch implementation. The trace records the call entry; it does not
independently measure the return registers. `rld` has not run. n32 echo, 4Dwm,
and Toolchest still return `ENOEXEC`.

## Runtime capability and identity queries

The `xiri/irix-o32-queries` fork branch, commit
`dc08d65a8e7b3e6cdbd7ca978a200b6f50a42ad5`, extends the runtime baseline with
bounded `syssgi` queries and real/effective UID/GID returns. The
[query record](../../docs/results/2026-10-30-irix-o32-queries.md) documents the
original-IRIX comparison and intentional capability-mode/unsupported-call
differences. Unmodified asa's libc now opens and reads `/lib/rld`, then fails
at unsupported `SGI_ELFMAP`. Neither rld nor asa's filter has executed.

Keep the prepared runtime/segment fixtures and imported vendor files above.
From the isolated NetBSD worktree and toolchain:

```sh
export XIRI_NETBSD_SOURCE_DIR="$PWD/.work/netbsd-irix-src"
export XIRI_NETBSD_BUILD_DIR="$PWD/.work/netbsd-irix-build"
git -C "$XIRI_NETBSD_SOURCE_DIR" switch --detach dc08d65a8e7b3e6cdbd7ca978a200b6f50a42ad5
export XIRI_NETBSD_TFTP_DIR="$XIRI_NETBSD_BUILD_DIR/queries-tftp"
export XIRI_NETBSD_CONFIG="$PWD/lab/irix-o32/XIRI_IRIX_QUERIES"
./scripts/build-netbsd-kernel.sh kernel
./scripts/build-irix-queries.py
for mode in ci ordinary; do
    ./scripts/probe-irix-runtime.py --suite queries --mode "$mode"
    ./scripts/probe-irix-experiment.py --suite segments --mode "$mode" --expect compat \
        --kernel-directory "$XIRI_NETBSD_TFTP_DIR" --ident XIRI_IRIX_QUERIES_20261030
done
```

[`queries.json`](queries.json) pins the committed kernel, unchanged vendor
runtime, 37-byte mapping diagnostic, exit 239, and eleven-call startup trace.
The query suite has 42 cases: the 37 runtime scenarios with the new vendor
boundary, asa under ordinary credentials, and four query executions with
16 records each. The native parent sets real/effective UID/GID and clears
supplementary groups before foreign exec. Profiles are root, user
(UID 1234/GID 5678), effective root with ordinary real IDs, and the reverse.
Only root asa is traced. The 89 static regressions run separately in each mode.
Results and serial logs stay under `.work/irix-queries-runs/` and
`.work/irix-experiment-runs/`. The default `--suite runtime` retains its earlier
kernel and expected capability-query failure.

[`queries.S`](queries.S) is original assembly without libc. Each of its sixteen
64-byte records captures v0, v1, a3, a 24-byte capability buffer, and surrounding
guards. The decoder checks exact byte count, magic, case order, returns,
preservation of v1 outside UID/GID calls, and unchanged guard/poison words.
It covers configuration, identity, unknown requests/attributes, null and bad
pointers, a read-only destination, and the 79/80-character name boundary.

After preparing and bootstrapping the [IRIX reference lab](../irix-reference/README.md),
run the identical binary on a fresh private reference disk/NVRAM clone:

```sh
./scripts/probe-irix-reference-queries.py
```

The harness verifies firmware and probe hashes, checks native asa/libc/rld
checksums against the extracted files, uploads through the scratch device,
and measures root and UID/GID 60001. An extra argument selects the probe's
reference-only setgid/setuid setup; the Xiri runner supplies exactly one argv
entry and uses native credential setup instead. The harness also repeats the
native asa filter control and requires clean shutdown, allowing up to five
minutes for installed third-party services. Its results remain under
`.work/irix-reference/query-runs/`. It checks raw-disk size and relies on the
intake SHA-256 record; it does not rehash the 94 GiB logical image on each run.
No reference overlay is committed, and the existing XFS alerts remain open.

## Bounded rld mapping

Branch `xiri/irix-o32-elfmap`, commit
`755afd768ae96bfde4a52705f1afe0fe1889d068`, adds `SGI_ELFMAP` for two bounded,
linked RX/RW segments. The original rld now executes through asa's libc.
It stops later in allocation after an unsupported indirect `sysmp(MP_PGSIZE)`
query; asa's filter has not run. The [mapping record](../../docs/results/2026-10-30-irix-o32-elfmap.md)
documents the contract, original-IRIX differences, and exact next boundary.

Keep the earlier segment, runtime, and query fixtures and extracted vendor
files. Build the committed source in the isolated worktree:

```sh
export XIRI_NETBSD_SOURCE_DIR="$PWD/.work/netbsd-irix-src"
export XIRI_NETBSD_BUILD_DIR="$PWD/.work/netbsd-irix-build"
git -C "$XIRI_NETBSD_SOURCE_DIR" switch --detach 755afd768ae96bfde4a52705f1afe0fe1889d068
export XIRI_NETBSD_TFTP_DIR="$XIRI_NETBSD_BUILD_DIR/elfmap-tftp"
export XIRI_NETBSD_CONFIG="$PWD/lab/irix-o32/XIRI_IRIX_ELFMAP"
./scripts/build-netbsd-kernel.sh kernel
./scripts/build-irix-elfmap.py
for mode in ci ordinary; do
    ./scripts/probe-irix-runtime.py --suite elfmap --mode "$mode"
    ./scripts/probe-irix-experiment.py --suite segments --mode "$mode" --expect compat \
        --kernel-directory "$XIRI_NETBSD_TFTP_DIR" --ident XIRI_IRIX_ELFMAP_20261030
done
./scripts/probe-irix-reference-elfmap.py
```

The last command requires the prepared [original IRIX reference](../irix-reference/README.md).
It freezes input copies before boot, checks native checksums, transfers an
archive through the scratch device, and runs the same probe and payloads.
[`elfmap-reference.json`](elfmap-reference.json) pins all 43 original observations
and input hashes. Collision relocation addresses may vary: executable bytes,
data/BSS, and preservation of the old mapping are checked by the probe, and
the host requires a distinct aligned user address. Other record fields and
exit statuses must match. Ordinary user setup uses the reference-only
setgid/setuid path, as in the query probe. Shutdown must reach the power-off
marker; no reference overlay is committed. Without a reference pin, the tool
labels its output `observed`, never `passed`.

[`elfmap.S`](elfmap.S) produces one 48-byte record per execution, with v0/v1/a3,
assertion flags, retry results, and an old-data sentinel. Payloads contain a
small executable function, initialized bytes, and nonzero poison immediately
after p_filesz. Positive cases verify code execution and every declared data/BSS
byte. Other cases exercise pure BSS, a full data page plus a partial tail,
private writes and fresh contents after remapping, text/gap faults, two rollback
stages, invalid descriptors/pointers/counts, and malformed layouts. Malformed
reference cases record the syscall result without accessing unvalidated ranges.

The NetBSD suite has 86 top-level cases: the prior 42 runtime/query scenarios
with the new vendor boundary, 42 ELF-map fixtures, an ordinary-user mapping,
and a noexec-mount check. The last check temporarily marks the disposable
guest's virtual CD noexec, opens its unchanged payload through a symlink,
requires EACCES, and restores the mount flags. Native execution, file/swap
controls, unchanged fixture hashes, and clean shutdown remain mandatory.
The 89 static regressions run separately on the same kernel in both modes.

[`elfmap.json`](elfmap.json) pins the kernel, imported runtime, 68-byte rld
diagnostic, exit 1, and sixteen-call vendor trace. Root asa is traced; the
ordinary-user run is not. Passing records this bounded startup result, not
completion of asa's filter. The `runtime` and `queries` suites retain their
earlier kernels and expected failure points. Full logs remain under
`.work/irix-elfmap-runs/`, `.work/irix-experiment-runs/`, and
`.work/irix-reference/elfmap-runs/`.

## Vendor asa execution

Branch `xiri/irix-o32-dispatch`, commit
`6abdd05eca298e29af07d6176ea453e696de90a3`, adds checked one-level indirect
syscalls, the real `sysmp(MP_PGSIZE)` query, and non-fixed mmap hints.
**Unmodified asa now completes its filter using the original libc and rld.**
The [result record](../../docs/results/2026-10-30-irix-o32-dispatch.md) describes
the exact contract, original-IRIX differences, output cases, and remaining
scope. The earlier pinned kernels retain their historical failure boundaries.

Keep the existing runtime/query/ELF-map fixtures, vendor files, installed
NetBSD checkpoint, and prepared original-IRIX reference. Reproduce with:

```sh
export XIRI_NETBSD_SOURCE_DIR="$PWD/.work/netbsd-irix-src"
export XIRI_NETBSD_BUILD_DIR="$PWD/.work/netbsd-irix-build"
git -C "$XIRI_NETBSD_SOURCE_DIR" switch --detach 6abdd05eca298e29af07d6176ea453e696de90a3
export XIRI_NETBSD_TFTP_DIR="$XIRI_NETBSD_BUILD_DIR/dispatch-tftp"
export XIRI_NETBSD_CONFIG="$PWD/lab/irix-o32/XIRI_IRIX_DISPATCH"
./scripts/build-netbsd-kernel.sh kernel
python3 scripts/build-irix-dispatch.py
python3 scripts/build-irix-experiment.py --dispatch
for mode in ci ordinary; do
    python3 scripts/probe-irix-runtime.py --suite dispatch --mode "$mode"
    python3 scripts/probe-irix-experiment.py --suite dispatch-regressions --mode "$mode" \
        --expect compat --kernel-directory "$XIRI_NETBSD_TFTP_DIR" \
        --ident XIRI_IRIX_DISPATCH_20261030
done
python3 scripts/probe-irix-reference-dispatch.py
```

[`dispatch.json`](dispatch.json) pins the kernel, unchanged runtime files,
successful asa result, and 24-call trace. The runtime suite has 148 scenarios:
the prior 86 with the new vendor outcome, 44 dispatcher probes, six indirect
UID/GID credential variants, and six additional asa inputs as root and as an
ordinary user. Every output/error/status is checked; binary records have exact
length and field checks. The 89 static/native executions run separately.
Their version 4 fixture directory is `.work/irix-o32-dispatch-regressions`,
preserving earlier manifests. Conditional assembly changes only the obsolete
indirect-call and nonzero-hint rejection assumptions.

[`dispatch.S`](dispatch.S) uses no libc or vendor code. It exercises argument
shifts through six words, stack faults/overflow, a spill crossing an unmapped
page, delay slots, invalid selectors, identity results, and indirect exit.
Mapping cases check private contents and occupied text/data preservation.
Both direct and indirect sysmp fetch the five-word ABI, including stack
arguments; only MP_PGSIZE is implemented. Hints remain advisory and never
replace mappings. Kernel-space hints are rejected.

The reference harness shares the existing disposable-IRIX boot/transfer/halt
workflow, freezes its input copies before boot, and checks all uploaded
checksums and the installed asa/libc/rld identities. It runs the same 44
executables and seven asa inputs. [`dispatch-reference.json`](dispatch-reference.json)
pins the observations, including intentional ENOSYS/EINVAL and delay-slot
differences. Successful mapping addresses may vary within checked bounds;
content assertions and all other fields must match. Without a pin, results
are labelled `observed`. A clean power-off marker is mandatory for either
observation or qualification.

Results remain under `.work/irix-dispatch-runs/`,
`.work/irix-experiment-runs/`, and `.work/irix-reference/dispatch-runs/`.
This suite qualifies the non-terminal asa filter path, not the other optional
runtime operations that it tolerates as unsupported. n32 and the desktop
remain separate work.
