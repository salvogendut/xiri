# IRIX resource checklist

This is the running record of what xiri needs from the supplied IRIX image.
It separates demonstrated runtime inputs, extracted candidates and assets
still to locate. A file's presence in the image does not prove it is required.
The [resource ledger](../lab/irix-desktop/resource-ledger.json) provides the same
categories in machine-readable form; the linked manifests own the checksums.

Original bytes stay in ignored `.work`. Extract read-only with `ro,norecovery`,
pin the selected files, and stage them in disposable guests with explicit file
modes. New discoveries should update this checklist, their manifest and the
experiment that establishes whether the resource is actually used.

## Already extracted

| Resource | Image paths | Evidence and current use |
| --- | --- | --- |
| Original applications and runtimes | Toolchest/4Dwm under `/usr/bin/X11`; `/usr/sbin/winterm`, `/usr/sbin/xwsh`; ABI-specific rld/libc and library closures | [Desktop](../lab/irix-desktop/manifest.json), [winterm](../lab/irix-winterm/manifest.json), [xclock](../lab/irix-xclock/manifest.json). Keep complete per-application closures; static DT_NEEDED discovery does not cover later loading. |
| Toolchest menu and defaults | `/usr/lib/X11/system.chestrc`, `/usr/lib/X11/app-defaults/Toolchest` | [Desktop manifest](../lab/irix-desktop/manifest.json); observed menu loading/rendering. Both are staged unchanged in the [input lab](../lab/irix-toolchest-input/README.md). |
| Motif key names | `/usr/lib/X11/XKeysymDB` | [Resource pin](../lab/irix-toolchest-input/resources.json). Missing names produce translation errors and prevent tested keyboard navigation; install readable by ordinary users under `/emul/irix`. |
| SGI color values | `/usr/lib/X11/rgb.txt` | [Resource pin](../lab/irix-toolchest-input/resources.json). Source of numeric SGIGray76/SGIDarkGray values. Current Toolchest uses explicit Xt numeric overrides. Original xclock additionally requests SGILightGray (170,170,170) and SGISlateBlue (113,113,198), both present in this file; its current launch still warns about those names. Copying the file does not constitute qualified server color-name support. |
| SGI Screen fonts | `/usr/lib/X11/fonts/misc/Scr*.pcf[.Z]` | [Selected font manifest](../lab/irix-x11-fonts/manifest.json): 22 fonts, 118,634 bytes. All 22 are indexed; xwsh's requested 15-pixel medium face renders in native xterm in both modes/identities. Use the native X server's font path, distinct from the foreign filesystem. |
| X locale data | `/usr/lib/X11/locale/locale.alias`, `locale.dir`, `C/{XI18N_OBJS,XLC_LOCALE}`, `iso8859-1/{Compose,XI18N_OBJS,XLC_LOCALE}` | [Font/locale manifest](../lab/irix-x11-fonts/manifest.json). Alias/directory files were already staged; the [resource experiment](../lab/irix-x11-fonts/README.md) adds C/ISO8859-1 data separately from fonts; the [access follow-up](results/2026-10-31-irix-winterm-access.md) verifies successful checks and reads of `C/XLC_LOCALE`, clearing the earlier locale/font failure. External modules mentioned by XI18N_OBJS and other locales remain unqualified. |
| Terminal defaults and launcher | `/usr/lib/X11/app-defaults/XWsh`, `IWsh`; `/usr/sbin/winterm`; `/usr/bin/gettxt` | [Winterm manifest](../lab/irix-winterm/manifest.json). XWsh defaults are now checked and read successfully. IWsh consumption remains unqualified. The launcher’s gettxt helper still fails exec; explicit WINTERM allows the unchanged script to launch xwsh with a native shell. |
| Window-manager and desktop defaults | `/usr/lib/X11/app-defaults/4DWm`, `system.4Dwmrc`, `system.4Dwmdesks`, `system.backgrounds` | [Desktop manifest](../lab/irix-desktop/manifest.json). Staged for the 4Dwm startup experiment. Its 4 KiB library boundary is resolved; GL initialization now passes its fixed/local mapping; the PRDA checkpoint clears the subsequent libc fault. Explicit mode 0444 is required after copying onto existing resource files: correct hashes alone did not ensure UID1234 could read them. The readable defaults work for window management with SG_manageSession/SG_autoSave disabled. Saved-session file operations, referenced artwork and full runtime behavior still need qualification. |
| Session scripts and default icon/device lists | `/usr/lib/X11/xdm/Xsession`, `Xsession.dt`, `Xresources`, `DefaultDeviceList`, `DefaultIconList`; corresponding `/var/X11/xdm` paths | [Session analysis](../lab/irix-desktop/session.json) and [desktop manifest](../lab/irix-desktop/manifest.json). Reference for launch order, resource lookup, per-screen setup and restoration. Adapt selected behavior to native X.org/NetBSD services. |
| Desktop helpers and programs | `/usr/lib/desktop/*`; `/usr/sbin/fm`, `bgicons`, `iconcatalog`, `genDeviceIcons`, `FLtoPopDB`; `/usr/bin/X11/wait4wm`, `tellwm`, `reaper` | [Desktop manifest](../lab/irix-desktop/manifest.json). Initial files/metadata extracted; executable/library closures, delayed modules and runtime data remain to be inventoried. |

## Still to locate or qualify

| Candidate | What to record next |
| --- | --- |
| Icon, bitmap, cursor and backdrop assets | Resolve filenames referenced by 4Dwm, fm, bgicons, iconcatalog and the default icon/background lists. Preserve image formats, directory layout and case. Current helper inventory is not an artwork inventory. |
| File-type rules and actions (FTR) | Locate the selected installation's rules, referenced icons and command handlers. Separate file identification from executing an action. |
| Color schemes, palettes and saved preferences | xwsh actually probes `/usr/lib/X11/{,C/}schemes/{Base,Myers}/BaseColorPalette` and `$HOME/.desktop-xiri-indy/schemes/{Base,Myers}/BaseColorPalette`. The implemented checks return `ENOENT` for these candidates in the guest, and xwsh continues to terminal setup. Inventory the image files and qualify appearance separately. Two numeric Toolchest colors do not establish full SGI appearance. |
| Additional fonts, aliases and encodings | Record actual requests from each original client. The private inventory has broader Fixed-font metadata; only the selected Screen family is in the import experiment. Preserve XLFD names and alias relationships. |
| Locale/input-method modules and catalogs | Resolve any actual module loads named by XI18N_OBJS; inventory message catalogs used by gettxt and desktop helpers. The xwsh error path now probes `/usr/lib/locale/C/LC_MESSAGES/uxsyserr`, `C/Xopen/LC_MESSAGES/uxsyserr` and `C/LC_MESSAGES/uxsyserr.cat`; the later fork failure also probes the corresponding `uxsgierr` paths. Their absence does not prevent the fallback English diagnostic. Multilingual locales and input methods are separate from the current C-locale checks. |
| File monitoring and desktop services | Trace fm/fam-related behavior, cache helpers, device icon discovery and interprocess messages. Pin required binaries, data and protocol behavior before selecting an original or native service. |
| Help and application catalogs | Inventory the selected SGIHelp/InSight, Icon Catalog and application registration data when their launch paths are reached. Installed manuals are also useful private behavior references. |
| Conditional session helpers | Qualify soundscheme/audio settings, powersaver, sysmon integration, first-login tasks and user `.sgisession` hooks separately; they are not all prerequisites for the first desktop display. |

## State supplied by xiri

`HOME`, a writable per-user home, user/group records, shell selection and X
connection credentials are session configuration. They should be supplied for
the NetBSD user rather than copied as old machine/account state. Current probes
use an explicit environment; an absent HOME caused an earlier Toolchest crash,
and xwsh rejects a numerical uid without an account record. The font experiment
uses synthetic foreign passwd/group fixtures to investigate that lookup.

Per-user `.desktop` state, `.chestrc`, `.Sgiresources`, `.Xdefaults` and saved
sessions must be tracked as generated or deliberately migrated state, distinct
from system defaults. XUSERFILESEARCHPATH, locale and helper PATH choices also
belong in the launch record. NetBSD's shell and native X.org server remain the
foundation. The [PTY checkpoint](results/2026-10-31-irix-pty.md) uses native
ptm/ptyfs allocation and ownership, a group-0/mode-0600 disposable ptyfs mount,
and a nullfs view under `/emul/irix/dev/pts` with the first 400 IRIX q/r aliases.
These are generated native session resources, not files to import from IRIX.
The [shell checkpoint](results/2026-11-01-irix-shell.md) now runs native
`/bin/sh` through original winterm/xwsh and accepts typed commands. No further
image resources were needed: the existing Screen fonts, C locale, XWsh defaults
and original runtime closure suffice for this path. The native helper verifies
and reopens `/dev/pts/N` before acquiring the controlling terminal, sets 80x24,
and execs `/bin/sh -i`; this avoids the observed layered-tty revoke panic.
The test uses explicit HOME, PATH, WINTERM and a reserved numeric UID; production
account/session setup, gettxt, foreign signal handlers, resize and normal app
exit still need work. The image's Xsgi, kernel, device nodes and boot
scripts remain reference inputs for the native NetBSD integration.

The [desktop acceptance plan](ROADMAP.md#milestone-3-original-desktop-proof)
links the supplied SGI interface guidelines. A component is complete only when
its resources and behavior have both been checked in the supported session.

The [4Dwm loader checkpoint](results/2026-11-01-irix-elfmap-subpage.md) now handles the two 4 KiB data boundaries and passes 750 mapping/limit checks. The [fixed/local mmap checkpoint](results/2026-11-01-irix-mmap-local.md) now also clears GL initialization, with 660 mapping cases and native page-zero controls. The [measured PRDA checkpoint](results/2026-11-01-irix-prda.md) now clears that libc fault, with 80 executions / 180 records plus fork and native-exec controls. The [4Dwm session](results/2026-11-01-irix-4dwm.md) now passes reparenting, pointer focus, key delivery and dragging alongside Toolchest and a working winterm shell. Session saving is explicitly disabled; desks, restoration and complete desktop services remain open.

The combined [4Dwm session](results/2026-11-01-irix-4dwm.md) also explicitly
installs the pinned XKeysymDB and rgb.txt in mode 0444. Its shell-only seed did
not include the prior Toolchest keysym installation. These are existing image
assets, not additional dependencies to extract. The remaining Trusted Path
panel/SGI-AccessControl behavior needs feature-query investigation; no new
font import was required for this window-manager step.

With session saving enabled, 4Dwm probes HOME/.xroomsrc, its .tmp peer and
HOME/.desktop-127.0.0.1 for the controlled display. The captured path hits
unimplemented mkdir/unlink/fsync/rename and later `(null).tmp`. These are
generated user-state dependencies to implement and qualify, not missing
original artwork or configuration files to extract.
