# Desktop geometry and Toolchest launch integration — 2026-11-02

The updated desktop runs native Xorg at 1280×1024 and opens supported
applications from original Toolchest. [Qualification metadata](2026-11-02-desktop-launch.json)
records two menu-created terminals executing native shell commands, plus
xclock, Icon Catalog and Mahjongg menu launches. This uses native integration
scripts; neither fork's kernel/emulator source nor the imported binaries change.

The original reusable image starts applications explicitly during session
startup. That did not test launching another application from Toolchest.
Manual testing exposed a smaller X root and a separate failed shell exec.

## Diagnosis

The old Xorg configuration leaves the mode unspecified and selects
1024×768. The emulated Newport framebuffer is 1282×1024 with its default
PROM timing. The new desktop-specific configuration requests 1280×1024 at
depth 24 with software rendering. The older 1024×768 qualification and its
configuration remain unchanged for reproduction. The two remaining columns
belong to the default emulated timing; physical monitor modes and XAA are
not qualified here.

An actual click on Desktop → Open Unix Shell in the original menu produces
this sequence in the disposable guest's ktrace:

```text
toolchest CALL fork
toolchest NAMI /emul/irix/bin/sh
toolchest RET execve -1 errno 8 Exec format error
```

The imported `bin/sh` and `bin/csh` are static n32 ELF executables. Current
vendor loading handles the bounded dynamic-interpreter contract; the static
fixture contract requires Xiri's marker. This is not a failure to find the
winterm executable, nor evidence that all n32 programs are unsupported.

The supplied `toolchest(1X)` manual confirms that `f.exec` uses `MWMSHELL`,
then `SHELL`, then `/bin/sh`. The `.sh` operators bypass those environment
choices and force `/bin/sh`. Consequently, setting `SHELL` alone cannot fix
the original system menu.

## Integration

`toolchest.chestrc` includes the unchanged original system menu and replaces
Desktop → Open Unix Shell and Find → Icon Catalog. It adds Applications
entries for Unix Shell, Clock, Icon Catalog and Mahjongg. These actions use
`f.exec` and `MWMSHELL=/usr/local/libexec/xiri/command-shell`, a symlink to
native `/bin/sh` outside the imported tree. Once native exec succeeds,
`xiri-launch` uses explicit `/emul/irix/...` paths to start the vendor apps.

For Unix Shell, the original xwsh terminal receives the existing native
controlling-PTY helper and a unique handoff-report path. This preserves the
native `/dev/pts` reopen needed to avoid the previously observed layered-tty
teardown panic. It also permits repeated terminals without reusing the
exclusive report file. Startup winterm continues using the vendor script;
menu winterm directly selects that script's xwsh backend.

Every launch has its own stdout/stderr/PID files under the session directory.
No imported executable, shell or system menu is overwritten. Other original
menu commands are still unqualified; this is an explicit integration profile,
not general support for all IRIX shell scripts or desktop services.

## Reproduction

```sh
PYTHONDONTWRITEBYTECODE=1 python3 scripts/probe-xiri-desktop-launch.py \
  --seed .work/xiri-image/prepared-seed
```

The probe verifies the reusable raw source hash, clones it, checks imported
files and executable permissions, and installs only Xiri's updated scripts
and configuration. It drives actual Toolchest selections under 4Dwm, types
commands into the resulting terminal, checks new application windows,
compares composed pixels outside the old root bounds, verifies payload
integrity again, and halts its own emulator. The original CHD is preserved.

Kernel source remains `4680cd61b625a5eaa393a0deaea73f4b9f7ed7bc`; emulator
and native helpers retain the signal/image checkpoint. IRIS upstream
`4ad1b1d435dc115697433f091b10dfa8c48aa7ed` was freshly checked and was already
contained in integration branch `xiri`. No fork source changes were needed.

The initial diagnostic is retained at
`.work/desktop-fixes/diag-3ww8kizl`, with its menu trace at
`.work/desktop-fixes/menu-launch.dump`. It opened a terminal from the adapted
Desktop menu, received `XIRI_MENU_SHELL_OK` from a typed native-shell command,
removed all reserved-UID clients, passed the native o32 control and halted
cleanly. An initial repeatable run, `.work/desktop-launch/ordinary-y8zsx38k`,
hit a 300-second in-guest payload-hash timeout before launch tests. It halted
cleanly and retained the original source hash. Its exact harness is saved as
`probe-as-run.py`. The corrected harness establishes initial integrity using
the qualified full raw-disk hash and gives the final guest payload check
900 seconds, avoiding a redundant initial guest hash.


Further diagnostic runs isolated two test boundaries. `ordinary-aud85wo_`
reported 1280×1024 through Xorg but its first GL-composited pixel was black;
it halted cleanly. `ordinary-n9rr9aaz` passed the extended framebuffer checks
but then targeted the first window named winterm, which belonged to an
already exited shell. Its xwsh retained that window and logged PTY write EIO.
The new menu-created shell had a separate, valid handoff and worked when
selected. Two successive menu terminal commands and all three Applications
launches subsequently passed during the retained diagnostic session.

The corrected probe explicitly removes reserved-UID xwsh processes after
its shell-exit steps. **Automatic xwsh window closure after native shell exit
remains open**; this does not claim a normal terminal-exit fix. Session-level
cleanup still removes all reserved-UID processes.

The pinned CLI's monitor capture returned stale window contents. Switching
from GL to software composition produced a fresh diagnostic frame, but a
later run with software selected still returned identical startup/menu PNGs.
Therefore the monitor's later PNG is not evidence of the menu-created
windows. The launch checks use X window records, native shell output files
and handoff reports. The larger-screen checks change root colors and verify
composed pixels outside both old bounds; the startup PNG is retained with
that limited scope. Final visual confirmation uses Prismatic's own frontend
capture. The launcher disables idle blanking and resets the screen saver.

## Accepted launch run

`.work/desktop-launch/ordinary-z18rnvjr` passes the corrected workload:

- Xorg reports 1280×1024; red and blue composed pixels at (1278,1022) and
  (1100,1000) match beyond both old screen bounds.
- Desktop → Open Unix Shell produces `XIRI_MENU_SHELL_1_OK`, followed by
  `XIRI_MENU_SHELL_2_OK` after explicit cleanup of the first closed-shell xwsh.
  Both have separate native handoff reports, UID/GID 1234 and native PTYs.
- Applications opens xclock, Icon Catalog and xmahjongg, with distinct
  launch-log directories and X window records.
- Native o32 controls pass before and after; native X remains responsive.
  Session cleanup reports `absent=1 valid=1`, with no UID 1234 processes left.
- All 1,701 regular imported/resource files and the five updated native
  files pass guest SHA-256 checks. The source raw image remains unchanged,
  and the test guest halts cleanly.

The [startup screenshot](images/2026-11-02-full-desktop.png) records the larger
initial desktop. The identical later monitor PNG is explicitly excluded as
visual evidence of menu launches. The JSON records this capture limitation;
the command proofs and launch/window records are independent of it.

## Replacement image and Prismatic confirmation

The accepted raw guest was packaged as
`.work/images/xiri-netbsd-desktop-20261102/netbsd-xiri.chd` (479,786,856 bytes).
`chdman verify` passed and the extracted 8 GiB disk matched the source exactly:

```text
CHD SHA-256: d8ad6f45e3e8c50b0f532366ecddf5e887df76752927bd0ae80cfd74f67333f2
raw SHA-256: 71327d0b2e3467daa0c0ac4e0dcbfd65081b5ca15ea5f8c9a273e88814d86130
```

The [cold-boot qualification](2026-11-02-xiri-image-desktop.json), from
`.work/xiri-image/runs/chd-4fh2be2o`, verifies direct disk boot, the five
installed integration files, the native-shell alias, 1280×1024 Xorg, visible
xmahjongg, native controls, reserved-UID cleanup and a clean guest halt.
The [X root capture](images/2026-11-02-xiri-image-desktop.png) is pixel-identical
to the guest XWD. The promoted bundle supplies both IRIS and Prismatic
configuration files with separate NVRAM state. The previous image and raw
seed remain preserved; `.work/xiri-image/prepared-seed-20261102` is the new
reusable raw seed. See [image instructions](../XIRI-IMAGE.md).

The [Prismatic confirmation](2026-11-02-prismatic-desktop-launch.json), from
`.work/prismatic-xiri/menu-20261102-013108`, uses a frozen copy of the existing
release binary with SHA-256
`3023cd1a6895740480f32c32e6b82928c4eee3fc7439c3bda1f38e2628acad92`.
This differs from the earlier boot-only test's binary; no new source revision
is inferred from the checkout and this work did not rebuild it.

After a disk boot, guest XTest helpers click Desktop → Open Unix Shell and
type a command into the new terminal. The resulting file contains the exact
standalone marker `XIRI_PRISMATIC_MENU_OK`, verified through serial output.
Native o32 controls pass before and after, no UID 1234 clients remain after
session cleanup, the guest syncs/unmounts and returns to the PROM, and
Prismatic exits normally with code 0. The base CHD remains unchanged.

The [actual Prismatic screenshot](images/2026-11-02-prismatic-menu-shell.png)
shows the menu-created native shell after that command. It preserves every
pixel from Prismatic's F4 PPM capture, including the two extra framebuffer
columns: the capture is 1282×1024 and Xorg's root is 1280×1024. This provides
frontend visual evidence independent of the stale CLI monitor snapshots.
The earlier attempt at `.work/prismatic-xiri/menu-20261102-012722` did not
pass the menu-shell step; it halted cleanly with the source CHD unchanged.
The accepted harness waits for usable application geometry and removes the
startup terminal before selecting the new identically named window.

All test emulator processes were stopped. The user's separately running
Prismatic instance was left untouched. Icon Catalog still needs its desktop
communication/content work, and terminal closure and other original menu
actions retain the limitations above.
