# Indy package device setup and Freeware artwork

This follow-up uses disposable copies of the clean v4 Indy desktops, the
NetBSD `xiri` kernel and module from `6e9a69e852f`, and matching original SGI
media. The [first installer trial](2026-11-24-indy-inst.md) established
that xmahjongg could be launched and removed on both releases.

## Who owns the devices?

SGI's supplied `inst(1M)` documents `-X /dev` for excluding the target's
device tree during installation and removal. The Foundation 1 inventory
contains four paths in that tree: `dev`, `dev/abi`, `dev/MAKEDEV.d`
and `dev/MAKEDEV`. In each release's first overlay, `dev/MAKEDEV` is the
only entry there. Its inventory entry owns both the permission-changing
pre-install command and the post-install invocation of `./MAKEDEV`.

| Original overlay input | 6.5.22f, R4400 | 6.5.30f, R5000 |
| --- | --- | --- |
| SGI product | `eoe_6522m` | `eoe_6530m` |
| First eight hex digits of MAKEDEV SHA256 | `a03c40e0` | `4abc9d9a` |
| SGI null and zero (major, minor) | (1, 2) and (37, 0) | (1, 2) and (37, 0) |

Both SGI recipes also call `/etc/devnm /` and contain direct `mknod`
commands. Overriding the `install` utility would leave those commands
active. The test gives the package root its own null and zero nodes using
the running NetBSD kernel's device numbers.

On each Indy, the original installer accepted the same ten subsystem
selections as the earlier trial with zero conflicts. With `-X /dev` it
reached exit commands and dependency checking without invoking MAKEDEV.
The target's device directory contained just null (20, 2) and zero
(20, 12). The inode and device numbers of both the target nodes and the
live NetBSD nodes matched their pre-install values. SGI's `versions`
listed the execution environment and xmahjongg in each target's history.

Installation history alone overstates what worked. Both transactions
reported failures in the catalog and filetype exit commands, the
Ethernet database conversion and mail configuration. Mail setup called
absolute IRIX utility paths, including `/bin/grep` and `/bin/awk`.
On 6.5.30f, the installer also logged failures creating time-zone links.
We isolated this on both releases with a two-line input to SGI's `zic`.

```text
Zone Xiri/Primary 0 - UTC
Link Xiri/Primary Xiri/Alias
```

Both compilers wrote the primary zone, left the alias absent and exited
1. Both traces recorded IRIX `link` (syscall 1009) returning `ENOSYS`.
This gives the next kernel-module fix a small test independent of `inst`.

The installer also exposed an interaction with native desktop startup.
The lab makes SGI's `/sbin/stat` available for installer scripts. When it
preceded `/usr/bin` in the boot service's PATH, the native PTY setup used
SGI syntax to interpret a NetBSD device query. The service returned 1
and xdm sent xiritest back to the greeter. The native setup script now
puts `/bin:/usr/bin` first. On each machine the updated script created
the readiness file with the SGI alias still present, the file monitor
was running, and xiritest reached 4Dwm through xdm. A final cold boot
on each CPU recreated the readiness file and started the file monitor.
The native and emulated null devices both reported (20, 2), and the
emulated PTY allocator reported (165, 2).

## Why the catalog exit command failed

The release's own `iconcatalogedit` ran on the desktop but exited 1 in
the newly installed package root. In the trace, its loader opened
`/usr/lib32/libgen.so` and received `EACCES` while mapping it.
Making just that file executable moved the failure to `libCsup.so`.
Of the six libraries in the helper's dependency chain, three needed
their modes changed from 0444 to 0555: `usr/lib32/libgen.so`,
`usr/lib32/libCsup.so` and `usr/lib32/libC.so.2`. The tests used the
package-installed contents on each release, including 6.5.30f's
`libgen.so`, which has a different digest from the desktop donor's copy.
With those modes the original helper printed usage and its original
add command created the expected Freeware symlink inside both targets.
This applies the same execution policy as the
[desktop importer](../IRIX-IMPORT.md) to three package-installed files.

## What the game supplies

CD 4 installs the original `xmahjongg.ftr` and its open and closed icon
drawings. The rule matches the basename `xmahjongg` and includes two
generic executable drawings from the parent filetype directory. Its
install hook calls the SGI filetype Makefile. That Makefile uses
`.IGNORE`, so even a zero exit status needs an independent check.
The [filetype probe](../../lab/irix-filetypes/fixture.c) uses SGI's own
library to look up a named rule and classify both an executable and a
catalog symlink by name and by open file descriptor.

On both release lines, the original compiler produced the same 3,868-byte
package table, SHA256
`06cc29d04e6f59b675100a1956084858ec3a897493aa7ed3981a25f29232b86a`.
We compiled from the package's own `usr/lib/filetype/install` directory
so its relative artwork includes resolved. We then merged this table
ahead of the existing release-specific `desktop.otr`. All four lookups
(game and catalog link, each by name and descriptor) changed from
`GenericExecutable` to `XMahjonggExecutable`. The independent xclock
control continued to return `XClock`. Both catalog links in this
classification check were test fixtures pointing to the actual installed
executable. The earlier installer recovery trial tested SGI registration.

## Original registration, second login and rollback

With the library modes corrected, SGI `inst` removed the game and then
reinstalled it from CD 4. On each release `versions` went from no game
rows to the installed subsystem. The original install hook recreated
the Freeware link and the installed executable matched the CD digest.
The package's own filetype hook still reported a missing
`/usr/sbin/fftr` in the alternate root, so the desktop used the table
compiled above.

We mounted the registered page read-only over the test page and logged
in again through xdm. In the original Icon Catalog, double-clicking the
tile opened a 1006×614 board as xiritest (uid 1234). Bringing the catalog
forward showed the open yellow tile. In the first login we also observed
the tile close again after the game exited, with the selection highlight
still visible. Restoring each desktop's saved table returned the game
and link to `GenericExecutable` and preserved the `XClock` control.

| Release and CPU | Registered Freeware entry | Catalog with the game running |
| --- | --- | --- |
| 6.5.22f, Indy R4400 | [Closed tile](2026-11-24-indy-6.5.22f-catalog-closed.png) | [Open tile and board](2026-11-24-indy-6.5.22f-catalog-open.png) |
| 6.5.30f, Indy R5000 | [Closed tile](2026-11-24-indy-6.5.30f-catalog-closed.png) | [Open tile and board](2026-11-24-indy-6.5.30f-catalog-open.png) |

The experiment used the emulator shipped in each v4 bundle. IRIS
`xiri` at `39ef6dff` contained the freshly checked upstream
`057ba095`. The shared module SHA256 was
`2664a87a32ec60d65756ca2af9517668806159a79c89c946665941888a0dc4d1`.
Both release-specific installer supplements built with the native utility
setup included, and the host suite passed all 94 tests. The
[release records](2026-11-24-indy-inst-followup.json) include the before
and after device observations, filetype digests, trace PCs and screenshots.
