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
