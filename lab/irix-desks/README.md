# 4Dwm windows and desks

`resources.json` records the original IRIX 6.5.22m `/usr/sbin/ov` binary,
installed at `/emul/irix/usr/sbin/ov`. The original image is read through
guestfish with `--ro` and XFS `ro,norecovery`; vendor bytes remain in `.work`.
The existing Overview application defaults, schemes and libraries are
prerequisites. No user profile is copied from the source disk.

Reproduce the resource package with:

```sh
python3 scripts/stage-irix-desks.py
```

Pass `--desks-resources .work/irix-desks-resources` to
`prepare-xiri-xdm-image.py` when preparing a replacement image. Its installed
hash, ownership and mode are verified independently of graphical behavior.

`windows.c` observes managed clients, frames, icons, stacking and focus
without changing them. Its other modes inject XTest pointer/key events without
implicitly raising or focusing a window. This avoids using a setup helper's
forced focus as evidence that keyboard navigation works.

The maintained cold-image check is:

```sh
python3 scripts/probe-xiri-desks.py --bundle <prepared-bundle>
```

It uses a disposable CHD copy, authenticates through native xdm, exercises
original window controls and the Toolchest Overview entry, creates desks and
moves a clock between them, checks separate users, and verifies the active
desk and geometries after login and orderly reboot. `--local-processes` is
only for the documented direct Distrobox adapter, whose processes share the
host namespace. The normal harness owns and terminates its own guests.

The [user guide](../../docs/IRIX-WINDOWS.md) describes controls and limits.
An ordinary launch or visible window alone is not a functional pass.
