# Winterm startup, font and PTY controls

See the [cycle record](../../docs/results/2026-11-03-winterm-reliability.md)
the [paired ABI qualification](../../docs/results/2026-11-03-winterm-abi.json)
and [font diagnostic record](../../docs/results/2026-11-03-winterm-fonts.json).
The module sources match NetBSD `xiri` commit `4f3d8a183ea`, as checked by
[source-equivalence.json](source-equivalence.json). [build.json](build.json)
retains the actual build provenance; [image-baseline.json](image-baseline.json)
keeps the unchanged `9390bc04900` core kernel paired with the new module.

`winsize.c`, `child-stop.c` and `shell-events.c` are original observations
compiled n32 with the supplied IRIX installation's GCC and headers. They
exercise master/slave size sharing, descriptor/pointer errors, libc signal
registration, child stop/continue/exit notifications and PTY EOF. Run as root,
or pass `user` to the first/third fixture; the stop fixture takes
`suppress|report root|user`. The files named `regular` must exist and be
readable by UID 1234. No vendor source is used.

`winsize-raw.c` and the established independent signal fixtures cover o32 and
n32, direct and indirect dispatch, root and UID 1234. Build with:

```sh
python3 scripts/build-irix-winterm-fixtures.py
```

The output manifest in `.work/irix-winterm-reliability/probes` pins every
source and executable. Use the same executables on original IRIX and NetBSD.
On IRIX, pass `0` or `1` for root/UID 1234. On NetBSD, use a native launcher
to set credentials before exec and pass no identity argument: the IRIX-side
setup calls capability setters that are intentionally unsupported by Xiri.
For the unprivileged case, root can run `su -m xiritest -c ./EXECUTABLE` from
the fixture directory. Apply the same native-launch rule to libc controls
instead of asking them to drop credentials through foreign setters.
The raw fixtures emit binary records to stdout; stderr must be empty and
exit status zero. Retain outputs as
`EXECUTABLE-IDENTITY.bin` and `.err`, then compare:

```sh
python3 scripts/qualify-irix-winterm-fixtures.py \
  --reference PATH_TO_IRIX_RECORDS --native PATH_TO_NETBSD_RECORDS \
  --output PATH_TO_REPORT.json
```

The 248 window-size observations must match byte for byte. The 24 child
fixtures explicitly check NOCLDSTOP and reuse the independent full signal
frame validator. The interrupt-safe `trampoline-v2.S` is required; the older
trampoline uses kernel-reserved registers and is excluded from qualification.

`font-metrics.c` compares native and original Xlib against the same X server.
It reports font-set extents, text width and underlying core-font metrics over
six create/free cycles. Its default pattern matches the imported XWsh
app-defaults; an optional argument selects another font.

`resize-watch.c` is a native foreground-job witness. It verifies controlling
terminal ownership, records the initial dimensions, waits for SIGWINCH and
records the new dimensions. The enhanced graphical check uses it before
performing its usual desktop arrangement:

```sh
python3 scripts/probe-xiri-xdm.py --bundle PATH_TO_BUNDLE --winterm
```

That check records untouched startup geometry/PNG, rejects collapsed font
increments, checks a resize to 66×21, starts another terminal at 100×30 and
requires typing `exit` to remove its process and window. Three xdm login
cycles also run the established desktop, logout and native ctwm controls.
The [fresh-image qualification](../../docs/results/2026-11-03-winterm-image.json)
records the complete cold-boot run, with
[untouched winterm PNG](../../docs/results/images/2026-11-03-winterm-image-winterm.png).
All imported binaries, toolchains, images and raw records remain in `.work/`.

The n32 libc stop/continue experiment was not part of this checkpoint's NetBSD acceptance:
`usleep()` reaches unsupported IRIX `nanosleep`, and native SA_NOCLDSTOP
still differs from the reference on continued-child notifications. The
current fixture fails and reaps its child when the delay is unsupported.
Its original-system observations used the archived pre-guard source. The
qualified raw signal controls cover child exit handling, not full stop/continue
parity. The later [child-state cycle](../irix-job-control/README.md) implements
and measures IRIX `nanosleep`, including the vendor libc wrappers, and adds
stop/resume wait events and continued-child notification policy.
The font collapse later reproduced in both native and original Xlib
on Xorg's scalable IBM Courier face. SGI Screen stayed at 8×15 in that failing
session; the later appearance cycle selected NetBSD bitmap Courier at 11×20.
The [Type1 follow-up](../../docs/results/2026-11-05-type1-scaler.md) now fixes
native MIPS signal-return FPU state loss. Explicit scalable Courier then
passes 12×21 metrics, input, foreground resize and normal exit; the desktop
keeps its bitmap default for its closer IRIX appearance.
