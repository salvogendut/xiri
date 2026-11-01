# Expanded desktop after limit and executable fixes

Original bgicons now executes, and all four file/icon launches successfully
query `RLIMIT_PTHREAD`. This clears the two startup failures from the
[first attempt](2026-11-01-irix-desktop-components.md). Each launch then reaches
a later pthread-table allocation failure: `mmap(MAP_PRIVATE|MAP_AUTORESRV)`
returns EINVAL. None of the added components yet provides a usable desktop
window.

The [limit/loader result](2026-11-01-irix-rlimit.md) establishes the kernel
contract independently. This [application record](2026-11-01-irix-desktop-startup-fixes.json)
binds the original component manifest, source hashes, kernel pins, traces,
native controls and cleanup. It retains the earlier successful 4Dwm matrix
and the previous failed expanded-session observations unchanged.

## Application observations

The final runs use NetBSD code `e8b037a4639d1683503d34c274fd0f1ec29746b1` and
the existing qualified IRIS build `9df1df14334838a989253efefe26f0547e6da592`.
Both clone the accepted 4Dwm CI seed, install the new kernel and the same
38 ELF paths / 16 resources, and run UID1234 under native Xvfb. The original
fonts, locale, defaults and shell helper remain sufficient for the terminal
control. Session saving stays disabled.

| Launch | Earlier boundary | Current boundary in both modes |
| --- | --- | --- |
| `bgicons -overlay` | Exec rejection | Executes, queries PTHREAD successfully, then mmap EINVAL |
| `fm -b` | PTHREAD query ENOSYS | Query succeeds, then mmap EINVAL |
| `iconcatalog -geometry 420x280+570+400` | PTHREAD query ENOSYS | Query succeeds, then mmap EINVAL |
| `fm "$HOME"` | PTHREAD query ENOSYS | Query succeeds, then mmap EINVAL |

Each trace ends with the same sequence:

1. Trap 1148, selector 8, returns `v0=0, a3=0`.
2. `/dev/zero` opens successfully as descriptor 3.
3. Trap 1134 requests address 0, length `0x160000` (1.375 MiB), protection 3
   and flags `0x102`; it returns `v0=22, a3=1` (EINVAL).
4. The descriptor closes, followed by a 59-byte stderr diagnostic:
   `PANIC pt_bootstrap() Couldn't create pt_table - {0x0, 0x0}`.
5. The process receives SIGSEGV; its waiting shell records status 139.

The archived public NetBSD `irix_mman.h` identifies `0x100` as
`IRIX_MAP_AUTORESRV` and `0x2` as PRIVATE. The current adapter accepts PRIVATE,
FIXED and LOCAL, and rejects the new combination. This is the next measured
application boundary, not evidence that the rest of pthread initialization
already works. Earlier nonfatal missing interfaces remain visible in the
traces. `fmserv` is staged but not directly launched.

## Window and shell controls

| Final run | Native window interaction | Original winterm / native shell |
| --- | --- | --- |
| CI, `ci-lb2342sy` | Reparenting, pointer focus, key delivery and drag pass | Exact typed marker, owned by UID1234 |
| Ordinary, `ordinary-kq787rai` | Same checks pass | Same marker and ownership |

The diagnostic refreshes client/frame coordinates before real XTest pointer
motion, waits 500 ms, then records actual pointer location and input focus.
It permits at most 20 attempts and never assigns focus. Both final runs pass
on attempt zero: target and actual pointer coordinates are (270,230), and
both the pointer leaf and focus are client 6291457. Key delivery succeeds;
dragging moves the client by (50,30). These observations do not establish the
cause of the previous PointerRoot/root failure or long-term repeatability.

The old-kernel comparison `baseline-ci-dt9i9w9o` uses the same final diagnostic
with the previous PRDA kernel. It also passes focus on attempt zero, key
delivery and the (50,30) drag, while reproducing the original application
startup blockers. Focus success therefore does not require the new kernel
changes. The earlier failure remains open with additional instrumentation;
no geometry race or emulator defect is claimed as its established cause.

The separate terminal-input helper explicitly focuses winterm. Its native
handoff reports UID/EUID/GID/EGID1234, no supplementary groups, a native
`/dev/pts/0` controlling terminal, 80×24 dimensions, and matching PID/session/
process-group/foreground-group values. Both commands create exactly
`XIRI_DESKTOP_COMPONENTS_SHELL_OK\n`; native window and shell results are
recorded independently.

Each session retains native ABI controls before and after, native X availability
after the job, and the 120-second supervisor's descendant-absence check. All
qualified guests halt cleanly. Per-PID traces capture first/last 4,000 lines;
overlap in short traces is not an event count. Original bytes, raw framebuffer
captures, full guest traces and disposable disks stay private under `.work`.
The final host process inspection found no remaining IRIS instances.
There is no new usable application to photograph; the earlier
[4Dwm/Toolchest/winterm PNG](images/2026-11-01-irix-4dwm-shell.png) remains the
visual success checkpoint.

## Reproduction and retained attempts

```sh
PYTHONDONTWRITEBYTECODE=1 python3 scripts/probe-irix-desktop-startup-fixes.py
PYTHONDONTWRITEBYTECODE=1 python3 scripts/probe-irix-desktop-startup-fixes.py --mode ordinary
PYTHONDONTWRITEBYTECODE=1 python3 scripts/probe-irix-desktop-startup-fixes.py --diagnostic-baseline
PYTHONDONTWRITEBYTECODE=1 python3 scripts/qualify-irix-desktop-startup-fixes.py \
  .work/irix-desktop-startup-fixes/runs/ci-lb2342sy \
  .work/irix-desktop-startup-fixes/runs/ordinary-kq787rai \
  --baseline .work/irix-desktop-startup-fixes/runs/baseline-ci-dt9i9w9o \
  --output docs/results/2026-11-01-irix-desktop-startup-fixes.json
```

The intermediate `ci-3wia_4nt` run already cleared both initial application
blockers and passed the interaction check, but observed focus after only
100 ms. Its frozen media retains that helper. It is excluded from the final
matrix, which restores the original check's 500 ms interval so a transient
early focus cannot substitute for that observation.

The earlier old-kernel attempt `baseline-ci-zkrszau3` used a 150-second guard
argument that exceeded the helper's 120-second maximum. It failed before
launching the session and therefore provides no focus evidence. Its harness
is retained privately; the argument was corrected before the final runs.
Both intermediate attempts halted cleanly.

## Next boundary

Measure the original `MAP_AUTORESRV` mapping behavior, including observable
allocation, protection and error behavior, before adding its native translation.
Then follow the real pthread initialization path. Continue to record actual
resource lookups before importing artwork, file-type rules or catalog pages;
this mapping failure establishes no new image resource requirement. File
navigation, icon actions, FAM/service behavior, saved sessions, normal exit,
terminal resize/signals and physical-display qualification remain open.

The subsequent [AUTORESRV checkpoint](2026-11-01-irix-mmap-autoresrv.md)
clears this mapping boundary. Its [application follow-up](2026-11-01-irix-desktop-autoresrv.md)
records successful table/fixed mappings followed by unsupported
`prctl(PR_INIT_THREADS)`. This earlier result remains tied to its original pins.
