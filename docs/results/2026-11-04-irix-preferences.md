# IRIX preference saving on NetBSD

Original GNOME Terminal, gedit and GIMP now save their settings and read them
back after a normal exit and relaunch as xiritest. GIMP also creates an exact
backup of the previous preferences file. The [application evidence](2026-11-04-irix-preferences.json)
records the files, ownership, six normal exits, screenshots and clean guest halt.
This report covers the preference guest; cumulative image acceptance is separate.

| Application | Change made through the original UI | Reopened result |
| --- | --- | --- |
| GNOME Terminal | Scrollback 100 → 257 lines | [257 in the Scrolling dialog](images/2026-11-04-gnome-preferences.png) |
| gedit | Tab width 8 → 3 | [3 in Preferences](images/2026-11-04-gedit-preferences.png) |
| GIMP 1.2.5 | Default new image 256×256 → 320×200 | [320×200 in Preferences](images/2026-11-04-gimp-preferences.png) |

GNOME Terminal also retains the changed bell and bold settings. The numeric
controls provide visible readback independent of the still unresolved GTK
checkbox rendering. The GNOME files have mode 0600; GIMP's `gimprc` and
`gimprc.old` have mode 0644. All belong to UID/GID 1234 under
`/usr/people/xiritest`. The prior GIMP file and its new backup both hash to
`9e5e83734a1a91397555a9fa6be9c92ffa498e199229644c6c018516126ff047`.
No diagnostic preferences are intended for the new manual image.

## Pathname compatibility

The original GNOME trace showed successful creation of a temporary settings
file followed by ENOSYS from IRIX `rename` (1114). The NetBSD module now
dispatches that call and copies both 32-bit pathname arguments before lookup.
It uses native emulation-root pathname handling and `do_sys_rename`, preserving
POSIX same-inode behavior. Measured IRIX differences are applied explicitly:
trailing slashes are removed except for root, and ENOTEMPTY becomes EEXIST.

NetBSD `xiri` commit `d35accbc0f8919a7b37debc17de117e0086e52bd` contains the
implementation. The [build ledger](../../lab/irix-pathops/build.json) records
module SHA-256 `cb20d5867e4adcd86536d4f65495a6f86b8a631e6dccf7f84aba610423062d85`.
The core kernel is unchanged. This is a module change, not a vendor-binary patch.

The [paired matrix](2026-11-04-irix-rename.json) compares 256 complete records
with original IRIX 6.5.22m: 32 cases, o32/n32, direct/indirect traps and
root/UID 1234. It checks return values and filesystem effects for ordinary
files, directories, symlinks, hard links, replacement, permissions, trailing
slashes, invalid pointers and malformed paths. All records match. Sixteen
additional controls cover emulation-root lookup, explicit native escape,
native fallback and a cross-namespace move. The [lab guide](../../lab/irix-pathops/README.md)
documents reproduction and fixture setup.

Early attempts are retained locally as failed diagnostics. The first runner
lacked its required empty input file; a subsequent candidate omitted the
dispatcher entry despite defining the handler and syscall table. Later
non-root records differed only in inherited directory GIDs. Preparing the
fixture parent's group as 1234 makes the intended identities comparable;
the final 256-record archive includes those corrected runs. These failures
are not counted as passes.

## Original resources and remaining work

GNOME Terminal's Preferences dialog also needed the original
`/usr/freeware/share/gnome-terminal` tree, including
`glade/gnome-terminal.glade`. The expanded [GNOME ledger](../../lab/irix-gnome/preferences-resources.json)
has 53 paths, adding three to the prior 50-path import. Original file bytes
are retained below `/emul/irix`; source-image user settings are excluded.

IRIX `fchmod` and `unlink` remain unimplemented. Their errors do not prevent
the observed successful saves, but other callers may need those interfaces.
Shared-memory fallback, gedit image/help/paper warnings, GTK checkbox drawing,
larger GIMP images and individual plug-ins remain separate follow-ups.
The rename fixtures do not qualify power-loss durability, concurrent directory
mutation or cross-filesystem moves.
