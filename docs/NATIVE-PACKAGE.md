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
prerequisites. Native-package promotion for 6.5.30 still requires its separate
installation/reinstallation acceptance run.
The [Indy/R5000 application trial](results/2026-11-14-r5000-6.5.30.md) now
passes core desktop/shell, logout/relogin and native ctwm checks with a newer
module that admits the donor's MIPS IV n32 interpreter. That module also passes
6.5.22f desktop regression checks. The existing native package retains its qualified 6.5.22
module pin; it is not silently repinned by that trial. The separate
[O2/R10000 candidate](../lab/irix-o2/README.md) uses a separate IP32 kernel/module
and native profile, the stock `crime` driver and `ip3xboot`; it does not use the
Indy's patched Newport driver. Package construction passes, but native boot
currently stops during SCSI initialization before package installation.

## Installation boundary

This is the native **package and preflight** milestone. A managed installer
with complete preflight for free space, backups, interrupted-install recovery,
upgrades and removal remains separate. The qualification fixture copies only
the known payload in a disposable guest; it is not the supported installer.
Kernel/boot activation remains a separate operation before module loading.

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
