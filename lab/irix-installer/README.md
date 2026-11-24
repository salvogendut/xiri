# Original installer and persistent-home lab

This lab follows the user's selected workflow: original IRIX `inst`, then
Software Manager, installing xmahjongg so its own hooks create a **Freeware**
Icon Catalog entry. See the [software plan](../../docs/IRIX-SOFTWARE.md) and
[media findings](../../docs/results/2026-11-01-irix-freeware.md).

`manifest.json` records original inst/swmgr/SoftwareManager/iconcatalogedit,
their 37-path static n32 closure and the original shell templates/manuals.
`inputs.json` pins the selected CD4 xmahjongg/fw_common distributions and the
original generic `/var/inst/machfile`. Extracted bytes remain private in
`.work/irix-freeware/installed` and `.work/irix-freeware/package`.

## Repeat the clean Indy installer check

Use the release that matches the private guest. From the Xiri repository
root, with the matching desktop import already built, prepare the
installer supplement from the original-media donor and May 2004 CD 4.

```sh
release=6.5.22f  # or 6.5.30f
mkdir -p .work/inst-media
python3 lab/irix-installer/prepare-media.py --release "$release" \
  --donor ".work/donors/irix-$release-original-media/irix-donor.chd" \
  --desktop-manifest ".work/imports/irix-$release-v1/manifest.json" \
  --dist .work/irix-freeware/package/cds/cd-4/dist \
  --output ".work/inst-media/$release.iso"
```

The builder verifies the donor and CD hashes, checks shared library
digests against the desktop manifest, and records the selected files in
`vendor.json`. It creates a new ISO. The installer supplement includes the
original `/sbin/stat` used during bootstrap. The input history database
comes from the target itself.

Boot a **disposable** Indy target with the matching supplementary ISO at
SCSI ID 4. As root, mount it, unpack the supplement and ask the original
installer to select the software and report conflicts. Clearing selections
before quitting produces an unattended return to the shell.

```sh
mkdir -p /cdrom
mount -r -t cd9660 /dev/cd0a /cdrom
(cd / && pax -rzpe -f /cdrom/installer.tgz)
export HOME=/ USER=root LOGNAME=root SHELL=/bin/sh TERM=vt100 LANG=C TZ=UTC
export PATH=/usr/local/bin:/usr/X11R7/bin:/bin:/sbin:/usr/bin:/usr/sbin
printf '%s\n' 'keep *' 'install fw_xmahjongg.sw.xmahjongg fw_common.sw.index' \
  'conflicts' 'keep *' quit >/var/tmp/xiri-inst-plan
/emul/irix/usr/sbin/inst -M -r /emul/irix -f /cdrom/dist -c /var/tmp/xiri-inst-plan
/emul/irix/usr/sbin/versions -r /emul/irix fw_xmahjongg
```

The clean v4 kernel predates the MIPS conversion and IRIX file-operation
fixes. See the [dual-release results](../../docs/results/2026-11-24-indy-inst.md)
for the tested kernel and the prerequisites reported by SGI.

To check that SGI can write and read its own installation history, use an
empty alternate root on a disposable guest with module `da98b7d4268` or
later. The Freeware CD's selection files have no base-package prerequisites.

```sh
target=$(mktemp -d /var/tmp/xiri-inst.XXXXXX)
mkdir -p "$target/var/inst"
cp /emul/irix/var/inst/machfile "$target/var/inst/"
inst=/emul/irix/usr/sbin/inst
versions=/emul/irix/usr/sbin/versions
for action in install remove; do
    printf '%s\n' 'keep *' "$action fw_common.sw.selections" conflicts go 'keep *' quit >"$target.commands"
    "$inst" -M -r "$target" -f /cdrom/dist -c "$target.commands" </dev/null
    "$versions" -r "$target" fw_common
    ls -l "$target/var/inst/hist"
    if test "$action" = install; then
        sha256 "$target/usr/freeware/relnotes/selections/gimp"
    else
        test ! -e "$target/usr/freeware/relnotes/selections/gimp" || exit 1
    fi
done
```

After installation, look for the installed product in `versions` and the
sample file digest in the release results. After removal the product row and
sample file disappear. The target retains its own history database.

To reproduce the xmahjongg prerequisite check, add the following two options
to the host's media-builder command above and choose a new output filename.

```sh
--base-media-root "$HOME/Downloads/IRIX media" \
--instigator ../prismatic/target/install-server/instigator
```

The builder checks the [original disc hashes](base-media.json) and copies
the product descriptors, inventories and software archives from Foundation 1
and overlays 1 and 2 for the chosen release. Both overlay discs are needed.
On the guest, use a new alternate root and request the complete selection.

```sh
target=$(mktemp -d /var/tmp/xiri-base.XXXXXX)
mkdir -p "$target/var/inst"
cp /emul/irix/var/inst/machfile "$target/var/inst/"
cat >"$target.commands" <<'EOF'
keep *
install c++_eoe.sw.lib eoe.sw.base eoe.sw.efs compiler_eoe.sw.cpp compiler_eoe.sw.lboot compiler_eoe.sw.lib compiler_eoe.sw.unix x_eoe.sw.eoe fw_common.sw.index fw_xmahjongg.sw.xmahjongg
conflicts
keep *
quit
EOF
/emul/irix/usr/sbin/inst -M -r "$target" \
    -f /cdrom/foundation -f /cdrom/overlay -f /cdrom/dist -c "$target.commands"
```

The expected report is `No conflicts`. The independent `go` trial on a
private guest reached an IRIX device-creation hook. Its results and the
observed game install and removal are in the [installer report](../../docs/results/2026-11-24-indy-inst.md).

To rebuild the conversion checks, run
`python3 lab/irix-installer/build-cvt-probes.py TOOLDIR NEW_OUTPUT`.
Copy the two binaries into the disposable guest and run each one. Exit zero
means all 52 conversions matched the expected binary64 bits and inexact
status. The o32 observer uses paired registers and n32 uses odd wide registers.

## Earlier installer checkpoints

The observer clones the clean ordinary desktop/pipe checkpoint, checks all
inherited and staged hashes, and uses the unchanged qualified pipe kernel.
It creates an ordinary native account under `/usr/people`, checks repeated
setup, writes a home file through native ksh and reads it through original
IRIX asa. Native ABI controls run before and after.

Original `inst` is attempted as root with `HOME=/`, first using its documented
`-H` hardware report, then `-n -M -r /emul/irix -f /cdrom/dist -c` with a
list/quit command file. These are bounded startup/distribution observations,
not an installation success. The native runner owns and removes the process
group; the disposable guest is halted in a finally block. Full hook execution,
GUI Software Manager, catalog launch, reboot persistence and removal remain
separate acceptance work.

```sh
PYTHONDONTWRITEBYTECODE=1 python3 scripts/probe-irix-installer.py
```

Account setup is [setup-xiri-user.sh](../../scripts/setup-xiri-user.sh).
The native account uses `/bin/ksh` and NetBSD's skeleton. IRIX desktop state
must be generated by the clients under that same persistent home. The helper
does not alter the administrative root account or any existing account with a
different home. Its optional numeric UID is used only to make lab checks
repeatable.

## Observed boundary

The [first result](../../docs/results/2026-11-01-irix-installer.md) verifies
account setup, native/foreign shared-file access and cold-boot persistence.
Original inst faults before output: a 1 MiB /dev/zero mmap with SHARED,
AUTOGROW and AUTORESRV is rejected, then libinst writes through MAP_FAILED.
The second probe uses the existing checked mmap tracer and known-fault
controls; both guests halt cleanly.

```sh
PYTHONDONTWRITEBYTECODE=1 python3 scripts/probe-irix-installer-fault.py
PYTHONDONTWRITEBYTECODE=1 python3 scripts/qualify-irix-installer.py \
  .work/irix-installer/runs/ci-e8jv2xtk \
  .work/irix-installer/runs/mmap-ci-pq57kpty \
  --output docs/results/2026-11-01-irix-installer.json
```

## Shared-mapping follow-up

[The new checkpoint](../../docs/results/2026-11-01-irix-installer-shared.md)
uses `probe-irix-installer-shared.py` with a separate kernel pin and fresh copy
of the same clean desktop seed. It passes the previous mmap crash. `inst -H`
prints an incomplete hardware report; the distribution dry run emits a fatal
`sproc` child-launch error before reading packages, despite exiting zero.
Signal-handler registration and hardware queries also remain incomplete.
`qualify-irix-installer-shared.py` checks the original trap instruction,
ordered trace, native/home controls and clean shutdown. The earlier observer,
tracer and their qualified source hashes remain unchanged.

The [sproc reference](../../docs/results/2026-11-01-irix-sproc-reference.md) now
qualifies 112 original-IRIX executions / 200 records for the next process
requirement. It establishes the armed exec/exit release distinction, private
PRDA/LOCAL pages and shared mapping updates. NetBSD sproc implementation and
a subsequent original-inst retry remain pending.


## Sproc follow-up

The [bounded sproc checkpoint](../../docs/results/2026-11-01-irix-sproc.md)
now lets original inst create its child and execute native `/bin/sh`. Run
`scripts/probe-irix-installer-sproc.py` and check the resulting directory with
`scripts/qualify-irix-installer-sproc.py --output FILE`. Inputs, commands and
home setup are unchanged. The [accepted trace](../../docs/results/2026-11-01-irix-installer-sproc.md)
identifies F_DUPFD EINVAL during pipe setup, followed by repeated gettimeofday
ENOSYS and a bounded timeout. Native helper searches also omit `/bin` for
ls/mkdir. No package has yet been installed. Pair calls by PID/LWP now that
the trace includes a child; successful exec register contents are not an
ordinary syscall errno return.


The [F_DUPFD follow-up](../../docs/results/2026-11-01-irix-installer-dupfd.md)
uses `probe-irix-installer-dupfd.py` and `qualify-irix-installer-dupfd.py`.
Both pipe duplications now succeed. The remaining capture shows a bounded
gettimeofday/select loop and unchanged helper search paths at that checkpoint.
The [time follow-up](../../docs/results/2026-11-01-irix-installer-time.md) uses
`probe-irix-installer-time.py` and `qualify-irix-installer-time.py`: time calls
now succeed, while the bounded dry run still times out. The
[helper follow-up](../irix-installer-helpers/README.md) captures full argv,
output, exit and process state. Four native utility aliases let the embedded
bootstrap exit zero, but the foreign parent leaves it unreaped. The
[signal lab](../irix-signal/README.md) now measures registration/delivery,
return and the callback's wait-any mode on original IRIX, with the measured
NetBSD subset qualified in the follow-up below. Installer qualification and native
`stat -qd` also remains incompatible. This is not distribution-read or
installation success.
No package is installed yet.


The [traditional-signal checkpoint](../../docs/results/2026-11-01-irix-signal.md)
now qualifies the measured handler and wait-any subset on NetBSD. The
installer is not retried in that cycle: the user chose to prioritize
[importing installed applications and their existing catalog registration](../irix-installed-desktop/README.md).
Retain this lab for later distribution reading, native utility semantics,
package history and original registration hooks. Copying installed files
does not qualify the installer or its lifecycle.
