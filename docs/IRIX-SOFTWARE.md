# IRIX application import and installation

The current reusable baseline and manual IRIS procedure are in
[XIRI-IMAGE.md](XIRI-IMAGE.md). [IRIX-IMPORT.md](IRIX-IMPORT.md) records exact
source/destination mappings, permission adjustments and the SGI catalog
reference check. Historical installer observations below retain their
original scope; the installed-image payload is now a separate working path.

The immediate path is to copy already installed applications, their resources
and existing Icon Catalog registration from the user's IRIX image. The
[installed-image inventory](results/2026-11-01-irix-installed-desktop.md) finds
166 entries in 17 tabs, including xmahjongg in Freeware. Import the catalog
links, filetype rules/icons, application defaults and required libraries
together with each application. Qualify direct execution, catalog launch,
interaction and persistence before calling an application supported.

The [Icon Catalog checklist](ICON-CATALOG.md) tracks each imported system
entry by tab, with startup observations, errors and later interaction/exit
checks. The survey uses the qualified GIMP CHD in disposable guests and
records processes that remain alive without producing a window.

The [GNOME startup follow-up](results/2026-11-04-irix-gnome.md) repairs the
measured Unix-socket loop in gedit's ORBit library and imports the original
VFS/editor resources. Gedit now passes basic text creation, save/reopen,
overwrite, catalog launch and GUI-exit checks as xiritest. Help and image
loading remain incomplete. The later [preference cycle](results/2026-11-04-irix-preferences.md)
qualifies settings persistence in gedit, GNOME Terminal and GIMP. The checklist keeps these candidate
module results separate from the earlier manual-image survey.

Several launchers need more than their executable and static library closure.
AbiWord calls missing `AbiWord_d`/`AbiWord_s` programs; Mozilla and gFTP
report absent runtime programs. Emacs needs its Lisp/data directories,
while Dia, LyX and xpat2 report missing application data. Preserve complete
package layouts and record the additional source/destination paths before
testing again. No additional vendor resources were imported by the survey.
The subsequent [Acrobat cycle](results/2026-11-04-irix-acrobat.md) imports its
complete Reader installation and adds support for its legacy ELF layout.
Catalog launch, PDF display, page/zoom changes, reopen and normal exit pass;
the catalog icon stays unchanged while Reader runs. The exact copy paths
are recorded in the [Acrobat resource ledger](../lab/irix-acrobat/resources.json).

Window creation remains a separate check from useful operation. Freeware's
NEdit launches through the catalog, accepts visible text, changes its icon
and closes through Quit/Discard, but Save reports that it cannot create the
file. A native write in the home's `.xiri-catalog/` subdirectory succeeds;
a control in the exact destination directory remains pending. This is a
partial application result, with the file-creation failure still to diagnose.

The [desktop service repair](results/2026-11-02-desktop-services.md) now shows
the existing Freeware page and all 21 entry names. Native FAM supplies the
directory notifications; no new package registration was fabricated. The
[icon repair](results/2026-11-02-desktop-icons.md) also restores the imported
application-specific artwork. The [original-shell checkpoint](results/2026-11-02-irix-vendor-shell.md)
clears the static n32 `/bin/sh` rejection and demonstrates two double-click
launches of xmahjongg from its existing Freeware entry. The later
[desktop behavior cycle](results/2026-11-02-desktop-behavior-image.md) qualifies
its opened-state feedback; broader application behavior remains unqualified. The
[application follow-up](results/2026-11-02-irix-elfmap-high.md)
records the earlier boundary, the high-address mapping fix for GIMP, its subsequent
signal registration failure, and xosview's unsupported statistics queries.
No further library copying was needed for GIMP's observed loader failure.
The [winterm cycle](results/2026-11-03-winterm-reliability.md) now adds SIGCHLD
NOCLDSTOP registration, terminal resize and normal shell exit. The subsequent
[GIMP checkpoint](results/2026-11-03-irix-gimp.md) fixes registration of full
signal masks and adds the original application data, plug-ins and canonical
`/sbin/sh`. Basic paintbrush editing, XCF/PNG save and reopen, normal exit and
launch from the existing Freeware entry now work as xiritest. Preference
backups now pass the later rename checks; shared-memory transport uses a working
fallback, and the wider plug-in collection remains unqualified. The new
CHD includes the resources and replacement module, with separate
[fresh GIMP](results/2026-11-03-irix-gimp-cold.json) and
[desktop-login](results/2026-11-03-irix-gimp-image.json) checks.
The earlier [shell image](results/2026-11-02-irix-shell-image.md) packages
the original-shell and high-address mapping fixes and verifies xmahjongg's
existing catalog action after a direct CHD boot.

Original IRIX `inst` and Software Manager (`swmgr`) remain the later target
for adding, upgrading and removing software with correct dependency handling,
installation history and package hooks. This work is deferred while we
establish the imported desktop. Copying installed files does not qualify a
package installation or justify copying the old installation database.
Both paths use Xiri's IRIX ABI; the desired kernel deployment remains a
module modeled on `compat_linux`.

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

The [helper follow-up](results/2026-11-01-irix-installer-helpers.md) captures
the compiled-in target-directory bootstrap. It replaces PATH with IRIX-style
directories that omit `/bin`. Four explicit native utility aliases
(`ls`, `mkdir`, `mv`, `ln`) let this bootstrap exit zero in CI and ordinary
guests, while the unchanged installer still waits and leaves the child a
zombie. SIGCHLD registration returns ENOSYS; the supplied library's completion
callback would use `waitsys(P_ALL, 0, ..., 0x43, 0)`, another unimplemented
mode. The [signal reference](results/2026-11-01-irix-signal-reference.md) now
executes that call successfully inside independent original-IRIX handlers,
including confirmation that the child is reaped. Its 480 executions also
measure registration, o32/n32 frames, signal return and FPU restoration.
The [native signal checkpoint](results/2026-11-01-irix-signal.md) now passes
1,216 records and 76 controls, including the measured handler/reap path,
FPU restoration, fork inheritance and invalid-context checks. The installer
itself has not yet executed this callback on NetBSD.

The aliases are a disposable lab arrangement, not general IRIX command
compatibility. Native `stat -qd` fails and the original script falls back to
zero, so filesystem-device comparison remains unqualified. The measured
signal and wait-any subset is now qualified. When installer work resumes,
retry it and resolve the utility mismatch before claiming support. Hardware
information, umask and creat also remain gaps. No package history or catalog
entry has been created.

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

The first import acceptance is to launch the installed executable with its
original game data, show its existing Freeware entry, launch it through Icon
Catalog and verify interaction and a later login. The complete installer
lifecycle remains a separate acceptance sequence:

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

## Selecting the IRIX desktop for a user

These instructions run inside NetBSD with Xiri already installed and its
boot services enabled, as in the prepared development image. Any ordinary
native account can select the desktop; the username does not have to be
`xiritest`. For system installation requirements, see the
[runtime guide](../runtime/README.md#existing-prerequisites).

As the desktop user, save any existing `~/.xsession`, then run:

```sh
cp /usr/local/share/xiri/xdm.xsession "$HOME/.xsession"
chmod 700 "$HOME/.xsession"
```

Log out and log back in through xdm with that account's native password.
The startup chain is:

```text
xdm -> ~/.xsession -> /usr/local/bin/xiri-session -> 4Dwm and desktop clients
```

Native xdm authenticates the user and supplies HOME, groups, DISPLAY and X
authority. The [session template](../runtime/etc/xdm.xsession) adjusts the
local display address for IRIX clients and invokes
[xiri-session](../runtime/bin/xiri-session). That script starts and supervises
the desktop under the logged-in user's identity, using xdm's existing X
server. FAM and the other system services are shared across user sessions.

The desktop starts in the user's own HOME. An existing home such as
`/home/alice` works; `/usr/people/alice` is our preferred IRIX-style convention.
Desktop links, Dumpster, preferences and session logs live beneath that home.
Startup errors are in `~/.xsession-errors`; session logs are in
`~/.xiri/sessions/`.

After creating an account or changing group membership, run this as root:

```sh
/usr/local/sbin/xiri-sync-users
```

This refreshes IRIX's password-free account/group lookup tables from native
NetBSD accounts. It also runs automatically at boot. Log in again after group
changes so the session and its FAM connections acquire the updated groups.

`/etc/xiri/session.conf` supplies shared locale, timezone and font settings.
Its `xiri_user` setting selects the account for the root-run `xiri-desktop`
convenience launcher only. Leave it alone when enabling normal xdm users;
their sessions use the account that logged in.

To return to a previous desktop, restore that user's saved `.xsession`.
With no custom `.xsession`, the prepared image selects standard NetBSD ctwm.

## Desktop preferences

Each user changes their desktop through **Desktop → Customize** in Toolchest:
**Background**, **Color Schemes**, and **Windows**. The same programs are in
Icon Catalog's **ControlPanels** page. From winterm, their imported paths are
`/emul/irix/usr/sbin/background`, `/emul/irix/usr/sbin/colorscheme`, and
`/emul/irix/usr/sbin/windows`.

The original panels save preferences in the current user's home. Xiri loads
`~/.Xresources`, then `~/.Sgiresources`, and searches for application settings
under `~/.desktop-<hostname>/`, `~/`, and
`~/.desktop-<hostname>/0.0/`. A backdrop can be stored in that directory's
`4DWm` file or as `4DWm*…` resources in `.Sgiresources`; preserve both when
backing up a profile. No root-owned copy of a user's preferences is needed.
Existing files take precedence over the desktop's initial appearance.

Reef and Sand patterns and Solid colours are qualified. For a solid colour,
select **Solid**, click its small colour square below the preview, choose a
colour in **Backgrounds: Color Browser**, press **OK**, then **Apply** in the
Background panel. Log out and back in to check the restored desktop colour.
The captured reopened chooser starts from the template blue, even though the
desktop retains its custom colour; check its preview before applying again.
That initialization still needs comparison with original IRIX.
The original picker uses its ordinary X11 controls under Xiri; its GL mode
crashes the bundled software renderer. This setting affects Background only.
The [colour result](results/2026-11-06-desktop-colours.md) records the tests.

Xiri generates a private `Xcms.txt` in each session's log directory from the
SGI entries in `/emul/irix/usr/lib/X11/rgb.txt`, then exports `XCMSDB` to clients.
This resolves names such as `sgiLightBlue` without replacing Xorg's standard
colour table. An explicitly supplied `XCMSDB` takes precedence. The database
is derived state; keep the original RGB resource, not a previous session's
`Xcms.txt`, when moving an installation.

If Window Settings asks to restart the window manager, choosing **Cancel**
keeps the saved choice for the next login. Log out normally and log back in
to apply it. Saved application windows are controlled separately through
**Save Windows & Desks**, described below.

Xmahjongg is available from **Freeware** or winterm; it is no longer part of
the default desktop startup. A saved session can include it.

## Saved desktop sessions

Open **Toolchest → Desktop → Customize → Windows**. Under **Save Windows &
Desks**, choose:

- **Continuously** to restore the running application windows from the last
  normal logout or orderly shutdown. Closing an application removes it from
  the next saved session.
- **Explicitly**, then **Set Home Session**, to keep a chosen starting desktop.
  Later changes do not replace that application list until you save again.

Log out through Toolchest or the desktop menu. Xiri waits for 4Dwm to finish
its save before terminating the session. With the `xiri_sessions` service
enabled, NetBSD `shutdown -r now` (reboot) and `shutdown -h now` (halt) also
save an active desktop before xdm closes X; `shutdown -p now` uses the same
shutdown hooks. Use these commands from an administrative terminal. Direct
`reboot`, `halt` and `poweroff` bypass NetBSD's rc shutdown hooks. Emulator
termination and power loss cannot save the current windows. Older images
without `xiri_sessions` still require logging out first.
Applications must publish a usable X11 restart command; support for one application does not establish support
for every catalog entry. Winterm restores fresh native shells in the user's
home. Save documents and finish shell jobs separately.

The current xdm display stores `4Dwmsession`, `4Dwmdesks` and `4Dwmdeskname` in
`~/.desktop-127.0.0.1/0.0/`. These files belong to the native desktop user, so
`xiritest` and `xiritest2` have independent saved sessions. A different display
host/number selects a different directory. Keep these files with the existing
`.Sgiresources` and `.desktop-<hostname>` preferences when backing up a profile.

Toolchest and the desktop file manager always start. The default winterm,
xclock and Icon Catalog are seeded only when no managed session has been
saved. A closed Catalog or terminal therefore stays closed on the next
continuous-mode login; use Toolchest to open it again. Xmahjongg can return if
you deliberately leave it in a saved session, but is not a default startup app.

To reset the saved windows, log out first and rename `4Dwmsession` in the above
directory from another login. Keep the old file as a backup. To also reset
the layout and desks, back up and rename `4Dwmdesks` and `4Dwmdeskname`.
The next login seeds the normal default windows. Do not edit these files while
4Dwm is running, since it may write them again.

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
useradd -m -d /usr/people/alice -s /bin/ksh alice
chmod 700 /usr/people/alice
passwd alice
/usr/local/sbin/xiri-sync-users
```

These native commands are available in the manual image. When the repository
helper is present in the guest, `sh scripts/setup-xiri-user.sh alice` can replace
the first two commands and adds the existing-account checks described above.

After creating the account, follow the
[per-user desktop setup](#selecting-the-irix-desktop-for-a-user) above as that
user. Each account selects its own `.xsession`; accounts without one retain
the native NetBSD desktop.

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
