# Native CD mount correction in the desktop image

This record preserves the failed candidate's original gate. The later
[Xorg scheduling cycle](2026-11-04-xorg-scheduling.md) identifies the input
stall and qualifies a separate replacement; that newer bundle is now selected.

The replacement bundle is
`.work/images/xiri-netbsd-desktop-20261104-stability/`. It contains the
[qualified native CD9660 correction](2026-11-04-system-stability.md) from
NetBSD `xiri` commit `0cd56e7a286c4cd3d67ab7cc971b233a83ac1655`.
Creation, `chdman verify`, the complete raw-disk round trip and full cold-image
xdm/session checks pass. The application focus gate fails with a reproduced
native XTest timeout, so this bundle is **not promoted**. `./xiri run` retains
the preceding Acrobat image and its manual state.

The 8 GiB disk compresses to **496,116,307 bytes**. CHD SHA-256:
`068e7ed67451cf664deafd8695d3825e141bcd41af0e0e02e701d18e43c450ff`.
Prepared and extracted raw-disk SHA-256:
`ad458af429db5e77242139d02f80b9e8e8de17532b7acf2dc7fe764f75473d95`.

## Included change and preserved state

The new [image pin](../../lab/system-stability/baseline.json) ties the core,
boot wrapper and module to their [build ledger](../../lab/system-stability/build.json).
Native core SHA-256 is
`5cbf43d2656fb6eefce3f487e0ba9c994e5104e7ae9908d7e158f49bb732c8b4`;
boot wrapper SHA-256 is
`61a6f8dd16ec8ac092f54ddafbd895d45086e1b905310ae28136bbadb3f1984b`.
The IRIX module remains byte-identical at
`37c8a5114483ad834d0dbef551175e506a1874599aa8caf70366481be7559b2f`.
The bundled IRIS emulator remains pinned to `819c682`.

Preparation refreshes a disposable clone of the verified Acrobat raw disk.
The installed-file comparison changes only `/netbsd` and `/netbsd.boot`.
All GIMP, GNOME, PTY-helper and Acrobat resource ledgers are unchanged, as are
the runtime bytes, native account/password databases and original application
payload. xiritest retains `/usr/people/xiritest`; netbsdtest retains native
ctwm, `/home/netbsdtest` and wheel membership. No application profiles from
the diagnostic guests are copied into the new image.

The preparation run is `.work/xdm-image/prepare/ordinary-zu8hi6kg`. It boots the
new core, verifies the inherited payload, installs the matching artifacts,
boots from disk to a 1280×1024 xdm greeter at securelevel 1, and halts cleanly.
Its source raw disk remains unchanged. The previous image's manual NVRAM and
overlay are retained independently; changed graphical NVRAM was preserved
during raw-seed materialization.

## Passed disk and session checks

The [disk/session record](2026-11-04-system-stability-image.json) comes from
`.work/irix-xdm/runs/ordinary-fl97ev0d`. It verifies graphical disk autoboot,
1280×1024 Xorg with XAA, filesystem module loading at securelevel 1, rejected
credentials, three IRIX logins, both logout menus, failed-startup recovery,
netbsdtest's native ctwm desktop and wheel membership, catalog xmahjongg launch
and FAM execution notification, and clean unmount/halt. Each IRIX rendering
check compares 8,536 pixels with zero mismatches. Three untouched winterm
starts preserve the bitmap-font geometry and deliver foreground resize signals;
an extra terminal also closes normally on typed `exit`. Services and the
independent login survive session transitions; no rpcbind bind warnings appear.

The separate [application/stability record](2026-11-04-system-stability-image-apps.json)
retains both passes and failures. Before its focus failure, `boot-25ukabya`
passes all 158 CD9660 checks, 40 native input round trips / 80 button events,
20 detached-child launch cases and 16 adversarial cases. The old image has
92 failures with the identical CD fixture. GNOME Terminal runs the interactive
original IRIX shell at `/usr/people/xiritest`, saves 257 scrollback lines,
reads that setting after relaunch and returns status zero on both normal
exits. These partial checks do not make the failed application run a pass.

The 38 host tests pass. Guest helpers compile with warnings treated as errors.
The previous stability cycle retains the separate 96 MiB paging evidence.
No resource or native account/password file changes in this image. The old
CHD, three manual NVRAM profiles and existing overlay retain their hashes.

PNGs: [4Dwm/catalog](images/2026-11-04-system-stability-image.png),
[native ctwm](images/2026-11-04-system-stability-image-native.png),
[xdm](images/2026-11-04-system-stability-image-greeter.png),
[untouched winterm](images/2026-11-04-system-stability-image-winterm.png),
[Reader before the timeout](images/2026-11-04-system-stability-image-acrobat.png),
and [reopened GNOME preferences](images/2026-11-04-system-stability-image-gnome.png).

## Native focus timeout

The new-image run `boot-25ukabya` reaches the PDF on its fifth Reader launch,
then the instrumented native focus helper exits 124. Connection opening and
motion synchronization finish; the last recorded stage is `button-sync`.
Its 100 ms delayed button-release request and subsequent `XSync` have not
completed when the ten-second alarm fires. The earlier four PDF/capture/focus/
Quit repetitions pass, as do GNOME Terminal's shell, preference and normal-exit
checks. This failed run is not application acceptance.

Twenty direct follow-up clicks complete. A reduced diagnostic that repeats
GL → software framebuffer capture followed by the same click, without
relaunching Reader, reproduces the timeout on repetition six. Both failures
stop at `button-sync`; the serial shell and subsequent native X queries remain
responsive. The [stage log](2026-11-04-stability-image-focus-timeout.log) and
[failure PNG](images/2026-11-04-system-stability-image-timeout.png) are retained.
This narrows the trigger but does not establish a kernel, emulator or
application cause. Promotion remains held.

A diagnostic variant stops itself at its alarm to retain the connection.
Twenty background/polling repetitions pass. A foreground version then stops
on repetition twelve, again at `button-sync`. Its automatic PID lookup fails;
the shell's job table and `ps` identify suspended PID 6069. Native GDB crashes
with SIGSEGV while attempting to inspect Xorg, so it supplies no usable
backtrace. A later read through `/proc/1313/mem`, using the ELF load base and
symbol table, finds `grabState=0` and `pPending=0`. This late observation does
not establish their values at the alarm. The raw reads, failed debugger output
and failed PID lookup remain in the record. The diagnostic job is killed and
the guest is halted; the original failed test result is preserved.

The [XTEST protocol](https://www.x.org/releases/current/doc/xextproto/xtest.pdf)
specifies that a delayed fake event also delays subsequent requests from that
client. The corresponding Xorg 1.10.6 sleep/wakeup path and server-grab state
are diagnostic targets, not yet established causes.
The next system step is to capture the delayed-client/wakeup state at the
failure without relying on the crashing guest debugger. The earlier native
child-control stalls and catalog-batch halt failure remain separate open
observations. Successful retries do not close any of these issues.

## Replay diagnostic

The first old-image control, `.work/system-stability/boot-k5afu343`, is a
failed diagnostic run, not acceptance. Its first four PDF/capture/focus/Quit
sequences pass. On the fifth launch, 4Dwm's automatic cascade puts Reader's
Open toolbar button under the fixed `300 300` focus coordinate. The PDF
capture shows that geometry; the failure capture then shows a modal Open
dialog. The instrumented helper completes open, motion, button synchronization
and close without a timeout. Cancelling the dialog and sending Ctrl-Q makes
the Reader process and window disappear; the desktop remains ready and the
guest halts cleanly.

The [before-focus capture](images/2026-11-04-stability-image-coordinate-before.png)
and [failure capture](images/2026-11-04-stability-image-coordinate-after.png)
preserve that transition.

The diagnostic also illustrates why a named X window alone is insufficient:
Acrobat retains its unmapped Open dialog after Cancel, so `xwininfo -name Open`
still succeeds. The maintained replay now checks viewable windows, places
Reader consistently before each capture and records the document geometry.
It preserves the original immediate capture → focus → Quit sequence and
retains the failed run. The parallel candidate run using the old fixture is
stopped explicitly and excluded; fresh old/new-image controls use the corrected
fixture. This coordinate error is separate from the earlier native XTest
alarm timeout, which remains unexplained.

The second old-image run, `boot-g__svm0j`, fails while recording GNOME
Terminal's reopened PID. Its [screenshot](images/2026-11-04-stability-image-typing-focus.png)
shows the end of the typed PID command in the newly opened Terminal; the
process/window exist, but the PID file does not. The fixture had submitted
launch and PID recording as two typed shell lines. The maintained helper now
submits both before one Return, preventing a new window from taking focus
between those lines. This is a test-input correction, not an application or
kernel change.

An explicitly separate continuation attempts to recover that control, but
its preliminary cleanup does not observe the known GNOME PID disappear within
30 seconds after SIGTERM. It stops before exercising the revised launcher;
no success or cause is inferred from that cleanup failure. The original guest
then halts cleanly. Both the failed cold run and failed continuation remain
excluded from acceptance, with their source snapshots, state and results in
the application/stability record. The accepted new-image run completes both
GNOME launches and normal exits with its retained earlier fixture.

Stopping that superseded run interrupted a paced serial command midway
through a shell `until` loop. Its first log-collection command and shutdown
landed at the continuation prompt. Sending Ctrl-C and `shutdown -h now` to
that guest's serial B connection recovered the prompt; the original harness
then verified clean unmount/halt. The interrupted result remains an error
with its collection failure and manual recovery recorded. It supplies no
acceptance coverage.

## Reproduction

```sh
python3 scripts/prepare-xiri-seed.py \
  .work/images/xiri-netbsd-desktop-20261104-acrobat \
  --output-directory .work/xiri-image/prepared-seed-20261104-acrobat
python3 scripts/prepare-xiri-xdm-image.py \
  --seed .work/xiri-image/prepared-seed-20261104-acrobat \
  --kernel-build .work/netbsd-stability-build \
  --baseline lab/system-stability/baseline.json --keep-accounts
```

Package the printed clean preparation run with `build-xiri-image.py`, using
the same baseline, `.work/netbsd-stability-build/tftp/netbsd-XIRI_INDY`, a new
output directory and the preceding bundle's pinned `emulator/` directory.
This cycle reuses the installed resource set instead of extracting it again.

Run the full `probe-xiri-xdm.py --bundle NEW_BUNDLE --winterm` checks and the
separate maintained application/focus replay before promoting the image:

```sh
python3 scripts/probe-system-stability.py --bundle NEW_BUNDLE \
  --runs 1 --sessions 1 --input-iterations 10 --child-iterations 5 \
  --require-cd9660 --acrobat-replay 6 --halt-active --debug-failure
```

The retained original focus helper and instrumented equivalent are described
in the [stability lab guide](../../lab/system-stability/README.md). An earlier
timeout is not considered fixed merely because a bounded replay passes.

For explicit investigation of this unpromoted candidate, use:

```sh
/var/home/salvogendut/Dev/xiri/.work/images/xiri-netbsd-desktop-20261104-stability/run-iris.sh
```

Credentials remain `xiritest` / `xiritest` for 4Dwm and `netbsdtest` /
`netbsdtest` for ctwm. The latter remains in wheel. This command uses the new
bundle's independent manual state; `./xiri run` continues to select the prior
qualified image. Shut down NetBSD before closing IRIS.
