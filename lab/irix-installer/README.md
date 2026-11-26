# Original installer and persistent-home lab

This lab follows the user's selected workflow: original IRIX `inst`, then
Software Manager, installing xmahjongg so its own hooks create a **Freeware**
Icon Catalog entry. See the [software plan](../../docs/IRIX-SOFTWARE.md) and
[media findings](../../docs/results/2026-11-01-irix-freeware.md).

`manifest.json` records original inst/swmgr/SoftwareManager/iconcatalogedit,
their 37-path static n32 closure and the original shell templates/manuals.
`inputs.json` pins the selected CD4 xmahjongg/fw_common distributions and the
original generic `/var/inst/machfile`. Extracted bytes remain private in
`.work/irix-freeware/installed` and `.work/irix-freeware/package`.

## Use the complete Freeware CD 4 with a clean Mozilla Indy

Use the clean Mozilla CHD for your release and the matching installer
supplement. The supplement supplies SGI's installer tools and the Foundation
and overlay prerequisites. The second drive supplies the packages from your
own May 2004 Freeware CD 4. The test workstation has a local ISO of the
complete CD 4 tree from the [four-disc archive](../../docs/results/2026-11-01-irix-freeware.md).
To make one from an extracted disc, run `genisoimage -R -o may2004-cd4.iso /path/to/cd-4`
with the directory containing both `dist` and `relnotes`.

From the Xiri checkout, select the matching release and launch the Indy.
The launcher writes changes to its disk overlay across boots.

```sh
release=6.5.22f  # or 6.5.30f
.work/images/xiri-clean-indy-${release}-mozilla-20261125/run-iris.sh \
  --cdrom4 "$PWD/.work/images/xiri-cd4-indy-${release}-v5-20261124/freeware-cd4.iso" \
  --cdrom5 "$PWD/.work/irix-freeware/may2004-cd4.iso"
```

At the xdm greeter, run these commands on the NetBSD root console. Run
`prepare-live-base.sh` once on a fresh desktop with empty SGI history.

```sh
mkdir -p /cdrom /mnt/freeware
mount -rt cd9660 /dev/cd0a /cdrom
mount -rt cd9660 /dev/cd1a /mnt/freeware
sh /cdrom/prepare-live-base.sh /cdrom
sh /cdrom/xmahjongg.sh install /mnt/freeware
/emul/irix/usr/sbin/versions -r /emul/irix fw_xmahjongg
shutdown -r now
```

Log in as `xiritest`, select **Freeware** in Icon Catalog and double-click
**xmahjongg**. To remove it, log out, mount the two CDs again on the root
console and run `sh /cdrom/xmahjongg.sh remove /mnt/freeware`. On the
next login the Freeware page should retain **FreewareRelnotes**.

### Install with graphical Software Manager

Use the same clean Mozilla Indy, release-matched prerequisites and Freeware
disc. A newly built prerequisite CD includes the graphical helper.
With a November 24 supplement, add
`--cdrom6 "$PWD/.work/irix-freeware/swmgr-tools.iso"` to the IRIS command
above. The original helper ISO is ready on the test workstation. To
build the current helper, choose a fresh ISO path and attach that at ID 6.

```sh
genisoimage -quiet -R -V XIRI_SWMGR -o /path/to/new-swmgr-tools.iso \
  lab/irix-installer/xmahjongg.sh lab/irix-installer/desktop-artwork.sh lab/irix-installer/package-filetypes.mk
```

On a fresh desktop, mount the two installation discs and run
`sh /cdrom/prepare-live-base.sh /cdrom` once on the NetBSD root console.
Log in to xdm as `xiritest`. Back on the root console, create the third
drive’s device nodes on first use and mount the helper CD read-only.

```sh
test -b /dev/cd2a || (cd /dev && sh MAKEDEV cd2)
mkdir -p /mnt/gui
mount -rt cd9660 /dev/cd2a /mnt/gui
export DISPLAY=127.0.0.1:0 XAUTHORITY=/usr/people/xiritest/.Xauthority
sh /mnt/gui/xmahjongg.sh --gui install /mnt/freeware
```

When using a newly built prerequisite CD, run the helper from `/cdrom`.
Use the authority file for the logged-in desktop if xdm uses a different
location. The helper opens SGI Software Manager on that display and waits
while you operate it.

Choose **Customize Installation**. The inventory contains **Freeware Shared
Utilities** and **xmahjongg-3.6.1**. Keep the preselected shared index
and game subsystem, then click **Start**. When SGI reports success, choose
**Exit, installations completed**, then **OK**. Wait for the root console to
print the desktop table checksum before rebooting or logging in again.

To remove the game, close it, mount the same discs and run
`sh /mnt/gui/xmahjongg.sh --gui remove /mnt/freeware` from the root
console with the desktop display and authority set as above. Finish the
transaction in Software Manager and log in again to refresh the catalog.
Closing the installer before pressing **Start** leaves the game installed.
[Screenshots and results for both releases](../../docs/results/2026-11-25-swmgr.md).

## Build the xosview supplement

From the checkout, set `dist` to the `dist` directory on an owned May 2004
SGI Freeware CD 4. The ISO includes SGI's product files and the guest setup
script. The same Freeware product installs against either release's own
initialized SGI package history.

```sh
dist=/path/to/full-cd4/dist
mkdir -p .work/irix-freeware
genisoimage -quiet -R -V XIRI_XOSVIEW -graft-points \
  -o .work/irix-freeware/xosview-cd4.iso \
  xosview.sh=lab/irix-installer/xosview.sh \
  "dist/fw_xosview=$dist/fw_xosview" "dist/fw_xosview.idb=$dist/fw_xosview.idb" \
  "dist/fw_xosview.sw=$dist/fw_xosview.sw" "dist/fw_xosview.man=$dist/fw_xosview.man"
```

Attach it as the second CD on a November 25 catalog Indy. The guest script
checks the distribution hashes, invokes the original `inst` and verifies the
installed subsystem and both runtime files. [Guest commands and screenshots](../../docs/results/2026-11-25-indy-interaction.md#install-freeware-xosview).

## Install xosview and upgrade UnZip in Software Manager

Use a clean Mozilla Indy and the release-matched installer supplement from
the [CD 4 instructions](#use-the-complete-freeware-cd-4-with-a-clean-mozilla-indy).
Mount the supplement at `/cdrom`, the complete May 2004 Freeware CD 4 at
`/mnt/freeware`, and prepare the base once. Log in to xdm as `xiritest`.
On the NetBSD root console, open xosview’s product from the disc.

```sh
export DISPLAY=127.0.0.1:0 XAUTHORITY=/usr/people/xiritest/.Xauthority
swmgr=/emul/irix/usr/sbin/swmgr
"$swmgr" -V background:off -r /emul/irix -f /mnt/freeware/dist/fw_xosview -K '*' -I fw_xosview.sw.xosview
```

Choose **Customize Installation**, keep the selected subsystem, click
**Start**, then choose **Exit, installations completed** and **OK**.
The SGI distribution supplies an executable and X resources. Open the CPU
and memory meters from the ordinary user's winterm.

```sh
/usr/freeware/bin/xosview -xrm 'xosview*load: False' -xrm 'xosview*gfx: False'
```

For the upgrade, use the older SGI UnZip 5.40 distribution together with
the 5.50 product on CD 4. The tested third ISO is at
`.work/irix-freeware/unzip-5.40.iso` in this workspace. To rebuild it,
use the recipe below with a fresh output path. It packages the older
runtime and a ZIP archive for checking extraction. The builder
verifies the original tardist digest before reading the three distribution
files. [Archived SGI 5.40 tardist](https://ftp.zx.net.nz/pub/archive/sgi-freeware/fw-6.2/Dist/fw_unzip-5.40.tardist).

```sh
python3 lab/irix-installer/prepare-unzip-media.py /path/to/fw_unzip-5.40.tardist /path/to/new-unzip-5.40.iso
```

Attach `--cdrom6 "$PWD/.work/irix-freeware/unzip-5.40.iso"` to the Indy
launcher alongside the two discs. In the active Xiri session, run these
commands on the root console with the same display and authority as above.

```sh
test -b /dev/cd2a || (cd /dev && sh MAKEDEV cd2)
mkdir -p /mnt/previous
mount -rt cd9660 /dev/cd2a /mnt/previous
"$swmgr" -V background:off -r /emul/irix -f /mnt/previous/dist/fw_unzip -K '*' -I fw_unzip.sw.unzip
/emul/irix/usr/sbin/versions -r /emul/irix fw_unzip
sh /mnt/previous/unzip-upgrade.sh upgrade /mnt/freeware
/emul/irix/usr/sbin/versions -r /emul/irix fw_unzip
```

Apply each transaction in Software Manager. Leave 5.40 installed when
opening 5.50. The upgrade adds SGI’s ZIP filetype and saves the previous
desktop table. To check either version from winterm, run the following.

```sh
/usr/freeware/bin/unzip -v | head -1
/usr/freeware/bin/unzip -p /mnt/previous/sample.zip sample.txt
```

The second command should print `Xiri Freeware upgrade`. When extracting
to disk, both versions can warn about restoring timestamps. The qualification
compares the extracted file contents with the original. To remove both
products, close xosview and run the commands below on the root console.
After a reboot, mount the discs again and set the display and authority
for the current login first.

```sh
sh /mnt/previous/unzip-upgrade.sh remove /mnt/freeware
"$swmgr" -V background:off -r /emul/irix -f /mnt/freeware/dist/fw_xosview -K '*' -R fw_xosview.sw.xosview
```

## Install GIMP 1.2.5 from the Freeware CDs

Use a clean Mozilla Indy for the desired IRIX release. GIMP is on May 2004
CD 2. Its runtime, base data, scripts and base plug-ins require 19 Freeware
subsystems across the four discs. The [package inventory](gimp-cd.json)
records each subsystem, source disc and file checksum. With extracted
`cd-1/dist` through `cd-4/dist` under a common directory, create a private ISO.

```sh
python3 lab/irix-installer/prepare-gimp-media.py /path/to/cds /path/to/gimp-1.2.5.iso
```

The qualified ISO on the test workstation is shared by both releases.
Select the release to supply its matching desktop, original installer and
base prerequisites.

```sh
release=6.5.22f  # or 6.5.30f
.work/images/xiri-clean-indy-${release}-mozilla-20261125/run-iris.sh \
  --cdrom4 "$PWD/.work/images/xiri-cd4-indy-${release}-v5-20261124/freeware-cd4.iso" \
  --cdrom5 "$PWD/.work/irix-freeware/gimp-1.2.5.iso"
```

On the NetBSD root console, mount both discs. Run the base preparation
once on a fresh desktop. If the SGI installation history is already
initialized, skip the last command in this block.

```sh
mkdir -p /cdrom /mnt/gimp
mount -rt cd9660 /dev/cd0a /cdrom
mount -rt cd9660 /dev/cd1a /mnt/gimp
sh /cdrom/prepare-live-base.sh /cdrom
```

Log in through xdm as `xiritest`. From the root console, start SGI Software
Manager on that user's display.

```sh
export DISPLAY=127.0.0.1:0 XAUTHORITY=/usr/people/xiritest/.Xauthority
sh /mnt/gimp/gimp.sh /mnt/gimp
```

Choose **Customize Installation**, leave the runtime selections checked,
then click **Start**. At completion choose **Exit, installations completed**
and **OK**. Wait for the helper to print the desktop table checksum. It
applies the Xiri mapping permissions to eight package libraries and merges
GIMP's SGI artwork. For later xmahjongg or UnZip changes on this desktop,
use the helpers from the GIMP ISO, which recognize its artwork receipt.

Log out and back in to refresh Icon Catalog. Open **Freeware** and
double-click **gimp**. Accept the first-run defaults to create
`~/.gimp-1.2` for the logged-in user. Use **File → Open** (Ctrl+O) to
open an image. [Two-release editing and reopen checks](../../docs/results/2026-11-26-freeware-gimp.md).

## Install xmahjongg and UnZip together

Use the release-specific supplement at SCSI ID 4, Freeware CD 4 at ID 5
and the shared helper ISO at ID 6. On each boot, mount the three discs
at `/cdrom`, `/mnt/freeware` and `/mnt/previous` as above. Use the two
helpers from **the same shared ISO** for subsequent changes to either product.
It includes both package helpers, the original UnZip 5.40 runtime and a
sample ZIP. Build it from the original tardist with `prepare-unzip-media.py`
as described above, or attach the workspace copy at
`.work/irix-freeware/shared-artwork.iso`.

Prepare the base on a fresh guest. After login through xdm, set the
display and X authority on the NetBSD root console. The following example
installs the game, installs the older UnZip and upgrades it from CD 4.

```sh
sh /mnt/previous/xmahjongg.sh --gui install /mnt/freeware
/emul/irix/usr/sbin/swmgr -V background:off -r /emul/irix -f /mnt/previous/dist/fw_unzip -K '*' -I fw_unzip.sw.unzip
sh /mnt/previous/unzip-upgrade.sh upgrade /mnt/freeware
```

Use `sh /mnt/previous/xmahjongg.sh --gui remove /mnt/freeware` or
`sh /mnt/previous/unzip-upgrade.sh remove /mnt/freeware` for removal.
Log out and back in to load the updated desktop types. The helpers track
the packages in `/emul/irix/var/inst/xiri-filetypes`, preserve the initial
desktop table and rebuild it with the surviving SGI package rules.
They recognize earlier single-package receipts and stop if the live table
has an unrelated edit.

## Install CD 4's xmahjongg into the live Indy desktop

Use a private copy of the v5 CHD for the matching vendor release. Boot the
Indy kernel and matching module from NetBSD `xiri` revision `df8a46a636f`.
The packaged v5 kernel predates the installer fixes. Build the private CD
from the matching original-media donor, Foundation, overlays and the Freeware
distribution. Run this from the Xiri checkout.

```sh
release=6.5.22f  # use 6.5.30f for the R5000 image
mkdir -p .work/inst-media
python3 lab/irix-installer/prepare-media.py --release "$release" \
  --donor ".work/donors/irix-$release-original-media/irix-donor.chd" \
  --desktop-manifest ".work/imports/irix-$release-v1/manifest.json" \
  --dist .work/irix-freeware/package/cds/cd-4/dist \
  --base-media-root "$HOME/Downloads/IRIX media" \
  --instigator ../prismatic/target/release/instigator \
  --output ".work/inst-media/$release.iso"
```

Attach the CD at SCSI ID 4. At the xdm greeter, use the NetBSD root console
for package maintenance. On a fresh target the following installs the base
prerequisites and then the game.

```sh
mkdir -p /cdrom
mount -r -t cd9660 /dev/cd0a /cdrom
sh /cdrom/prepare-live-base.sh /cdrom
sh /cdrom/xmahjongg.sh install /cdrom
```

The first command script uses SGI's `-Y` file selection across eight
prerequisite subsystems. Their entries in `versions` describe a partial
installation. The setup installs SGI make and nawk, supplies NetBSD device
numbers for the chroot and sets executable modes on the three libraries
mapped by the catalog helper. The game transaction runs in `/emul/irix`.
SGI creates the history and Freeware symlink there. Log in as `xiritest`,
open **Icon Catalog → Freeware** and double-click **xmahjongg**.

Close the game and log out before removal. At the root console run
`sh /cdrom/xmahjongg.sh remove /cdrom`. The Freeware release notes have
their own subsystem and stay installed. The two transaction logs and current
game history are under `/emul/irix/var/inst/xiri-xmahjongg/`.

During installation the package's own exit command invokes SGI make in the
filetype directory. A temporary lowercase `makefile` compiles the new artwork
using SGI fftr. The installer merges it ahead of the saved desktop table
and publishes the result by rename. Removal restores that saved table. An
existing lowercase site makefile or an independently changed desktop table
requires review. The Freeware release-note script uses NetBSD utilities and
IRIX shell redirections on the same scratch filenames. The installer shares
native `/tmp` with the chroot for the transaction and checks that the mount
point is empty first.

## Repeat the clean Indy installer check

To check the timezone exit command independently, copy `usr/bin/zic` from
the matching IRIX overlay into the guest and make it executable. On NetBSD,
run `sh check-zic-links.sh /absolute/path/to/zic`. The check compiles a
zone and alias, compares their device, inode and link count, then removes
the primary and verifies the surviving alias is nonempty.

Use the release that matches the private guest. From the Xiri repository
root, with the matching desktop import already built, prepare the
installer supplement from the original-media donor and May 2004 CD 4.

```sh
release=6.5.22f  # or 6.5.30f
mkdir -p .work/inst-media
python3 lab/irix-installer/prepare-media.py --release "$release" \
  --donor ".work/donors/irix-$release-original-media/irix-donor.chd" \
  --desktop-manifest ".work/imports/irix-$release-v1/manifest.json" \
  --dist .work/irix-freeware/package/cds/cd-4/dist \
  --output ".work/inst-media/$release.iso"
```

The builder verifies the donor and CD hashes, checks shared library
digests against the desktop manifest, and records the selected files in
`vendor.json`. It creates a new ISO. The installer supplement includes the
original `/sbin/stat` used during bootstrap. The input history database
comes from the target itself.

The clean v4 NetBSD images keep `mkdir`, `ls`, `mv` and `ln` in `/bin`.
SGI's bootstrap resets PATH and searches `/usr/bin` for them. The media
builder includes the [native utility setup](../irix-installer-helpers/setup-native-paths.sh).
It preserves existing paths and reports conflicts.
If you keep the native `/sbin/stat` alias across boots on a private v4
image, also install the [updated PTY setup](../../runtime/libexec/setup-pty.sh)
as `/usr/local/libexec/xiri/setup-pty.sh`, mode 0555. The v4 boot
service can otherwise select SGI's stat and leave xdm login without PTYs.

Boot a **disposable** Indy target with the matching supplementary ISO at
SCSI ID 4. As root, mount it, unpack the supplement and ask the original
installer to select the software and report conflicts. Clearing selections
before quitting produces an unattended return to the shell.

```sh
mkdir -p /cdrom
mount -r -t cd9660 /dev/cd0a /cdrom
(cd / && pax -rzpe -f /cdrom/installer.tgz)
sh /cdrom/setup-native-paths.sh
if test ! -e /sbin/stat && test ! -L /sbin/stat; then
    ln -s /emul/irix/sbin/stat /sbin/stat
fi
export HOME=/ USER=root LOGNAME=root SHELL=/bin/sh TERM=vt100 LANG=C TZ=UTC
export PATH=/usr/local/bin:/usr/X11R7/bin:/bin:/sbin:/usr/bin:/usr/sbin
printf '%s\n' 'keep *' 'install fw_xmahjongg.sw.xmahjongg fw_common.sw.index' \
  'conflicts' 'keep *' quit >/var/tmp/xiri-inst-plan
/emul/irix/usr/sbin/inst -M -r /emul/irix -f /cdrom/dist -c /var/tmp/xiri-inst-plan
/emul/irix/usr/sbin/versions -r /emul/irix fw_xmahjongg
```

The clean v4 kernel predates the MIPS conversion and IRIX file-operation
fixes. See the [dual-release results](../../docs/results/2026-11-24-indy-inst.md)
for the tested kernel and the prerequisites reported by SGI.

To check that SGI can write and read its own installation history, use an
empty alternate root on a disposable guest with module `da98b7d4268` or
later. The Freeware CD's selection files have no base-package prerequisites.

```sh
target=$(mktemp -d /var/tmp/xiri-inst.XXXXXX)
mkdir -p "$target/var/inst"
cp /emul/irix/var/inst/machfile "$target/var/inst/"
inst=/emul/irix/usr/sbin/inst
versions=/emul/irix/usr/sbin/versions
for action in install remove; do
    printf '%s\n' 'keep *' "$action fw_common.sw.selections" conflicts go 'keep *' quit >"$target.commands"
    "$inst" -M -r "$target" -f /cdrom/dist -c "$target.commands" </dev/null
    "$versions" -r "$target" fw_common
    ls -l "$target/var/inst/hist"
    if test "$action" = install; then
        sha256 "$target/usr/freeware/relnotes/selections/gimp"
    else
        test ! -e "$target/usr/freeware/relnotes/selections/gimp" || exit 1
    fi
done
```

After installation, look for the installed product in `versions` and the
sample file digest in the release results. After removal the product row and
sample file disappear. The target retains its own history database.

To reproduce the xmahjongg prerequisite check, add the following two options
to the host's media-builder command above and choose a new output filename.

```sh
--base-media-root "$HOME/Downloads/IRIX media" \
--instigator ../prismatic/target/install-server/instigator
```

The builder checks the [original disc hashes](base-media.json) and copies
the product descriptors, inventories and software archives from Foundation 1
and overlays 1 and 2 for the chosen release. Both overlay discs are needed.
On the guest, use a new alternate root and request the complete selection.

```sh
target=$(mktemp -d /var/tmp/xiri-base.XXXXXX)
mkdir -p "$target/var/inst"
cp /emul/irix/var/inst/machfile "$target/var/inst/"
cat >"$target.commands" <<'EOF'
keep *
install c++_eoe.sw.lib eoe.sw.base eoe.sw.efs compiler_eoe.sw.cpp compiler_eoe.sw.lboot compiler_eoe.sw.lib compiler_eoe.sw.unix x_eoe.sw.eoe fw_common.sw.index fw_xmahjongg.sw.xmahjongg
conflicts
keep *
quit
EOF
/emul/irix/usr/sbin/inst -M -r "$target" \
    -f /cdrom/foundation -f /cdrom/overlay -f /cdrom/dist -c "$target.commands"
```

The expected report is `No conflicts`. The independent `go` trial on a
private guest reached an IRIX device-creation hook. Its results and the
observed game install and removal are in the [installer report](../../docs/results/2026-11-24-indy-inst.md).

### Reproduce the catalog launch on a disposable Indy

The graphical test used NetBSD fork commit `6e9a69e852f` and an initially
empty target at `/var/tmp/xiri-pkg`. From the release-matched `/emul/irix`,
copy `lib`, `lib32`, `sbin`, `usr/lib32`, `usr/lib/desktop`,
`usr/lib/filetype`, `usr/sbin/iconcatalogedit`, `etc/passwd` and `etc/group`
to the same paths in the target. Preserve modes and links. The only initial
file under `var/inst` is `machfile`. Inside the target create `dev/null`
and `dev/zero` with the major/minor numbers of those devices on the
running NetBSD guest. Use `/usr/bin/stat -f %Hr /dev/null` for the major
and `/usr/bin/stat -f %Lr /dev/null` for the minor, then repeat for zero.
The absolute name selects NetBSD's format syntax even when SGI's
`/sbin/stat` is on PATH. This lets the SGI loader run inside `chroot`.

Insert `go` after `conflicts` in the command file above. After the base
device hook stops, verify the game with `versions -r "$target" fw_xmahjongg`.
Reopen `inst` on that target with CD 4 as its distribution. Choose
**Ignore the previous installation session**, then **Execute them now**
at the outstanding exit-commands prompt. Check the resulting Freeware
directory on disk. Both the game and its catalog link came from this
transaction.

The test guests exposed the package's `usr/freeware` and SGI-created
Freeware page with read-only NetBSD null mounts. Native `/usr/freeware`
pointed to the package tree. The desktop and its native file monitor could
then see the same files. Log in through xdm, select **Freeware** in Icon
Catalog, and double-click **xmahjongg**. The release report records the
observed window, user, and remaining OS installation issue. For removal,
close the game and use CD 4 as the source with `remove fw_xmahjongg.sw.xmahjongg`,
`conflicts` and `go` in the same alternate root.

### Test the device exclusion and game artwork

On a fresh private target, use the same ten selections with `go`. Add
`-X /dev` to the original `inst -M -r "$target"` invocation. Record
`/usr/bin/stat -f '%N %Hr,%Lr %i' "$target/dev/null" "$target/dev/zero"`
and the same values for the native nodes before and after. Check the
full installer output for exit-command errors as well as the installed
subsystem rows from `versions -r "$target" eoe.sw.base fw_xmahjongg`.

The base install writes three of the catalog helper's libraries with mode
0444. On the tested alternate roots these are ordinary files under
`$target/usr/lib32`. Set `libgen.so`, `libCsup.so` and `libC.so.2` there to
0555 and verify their digests against the files from that installation.
The original hook can then run inside that root. Record both the return
status and the resulting link.

```sh
chroot "$target" /usr/sbin/iconcatalogedit -add \
    "$target/usr/freeware/bin/xmahjongg" -syspage Freeware
readlink "$target/usr/lib/desktop/iconcatalog/pages/C/Freeware/xmahjongg"
```

To compile the artwork outside the partially installed base, use the
matching desktop's original SGI compiler. The following builds a
candidate table in a fresh work directory on the guest.

```sh
types=/emul/irix/usr/lib/filetype
fftr=/emul/irix/usr/sbin/fftr
work=$(mktemp -d /var/tmp/xiri-art.XXXXXX)
cp -p "$types/desktop.otr" "$work/baseline.otr"
(cd "$target/usr/lib/filetype/install" &&
    "$fftr" -o "$work/game.otr" xmahjongg.ftr) &&
    "$fftr" -o "$work/desktop.otr" "$work/game.otr" "$work/baseline.otr"
sha256 "$work/game.otr" "$work/desktop.otr"
```

The public v4 desktop already supplies the compiler's `/usr/bin/nawk`
alias and the generic executable drawings in the parent `iconlib` directory.
On the disposable test desktop, replace the active table by renaming
a complete candidate on the same filesystem. Log in to start a new
catalog process. Retain the original table for the rollback control.
The [follow-up results](../../docs/results/2026-11-24-indy-inst-followup.md)
give the checks against SGI's filetype library.

To rebuild the conversion checks, run
`python3 lab/irix-installer/build-cvt-probes.py TOOLDIR NEW_OUTPUT`.
Copy the two binaries into the disposable guest and run each one. Exit zero
means all 52 conversions matched the expected binary64 bits and inexact
status. The o32 observer uses paired registers and n32 uses odd wide registers.

## Earlier installer checkpoints

The observer clones the clean ordinary desktop/pipe checkpoint, checks all
inherited and staged hashes, and uses the unchanged qualified pipe kernel.
It creates an ordinary native account under `/usr/people`, checks repeated
setup, writes a home file through native ksh and reads it through original
IRIX asa. Native ABI controls run before and after.

Original `inst` is attempted as root with `HOME=/`, first using its documented
`-H` hardware report, then `-n -M -r /emul/irix -f /cdrom/dist -c` with a
list/quit command file. These are bounded startup/distribution observations,
not an installation success. The native runner owns and removes the process
group; the disposable guest is halted in a finally block. Full hook execution,
GUI Software Manager, catalog launch, reboot persistence and removal remain
separate acceptance work.

```sh
PYTHONDONTWRITEBYTECODE=1 python3 scripts/probe-irix-installer.py
```

Account setup is [setup-xiri-user.sh](../../scripts/setup-xiri-user.sh).
The native account uses `/bin/ksh` and NetBSD's skeleton. IRIX desktop state
must be generated by the clients under that same persistent home. The helper
does not alter the administrative root account or any existing account with a
different home. Its optional numeric UID is used only to make lab checks
repeatable.

## Observed boundary

The [first result](../../docs/results/2026-11-01-irix-installer.md) verifies
account setup, native/foreign shared-file access and cold-boot persistence.
Original inst faults before output: a 1 MiB /dev/zero mmap with SHARED,
AUTOGROW and AUTORESRV is rejected, then libinst writes through MAP_FAILED.
The second probe uses the existing checked mmap tracer and known-fault
controls; both guests halt cleanly.

```sh
PYTHONDONTWRITEBYTECODE=1 python3 scripts/probe-irix-installer-fault.py
PYTHONDONTWRITEBYTECODE=1 python3 scripts/qualify-irix-installer.py \
  .work/irix-installer/runs/ci-e8jv2xtk \
  .work/irix-installer/runs/mmap-ci-pq57kpty \
  --output docs/results/2026-11-01-irix-installer.json
```

## Shared-mapping follow-up

[The new checkpoint](../../docs/results/2026-11-01-irix-installer-shared.md)
uses `probe-irix-installer-shared.py` with a separate kernel pin and fresh copy
of the same clean desktop seed. It passes the previous mmap crash. `inst -H`
prints an incomplete hardware report; the distribution dry run emits a fatal
`sproc` child-launch error before reading packages, despite exiting zero.
Signal-handler registration and hardware queries also remain incomplete.
`qualify-irix-installer-shared.py` checks the original trap instruction,
ordered trace, native/home controls and clean shutdown. The earlier observer,
tracer and their qualified source hashes remain unchanged.

The [sproc reference](../../docs/results/2026-11-01-irix-sproc-reference.md) now
qualifies 112 original-IRIX executions / 200 records for the next process
requirement. It establishes the armed exec/exit release distinction, private
PRDA/LOCAL pages and shared mapping updates. NetBSD sproc implementation and
a subsequent original-inst retry remain pending.


## Sproc follow-up

The [bounded sproc checkpoint](../../docs/results/2026-11-01-irix-sproc.md)
now lets original inst create its child and execute native `/bin/sh`. Run
`scripts/probe-irix-installer-sproc.py` and check the resulting directory with
`scripts/qualify-irix-installer-sproc.py --output FILE`. Inputs, commands and
home setup are unchanged. The [accepted trace](../../docs/results/2026-11-01-irix-installer-sproc.md)
identifies F_DUPFD EINVAL during pipe setup, followed by repeated gettimeofday
ENOSYS and a bounded timeout. Native helper searches also omit `/bin` for
ls/mkdir. No package has yet been installed. Pair calls by PID/LWP now that
the trace includes a child; successful exec register contents are not an
ordinary syscall errno return.


The [F_DUPFD follow-up](../../docs/results/2026-11-01-irix-installer-dupfd.md)
uses `probe-irix-installer-dupfd.py` and `qualify-irix-installer-dupfd.py`.
Both pipe duplications now succeed. The remaining capture shows a bounded
gettimeofday/select loop and unchanged helper search paths at that checkpoint.
The [time follow-up](../../docs/results/2026-11-01-irix-installer-time.md) uses
`probe-irix-installer-time.py` and `qualify-irix-installer-time.py`: time calls
now succeed, while the bounded dry run still times out. The
[helper follow-up](../irix-installer-helpers/README.md) captures full argv,
output, exit and process state. Four native utility aliases let the embedded
bootstrap exit zero, but the foreign parent leaves it unreaped. The
[signal lab](../irix-signal/README.md) now measures registration/delivery,
return and the callback's wait-any mode on original IRIX, with the measured
NetBSD subset qualified in the follow-up below. Installer qualification and native
`stat -qd` also remains incompatible. This is not distribution-read or
installation success.
No package is installed yet.


The [traditional-signal checkpoint](../../docs/results/2026-11-01-irix-signal.md)
now qualifies the measured handler and wait-any subset on NetBSD. The
installer is not retried in that cycle: the user chose to prioritize
[importing installed applications and their existing catalog registration](../irix-installed-desktop/README.md).
Retain this lab for later distribution reading, native utility semantics,
package history and original registration hooks. Copying installed files
does not qualify the installer or its lifecycle.
