# Graphical boot and desktop logout

The manual test feedback identified four distinct issues: the serial PROM
made a desktop image appear idle, rpcbind printed duplicate loopback-bind
warnings, both logout menus did nothing, and Icon Catalog showed names
without application artwork.

The first three are the scope of this usability cycle. The missing artwork
remains a compatibility issue: the next measured failure is IRIX
`F_SETBSDLKW` (fcntl command 13) on the opened desktop filetype database,
`/usr/lib/filetype/desktop.otr`. Its resources are already imported. The
next kernel cycle needs original-IRIX lock observations before an adapter.

## Changes

The manual firmware profile selects `console=g` and `AutoLoad=Yes`, retaining
the existing NetBSD disk boot variables. NetBSD enables `ttyE0` for display
login and `ttyZ0` with `local softcar` for serial B diagnostics, disabling the
alias `constty` getty to avoid duplicate readers. A small `rc.local` command
also allocates the text screen on serial diagnostic boots. The automation
profile keeps serial PROM boot and `AutoLoad=No`.

Toolchest retains its original headings and Log Out label, with a native
logout action. Each desktop session generates a copy of the original
`system.4Dwmrc` changing only the endsession command paths, so the right-click
menu reaches the same action. The imported vendor file is unchanged.
The vendor root menu uses press-drag-release: hold the right button, move
over Log Out and release. A complete click followed by a separate keypress
does not select that menu item.
`xiri-logout` creates a request file in the current session directory; the
existing native supervisor, already running as UID 1234, performs its normal
client cleanup. The launcher reaps its services and Xorg and returns to the
shell that started it. This does not implement IRIX session saving or restore
an earlier application layout.

The [native rpcbind change](../../lab/native-rpcbind/README.md) avoids adding
an implicit loopback literal already explicitly requested by `-h`. The
service remains bound to loopback. The change is a native userland utility
fix, not an IRIX syscall or kernel change.

The session waits for 4Dwm to publish `_MOTIF_WM_INFO` before launching the
other clients. The previous fixed four-second delay could start winterm
before the window manager was ready, producing the observed short window.

## Evidence

Initial diagnostics used a disposable copy of the qualified service seed,
`.work/desktop-repair/graphics-fhfprmwo`. They reached graphical login and a
working serial diagnostic login, registered FAM without duplicate-bind
warnings, and exercised Toolchest logout. An initial winterm mapped at
983x72; a second session mapped at 983x504 and accepted a native shell
command. This startup variation is retained as a diagnostic observation.
The diagnostic harness did not certify its final shutdown and is not an
image seed.

The reproducible fresh-copy qualification is
`scripts/probe-xiri-desktop-usability.py`. It checks graphical login using
emulated PS/2 keys, launches the desktop from that console, types through
winterm, checks FAM registration and loopback binding, invokes both logout
menus and verifies return to the graphical shell with no remaining session
clients, FAM, rpcbind or Xorg. Since shutdown messages go to the graphical
console, the harness reads the pinned kernel's message ring through the
emulator monitor and requires clean unmount and halt messages. It uses the
KSEG0 alias after firmware clears KX; this observer does not modify the guest.
The final fresh-copy run `ordinary-bk_e3ze3` passed. Its
[public result](2026-11-02-desktop-usability.json) records graphical console
login, two usable winterm shells, both logout paths, absence of remaining
clients/services, native controls and clean shutdown. The syslog counter
remained at two inherited RPC warnings before and after the test: the new
sessions added none. The immutable service seed's raw hash is unchanged.

The [graphical login capture](images/2026-11-02-graphics-login.png),
[desktop capture](images/2026-11-02-desktop-usability.png) and
[open logout menu](images/2026-11-02-desktop-logout.png) are original IRIS
framebuffer PNGs. The desktop still lacks filetype icon artwork.

Failed diagnostic runs remain in `.work/desktop-usability/`:
`ordinary-_h0ziau9` exposed the short initial winterm; `ordinary-_dyhpasq`
and `ordinary-r32bze3t` exposed the incorrect menu click test. The last run
then demonstrated the correct gesture with the final configuration and
halted cleanly, but its original failing result is preserved and is not an
image seed. The replacement qualification starts from a fresh copy.

`ordinary-rbf_96w4` passed its first shell/logout cycle, then failed log
collection because an unpaced serial command lost the `H` in `HEX_END`.
Its later diagnostic root-menu logout and clean shutdown succeeded, but
the run remains failed. The subsequent `ordinary-3cmpf2x4` still lost a
character with 16-byte chunks. Eight consecutive large transfers then
passed using one byte per 5 ms. The usability and cold-boot probes now use
that pacing; framing and gzip validation remain strict. This change is
test transport handling, not a guest fix.

The menu-regression diagnostic `ordinary-no0fy1vd` passed two shell
launches and opened Icon Catalog, then failed its Freeware-page wait.
Its wait exited the diagnostic shell and cleanup could not
certify a halt. That disposable run is retained as failed. The menu probe
now uses the same byte pacing, scopes failed waits to a subshell, installs
the current logout helper/supervisor and follows the updated menu position.
The next run, `ordinary-gfam91g3`, halted cleanly but its eight synthetic
Next key holds overshot to Printing, page 14. The screenshot establishes
that focus/navigation worked; the earlier irregular serial echo alone did
not establish a failed focus command. The follow-up disables key repeat
only during generated page navigation and requires each intermediate page.

The final menu regression, `ordinary-u09rhboh`, passed both repeated shell
launches, the original Icon Catalog menu action, pages 2 through 9 with the
Freeware title checked, FileManager browsing and native FAM create/delete
notifications. It verified the staged vendor files and installed helpers,
passed native controls and halted cleanly. The
[menu result](2026-11-02-desktop-usability-menus.json) and
[PNG](images/2026-11-02-desktop-usability-menus.png) retain the evidence.
Automatic xwsh closure remains unfinished; the test explicitly removes an
exited terminal before selecting the next identically named one.

## Replacement image

The new bundle is `.work/images/xiri-netbsd-desktop-20261102-graphical/`.
Its 480,190,454-byte CHD passed `chdman verify` and an exact 8 GiB extracted
disk comparison. CHD SHA256:
`b9d29c5e7b71bffc14c6d8115103ba51d4051a1d7a9432ae2be86c189280bd46`.
Raw SHA256:
`d3bc60be7c897327599aaf9df8040de5399127a3f041c67dcd61d3842f646971`.
The graphical and serial NVRAM profiles are separate; image promotion and
raw-seed preparation preserve both. Direct CHD cold-boot qualification is
recorded separately from the seed's graphical-session checks.

The first CHD run, `chd-e9lcj3go`, booted and passed its guest controls but
produced a black framebuffer capture; the image qualifier rejected it.
The fresh retry, `chd-614kpfwx`, passed the
[cold-boot qualification](2026-11-02-desktop-usability-image.json), including
the [framebuffer PNG](images/2026-11-02-desktop-usability-image.png). It had
64 colors before the new modifier-key input and 72 after input/frame settling,
so the retry does not prove that keyboard wake-up caused the improvement.
The earlier black capture remains an unresolved intermittent observation.
The probe now checks framebuffer content before tearing down the guest;
the qualifier independently retains its pixel-content check.

The new image is promoted in `lab/irix-installed-desktop/image.json`.
`.work/xiri-image/prepared-seed-20261102-graphical/` provides the reusable
raw automation seed, with both NVRAM profiles retained. The earlier service
image and its seed remain available. NetBSD `d3a316bd7e1` is pushed on
`xiri`; the kernel and emulator pins are unchanged.

The user's active service-image overlay and Prismatic state are left alone;
replacement artifacts are built in a new directory.

## Fork check

IRIS upstream was fetched again on 2026-11-02. `main` remained at
`43e525a847ceeb9453af5d685dd8d353bea133e1`, already integrated into `xiri`
at `a4a1659d0b3180713f988d73b7b7da204048ae6a`. No new emulator merge or
rebuild was necessary. The existing guest emulator pin is unchanged.
