# Loadable IRIX personality on the N64 Xiri kernel

The loadable-module milestone passes on the emulated R4400 Indy. The
[qualification record](2026-11-03-irix-module.json) covers lifecycle, normal
boot loading, the desktop and 415 application/ABI/control checks.

The module build separates the existing IRIX o32/n32 personality from the
NetBSD kernel. `compat_irix_o32.kmod` uses NetBSD's exec-module lifecycle and
depends on the kernel's `exec_elf32` and `compat_netbsd32` components.
`XIRI_IRIX_MODULE` enables `MODULAR`, omits `COMPAT_IRIX_O32`, and retains
the accelerated Newport configuration.

This is the first module milestone on our fork. It still requires the
exported `selcommon_kern` helper and the `emul.e_sigmask` callback. It does
not establish compatibility with stock NetBSD or change service/session
ownership. NetBSD's current MIPS module loader supports N64 only; one module
on that kernel handles both foreign ABIs. The 32-bit kernel continues to use
the built-in personality.

## Build and boot requirements

The [reproduction guide](../../lab/irix-module/README.md) gives the isolated
build and installation commands. NetBSD's module build exposed signedness
warnings that the kernel build suppresses; the patch makes those conversions
explicit without changing accepted argument ranges. The module's 147 imports
are present in the kernel, which contains no IRIX implementation symbols.
Its relocation types are supported by the existing MIPS loader.

Direct Indy PROM boot does not provide a NetBSD symbol-table bootinfo record.
`COPY_SYMTAB=1` embeds the symbols needed for runtime linking. No MIPS loader
or emulator change was needed. The module and kernel must come from a matching
source/configuration build.

Interactive lifecycle checks run in single-user mode at securelevel 0. The
PROM command is `boot -f bootp()/netbsd-XIRI_INDY --s`; the PROM removes one
dash before passing `-s` to NetBSD. At the normal multiuser securelevel 1,
module administration returns `EPERM`. This refusal is distinct from the
`EBUSY` result required while an IRIX process is active. Setting -1 in
rc.conf cannot lower the kernel's initial securelevel and is not the test
setup used here.

For normal startup, install the module in
`$(sysctl -n kern.module.path)/compat_irix_o32/compat_irix_o32.kmod`, add
`compat_irix_o32` to `/etc/modules.conf`, and enable `modules=YES` in
`/etc/rc.conf`. The existing modules rc.d service runs before securelevel
rises and before desktop services or clients.

## Diagnostic receive assertion

The first desktop run with the module panicked in `irix_recvmsg`. Module
builds enable `DIAGNOSTIC`; the previous built-in personality had compiled
out this assertion. `m_length()` trusts `M_PKTHDR`'s packet length, which can
retain the original length after a stream read trims the chain. It also
cannot accept the NULL chain returned at EOF. The assertion now sums the
actual returned mbufs, including an empty chain, and compares that sum with
the receive count. The existing scatter-copy and fault-consumption behavior
is preserved. Targeted receive tests include short reads, zero length,
scatter, partial copy faults, peek, nonblocking empty reads and EOF.

The initial failing captures and their disposable disks remain in
`.work/irix-module/runs`; they are diagnostic evidence, not qualified seeds.
The previously qualified desktop CHD and pinned emulator remain available.

## Validation

All final runs passed and shut down cleanly:

| Check | Coverage |
| --- | --- |
| Module lifecycle | 12 vendor executions across absent, loaded, unloaded, reloaded and boot-loaded states; native controls throughout |
| Busy/idle unload | Native parent observes `EBUSY` while asa is active, then successful unload after reaping it |
| LP64 matrix | 243 unchanged native/foreign ABI, mapping, loader, identity, FPU and vendor-runtime cases |
| Signal/sproc/receive | 48 signal, 48 sproc and 72 recvmsg cases, covering o32/n32, direct/indirect dispatch and root/UID 1234 |
| Native controls | Four signal and time/select checks after the foreign regression batch |
| Desktop | Boot-loaded module at securelevel 1; 4Dwm, Toolchest, Icon Catalog, xmahjongg and winterm; typed `pwd` returns `/usr/people/xiritest`; clean logout |
| Host workflow | 18 tests pass; Python compilation, whitespace and local documentation links checked |

The [desktop PNG](2026-11-03-irix-module-desktop.png) preserves the actual
capture. This is startup/session qualification, not a new full application
survey or a replacement CHD qualification.

NetBSD commits `c46d4e9a931` (module recipe and warning fixes) and
`d1ce7a96615` (diagnostic receive count) contain the implementation. The
[build manifest](../../lab/irix-module/build.json) retains the original build
state and identifies the equivalent committed source; its recorded source
hashes match `d1ce7a96615`.

Validation records are produced by `probe-irix-module.py`, the LP64
application matrix, and `probe-irix-module-regressions.py`. The latter reuses
the existing original-IRIX signal, sproc and receive record decoders rather
than defining a new expected ABI from the module implementation.

The lifecycle native parent proves foreign exec completed, keeps asa blocked
on its input pipe, checks `EBUSY`, then closes input and reaps the child before
checking successful unload. Direct-exec records distinguish `ENOEXEC` from
shell fallback. The desktop probe checks Icon Catalog and winterm's working
directory, captures a PNG, and verifies session cleanup.

IRIS upstream `28fa516684c54e00e35b258c65e5dcac3a36165c` was integrated and
pushed as `1aed0dfc842a427e32a53ad083e1be0a9d46a613`. Its sole new test fix was
already present in our fork; the merge has an identical tree to its first
parent. Guest tests use the desktop bundle's qualified `819c682` emulator.
See the [fork record](../FORKS.md).
