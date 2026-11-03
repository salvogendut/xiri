# Winterm startup, resize and normal shell exit

The new manual CHD uses readable SGI bitmap text, propagates terminal resizes
and closes winterm normally when its shell exits. The
[fresh-image qualification](2026-11-03-winterm-image.json) passes three IRIX
logins, a native ctwm login, both original logout menus, catalog launching,
rendering and clean halt. The underlying native Type1 metric failure remains
open; the bitmap selection avoids that font path.

Run `./xiri run` from the repository. Log in as `xiritest` / `xiritest` for
4Dwm or `netbsdtest` / `netbsdtest` for ctwm. The wheel-account image remains
preserved as an earlier control. PNGs show
[winterm before any test resize](images/2026-11-03-winterm-image-winterm.png),
[the desktop and catalog launch](images/2026-11-03-winterm-image.png),
[ctwm](images/2026-11-03-winterm-image-native.png) and
[the greeter](images/2026-11-03-winterm-image-greeter.png).

## Findings

The disposable graphical run `.work/winterm-cycle/explore-mioetniq` boots the
preserved wheel-account CHD and logs in through xdm as xiritest. Unlike earlier interaction
checks, it does not resize winterm before recording its initial geometry.
Its first launch has 983×504 pixels and 12×21 resize increments. Additional
default Courier, exact SGI Screen and fixed-font launches report respectively
12×21, 8×15 and 6×13 increments. The collapsed-text problem did not reproduce
in this initial run; a later cold boot below captures it.

The imported XWsh defaults request a wildcard 20-pixel bold Courier font.
Native and original IRIX Xlib, talking to the same Xorg server, both select
IBM Courier and report 12×21 logical extents, ascent 17 and descent 4 over
six create/free cycles. IRIX Xlib includes the same face twice in its font
set, but its text widths and extents match native Xlib. SGI Screen and fixed
fonts remain available. At this stage font selection was only a lead; the
later failing-session controls identify a bad server-side Type1 face.

Before the fix, resizing winterm changes its X window from 983×504 to 815×441,
but native `stty size` remains `24 80`. The trace records IRIX ioctl
`0x80087467` on the PTY master returning ENOSYS. The native shell handoff also
overwrites the PTY dimensions with 80×24. The replacement implements the two
measured window-size selectors and preserves initialized dimensions during
handoff. Native tty code owns synchronization and SIGWINCH delivery.

Before the fix, typed `exit` ends the native shells, but four test xwsh processes remain and
spin on PTY EOF/write errors. They were explicitly stopped. An earlier empty
process query was caused by unsupported `ps` syntax, not successful exit.
The trace shows SIGCHLD registration rejected with EOPNOTSUPP before fork.
Original IRIX's `signal(SIGCHLD, handler)` requests flags `0x20012`, including
`SA_NOCLDSTOP=0x20000`. The adapter rejected that flag. The replacement maps
it to native SA_NOCLDSTOP and retains it in queried foreign metadata;
SA_NOCLDWAIT remains unsupported. PTY EOF itself is zero bytes on both systems.

## Original-system controls

Independent fixtures use the supplied IRIX 6.5.22m installation's headers and
libraries, or original libc-free code cross-compiled with the existing GNU
toolchain. No leaked sources are used. Libc reference run `ci-lexr5u8r` and the corrected raw-fixture run
`ci-5an50s0l` record:

- `TIOCGWINSZ=0x40087468`, `TIOCSWINSZ=0x80087467`; an eight-byte structure of
  four unsigned 16-bit fields, shared between PTY master and slave.
- Zero and maximum dimensions, invalid descriptors, regular files, `/dev/null`,
  null/unaligned/high pointers, page-boundary faults and read-only mappings.
  A failed get crossing an inaccessible page leaves the accessible prefix
  unchanged; a failed set leaves the previous dimensions unchanged.
- 31 raw ioctl observations × o32/n32 × direct/indirect dispatch × root/UID1234
  (248 observations), plus paired master/slave libc controls under n32.
- 24 child-exit fixtures spanning both ABIs, both dispatch paths, both users
  and legacy/siginfo/one-shot handler forms with NOCLDSTOP.
- n32 libc stop/continue/exit controls under root and UID1234: NOCLDSTOP
  suppresses stop notifications while retaining a waitable exit status 37.
  Without it, stop and continue notifications are also observed.

The early `ci-5mdf2y85` and `ci-lffxzww8` attempts failed compilation because
neither MAP_ANONYMOUS nor MAP_ANON was available in the installed headers.
Both are excluded. The corrected fixture maps `/dev/zero`. An initial raw
signal run used the older kernel-register trampoline and is also excluded;
`ci-5an50s0l` reruns the interrupt-safe v2 trampoline. Both successful reference
guests and the original NetBSD exploratory guest halted cleanly. The installed
GCC's o32 assembler path also fails, so the o32 controls use independently
built libc-free fixtures rather than the unavailable native compiler.

## Build and qualification

NetBSD source starts at `9390bc04900` on `xiri`. The module is rebuilt in
`.work/netbsd-winterm-build`, a separate reflink copy of the qualified xdm
build. Only compatibility module sources change; the core kernel, its boot
wrapper and configuration remain byte-identical. The module import and
relocation audit passes. Runtime shell handoff builds natively in the guest.
The paired ABI checks and exploratory graphical desktops pass the resize
and normal-exit controls. The fresh bitmap-default CHD passes the complete
login cycle with untouched geometry checks, foreground resize and normal
terminal exit. The
module sources are committed as `4f3d8a183ea` on NetBSD `xiri`;
[source-equivalence.json](../../lab/irix-winterm-reliability/source-equivalence.json)
verifies every recorded source against that commit. The core kernel stays at
the qualified `9390bc04900` build. The native shell-handoff source is committed
in this repository as `1afbc35`; its bytes match the prepared image's runtime
source inventory.

IRIS upstream was checked at `28fa516684c54e00e35b258c65e5dcac3a36165c`,
already in integration `ae62114`; no integration was needed. The tests retain
the image's pinned `819c682` emulator. Qualified images and detached source
worktrees remain unchanged.

The paired raw tests now pass on NetBSD: all 248 ioctl records match byte for
byte, and all 24 NOCLDSTOP signal/frame controls pass the independent decoder.
The [ABI qualification record](2026-11-03-winterm-abi.json) includes the fixture
source/executable hashes and decoded observations.
Both n32 libc master/slave size controls also complete successfully. Native
launchers set test credentials before foreign exec; passing the IRIX identity
argument directly would invoke intentionally unsupported capability setters
and was rejected as fixture setup, not an ioctl failure.

An exploratory n32 libc stop/continue test is excluded from NetBSD acceptance:
its unchecked `usleep()` calls hit unsupported `nanosleep` syscall 1077, removing its delay
and racing SIGCONT against the child's self-stop. One run stalled and was
interrupted; a bounded traced repeat completed and exposed the missing delay.
The fixture now fails explicitly on an unsupported delay. The original IRIX
observations use the pre-guard source retained with the private build archive.
NetBSD also sends a continued-child notification with native SA_NOCLDSTOP where
the IRIX observation suppresses it. This cycle qualifies child exit handling;
full continued-child notification parity and the n32 libc sleep interface remain
follow-up work. No stopped fixture processes were left running.

Before the bitmap default, a healthy Courier window settles at 80×24 with
12×21 font cells. Its native handoff can precede final layout and report 78 columns, followed by xwsh's
window-size update to 80; this is not a lost resize. A foreground native job
receives SIGWINCH and measures 66×21 after resizing. A second terminal opens
at 100×30, preserves its nondefault initial size and reports 30 rows/100 columns
through `stty size`. Typing `exit` closes its X window and exits zero. The
launching native interactive shell may retain the dead background child until
its next input; the check explicitly waits for it and then requires the PID
to be gone. No forced signal is needed to close the terminal.

## Reusable image and reproduction

The replacement bitmap-default bundle is
`.work/images/xiri-netbsd-desktop-20261103-winterm-v2/`, prepared by the
maintained script in `ordinary-bvihrws9` with `--keep-accounts`. Preparation
verified boot-loaded module/service state, a 1280×1024 greeter and clean halt.
The source raw disk stayed unchanged. Its CHD is 481,236,546 bytes, SHA256
`ebecbb0d0c87ae9a58bb58bdc008011cbe1bcea8d4a062a0649f1d7ddf796a65`.
Extraction matches the prepared 8 GiB disk exactly, SHA256
`55538d1edd69280dbf888f50e01c6ef41217556fc06c01ce92047c80b0d9ce51`.
The installed font-resource SHA256 is
`3f47bbfaa04d7094c052d619f8c48aee2745378cf47406c2e2e29cf0e20d36aa`.
The native helper and module retain the hashes listed with the initial
module-only candidate below.

The initial module-only candidate was
`.work/images/xiri-netbsd-desktop-20261103-winterm/`. It is **not qualified**:
the third cold boot reproduced the font collapse. Its CHD has 481,201,508
bytes and SHA256
`f9a09a4fc470ca0041bfc2ea2a1670de012910e76499ecd075c2d7db75da355b`.
The decoded 8 GiB disk matches the prepared source exactly, with SHA256
`228161ab264dd15caf0c59e821eb1d2e1f354640a570beb5e5bdd311f1df5982`.
The module SHA256 is
`e775398868484a306897d9c07ebd85f56d39687e4ebb9357d0c1a53fed198f47`;
the installed native shell helper is
`cea28f5592845d4c79532918c8928952670263dc453274a1766f482ae2971175`.

For that initial candidate, the seed derives from the preserved wheel-account
CHD. Preparation used a
disposable ordinary graphical guest (`ordinary-3s9w06m4`) and retained the
account files, including netbsdtest's wheel membership. An interactive wrapper
around the maintained preparation script kept that guest available for the
bounded diagnostics above. Its original measured result is retained separately;
after committing the module, source-equivalence metadata was added without
changing the measured artifact hashes. The build manifest still records the
actual parent revision and dirty module files used during the build.

The maintained preparation command for a fresh copy of that seed is:

```sh
python3 scripts/prepare-xiri-xdm-image.py \
  --seed .work/xiri-image/prepared-seed-20261103-wheel \
  --kernel-build .work/netbsd-winterm-build \
  --baseline lab/irix-winterm-reliability/image-baseline.json --keep-accounts
```

Build into a new directory using its result as `--seed-run`, then run:

```sh
python3 scripts/probe-xiri-xdm.py \
  --bundle .work/images/xiri-netbsd-desktop-20261103-winterm-v2 --winterm
```

The check captures winterm before any test resize, measures the foreground
job's dimensions and SIGWINCH, and requires an extra terminal to exit zero
without a forced signal. It also repeats the established full-screen xdm,
4Dwm/ctwm, catalog launch, pixel rendering, logout and service-ownership checks.
This cycle's host regression suite passes all 37 tests; the module and native
helpers build with the required warning checks.

No new IRIX fonts or resources are required. GIMP needs a fresh application
check after the SIGCHLD change; this cycle does not claim it now works.

The first cold-CHD run, `ordinary-nnv6z9mp`, is retained but excluded from
promotion. Two untouched winterm starts/resizes, the extra terminal's normal
exit, both logout menus and failed-startup recovery passed. The native user's
terminal recorded the correct identity/home and `netbsdtest wheel`; however,
the harness then tried to parse a cached startup `pgrep` result containing
two PIDs as one integer. The native desktop was visible and responsive. The
guest halted cleanly and its base CHD stayed unchanged.

That PID list had been captured before ctwm finished starting. Its
[configuration parser forks before executing m4](https://github.com/NetBSD/xsrc/blob/trunk/external/mit/ctwm/dist/parse_m4.c),
so a transient child sharing the command line is a plausible explanation;
the failed run did not record those processes' parent/state fields. The
corrected check retains the early list, refreshes it after the managed
terminal is usable, requires exactly one live ctwm process and records its
parent/state. It still requires all of that native user's processes to end
on logout. The complete fresh-CHD cycle is rerun with this stricter observation.

The second run, `ordinary-sn2txie0`, is also excluded from promotion. It
confirmed a transient startup list (PIDs 4257 and 1489) settling to a single
manager, but the added diagnostic used GNU-style comma-separated empty `ps`
headings. NetBSD interpreted the remainder as one heading, so the assertion
rejected the output. A live debug request verified the corrected native
`ps -o pid,ppid,stat,comm` form: PID 1489, parent 3709, state `Is`, command
`/usr/X11R7/bin/ctwm`. The parser now removes the normal header and accepts
the observed full command path. The guest was asked to halt cleanly before
another complete fresh-CHD run. Neither test-harness correction changes the
packaged kernel, module, runtime or CHD.

## Reproduced font collapse and bitmap default

The third cold-CHD run, `ordinary-6emvlxse`, rejects the first untouched
winterm at 983×72 pixels with 12×2 resize increments. Its native handoff
reports 36 rows/78 columns. The failure PNG and diagnostic emulator snapshot
are retained; the snapshot has not been qualified for restoration. This run
is excluded from image promotion.

The default wildcard selects
`-ibm-courier-bold-r-normal--20-145-100-100-m-110-iso8859-1`, supplied by
NetBSD's `/usr/X11R7/lib/X11/fonts/Type1/courb.pfa`. Both native and original
IRIX Xlib observe ascent 1, descent 1 and logical extents 12×2 over six
create/free cycles. Their successful earlier observation was ascent 17,
descent 4 and 12×21. Thus the current failure is visible to native clients
too; the precise Type1/scaling/cache defect is not yet localized.

On the same failing X server, the already imported
`-sgi-screen-medium-r-normal--15-150-72-72-m-80-iso8859-1` bitmap stays at
ascent 11, descent 4 and 8×15 in both libraries. A new original xwsh using
that face opens at 663×360 with readable text while the original Courier
terminal remains collapsed. The failed terminal was enlarged only to drive
the diagnostic keyboard helper; the new bitmap terminal was measured before
any resize. Its font selection, rather than that diagnostic enlargement,
changes its metrics.

The runtime now installs `/etc/xiri/Xresources` and merges these terminal
defaults below the login's existing resource values. Administrators can edit
the file or select another via `xiri_xresources`; reinstallation preserves
local configuration and updates the `.example`. No additional IRIX fonts or
libraries are imported. The replacement image carries this resource
selection as well as the module and shell-handoff changes; it does not claim
to repair the underlying native Type1 failure.

The [font diagnostic record](2026-11-03-winterm-fonts.json) retains the raw
native/IRIX metrics, original probe and diagnostic-script hashes, resource
precedence control and five completed bitmap-terminal size/exit controls.
Its [untouched failure PNG](images/2026-11-03-winterm-font-collapsed.png)
shows the collapsed Courier terminal; the
[bitmap comparison](images/2026-11-03-winterm-font-bitmap.png) shows readable
SGI text on that same X server. The older terminal was enlarged to permit
the input helper; that enlargement did not fix its Courier metrics.

The extended diagnostic also exposed automated-input failures. The fifth
launch's serial completion exceeded its original 120-second deadline; its
zero-status marker arrived later. Its first size command contained a doubled
hyphen in the output pathname, confirmed by the screenshot and guest file
listing. A separately recorded continuation completed that terminal's size
and normal-exit checks. The sixth terminal had correct 100×30 startup and
8×15 cells, but repeated `D` characters corrupted `XIRI_SESSION_DIR`; the
[screenshot](images/2026-11-03-winterm-font-input-failure.png) shows the
resulting permission error. That sixth input/exit attempt is excluded.
These failures occurred during the extended concurrent-guest diagnostic;
their cause is not localized and concurrency is not established as causal.
The fresh-image qualification remains a separate complete run with its
normal keyboard assertions intact. Existing explicit font resources survive
the default merge, verified with a `fixed` override and an unrelated resource.

The font diagnostic guest then halted cleanly, unmounted its filesystems and
left the module-only base CHD unchanged. The private HTTP transfer server was
stopped. The independent fresh-image qualification then completed and halted
cleanly too.

## Fresh-CHD acceptance

Run `ordinary-b_vg9nc4` cold-boots the new CHD with the bundled emulator and
passes the complete maintained check without diagnostic intervention:

- Three untouched winterm starts have 8×15 cells and an 80×24 visible grid.
  A foreground native job receives SIGWINCH and measures 66×21 after each
  resize. The extra 100×30 terminal reports its actual dimensions and exits
  zero on typed `exit`, with its window and process gone and empty stderr.
- All 1,790 installed support-file hashes match. The replacement module is
  boot-loaded, the core kernel is unchanged, and Xorg uses 1280×1024 XAA.
  The native Render control reports 8,536 checked pixels and zero mismatches.
- Incorrect-password rejection, both original IRIX logout menus, deliberately
  failed startup, recovery and an independent same-user shell all pass.
  The system services survive session changes.
- `netbsdtest` runs standard ctwm at `/home/netbsdtest`, with effective groups
  `netbsdtest wheel`. Its manager PID is rechecked after startup and all that
  user's processes end on tested terminal-driven logout. Its Quit menu is
  outside this check. The prior wheel image retains the interactive `su -`
  qualification; this replacement preserves its account files.
- A final IRIX login double-clicks xmahjongg in the Freeware catalog, observes
  a new process/window and a FAM execution event, and retains the backdrop
  and desktop icons. No rpcbind loopback warning appears during the cycle.
- The guest unmounts cleanly and halts; the source CHD remains unchanged.
  All test IRIS instances and their Xvfb processes are stopped.

The strict image qualifier verifies source/artifact hashes and PNGs before
selecting this bundle. `./xiri check` now includes `--winterm` automatically.
The 37 host tests passed, and the local workflow/toolbox check passed. The
emulator snapshot from the earlier font failure is retained as a diagnostic
capture only; restoring it is still unqualified.
