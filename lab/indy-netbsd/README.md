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
transfer did not complete. See the
[run record](../../docs/results/2026-10-29-indy-netbsd-install.md) for observed
results and remaining qualification work.
