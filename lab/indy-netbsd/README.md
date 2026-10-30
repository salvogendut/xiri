# IRIS Indy / NetBSD 11.0 guest

This lab configuration runs a 256 MiB R4400 Indy with Newport graphics, an
8 GiB SCSI disk, a virtual CD, and a serial console. Run commands from the
repository root. It uses the [verified NetBSD inputs](../netbsd-11.0/README.md)
and the [pinned IRIS build](../iris/README.md). Derived images and logs live in
`.work/` and are excluded from Git.

Prepare the inputs after running `scripts/fetch-netbsd-11.sh` and
`scripts/build-iris.sh`:

```sh
mkdir -p .work/indy-netbsd
test -e .work/indy-netbsd/disk.raw || truncate -s 8G .work/indy-netbsd/disk.raw
genisoimage -quiet -R -J -V NETBSD_SETS -o .work/indy-netbsd/sets.iso \
  .work/netbsd-11.0/sgimips/binary/sets
isoinfo -R -i .work/indy-netbsd/sets.iso -f
```

The ISO must expose `kern-GENERIC32_IP2x.tgz`, `modules.tgz`, `base.tgz`,
`etc.tgz`, `comp.tgz`, and `rescue.tgz` at its root. `-R` preserves the long
kernel set name.

Start IRIS inside the `xiri-iris` Toolbox:

```sh
toolbox run -c xiri-iris "$PWD/.work/target/release/iris" \
  --config lab/indy-netbsd/iris.toml --ci \
  > .work/indy-netbsd/iris.stdout.log 2>&1
```

In a second terminal at the repository root, control its configured socket:

```sh
export IRIS_SOCKET=.work/indy-netbsd/iris.sock
.work/target/release/iris-ci start
.work/target/release/iris-ci serial-read
```

For a new NVRAM file, first start IRIS with an additional `--headless` argument
to reach the serial PROM menu. If automatic boot fails, send an empty line to
reach the menu. Choose `5` for the Command Monitor and send
`setenv -f console d` using `iris-ci serial-send`. Run `iris-ci rtc-save`, then
`iris-ci quit`. Restart with the command above, without `--headless`, so
Newport is enabled for the guest. This bootstrap used IRIS's embedded PROM;
no external PROM file is required for this recorded configuration.

Boot the installer with `boot -f bootp()/netbsd-INSTALL32_IP2x`. In sysinst,
install to `sd0` and choose the six available sets above. Use a custom set
selection to omit graphics firmware and X11, which are absent from this ISO.
The virtual CD is
`cd0a`; set its binary set directory to `/`. The default CD path
`/sgimips/binary/sets` does not match this ISO. Complete the install and set
the PROM variables documented in NetBSD's `sgimips/INSTALL.txt` for SCSI ID 1:

```text
setenv systempartition scsi(0)disk(1)rdisk(0)partition(8)
setenv osloadpartition scsi(0)disk(1)rdisk(0)partition(0)
setenv osloadfilename netbsd
setenv osloadoptions auto
setenv osloader boot
```

Save NVRAM with `iris-ci rtc-save`. Shut the guest down cleanly before stopping
IRIS; quitting the emulator while the guest writes to disk can leave FFS
inconsistent.

The recorded disk has a root partition of 16,703,488 sectors beginning at
sector 8,256, and a swap partition of 65,472 sectors beginning at 16,711,744
(512-byte sectors). Verify the installer layout before formatting. This run
had to add the reserved swap partition after installation; the exact repair
commands are in the run record.

The installed lab uses hostname `xiri-indy`, DHCP on `sq0`, UTC, and `/bin/sh`.
Root has an empty password for serial access; sshd is disabled. Entropy setup
is incomplete. The clean disk and NVRAM checkpoint is retained locally in
`.work/indy-netbsd/base/`; its hashes are in the run record. It contains a disk
checkpoint, not an emulator RAM snapshot.

The R5000 profile reached the NetBSD 11.0 install kernel but panicked with
`r5k picache line size 16`. The R4400 profile installed and booted to multiuser.
The ISO is the recorded working set source; the NFS attempt and a larger HTTP
transfer did not complete during installation. The later [I/O qualification](../../docs/results/2026-10-30-netbsd-io.md) passes bounded transfers on the installed guest with the NFS fix; the installer stall remains open. See the
[run record](../../docs/results/2026-10-29-indy-netbsd-install.md) for observed
results and remaining qualification work.

For kernel development, use the [host kernel build](../netbsd-11.0/README.md#host-kernel-build)
and the [custom-kernel boot procedure](../../docs/results/2026-10-30-netbsd-kernel.md).
That experiment uses separate disk/NVRAM copies under
`.work/indy-netbsd-kernel/`, leaving the release checkpoint in `base/` intact.

## Automated probes

After the [custom-kernel setup](../../docs/results/2026-10-30-netbsd-kernel.md),
keep `.work/indy-netbsd-kernel/disk.raw` and `nvram.bin` stopped and clean.
The disk must contain the matching `/netbsd`, and NVRAM must have
`AutoLoad No`. Each invocation copies them into a new directory under
`.work/netbsd-probes/`, uses separate ports, and cold-boots over TFTP:

```sh
./scripts/probe-netbsd.py
./scripts/probe-netbsd.py --debugger
```

The second command requires the [cross-debugger](../netbsd-11.0/README.md#cross-debugger).
It attaches at the PROM, loads `netbsd.gdb`, checks breakpoints at `main` and
`cpu_rootconf`, then detaches and explicitly resumes the CPU. The retained
[GDB settings](debugger.gdb) match IRIS's 64-bit remote registers; the guest
kernel remains 32-bit. These checks validate breakpoints, registers,
disassembly, and reading `kernel_ident`, not general C ABI inspection or
stack unwinding.

The [guest probe](probe.sh) verifies the kernel identifier and hash, the
baseline file checksum, active swap, and a 128 KiB file copied from the
virtual CD to the root disk. Success requires exit status zero, the expected
output marker, and a clean shutdown. Full serial and emulator logs, the
launch command/configuration, and `result.json` stay in each run directory;
debugger runs also retain `gdb.log`.

The default boot and probe deadlines are 300 and 30 host seconds; override
them with `--boot-timeout` and `--probe-timeout`. Startup, debugger setup,
control commands, and shutdown have bounded waits too. On a timeout the
harness interrupts the command and attempts a clean halt; if that fails,
only the disposable run is terminated and `clean_shutdown` is false.

Exercise the two intentional failure cases:

```sh
./scripts/probe-netbsd.py --case exit
./scripts/probe-netbsd.py --case timeout --probe-timeout 3
```

These must exit with host status 23 and 124 respectively. A guest exit is
recorded separately from a timeout, where no completed guest status exists.
Other harness failures exit nonzero and retain their error in `result.json`.

To compare ordinary execution with Newport enabled on a host virtual display:

```sh
toolbox run -c xiri-iris sudo dnf install -y \
  xorg-x11-server-Xvfb xorg-x11-xauth libXcursor libXi libXrandr \
  libXinerama libxkbcommon-x11
./scripts/probe-netbsd.py --mode ordinary
```

This sets `ci = false`, uses the TCP serial console and monitor, and runs
the host window under Xvfb. It does not disable Newport. This comparison
does not test a guest X server or establish graphics correctness.

## Disk and network qualification

Build the pinned [IRIS fork](../iris/README.md), then run:

```sh
./scripts/qualify-netbsd-io.py
./scripts/qualify-netbsd-io.py --mode ordinary
```

Each run clones the stopped custom-kernel checkpoint into a unique directory
under `.work/netbsd-io/`. It generates two distinct 16 MiB payloads and an ISO,
writes and checksums both files for three rounds, cleanly halts the guest, then
starts a fresh emulator process on the same disk and checks the persisted files.
The second boot must report a clean root filesystem. This exercises 96 MiB of
disk writes and reads back 32 MiB after a cold start.

Network checks copy a payload through the built-in NFS server in both
directions, repeat HTTP downloads, and send a TCP upload to a host receiver.
SHA-256 comparisons check the destination bytes. The HTTP and TCP services bind
to host loopback; the guest reaches them through NAT at `192.168.231.1`. NFS
exports only that run's generated files. NetBSD needs UDP for both MOUNT and
NFS (`mount_nfs -3 -u -U`), plus the fork's AUTH_SYS negotiation fix.

Use `--case disk` or `--case network` to isolate a workload, `--size-mib` and
`--rounds` to change its size, and `--io-timeout` to change the per-operation
host deadline (default 300 seconds; multiplied by rounds for the disk script).
The test NFS mount is soft with bounded retries so unavailable exports can
fail and permit cleanup; this is a test setting, not a production mount recipe.

Each directory retains `result.json`, input hashes, full serial/emulator logs,
and network/device counters. A run succeeds only when every check passes and
the guest halts cleanly. Failures retain diagnostic counters when reachable
and attempt the same bounded cleanup as the smoke harness. Disk contents and
logs remain available for inspection. These tests do not qualify power-loss
recovery, guest X, snapshots, or physical hardware.
