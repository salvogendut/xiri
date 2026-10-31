# Original Toolchest resources and menu input

The [run record](../../docs/results/2026-10-31-irix-toolchest-input.md) passes seven staged observations and 73 captured frames, including combined resources as root and uid 1234 in CI and ordinary execution.

This experiment extends the [SIOCNREAD display/redraw checkpoint](../irix-siocnread/README.md)
without changing the kernel, emulator, vendor executable, libraries or app-defaults.
It separates missing X key names from the two SGI color names, then measures
mouse posting, arrow-key traversal and dismissal on a private guest Xvfb.

## Inputs and reproduction

Extract the original resources using the host's libguestfs installation:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 scripts/extract-irix-toolchest-resources.py
```

The supplied IRIX image is mounted read-only with `ro,norecovery`. Original
resource bytes remain under ignored `.work/irix-toolchest-input/root`; only
paths, sizes, checksums and the two numeric color values are committed in
[resources.json](resources.json). The extraction closes its guestfish daemon.
The harness verifies those hashes before copying any resource into a guest.

Run from the host, where `genisoimage` is available. The harness starts IRIS
inside the existing `xiri-iris` toolbox:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 scripts/probe-irix-toolchest-input.py \
  --seed-directory .work/irix-siocnread/runs/lp64-ci-d2asxkow
PYTHONDONTWRITEBYTECODE=1 python3 scripts/probe-irix-toolchest-input.py \
  --seed-directory .work/irix-siocnread/runs/lp64-ci-d2asxkow \
  --mode ordinary --combined-only
```

The CI experiment compares the existing resources, original `XKeysymDB` alone,
numeric colors alone, and both together as uid 1234. The combined setup also
runs as root. Ordinary execution repeats the combined setup as both identities.
Each disposable disk inherits checked binaries/resources from a stopped,
qualified SIOCNREAD seed and installs the verified NetBSD X development set.
All guests must be stopped afterward; the global limit is four IRIS instances.

`XKeysymDB` is installed mode 0444 at
`/emul/irix/usr/lib/X11/XKeysymDB`, so both tested identities can read it. The explicit Xt
resources are `*background: #c1c1c1` and `*decalForeground: #555555`, supplied
with `-xrm`. These numbers come from the supplied IRIX RGB table. They do not
add SGI color-name support to X.org or establish a complete original SGI theme.
The guest's XLookupColor control records what its server actually accepts.

## Evidence and boundaries

[inputcheck.c](inputcheck.c) uses the [XTEST extension](https://www.x.org/releases/X11R7.7/doc/libXtst/xtestlib.pdf)
to send mouse and key events only to `127.0.0.1:98` inside the disposable guest.
An independent native X client checks button press/release coordinates, key
press/release and `send_event=0` before and after the vendor workload. A separate
native Expose control verifies redraw. The observer records window trees and
unmodified root XWD frames at each input phase. Frames are captured in the
guest during the input sequence and downloaded after the bounded client exits,
so serial-transfer time does not consume its interaction window. Vendor output and syscall traces
stay private under `.work`.

The manual's [menu chapter](https://techpubs.jurassic.nl/library/manuals/2000/007-2167-006/sgi_html/ch08.html)
provides the posted-menu, arrow-navigation and Escape expectations. This
experiment does not select an application-launching menu item. It does not
qualify a window manager, spring-loaded dragging, timers, focus policy, full
keyboard accessibility or a complete desktop session. XTEST exercises delivery
through X.org; it does not repeat the separate physical/emulated input-device
qualification. Parent timeouts are intentional client termination.

## Recheck saved evidence

```sh
PYTHONDONTWRITEBYTECODE=1 python3 scripts/qualify-irix-toolchest-input.py \
  .work/irix-toolchest-input/runs/ci-se8hqxqq \
  .work/irix-toolchest-input/runs/ordinary-tivoyei2 \
  --output docs/results/2026-10-31-irix-toolchest-input.json
```
