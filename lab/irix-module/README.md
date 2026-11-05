# Loadable IRIX personality

This cycle builds `compat_irix_o32.kmod` for the big-endian N64 sgimips
kernel. One module implements both foreign o32 and n32 execution. The name
retains the original personality's name; it does not restrict the module to
o32 applications. The 32-bit kernel continues to use the built-in option:
NetBSD's current MIPS kernel-object loader requires N64.

The module follows the existing `MODULE_CLASS_EXEC` registration and
`exec_add`/`exec_remove` lifecycle, with dependencies on `exec_elf32` and
`compat_netbsd32`. Those dependencies remain built into this kernel.
`XIRI_IRIX_MODULE` enables `MODULAR` and omits `COMPAT_IRIX_O32`.
`COPY_SYMTAB` embeds symbols because a direct Indy PROM ELF32 boot does not
supply the NetBSD bootloader's symbol-table bootinfo record.

This is module delivery on the Xiri fork. The kernel still supplies
`selcommon_kern`, `emul.e_sigmask`, and the opt-in `EMUL_NOCLDSTOP_CONT`
child-notification policy; upstreaming or replacing these interfaces is a
separate requirement for stock-NetBSD deployment. The
[child-state cycle](../irix-job-control/README.md) requires a matching core and
module: the existing `emul.e_flags` layout is unchanged, but an older core
does not implement the new flag. Newport remains a native driver and is not
part of the compatibility module.

## Build

Use an isolated source/build tree and matching NetBSD cross-tools. During
development the source worktree is `.work/netbsd-module-src`, created from
NetBSD `xiri` at `5f094bc6ab9`. The module and diagnostic receive fix are
recorded at `d1ce7a96615`; [build.json](build.json) pins the artifacts and
matching source hashes. Do not reuse a qualified build directory for
a different source tree. Prepare tools with the existing kernel builder's
`tools` operation when a matching toolchain is unavailable.

```sh
export XIRI_NETBSD_SOURCE_DIR="$PWD/.work/netbsd-module-src"
export XIRI_NETBSD_BUILD_DIR="$PWD/.work/netbsd-module-build"
export XIRI_NETBSD_TFTP_DIR="$XIRI_NETBSD_BUILD_DIR/tftp"
export XIRI_NETBSD_CONFIG="$PWD/lab/irix-module/XIRI_IRIX_MODULE"
export XIRI_NETBSD_ARCH=mips64eb XIRI_BUILD_JOBS=2
bash scripts/build-netbsd-kernel.sh kernel
python3 scripts/build-irix-module.py --build "$XIRI_NETBSD_BUILD_DIR"
```

The module build uses NetBSD's `bsd.kmodule.mk` and its warning checks. The
manifest records source/configuration hashes, artifacts, unresolved module
imports and relocation types. Its audit requires every import to be present
in the kernel and verifies that the kernel has no IRIX implementation symbols.
It also checks the generated kernel option headers. Keep the kernel and
module from the same source/configuration build together.

## Install and lifecycle

On the matching kernel, install under the path reported by
`sysctl -n kern.module.path`:

```sh
module_dir="$(sysctl -n kern.module.path)/compat_irix_o32"
mkdir -p "$module_dir"
install -m 444 compat_irix_o32.kmod "$module_dir/compat_irix_o32.kmod"
```

Add `compat_irix_o32` to `/etc/modules.conf` and `modules=YES` to
`/etc/rc.conf`. NetBSD's modules rc.d service runs before multiuser programs
and before securelevel rises. Interactive `modload`/`modunload` tests run in single-user mode at
securelevel 0; a normal multiuser boot at level 1 rejects these operations
with `EPERM`. Setting `securelevel=-1` in rc.conf cannot lower the initial
kernel level and is not used by this probe. The busy-process check must see `EBUSY`, not
count a securelevel refusal as proof of lifecycle protection.

```sh
python3 scripts/probe-irix-module.py --desktop
```

The probe clones the qualified desktop seed, uses its pinned IRIS emulator,
and retains serial logs and results under `.work/irix-module/runs`. It checks
foreign direct-exec failure without the module, o32 asa/n32 echo after load,
busy/idle unload, reload, reboot loading and an optional real Newport desktop.
The native parent holds asa's stdin open and waits for a close-on-exec
acknowledgment before testing busy unload. It closes the input and reaps the
child before testing successful unload. All owned emulators are stopped.

The [module-based manual CHD](../../docs/results/2026-11-03-irix-module-image.md)
now passes its own cold-boot and desktop checks and is selected by `./xiri run`.
The previous built-in CHD and its user state remain available for comparison.

The ordinary multiuser desktop capture and lifecycle records are in the
[cycle result](../../docs/results/2026-11-03-irix-module.md). After a passed
module run, replay the measured signal, sproc and recvmsg subsets with:

```sh
python3 scripts/probe-irix-module-regressions.py --seed .work/irix-module/runs/<passed-run>
```

The module cycle also runs the unchanged LP64 case matrix through
`probe-irix-lp64.py --require-module`, with explicit checkpoint, kernel-build,
pin and emulator paths. Its optional arguments preserve historical defaults.

To replay the 243-case LP64 matrix from the retained qualified seed:

```sh
python3 scripts/probe-irix-lp64.py --mode ordinary --require-module \
  --checkpoint .work/irix-module/runs/ordinary-stpqqniv \
  --pin lab/irix-module/lp64-regression.json \
  --build-directory .work/netbsd-module-build \
  --iris-bin-dir .work/images/xiri-netbsd-desktop-20261103-newport-xmahjongg/emulator
```

That pin deliberately checks the exact disk and NVRAM hashes. A newly prepared
seed needs a fresh pin and its own evidence; do not silently replace a
qualified seed or modify the recorded pin to bypass a mismatch.

## Prepare a manual image

[image-baseline.json](image-baseline.json) pairs the audited module build with
the accelerated desktop's tested IRIS binaries. Prepare a disposable clone
of the previous image using the graphical console/desktop probe:

```sh
python3 scripts/probe-xiri-desktop-usability.py \
  --seed .work/xiri-image/seed-1fa5c92ffac3 \
  --kernel-build .work/netbsd-module-build \
  --baseline lab/irix-module/image-baseline.json \
  --iris-bin-dir .work/images/xiri-netbsd-desktop-20261103-newport-xmahjongg/emulator \
  --xorg-config lab/newport-accel/xorg.conf \
  --newport-driver .work/newport-xmahjongg/newport_drv.so \
  --irix-module .work/netbsd-module-build/obj/sys/modules/compat_irix_o32/compat_irix_o32.kmod \
  --check-xmahjongg --arrange-winterm
```

The probe verifies the matching kernel/module hashes, installs the module
under `kern.module.path`, preserves other `/etc/modules.conf` entries, enables
the modules rc.d service and reboots onto the graphical console. Its result
records hashes for the module and both boot configuration files alongside
the existing native helper ledger. It requires `modstat` to report the IRIX
personality as `exec / filesys` at securelevel 1 before testing the desktop.

Package the passed, halted run with `scripts/build-xiri-image.py`, using
this baseline and `.work/netbsd-module-build/tftp/netbsd-XIRI_INDY`.
Then cold-boot the actual CHD with `scripts/probe-xiri-image.py` and qualify
with `scripts/qualify-xiri-image.py`. The qualifier checks the module again,
including its file hash and normal securelevel; successful CHD compression
alone does not promote an image. See the [image procedure](../../docs/XIRI-IMAGE.md).
