# First expanded IRIX desktop attempt

The first expanded session attempts the original file manager (`fm`), background
icons (`bgicons`) and Icon Catalog alongside 4Dwm, Toolchest and winterm. None of
the added components reaches a usable desktop window. The attempt identifies
two concrete compatibility boundaries: pthread resource-limit initialization
and executable-segment alignment. It does not qualify a complete desktop.

The [lab](../../lab/irix-desktop-components/README.md) contains the extraction
and launch recipes. The [observation record](2026-11-01-irix-desktop-components.json)
binds the two runs, sources, staged hashes, trace excerpts and controls. The
earlier [successful 4Dwm matrix](2026-11-01-irix-4dwm.json) remains unchanged.

## Inputs and scope

Both runs clone the accepted `session-ci-xb3cj1si` disk and retain the qualified
PRDA kernel (`348bd3c8e794f9535e1964bc86d309746e1b576d`) and IRIS
(`9df1df14334838a989253efefe26f0547e6da592`). They use native Xvfb inside the
emulated R4400 Indy, a private UID1234 home, the existing Screen fonts and native
shell handoff, and explicit `SG_manageSession:false` / `SG_autoSave:false`.
No kernel or emulator code was changed for this attempt.

The [new manifest](../../lab/irix-desktop-components/manifest.json) records
38 ELF paths and 16 selected resource files from the supplied image. Static
dependency resolution has no missing entries. Seven libraries extend the
previous 4Dwm/Toolchest closure: libimdModel, libimdApp, libimdIconPanel,
libMediaViewer, libmediaclient, libpthread and librpcsvc. `fmserv` is extracted
and staged as a candidate helper, but not directly launched in this test.
Delayed loads and service behavior remain unqualified.

Resource discovery also locates `/usr/lib/filetype`, its `iconlib`,
`/usr/lib/desktop/iconcatalog/pages`, `/usr/lib/images` (235 top-level entries)
and `/usr/lib/X11/schemes` (31). Their contents are not yet staged. The 16
selected defaults include candidates matched by broad file/icon/desktop
patterns; this count is not a claim that every file is needed. Original vendor
bytes remain under ignored `.work`.

The launch choices follow the supplied Xsession.dt/startdesktop evidence and
[SGI's desktop overview](https://techpubs.jurassic.nl/library/manuals/2000/007-2167-006/sgi_html/ch01.html).
File navigation, icon actions and catalog behavior must be tested after startup.
[SGI's service description](https://techpubs.jurassic.nl/library/manuals/2000/007-2167-006/sgi_html/ch04.html)
also makes file-change notifications a later behavioral requirement; this
attempt does not yet establish a FAM protocol or service implementation.

## Observed startup boundaries

| Launch | Outcome | Evidence |
| --- | --- | --- |
| `fm -b` | Pthread bootstrap panic, SIGSEGV, shell status 139 | `getrlimit` syscall 1148 with resource 8 returns IRIX error 89 |
| `fm "$HOME"` | Same panic and termination | Same resource-limit call and return |
| `iconcatalog -geometry 420x280+570+400` | Same panic and termination | Same resource-limit call and return |
| `bgicons -overlay` | Native shell reports “Cannot execute ELF binary”, status 2 | No foreign syscall records; its RW segment has `p_align=4096` |

The first three traces show a lookup of the staged `libpthread.so`, then
`getrlimit(8, ...)` returning `v0=0x59, a3=1`, a 63-byte write to stderr and
SIGSEGV. The diagnostic is `PANIC pt_bootstrap() Couldn't get initial rlimits -
{0x0, 0x0}`. The audited historical NetBSD IRIX headers identify resource 8 as
`IRIX_RLIMIT_PTHREAD` and syscall 148 (1148 in the traced convention) as
`getrlimit`; the current error map identifies 89 as `IRIX_ENOSYS`. The current
dispatcher has no handler for it. Earlier unsuccessful calls in library
initialization are retained in the traces; this is the immediate fatal boundary,
not proof that all preceding behavior is implemented.

`bgicons` has an RX segment at `0x10000000`, offset 0, alignment 8192; its RW
segment is at `0x10016000`, offset `0x6000`, alignment 4096. Both addresses and
offsets are aligned to the guest's 8 KiB page size. The current
`irix_o32_runtime_image` validator nevertheless requires every PT_LOAD's
declared alignment to be at least PAGE_SIZE, so this header fails that check.
This is the executable-loading path; the previously qualified SGI_ELFMAP
library subpage support does not change it. The probe captures the shell's
rejection, not the native exec errno or a live breakpoint at the validator.

For the naming/layout evidence, see the [historical source audit](2026-10-30-irix-compat-audit.md)
and its archived `irix_resource.h`, `irix_resource.c` and `irix_syscall.h`.
That historical resource adapter itself rejects PTHREAD, so copying it would
not resolve this observed startup failure.

## Controls and limitations

Each expanded session has a 120-second native supervisor. It records component
PIDs, exit status, diagnostics and first/last 4000 lines of per-PID kdump output,
plus the process list, X window tree and framebuffer before cleanup. Short
trace captures overlap; their line counts are not event counts. The full guest
trace hash is recorded, and its bytes remain in the disposable disk.

The native-window test runs before Toolchest/winterm and the new components.
Both runs map and reparent its two windows, then fail the focus check with
`WMCHECK_STATUS=5`: PointerRoot resolves to the root (841), rather than the
expected client. Key delivery and dragging are therefore not reached in this
helper invocation. The focus failure needs separate investigation; it cannot
be attributed to the added programs, which have not started yet. These runs
do not extend the successful window interaction matrix.

| Mode and run | New components | Terminal command | Other controls |
| --- | --- | --- | --- |
| CI, `ci-hbta8m3o` | Three pthread panics and one exec rejection | Native UID1234 handoff; exact command-created marker | Native ABI before/after, X after, descendant cleanup and clean halt pass |
| Ordinary, `ordinary-hzy8u164` | Same failures | Same handoff identities and marker | Same controls pass |

The independent observation qualifier verifies all eight component outcomes,
the two terminal command markers, four native ABI controls, native X availability
after each job and descendant cleanup. Both guests halted cleanly. A final host
process inspection found no remaining IRIS instances. The successful terminal
input does not turn the failed pointer-focus checks into passes.

The raw frame remains available privately. Since no new desktop component
succeeds, no new PNG is presented as a full-desktop success. The earlier
[4Dwm/Toolchest/winterm PNG](images/2026-11-01-irix-4dwm-shell.png) remains the
successful visual checkpoint. Saved sessions, desks, directory navigation,
icon actions, file notifications and logout remain open, as do the existing
terminal signal/resize/normal-exit and physical-display limitations.

## Next implementation cycle

1. Measure original IRIX `getrlimit` behavior, including PTHREAD, supported
   layouts, error paths and inheritance. Implement and test the corresponding
   resource-limit contract in NetBSD `xiri`; a successful query alone will not
   establish working pthread creation or synchronization.
2. Extend the bounded executable loader for the measured `bgicons` layout,
   retaining checks for segment overlap, file bounds, protections and invalid
   alignment. Repeat the original binary and existing loader regressions.
3. Re-run these components, then follow their actual file-type, artwork,
   catalog and service lookups. Keep the working terminal controls and address
   saved-session filesystem operations before qualifying restoration/logout.

IRIS upstream was checked at cycle start: `upstream/main` was
`f17b4d3bc1663efd02f93a5e0e4811eebba510c8`, already contained in `origin/xiri`
`182efc8171f915be2152426819da8d05507c06c9`. No new integration was necessary.
This observation continues to use the older qualified emulator pin.

The subsequent [resource-limit/loader checkpoint](2026-11-01-irix-rlimit.md)
implements and tests the first two items. Its [application follow-up](2026-11-01-irix-desktop-startup-fixes.md)
clears both original startup blockers and records the later pthread-table
mapping failure. This earlier observation and its failures remain unchanged.
