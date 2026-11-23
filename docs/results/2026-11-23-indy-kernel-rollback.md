# Indy kernel rollback and desktop recovery

Both clean Indy images booted the saved NetBSD 11.0 kernel and then returned
to Xiri 11.99.11. Each test used one private writable overlay for all three
boots. The original CHD hashes matched before and after. The manual bundles
kept their separate writable overlays.

| IRIX payload and CPU | Stock 11.0 | Restored Xiri desktop | Saved winterm foreground |
| --- | --- | --- | --- |
| 6.5.22f, R4400 | [xdm greeter](2026-11-23-indy-rollback-6.5.22f-stock.png) | [4Dwm at 1280×1024](2026-11-23-indy-rollback-6.5.22f-restored.png) | `#c9ecc9` |
| 6.5.30f, R5000 | [xdm greeter](2026-11-23-indy-rollback-6.5.30f-stock.png) | [4Dwm at 1280×1024](2026-11-23-indy-rollback-6.5.30f-restored.png) | `#c9d9ec` |

1. On the first Xiri boot, `xiritest` wrote a private file and set a winterm
   foreground colour in `~/.Xresources`. The probe recorded the checksums,
   owners, groups and modes of both files, the user's X session selector,
   the native account and group databases, module and desktop configuration,
   and the release-specific install receipt.
2. With the PROM set to `netbsd.stock`, each guest reported the full NetBSD
   11.0 `GENERIC32_IP2x` build string. The saved kernel matched the binary
   in the pinned distribution set. All recorded files passed verification.
   The stock kernel logged `modload: compat_irix_o32: Function not implemented`
   and reached xdm. A native login shell for `netbsdtest` started in
   `/home/netbsdtest` and wrote a second private file.
3. With the PROM back on `netbsd.boot`, each guest reported the original
   Xiri 11.99.11 build and loaded `compat_irix_o32` from the filesystem.
   The file written under stock 11.0 retained its contents and native
   owner. A real xdm login as `xiritest` brought up 4Dwm, Toolchest,
   Icon Catalog, winterm and xclock. The X server's active resource database
   contained the saved colour. The original IRIX shell ran, logout returned
   to xdm and the preserved files still matched.

All six qualified boots reached securelevel 1 and recorded a clean unmount
and halt in the running kernel's message buffer. The probe used the normal
graphics console on `ttyE0` and a separate native login on `ttyZ0`.
Forcing the PROM console to serial made two gettys compete for input on these
images. An interrupted R4400 run was repeated from a fresh private disk.
The images used the same pinned emulator as the clean-install qualification.
Inside each restored desktop, X reported 1280×1024. The raw IRIS framebuffer
captures measure 1282×1024.

For manual recovery, follow the [PROM commands](../NATIVE-PACKAGE.md#switching-between-the-stock-and-xiri-kernels).
The [machine-readable record](2026-11-23-indy-kernel-rollback.json)
contains the input hashes, per-boot results and screenshot hashes. The
[lab instructions](../../lab/native-package/README.md#stock-kernel-round-trip)
reproduce the test. Compact serial, emulator and shutdown logs are retained
locally in `.work/installers/indy-11.99.11/rollback-qualification.tar.gz`.
