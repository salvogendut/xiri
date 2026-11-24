# Native package qualification

The maintained packager is described in [the native package guide](../../docs/NATIVE-PACKAGE.md).
Its guest test runs on a **disposable** copy of the qualified native NetBSD
base. It replaces the complete vendor tree from the versioned importer and
installs the native package with `install-fixture.sh`, with xdm, FAM and
rpcbind stopped. That script is a test fixture, not a managed installer.

```sh
python3 scripts/probe-irix-import.py \
  --bundle .work/images/xiri-netbsd-desktop-20261114-controls \
  --payload .work/imports/irix-6.5.22f-v1 \
  --native-package .work/packages/netbsd-sgimips-native-v1 \
  --output .work/native-package-check
```

Use a new output directory. Checks cover native package integrity, running
kernel identity, all recorded native prerequisites, rejection of a mismatched
kernel and missing prerequisites, installation and repeat installation,
configuration/account preservation, and imported file hashes. Graphical
checks exercise full-screen xdm, 4Dwm/Toolchest/Icon Catalog/winterm/xclock,
shell identity/home, IRIX `/bin/sh`, File Manager, logout/relogin and native
ctwm with a visible uxterm. A verified clean halt and unchanged source CHD
are required. Retain result JSON, exact executed probes, logs and PNGs before
removing temporary disks/CDs and duplicate package builds.

The base already contains the qualified kernel/boot wrapper, stock userland
and X sets, device/account setup and user homes. The fixture does not replace
the kernel. Its existing file mode is preserved while its exact bytes and
running version are checked. This cycle does not establish a fresh install,
new kernel activation, recovery after interruption or application-wide
compatibility. IRIX 6.5.30 requires a separate donor/import and guest run.

## Bootstrapping a stock target

`check-clean-bootstrap.py` starts from the pinned NetBSD 11.0 R4400/Indy
installation with no Xorg, vendor tree or Xiri desktop account. It installs the
four X runtime sets, kernel, boot wrapper and compatibility module on a
temporary copy, selects the new kernel in the PROM and boots from disk again.
The second boot verifies the installed hashes and the loaded module. Use the
November 14 Indy build and a fresh output directory.

```sh
IRIS_NO_IDLE=1 python3 lab/native-package/check-clean-bootstrap.py \
  --base .work/indy-netbsd/base \
  --sets .work/netbsd-11.0/sgimips/binary/sets \
  --build .work/irix-mips4-module \
  --emulator .work/emulators/iris-xiri-20261114-r5k-config \
  --output .work/clean-indy-bootstrap
```

This bootstrap ends at native multi-user login. The per-release installer
and xdm qualification are described below. [Stock installation](../../docs/results/2026-10-29-indy-netbsd-install.md) ·
[Kernel and module build](../irix-mips4/module-build.json)

For 11.99.11 use `--native-package DIR --keep-target` in place of `--build`.
This extracts and verifies the matching Indy kernel, wrapper and module from
the native package. It retains the halted raw disk and serial PROM alongside
the result JSON. Use these only as a common **pre-desktop** starting point
for the independent release installations. The stock image remains available
for another run. Build the two install CDs as described in the
[native installation guide](../../docs/NATIVE-PACKAGE.md#clean-installation-on-an-emulated-indy).

```sh
python3 lab/native-package/check-clean-desktop.py install \
  --base "$bootstrap" --media "$iso" --emulator "$emulator" \
  --output "$run" --release "$release"
python3 lab/native-package/package-clean-desktop.py \
  --installation "$run" --emulator "$emulator" --output "$bundle"
python3 lab/native-package/check-clean-desktop.py desktop \
  --base "$bootstrap" --media "$iso" --emulator "$emulator" \
  --output "$run" --release "$release" --bundle "$bundle" --kernel "$kernel"
```

Set `release` to `6.5.22f` or `6.5.30f`, use distinct run/bundle paths,
and supply the exact unstripped Indy kernel as `kernel`. The guest fixture
creates disposable xiritest and netbsdtest accounts, sends TERM to the installer
during its first transaction, tests a conflicting administrator file and checks
preservation on resume and repeat. Production installation creates no login
accounts. Packaging verifies the CHD data SHA-1 against the halted raw disk.
The desktop phase uses a private copy of the packaged CHD and the bundle's
graphical PROM. Check the corresponding result JSON and desktop PNG before
publishing a manual image.

## Stock kernel round trip

Use the clean desktop bundle, its qualified emulator and the pinned serial
PROM from the original Indy installation. The probe uses the serial PROM to
set the two boot filenames and exports two private graphical PROM settings.
All three operating-system boots use the normal graphics console and a
separate serial login. Each release gets its own copy of the CHD and writable
overlay. The same overlay carries user files through the three boots.

```sh
python3 lab/native-package/check-kernel-rollback.py \
  --bundle "$bundle" --emulator .work/emulators/iris-xiri-20261122/accelerated \
  --serial-prom .work/indy-netbsd/base/nvram.bin \
  --sets .work/netbsd-11.0/sgimips/binary/sets \
  --kernel "$kernel" --output "$run"
```

Supply the unstripped 11.99.11 Indy kernel as `kernel` (member `kernel/netbsd`
of the native package), and choose a new output directory for each run. The
probe verifies the saved kernel against the distribution kernel set, compares
both running build strings, and checks user data and policy across the round
trip. The final X session checks the saved preference against the X resource
database. Inspect the result JSON and the per-boot shutdown logs before
removing the private CHD and overlay.

## Desktop removal and reinstall

Build a fresh installer CD with `./xiri install-media` for the matching
clean Indy bundle. Add `--install-media "$iso"` to the stock kernel round-trip
command above, using a fresh output directory. Repeat with the other release's
CHD and CD. The guest runs from a private overlay through four cold boots.

The first boot removes the original November 23 installation. The probe
supplies native NetBSD xdm policy and a Newport Xorg configuration before
removal, seeds user and administrator edits, and checks the saved stock
driver and rpcbind. The stock boot logs a native user into ctwm and checks
for a mapped UXTerm. The third boot reinstalls Xiri, exercises the new
ownership records with an interrupted removal, resumes it and installs the same release again.
The final login checks the saved winterm colour in the running X server and
executes the vendor shell. The JSON, screenshots and kernel shutdown logs
are local to the test's output directory. See the
[operator procedure](../../docs/NATIVE-PACKAGE.md#remove-the-desktop-and-return-to-native-netbsd).

## In-place native helper update

Build a release-specific CD with the [upgrade procedure](../../docs/NATIVE-PACKAGE.md#upgrade-native-helpers-on-an-installed-indy).
Use `--upgrade-media "$iso"` with the kernel round-trip runner above, and give
each release its own output directory. Its three boots exercise the update,
the upgraded desktop, and the desktop after rollback. The probe sends TERM
to the installer after a helper has been replaced and before the completed
receipt changes. It also tries a conflicting local edit before the update.
The two graphical boots each exercise both xdm logins, check a saved winterm
colour on the X server and run the vendor shell. See `result.json` in the
run directory for the receipts and per-boot screenshots' hashes.

For the helper inventory migration use the same runner with
`--upgrade-media .work/installers/indy-11.99.11/helper-layout/xiri-${release}.iso`
and `--inventory-base-media .work/installers/indy-11.99.11/upgrade/xiri-${release}.iso`.
The previous CD is at SCSI ID 5. Both tests begin by upgrading the published
clean image to v2. The R4400 exercises its legacy receipt. The R5000 also
removes and reinstalls v2 over a site-owned mapper to exercise recorded file
ownership. Both tests interrupt forward and reverse migration between the
caller switch and final retirement, verify local collisions, and check both
xdm sessions after each reboot.
