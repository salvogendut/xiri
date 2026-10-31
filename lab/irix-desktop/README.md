# Desktop dependency and startup boundary lab

For the current Toolchest resource boundary, see the [fxstat lab](../irix-fxstat/README.md) and [results](../../docs/results/2026-10-31-irix-fxstat.md). The [session lab](../irix-toolchest/README.md) retains the empty-HOME diagnosis. The [live xclock loader capture](../../docs/results/2026-10-31-irix-xclock-elfmap.md) independently confirms a libXmu/libXaw mapping collision. The inventory and startup experiment below remain the historical baseline.

This checkpoint inventories the supplied n32 4Dwm and Toolchest and measures
their first startup blockers on the unchanged
[qualified LP64 kernel](../irix-lp64/README.md). It does **not** qualify a
working desktop. See the [results](../../docs/results/2026-10-30-irix-desktop-startup.md).

## Inputs and inventory

`manifest.json` contains 29 logical ELF paths (28 distinct files), 124
DT_NEEDED edges and 101 selected resource/service candidates. Its two
program closures contain 25 libraries for 4Dwm and eight for Toolchest.
All library names resolve on the supplied IRIX 6.5.22m image. Native `ldd`
checks those choices separately. The libc aliases account for the duplicate
content; `/usr/lib32/libm.so` resolves to its MIPS III implementation.

The static resolver follows absolute embedded RPATH and the supplied rld
manual's n32 default path:
`/usr/lib32:/usr/lib32/internal:/lib32:/opt/lib32`. It records both DT_NEEDED
and MIPS liblist names, ELF load ranges, ABI flags and hashes. This is a
bounded inventory tool, not a general runtime-linker implementation. Delayed
loading and later `dlopen` modules require separate observation.

The `static_analysis` entries report unaligned load boundaries and overlapping
linked addresses per program. They describe file metadata, not actual runtime
placement. `session.json` summarizes the supplied session scripts and links
each interpretation to the source file's checksum. Resource presence alone
does not establish that a process needs it on the tested path.

Recreate the local inventory with the existing libguestfs installation:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 scripts/inventory-irix-desktop.py
```

This uses a new read-only `ro,norecovery` mount of
`.work/irix-reference/media/irix65.raw`. The source image's size is checked;
its content hash comes from the earlier intake. The daemon closes on exit.
The script writes original files only below `.work/irix-desktop/root` and
metadata to `.work/irix-desktop/inventory.json`. Review a new inventory before
replacing the committed manifest. Firmware, disks, binaries, libraries,
manuals, resources and instruction dumps must stay outside Git.

## NetBSD boundary probe

Prerequisites are the existing LP64 kernel/emulator/input pins, private
vendor extraction, native o32 control and immutable seed disk from the
[LP64 lab](../irix-lp64/README.md), plus the inventory files above.

```sh
export PYTHONDONTWRITEBYTECODE=1
python3 scripts/probe-irix-desktop.py --mode ci
python3 scripts/probe-irix-desktop.py --mode ordinary
```

Each run starts from private disk/NVRAM copies and performs 16 scenarios:

- Native control before and after.
- Asa and echo as root and UID 1234/GID 5678, plus both commands after the
  desktop attempts (six successful vendor controls).
- Both desktop components as root and ordinary user with only libc/rld.
- Both components under both identities after installing the library closure.

Desktop arguments are `-display 127.0.0.1:99`, with an empty environment.
No X server is launched. This selects TCP and an unused display port,
separating the transport boundary from IRIX's local shared-memory X devices.
The existing native runner captures exec errors, stdout, stderr, termination
and a five-second child deadline. User syscall and pathname traces are
required for every desktop attempt. Console text is captured separately:
rld writes some diagnostics through `/dev/tty`, outside the redirected pipes.

The library stage installs unchanged bytes at their original logical paths
under `/emul/irix`; aliases are separate file copies. It does not reproduce
original symlink/inode metadata or install the complete resource/session
configuration. Checksums, native kernel/file/swap controls and clean halt are
mandatory. Asa/echo must continue to succeed.

`expectations.json` pins the **expected blockers**, console text and ordered
syscall/path signatures. Stack addresses and PCs are omitted from signatures;
indirect selectors, syssgi requests and socket domain/type/protocol remain.
A pass means these boundaries and controls reproduced, not that a desktop
ran. Without the pin, the harness records observations for review instead
of qualifying them. Local evidence stays in `.work/irix-desktop-runs/`.

## Original IRIX comparison

```sh
PYTHONDONTWRITEBYTECODE=1 python3 scripts/probe-irix-desktop-reference.py
```

The reference harness uses a disposable image copy and the earlier default
IRIS build. It checks all 29 ELF paths against local extraction using guest
checksums, compares native `ldd` with both static closures, and runs each
program with an empty environment and the same TCP display argument.
Each component runs once directly and once under `par`; echo is the final
control. A 30-second watchdog bounds each launch and `par` has a 20-second
trace limit. Watchdog termination is an incomplete observation and fails
qualification. `reference.json` pins outputs and tracer/command exit codes,
library resolution, and required socket/connect/exit trace markers.

Native direct commands exit 1 because no X server listens on port 6099.
The tracer returns 0; its trace must show the child's `exit(1)` and real
socket creation followed by connection refusal. This establishes the tested
loader/client startup path, not a graphical reference session. Existing XFS
alerts and reference-service warnings remain outside that qualification.
The harness requires clean IRIX shutdown and never commits its overlay.

## Next implementation boundary

Start with Toolchest's TCP path: qualify foreign socket type/address/option
translation and the observed connect/retry calls using original paired
probes, then attempt a connection to a controlled native X server. Socket
failure currently prevents later X connection and event-loop requirements
from being observed. The local-display path additionally exposes gethostname
and IRIX-specific transports; it is not covered by a TCP implementation.

4Dwm also needs mapping support for two 4 KiB-only data boundaries and a
strategy for overlapping library addresses. Preserve rejection and collision
regressions while expanding that contract. Native X/Newport, additional
runtime modules, session services, real desktop interaction and physical
hardware remain separate qualification gates.

The subsequent [TCP checkpoint](../irix-tcp/README.md) implements the initial
transport and reaches successful native X connect followed by unsupported
getsockname. This lab retains the original pre-implementation boundary pins.

The subsequent [getsockname lab](../irix-sockname/README.md) qualifies local-address
output translation against original IRIX. Toolchest now passes that query
after its native X connection and stops at unsupported getpeername (1093).
The earlier boundary pins in this lab remain historical evidence.

The subsequent [getpeername lab](../irix-peername/README.md) now reaches both endpoint queries, followed by unsupported gethostname, fcntl and sendmsg, plus shutdown on cleanup. Use the [desktop acceptance plan](../../docs/ROADMAP.md#milestone-3-original-desktop-proof) and the user-supplied SGI interface guidelines once X applications run.
