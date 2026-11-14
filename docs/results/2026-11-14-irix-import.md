# Reproducible IRIX 6.5.22f vendor import

The versioned vendor importer passes reproducibility, host tests and NetBSD
desktop smoke checks. This is the vendor-payload stage of the
[installation plan](../XIRI-INSTALLATION.md); native packaging and a clean
NetBSD target remain separate work. The [machine-readable record](2026-11-14-irix-import.json)
distinguishes the main desktop run from the focused native-session follow-up.

## Payload and reproduction

The [profile guide](../../profiles/README.md) documents the maintained
`./xiri import` command. It works without a prepared NetBSD image, historical
staging caches or the selected-image pointer. The source is our
[original-media 6.5.22f donor](2026-11-14-irix-donor.md), pinned by CHD and raw
hashes. No download of a preinstalled IRIX image is needed.

Two independent builds of desktop, fonts and Acrobat produce byte-identical
archives and manifests:

| Result | Value |
| --- | --- |
| Profile | `profiles/irix-6.5.22f-v1.json` |
| Payload | 62,109,118 bytes; SHA256 `6feb87643a47b0128fe635b7d06903ef2e78da0317ba29c5a88a700c85403dec` |
| Manifest SHA256 | `61614b1dc24ed332641a20630603c012f69268b787ff6c5aebd85db756eca071` |
| Explicit payload paths | 1,738: 1,534 files, 91 directories, 113 symlinks |
| File bytes before compression | 196,463,615 |
| Recorded library edges | 1,636 |
| Native Xorg font files | 22 |
| Selected system catalog entries | 94, across 10 pages |
| Omitted catalog links | 11, because their targets are not included |
| Host tests | 78 passed, including 8 new import tests |

The output manifest records each source/destination, content hash, mode,
source type, canonical path and dependency edge. Parent directories are
generated with normalized ownership and modes. Archive symlinks are never
created on the host. Executable/library donor symlinks are copied as regular
files, including their canonical names. Both archive ordering and gzip headers
are deterministic. Required missing files, unsupported components, unsafe
destinations, symlink parents, source mismatches and unresolved libraries stop
the build before an installable payload is published.

Acrobat is an optional component. GIMP, GNOME and xmahjongg are absent from this
donor; requesting them reports the missing source before opening the image.
Their already-qualified 6.5.22m resources remain in the existing manual CHD.

## Native extraction finding

The first two disposable imports stopped at file verification. The archive's
contents match the host manifest, but the guest's `/emul/irix/lib/rld` did not.
The persisted failure had hash
`52195d2c442abc1eebf9a941b0dc09c185b08ee8a97c43800d46f57ea35a1e14`, versus the
expected `30228b54c1e5585b365514eb7c9895b03cc0f61cb898e05e3ddafece87863439`.
Its 16 KiB region at offsets `0x74000`–`0x77fff`, which should be zero, contained
nonzero data. File size and mode were correct.

The base supplies bsdtar/libarchive 3.7.7. A direct copy of the verified CD file,
`tar` extraction to stdout, and native `pax` extraction all reproduce the
expected hash. The pax copy also has the expected sparse block allocation.
Reinstalling the **entire** vendor tree with `pax -rz -pe` passes all 1,534 file
hashes. The maintained harness therefore uses pax, retaining the checksum
gate. The exact libarchive/filesystem cause is deferred; no emulator or kernel
change was needed for this workaround.

An earlier logout check called `xiri-logout` through a separate login shell,
which correctly rejected the missing session environment. The corrected test
invokes logout through winterm, as the logged-in user. Early failures also led
to fixing diagnostic output in a writable directory, rather than on the
read-only probe CD.

## Native acceptance and limits

The harness copies the November 14 controls CHD and uses its pinned kernel,
module, native services, Xorg configuration and `819c6825` emulator. It removes
the entire old `/emul/irix` tree and imported font directory, installs the new
payload, verifies every file, then regenerates accounts, devices, font indexes
and the augmented filetype database. Old vendor files cannot satisfy missing
libraries or resources. The original manual CHD is preserved.

The final fresh-copy run verifies all imported file hashes and demonstrates
full-screen xdm, original 4Dwm/Toolchest/Icon Catalog/winterm/xclock, File Manager,
and two IRIX logins with successful logout between them. In both sessions,
winterm reports user `xiritest`, home and working directory
`/usr/people/xiritest`, and successfully executes an IRIX `/bin/sh` command.

The final assertion in that run falsely rejected native ctwm: it searched for
the basename with `pgrep -x`, while NetBSD retained its full launch path.
The screenshot already showed the native desktop. The harness now matches
`^/usr/X11R7/bin/ctwm( |$)`. A focused cold boot of the cleanly halted test disk
passes that corrected check, confirms native UID 1236, a visible uxterm window
and 1280×1024 X dimensions. Both runs halt cleanly and preserve their source
images. The original main-run result remains marked failed; qualification
combines its completed desktop checks with the passing focused follow-up,
rather than claiming a single uninterrupted passing run.

The native base and existing user homes are inherited. The diagnostic user's
catalog shows 16 pages including saved user state; the payload itself supplies
94 system entries in 10 pages. This does not qualify a fresh account setup,
every catalog application, all Acrobat functions or installation on an
unmodified NetBSD kernel.

The vendor winterm wrapper recorded a nonfatal `gettxt` segmentation fault;
its fallback still started winterm and a working shell. The imported gettxt
hash matches the earlier 6.5.22m reference, and its ELF interpreter is
`/usr/lib32/libc.so.1`. This is recorded for a separate helper investigation,
without attributing it to the release change or claiming its cause is known.

IRIS upstream `49210388` was fetched at the start of the cycle and is already
included in `xiri` at `7c4552a6`. There were no incoming commits and no fork
changes. IRIX 6.5.30 retains its separate donor/profile/qualification roadmap.

## Retained artifacts and next step

The retained payload is `.work/imports/irix-6.5.22f-v1/`, with its manifest and
`verification/` evidence: the exact executed probes, original result records,
logs and PNG screenshots. `verification/desktop/desktop-filemanager.png` shows
the imported desktop; `verification/native/native-ctwm.png` shows the native
control. Small failed-attempt records preserve the extraction diagnosis.
The verified donor and selected manual-test CHD are retained separately.

Temporary raw disks, appliance caches, duplicate payloads, probe CDs and
disposable emulator disks are removed after qualification. Cleanup totals and
the stopped-process checks are recorded in the linked JSON. Removed files total
12.77 GiB of allocated space, including the earlier 8.36 GiB inspection disk/cache.
Reflink copies share blocks, so that total is not exclusive physical space freed.
Filesystem availability increased by 1.16 GiB during the final cleanup pass;
the earlier inspection cleanup was not measured with a filesystem free-space
comparison. All five recorded test process groups are stopped and no process
held the temporary disks when they were removed.

The next installation stage is packaging the matching native kernel/module,
Xorg/Newport/Type1 support, FAM/rpcbind and maintained runtime/configuration,
then qualifying installation and repeat installation on a clean NetBSD target.
