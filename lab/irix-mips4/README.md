# IRIX 6.5.30 n32 interpreter admission

The original-media 6.5.30f n32 libc is an ELF interpreter declaring MIPS IV
(`e_flags=0x30000022`). Its fftr and 4Dwm main programs declare MIPS III.
The compatibility module's previous exact flag whitelist rejected this libc
even on R5000. NetBSD `xiri` commit `93a25807724` admits that interpreter only on a MIPS IV CPU.
It preserves MIPS III rejection and the existing ELF/segment constraints.

Run the source-level regression against the actual validator and separate
private donor payloads:

```sh
python3 lab/irix-mips4/check-admission.py \
  ../NetBSD-xiri/sys/compat/irix_o32/irix_o32.c \
  --payload-22 .work/imports/irix-6.5.22f-v1/payload.tar.gz \
  --payload-30 .work/imports/irix-6.5.30f-v1/payload.tar.gz
```

The test compiles the actual validator with a read stub supplying each donor
file's decoded program headers. It checks sh, fftr, 4Dwm and libc on both CPU
classes, plus invalid ELF class, byte order, flags and text permissions.
The new interpreter case fails before the patch; all 20 pass afterward.
This is a loader-admission test, not a substitute for executing the binaries.

`module-build.json` retains the original dirty build provenance and kernel
export/relocation audit. `source.patch` is the corresponding small fork delta.
`source-equivalence.json` verifies the recorded sources against the committed fork.
The unchanged native kernel is the qualified Indy module host. Build with
`scripts/build-irix-module.py --build <isolated-build> --jobs 2` after preparing
the matching N64 tools, configuration headers and kernel artifacts as described
in the [module workflow](../irix-module/README.md).

The guest qualification commands use new output directories:

```sh
python3 scripts/probe-irix-import.py \
  --bundle .work/images/xiri-netbsd-desktop-20261114-controls \
  --payload .work/imports/irix-6.5.30f-v1 \
  --cpu r5000 --cache shadow \
  --emulator-bundle .work/emulators/iris-xiri-20261114-r5k-config \
  --module-build .work/irix-mips4-module \
  --output .work/irix-6.5.30-mips4-check

python3 scripts/probe-irix-import.py \
  --bundle .work/images/xiri-netbsd-desktop-20261114-controls \
  --payload .work/imports/irix-6.5.22f-v1 \
  --module-build .work/irix-mips4-module \
  --output .work/irix-6.5.22-mips4-check
```

The first run selects shadow cache mode because full-cache extraction produced
persistent zeroed blocks. All vendor file checksums must pass before execution.
The candidate module is installed in the private overlay and loaded through
a clean cold boot, preserving securelevel 1. Each result records its effective
module separately from the parent image's original pin. See the
[R5000 cycle report](../../docs/results/2026-11-14-r5000-6.5.30.md) for results
and remaining limits. The qualified manual 6.5.22 image is not overwritten.

To repeat a cleanly halted import after filetype activation, add
`--resume-import <prior-run> --reset-filetypes`. The original table backup must
match the donor manifest before restoration on the private copy; the complete
vendor checksum gate then runs again. If that disk already contains the
candidate module, its initial cold boot supplies the loading check and no
second reboot is needed. Interrupted runs retain their original failed status.

`--desktop-only --resume-import <prior-run>` is a separately labelled cold-boot
desktop follow-up. It requires a prior full-import run that verified the vendor
tree and reached a desktop session. It records that result and checkpoint's
hashes, rechecks the native ledger and ten core vendor executables/interpreter
files, and repeats the graphical sessions without another import or filetype
reset. Its passing result must be read together with the full-import evidence;
it does not claim to repeat the complete vendor-file scan.
