# IRIX reference media and first vendor tests — 2026-10-30

The supplied image is usable for file extraction and a limited native reference
session. It boots as **IRIX 6.5.22m** in the pinned IRIS emulator. Original
`echo` and `asa` run successfully there. On the current Xiri kernel, unmodified
`asa`, `echo`, `4Dwm`, and Toolchest all return **`ENOEXEC`**, in both CI and
ordinary execution. Native NetBSD controls continue to pass.

The first desktop ABI inventory changes the implementation priority: `4Dwm`
and Toolchest are n32. n32 support is now a confirmed requirement for this
reference desktop, alongside the dynamic loader/runtime work.

## Inputs and preservation

The user supplied `irix65_chd.rar` and the optional freeware RAR directly in
`~/Downloads/`, with instructions, MAME launchers, checksums, and `indy_4610.zip`
in `~/Downloads/RUNIRIX/`. Both RAR files and the ZIP match the accompanying
MD5 values. The [manifest](../../lab/irix-reference/manifest.json) pins their
identities and the selected vendor files. The system CHD SHA-256 is
`f0615ce71308026c1366c289be8de8a640a0ca83ca7b808139acb71f3482a659`.

The system archive contains a 5,664,440,320-byte uncompressed version 5 CHD,
representing a 100,663,296,000-byte virtual disk. It has no embedded SHA-1
digest. A sparse raw conversion occupies about 5.3 GiB and has SHA-256
`4979bd813d1a17638694a9fdbb5901264c6c816f036fbe54ae5899f296b544a4`.
Conversion left the extracted CHD hash unchanged. The optional freeware CHD
was listed but not extracted or attached.

The SGI volume header has a valid checksum. The root XFS filesystem starts
at sector 266240 (512-byte sectors); libguestfs inspected it with
`--ro` and `ro,norecovery`. The reference boot used a separate raw disk copy,
copy-on-write overlay, and private NVRAM. No vendor binary, library, firmware,
or image is committed to Git. The original downloads were only read.

## Native IRIX reference

IRIS remained at `484452d963d2da4e2a7559e88bcc33da0f2a0c01`, binary SHA-256
`cc6561d0bdfec6ce30d656caf4a6eaee6ffbf622e5348c3b77b73810d5293f56`.
The provided Indy PROM is 524288 bytes, SHA-1
`ac663a4db68528e400487e98cbf901f620fb30ce`. This run used R4400, 256 MiB,
Newport, and CI mode. No emulator or NetBSD source change was needed for media
intake or these baseline tests.

| Observation | Result |
| --- | --- |
| `uname -a` | `IRIX IRIX 6.5 10070055 IP22` |
| `uname -R` | `6.5 6.5.22m` |
| Desktop packages | `desktop_base`, `eoe`, and `x_eoe` report 6.5.22; X11 is based on X11R6.6 |
| Native n32 `/sbin/echo` | Exact `XIRI_VENDOR_REFERENCE\n` output |
| Native o32 `/usr/bin/asa` | Input ` XIRI_VENDOR_O32\n` produces `XIRI_VENDOR_O32\n`, status 0 |
| Candidate file integrity | Native POSIX `cksum` and sizes match all four offline copies |
| Shutdown | IRIX reports `Okay to power off the system now.`; emulator then exits |

Direct CHD attachment with an overlay failed with `InvalidFile`; the raw copy
worked. The cause of that CHD limitation was not investigated. Blank NVRAM
needed serial-console setup; the tested run seeded private NVRAM from the
qualified checkpoint and changed only its own IRIX boot variables. The custom
Bash prompt also required manual login and `iris-ci run --shell sh`.

Boot reported XFS `xfs_itobp` alerts. It also attempted to mount the optional
freeware disk at `/disk2`, where the lab attached a scratch volume, and several
third-party services reported configuration errors. The guest reached login,
ran the selected commands, and shut down, but these results do not establish
filesystem health, ordinary-mode IRIX boot equivalence, or desktop operation.
Preserve these alerts for separate image/emulator diagnosis.

## Actual executable requirements

A read-only scan of regular ELF files under `/sbin`, `/usr/bsd`, and `/usr/bin`
(including its subdirectories) found 417 ELF32 big-endian MIPS files: 405 n32
and 12 o32. Symlinks are not counted, and the image includes third-party
software, so this is not an inventory of every SGI-supplied executable.

| Candidate | ABI / flags | Entry | Requested interpreter | Direct libraries |
| --- | --- | --- | --- | --- |
| `/usr/bin/asa` | o32, MIPS II, `0x10000005` | `0x00400e60` | `/usr/lib/libc.so.1` | `libc.so.1` |
| `/sbin/echo` | n32, MIPS III, `0x20000024` | `0x10000ff0` | `/lib32/libc.so.1` | `libc.so.1` |
| `/usr/bin/X11/4Dwm` | n32, MIPS III, `0x20000024` | `0x10059bac` | `/usr/lib32/libc.so.1` | 12; recorded in manifest |
| `/usr/bin/X11/toolchest` | n32, MIPS III, `0x20000024` | `0x1000df18` | `/usr/lib32/libc.so.1` | 7; recorded in manifest |

These are the actual `PT_INTERP` strings, not guessed `/lib/rld` paths. The
matching image contains both o32 and n32 libc/rld runtime files; the libc
entry/bootstrap and rld relationship must be traced as part of implementation.
`asa` is the small o32 command selected for runtime bring-up. It has RX text at
`0x00400000`, RW data at `0x10004000`, 16 KiB ELF alignment, additional
MIPS/ELF headers, and no Xiri note. These already exceed the synthetic loader's
accepted identity, address window, and static-only layout.

`4Dwm` directly needs the SGI `libimdXutil`, `libimdUtil`, and `libimdFtrIcon`
libraries, plus Motif/X, math, C++, and libc libraries. Toolchest needs Motif/X,
`libgen`, C++, and libc. This records direct dependencies only; transitive
libraries, resources, services, and display requirements remain to be mapped.

## Xiri rejection baseline

Both runs use NetBSD commit `6a162a938061d16a60842fd9bb31d69e546d66dc`, kernel
identifier `XIRI_IRIX_SEGMENTS_20261030`, SHA-256
`8d91316b80352d4f271bb97ac993947f309275433709a7f32df73e40fc005366`.
The [new probe](../../scripts/probe-irix-vendor.py) hashes the original vendor
files, imports exact copies into disposable guests, calls `execve` directly,
and captures errno through a close-on-exec pipe. Native controls run before
and after, alongside the existing native kernel/file/swap smoke check.

| Run | Vendor observations | Native controls | Duration | Shutdown |
| --- | --- | --- | --- | --- |
| `ci-wjhy6aib` | All four `ENOEXEC=8`; no vendor code executed | Both pass | 147.683 s | Clean |
| `ordinary-k9b49hjv` | All four `ENOEXEC=8`; no vendor code executed | Both pass | 152.451 s | Clean |

The six-case matrices pass their **rejection** expectations. This is a measured
compatibility boundary, not a vendor-execution success. The harness does not
patch ELF identity or supply the runtime at this stage. Post-run hashes confirm
all imported executables remain unchanged. The [retained JSON](2026-10-30-irix-vendor-baseline.json)
contains all twelve observations, source and media pins, and native reference
results. Full logs and working disks stay under `.work/irix-reference/` and
`.work/irix-vendor-runs/`.

## Next work

Use unmodified `asa` and its matching runtime to guide o32 recognition,
interpreter/bootstrap, address layout, auxiliary data, and syscall work. Keep
the original-IRIX input/output check as the acceptance target. Establish the
current NetBSD kernel/dispatch route for n32 now, using `echo` as the small n32
target before the supplied desktop. A synthetic dynamic probe can isolate
failures, but must support these concrete vendor tests.

Reference-image XFS alerts and a clean graphical session need separate
qualification. Reproduction and media preparation are documented in the
[reference lab](../../lab/irix-reference/README.md).
