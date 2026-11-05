# Icon Catalog application checklist

Updated 2026-11-04 after the [startup survey](results/2026-11-03-irix-catalog.md)
and the [GNOME](results/2026-11-04-irix-gnome.md),
[terminal](results/2026-11-04-irix-terminal.md),
[preference](results/2026-11-04-irix-preferences.md) and
[Acrobat](results/2026-11-04-irix-acrobat.md) follow-ups.
This is the requested list to use when returning to failures one by one.
It preserves all **166 registered entries in 17 system tabs** from the supplied
IRIX 6.5.22 installation, including unresolved source links that the running
catalog may omit. The eighteenth page is the user's empty **Blank** page.
Click the stacked page edges at the bottom-right of Icon Catalog to open the
[menu of all pages](results/images/2026-11-03-irix-catalog-pages.png), including
those whose tabs do not fit along the bottom.

The [2026-11-05 shared text repair](results/2026-11-05-newport-text.md)
restores native Newport software-fallback drawing, including disabled labels
and Xft/Render glyphs. Repeat previously blank UI observations on that driver
when application work resumes; this repair alone does not upgrade any entry
below to a functional pass. Missing Fontconfig or GNOME print resources remain
separate from Xorg's drawing path.

The [job-control cycle](results/2026-11-05-irix-job-control.md) adds measured
sleep, child-state and process-group support, verifies real jobs in both
shells, and fixes a separate native wait-accounting bug. Its old/new
22-target system replays verify bounded cleanup and halt; they do not upgrade
individual applications to functional passes. The original catalog stalls
remain retained and unexplained.

The original GIMP CHD survey ran as **xiritest**, UID/GID 1234, HOME and cwd
`/usr/people/xiritest`, with accelerated 1280×1024 NetBSD Xorg. There were
**124 distinct direct program-target attempts**; repeated targets share the
same startup observation. GIMP, xmahjongg and xclock retain their separately
linked bounded results. The 19 document/web entries, 13 unresolved source
links and one directory target are distinguished below.

**A window is not a functional pass.** It may be a warning, privilege request
or setup dialog. The launch guard requested a stop at its 45-second deadline;
measured cleanup could take longer. Such a stop is not a normal GUI exit or
an application crash. CPU/process samples, exact output, window observations,
interrupted queries and cleanup failures are retained in the
[machine-readable evidence](results/2026-11-03-irix-catalog.json).

The [interactive checks](results/2026-11-03-irix-catalog-interactive.json)
exercise real catalog double-clicks for Acrobat and Freeware NEdit. NEdit
accepts visible text and restores its icon after Quit/Discard, but saving
fails. Acrobat's then-missing Reader helper is supplied by the later complete
import; PDF operations and catalog launch now pass, while its running icon
remains unchanged. Other aliases
still need individual double-click, running-icon, useful-action, persistence
and normal-exit tests. Terminal tools ran with stdin closed and may require
arguments or a terminal. System/hardware tools were observed without applying
settings or installing software.

**Later module/application checks are identified in their rows.** The GNOME
follow-up uses the pathname Unix socket module and 50 additional original
resource paths in a disposable guest. Gedit passes basic document checks;
the eight other previously busy targets have new bounded startup observations.
The later terminal cycle adds socket pairs, one-descriptor transfer and native
PTY setup; its individual rows distinguish shell checks from terminal-program
support. The preference cycle adds measured rename behavior and expands the
GNOME resources to 53 paths. The [image guide](XIRI-IMAGE.md) identifies which
changes are in the selected cumulative CHD. Historical survey evidence is
retained; untested behavior is not promoted to a pass.


## Alias (2)

| Entry | Original target | Observed result / next check |
| --- | --- | --- |
| `Maya6.5` | `/usr/aw/maya6.5/bin/Maya6.5` | **No window before test stop.** UX:csh: SV=0: /bin/uname - Command not found |
| `Maya6.5_Extras` | `/usr/aw/maya6.5/bin/Maya6.5_Extras` | Directory target; browsing and its payload remain untested. |

## AliasWavefront (4)

| Entry | Original target | Observed result / next check |
| --- | --- | --- |
| `dispatcher` | `/usr/aw/COM2.0/bin/dispatcher` | **Exits 126 without a window.** xiri-catalog: /usr/aw/COM2.0/bin/dispatcher: cannot execute |
| `Dispatcher.doc` | `/usr/aw/COM2.0/doc/dispatcher_html/Dispatcher.doc` | Document/web shortcut; assigned handler and destination remain untested. |
| `Licenser` | `/usr/aw/COM2.0/bin/Licenser` | **Exits 1 without a window.** |
| `mayalive4.0` | `/usr/aw/maya6.5/bin/mayalive4.0` | Unresolved target in the original source inventory; no launch attempted. |

## Applications (31)

| Entry | Original target | Observed result / next check |
| --- | --- | --- |
| `AboutNetscapeMessenger` | `/var/netscape/communicator/AboutNetscapeMessenger` | Document/web shortcut; assigned handler and destination remain untested. |
| `acadr13` | `/opt/acad13/bin/acadr13` | **Exits 127 without a window.** /opt/acad13/bin/acadr13[14]: /bin/uname:  not found /opt/acad13/bin/acadr13[59]: /bin/uname:  not found /opt/acad13/bin/acadr13[59]: Echo:  not found /opt/acad13/bin/acadr13[63]: /opt/acad13/bin/acad:  not foun… |
| `acroread` | `/usr/adobe/Acrobat4.0/bin/acroread` | **PDF and catalog launch checks pass; running icon unchanged.** The complete original Reader package opens a nine-page PDF, changes page and zoom, reopens through its chooser and exits normally as xiritest. Applications double-click launches Reader after xdm login. Its icon remains unchanged while running and FAM records no wrapper execution event; feedback, broader PDFs, printing and browser integration remain open. [Follow-up](results/2026-11-04-irix-acrobat.md). |
| `dia` | `/usr/freeware/bin/dia` | **Exits 1 without a window.** Gtk-CRITICAL **: file gtkcontainer.c: line 713: assertion 'widget != NULL' failed. Couldn't find standard objects when looking for object-libs, exiting... |
| `evolution` | `/usr/freeware/bin/evolution` | **Error dialog in candidate.** Evolution reaches a copy-error dialog; /usr/freeware/share/evolution/default_user/* is missing. Main mail use and normal exit remain untested. [Follow-up](results/2026-11-04-irix-gnome.md). |
| `galculator` | `/usr/freeware/bin/galculator` | **Launch fails.** Exits 1. Fontconfig cannot load its default configuration and reports no fonts; UTF-8 conversion also warns. This is separate from the X-server fonts already used by the desktop. |
| `gedit` | `/usr/freeware/bin/gedit` | **Basic document and preference checks pass.** Freeware double-click, opened/closed icon artwork, text editing, new-file save, reopen, overwrite and GUI exit work as xiritest. Tab-width preferences now save and survive a normal exit/relaunch. Help, image loading, paper resources and broader plug-ins remain open. The Applications alias has not been double-clicked separately. [Follow-up](results/2026-11-04-irix-preferences.md). |
| `glynx` | `/usr/freeware/bin/glynx` | **Missing Lynx payload in candidate.** The original glynx wrapper now gets through GNOME Terminal startup and exits quickly. It invokes gnome-terminal -x lynx, but /usr/freeware/bin/lynx is absent from both the imported tree and its native alias. Import the actual browser and package resources before testing it; catalog double-click and browser use remain unqualified. [Follow-up](results/2026-11-04-irix-terminal.md). |
| `gnome-terminal` | `/usr/freeware/bin/gnome-terminal` | **Interactive original shell, catalog and preferences pass.** Applications double-click launches the original IRIX shell with its prompt and HOME/cwd /usr/people/xiritest. Typed commands, foreground Ctrl-C, resize, normal exit and running-icon feedback pass. Scrollback and other settings now persist across a normal exit/relaunch. The later direct-terminal [job checks](results/2026-11-05-irix-job-control.md) pass Ctrl-Z, bg/fg, background terminal reads and explicit waits. Help/shared-memory warnings and arbitrary nested pipelines remain open. [Preferences](results/2026-11-04-irix-preferences.md). |
| `gnome-terminal --login` | `/usr/freeware/bin/gnome-terminal --login` | Unresolved target in the original source inventory; no launch attempted. The target contains command-line text; check registration/action handling. |
| `gtop` | `/usr/freeware/bin/gtop` | **Launch fails.** Exits 1 with Function not implemented while writing its GNOME preferences; its help-topics file is also unavailable. |
| `jot` | `/usr/sbin/jot` | **Exits 0 without a new window.** |
| `lyx` | `/usr/freeware/bin/lyx` | **Window observed.** Question. Use and normal exit remain untested. LyX Warning! Couldn't determine system directory. Try the '-sysdir' command line parameter or set the environment variable LYX_DIR_11x to the LyX system directory containing the file 'chkconfig.ltx'. Using buil… |
| `maker` | `/usr/frame/bin/maker` | Unresolved target in the original source inventory; no launch attempted. |
| `MediaMail` | `/usr/bin/X11/MediaMail` | Unresolved target in the original source inventory; no launch attempted. |
| `midnight-commander` | `/usr/freeware/bin/midnight-commander` | **Missing Midnight Commander payload in candidate.** The original wrapper now gets through GNOME Terminal startup and exits quickly. It invokes gnome-terminal -x mc, but /usr/freeware/bin/mc is absent from both the imported tree and its native alias. Import the actual file manager and package resources before testing it; catalog double-click and file operations remain unqualified. [Follow-up](results/2026-11-04-irix-terminal.md). |
| `Mozilla` | `/var/netscape/mozilla/mozilla` | **Exits 1 without a window.** Cannot find mozilla runtime directory. Exiting. |
| `mozilla` | `/usr/bin/X11/mozilla` | **Exits 1 without a window.** Cannot find mozilla runtime directory. Exiting. |
| `nedit` | `/usr/sbin/nedit` | **Exits 126 without a window.** xiri-catalog: /usr/sbin/nedit: cannot execute |
| `NetscapeMail` | `/var/netscape/communicator/NetscapeMail` | Document/web shortcut; assigned handler and destination remain untested. |
| `showcase` | `/usr/sbin/showcase` | **Exits 1 without a window.** |
| `Wingz` | `/usr/bin/X11/Wingz` | Unresolved target in the original source inventory; no launch attempted. |
| `xboard` | `/usr/freeware/bin/xboard` | **Error dialog.** The chess frontend creates windows but reports a fatal error because the gnuchessx engine is missing. |
| `xbuffy` | `/usr/freeware/bin/xbuffy` | **Needs arguments.** Prints usage and exits 255 when no mailbox/file argument is supplied. Test with a configured input before judging useful operation. |
| `xearth` | `/usr/freeware/bin/xearth` | **Exits 126 without a window.** xiri-catalog: /usr/freeware/bin/xearth: cannot execute |
| `xfig` | `/usr/freeware/bin/xfig` | **Main window opens.** Xfig and its error window open; CompKeyDB is missing, disabling multi-key sequences. Drawing, save and normal exit remain untested. |
| `xmms` | `/usr/freeware/bin/xmms` | **Launch fails.** Exits 0 without a window after its control socket fails with Address family not supported by protocol family. |
| `xosview` | `/usr/freeware/bin/xosview` | **Launch fails.** Exits 0 without a window and reports sysinfo scall interface not supported. |
| `xpat2` | `/usr/freeware/bin/xpat2` | **Exits 1 without a window.** FAILED to open keyboard file "keys" xpat2: WARNING, cannot load configuration file /usr/freeware/lib/xpat/default/Cards.conf xpat2: cannot read suits |
| `xscreensaver-demo` | `/usr/freeware/bin/xscreensaver-demo` | **Window observed.** XScreenSaver 4.01, 24-Feb-2002, XScreenSaver. Use and normal exit remain untested. |
| `zsh` | `/usr/freeware/bin/zsh` | **Exits 0 without a new window.** |

## Collaboration (6)

| Entry | Original target | Observed result / next check |
| --- | --- | --- |
| `AboutNetscapeMessenger` | `/var/netscape/communicator/AboutNetscapeMessenger` | Document/web shortcut; assigned handler and destination remain untested. |
| `inperson` | `/usr/sbin/inperson` | Unresolved target in the original source inventory; no launch attempted. |
| `MediaMail` | `/usr/bin/X11/MediaMail` | Unresolved target in the original source inventory; no launch attempted. |
| `NetscapeMail` | `/var/netscape/communicator/NetscapeMail` | Document/web shortcut; assigned handler and destination remain untested. |
| `outbox` | `/usr/sbin/outbox` | **Exits 126 without a window.** xiri-catalog: /usr/sbin/outbox: cannot execute |
| `sgimeeting` | `/usr/bin/X11/sgimeeting` | **Exits 0 without a new window.** awk: can't open file /usr/SGImeeting/config/sgimeeting source line number 1 /usr/bin/X11/sgimeeting[180]: /usr/SGImeeting:  not found /usr/bin/X11/sgimeeting[181]: ./bin/sgim_cc:  not found /usr/bin/X11/sgimeet… |

## ControlPanels (18)

| Entry | Original target | Observed result / next check |
| --- | --- | --- |
| `accessibility` | `/usr/sbin/accessx` | **Error dialog.** Cannot save the active AccessX profile; xmodmap helper is also absent. |
| `audiopanel` | `/usr/sbin/audiopanel` | **Error dialog.** Reports that this machine has no audio driver. |
| `background` | `/usr/sbin/background` | **Main window opens.** Background Setting renders its pattern list and preview; Apply and persistence are untested. |
| `colorscheme` | `/usr/sbin/colorscheme` | **Window observed.** Color Scheme Browser. Use and normal exit remain untested. |
| `desktop` | `/usr/sbin/desktop` | **Main window opens.** Desktop Settings renders its controls; changing settings and persistence are untested. |
| `display` | `/usr/bin/X11/xsetmon` | **Error dialog.** Reports that the X display lacks the XSGIvc extension required by xsetmon. |
| `iconviews` | `/usr/sbin/fmprefs` | **Window observed.** Default Layout for Icon Views. Use and normal exit remain untested. |
| `keyboard` | `/usr/sbin/keyboard` | **Exits 126 without a window.** xiri-catalog: /usr/sbin/keyboard: cannot execute |
| `language` | `/usr/sbin/language` | **Exits 1 without a window.** Error:            Can't get default (en) or fallback (en) dictionaries No dictionary loaded.  Messages may be very strange Fatal Error:      Couldn't load config files Exiting |
| `monpanel` | `/usr/sbin/monpanel` | **Error dialog.** Reports that Monpanel requires a machine with the flat panel adapter. |
| `mouse` | `/usr/sbin/mouse` | **Window observed.** Mouse Settings. Use and normal exit remain untested. |
| `screensaver` | `/usr/sbin/screensaver` | **Window observed.** Screen Saver. Use and normal exit remain untested. |
| `sounds` | `/usr/sbin/dtSounds` | **Window observed.** dtSounds. Use and normal exit remain untested. |
| `syserrpanel` | `/usr/sbin/syserrpanel` | **Exits 1 without a window.** cannot read config file: /usr/lib/sysmon/notifier.config |
| `utilities` | `/usr/sbin/dtUtilities` | **Window observed.** Default Viewer & Editor Utilities. Use and normal exit remain untested. |
| `videopanel` | `/usr/sbin/videopanel` | **Window observed.** vcp. Use and normal exit remain untested. |
| `webcontrol` | `/root/usr/sbin/webcontrol` | Unresolved target in the original source inventory; no launch attempted. |
| `windows` | `/usr/sbin/windows` | **Window observed.** Window Settings. Use and normal exit remain untested. |

## Demos (2)

| Entry | Original target | Observed result / next check |
| --- | --- | --- |
| `bzflag` | `/usr/freeware/bin/bzflag` | **X observation interrupted.** The bounded X query failed; process cleanup and the guest halt are recorded. Repeat interactively before classifying the application. |
| `bzfs` | `/usr/freeware/bzfs` | Unresolved target in the original source inventory; no launch attempted. |

## DesktopTools (24)

| Entry | Original target | Observed result / next check |
| --- | --- | --- |
| `clock` | `/usr/sbin/clock` | **Exits 0 without a new window.** |
| `colorview` | `/usr/sbin/colorview` | **Exits 1 without a window.** cannot open rgb database "/usr/lib/X11/rgb" |
| `desktophelp` | `/usr/sbin/desktophelp` | **Exits 0 without a new window.** sh: /usr/bin/X11/xconfirm:  not found |
| `enterlicense` | `/usr/etc/enterlicense` | **Window observed.** License Manager 3.4 - Privileges Required. Use and normal exit remain untested. |
| `gr_osview` | `/usr/sbin/gr_osview` | **Exits 0 without a new window.** can't open memory special file |
| `ical` | `/usr/sbin/ical` | **X observation interrupted.** The bounded X query failed; process cleanup and the guest halt are recorded. Repeat interactively before classifying the application. |
| `infosearch` | `/usr/sbin/infosearch` | **Information dialog.** Explains that InfoSearch has been replaced by the configured desktop web browser; browser/document handling remains untested. |
| `insight` | `/usr/sbin/insight` | **Information dialog.** InSight opens the InfoSearch notice explaining that the configured desktop web browser replaces the client. Browser and document handling remain untested. |
| `LicenseManager` | `/usr/etc/LicenseManager` | **Privilege prompt.** Requests root privileges for installing/removing licenses and offers Continue for read-only mode; neither path was exercised. |
| `mag` | `/usr/sbin/mag` | **Missing X extension.** The automatic X query timed out. An interactive retry reports that ReadDisplay is unsupported; pointer steering failed during the attempt. Timed descendant cleanup and subsequent desktop readiness passed. Magnification remains unqualified. |
| `mailbox` | `/usr/sbin/mailbox` | **X observation interrupted.** The bounded X query failed; process cleanup and the guest halt are recorded. Repeat interactively before classifying the application. |
| `makemap` | `/usr/sbin/makemap` | **Exits 1 without a window.** ERROR #114  _GLgetfd : Cannot Open Graphics: ERR_NOGRAPHICS |
| `notepad` | `/usr/sbin/notepad` | Unresolved target in the original source inventory; no launch attempted. |
| `rcpDevice` | `/usr/lib/desktop/rcpDevice` | **Exits 1 without a window.** /usr/lib/desktop/rcpDevice[12]: test: argument expected Invalid argument: |
| `showmap` | `/usr/sbin/showmap` | **Exits 1 without a window.** ERROR #114  _GLgetfd : Cannot Open Graphics: ERR_NOGRAPHICS |
| `snoop` | `/usr/bin/snoop` | **Exits 1 without a window.** Warning: sigaltstack: Function not implemented |
| `SoftwareManager` | `/usr/sbin/SoftwareManager` | **Window observed.** SuWindow. Use and normal exit remain untested. |
| `xcalc` | `/usr/bin/X11/xcalc` | **Window observed.** Calculator. Use and normal exit remain untested. Warning: Color name "sgilightgray" is not defined Warning: Cannot convert string "calculator" to type Pixmap |
| `xclock` | `/usr/bin/X11/xclock` | [Prior bounded UTC/time pass](results/2026-11-01-irix-time.md); not repeated by this survey. |
| `xfontsel` | `/usr/bin/X11/xfontsel` | **Window observed.** xfontsel. Use and normal exit remain untested. |
| `xpsview` | `/usr/bin/X11/xpsview` | **Main window opens.** Adobe ShowPS 1.0.7 opens its main window and file selector. PostScript rendering, PDF handling and normal exit have not been tested. |
| `xshowcmap` | `/usr/bin/X11/xshowcmap` | **Window observed.** colors. Use and normal exit remain untested. |
| `xwininfo` | `/usr/bin/X11/xwininfo` | **No window before test stop.** This tool needs interactive window selection; the survey supplied no selection. |
| `xwsh` | `/usr/sbin/xwsh` | **Window observed.** xwsh. Use and normal exit remain untested. |

## DeveloperMagic (6)

| Entry | Original target | Observed result / next check |
| --- | --- | --- |
| `cvbuild` | `/usr/sbin/cvbuild` | **Exits 1 without a window.** VkMsgFacility: Couldn't find /usr/lib/CaseVision/ttutil VkMsgFacility: Warning: couldn't find case session, using default VkMsgFacility: Couldn't find /usr/lib/CaseVision/ttutil VkMsgFacility: Warning: couldn't… |
| `cvd` | `/usr/sbin/cvd` | **Exits 127 without a window.** /usr/sbin/cvd[289]: /usr/lib/WorkShop/cvmain:  not found |
| `cvmake` | `/usr/sbin/cvmake` | **Exits 1 without a window.** VkMsgFacility: Couldn't find /usr/lib/CaseVision/ttutil VkMsgFacility: Warning: couldn't find case session, using default VkMsgFacility: Couldn't find /usr/lib/CaseVision/ttutil VkMsgFacility: Warning: couldn't… |
| `cvperf` | `/usr/sbin/cvperf` | **Terminates on signal 11.** |
| `cvstatic` | `/usr/sbin/cvstatic` | **Exits 1 without a window.** VkMsgFacility: Couldn't find /usr/lib/CaseVision/ttutil VkMsgFacility: Warning: couldn't find case session, using default VkMsgFacility: Couldn't find /usr/lib/CaseVision/ttutil VkMsgFacility: Warning: couldn't… |
| `swpkg` | `/usr/sbin/swpkg` | **Exits 1 without a window.** VkMsgFacility: VkMsgOpen failed with status TT_ERR_NOMP! |

## Freeware (21)

| Entry | Original target | Observed result / next check |
| --- | --- | --- |
| `abiword` | `/usr/freeware/bin/abiword` | **Exits 0 without a new window.** Error: can't find AbiWord executables: /usr/freeware/bin/AbiWord_d -or- /usr/freeware/bin/AbiWord_s |
| `balsa` | `/usr/freeware/bin/balsa` | **Setup window in candidate.** Configure Balsa opens, with a partly blank wizard in the captured frame. Setup completion, mail operations, settings persistence and normal exit remain untested. [Follow-up](results/2026-11-04-irix-gnome.md). |
| `CUPS` | `/usr/freeware/etc/cups/CUPS` | Document/web shortcut; assigned handler and destination remain untested. |
| `dia` | `/usr/freeware/bin/dia` | **Exits 1 without a window.** Gtk-CRITICAL **: file gtkcontainer.c: line 713: assertion 'widget != NULL' failed. Couldn't find standard objects when looking for object-libs, exiting... |
| `emacs` | `/usr/freeware/bin/emacs` | **Launch fails.** Exits 0 with missing Emacs architecture data, Lisp directories and term/x-win. A complete Emacs resource import remains necessary. |
| `fluid` | `/usr/freeware/bin/fluid` | **Window observed.** fluid, Bin. Use and normal exit remain untested. |
| `FreewareRelnotes` | `/usr/freeware/relnotes/shared/FreewareRelnotes` | Document/web shortcut; assigned handler and destination remain untested. |
| `gedit` | `/usr/freeware/bin/gedit` | **Basic document and preference checks pass.** Freeware double-click, opened/closed icon artwork, text editing, new-file save, reopen, overwrite and GUI exit work as xiritest. Tab-width preferences now save and survive a normal exit/relaunch. Help, image loading, paper resources and broader plug-ins remain open. The Applications alias has not been double-clicked separately. [Follow-up](results/2026-11-04-irix-preferences.md). |
| `gftp` | `/usr/freeware/bin/gftp` | **Exits 0 without a new window.** Error: Can't find gFTP binaries installed in /usr/freeware/bin |
| `gimp` | `/usr/freeware/bin/gimp` | [Prior bounded pass: setup, paint, XCF/PNG save/reopen, catalog launch and exit](results/2026-11-03-irix-gimp.md). [Preference save, exact backup and relaunch now pass](results/2026-11-04-irix-preferences.md); wider plug-ins remain open. |
| `glade` | `/usr/freeware/bin/glade` | **Main windows in candidate.** Glade opens its main window, widget palette and properties panel. OAF activation and preference writes warn. Creating, saving and reopening a project, catalog clicks and normal exit remain untested. [Follow-up](results/2026-11-04-irix-gnome.md). |
| `gnumeric` | `/usr/freeware/bin/gnumeric` | **Font error in candidate.** Gnumeric reports no suitable default font and missing fontmap2 from its GNOME print installation. Inspect/import the original font package before spreadsheet checks. [Follow-up](results/2026-11-04-irix-gnome.md). |
| `grok` | `/usr/freeware/bin/grok` | **Window observed.** grok, Grok Dialog_popup. Use and normal exit remain untested. |
| `Maelstrom` | `/usr/freeware/bin/Maelstrom` | **Exits 1 without a window.** Couldn't create bound network socket |
| `nedit` | `/usr/freeware/bin/nedit` | **Partial use.** Freeware double-click, visible text editing, opened/closed icon artwork and Quit/Discard work. Save fails with cannot create; the file remains absent. A native write in the home’s .xiri-catalog subdirectory succeeds; a control in the exact destination directory remains pending. Exit status was not captured. |
| `plan` | `/usr/freeware/bin/plan` | **Window observed.** plan, Warning_popup. Use and normal exit remain untested. ERROR: Error while reading files: Failed to read master file ~/.dayplan, error 2 Failed to read private file ~/.dayplan.priv, error 2 ERROR: Error while reading files: Failed to read master file ~/.dayplan, err… |
| `xcdroast` | `/usr/freeware/bin/xcdroast` | **Exits 1 without a window.** ** WARNING **: Installation problem? /usr/freeware/lib32/xcdroast/bin/xcdrwrap not found. ** WARNING **: No /usr/freeware/lib32/xcdroast/bin/xcdrwrap installed ** WARNING **: (Invalid lib-directory? Check -l op… |
| `xchat` | `/usr/freeware/bin/xchat` | **Information dialog in candidate.** XChat reaches the first-run download-directory notice. It was stopped without advancing the dialog; main UI, network use, persistence and normal exit remain untested. [Follow-up](results/2026-11-04-irix-gnome.md). |
| `xmahjongg` | `//usr/freeware/bin/xmahjongg` | [Prior bounded rendering/interaction pass](results/2026-11-03-newport-xmahjongg.md); a complete game remains unqualified. |
| `xmcd` | `/usr/freeware/bin/xmcd` | **Launch fails.** Its wrapper selects bin-NetBSD-ALL/xmcd, which is absent. Check OS detection as well as the original xmcd payload before retrying. |
| `xsane` | `/usr/freeware/bin/xsane` | **Launch fails.** Exits 0 after reporting that the XSane EULA text is missing. No scanner operation was tested. |

## Imaging (2)

| Entry | Original target | Observed result / next check |
| --- | --- | --- |
| `Eclipse` | `/usr/bin/Eclipse` | **Exits 0 without a new window.** Couldn't loap pixmap "/usr/Eclipse/util/bitmaps/red_toolbox_mult" Couldn't loap pixmap "/usr/Eclipse/util/bitmaps/red_toolbox_mult" Couldn't loap pixmap "/usr/Eclipse/util/bitmaps/red_toolbox_mult" Couldn't loa… |
| `www.formvision.de` | `/usr/Eclipse/etc/www.formvision.de` | Document/web shortcut; assigned handler and destination remain untested. |

## ImagingTools (4)

| Entry | Original target | Observed result / next check |
| --- | --- | --- |
| `EcLink` | `/usr/bin/EcLink` | **Window observed.** EcLink 3.1.3, Error. Use and normal exit remain untested. Couldn't loap pixmap "/usr/Eclipse/util/bitmaps/left_point_button" Couldn't loap pixmap "/usr/Eclipse/util/bitmaps/left_point_button" Couldn't loap pixmap "/usr/Eclipse/util/bitmaps/left_point_button" Couldn't … |
| `EcMonitorSetup` | `/usr/bin/EcMonitorSetup` | **Terminates on signal 6.** Assertion failed: w->glwDrawingArea.visualInfo, file ./GLwDrawA.c, line 433 |
| `EcRender` | `/usr/bin/EcRender` | **Exits 126 without a window.** xiri-catalog: /usr/bin/EcRender: cannot execute |
| `EcWatch` | `/usr/bin/EcWatch` | **Window observed.** EcWatch 3.1.3. Use and normal exit remain untested. |

## Interoperability (1)

| Entry | Original target | Observed result / next check |
| --- | --- | --- |
| `tfxConfig` | `/usr/sbin/tfxConfig` | **Exits 126 without a window.** xiri-catalog: /usr/sbin/tfxConfig: cannot execute |

## MediaTools (22)

| Entry | Original target | Observed result / next check |
| --- | --- | --- |
| `cdman` | `/usr/sbin/cdman` | **Terminates on signal 8.** |
| `cdplayer` | `/usr/sbin/cdplayer` | **Terminates on signal 8.** |
| `compview` | `/usr/sbin/compview` | **Cleanup not verified.** X queries timed out and the launch tracker ended with absent=0, valid=0 and one remaining tracked identity. Later process snapshots do not show that PID, so an actual live-process leak is not established. The entire disposable guest subsequently halted cleanly. Investigate process tracking and application startup together. |
| `datman` | `/usr/sbin/datman` | **Exits 0 without a new window.** Can't find color named sgislateblue |
| `datplayer` | `/usr/sbin/datplayer` | **Terminates on signal 8.** |
| `image_editor` | `/usr/sbin/imged` | **Exits 0 without a new window.** /usr/sbin/imged: ReadDisplay extension not supported by current X server!usage: imged <infile> [xsize ysize [-rgb]] |
| `imgcopy` | `/usr/sbin/imgcopy` | **Exits 126 without a window.** xiri-catalog: /usr/sbin/imgcopy: cannot execute |
| `imginfo` | `/usr/sbin/imginfo` | **Exits 126 without a window.** xiri-catalog: /usr/sbin/imginfo: cannot execute |
| `imgview` | `/usr/sbin/imgview` | **Exits 126 without a window.** xiri-catalog: /usr/sbin/imgview: cannot execute |
| `imgworks` | `/usr/sbin/imgworks` | **Exits 126 without a window.** xiri-catalog: /usr/sbin/imgworks: cannot execute |
| `macromedia` | `/usr/sbin/macromedia` | Unresolved target in the original source inventory; no launch attempted. |
| `mediaconvert` | `/usr/sbin/mediaconvert` | **Window observed.** MediaConvert. Use and normal exit remain untested. |
| `mediaplayer` | `/usr/sbin/mediaplayer` | **Window observed.** MediaPlayer. Use and normal exit remain untested. |
| `mediarecorder` | `/usr/sbin/mediarecorder` | **Terminates on signal 6.** libmovierecord failed to create shared arena at /var/tmp/.mvrlBAAa000Fv: out of disk space?  swap space? Assertion failed: queue, file events.c, line 580 |
| `moviemaker` | `/usr/sbin/moviemaker` | **X observation interrupted.** The bounded X query failed; process cleanup and the guest halt are recorded. Repeat interactively before classifying the application. |
| `musicplayer` | `/usr/sbin/musicplayer` | **Exits 1 without a window.** Error Loading Skin.. sh: /sbin/tar:  not found sh: /usr/sbin/gzip:  not found |
| `soundeditor` | `/usr/sbin/soundeditor` | **Exits 0 without a new window.** Could not get input sample rate. |
| `soundplayer` | `/usr/sbin/soundplayer` | **Exits 1 without a window.** soundplayer: no audio output devices found |
| `soundtrack` | `/usr/sbin/soundtrack` | **Terminates on signal 8.** |
| `videoin` | `/usr/sbin/videoin` | **Exits 0 without a new window.** videoin: error opening video: VL: Failed allocation of resource or memory |
| `videoout` | `/usr/sbin/videoout` | **Exits 1 without a window.** /usr/sbin/videoout: couldn't open VL video |
| `videopanel` | `/usr/sbin/videopanel` | **Window observed.** vcp. Use and normal exit remain untested. |

## Printing (3)

| Entry | Original target | Observed result / next check |
| --- | --- | --- |
| `printers` | `/usr/sbin/printers` | **Window observed.** Printer Manager for xiritest@xiri-indy, Error. Use and normal exit remain untested. Warning: Color name "SGIVeryLightGrey" is not defined sh: /usr/bin/lpstat:  not found sh: /usr/bin/lpstat:  not found |
| `PrintPanel` | `/usr/sbin/PrintPanel` | **Window observed.** PrintPanel on xiri-indy, Error. Use and normal exit remain untested. Warning: Color name "SGILightGrey" is not defined sh: /usr/bin/lpstat:  not found sh: /usr/bin/lpstat:  not found |
| `PrintStatus` | `/usr/sbin/PrintStatus` | **Window observed.** Error. Use and normal exit remain untested. sh: /usr/bin/lpstat:  not found |

## SupportTools (4)

| Entry | Original target | Observed result / next check |
| --- | --- | --- |
| `confidence` | `/usr/sbin/confidence` | **Window observed.** Confidence Tests. Use and normal exit remain untested. Warning: Color name "SGIVeryLightGrey" is not defined /bin/sh: /usr/sbin/showprods:  not found |
| `Embedded_Support_Partner` | `/var/esp/ssc/ESPartnerURL` | Document/web shortcut; assigned handler and destination remain untested. |
| `Supportfolio_Online` | `/usr/share/WebMagic/jumpsites/Supportfolio_Online` | Document/web shortcut; assigned handler and destination remain untested. |
| `SupportInfo` | `/usr/share/WebMagic/jumpsites/SupportInfo` | Document/web shortcut; assigned handler and destination remain untested. |

## WebTools (12)

| Entry | Original target | Observed result / next check |
| --- | --- | --- |
| `AboutNetscapeMessenger` | `/var/netscape/communicator/AboutNetscapeMessenger` | Document/web shortcut; assigned handler and destination remain untested. |
| `ApacheGuide` | `/var/sgi_apache/server/share/htdocs/ApacheGuide` | Document/web shortcut; assigned handler and destination remain untested. |
| `InfoSearch` | `/usr/lib/infosearch/C/InfoSearch` | Document/web shortcut; assigned handler and destination remain untested. |
| `mozilla` | `/usr/bin/X11/mozilla` | **Exits 1 without a window.** Cannot find mozilla runtime directory. Exiting. |
| `netscape` | `/usr/bin/X11/netscape` | **Exits 1 without a window.** |
| `NetscapeMail` | `/var/netscape/communicator/NetscapeMail` | Document/web shortcut; assigned handler and destination remain untested. |
| `outbox` | `/usr/sbin/outbox` | **Exits 126 without a window.** xiri-catalog: /usr/sbin/outbox: cannot execute |
| `SiliconSurf` | `/usr/share/WebMagic/jumpsites/SiliconSurf` | Document/web shortcut; assigned handler and destination remain untested. |
| `sitemgr` | `/usr/sbin/sitemgr` | **Exits 126 without a window.** xiri-catalog: /usr/sbin/sitemgr: cannot execute |
| `webjumper` | `/usr/sbin/webjumper` | **Window observed.** WebJumper. Use and normal exit remain untested. |
| `WebSetup` | `/var/www/htdocs/webface/WebSetup` | Unresolved target in the original source inventory; no launch attempted. |
| `WelcomeToWeb` | `/var/netscape/communicator/WelcomeToWeb` | Document/web shortcut; assigned handler and destination remain untested. |

## WhatsNew (4)

| Entry | Original target | Observed result / next check |
| --- | --- | --- |
| `New_IRIX_Info` | `/var/www/htdocs/WhatsNew/New_IRIX_Info` | Document/web shortcut; assigned handler and destination remain untested. |
| `sgimeeting` | `/usr/bin/X11/sgimeeting` | **Exits 0 without a new window.** awk: can't open file /usr/SGImeeting/config/sgimeeting source line number 1 /usr/bin/X11/sgimeeting[180]: /usr/SGImeeting:  not found /usr/bin/X11/sgimeeting[181]: ./bin/sgim_cc:  not found /usr/bin/X11/sgimeet… |
| `WebSetup` | `/var/www/htdocs/webface/WebSetup` | Unresolved target in the original source inventory; no launch attempted. |
| `Welcome_to_SGI` | `/var/www/htdocs/WhatsNew/Welcome_to_SGI` | Document/web shortcut; assigned handler and destination remain untested. |

## Blank (user page, 0)

The native directory listing confirms that `.desktop-xiri-indy/iconcatalog/pages/Blank`
is empty. It is an additional user page, not a missing system-application tab.
