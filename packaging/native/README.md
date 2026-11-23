# Native NetBSD package

This package supplies the qualified MIPS64 kernel/boot wrapper and matching
IRIX module, patched native FAM/rpcbind/Newport driver, and a newly built o32
session runtime. Its target is NetBSD/sgimips 11.0 userland and X sets with our
11.99.9 kernel. The Type1 signal/FPU correction is in that kernel; stock Xorg
and font libraries remain distribution prerequisites.

Unpack `native.tar.gz` into a new staging directory using native
`pax -rz -pe -f native.tar.gz`. The archive has a `kernel/` directory and a
`root/` payload. **It is not a live-root overlay or a complete installer.**
Keep kernel activation separate from userspace installation and reboot before
checking the running kernel. Never extract this package directly over `/`.

From the unpacked directory, `sh preflight.sh` checks package integrity, the
running kernel version, on-disk kernel hash and native library/tool/resource
prerequisites. `sh preflight.sh --root /path/to/target` checks an offline target
with NetBSD tools; it cannot attest to that target's running kernel.
`--verify-installed` additionally checks installed package files, modes and
symlinks. Administrator configuration may differ from the shipped defaults.
These commands are read-only and do not enable services or create accounts.

The manifest records every package file and native dependency, pinned NetBSD
sets, compiler and source hashes. Standard sets must be installed normally;
do not substitute a desktop image as a source for their libraries. Configuration
under `root/etc/xiri` is a default to install only when absent; `.example`
files are updated copies for review. Service and module snippets under
`root/usr/local/share/xiri/examples` are opt-in. Preserve existing `rc.conf`,
`modules.conf`, `ttys`, accounts, passwords, homes and user preferences.

Install the vendor payload separately. Activation must create the native
`/usr/lib/desktop` alias, synchronize IRIX account lookup tables, set up PTYs,
generate font indexes/filetypes, and select the desktop in each native user's
`.xsession`. The maintained runtime documentation describes these steps.
The package does not import donor accounts or fabricate lab users/passwords.
Managed installation, backups, retry/removal and a clean-target boot test remain
the next installation stage; preflight success alone is not a working desktop.

Maintain both IRIX 6.5.22 and 6.5.30 deliverables. Native components can be shared,
but each vendor release requires its own import profile, desktop qualification
and CHD. A passing 6.5.22 session does not qualify 6.5.30.

The clean Indy profile targets the 11.99.11 kernel with stock 11.0 userland.
`./xiri install-media` puts `install-desktop.sh`, that native package, and
one verified local donor payload on a CD. Run the installer from the mounted
CD on the matching bootstrapped target. See the [clean installation
instructions](../../docs/NATIVE-PACKAGE.md#clean-installation-on-an-emulated-indy).
