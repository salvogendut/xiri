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
procedure below uses the same input archives. Version upgrades remain open. Boot the
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

## Clean installation on an emulated Indy

Use the [11.99.11 Indy profile](../profiles/netbsd-sgimips-indy-11.99.11-v1.json)
with `./xiri package-native`. Supply the three Indy kernel artifacts from the
[NetBSD integration build](results/2026-11-23-netbsd-current.json) and the
three service/display artifacts listed above. This profile selects accelerated
Newport at 1280×1024. Start with NetBSD 11.0/sgimips userland, the four X
runtime sets, and the matching 11.99.11 kernel and boot-loaded module. The
[stock bootstrap procedure](../lab/native-package/README.md#bootstrapping-a-stock-target)
prepares this target from the recorded NetBSD installation.

Build a local CD for each imported release. Replace the example paths with
your local native package and previously generated donor imports.

```sh
for release in 6.5.22f 6.5.30f; do
    ./xiri install-media --native-package .work/packages/netbsd-sgimips-indy-11.99.11-v1 \
        --vendor-payload ".work/imports/irix-${release}-v1" \
        --output ".work/xiri-installer-${release}.iso" || exit 1
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
.work/images/xiri-clean-indy-${release}-20261123/run-iris.sh \
    --cdrom4 "$PWD/.work/installers/indy-11.99.11/removal/xiri-${release}.iso"
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

The November 23 clean Indy CHDs predate per-file ownership records. **On
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
