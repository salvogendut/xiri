# IRIX 6.5.22m reference and vendor probes

The latest paired transport measurements are in the [recvmsg lab](../irix-recvmsg/README.md), including guarded output records, queue-consumption checks and original-IRIX error ordering.

Follow-up: [unmodified asa and echo now run on Xiri](../../docs/results/2026-10-30-irix-lp64.md)
with their original libc and rld. The [desktop lab](../irix-desktop/README.md)
adds library/resource inventory and native 4Dwm/Toolchest startup comparisons. The rejection tests below remain pinned to
the earlier static kernel.

The user supplied an installed IRIX disk and a MAME Indy firmware bundle on
2026-10-30. Native `uname -R` reports `6.5 6.5.22m`. `desktop_base`, `eoe`, and
`x_eoe` report 6.5.22. See the [result record](../../docs/results/2026-10-30-irix-vendor-baseline.md)
for native command behavior, the Xiri rejection baseline, and reference-boot
limitations. The original desktop has not been qualified.

[`manifest.json`](manifest.json) pins the supplied archives, extracted CHD,
firmware, four vendor executables, and the tested Xiri kernel. No firmware,
disk image, vendor binary, or library is stored in Git. Prepared media and
extracted files live under ignored `.work/irix-reference/`.

## Supplied inputs

The instructions, launchers, checksums, and `indy_4610.zip` were supplied in
`~/Downloads/RUNIRIX/`. The RAR5 archives were in the parent `~/Downloads/`:

| Archive | Contents | Use |
| --- | --- | --- |
| `irix65_chd.rar` | `irix65.chd`, 5,664,440,320 bytes | Installed system |
| `irix-sgi-freeware-cdroms-chd.rar` | `irix-sgi-freeware-cdroms.chd`, 8,577,503,232 bytes | Optional package disk; not used in these tests |
| `indy_4610.zip` | Indy PROM and two other ROM files | Only `ip24prom.070-9101-011.bin` used by IRIS |

All three archives match the accompanying MD5 list; SHA-256 pins are retained
for the RAR files and extracted system CHD. The provided launchers target MAME
`indy_4610` with `xl24` graphics. They were inspected, not executed. MAME itself
remains unqualified on this host.

## Prepare working media

The host's 7-Zip build did not open these RAR5 files. The extractor uses the
installed libarchive reader, validates the pinned archive and CHD hashes,
accepts exactly the expected regular file, and refuses existing outputs:

```sh
./scripts/extract-irix-rar.py "$HOME/Downloads/irix65_chd.rar"
```

Extract `ip24prom.070-9101-011.bin` from the ZIP into the same `media` directory
and verify its SHA-256 against the manifest. The CHD is version 5, uncompressed,
with 100,663,296,000 logical bytes and no embedded SHA-1 digest. Direct attachment
with a CHD overlay returned `InvalidFile` in the pinned IRIS build. The tested
route converts it to a sparse raw image using IRIS's existing extraction tool:

```sh
toolbox run -c xiri-iris env \
    RUSTUP_HOME="$PWD/.work/rustup" CARGO_HOME="$PWD/.work/cargo" \
    CARGO_TARGET_DIR="$PWD/.work/target" CARGO_BUILD_JOBS=8 \
    "$PWD/.work/cargo/bin/cargo" +nightly-2026-10-28 \
    build --release --offline --locked --manifest-path "$PWD/.work/iris/Cargo.toml" \
    --bin chd-extract
set -o pipefail
toolbox run -c xiri-iris "$PWD/.work/target/release/chd-extract" \
    "$PWD/.work/irix-reference/media/irix65.chd" /dev/stdout \
    2>.work/irix-reference/chd-extract.log | \
    dd of=.work/irix-reference/media/irix65.raw bs=1M iflag=fullblock conv=sparse
```

Use an unused output path when reproducing alongside an existing lab. The raw
image occupies about 5.3 GiB despite its 93.75 GiB logical size. Its SHA-256 is
`4979bd813d1a17638694a9fdbb5901264c6c816f036fbe54ae5899f296b544a4`.
The extracted CHD hash remained unchanged after conversion.

The SGI volume-header checksum is valid. Root is partition 0, type 10 (XFS),
starting at sector 266240, with 196341760 sectors of 512 bytes. Linux/libguestfs
names it `/dev/sda1`. XFS has 4096-byte blocks, 256-byte inodes, and version
`0x30b4`. Read-only inspection uses `ro,norecovery` inside libguestfs:

```sh
mkdir -p .work/irix-reference/{guestfs-cache,tmp,vendor/usr/bin/X11,vendor/sbin}
export LIBGUESTFS_BACKEND=direct
export LIBGUESTFS_CACHEDIR="$PWD/.work/irix-reference/guestfs-cache"
export LIBGUESTFS_TMPDIR="$PWD/.work/irix-reference/tmp"
guestfish --ro -a .work/irix-reference/media/irix65.raw \
    -m /dev/sda1:/:ro,norecovery:xfs \
    download /usr/bin/asa .work/irix-reference/vendor/usr/bin/asa : \
    download /sbin/echo .work/irix-reference/vendor/sbin/echo : \
    download /usr/bin/X11/4Dwm .work/irix-reference/vendor/usr/bin/X11/4Dwm : \
    download /usr/bin/X11/toolchest .work/irix-reference/vendor/usr/bin/X11/toolchest
```

Runtime files inspected separately include `/lib/rld`, `/lib/libc.so.1`,
`/lib32/rld`, and `/lib32/libc.so.1`. Keep the complete image as the source for
the matching runtime; the rejection probe below does not install these libraries.

## Reference boot

[`iris.toml`](iris.toml) retains the tested configuration with repository-relative
paths. Run it from the Xiri root after preparing the working copy and NVRAM.
The tested reference used the pinned IRIS build with R4400, 256 MiB, Newport,
the supplied PROM, a reflink copy of `irix65.raw`, and `overlay = true`. It had
private NVRAM, ports 18898/18890/18891, NAT subnet `192.168.232.0/24`, and no
forwarded ports. Its local configuration and serial log are retained under
`.work/irix-reference/boot-ci/`.

Blank NVRAM did not present the expected serial menu. The working NVRAM was
seeded from the qualified NetBSD checkpoint, then its own PROM variables were
set to `OSLoader=sash`, `OSLoadFilename=/unix`, `eaddr=08:00:69:12:34:58`,
`netaddr=192.168.232.2`, and `monitor=h`. System/root partitions remained
`scsi(0)disk(1)rdisk(0)partition(8)` and partition 0, with `console=d`.
The original checkpoint was not modified.

Root login required no password. The image uses a custom Bash prompt, so the
generic `iris-ci login` macro timed out after successful login; it expects `#`.
Send `root`, accept the TERM prompt, and wait for `root@IRIX: />`. Subsequent
commands use `iris-ci run --shell sh`. Use `versions -b desktop_base x_eoe eoe
| cat` to avoid its interactive pager. The native command probes were:

```sh
uname -a
uname -R
/sbin/echo XIRI_VENDOR_REFERENCE
printf ' XIRI_VENDOR_O32\n' | /usr/bin/asa
```

The echo and asa outputs were exactly `XIRI_VENDOR_REFERENCE\n` and
`XIRI_VENDOR_O32\n`; asa returned zero. Native `cksum` values for all four
candidate files matched the offline copies. Shutdown uses
`/etc/shutdown -y -g0 -i0`; wait for `Okay to power off the system now.` before
quitting IRIS. No overlay was committed.

This is a limited reference session: boot emitted `xfs_itobp` alerts, the
optional `/disk2` mount failed because a scratch device occupied that ID, and
installed third-party services reported configuration warnings. Those findings
do not invalidate the recorded file checksums or command observations, but a
clean filesystem/desktop reference qualification remains open.

## Unmodified vendor tests on Xiri

Build the pinned [segment kernel and native control](../irix-o32/README.md#writable-elf-data-and-bss),
extract the four candidates above, then run:

```sh
./scripts/probe-irix-vendor.py --mode ci
./scripts/probe-irix-vendor.py --mode ordinary
```

Each run cold-boots a disposable NetBSD guest with the pinned compatibility
kernel. It verifies the original vendor hashes, compiles the direct-exec runner,
runs the native kernel/file/swap smoke probe, and attempts all four vendor
executables between native controls. No ELF bytes are patched or branded.

This baseline **expects vendor `ENOEXEC`**, records the exact errno separately
from exit status, and requires native execution and clean shutdown. Passing
means rejection was measured correctly; it does not mean vendor applications
ran on Xiri. Results remain under `.work/irix-vendor-runs/`.

Further implementation uses the actual loader contracts: o32 `asa`
requests `/usr/lib/libc.so.1`, while n32 `echo` requests `/lib32/libc.so.1`.
Both desktop candidates are n32 and request `/usr/lib32/libc.so.1`. Resolve the
n32 kernel/dispatch path early; it is a confirmed desktop requirement.

The later [o32 query experiment](../../docs/results/2026-10-30-irix-o32-queries.md)
gets asa's original libc through configuration/capability checks and as far as
opening and reading `/lib/rld`. Mapping still fails at `SGI_ELFMAP`; the earlier
rejection baseline above remains pinned. The
[query lab](../irix-o32/README.md#runtime-capability-and-identity-queries) includes
a reference harness that runs the same original direct-trap probe on IRIX,
compares root/user query results, repeats native asa, and waits for a clean halt.

The [ELF-map experiment](../../docs/results/2026-10-30-irix-o32-elfmap.md) now
enters the original rld on Xiri. Its paired
[reference harness](../../scripts/probe-irix-reference-elfmap.py) runs 42 mapping
cases plus an ordinary-user control using original assembly and payloads.
It checks execution, initialized data/BSS, protection faults, repeat mappings,
and preservation of old mappings during relocation. Broader and malformed
cases record syscall outcomes; successful mapping alone does not validate
those layouts. The pinned comparison records IRIX's wider acceptance alongside
Xiri's bounded, stricter contract. Reproduction is in the
[o32 mapping lab](../irix-o32/README.md#bounded-rld-mapping).

The [dispatch reference harness](../../scripts/probe-irix-reference-dispatch.py)
now compares 44 original direct/indirect-call and mapping-hint probes plus
seven asa stdin cases. It uses the same disposable reference workflow, checks
all uploaded inputs and installed runtime checksums, and requires a clean
halt. Exact records are pinned in
[`dispatch-reference.json`](../irix-o32/dispatch-reference.json), with bounded
address variation for non-fixed mappings. The comparison preserves original
IRIX's different unknown-call errors and branch-delay SIGSYS behavior instead
of hiding them. See the [asa execution lab](../irix-o32/README.md#vendor-asa-execution)
for build/run commands and the distinction between this tested filter path
and general vendor compatibility.


## Desktop startup reference

The [desktop inventory and startup lab](../irix-desktop/README.md) records the
transitive n32 closures, selected resource/service files and session-script
roles. Native ldd verifies the static choices, including the internal library
directory. The reference harness checks all extracted ELF files, runs each
desktop program directly and under par with an empty environment and TCP
display `127.0.0.1:99`, and requires complete exits plus clean shutdown.
Both native clients create sockets and encounter connection refusal at the
unused port. This isolates library/client startup from the still-unqualified
graphical reference session. The paired NetBSD probe records earlier mapping
and socket blockers rather than treating identical display errors as proof
of equivalent behavior.

The [TCP lab](../irix-tcp/README.md) adds 168 original o32/n32 interface
comparisons, including an original assembly loopback peer, option/error
behavior, retry timing and the runtime clock query. Vendor content and raw
reference traces remain private.
