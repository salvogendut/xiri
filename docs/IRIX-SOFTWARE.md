# Original IRIX software installation

The target is to use original IRIX `inst` and Software Manager (`swmgr`) on
NetBSD, preserving their dependency handling, installation history and package
hooks. Applications should appear in Icon Catalog through their own
registration mechanism. This is a userland capability supported by Xiri's
IRIX ABI; the desired kernel deployment remains a module modeled on
`compat_linux`.

The [shared-mapping checkpoint](results/2026-11-01-irix-mmap-shared.md) clears
the initial installer crash. The [bounded sproc adapter](results/2026-11-01-irix-sproc.md)
now supplies the measured child lifecycle, with 340 executions / 600 records
and 44 controls passing. The [new retry](results/2026-11-01-irix-installer-sproc.md)
creates the subcommand child, arms parent release and executes native `/bin/sh`.
The [F_DUPFD follow-up](results/2026-11-01-irix-dupfd.md) now fixes the two
pipe-writer duplications. The [time follow-up](results/2026-11-01-irix-installer-time.md)
now confirms successful time/gettimeofday calls, while the unchanged dry run
still reaches its watchdog. Distribution reading and installation remain
unqualified.

The helper shell searches IRIX-style directories for `ls` and `mkdir`, omitting
NetBSD's `/bin`. Next capture helper arguments/output and qualify an explicit
native bootstrap arrangement or the required original utilities, then follow
the parent's output/child-completion handling. The missing paths do not prove
the timeout's sole cause. Signal registration, system/hardware information,
umask and creat remain observed gaps. No package history or catalog entry is
created merely by resolving these ABI requirements.

Native/IRIX shared-home access passes again. Cold-boot home persistence remains
qualified by the [earlier probe](results/2026-11-01-irix-installer.md); graphical
login persistence remains open. The [original sproc reference](results/2026-11-01-irix-sproc-reference.md)
continues to define the measured exec/exit/unblock distinction. General share
groups and pthread creation are outside the new bounded adapter.

## First application: xmahjongg

The user selected **xmahjongg 3.6.1** from the supplied May 2004 freeware set.
Its distribution includes registration/removal hooks calling original
`iconcatalogedit` with `-syspage Freeware`, two `.fti` artwork files and a
`.ftr` type rule. Another hook rebuilds the file-type database using its
original Makefile. The [media inventory](results/2026-11-01-irix-freeware.md)
records the exact inputs; no software has been installed merely by reading
the inventories.

Acceptance is one complete lifecycle:

1. Original `inst` reads the selected distribution and resolves its actual
   prerequisites, including `fw_common` where required.
2. Install into the IRIX compatibility tree and retain accurate installation
   history. Do not import history claiming that unstaged software is installed.
3. Execute the package's original catalog and file-type registration hooks.
4. In an ordinary user's desktop, open the **Freeware** tab and launch
   xmahjongg from its entry; capture a PNG and check interaction.
5. Repeat after logout/login, then remove the package through the original
   installer and verify removal of its catalog entry. Qualify upgrades next.

The installed `inst(1M)` manual documents `-r` for an alternate installation
root, `-n` for dry runs and `-c` for command files. Even a dry run may write
configuration under the target's `var/inst`, so initial experiments use
disposable guests. The initial candidate is `-r /emul/irix`. Its path handling,
hook `chroot`, shell execution, helper programs and database operations all
need measurement before this is a supported installation command.

Original `inst`, `swmgr`, `SoftwareManager` and `iconcatalogedit` have been
inventoried with a complete static n32 library closure. GUI resources, delayed
loads, helper execution and installation behavior are separate checks. Start
with `inst` distribution reading, then qualify Software Manager's graphical
workflow. See the [installer lab](../lab/irix-installer/README.md).

## Native accounts with the IRIX home layout

Ordinary Xiri users use **`/usr/people/<username>`** as their native NetBSD
account home and session `HOME`. The inspected installation contains
`/usr/people`; its fresh shell templates are `/etc/stdcshrc`, `/etc/stdlogin`
and `/etc/stdprofile`. Their presence is inventoried, not a reason to copy an
existing account's personal configuration.

[setup-xiri-user.sh](../scripts/setup-xiri-user.sh) creates a native NetBSD
account with that home and native `/bin/ksh`, copies NetBSD's account skeleton
through `useradd`, and makes the new home private to its owner. Repeating it
preserves the account and files. It refuses to adopt an existing directory or
silently move an account with a different home. Password/login policy stays
with native NetBSD administration.

```sh
# Inside the NetBSD target, as its administrator:
sh scripts/setup-xiri-user.sh alice
```

Native and IRIX applications must see the same home. Do not create a second
home under `/emul/irix/usr/people`. IRIX clients should generate their own
`.desktop-<hostname>` and `.desktophost/<hostname>` state beneath the native
home; these must persist across sessions and retain native user ownership.
Do not invent a modern Desktop/Documents layout or copy old machine-specific
desktop state. The earlier `/tmp/xiri-home` labs remain pinned reproductions;
new persistent-session tests use `/usr/people`.

IRIX **root is the exception: its home is `/`**, not `/usr/people/root` or
`/root`. Original installer tests therefore use `HOME=/`. This is the foreign
root-session environment; the account helper only creates ordinary users and
does not migrate NetBSD's administrative account.
