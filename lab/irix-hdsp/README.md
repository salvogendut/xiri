# Measuring the IRIX HDSP master device

The [mapped playback add-on](playback/README.md) uses this HDSP baseline
and adds ordinary SGI Audio Library playback. The qualification probe's
`--silence-test-gain` selects negative infinity for both output channels.


The n32 probe uses the same calls and layouts as SGI libaudio. Its ordinary
invocation reads resource IDs, parameter descriptors, interface names and
current gains. With `--set-test-gain` it writes two distinct levels to the
default analog output. `--event-test` additionally subscribes to gain changes,
sets the same levels, verifies the resulting event and drains its queue. Use
either write option on a disposable test disk.

```sh
sh lab/irix-hdsp/build.sh .work/netbsd-octane-build/tools/bin/mips64--netbsd ./hdsp-build
```

To measure original IRIX, add `--hdsp-query ./hdsp-build/hdsp-query` to the
[donor verification command](../../scripts/probe-irix-donor.py). It enables
the emulated audio board, attaches a private scratch SCSI disk and collects
`hdsp-reference.txt` from the disposable donor copy. The report includes
the machine's audio identity, the original panel traces and the n32 probe
results. In serial-only mode the donor probe reads the resource graph and skips the graphical checks. The 6.5.22f original-media donor is an A2 Indy and the 6.5.30f
donor is an A3 O2. Both Xiri target desktops run on an A2 Indy.

Build the matching Indy kernel, PROM image and module from the repository root.
The kernel provides MIPS long conversions. The module supplies the IRIX HDSP ABI.
Use new output directories for the two sets of floating-point probes.

```sh
sh lab/ip28-kernel/build.sh ../NetBSD-xiri .work/netbsd-octane-build/tools ./kernel-build \
  "$PWD/lab/irix-module/XIRI_IRIX_MODULE"
python3 lab/irix-installer/build-cvt-probes.py .work/netbsd-octane-build/tools ./cvt-build
python3 lab/irix-installer/build-cvt-probes.py --trunc .work/netbsd-octane-build/tools ./trunc-build
sh lab/ip28-kernel/build-module.sh ../NetBSD-xiri .work/netbsd-octane-build/tools ./module-build
sh lab/irix-hdsp/package.sh ./module-build/module/compat_irix_o32.kmod \
  ./kernel-build/kernel ./hdsp-build/hdsp-query ./cvt-build ./trunc-build ./indy-hdsp.iso
```

SGI describes the resource hierarchy, parameter types and public calls in
its [Digital Media Programming Guide](https://techpubs.jurassic.nl/library/manuals/1000/007-1799-060/sgi_html/ch04.html).

Run the desktop regression with the uncompressed v6 kernel and the pinned
emulator from the ControlPanels baseline. Use a new output directory for
each release. The harness uses a disk copy and the SGI windows on Newport.

```sh
release=6.5.22f  # repeat with 6.5.30f
python3 lab/irix-hdsp/check.py --release "$release" \
  --bundle ".work/images/xiri-clean-indy-${release}-v6-20261126" \
  --emulator .work/emulators/iris-xiri-20261122/accelerated \
  --kernel ./netbsd --media ./indy-hdsp.iso --output "./hdsp-$release"
```
