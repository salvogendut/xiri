# NetBSD host build and changed-kernel boot — 2026-10-30

The host cross-built a NetBSD 11.0 kernel with identifier
`XIRI_INDY_20261030`. A fresh IRIS process loaded it over TFTP, mounted the
installed SCSI root, and reached multiuser. The guest reported the new
identifier and retained the baseline file checksum and working swap.

## Build inputs and configuration

| Item | Recorded value |
| --- | --- |
| Host | Fedora 44 x86-64, existing `xiri-iris` Toolbox; 43 GiB available RAM and 530 GiB free workspace storage at the start |
| Source | NetBSD 11.0 `src`, `gnusrc`, `sharesrc`, and `syssrc` archives; all SHA-512 values rechecked against the [pinned manifest](../../lab/netbsd-11.0/SHA512SUMS) |
| Host compiler | `gcc` and `gcc-c++` `16.2.1-2.fc44` |
| Native headers | `glibc-devel-2.43-9.fc44`, `zlib-ng-compat-devel-2.3.3-3.fc44`, `ncurses-devel-6.6-1.fc44` |
| Cross compiler | `mipseb--netbsd-gcc (NetBSD nb3 20260326) 12.5.0` |
| Target | `sgimips` / `mipseb`, unprivileged build, eight jobs, X11 disabled |
| Kernel | [XIRI_INDY](../../lab/netbsd-11.0/XIRI_INDY), inheriting `GENERIC32_IP2x`, with a custom identifier, `DEBUG=-g`, and `root on sd0a type ffs` |
| Emulator | [Pinned IRIS build](2026-10-29-iris-build.md), R4400, 256 MiB, Newport, CI mode |

The kernel configuration is retained separately from the extracted source;
no NetBSD C or assembly source patch was needed. Fixing root to `sd0a`
allows the kernel to load from `sq0` while using the existing disk filesystem.
Debug information is retained for the next debugger experiment.

The repeatable entry point is
[`scripts/build-netbsd-kernel.sh`](../../scripts/build-netbsd-kernel.sh).
It invokes NetBSD's `build.sh` with separate object, tool, and destination
directories under `.work/netbsd-build/`, and uses `kernel.gdb=` for the kernel.
The `kernel` mode skips rebuilding tools. Logs and output hashes stay in
`.work/`; kernel timestamps and build counters are retained, so this is a
repeatable procedure rather than a claim of identical bytes across clean builds.

The source archives were verified and extracted during this run, and their
manifest was recorded in the source stamp before exercising the script's
kernel mode. Future preparation refuses to overwrite an unmarked source tree.

## Host compiler compatibility and timing

The first tools attempt failed in bundled Texinfo because GCC 16 defaults to
C23 (`__STDC_VERSION__=202311L`). Selecting GNU C17 through `HOST_CFLAGS`
cleared that failure, but GMP's configure stage deliberately strips CFLAGS
while detecting its ABI. The working settings are:

```text
HOST_CC=cc -std=gnu17
HOST_CFLAGS=-O2 -std=gnu17
```

These apply only to the host tools. The kernel is built by the NetBSD MIPS
cross compiler using its own target flags. The failed logs are retained as
`tools-default-c.log` and `tools-cflags.log` in `.work/netbsd-build/`.

| Operation | Observed time |
| --- | --- |
| Successful resumed tools build | 07:13:20–07:16:26 UTC, 3 min 6 s; excludes earlier failed work |
| Initial kernel compile | 07:17:04–07:17:26 UTC, 22 s |
| Incremental change to fixed disk root | 07:21:16–07:21:19 UTC, 3 s |

A subsequent unchanged kernel build preserved both kernel hashes while
packaging the virtual CD. `genisoimage 1.1.11` created the ISO; its timestamp
can change on regeneration.

## Cold-boot procedure

The [release disk checkpoint](2026-10-29-indy-netbsd-install.md#retained-artifacts)
and NVRAM hashes were checked before making copies at
`.work/indy-netbsd-kernel/disk.raw` and `nvram.bin`. The baseline remains
untouched. The test NVRAM was changed at the PROM with `setenv AutoLoad No`
and saved with `iris-ci rtc-save`, so the next process waits at the menu.
The initial attempt to interrupt automatic boot missed its prompt and
booted the release kernel; it was shut down cleanly before proceeding.

From the repository root, start the emulator in one terminal:

```sh
toolbox run -c xiri-iris "$PWD/.work/target/release/iris" \
  --config lab/indy-netbsd/iris.toml --ci \
  --nvram .work/indy-netbsd-kernel/nvram.bin \
  --scsi1 .work/indy-netbsd-kernel/disk.raw \
  --ci-socket .work/indy-netbsd-kernel/iris.sock \
  --serial-log .work/indy-netbsd-kernel/final.serial.log \
  > .work/indy-netbsd-kernel/final.stdout.log 2>&1
```

In a second terminal at the repository root:

```sh
export IRIS_SOCKET=.work/indy-netbsd-kernel/iris.sock
.work/target/release/iris-ci start
.work/target/release/iris-ci serial-wait 'Option?' --timeout 30
.work/target/release/iris-ci serial-send 5
.work/target/release/iris-ci serial-send 'boot -f bootp()/netbsd-XIRI_INDY'
```

The test uses a fresh emulator process rather than a RAM snapshot. The first
custom-kernel run is in `cold.serial.log` and `cold.stdout.log`.

## Matching the guest kernel file

The first custom boot reached multiuser but `savecore` warned
`dumpdev /dev/console is tty; override kernel`. The guest's `/netbsd` still
contained the release kernel, so its symbol addresses did not match the
running kernel. Installing the matching file corrected the warning.

Attach the kernel ISO using the controller:

```sh
.work/target/release/iris-ci cdrom-load 4 "$PWD/.work/netbsd-build/kernel.iso"
```

At the guest's root shell, mount it, verify its hash against
`.work/netbsd-build/kernel.sha256`, preserve the release file, and install:

```sh
mkdir -p /cdrom
mount -t cd9660 -o ro /dev/cd0a /cdrom
sha256 /cdrom/netbsd
test -e /netbsd.release || cp -p /netbsd /netbsd.release
cp /cdrom/netbsd /netbsd
chmod 755 /netbsd
sha256 /netbsd
umount /cdrom
```

Both guest hashes matched the host's TFTP kernel hash. With the matching
file in place, `savecore -n` reported `no core dump`. For later rebuilds,
install the new file before cleanly halting the guest, stop IRIS, and load
the corresponding TFTP kernel in a fresh process.

## Final cold-boot verification

The final fresh process reached the login prompt with the matching kernel
installed on disk. Its serial log contains:

```text
NetBSD 11.0 (XIRI_INDY_20261030) #1: Fri Oct 30 07:21:17 UTC 2026
/dev/rsd0a: file system is clean; not checking
savecore: no core dump
```

After logging in as root, the checks were:

```text
kern.configname = XIRI_INDY_20261030
3540535338 33 /root/xiri-probe
Device      1K-blocks     Used    Avail Capacity  Priority
/dev/sd0b       32736        0    32736     0%    0
SHA256 (/netbsd) = 2428f60fbf6f830dcddd031b8540d0d52cbb458ee6a0166b257b0bae9941ed6c
```

This confirms the running build identifier, the retained baseline marker,
active swap, and the matching kernel file after another cold boot. Full
serial and emulator logs remain in `.work/indy-netbsd-kernel/final.serial.log`
and `final.stdout.log`. `shutdown -h now` completed disk syncing and
filesystem unmounting and returned to the PROM menu before IRIS was stopped.

## Artifacts and remaining work

| Artifact | Bytes | SHA-256 |
| --- | ---: | --- |
| `.work/netbsd-11.0/tftp/netbsd-XIRI_INDY` | 6,030,084 | `2428f60fbf6f830dcddd031b8540d0d52cbb458ee6a0166b257b0bae9941ed6c` |
| `.work/netbsd-build/obj/sys/arch/sgimips/compile/XIRI_INDY/netbsd.gdb` | 37,997,828 | `760b1f920541a8de6807e06a5e581745ad4116be6757fd3217fb6df080f15726` |
| `.work/netbsd-build/kernel.iso` | 6,402,048 | `06508c4a26d64d0847512635b4a29f329f0c019a67a5e71e557416756a1b50e0` |
| Test `nvram.bin` after disabling automatic boot | 8,192 | `ee883474d52f09278287b2044f7aeca61d2e7bc39c0bb8fd85c983ab64063d15` |

The ELF is 32-bit, big-endian MIPS, with entry point `0x88069000`.
The debug artifact contains `.debug_info`, `.debug_line`, and `.symtab`;
its `main` symbol is at `0x88442740` and `kernel_ident` at `0x8846e520`.
These addresses describe this exact build only.

Debugger attachment and breakpoint continuation, an unattended probe with
timeouts, ordinary-versus-CI comparison, sustained disk/network qualification,
snapshots, graphics, and physical hardware remain pending. The previously
recorded R5000, network-transfer, entropy, and device-probing issues were not
resolved by this kernel configuration change.
