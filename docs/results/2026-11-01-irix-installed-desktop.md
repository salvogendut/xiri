# Installed-image desktop import

The installed image already contains the application's Icon Catalog
registration. We can copy installed applications and their resources into
the compatibility tree without waiting for original `inst` to work. This is
now the immediate desktop path; installer/package lifecycle work is deferred.

The read-only [inventory and import lab](../../lab/irix-installed-desktop/README.md)
finds **166 entries in 17 catalog pages**, including **21 Freeware entries**.
The original xmahjongg entry links to `//usr/freeware/bin/xmahjongg`. Its n32
executable is 252,672 bytes, SHA-256
`35253008a6d31ad6c4589c622146bcd0ae781488bc5d7872a4114b888e1edb59`.
Its static library/interpreter closure resolves, and its 33 game-data files,
two filetype icons, rule and application icon are available in the image.
The installed rule matches the `xmahjongg` executable name, selects its
open/closed artwork and defines the normal executable launch action. Copying
that rule and its compiled tables preserves the existing registration; no
installer hook needs to be rerun merely to reproduce those files.

The bundle includes the system catalog tree, installed/compiled filetype
rules and artwork, application defaults, color schemes and selected desktop
defaults. It preserves the directory and symlink layout beneath `/emul/irix`.
Native NetBSD accounts, home ownership, X server and session environment
remain authoritative. Native source inspection confirms that absolute links
followed by foreign processes restart at their emulation root, allowing
original catalog links to retain their text.

Of the catalog targets, 152 resolve to files and one to a directory. Thirteen
do not resolve as files in the source image, including names containing
arguments. The [manifest](../../lab/irix-installed-desktop/manifest.json)
records them explicitly; importing the catalog does not imply those entries
are usable. Delayed libraries, script commands and application data outside
the selected trees remain to investigate.

No old package-history database is imported, and this does not qualify
installation, upgrades or removal. System registration is distinct from
personal desktop preferences. Original root and `/usr/people` layout files
are inventoried privately; the test uses a fresh native user home.

The first ordinary-mode attempt, `ordinary-6q1wpc55`, successfully imported
the complete payload and verified every regular-file hash and original link.
It stopped before launching applications because the seed's old font
directory lived under `/tmp`, which NetBSD clears at boot. The guest halted
cleanly. The corrected harness recreates the already pinned 22 Screen fonts
and their native X font index each time. A second attempt reverified the
payload and passed font setup, but stopped at a missing empty input file
required by the native control runner. That harness omission is corrected.
Both attempts halted cleanly before foreign application launch. Resumed
runs verify the whole stopped disk and its clone by SHA-256 on the host,
retaining the seed's complete content verification. No additional source
image asset or kernel change was needed for this lab setup correction.

## Qualified import and first application rendering

The final `ordinary-w6lzsg5x` run passes payload provenance, native execution
and X controls, owned-descendant cleanup and clean halt. Its
[JSON record](2026-11-01-irix-installed-desktop.json) and
[PNG](images/2026-11-01-irix-installed-desktop.png) show original xmahjongg
rendering with its game artwork under 4Dwm. Icon Catalog overlays part of
the board in this initial combined capture. Game interaction and catalog
launch are not yet qualified.

The preceding launch `ordinary-o5u6xm80` found EACCES from SGI_ELFMAP for
libXt and libimdUtil: the image's shared-library mode 0644 lacked the execute
permission required by the current native VEXEC policy. The
[permission manifest](../../lab/irix-installed-desktop/permissions.json)
now sets imported ELF files, including libraries, to 0555. The unchanged
bytes then load and render. The earlier failing trace is retained; this is
a required import adjustment, not a kernel change.

Icon Catalog still renders **Blank**, despite the verified 166 system links
and copied filetype resources. Absence of application data no longer explains
that result. Its directory discovery/registration-consumption path needs a
focused trace and compatibility follow-up; the retained trace is clipped
to startup/tail sections and does not yet establish the exact cause.

The guest also installs persistent fonts, a manual desktop launcher, native
session/cleanup helpers, PTY setup and `/netbsd.boot`. A native test verifies
that the manual supervisor accepts a stop request and removes its child.
The user requested a reusable CHD and manual IRIS testing; the
[copy/placement guide](../IRIX-IMPORT.md) records 1,990 source-to-destination
entries and separates imported assets from native generated state.
