# Document opening and native application icons — 2026-11-13

This cycle separates document Open actions, drops onto application icons and
drops into running windows. It fixes two shared desktop integration gaps:
loading saved Utilities choices at login, and recognizing native NetBSD
executables as applications. The original IRIX binaries remain unchanged.

## Causes and changes

The original Utilities panel writes shell settings to
`$HOME/.desktop-$(hostname)/desktopenv`. File Manager applies them immediately,
but Xiri did not source the file at the next login. Before the change a fresh
winterm inherited the default Vi command and no `IMGVIEWER`, despite saved
gedit/GIMP choices. After the change it inherits both saved commands. This
follows the supplied IRIX 6.5.22m `Xsession.dt` and runs as the authenticated
user.

IRIX's generic executable rule excludes the MIPS PIC flag, which native
NetBSD PIE executables also use. Its library rule therefore classified native
xedit and xterm as `SharedLibraryExecutable`, without a Drop action. A drop
onto xedit's icon moved the document into the containing folder instead of
launching xedit.

The additive `XiriNetBSDExecutable` rule checks the native interpreter in a
bounded ELF32 big-endian MIPS program-header table and supplies Open/Drop
commands with the original executable artwork. The original `fftr` compiler
builds the combined table. It is the only new imported executable (142,476
bytes); its libraries and the artwork were already present. The installer
keeps the first table for rollback, updates atomically after compilation and
skips unchanged inputs. A deliberately invalid rule returns the original
compiler's syntax error without changing the active table or retaining its
update lock.

## Document and drop observations

| Path | Observation |
| --- | --- |
| Original text Open before choosing an editor | Native Vi runs in original xwsh and displays the complete fixture. |
| Text Open with gedit selected | Original gedit opens the filename with spaces and displays its contents. |
| PDF Open | Original Acrobat 4 displays the bundled Reader guide after its first-run license dialog. |
| PNG Open with GIMP selected | Original GIMP 1.2.5 displays the 96×64 RGB stripe fixture after its original first-run setup. |
| PNG dropped onto the GIMP application icon | GIMP opens the image; the source pathname and hash are unchanged. |
| Text dropped onto native xedit's application icon | With the native rule, xedit displays the document as UID 1234 and leaves the source in place. |
| Text dropped onto the installed gedit icon | No window. The original rule passes `-f`; a direct replay reports `unknown option` and exits 1. |
| Drops into running GIMP and gedit | The repeated visible-window attempts did not open the files. Both advertise drag-receiver support; the protocol/content cause remains unestablished. |

The original text fixture is 44 bytes with SHA-256
`4abcb57ad09ea131ee0092241616675bddbc18dcb93ad55ef022954d5968677b`.
The 179-byte PNG has SHA-256
`b98fe8f345e051a7628c7f174fc246a9c4215f246f98ab19dd4d68ebe7eda4ce`.
The copied Reader guide has SHA-256
`f1bc498f742ca8f72f22cf650a43584494b41e1b2eb24b7e2d8d626eab758c9a`.
None of these checks installs test documents or chosen application defaults
into the manual image.

The original library passes 56 filename/file-descriptor checks over inert
ELF fixtures, including interpreter placement at the first, intermediate and
32nd program headers, non-executable modes, wrong interpreter, class, machine
and byte order, truncated data and out-of-bounds offsets. Real binary controls
identify xedit/xterm as native applications, retain GIMP/gedit's vendor types,
and retain libc's library type. The inert headers are classified as data and never executed.

Exploratory mistakes are retained separately: early double-click coordinates
used the wrong coordinate space, a moved file changed its icon position, and
one running-gedit attempt targeted an unmapped menu window with the same
short title. The repeated visible-window checks use the actual application
titles. A window-tree lookup raced with client exit; the native input helper
now ignores only vanished children during lookup. No kernel crash fix is
claimed from those harness observations.

Three cold-check attempts are excluded from acceptance. The first used fixed
menu coordinates. The second selected a hidden 4Dwm icon window sharing the
Utilities title and returned an input-helper error. The helper now places
and targets only visible clients. In the third attempt End/Return did not
select Other in the option menu; that guest halted cleanly. The maintained
cold regression now writes the original saved-file format through each
user's terminal, separating login-time consumption from the independently
observed Utilities GUI workflow. The second supervisor exited 143 during cleanup; its serial log
records completed shutdown hooks, but clean unmount/halt was not captured.
Its verified orphan process group was stopped and its private disk removed.
None of these attempts is used to qualify the replacement image.

The captured workflows show [native xedit opened by an icon drop](images/2026-11-13-documents-native.png),
[Acrobat displaying the PDF](images/2026-11-13-documents-pdf.png), and
[GIMP displaying the PNG](images/2026-11-13-documents-gimp.png).

## Cold document checks

The [fresh CHD document regression](2026-11-13-documents-cold.json) passes
under both `xiritest` and `xiritest2`. Different saved editor commands survive
logout/login with the correct HOME and UID. Each user cancels a drag without
launching an application or moving the file, then drops the document onto
native xedit and opens it through File Manager. All six before/after file
checks retain the original pathname and hash. Gedit's Copy operation returns
the exact 57-byte first-user fixture. A final first-user login retains its
choice after the second user's session. All five logouts report zero remaining
descendants; the guest halts cleanly and leaves the source CHD unchanged.

The cold probe writes the panel's saved shell format through each user's
winterm. It tests consumption and isolation of saved settings; the original
Utilities panel observations above are separate. Reviewed screenshots show
[gedit's exact content](images/2026-11-13-documents-gedit.png),
[the first user's native drop](images/2026-11-13-documents-native-cold.png),
[the second user's drop](images/2026-11-13-documents-second-user-drop.png), and
[the second user's document Open](images/2026-11-13-documents-second-user-open.png).

The initial desktop run passed its requested checks and halted cleanly, but
[omitted required winterm/font checks](2026-11-13-documents-desktop-incomplete.json).
The image qualifier rejected promotion. The complete image invocation is:

```sh
python3 scripts/probe-xiri-xdm.py --bundle .work/images/xiri-netbsd-desktop-20261113-documents \
    --multiuser --colours --winterm --fonts
```

Two earlier completed host wrappers reported 143 during cleanup, although their
final guest results were saved and clean halt was verified. Recorded owner
and emulator PIDs were absent before retiring the private disks. The host
exit status is retained separately from the guest checks. The final complete
image run exits 0, passes qualification and records a clean halt.

## Manual image

The selected bundle is `.work/images/xiri-netbsd-desktop-20261113-documents/`.
CHD verification, the exact raw-disk round trip, the cold document regression
and the [complete desktop qualification](2026-11-13-documents-image.json) pass.
The full image check includes both IRIX accounts, native ctwm, full-screen
1280×1024 XAA, 345 native text comparisons, three winterm geometry/resize
checks, normal terminal exit, colour aliases, catalog launch, logout/recovery,
saved sessions and clean halt. The source CHD remains unchanged.

Run `./xiri run`, or directly:

```sh
.work/images/xiri-netbsd-desktop-20261113-documents/run-iris.sh
```

Use `xiritest` / `xiritest` or `xiritest2` / `xiritest2` for separate IRIX
desktops, and `netbsdtest` / `netbsdtest` for native ctwm. These remain public
lab credentials. The image does not include the probe documents or its
chosen editor settings. Select your own editor/viewer through Utilities.

The screenshots show the [catalog-launched game](images/2026-11-13-documents-desktop.png),
[untouched winterm](images/2026-11-13-documents-desktop-winterm.png), and
[native ctwm](images/2026-11-13-documents-desktop-native.png).
CHD SHA-256:
`ebe05509864ec21564602939f0c997e40af0752028d2912de1788ee19d04e4e7`.
Prepared raw-disk SHA-256:
`b029a3bb5a07dcd8c8556470b9f6fbf43d6540f8de597edc9ba6a2a7d45fb984`.

The preceding File Manager CHD and manual state are retained. The
[runtime source comparison](2026-11-13-documents-runtime-source.json) matches
all 29 prepared runtime inputs to pushed commit `a499748`, preserving the
original build metadata rather than rewriting its revision.

## Reproduction and remaining work

The [document guide](../IRIX-DOCUMENTS.md) and
[lab](../../lab/documents/README.md) record the supported gestures, preferences,
resource ledger and maintained regression command. Imported rule source hashes
are in [rules.json](../../lab/documents/rules.json). The original compiler
manual, installed SGI session script and linked SGI desktop manuals provide
the reference behavior.

Keep running-window protocol work, gedit's stale Drop action, other document
handlers, printing, personal FTR customization and broader application repair
separate. `imgview` still fails; choosing GIMP is a tested viewer choice.
Shared-memory fallback and existing gedit image/help warnings remain visible.
No NetBSD kernel/module change is needed for this cycle.

IRIS upstream through `9605704cf2a0b204fddc920e6236a3b8050f9e38` is merged into
fork `xiri` as `84125cacb985f974c8f9d81150560150267fb194`. Validation passes
5,539 feature-library tests, 4,852 default-library tests, 32 idle-park checks
and both default CLI builds. The [upstream record](2026-11-13-documents-upstream.json)
retains the exact configuration and ignored counts. Desktop/image checks use
the existing qualified emulator `819c682`, with NetBSD's native-wait core and
`8bf86af` compatibility module; the upstream merge is not a new manual-emulator
qualification.

## Cleanup and host checks

The [cleanup ledger](2026-11-13-documents-cleanup.json) records removal of
21.39 GiB of allocated temporary-file sizes: the upstream test build,
redundant disk decode, extraction cache, completed/failed test disks and
media, and the superseded raw seed. Shared extents mean that total is not
physical space freed. After filesystem sync, available space rose by
20,082,688 bytes (19.15 MiB) over the final cleanup interval; other host
activity prevents attributing that net change solely to this task.

All eight recorded test emulator groups have no active processes. The new
verified raw seed remains at `.work/xiri-image/seed-ebe05509864e/`; the previous
CHD can recreate its retired raw seed if needed. Both manual CHDs, user
overlays/NVRAM, original media, pinned worktrees, logs and screenshots remain.
The 58 host regressions pass. `./xiri doctor`, using the existing direct
Distrobox adapter in this agent environment, verifies 19 immutable artifacts
for the newly selected bundle. Both fork checkouts remain clean on `xiri`.
