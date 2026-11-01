# Original 4Dwm on native X

This lab follows the working [winterm shell](../irix-shell/README.md). The
first boundary is the original runtime's SGI_ELFMAP call for libimdUtil's
4 KiB data segment. The [subpage mapper lab](../irix-elfmap-subpage/README.md)
measures that extension separately from window-manager startup.

```sh
PYTHONDONTWRITEBYTECODE=1 python3 scripts/probe-irix-4dwm.py --stage shell
PYTHONDONTWRITEBYTECODE=1 python3 scripts/probe-irix-4dwm.py --stage subpage
```

Both modes clone the stopped, qualified shell guest, verify pinned kernels,
emulator and supplied application/library bytes, and stage the original 4DWm
app defaults, system.4Dwmrc, system.4Dwmdesks and system.backgrounds. Existing
locale/account resources come from the shell seed. The new-kernel attempt uses
native Xvfb and the imported SGI Screen fonts with an explicit environment.

The shell-baseline capture uses the previously qualified native ptrace tracer
to record original ELF-map headers and returns. The new-kernel observation runs
4Dwm as UID1234 under the native shell lab's descendant supervisor, captures
window trees, root properties, the framebuffer and raw kdump evidence, and
verifies native controls and clean shutdown. A captured framebuffer alone does
not prove that a window manager started. Original bytes and raw traces remain
under ignored `.work/irix-4dwm`.

## Interactive acceptance

Use [Chapter 3 of SGI's supplied desktop guidelines](https://techpubs.jurassic.nl/library/manuals/2000/007-2167-006/sgi_html/ch03.html)
as the behavior reference: window decorations and menus, pointer-driven keyboard
focus, minimized windows, desks and session restoration are distinct checks.
After startup, first verify that 4Dwm owns management and reparents a native test
window; then qualify focus and movement with real X input. Combine it with the
working Toolchest and winterm, run a shell command, and capture a real PNG.
Check resize on a native client separately from xwsh's still-unqualified tty
resize path. Desks, restoration, logout and desktop services remain later gates.

The [qualified mapper](../../docs/results/2026-11-01-irix-elfmap-subpage.md) clears the actual original library boundary. The unchanged application next fails in GL initialization: a `/dev/zero` mmap request with address 0, length 4096, protection 3 and flags 0x92 returns EINVAL, then SIGSEGV follows. This is not a working window manager yet. The [before/after record](../../docs/results/2026-11-01-irix-4dwm-loader.json) binds the observations and native controls.

```sh
PYTHONDONTWRITEBYTECODE=1 python3 scripts/qualify-irix-4dwm-loader.py \
  .work/irix-4dwm/runs/shell-ci-mhng43qw \
  .work/irix-4dwm/runs/subpage-ci-x0jv8i9d \
  --output docs/results/2026-11-01-irix-4dwm-loader.json
```

 The first two bring-up
attempts stopped in the native control because the new harness omitted its
input.txt fixture. They halted cleanly and never reached 4Dwm; they are excluded
from application evidence. The corrected harness creates that fixture.

The next two attempts exposed EACCES before application execution because executable destination modes were not explicitly restored. The corrected harness sets every staged ELF to mode 0555. Those staging failures are also excluded.

The [fixed/local mmap checkpoint](../../docs/results/2026-11-01-irix-mmap-local.md)
now removes the GL mapping warning and fault at 0x1050. The native page-zero
guard remains in force for native programs, including after foreign exec.
`probe-irix-4dwm-local.py` checks reparenting, focus, keyboard delivery and
pointer dragging using the original `wmcheck.c` native client; the pre-PRDA
4Dwm faults in libc `_usinit` at the absent PRDA PID field (`0x200e00`) before reparenting, so this is a negative
management check. `probe-irix-4dwm-local-fault.py` captures that subsequent
fault with native tracer controls. Raw frames and disassembly remain private.

## PRDA and readable resource follow-up

The [PRDA checkpoint](../../docs/results/2026-11-01-irix-prda.md) clears the
libc fault. `probe-irix-4dwm-prda.py` retains the exact initial observation:
4Dwm reparents/decorates native clients, but pointer focus fails. Its original
configuration file was unreadable by UID1234 despite matching content hashes.
`probe-irix-4dwm-resources.py` explicitly restores mode 0444 on the four
original files and uses a private UID1234-owned HOME. CI and ordinary execution
both remove the open warning and reach further session-saving activity, but
fail the reparenting bound. The bounded supervisor still cleans up all
processes and native X remains usable.

`probe-irix-4dwm-sessionless.py` isolates window management using explicit
`SG_manageSession: false` and `SG_autoSave: false` resources. This is a diagnostic
configuration; it does not qualify session saving or restoration.
`probe-irix-4dwm-desktop.py` exercises the combined original applications and
native shell handoff. The first attempt reaches the shell handoff but fails
keyboard input while 4Dwm is stalled; it is excluded from desktop acceptance.
Raw captures remain private until a real interactive success is qualified.

The session-saving isolation restores reparenting. Its first check then exposed
a native test-helper error: XGetInputFocus may return the special PointerRoot
value, which cannot be passed to XQueryTree as a window ID. The corrected
`wmcheck-pointer.c` resolves the real pointer's deepest child for that focus
policy, requires it to be the intended client, and still requires delivery of
an actual XTest KeyPress. It never assigns focus itself. Historical `wmcheck.c`
and its recorded failures remain unchanged.

`probe-irix-4dwm-windowtest.py` and
`probe-irix-4dwm-desktop-windowtest.py` use that corrected check. Their combined
session explicitly stages the pinned original XKeysymDB/rgb resources with
readable permissions; the standalone shell seed did not contain the previously
qualified Toolchest keysyms. The terminal's typing helper retains the established
explicit focus request, separately from the window-manager focus test.

The first combined session (`desktop-sessionless-ci-8t6uorae`) passes native
reparenting, pointer focus, actual key delivery, dragging and a command-created
winterm shell marker. The repeated combined run using the corrected focus
helper also passes. See the [application report](../../docs/results/2026-11-01-irix-4dwm.md).
Standalone checks are additionally required to wait for IsViewable: reparenting
can precede mapping. `wmcheck-ready.c` adds that gate without assigning focus;
`probe-irix-4dwm-windowready.py` retains the standalone comparison.

Both readiness-aware standalone runs pass. The first ordinary combined attempt
passed window interaction but captured a three-row winterm and no command
marker. Its geometry/input failure is excluded from acceptance. The final
`probe-irix-4dwm-session.py` uses `session.sh` to finish native drag checks before
releasing original client startup. `type-ready.c` requires a viewable terminal
large enough for the input coordinates, without resizing it. This separates
synthetic movement from concurrently mapping applications and preserves the
known terminal-resize limitation.

The reordered ordinary session passes with a full-height terminal. Its first CI
attempt passes the window tests but leaves xwsh alive without a mapped terminal
or handoff. Startup repeatability is therefore open even when individual
bounded sessions pass. `qualify-irix-4dwm-attempts.py` binds eight intermediate
attempts, including both earlier CI successes and this later failure, without
promoting failed attempts into the accepted interaction matrix.

## Accepted interaction matrix

The unchanged final CI repeat passes, as does ordinary execution. The accepted
matrix contains both readiness-aware standalone runs and both final combined
sessions. It checks eight native ABI and sixteen native controlling-terminal
controls, full descendant cleanup and clean guest halts. The
[qualification](../../docs/results/2026-11-01-irix-4dwm.json) binds the successful
runs and the separate failed-attempt history. Startup repeatability remains open.

```sh
PYTHONDONTWRITEBYTECODE=1 python3 scripts/probe-irix-4dwm-windowready.py
PYTHONDONTWRITEBYTECODE=1 python3 scripts/probe-irix-4dwm-windowready.py --mode ordinary
PYTHONDONTWRITEBYTECODE=1 python3 scripts/probe-irix-4dwm-session.py
PYTHONDONTWRITEBYTECODE=1 python3 scripts/probe-irix-4dwm-session.py --mode ordinary
PYTHONDONTWRITEBYTECODE=1 python3 scripts/qualify-irix-4dwm-windowtest.py \
  .work/irix-4dwm/runs/windowready-ci-5a8k9gfu \
  .work/irix-4dwm/runs/windowready-ordinary-oxrzw7ig \
  .work/irix-4dwm/runs/session-ci-xb3cj1si \
  .work/irix-4dwm/runs/session-ordinary-tr7z_ql2 \
  --output docs/results/2026-11-01-irix-4dwm.json \
  --png docs/results/images/2026-11-01-irix-4dwm-shell.png
```

The PNG comes from ordinary execution and matches the captured XWD pixel for
pixel. Historical harness/helper variants remain frozen to preserve source
hashes for the staged resource fixes and failed attempts. Original binaries,
resource bytes, raw traces, frames and guest disks stay in ignored `.work`.
