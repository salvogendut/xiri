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
pointer dragging using the original `wmcheck.c` native client; the current
4Dwm faults in libc `_usinit` at the absent PRDA PID field (`0x200e00`) before reparenting, so this is a negative
management check. `probe-irix-4dwm-local-fault.py` captures that subsequent
fault with native tracer controls. Raw frames and disassembly remain private.
