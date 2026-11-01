# Desktop clients after AUTORESRV support

Original bgicons, background fm, home-directory fm and Icon Catalog now pass
pthread-table allocation. Each then aborts at `prctl(PR_INIT_THREADS)`, which
is still unsupported. This clears the [previous mapping failure](2026-11-01-irix-desktop-startup-fixes.md)
but does not yet produce a usable file/icon desktop.

The [mapping qualification](2026-11-01-irix-mmap-autoresrv.md) independently
checks 1,160 native mapping cases against the original IRIX contract and listed
native policies. This [application record](2026-11-01-irix-desktop-autoresrv.json)
binds the two desktop observations, exact source/kernel pins, original resource
hashes, trace excerpts and controls.

## Observed progress

Both runs use NetBSD code `c11c9f16fad11837a169a3cd566582bebea2c029`, the
qualified IRIS `9df1df14334838a989253efefe26f0547e6da592`, and the unchanged
38-path ELF / 16-resource component inventory. They clone the accepted 4Dwm
seed and install the new kernel. Native Xvfb, UID1234, existing Screen fonts,
explicit session environment and disabled session saving remain unchanged.

Each of the four launches produces this final trace sequence:

| Operation | Result |
| --- | --- |
| `getrlimit(RLIMIT_PTHREAD)` | Success |
| Open `/dev/zero`, O_RDWR | Descriptor 3 |
| `mmap(0, 0x160000, 3, 0x102, ...)` | Success: private AUTORESRV allocation |
| `mmap(returned_address, 0xb0000, 3, 0x12, ...)` | Success at the same address: private fixed mapping |
| Close descriptor 3 | Success |
| Trap 1130, option 20 | `v0=89, a3=1`: IRIX ENOSYS |
| Write diagnostic and terminate | 56-byte INIT_THREADS panic, then SIGSEGV / shell status 139 |

The first allocation is 1.375 MiB; the following fixed mapping covers 704 KiB
at its start. The qualifier verifies successful returns, alignment, foreign
address bounds, and the fixed return matching the first allocation. It does
not infer additional argument meanings from stale argument registers.

The archived public NetBSD headers identify syscall 130 as `prctl` and option
20 as `IRIX_PR_INIT_THREADS`. The original diagnostic is:

```text
PANIC pt_bootstrap() Couldn't INIT_THREADS - {0x0, 0x0}
```

The report binds those headers and the current error map to exact source
revisions. The actual calls establish the next startup boundary; a successful
mapping does not establish working thread initialization or creation.

## Preserved controls

| Run | Native interaction | Original winterm / native shell |
| --- | --- | --- |
| CI, `ci-d484tk__` | Reparenting, pointer focus, key delivery and dragging pass | Typed marker and UID1234 ownership pass |
| Ordinary, `ordinary-uyl51qbn` | Same checks pass | Same shell checks pass |

The native helper uses real pointer/key/button events without assigning focus.
The terminal helper's explicit focus remains separate. Handoff checks retain
UID/EUID/GID/EGID1234, no supplementary groups, native PTY ownership, 80×24
dimensions, and matching session/process-group/foreground-group identities.
The exact command-created marker remains `XIRI_DESKTOP_COMPONENTS_SHELL_OK\n`.
The earlier intermittent focus failure is not claimed to be root-caused by
this mapping change.

Each 120-second session retains native ABI checks before/after, native X
availability afterward, bounded descendant cleanup and clean guest shutdown.
The final host process inspection found no remaining IRIS instances.
Per-PID first/last 4,000-line captures can overlap; their line counts are not
syscall counts. Full guest traces, original files, disks and raw framebuffers
remain private. No new file/icon client reaches a usable window, so the earlier
[4Dwm/Toolchest/winterm PNG](images/2026-11-01-irix-4dwm-shell.png) remains the
visual success checkpoint.

```sh
PYTHONDONTWRITEBYTECODE=1 python3 scripts/probe-irix-desktop-autoresrv.py
PYTHONDONTWRITEBYTECODE=1 python3 scripts/probe-irix-desktop-autoresrv.py --mode ordinary
PYTHONDONTWRITEBYTECODE=1 python3 scripts/qualify-irix-desktop-autoresrv.py \
  .work/irix-desktop-autoresrv/runs/ci-d484tk__ \
  .work/irix-desktop-autoresrv/runs/ordinary-uyl51qbn \
  --output docs/results/2026-11-01-irix-desktop-autoresrv.json
```

## Next implementation boundary

Measure original `prctl(PR_INIT_THREADS)` and the state/lifecycle it establishes,
then implement the corresponding native behavior before following later thread
operations. A successful placeholder return would not establish that contract.
Existing PRDA, fork and signal-mask support should be retained as controls.

No new image resources are established by this kernel initialization failure.
The [resource checklist](../IRIX-RESOURCES.md) continues to track artwork,
file-type rules, catalog pages and services for later actual lookups. `fmserv`
remains staged but untested. File navigation, icon actions, file monitoring,
saved sessions, normal exit, terminal resize/signals and physical-display
qualification remain open.
