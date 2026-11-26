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

For Indy v5, add `--sgi-clock` to the desktop phase. It launches the
original SGI Clock under the authenticated 4Dwm user, checks its window
class and compares two window dumps before returning to xdm. The screenshot
is saved as `desktop/sgi-clock.png`.

For the Indy browser checks, use the matching Mozilla installer ISO. Add
`--mozilla` to the `install` phase and package its halted result as above.
Extract `netbsd` from the qualified browser kernel archive into a temporary
directory for the graphical halt checks, then run:

```sh
python3 lab/native-package/check-clean-desktop.py mozilla \
  --base "$bootstrap" --media "$iso" --emulator "$emulator" \
  --output "$run" --release "$release" --bundle "$bundle" --kernel "$browser_kernel"
```

The test logs in through xdm, opens the SGI browser as `xiritest` and
navigates to CERN's World Wide Web project page over HTTP. On the private overlay it removes the
component, boots the v5 kernel, adds Mozilla again and boots the browser
kernel. It checks profile and site-file hashes across the changes and saves
both browser screenshots. The guest needs outbound DNS and HTTP.

### Original SGI installers and Freeware CD 4

To exercise the original SGI installer against the complete Freeware CD 4,
use the clean Mozilla bundle, its unstripped browser kernel and the
[two installation discs](../irix-installer/README.md#use-the-complete-freeware-cd-4-with-a-clean-mozilla-indy).
Use a fresh output directory for each release.

```sh
IRIS_NO_IDLE=1 python3 lab/native-package/check-clean-desktop.py freeware \
  --release "$release" --bundle "$bundle" --emulator "$bundle" --kernel "$browser_kernel" \
  --media "$supplement" --cd4 "$cd4" --output "$run"
```

The test creates a private overlay, sets a homepage in a real browser
profile, installs xmahjongg and reboots. It double-clicks the game in the
Freeware tab, removes it through SGI's installer and reopens the saved
homepage from Applications. The output includes both catalog states,
the browser, SGI package history and profile checksums.

Add `--software-manager` to run the same checks using SGI's graphical
installer. The runner builds and attaches a small third CD with the current
helper, opens Software Manager on the logged-in user's display, clicks
**Start** and exits through SGI’s completion dialog. It saves the selection
and completion screenshots for both transactions.

For xosview and the UnZip 5.40 to 5.50 upgrade, build the small third CD
from the original 5.40 tardist. Use the same complete CD 4, release-specific
supplement and clean Mozilla bundle as above. [Prepare the third CD](../irix-installer/README.md#install-xosview-and-upgrade-unzip-in-software-manager).

```sh
IRIS_NO_IDLE=1 python3 lab/native-package/check-clean-desktop.py freeware-upgrade \
  --release "$release" --bundle "$bundle" --emulator "$bundle" --kernel "$browser_kernel" \
  --media "$supplement" --cd4 "$cd4" --old-unzip "$previous_iso" --output "$run"
```

The check drives Software Manager, opens xosview as `xiritest` and extracts
the same ZIP with both versions. It verifies 5.50 again after reboot, then
removes the two products and compares SGI history and the desktop table
with their pre-install values.

For a coexistence test, use `freeware-artwork` with the shared helper ISO
for `--old-unzip`. Run once with `--first-product xmahjongg` and once with
`--first-product unzip` for each release, with separate output directories.
The first product installed is also removed first. The game-first case
starts from the original supplement's single-product receipt. The
remaining product is exercised from the user's desktop before removal.

### GIMP across two xdm logins

Build the [GIMP medium](../irix-installer/README.md#install-gimp-125-from-the-freeware-cds).
Use the matching clean Mozilla bundle, release supplement and unstripped
kernel. The host check uses Pillow to compare the saved pixels with the
reopened window. Choose a fresh output directory for each release.

```sh
IRIS_NO_IDLE=1 python3 lab/native-package/check-clean-desktop.py freeware-gimp \
  --release "$release" --bundle "$bundle" --emulator "$bundle" --kernel "$kernel" \
  --media "$supplement" --gimp-media "$gimp_iso" --output "$run"
```

### In-place display upgrade

Use the v4 bundle and the matching v5 ISO to test a live upgrade on a
private overlay. The runner checks refusal at the active greeter, stops xdm,
applies the upgrade twice, rolls back twice and verifies file hashes, modes
and the original receipt. Add `--legacy-ownership` to exercise an older
installation without the created-file ledger.

```sh
python3 lab/native-package/check-clean-desktop.py display-upgrade \
  --base "$bootstrap" --media "$iso" --emulator "$emulator" \
  --output "$run" --release "$release" --bundle "$v4_bundle" --kernel "$kernel"
```

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

## FAM service update

Use the same kernel round-trip runner and a fresh output directory per release.
Pass `--upgrade-media .work/installers/indy-11.99.11/fam-service/xiri-${release}.iso`
and `--service-base-media /tmp/base-${release}.iso`. Build the latter with
`./xiri install-media` using v1 as `--upgrade-from`, v3 as `--native-package`
and the release's vendor payload. The runner applies it to a private copy of
the clean v1 CHD before testing v4.

The test interrupts the updater between the service script and example in
each direction. It checks new startup log messages from FAM's current PID, local file hashes,
ownership, modes and inodes. While logged into 4Dwm it launches SGI File
Manager on a fresh directory. It traces that process's reads and matches
both FAM messages to its directory subscription while NetBSD creates and
deletes a file. Each graphical boot also exercises the native ctwm login.

For the rc.conf.d removal check, use another disposable v4 installation.
Save its edited `/etc/rc.conf.d/xiri_famd`, stop xdm and FAM, and remove the
desktop using that installation's ownership mode. Compare the live file
with the saved edit and move it aside on the test disk. Reinstall from the
v4 CD. The live file should contain only `xiri_famd=YES` and a newline at
mode 0644, owned by root and wheel. The example should document
`xiri_famd_logfile`. Run the tracked uninstall and verify the live enable
file is gone and the saved edit is intact.

## Disk-full recovery and fresh v4 images

Build a v3-to-v4 CD from the current media scripts for each release, then
prepare the halted 11.99.11 bootstrap as above. Run each release on its
own disposable disk.

```sh
python3 lab/native-package/check-clean-desktop.py disk-full \
  --base "$bootstrap" --media "$iso" --emulator "$emulator" \
  --output "$fault_run" --release "$release"
```

The runner mounts the lab fixture at SCSI ID 5. Inside the guest it uses two
1 MiB tmpfs mounts, one for the live service settings and one for the
packaged examples. It fills each mount at the target write, checks the
write's ENOSPC diagnostic and the state of the transaction, removes the
filler and retries on the same mount. The release ISO supplies all installer
and updater code. The output includes the guest diagnostics in
`disk-full/space.log`. These disposable disks are used only for fault testing.

Repeat the command with `--full-target payload` and a fresh output directory.
This fills a separate filesystem under `/usr/local/share/xiri` as pax copies
the fonts, after the installer has published `/emul/irix`. The probe checks
the IRIX tree receipt, removal of the partial font staging directory and
the recovered font contents against the vendor manifest. It excludes the
generated `fonts.dir` from the byte comparison.

For the manual bundle, use a separate `install` run against a fresh copy
of the bootstrap, followed by `package-clean-desktop.py` and the `desktop`
run described above. New bundle manifests include the installed package
receipt and the installer ISO digest. The cold-boot check compares the
guest receipt with the manifest and exercises both xdm sessions.
