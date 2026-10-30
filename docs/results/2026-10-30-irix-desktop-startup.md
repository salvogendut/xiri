# Desktop dependencies and first startup blockers — 2026-10-30

Unmodified Toolchest now reaches X display setup on the existing LP64 NetBSD
kernel after its libraries are installed. It stops at the unsupported IRIX
`socket` call. Unmodified 4Dwm reaches its original runtime linker, which
rejects the 4 KiB-aligned data load in `libimdUtil.so`. Neither program has
a working graphical session on Xiri yet.

This step adds an inventory and reproducible boundary tests; it changes no
NetBSD or emulator source. The source remains NetBSD
`0859ba7eb2a784b7f34dd0a52d9e19d32d978898` on `xiri/irix-lp64` and IRIS
`9df1df14334838a989253efefe26f0547e6da592` on `xiri/netbsd64-tlb`.
The [LP64 pin](../../lab/irix-lp64/baseline.json) retains exact kernel and
emulator hashes. The [lab](../../lab/irix-desktop/README.md) gives reproduction
commands; the [JSON record](2026-10-30-irix-desktop-startup.json) retains
observations, trace evidence, source hashes and local log paths.

## Dependency closure

The read-only inventory resolves 29 ELF paths representing 28 distinct files:
two programs, the original n32 rld, 25 needed libraries and a libc alias.
There are 124 DT_NEEDED edges across the inventory. Native IRIX `ldd` returns
zero for both programs and selects exactly the paths found by the static
resolver, including `/usr/lib32/internal` for Indigo Magic libraries.
All candidates are n32; `/usr/lib32/libm.so` resolves to the MIPS III variant.
The [manifest](../../lab/irix-desktop/manifest.json) records every path, alias,
hash, interpreter, dependency and load range.

| Component | Direct libraries | Transitive library set | 8 KiB boundary exceptions | Overlapping library pairs |
| --- | ---: | ---: | ---: | ---: |
| 4Dwm | 12 | 25 | 2 | 11 |
| Toolchest | 7 | 8 | 0 | 0 |

The transitive counts include direct dependencies and libc, excluding the
program and rld. Overlaps are comparisons of linked ELF ranges, not observed
runtime collisions. For example, libXmu and libXt share a linked base address.
The existing mapper only inserts at linked addresses and preserves occupied
mappings; the larger 4Dwm set therefore needs relocation support. Native ldd
marks libgl as delayed for 4Dwm and libgen as delayed for Toolchest. This
inventory does not enumerate every later dlopen module or graphics backend.

Two data segments in 4Dwm's closure have only 4 KiB alignment:

| Library | File offset | Virtual address | Memory bytes | ELF alignment |
| --- | --- | --- | --- | --- |
| internal/libimdUtil.so | `0x11000` | `0x09851000` | `0x2000` | `0x1000` |
| libXpm.so.1 | `0xf000` | `0x0f74f000` | `0x1000` | `0x1000` |

The kernel uses 8 KiB pages. Its current SGI_ELFMAP validation rejects these
unaligned boundaries. This is a known contract limit, not evidence that the
files are corrupt. Future support needs explicit page-offset, permission,
collision, zero-fill and rollback tests; simply removing the checks would
not establish correct mapping behavior.

## Startup observations

The probes install the original libc/rld first, then the complete library
closure, and attempt both desktop programs as root and UID 1234/GID 5678.
They retain empty environments and use `-display 127.0.0.1:99`. No X server
listens on that display. Eight successful native/asa/echo controls surround
eight desktop attempts in each NetBSD run.

| Environment | 4Dwm | Toolchest |
| --- | --- | --- |
| NetBSD, libc/rld only | rld cannot find libimdXutil.so; exit 1 | rld cannot find libXm.so.1; exit 1 |
| NetBSD, library closure installed | rld rejects libimdUtil.so mapping; exit 1 | Reaches TCP socket creation, then reports display-open failure; exit 1 |
| Original IRIX, installed libraries | Creates TCP sockets, connect returns ECONNREFUSED; exit 1 | Creates TCP sockets, connect returns ECONNREFUSED; exit 1 |

The same display error does not mean the same capability passed. Original
IRIX traces show successful `socket(PF_INET, SOCK_STREAM, 0)`, TCP and socket
options, and `connect` to 127.0.0.1:6099 returning IRIX errno 146. Retries use
sginap; both traces reach `exit(1)`. On NetBSD, Toolchest calls trap 1107 with
arguments `(2, 2, 0)`. That trap is absent from the qualified allowlist and
returns ENOSYS; no connect attempt is reached. Foreign socket types and
sockaddr/option layouts need explicit translation, not native passthrough.

4Dwm's trace successfully opens the installed library and calls SGI_ELFMAP
before the libimdUtil diagnostic. Its ELF metadata violates the mapper's
existing page-alignment checks. Rld's fatal message is written to `/dev/tty`,
so the harness captures console diagnostics separately from stdout/stderr.
Its displayed process number is also affected by unsupported getpid. These
optional/cosmetic calls are distinct from the mapping blocker.

An initial local-display (`:99`) diagnostic exposed gethostname and IRIX's
shared-memory/local X transports. The first reference watchdog was too short
for Xlib's retry sequence and interrupted those observations. Those runs are
excluded from qualification. Explicit TCP plus a longer bounded reference
window produced complete native exits and traces. The final reference
tracer exits zero while the traced program exits one; both are checked.

## Resources and services

The inventory also pins 101 selected resource/service paths, including application defaults,
window-manager/menu configuration, XDM scripts, desktop helpers and manuals.
The [session analysis](../../lab/irix-desktop/session.json) summarizes the
supplied scripts without distributing their text:

- Both desktop and xdm are enabled. Xsession selects Xsession.dt, and Xservers
  starts the reference display through `/usr/bin/X11/X`.
- The session configures resources, locale and per-host user state, prepares
  visuals/colormaps, starts 4Dwm with session restoration, waits for it, and
  starts Toolchest on each screen.
- The desktop also includes fm, icon/background helpers, per-user session
  files and reaper-based cleanup. Audio, powersaver, first-login and system
  monitoring helpers are conditional work beyond the two executables.

The NetBSD library-only experiment also attempts X locale and Xt error
resource lookups. The supplied locale alias/directory files are inventoried;
XtErrorDB is absent from the supplied reference path. These lookups should
not be confused with the socket failure. This step does not install a full
resource tree, reproduce original inode/symlink metadata, or run the desktop
session scripts on NetBSD. Fonts, messages, per-user resources, plugins and
service behavior still require runtime qualification.

## Qualification

| Run | Scenarios | Seconds | Result |
| --- | ---: | ---: | --- |
| NetBSD desktop boundaries and controls, ci | 16 | 256.448 | Pass |
| NetBSD desktop boundaries and controls, ordinary | 16 | 261.462 | Pass |
| Original IRIX direct/traced startup and echo, CI | 5 | 317.905 | Pass |

All 37 scenarios across three runs passed, with clean shutdowns. The 16
NetBSD desktop attempts deliberately reproduce startup blockers; the other
16 NetBSD scenarios preserve native and working vendor command controls.

Each NetBSD run checks exact output/termination, console diagnostics, ordered
foreign syscall signatures and relevant pathname sequences. It verifies
input hashes, native kernel/file/swap behavior, working asa and echo before
and after, and clean halt. The reference validates all 29 extracted ELF
paths, both native ldd closures, direct and traced program outputs, required
TCP trace markers and clean shutdown. No original file is patched; all
vendor content and raw traces remain ignored private artifacts.

Passing these tests means that the expected boundaries reproduced. It does
not mean 4Dwm or Toolchest displayed a window. The unchanged kernel retains
its prior [1,093-scenario LP64 qualification](2026-10-30-irix-lp64.md); this
step adds a separate workload and does not count that earlier suite again.

## Next step

Qualify the initial IRIX TCP socket path for Toolchest using paired original
probes, including foreign type/address/option layouts and connect/retry
errors. Then use a controlled native NetBSD X server to expose the next
connection, authentication or event-loop requirement. Toolchest avoids the
additional alignment and linked-address collisions in 4Dwm's current closure.

Handle 4Dwm's mapping boundary with a separate bounded extension and original
comparison. A complete desktop still requires resource/session integration,
working input and application launch, repeated logout/login, a clean
reference graphical session, and physical Indy validation. Existing reference
XFS alerts and native X/Newport limitations remain open.
