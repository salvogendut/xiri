# Imported IRIX files and reusable NetBSD image

The prepared image contains NetBSD, the matching Xiri kernel and boot-loaded
compatibility module, and the IRIX runtime/application payload. It is a development baseline for cloning and
manual IRIS testing. Routine runs should reuse it; importing from the IRIX
source disk is a bootstrap or deliberate payload-update operation.

The working source release is **IRIX 6.5.22** (the installed baseline reports
**6.5.22m**), confirmed by the user on 2026-11-02. Keep these payload and
behavior records tied to that release. Later versions may differ in their
libraries, resources, ABI use or desktop behavior; record those differences
against a separately identified image instead of replacing this baseline.

The exact [copy ledger](../lab/irix-installed-desktop/copy-ledger.json) has
1,990 source-to-destination records. It includes regular-file hashes,
symlink targets, directories, source provenance and installed permission
policy. The [catalog manifest](../lab/irix-installed-desktop/manifest.json)
lists all 166 entries in 17 pages, including 21 Freeware entries. The source
image is read-only; all vendor bytes and generated disk images stay in `.work`.

## Placement

Multi-user desktop support imports no additional IRIX files. Native account
administration creates each owned home; the user selects the existing xdm
session template. `xiri-sync-users` generates `/emul/irix/etc/passwd` and
`/emul/irix/etc/group` from native NSS, replacing password fields with `*` and
retaining original lookup tables once as `*.before-xiri-users`. Native login
databases remain unchanged. IRIX root's lookup home stays `/`; other users
retain their native HOME, including `/usr/people/<name>`. Boot refreshes the
lookup tables; refresh explicitly after account/group changes. These generated
tables and per-user Desktop/Dumpster/session files are not vendor imports.

The [xdm image cycle](results/2026-11-03-xiri-xdm-image.md) needs no new IRIX
files. Its additions are native: `runtime/` installs rc.d services, helpers,
configuration and an xdm session example; image preparation selects that
example as `/usr/people/xiritest/.xsession`. `/home/netbsdtest` is a separate
native ctwm account. Native xdm supplies credentials and per-login X authority;
IRIX root's home, saved sessions and vendor login-manager files are not copied.
The [wheel update](results/2026-11-03-xiri-wheel.md) adds `netbsdtest` to the
native `/etc/group` wheel entry for `su -`; it requires no vendor resources.
Service logs are `/var/log/xiri-fam.log` and `/var/log/xdm.log`; user logs are
`$HOME/.xsession-errors` and `$HOME/.xiri/sessions/`. These are generated native
state, separate from the imported-file ledger below.

The [desktop behavior cycle](results/2026-11-02-irix-desktop-behavior.md) adds
one resource beyond the published shell image: the original
`/usr/include/X11/bitmaps/granite`, installed at
`/emul/irix/usr/include/X11/bitmaps/granite` with mode 0444. Its
[supplementary ledger](../lab/irix-desktop-behavior/resources.json) owns the
checksum and provenance. The session creates a new user's `Desktop` links
to `/`, HOME and `../dumpster`, plus `dumpster/.dumpster`; these are native
user state, not copied IRIX root-home files. Existing Desktop content is
preserved. The existing 1,990-record ledger and older shell CHD remain intact;
the [behavior CHD](results/2026-11-02-desktop-behavior-image.md) includes the
supplementary ledger and resource.

The [original-shell checkpoint](results/2026-11-02-irix-vendor-shell.md)
uses the already imported `/emul/irix/bin/sh` bytes (source `/bin/sh` resolves
to `/sbin/sh`). No additional shell import is needed. Native setup now
creates `/emul/irix/dev/null` using the native device's major/minor and mode
0666; this is generated NetBSD state, not an IRIX device copy. The
[shell image](results/2026-11-02-irix-shell-image.md) includes this setup and
the new kernel. Its vendor copy ledger and imported bytes are unchanged.

`/usr/lib/desktop/launcheffect` and `waitmap` have been located and extracted
privately as launch-feedback candidates. Their [separate inventory](../lab/irix-vendor-shell/launch-helpers.json)
records exact hashes and intended `/emul/irix` destinations. They are not
part of the installed payload or the successful catalog-launch demonstration.

| Original IRIX source | NetBSD destination | Purpose |
| --- | --- | --- |
| `/lib/rld`, `/lib32/rld`, libc and resolved `/usr/lib{,32}` libraries | Same path beneath `/emul/irix` | Original dynamic loaders and o32/n32 runtimes |
| `/usr/bin/X11/4Dwm`, `toolchest`, `xclock`; `/usr/sbin/xwsh`, `winterm`, `iconcatalog`, `fm`, `bgicons`; resolved catalog launch targets | Same path beneath `/emul/irix` | Original desktop and applications; presence does not certify every program |
| `/usr/lib/desktop/iconcatalog` | `/emul/irix/usr/lib/desktop/iconcatalog` | System pages and original launcher links |
| `/usr/lib/filetype` | `/emul/irix/usr/lib/filetype` | Installed rules, compiled tables, iconlib and actions |
| `/usr/include/X11/bitmaps/sgidesktop` | Same path beneath `/emul/irix` | FileManager toolbar resources; the separate [bitmap ledger](../lab/irix-desktop-bitmaps/copy-ledger.json) preserves 48 files, six aliases and their directory |
| `/usr/lib/X11/app-defaults`, `/usr/lib/X11/schemes` | Same path beneath `/emul/irix` | Application resources and color schemes |
| Selected `/usr/lib/X11/system.*` and XDM default icon/device lists | Same path beneath `/emul/irix` | Window-manager and desktop defaults; exact selection is in the ledger |
| `/usr/lib/X11/XKeysymDB`, `rgb.txt` and selected C/ISO8859-1 locale files | Same path beneath `/emul/irix` | Key names, source color data and locale lookup |
| 22 `/usr/lib/X11/fonts/misc/Scr*.pcf[.Z]` files | `/usr/local/share/xiri/fonts/` | Native X font directory; run native `mkfontdir` and add it with `xset +fp` |
| `/usr/freeware/bin/xmahjongg` | `/emul/irix/usr/freeware/bin/xmahjongg` | Installed n32 game executable, version string 3.6.1 |
| `/usr/freeware/share/xmahjongg` | `/emul/irix/usr/freeware/share/xmahjongg` | Its 33 game-data files |
| xmahjongg's catalog link, installed `.ftr`, two `.fti` icons and `/usr/lib/images/XMahjongg.icon` | Corresponding paths beneath `/emul/irix` | Existing Freeware integration, copied with the program |

The current copied payload contains 1,951 unique paths and 238,745,814
regular-file bytes, in addition to earlier runtime resources and native font
copies. The ledger describes the combined baseline, not just this new tar.
Original absolute catalog links are retained: foreign pathname lookup
resolves them through the emulation root. Host extraction records these
links as metadata and never follows them into the host filesystem.

Saved application sessions additionally need the unchanged original
`/usr/bin/X11/tellwm` at `/emul/irix/usr/bin/X11/tellwm` (22,848 bytes;
[resource ledger](../lab/irix-session/resources.json)). Stage it with
`scripts/stage-irix-session.py`, then pass
`--session-resources .work/irix-session-resources` to image preparation.
Its `libX11.so.1` and `libc.so.1` dependencies are already imported.

Empty Dumpster additionally needs the unchanged original
`/usr/lib/desktop/telldesktop` at
`/emul/irix/usr/lib/desktop/telldesktop` (14,252 bytes, mode 0555, root:wheel;
[resource ledger](../lab/irix-filemanager/resources.json)). Its n32 library
dependencies are already present. Stage it with
`scripts/stage-irix-filemanager.py`, then pass
`--filemanager-resources .work/irix-filemanager-resources` to image preparation.
The existing `/usr/lib/desktop` alias exposes it to native shells. The
[File Manager guide](IRIX-FILEMANAGER.md) also documents the native hostname
entry needed for local file operations; that configuration is not an import.

## Permissions and generated state

The [module-image preparation](../lab/irix-module/README.md#prepare-a-manual-image)
adds no vendor resources. Its native files are a matching `/netbsd`,
PROM-compatible `/netbsd.boot`, and
`/stand/sgimips/11.99.9/modules/compat_irix_o32/compat_irix_o32.kmod` (mode 0444).
The installer derives that module directory from `kern.module.path`, adds
`compat_irix_o32` to `/etc/modules.conf`, and enables `modules=YES` in
`/etc/rc.conf`. Preparation and CHD qualification record and verify their
hashes. The module belongs to the same NetBSD build as the kernel, rather
than the IRIX copy ledger. Normal boot retains securelevel 1.

The first launch exposed an essential permission difference. Some original
shared libraries are mode 0644, while the current SGI_ELFMAP implementation
uses native `VEXEC` authorization. It rejected libXt/libimdUtil with EACCES.
The [explicit permission manifest](../lab/irix-installed-desktop/permissions.json)
sets imported ELF files to **0555**, including libraries. Resource files
remain readable; copied set-id bits are omitted. This adjustment preserves
the kernel's current native execution policy and is part of the import
recipe, not an unexplained source-image modification.

These files are built or generated by Xiri/NetBSD rather than copied from IRIX:

- `/netbsd` is the native ELF64 kernel; `/netbsd.boot` is its PROM-compatible
  ELF32 wrapper. The earlier image uses the signal checkpoint; the desktop
  service upgrade uses the [qualified filesystem/poll kernel](results/2026-11-02-irix-desktop-fs.md).
- `/usr/local/bin/xiri-desktop` launches native X and the desktop test session.
- The graphical-boot usability update configures native `/etc/ttys` for
  `ttyE0` and serial `ttyZ0` (`local softcar`), with `constty` disabled.
  `/etc/rc.local` allocates screen zero when booting with a serial console.
- `/usr/local/bin/xiri-logout` requests cleanup through a file in the current
  session directory. The session generates `4Dwmrc` from the imported
  `system.4Dwmrc`, replacing only its endsession command paths; vendor bytes
  stay intact. Native `/usr/local/libexec/xiri/save-session` coordinates
  original 4Dwm's session save before cleanup. The original panels save
  preferences separately in the user's home.
- The usability update replaces native `/usr/sbin/rpcbind` with the
  [pinned build](../lab/native-rpcbind/source.json) avoiding duplicate implicit
  loopback addresses. The utility is built from the NetBSD `xiri` fork.
- The original service upgrade added native `/usr/local/sbin/famd`, built
  from the [pinned public FAM source](../lab/native-fam/README.md), with a
  launcher-owned service mapped to UID/GID 1234. The maintained runtime uses
  `/etc/xiri/fam.conf` and independent rc.d services that survive logout.
  Its multi-user patch identifies each loopback TCP client through native
  socket ownership and applies that account's native groups.
- Native `/usr/lib/desktop` links to `/emul/irix/usr/lib/desktop`, so FAM can
  watch the same logical catalog paths as the original clients. Configure
  this before launching them; an earlier failed watch is not retried merely
  because the alias appears later. The installer refuses an incompatible
  existing path. This alias is generated integration state, not vendor data.
- `/usr/local/bin/xiri-launch` dispatches the supported menu applications.
  The runtime also supplies `/emul/irix/usr/sbin/schemebr -> colorscheme`
  when absent: the installed-image import already contains the original
  browser under `colorscheme`, while Toolchest uses its canonical name.
  No additional vendor bytes are required for this alias or for restoring
  desktop preferences. `.Sgiresources` and `.desktop-<hostname>/4DWm` are
  generated user state, not files to copy from the source image.
  Each session also derives `Xcms.txt` from the already imported
  `/emul/irix/usr/lib/X11/rgb.txt` (142 SGI aliases, 71 normalized names in
  6.5.22m). `XCMSDB` points clients at this private generated file. No new
  vendor files are needed; standard native RGB names are not replaced.
  `/usr/local/share/xiri/desktop-Xresources` is maintained integration data
  selecting the Background colour chooser's X11 mode.
  `4Dwmsession`, `4Dwmdesks` and `4Dwmdeskname` are generated per-user state;
  do not copy them from the original root account. The current TCP display
  uses `$HOME/.desktop-127.0.0.1/0.0/` for those files.
  `/usr/local/libexec/xiri/command-shell` links to native `/bin/sh` at a path
  that does not select the imported IRIX shell through emulation lookup.
  `/usr/local/share/xiri/toolchest.chestrc` includes the unchanged vendor menu
  and overrides the qualified actions using `f.exec` and `MWMSHELL`.
- `/usr/local/libexec/xiri/` contains the native session/cleanup helpers and
  the desktop/PTY setup scripts. `/usr/libexec/xiri-shell` supplies native
  controlling-terminal setup and starts NetBSD's shell in winterm.
- `/usr/local/share/xiri/xorg.conf` selects Newport, native keyboard/mouse
  drivers, explicit 1280×1024 geometry and software rendering (`NoAccel`). `fonts/fonts.dir` is generated
  by native `mkfontdir`; the font files themselves come from IRIX.
- Native `/usr/people/xiritest` stores the test user's desktop state. General
  native account creation remains described in [IRIX-SOFTWARE.md](IRIX-SOFTWARE.md).
  Foreign root sessions use `HOME=/`; the native administrator still logs in
  as NetBSD root.
- `/usr/people/xiritest/XiriTest/Examples` and `XiriTest/Readme.txt` are native
  demonstration files created during FileManager qualification, not copied
  from an IRIX user's home. Session proof files and logs are also generated.
- PTY devices, aliases and ptyfs are native runtime setup. Earlier images
  use a nullfs slave view; the terminal candidate replaces it with the native
  root symlink described in the [runtime guide](../runtime/README.md).
  `/var/tmp/xiri-desktop/session.*` stores per-launch logs; temporary working
  directories and X server state are recreated as needed.

The imported `/emul/irix/bin/sh` and `csh` are static n32 executables, outside
the current vendor ELF loading contract. Toolchest's original `.sh` actions
force `/bin/sh` even when `SHELL` or `MWMSHELL` is set; the observed launch
fork reaches `execve` and returns `ENOEXEC`. The native bridge preserves both
vendor shells and uses explicit `/emul/irix/...` application paths after
entering the native shell. Each menu-created winterm uses the existing native
PTY handoff and records it in its own `launch-winterm.*/handoff` file.
Other original menu actions still need their own compatibility work.
Typing `exit` can end the native shell while leaving its xwsh window open;
automatic terminal closure is a separate remaining issue. Session cleanup
removes these clients along with the other reserved-UID processes.

The [2026-11-05 font update](results/2026-11-05-newport-text.md) needs no new
vendor import. Winterm selects NetBSD's existing
`/usr/X11R7/lib/X11/fonts/100dpi/courB14-ISO8859-1.pcf.gz` through
`/etc/xiri/Xresources`. Its exact file/resource hashes are in
[`font-profile.json`](../lab/newport-text/font-profile.json). IRIX's original
`courB14.pcf.Z` was extracted read-only for a glyph comparison; it is not
installed in the new image. The earlier imported SGI Screen fonts remain available.

The fonts and helpers are persistent. They must not depend on `/tmp`
surviving a reboot: NetBSD clears it during startup. The initial diagnostics
exposed that mistake and a missing empty input file in the native test runner;
both are corrected and retained in the lab record.

## Deliberately separate work

Old IRIX accounts, home contents, package history, Xsgi, IRIX kernel and boot
scripts are not imported as host configuration. Existing personal layouts
are inventoried separately; system defaults and application registration
are copied while the native user generates fresh desktop state.

Thirteen original catalog targets do not resolve as files and one targets a
directory. Static ELF dependency closure does not include every application's
data tree, script commands or delayed libraries. Only xmahjongg's application
data tree is complete in this first experiment. Original `inst`/Software
Manager installation, upgrade/removal and package-history support remain
separate from copying installed files.

The [import result](results/2026-11-01-irix-installed-desktop.md) records
rendering and the remaining catalog behavior. Use the image as a reproducible
current checkpoint; complete desktop compatibility is still being developed.

## Icon Catalog reference check (2026-11-02)

SGI's [integration guide, chapter 11](https://techpubs.jurassic.nl/library/manuals/2000/007-2006-130/sgi_html/ch11.html)
uses `iconcatalog/pages/C/<page>` in its install examples, although nearby
prose omits `pages`. It distinguishes installing launcher symlinks from
compiling changed FTR sources into `.otr` tables. Makefile rules describe
those installation steps; they are not a required startup operation.
The [interface guidelines, chapter 2](https://techpubs.jurassic.nl/library/manuals/2000/007-2167-006/sgi_html/ch02.html)
specify double-click or Selected → Open, FTR-controlled actions, and icons
that change appearance to indicate running state.

Our supplied image actually uses `/usr/lib/desktop/iconcatalog/pages/C`.
The copied xmahjongg link is `pages/C/Freeware/xmahjongg`, with original
target `//usr/freeware/bin/xmahjongg`. The session sets `LANG=C` and
`LC_ALL=C`; the entire catalog and filetype trees are present. Thus neither
an absent Freeware registration nor a proven locale mismatch explained the
earlier Blank page. The [desktop repair trace](results/2026-11-02-desktop-services.md)
now establishes the missing directory/poll adapters and native FAM namespace
as discovery blockers. The [icon repair](results/2026-11-02-desktop-icons.md)
adds record locking for `desktop.otr`, seek offsets for embedded filetype
tags, and native FAM path translation. Application-specific Freeware icons
and FileManager folder/document icons now render. The original links,
compiled tables and executables remain unchanged. No new vendor assets
were needed in this cycle.

The session starts native FAM with `XIRI_FAM_ROOT=/emul/irix`. FAM watches
physical imported paths while returning the original client pathnames; it
falls back to native paths for the shared `/usr/people` home. The previous
`/usr/lib/desktop` alias is retained for existing helpers. A broad
`/usr/freeware` alias was used only to diagnose the problem and is not installed
in the reusable image. Neither the temporary filetype observer library nor
`_RLD_LIST` overrides are part of the final desktop.

The user also supplied the community page
[IRIX Customizing the Desktop](https://wiki.preterhuman.net/IRIX_Customizing_the_Desktop).
Public fetches returned HTTP 403 on 2026-11-02. The user then supplied
`~/Downloads/RUNIRIX/IRIX Customizing the Desktop - Higher Intellect Vintage Wiki.html`;
that local copy was read successfully (SHA-256
`4f50180a04627914e275dd9b043535c3a6921158dc675aba8cb17f8d42e6368d`,
wiki revision 11152, dated 2019-08-20). SGI's independently accessible
[Desktop User's Guide, customization chapter](https://techpubs.jurassic.nl/library/manuals/1000/007-1342-180/sgi_html/ch11.html)
provides the primary reference for `.sgisession`, `.auxchestrc`/`.chestrc`
and personal filetype rules under `~/.desktop-<hostname>/filetype`.
These are candidates for native-home/session support; preserve the
separation between system registration and per-user overrides. Importing
someone else's old personal state is not required to obtain system pages.

The local customization article adds these concrete follow-ups:

| Resource or setting | Xiri treatment |
| --- | --- |
| `.ftr` definitions in `/usr/lib/filetype/install` and `.fti` artwork in its `iconlib` | Already copied, together with compiled tables. Recompile when changing definitions; do not retag original binaries just to recover their installed icons. |
| `/usr/lib/X11/system.chestrc`, optional `nodesktop.chestrc`; user `.auxchestrc`/`.chestrc` | `system.chestrc` is in the ledger. Generate user overrides in the native home when needed; qualify helper launches. `nodesktop.chestrc` is an unstaged optional candidate. |
| `/usr/lib/X11/system.backgrounds` and user `.backgrounds` | System file is copied. Retain user background choices under `/usr/people/<user>`; record any selected image and renderer dependency before adding it. |
| Background image loaders and IRIX 6.5.22+ `-image` entries | Candidates for a later original-background-control test. The article's Xsgi/Xservers changes do not configure native NetBSD Xorg. Current Xorg already supplies 24-bit Newport. |
| User `.icons/login.icon`, `/usr/lib/faces/<user>`, `/usr/local/lib/faces/<user>`, `/usr/Cadmin/images/cloginlogo.rgb` | Optional visual-login assets, not present in the current import. Evaluate with the eventual native login/session integration; original `chkconfig` recipes are not NetBSD startup configuration. |

The community examples are useful leads, not directly executed recipes.
For instance, the shown FTR include line ends with a colon and one background
example has an unterminated quoted path. New rules must be checked against
SGI syntax and the actual compiler. Existing xmahjongg rules remain intact.

### Application follow-up (2026-11-02)

No vendor payload changed during the [high-address mapper and launch diagnosis](results/2026-11-02-irix-elfmap-high.md).
GIMP's `libgtk-1.2.so.1` was already staged with the required mode; the kernel
mapping range caused the failure. The existing generated helper
`/usr/local/libexec/xiri/manual-session.sh` now starts applications in HOME
and writes logs using absolute session paths. The new shell CHD includes
this helper and verifies `pwd` in winterm. The preserved icons CHD retains
the previous helper. `/usr/lib/desktop/launcheffect` and
`/usr/lib/desktop/waitmap` have since been located and privately extracted;
their runtime role remains to qualify before installation.

### GIMP application resources (2026-11-03)

After resolving signal registration, the original GIMP 1.2.5 setup requires
its application data, defaults and plug-ins. Run `scripts/stage-irix-gimp.py`
against the read-only supplied installation. Its
[ledger](../lab/irix-gimp/resources.json) records every source/destination,
checksum, original mode and applied mode. The three trees are
`/usr/freeware/{share,etc,lib32}/gimp/1.2`; the additional library files are
`libgck-1.2.so.1`, `libgtkxmhtml.so.2` and `libgimpprint.so.2` under
`/usr/freeware/lib32`. Destinations retain these paths below `/emul/irix`.
ELF files use the existing 0555 policy; scripts use 0755, other files 0644,
and directories 0755. Source bytes remain unchanged.

The payload also installs original `/sbin/sh` at `/emul/irix/sbin/sh`.
IRIX libc uses this canonical path for `popen`; the previously imported
`/bin/sh` contains identical bytes but did not cover that pathname. The
runtime installer publishes `/usr/freeware -> /emul/irix/usr/freeware` when
unused, because native `cp` invoked by the original setup script does not
apply the foreign emulation-root lookup to its arguments. Existing native
directories and links are preserved.

Image preparation accepts `--gimp-resources .work/irix-gimp-resources` and
verifies archive members, file hashes, ownership, modes and link targets.
It records the resource ledger in the resulting CHD bundle. Per-user setup
runs as xiritest in `/usr/people/xiritest`; no `.gimp-1.2` from the source
image or its package database is copied. See the
[application observations](results/2026-11-03-irix-gimp.md) for tested paths
and remaining compatibility gaps.

### GNOME VFS and gedit resources (2026-11-04)

`python3 scripts/stage-irix-gnome.py` reads the same supplied installation
with `guestfish --ro` and XFS `ro,norecovery`. It stages four trees under
`/usr/freeware`: `share/gedit`, `lib32/gedit`, `lib32/vfs` and `etc/vfs`, plus
`lib32/libgnomevfs-pthread.so`, `lib32/libbz2.so.1` and
`share/pixmaps/gedit-icon.png`. Every destination is the original path below
`/emul/irix`. The [ledger](../lab/irix-gnome/resources.json) lists 42 files
and eight directories, all source/destination pairs, hashes and modes.
ELF files use 0555, data 0644 and directories 0755, with root ownership.

The stage uses the installed-desktop and GIMP inventories to resolve existing
dependencies; dynamically loaded VFS and editor modules are explicit inputs.
The generated `.work/irix-gnome-resources/payload.tgz` is local-only. Verify
every file hash and each entry's owner, group and mode after extraction.
The diagnostic guest did so before launching gedit. Its existing native
`/usr/freeware` alias remains necessary for native helpers. No old `.gnome`
profile or package database is copied. The [application record](results/2026-11-04-irix-gnome.md)
distinguishes its working text saves from the then-failing preferences and
unresolved image/help resources. The expanded import and preference repair
are recorded below; module support alone does not supply these files.

### GNOME PTY helper (2026-11-04)

`python3 scripts/stage-irix-terminal.py` imports the original
`/usr/freeware/sbin/gnome-pty-helper` to
`/emul/irix/usr/freeware/sbin/gnome-pty-helper`. Its n32 executable is
23,120 bytes and needs the already staged `libc.so.1`. The
[ledger](../lab/irix-terminal/resources.json) records its source hash and
original 0755 mode; the destination uses 0555 and root ownership, with no
setuid bit. Extraction uses the same read-only XFS workflow. No accounting
database, user profile or package database is copied. The terminal protocol
also needs module socketpair/descriptor support and native PTY setup; the
helper alone does not establish working terminal behavior.

The subsequent [interactive-shell cycle](results/2026-11-04-irix-termios.md)
imports no further runtime payload. It adds module support for the original
shell's terminal attributes and controlling-terminal setup. Original terminal
headers were inspected read-only for constants and layout; their hashes are
recorded in [the lab](../lab/irix-terminal/termios-headers.json), and the headers
are not redistributed. Independent probes establish behavior on IRIX 6.5.22m.
The cumulative image preparation below includes this module support.

The earlier diagnostic seed contains an older `/emul/irix/etc/passwd` with
`/tmp/xiri-home` for xiritest and `/root` for root. Those fields are stale:
the native account and session HOME/cwd are `/usr/people/xiritest`, while
the intended IRIX root convention is `/`. The cumulative image preparation
migrates this synthetic file as described below. Do not copy the original
image's password database or change the native root account to compensate.


### Preferences and complete Acrobat resources (2026-11-04)

The expanded [GNOME ledger](../lab/irix-gnome/preferences-resources.json) adds
`/usr/freeware/share/gnome-terminal` and its `glade/gnome-terminal.glade` to
the prior import: 43 files and ten directories in total. Stage it separately
with `stage-irix-gnome.py --output-directory .work/irix-gnome-preferences-resources`
to preserve the earlier 50-path artifact. The original dialog works with the
rename module; GNOME Terminal, gedit and GIMP now persist preferences as
recorded in the [preference report](results/2026-11-04-irix-preferences.md).

`stage-irix-acrobat.py` stages the complete `/usr/adobe/Acrobat4.0` tree and
its missing `/usr/lib/libMrm.so.1` dependency. The [86-path ledger](../lab/irix-acrobat/resources.json)
contains 62 files, 17 directories and seven symbolic links. Every source
path is retained below `/emul/irix`, with original bytes, root ownership,
0555 ELF files, 0755 executable scripts/directories, 0644 data and unchanged
link targets. It includes acroread.dist, the actual Reader, libraries,
fonts, plug-ins, app-defaults, the sample Acrobat.pdf and reader.pdf help.
No source-image user settings or package database are imported.

The native runtime installer creates `/usr/adobe -> /emul/irix/usr/adobe`
when that native prefix is unused, preserving administrator directories and
even dangling links. Acrobat's original wrapper calls native utilities with
those absolute paths. Its existing `ACRO_CONFIG=mipsirix` override is exported
by the IRIX desktop session; native uname continues to identify NetBSD.

`prepare-xiri-xdm-image.py` now accepts verified GNOME, terminal and Acrobat
resource directories, checks archive contents/hashes/modes/owners/links and
retains their ledgers in the image. Refreshing an image preserves the inherited
GIMP resource ledger. The synthetic `/emul/irix/etc/passwd` is migrated to
xiritest HOME `/usr/people/xiritest` and IRIX root HOME `/`; native account and
password database hashes must remain unchanged. The native root home remains
`/root`. This migration applies to the generated compatibility lookup file,
not the supplied IRIX installation's accounts.

The [cumulative manual image](results/2026-11-04-irix-acrobat-image.md) now
includes these resource sets and the account migration. Its immutable CHD,
resource ledgers and separate cold application/session checks are recorded
there; previous images and diagnostic overlays remain preserved.
