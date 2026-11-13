# Local file drops into running applications

The original File Manager's Motif source advertises `_SGI_ICON`, but the
imported GTK applications require URI lists. `runtime/libexec/drop-bridge.c`
is a native, per-user X client which translates that boundary. It does not
modify imported application binaries or add kernel code.

`sgi-icons.json` retains the measured NUL-separated payload from the original
IRIX 6.5.22m File Manager running on NetBSD. The four records include spaces,
doubled quotes and literal backslashes. This is measured vendor-client
output, not a claim that the full reference-IRIX drag UI was qualified.

Run the bounded parser checks with the repository's host tests:

```sh
python3 -m unittest discover -s tests
```

The separate wire-level fixture acts as a Motif source and XDND receiver on
an owned, authenticated Xvfb server:

```sh
python3 scripts/probe-xiri-drag-protocol.py
```

It checks both byte orders, XDND versions 3 and 5, receivers without Motif
properties, exact URI bytes for multiple special filenames, cancel/help,
refusal, a destroyed target, unchanged non-SGI Motif forwarding, drop-only
entry, duplicate-helper exclusion and property restoration on shutdown.
No wire fixture alone establishes an application's document handling.

For a prepared image containing the new runtime:

```sh
python3 scripts/probe-xiri-drag-drop.py --bundle /path/to/bundle
```

The cold probe uses actual File Manager gestures, the original gedit and
GIMP, and the two public test accounts. It checks gedit's corrected icon
action, exact text after a running-window drop, cancellation, unchanged
sources, a PNG in GIMP, the helper's ownership and logout cleanup, and its
absence in the native ctwm session. PNGs, hashes and logs go into
`.work/drag-drop/qualified-*`. The existing document probe remains the
regression for native xedit icon drops and saved editor preferences.

For the documented direct Distrobox environment add `--local-processes`.
This scopes cleanup to the guest's recorded process group. Always preserve
the selected qualified CHD until the replacement passes the image gate.

See the [user guide](../../docs/IRIX-DOCUMENTS.md) for configuration and
explicit limits. The runtime does not fetch remote files, infer shell
commands from filenames or perform file moves.
