# Native package for NetBSD/sgimips

`./xiri package-native` assembles the native half of Xiri independently of a
prepared desktop CHD. It consumes explicitly named, hash-pinned kernel/module,
FAM, rpcbind and Newport driver artifacts, verifies the public NetBSD 11.0
sets, and cross-builds the maintained session helpers. It packages no IRIX
programs, user accounts, passwords or homes.

The first [profile](../profiles/netbsd-sgimips-native-v1.json) targets o32
NetBSD/sgimips 11.0 userland and X sets with the qualified MIPS64 11.99.9
kernel. It pins the kernel and module as a pair. The native Type1/FPU signal
correction is in this kernel; no replacement FreeType or libXfont is needed.
The supplied Newport driver includes the texture-coordinate and software
fallback corrections. FAM supplies native user identity and IRIX path mapping;
rpcbind includes the loopback-bind correction.

## Build inputs

Provide a JSON file mapping these artifact names to explicit local file paths:

| Key | Artifact and source record |
| --- | --- |
| `kernel` | Native `/netbsd`; [native-wait build](../lab/native-wait/build.json) |
| `boot` | `/netbsd.boot` wrapper from that same build |
| `module` | `compat_irix_o32.kmod`; [desktop-controls module build](../lab/irix-desktop-controls/module-build.json) |
| `famd` | Multi-user daemon; [FAM source and builder](../lab/native-fam/README.md) |
| `rpcbind` | Patched native utility; [rpcbind source and builder](../lab/native-rpcbind/README.md) |
| `newport` | Xorg 1.10.6 / video ABI 10 driver; [Newport source](../lab/newport-text/README.md) |

These are supplied artifacts, not silently rebuilt from a newer branch tip.
Their original source revisions, source-file hashes and dirty-build records
remain in the referenced provenance; packaging does not relabel them as new
builds. A replacement kernel/module or toolchain requires an audited profile
and new qualification.

For example, with `native-inputs.json` containing those six paths:

```sh
./xiri package-native \
  --artifacts native-inputs.json \
  --compiler .work/netbsd-irix-build/tools/bin/mipseb--netbsd-gcc \
  --sets .work/netbsd-11.0/sgimips/binary/sets \
  --output .work/packages/netbsd-sgimips-native-v1
```

The output directory must be new. The compiler and sets are hash-checked
before building. Build inputs are `base`, `etc`, `comp`, `xbase`, `xetc`,
`xfont`, `xserver` and `xcomp`; the installed target does not need the compiler
sets. `runtime/Makefile` accepts separate X11 include/link flags for the
cross sysroot, while retaining the original native defaults and target rpath.
No previous image or selected-image pointer is consulted. Temporary sysroots
and compiler output are removed on completion or handled failure.

## Output and checks

- `native.tar.gz`: normalized archive with `kernel/` and `root/` payloads,
  read-only preflight, file/dependency tables and checksums.
- `manifest.json`: every file's hash, mode, destination and installation policy;
  native ELF dependency closure; set/compiler/source hashes and artifact pins.
- `build.log`: the actual build commands and compiler diagnostics.

The first package has 47 payload entries and checks 80 native prerequisites.
It records 281 library dependency edges. All native ELF userland files are
checked as big-endian MIPS o32. Required stock libraries, display/login tools,
xdm/PAM resources and the bitmap Courier font are accounted for explicitly.
Xorg's wider dynamically loaded module set still comes from the required
standard X sets; the ELF closure alone cannot discover every runtime plugin.

Unpack into a new directory with native `pax -rz -pe -f native.tar.gz`, then run
`sh preflight.sh` there. This checks package bytes, the running kernel's full
build-version digest, the on-disk kernel and the required native files.
`--root /path/to/target` checks an offline root using NetBSD tools; it omits
running-kernel assertions. `--verify-installed` also checks installed payload
types, modes, links and hashes, allowing administrator-owned configuration to
differ. These checks neither install files nor change services.

The [6.5.22f guest qualification](results/2026-11-14-native-package.md) passes
installation and repeat installation, configuration/account preservation,
full-screen desktop and shell, File Manager, logout/relogin, native ctwm and
clean shutdown. The package also rejects wrong kernels and missing native
prerequisites. That result applies to the original 11.99.9 profile.
The [Indy/R5000 application trial](results/2026-11-14-r5000-6.5.30.md) now
passes core desktop/shell, logout/relogin and native ctwm checks with a newer
module that admits the donor's MIPS IV n32 interpreter. That module also passes
6.5.22f desktop regression checks. The existing native package retains its qualified 6.5.22
module pin; it is not silently repinned by that trial. The separate
[O2/R10000 candidate](../lab/irix-o2/README.md) uses a separate IP32 kernel/module
and native profile, the stock `crime` driver and `ip3xboot`; it does not use the
Indy's patched Newport driver. The subsequent [O2 disk and Ethernet qualification](results/2026-11-23-o2-io.md)
covers both release lines.

## Installation boundary

The historical native fixture qualified package assembly and preflight. The
11.99.11 clean Indy installer below adds target space checks, original-file
backups, conflict recovery and repeat installation. The desktop removal
procedure below uses the same input archives. A [native helper upgrade](#upgrade-native-helpers-on-an-installed-indy)
uses media built from the installed and candidate native packages. Boot the
matching kernel before installing its userspace.

Defaults under `/etc/xiri` must be installed only if absent. Update `.example`
files for review. Service/module examples are opt-in: preserve `rc.conf`,
`modules.conf`, `ttys`, passwords, accounts and homes. Activation must create
the declared native aliases, import the chosen vendor payload, generate IRIX
account tables, devices, font indexes and filetypes, then let each ordinary
user select the desktop. See [runtime integration](../runtime/README.md).

We maintain **two release lines, IRIX 6.5.22 and IRIX 6.5.30**. Each needs its
own donor, profile, qualification and CHD. A common native package may serve
both after separate desktop checks; neither version replaces the other.
See the [complete installation plan](XIRI-INSTALLATION.md) for clean-target
installation and the separate original-media donor processes.

## Install or update an Indy to v6

Choose the installer for the IRIX release on the target. The local CDs are
`.work/installers/indy-11.99.11/utime-v6/xiri-6.5.22f.iso` and
`.work/installers/indy-11.99.11/utime-v6/xiri-6.5.30f.iso`.
The base package owns the Indy kernel, PROM boot file and IRIX module.
Mozilla remains optional. Both browser editions use the same base module.
[Clean CHDs, launchers and test records](results/2026-11-26-indy-v6.md).

**Existing v5 desktop.** Mount the matching v6 CD on the NetBSD root
console. Run the update and reboot after it reports completion.

```sh
mkdir -p /cdrom
mount -rt cd9660 /dev/cd0a /cdrom
sh /cdrom/upgrade.sh && shutdown -r now
```

The updater checks the original v5 native package, the release-specific
desktop receipt and, when installed, the Mozilla receipt. It verifies the
boot files before replacing them and records which package owns them. It
preserves user homes and site settings. To roll back, mount the same v6 CD
again and run `sh /cdrom/upgrade.sh --rollback && shutdown -r now`.
An interrupted operation can be repeated from the native root console using
the same CD and direction. If the updater reports an unexpected boot file,
compare its checksum with the [release records](results/2026-11-26-indy-v6.json);
a disk already modified with the earlier manual module-only procedure should
first be restored to its recorded v5 module using that procedure's backup.

**Fresh installation.** Prepare a clean NetBSD 11.0/sgimips target with the
v6 native package using the stock bootstrap below. On the booted target,
mount the release-matched installer as above, then run one of these commands:

```sh
sh /cdrom/install.sh             # base desktop
sh /cdrom/install.sh --mozilla   # base desktop plus the original SGI browser
```

Select the Xiri session for participating users and reboot. On the ready-made
CHDs, `xiritest` already has the Xiri session and `netbsdtest` has native
ctwm. Both test passwords equal the username. To remove the browser later,
use `sh /cdrom/install.sh --remove-mozilla` on the v6 CD.

**Build the media locally.** Stage the five unchanged userspace artifacts
from the v5 native package, and the verified boot pair and module from
their local archives. From the Xiri checkout:

```sh
inputs=$(mktemp -d)
v5=.work/packages/netbsd-sgimips-indy-11.99.11-glx-v5
v6=.work/packages/netbsd-sgimips-indy-11.99.11-utime-v6
profile=profiles/netbsd-sgimips-indy-11.99.11-utime-v1.json
tar -xzf "$v5/native.tar.gz" -C "$inputs" root
tar -xJf .work/modules/irix-threaded-stack-guard-20261125/indy-kernel-module.tar.xz \
    -C "$inputs" netbsd netbsd.boot
isoinfo -R -i .work/modules/irix-utime-20261126/utime.iso -x /compat_irix_o32.kmod >"$inputs/module"
jq --arg dir "$inputs" '.artifacts | with_entries(
    .value = ($dir + (if .key == "module" then "/module"
                     elif .key == "boot" or .key == "kernel" then .value.destination
                     else "/root" + .value.destination end)))' "$profile" >"$inputs/paths.json"
./xiri package-native --profile "$profile" --artifacts "$inputs/paths.json" \
    --compiler .work/netbsd-irix-build/tools/bin/mipseb--netbsd-gcc \
    --sets .work/netbsd-11.0/sgimips/binary/sets --output "$v6"
```

Use a new output directory when reproducing published artifacts. For each
release, set `release` and `disc` as in the v5 loop below and run:

```sh
./xiri install-media --native-package "$v6" --upgrade-from "$v5" \
    --previous-media ".work/installers/indy-11.99.11/mozilla-v5/xiri-$release.iso" \
    --vendor-payload ".work/imports/irix-$release-v1" \
    --clock-overlay "$HOME/Downloads/IRIX media/$disc" \
    --instigator ../prismatic/target/release/instigator \
    --mozilla-payload ".work/imports/irix-$release-mozilla-v1" \
    --mozilla-network .work/modules/irix-browser-network-20261125/browser-network.iso \
    --output ".work/installers/rebuilt-v6/xiri-$release.iso"
```

The native packager checks the pins in the v6 profile. The media builder
checks that the v5 and v6 archives agree on native userspace, Mozilla
userspace and the release-specific desktop payload before building the
update. For fresh target preparation, pass `--native-package "$v6"` and
`--keep-target` to the [stock bootstrap](../lab/native-package/README.md#bootstrapping-a-stock-target).

## Clean installation on an emulated Indy

The Indy v5 package targets NetBSD 11.0/sgimips userland and X sets with
the 11.99.11 kernel and boot-loaded Xiri module. It uses accelerated Newport
at 1280×1024. The stock bootstrap prepares this target from the recorded
NetBSD installation. [Bootstrap procedure](../lab/native-package/README.md#bootstrapping-a-stock-target)

Build the native archive using the GLX profile. Supply the six Indy artifacts
listed above and two additional entries in your artifact path JSON. The
`xorg` entry points to the qualified Xorg executable and `glx` points to
its matching `libglx.so.0`. The builder takes the original display files
from the verified NetBSD X server set for rollback.
[Indy GLX profile](../profiles/netbsd-sgimips-indy-11.99.11-glx-v1.json) ·
[Display build and hashes](results/2026-11-24-indy-glx.md)

```sh
./xiri package-native --profile profiles/netbsd-sgimips-indy-11.99.11-glx-v1.json \
    --artifacts native-inputs.json \
    --compiler .work/netbsd-irix-build/tools/bin/mipseb--netbsd-gcc \
    --sets .work/netbsd-11.0/sgimips/binary/sets \
    --output .work/packages/netbsd-sgimips-indy-11.99.11-glx-v5
```

Build one CD per vendor release from the existing verified donor import and
the same release's original Overlay 1. The builder checks the disc SHA256,
extracts four files using Instigator, and runs the host's `mkfontdir` to
index the three bitmap fonts. The updater is optional for fresh installs.

```sh
for release in 6.5.22f 6.5.30f; do
    case "$release" in
        6.5.22f) disc="6.5.22/IRIX 6.5.22 Overlay 1 of 3.iso" ;;
        6.5.30f) disc="6.5.30/IRIX 6.5.30 Installation Tools and Overlays (1 of 3).iso" ;;
    esac
    ./xiri install-media \
        --native-package .work/packages/netbsd-sgimips-indy-11.99.11-glx-v5 \
        --upgrade-from .work/packages/netbsd-sgimips-indy-11.99.11-fam-service-v4 \
        --vendor-payload ".work/imports/irix-${release}-v1" \
        --clock-overlay "$HOME/Downloads/IRIX media/$disc" \
        --instigator ../prismatic/target/release/instigator \
        --output ".work/installers/indy-11.99.11/glx-v5/xiri-${release}.iso" || exit 1
done
```

Attach one ISO as a SCSI CD-ROM. On the corresponding booted Indy, log in as
root on the console and run the following commands. Use a separate target
disk for each release. The 6.5.22f medium includes the optional Acrobat import.
The 6.5.30f medium uses the desktop and fonts import.

```sh
mkdir -p /cdrom
mount -t cd9660 -o ro /dev/cd0a /cdrom
sh /cdrom/install.sh
```

The installer verifies the media and running kernel, checks available space,
stages and verifies the vendor files and catalog links, and installs the native
runtime. It saves replaced native files under `/var/db/xiri-install/original`.
On a stock NetBSD X installation this includes the original Newport driver
symlink. It generates IRIX account mappings, font indexes and filetypes. It
installs missing rc.conf.d defaults for rpcbind, PTYs, FAM, sessions and xdm.
Existing service settings and files under `/etc/xiri` take precedence. An
existing unmanaged vendor tree or conflicting `/usr/lib/desktop` requires
administrator review. Correct the reported conflict and repeat
`sh /cdrom/install.sh` with the same release and native build. A finished
installation has a receipt at `/var/db/xiri-install/installed`.

### Install or remove Mozilla on the Indy

Use the installer CD for the guest's IRIX release. To build a browser-capable
CD, add these three arguments to the v5 build command above and choose a new
output path. The builder uses `isoinfo` to read the native network update.

```sh
        --mozilla-payload ".work/imports/irix-${release}-mozilla-v1" \
        --mozilla-kernel .work/modules/irix-threaded-stack-guard-20261125/indy-kernel-module.tar.xz \
        --mozilla-network .work/modules/irix-browser-network-20261125/browser-network.iso
```

Build the [browser import](results/2026-11-24-indy-mozilla.md#build-the-matching-payload)
from the same installed donor as the desktop. The R4400 uses the 6.5.22f
import and the R5000 uses 6.5.30f. An existing v4 installation needs the
[v5 display upgrade](#upgrade-or-roll-back-the-indy-display-package) first.
On the guest, mount the matching CD as
above. Plain `sh /cdrom/install.sh` selects the base desktop. For a fresh
install with Mozilla, or to add it to an existing v5 desktop, run as root:

```sh
sh /cdrom/install.sh --mozilla && shutdown -r now
```

At xdm, log in to a Xiri session and double-click **Mozilla** in
**Icon Catalog → Applications**. A new profile opens **Welcome to Xiri**.
Try `http://info.cern.ch/hypertext/WWW/TheProject.html` with **Ctrl+L**. Public hostname lookups use
the guest's NetBSD resolver and the `xiri_hosts` rc.d service.

The same clean installation can run SGI's original installer against
Freeware CD 4. Use the installer supplement for the guest's release and
attach your Freeware disc as the second CD. You can install xmahjongg from
the root console or use the graphical installer in the active Xiri desktop.
[Terminal installation](../lab/irix-installer/README.md#use-the-complete-freeware-cd-4-with-a-clean-mozilla-indy)
· [Graphical Software Manager](../lab/irix-installer/README.md#install-with-graphical-software-manager).

For xosview and an in-place Freeware UnZip upgrade, keep the release
supplement and CD 4 attached. Add the older UnZip runtime at SCSI ID 6.
[Installation, upgrade and removal](../lab/irix-installer/README.md#install-xosview-and-upgrade-unzip-in-software-manager).
When using UnZip and xmahjongg together, attach the [shared helper ISO](../lab/irix-installer/README.md#install-xmahjongg-and-unzip-together) at ID 6.
For GIMP, attach the four-disc package selection at ID 5 alongside the matching
release supplement. Keep the maintenance CD for later removal or reinstallation.
[Build the CD and install GIMP](../lab/irix-installer/README.md#install-gimp-125-from-the-freeware-cds) · [Remove or reinstall GIMP](../lab/irix-installer/README.md#remove-and-reinstall-gimp).

To return to the previous v5 desktop, quit Mozilla, mount the same CD again
and run:

```sh
sh /cdrom/install.sh --remove-mozilla && shutdown -r now
```

The component records ownership and saves replaced files under
`/var/db/xiri-install/mozilla`. Removal restores the previous kernel, PROM
boot file, module and launcher. Each user's `~/.mozilla` profile stays in
place. If removal reports a changed application file, save that edit and
restore the packaged contents before retrying. An edited resolver rc.conf.d
setting stays in place. Remove the component before changing or uninstalling
the base desktop package. [Installer qualification](results/2026-11-25-mozilla-installer.md).

The earlier hand-assembled November 25 Mozilla input CHDs use a different
module baseline. To update those images in place, use their [network update
CD](results/2026-11-25-mozilla-http.md#update-an-existing-november-25-mozilla-input-disk).

### Upgrade or roll back the Indy display package

Log out of the graphical session. From a root text console, mount the v5 CD
for the installed IRIX release and run the following commands.

```sh
/etc/rc.d/xdm stop
sh /cdrom/upgrade.sh && /etc/rc.d/xdm start
```

For rollback, stop xdm again and run `sh /cdrom/upgrade.sh --rollback`, then
restart xdm. Both directions check the installed file hashes and permissions,
including the setuid mode on Xorg. The update installs the original release's
font map, three Iris bitmaps and their index under `/emul/irix/usr/lib/X11/fonts`.
The package also includes the PTY setup fix for installing original IRIX
software. Rollback restores the stock Xorg and GLX files, the v4 helper
and the previous installation receipt. An interrupted update resumes with the
same CD and direction. If a local file conflicts, the command reports its
path before applying the update. Save the local change before retrying.

### Recover from a full target filesystem

Use the corrected v4 media in `.work/installers/indy-11.99.11/space-recovery/`.
Choose the ISO matching the installed IRIX release. These CDs contain the
same v4 native archive and vendor payloads as the earlier FAM update.

If an operation reports `No space left on device`, use `df -k` on the
reported path or its parent directory to identify the full filesystem. Use
`df -i` to check for exhausted inodes. Free space on that filesystem and
repeat the original command from the same CD as root.

| Interrupted operation | Command to resume |
| --- | --- |
| Fresh installation | `sh /cdrom/install.sh` |
| v3 to v4 update | `sh /cdrom/upgrade.sh` |
| v4 to v3 rollback | `sh /cdrom/upgrade.sh --rollback` |

Keep `/var/db/xiri-install` and both installed payload trees in place.
During a fresh installation the `inputs` file can exist before the
`installed` receipt. During an update, `upgrading` records the direction
and package identities. A mix of old and new files can already be on disk
at this point. Finish the retry before restarting services or logging into
the desktop. On success, `inputs` and `installed` match and the update
journal is gone.

The [Indy recovery results and manual images](results/2026-11-24-indy-v4-recovery.md)
include the two release-specific launch commands and the paths exercised.

### Select the desktop after installation

Create desktop users through normal NetBSD account administration. An IRIX-style
home is `/usr/people/USERNAME`. Select the desktop by running the following
command **as that user** after reviewing any existing `~/.xsession`:

```sh
install -m 700 /usr/local/share/xiri/xdm.xsession "$HOME/.xsession"
```

Keep the stock Xsession selection for users who want NetBSD ctwm. Ensure the
local hostname resolves. On the Indy, use graphics console `g` in the PROM,
reserve `ttyE0` for X and enable serial `ttyZ0` for recovery. Reboot to start
services in rc order. See [user session configuration](../runtime/README.md)
for additional accounts and existing xdm configurations.

### Switching between the stock and Xiri kernels

On either clean Indy image, shut down as root with `shutdown -h now`. At the
Indy System Maintenance menu choose **5. Enter Command Monitor**. If starting
from power-on, press Esc at the PROM countdown to reach that menu. Keep the
graphical console selected. Select the original NetBSD kernel at the PROM.

```text
setenv OSLoadFilename netbsd.stock
boot
```

Run `uname -r` in the guest. The stock kernel reports `11.0`. Use a native
NetBSD account such as `netbsdtest` during recovery. Stock 11.0 logs
`modload: compat_irix_o32: Function not implemented` and continues to xdm.
The installed Xiri module requires the matching Xiri kernel.

To return, shut down cleanly again and select the Xiri boot wrapper at the PROM.

```text
setenv OSLoadFilename netbsd.boot
boot
```

`uname -r` now reports `11.99.11`, and `modstat | grep compat_irix_o32`
shows the module loaded from the filesystem. Log in at xdm with the
usual Xiri desktop account. The PROM remembers the selected filename. Both
kernels use the same root filesystem, user homes and configuration. See the
[dual-release rollback test](results/2026-11-23-indy-kernel-rollback.md).

### Remove the desktop and return to native NetBSD

Use the CD built for the installed IRIX release and native package. The
November 24 installer media include `uninstall.sh`. To use an older clean
Indy image, build or attach the newer CD with the same native and vendor
archives. Log out of all desktop sessions, log in on the serial console as
root, mount the CD read-only and stop xdm and the Xiri FAM daemon.

From the repository root, the manual Indy launcher accepts a CD at SCSI ID 4.
Choose the release that matches the CHD.

```sh
release=6.5.22f
.work/images/xiri-clean-indy-${release}-v4-20261124/run-iris.sh \
    --cdrom4 "$PWD/.work/installers/indy-11.99.11/space-recovery/xiri-${release}.iso"
```

**Native graphical login on the clean Indy.** Enable `xdm=YES` in the
site's `/etc/rc.conf` if native graphical login is desired. For an Indy with
no site Xorg configuration, before removal copy the Newport configuration
to the native Xorg location with stock acceleration disabled.

```sh
test ! -e /etc/X11/xorg.conf && test ! -L /etc/X11/xorg.conf &&
    sed 's/"NoAccel" "false"/"NoAccel" "true"/' \
        /usr/local/share/xiri/xorg.conf > /etc/X11/xorg.conf
```

An existing site configuration takes precedence. Review any locally edited
`/etc/rc.conf.d/xdm` for Xiri-specific server paths.

Inside the guest, run the following commands from the root console.

```sh
mkdir -p /cdrom
mount -t cd9660 -o ro /dev/cd0a /cdrom
/etc/rc.d/xdm stop
/etc/rc.d/xiri_famd stop
sh /cdrom/uninstall.sh
```

The November 23 clean Indy CHDs predate per-file ownership records. For
an original v1 installation on one of those images, attach
`.work/installers/indy-11.99.11/removal/xiri-${release}.iso`. **On
those images only**, use `sh /cdrom/uninstall.sh --legacy-clean-indy`
for the first removal. This tells the uninstaller that package paths with
matching contents came from the documented clean installation. An older
receipt alone cannot establish that on an independently configured machine.
Subsequent installations from the new media record which files and links
they created and use the ordinary command.

The uninstaller restores replaced native files, including the original
Newport driver link and rpcbind. It compares native files against the package
before deleting them. Site configuration, accounts, home directories and
session selectors stay under local administration. Modified replacements for
which an original must be restored are saved in the transaction's `edits/`
directory. The bootstrapped kernel, module and module-loading configuration
have their own lifecycle. Select `netbsd.stock` and later `netbsd.boot`
using the [kernel switching procedure](#switching-between-the-stock-and-xiri-kernels).

The final message gives a private history directory under
`/var/db/xiri-install`. Its `trees` file lists the detached vendor and font
directories. They retain extra software, locally edited vendor files and
generated data on their original filesystems, so removal does not reclaim
their disk space. Reinstallation publishes fresh trees from the CD. Review
any additions you want to copy back before discarding a detached tree.
After an interrupted removal, rerun the same command from the same CD.

After booting `netbsd.stock`, log in as `netbsdtest` for ctwm. To reinstall, boot
`netbsd.boot`, mount the same CD, run `sh /cdrom/install.sh` and reboot.
The existing `xiritest` session selector and home preferences apply at xdm.
See the [dual-release results and screenshots](results/2026-11-24-indy-desktop-removal.md).

### Upgrade native helpers on an installed Indy

Use the upgrade CD for the IRIX release already installed. On the host, the
following launches the November 23 clean Indy with its matching update CD.
Set `release=6.5.30f` for the R5000 image.

```sh
release=6.5.22f
.work/images/xiri-clean-indy-${release}-20261123/run-iris.sh \
    --cdrom4 "$PWD/.work/installers/indy-11.99.11/upgrade/xiri-${release}.iso"
```

Log out to the xdm greeter. At the NetBSD root console, mount the CD, update
the installed helpers and reboot.

```sh
mkdir -p /cdrom
mount -t cd9660 -o ro /dev/cd0a /cdrom
sh /cdrom/upgrade.sh
shutdown -r now
```

To restore the previous native helpers, mount the same CD again, run
`sh /cdrom/upgrade.sh --rollback` and reboot. If either operation is
interrupted, repeat it from the same CD with the same option. A successful
repeat reports that the requested package is already installed. The two
archives and release in `/var/db/xiri-install/installed` identify the
current installation. To remove the desktop later, use uninstall media
whose native and vendor archives match that receipt.

The update touches only the native helper paths listed in the package delta.
It preserves installed IRIX programs, fonts, user homes, active configuration
and the kernel/module pair. If a changed helper also has a local edit or
different permissions, the command identifies its path before starting the
update. Save the local version elsewhere and restore the exact source bytes,
owner, group and mode before retrying. The CD's `delta.tgz` contains both
versions under `old/root/` and `new/root/`. Reapply any edits that are still
needed after the transaction completes.
The first update changes `/usr/local/sbin/xiri-sync-users`. An account refresh
now leaves each correct IRIX lookup file in place when its contents,
permissions and ownership already match.

To build media, supply both native package directories and one vendor
payload. Repeat for the other IRIX release, choosing a separate output ISO.

```sh
./xiri install-media \
    --upgrade-from .work/packages/netbsd-sgimips-indy-11.99.11-v1 \
    --native-package .work/packages/netbsd-sgimips-indy-11.99.11-sync-users-v2 \
    --vendor-payload ".work/imports/irix-${release}-v1" \
    --output "/tmp/xiri-upgrade-${release}.iso"
```

Both packages must use the same qualified Indy profile, kernel and native
prerequisites. The media builder accepts regular Xiri commands in
`/usr/local/bin` and `/usr/local/sbin`, and helpers in `/usr/local/libexec/xiri`.
The [v4 FAM update](#configure-the-fam-service-log-with-v4) also supports
replacement of its startup script and packaged example.
[First helper update and screenshots](results/2026-11-24-indy-native-upgrade.md)

### Add or retire helpers with the v3 account update

The next CD upgrades **v2 to v3** on the same installed vendor release.
Check `cat /var/db/xiri-install/installed` at the root console. Its second
field identifies the native package. The v2 digest begins with `b0a4a093`.
On a November 23 clean Indy still at v1 (`8fe4ab36`), apply the v2 CD
above first. The v3 digest begins with `ab50f980`. To boot the installed
system with the v3 CD attached, set `release` to the matching vendor release.

```sh
release=6.5.22f
.work/images/xiri-clean-indy-${release}-20261123/run-iris.sh --cdrom4 "$PWD/.work/installers/indy-11.99.11/helper-layout/xiri-${release}.iso"
```

Mount the matching CD and log out to the xdm greeter. For an installation
with a `/var/db/xiri-install/created` directory, run the update as root.

```sh
sh /cdrom/upgrade.sh
shutdown -r now
```

The original clean Indy images have older receipts. Applying the v2 update
to one of those images retains its older ownership information.
**Only on a documented clean Indy with that older receipt**, use
`sh /cdrom/upgrade.sh --legacy-clean-indy`. That option authorizes retiring
an unchanged helper whose original ownership was never recorded. To reverse
the update, mount the same v3 CD and add `--rollback` to the command used
for the upgrade. Resume an interrupted operation with the same direction
and options.

The updater adds new helpers before switching their callers and retires old
helpers last. The v3 package adds `/usr/local/bin/xiri-account-map`, updates
`xiri-sync-users` and retires `/usr/local/libexec/xiri/account-map.awk`.
A new name occupied by a local file, directory or dangling link stops the
transaction before any helper changes, even when the file matches the new
package byte for byte. Move the local entry to a name of your choosing before
retrying. An edit to a retiring helper also stops the update. Save the edit
and restore the packaged bytes and mode before retrying.

On a tracked installation, retirement restores a file displaced by the
original install with its saved ownership and permissions. A file already
identical when first installed stays in place. Rollback checks any restored
site file before switching the name back into package use.

To reproduce the source package, build the Indy profile from Xiri commit
`22981cd` for v2. Build the same profile from the v3 sources for the target.
To assemble this release-specific CD, run the media command above with
`--upgrade-from .work/packages/netbsd-sgimips-indy-11.99.11-sync-users-v2`
and `--native-package .work/packages/netbsd-sgimips-indy-11.99.11-account-map-v3`.
Use a new output filename. [Dual-release qualification](results/2026-11-24-indy-helper-inventory.md)

### Configure the FAM service log with v4

Start with an installed v3 Indy desktop. The native archive digest in the
second field of `/var/db/xiri-install/installed` begins with `ab50f980`.
Attach the update CD for the installed IRIX release when starting the emulator.

```sh
release=6.5.22f
.work/images/xiri-clean-indy-${release}-20261123/run-iris.sh --cdrom4 "$PWD/.work/installers/indy-11.99.11/space-recovery/xiri-${release}.iso"
```

Log out to xdm, mount the CD as above, and run `sh /cdrom/upgrade.sh` as
root. V4 replaces `/etc/rc.d/xiri_famd` and the reference copy at
`/usr/local/share/xiri/examples/rc.conf.d/xiri_famd`. The running daemon
continues serving clients until its next restart. An edit to either packaged
file stops the update and identifies the path. Save the edit and reconcile
the reported file before retrying.

For a new v3-to-v4 update, use the [space-recovery media](#recover-from-a-full-target-filesystem).

To choose a log destination, add a line like the following to the live
`/etc/rc.conf.d/xiri_famd`. Keep the existing `xiri_famd=YES` setting.

```sh
xiri_famd_logfile="/var/log/xiri fam site.log"
```

Reboot or run `/etc/rc.d/xiri_famd restart` from the greeter. FAM appends
to the chosen file. With the setting omitted or empty it appends to
`/var/log/xiri-fam.log`. To roll back, mount the same CD, run
`sh /cdrom/upgrade.sh --rollback` and reboot. V3 uses the default log again.
The administrator's rc.conf.d setting and `/etc/xiri/fam.conf` survive both
directions. If interrupted, repeat the same command with the same CD.

Build the CDs with the preceding media command, using the v3 package as
`--upgrade-from` and `.work/packages/netbsd-sgimips-indy-11.99.11-fam-service-v4`
as `--native-package`. Select the matching vendor payload for each output.
[Indy test results and screenshots](results/2026-11-24-indy-fam-service.md)
